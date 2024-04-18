import json
import random
import requests
import sys
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import nltk
from nltk.stem import WordNetLemmatizer
from transformers import pipeline
import language_tool_python


class ChatbotService:
    def __init__(self):
        self.conversation_context = {
            'last_intent': None,
            'last_entities': None,
            'last_response': None
        }
        self.tool = language_tool_python.LanguageTool('en-US')
        self.initialize_nltk()
        self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
        self.qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
        self.lemmatizer = WordNetLemmatizer()
        self.headers = {
            'Authorization': 'Bearer 8|uWuvC6BOGDz2LzvCVeNcLh9La0FjRgP6NMEuE2ic',
        }
        self.articles = self.get_articles()

    def initialize_nltk(self):
        nltk.download('punkt')
        nltk.download('wordnet')
        nltk.download('omw-1.4')

    def get_articles(self):
        response = requests.get('https://pip.edu.ge/api/v1/articles', headers=self.headers)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f'Error: {response.status_code}', response.text)
            return []

    def correct_grammar(self, text):
        # Check the text for grammatical errors
        matches = self.tool.check(text)

        # Automatically apply suggestions to correct the text
        corrected_text = language_tool_python.utils.correct(text, matches)

        # Ensure the corrected text starts with a capital letter and ends with a period
        corrected_text = corrected_text.strip().capitalize()
        if not corrected_text.endswith('.'):
            corrected_text += '.'

        return corrected_text

    def preprocess_text(self, text):
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text(separator=' ')
        tokens = nltk.word_tokenize(text)
        return [self.lemmatizer.lemmatize(token.lower()) for token in tokens if token.isalpha()]

    def fetch_from_witai(self, user_query):
        url = f"https://api.wit.ai/message?q={user_query}"
        response = requests.get(url, headers={"Authorization": "Bearer 7J5ZT2ZAR2ICKM5GSQPGXDJ3CCNPAYXO"})
        if response.status_code == 200:
            data = response.json()
            intent = data["intents"][0]["name"] if data["intents"] else None
            entities = {}
            if 'entities' in data:
                for key, val in data['entities'].items():
                    # Assuming each key in entities maps to a list of dicts
                    if val:  # Check if val is not an empty list
                        # Extract the first item's role and value
                        entities[val[0]['role']] = val[0]['value']
            return intent, entities
        return None, {}

    def entity_in_text(self, entity, text):
        # Lowercase both for case-insensitive comparison
        entity_lower = entity.lower()
        text_lower = text.lower()
        # Check if the entire entity phrase is in the text
        return entity_lower in text_lower

    def search_articles(self, entities):
        # Find matching articles based on lemmatized entities
        matching_articles = []

        # First attempt: Using lemmatized entities against lemmatized article content
        lemmatized_entities = [self.lemmatizer.lemmatize(entity.lower()) for entity in entities.values()]

        for lemmatized_entitity in lemmatized_entities:
            for article in self.articles:
                article['processed_text'] = self.preprocess_text(article['info']['text'])
                article['processed_title'] = self.preprocess_text(article['info']['title'])

                if lemmatized_entitity in article['processed_title'] or lemmatized_entitity in article[
                    'processed_text']:
                    matching_articles.append(article)

        if not matching_articles:
            for lemmatized_entitity in lemmatized_entities:
                for article in self.articles:
                    full_lemmatized_content = ' '.join(
                        article['processed_title'] + article['processed_text'])
                    if lemmatized_entitity in full_lemmatized_content:
                        matching_articles.append(article)

        return matching_articles

    def generate_response(self, intent, matching_articles, entities):
        if not matching_articles:
            return {
                "message": "I'm sorry, I couldn't find any article related to this topic.",
                "titles": []
            }

        num_articles = len(matching_articles)  # Get the count of articles
        titles = [f"{index + 1}) {article['info']['title']}" for index, article in enumerate(matching_articles)]
        response = {
            "message": f"I have found relevant information in these {num_articles} articles:",
            "titles": titles,
            "answer": self.generate_intent_based_answer(intent, entities, matching_articles)
        }
        return response

    def chunk_text(self, text, chunk_size=1024):
        tokens = text.split()
        return [' '.join(tokens[i:i + chunk_size]) for i in range(0, len(tokens), chunk_size)]

    def generate_intent_based_answer(self, intent, entities, articles):
        answers = ""
        # Combine texts from all matching articles for a broad context
        plain_context = ""
        for article in articles:
            plain_context += ' '.join(
                article['processed_title'] + article['processed_text'])
            plain_context += "\n\n"

        # Define required entity keys for each intent
        if intent == 'get_contribution_between_subject_and_context':
            required_keys = ['message_subject', 'context']
        elif intent == 'get_definition_of_subject':
            required_keys = ['message_subject']
        elif intent in ['get_examples_of_benefits', 'get_examples_of_influence']:
            required_keys = ['influencing_factor', 'influencing_outcome']
        elif intent == 'query_relationship_between_subject_and_context':
            required_keys = ['relationship_type', 'message_subject', 'context']
        else:
            required_keys = []

        # Resolve entities based on the intent
        resolved_entities = self.resolve_entities(entities, required_keys)

        # Formulate a question based on the intent and entities
        if intent == 'get_contribution_between_subject_and_context':
            question = f"How does {resolved_entities.get('message_subject')} contribute to {resolved_entities.get('context')}?"
        elif intent == 'get_definition_of_subject':
            question = f"What is the definition of {resolved_entities.get('message_subject')}?"
        elif intent == 'get_examples_of_benefits':
            question = f"What are the examples of benefits between {resolved_entities.get('influencing_factor')} and {resolved_entities.get('influencing_outcome')}?"
        elif intent == 'get_examples_of_influence':
            question = f"What are the examples of influence between {resolved_entities.get('influencing_factor')} and {resolved_entities.get('influencing_outcome')}?"
        elif intent == 'query_relationship_between_subject_and_context':
            question = f"What is the {resolved_entities.get('relationship_type')} between {resolved_entities.get('message_subject')} and {resolved_entities.get('context')}?"
        else:
            # Default or fallback question formulation
            question = ""

        print("\n\nThe intent is: " + intent)
        print("\nAsking question: " + question)
        # Generate answer from the QA model

        answers = self.answer_question(question, plain_context)
        # context_chunks = chunk_text(plain_context)
        # for context in context_chunks:
        #     answer = answer_question(question, context)
        #     answers = answers + answer + "\n"
        return answers

    def resolve_entities(self, entities, required_keys):
        """
        Dynamically assigns entities to required keys, using available entities when some are missing.
        :param entities: Dictionary of entities from wit.ai
        :param required_keys: List of required entity keys for the specific intent
        :return: Dictionary with resolved entities
        """
        resolved_entities = {}
        used_keys = set()

        # First pass: Assign available entities to their matching keys
        for key in required_keys:
            if entities.get(key):
                resolved_entities[key] = entities[key]
                used_keys.add(key)

        missing_keys = set(required_keys) - set(resolved_entities.keys())
        available_entities = {k: v for k, v in entities.items() if k not in used_keys and v is not None}

        # Second pass: Fill in missing keys with available entities
        for key in missing_keys:
            if available_entities:
                # This picks a random entity to assign, modify as needed
                chosen_key, chosen_value = random.choice(list(available_entities.items()))
                resolved_entities[key] = chosen_value
                del available_entities[chosen_key]
            else:
                resolved_entities[key] = "a value"  # Placeholder for missing entities, adjust as necessary

        return resolved_entities

    def answer_question(self, question, context):
        result = self.qa_pipeline(question=question, context=context)
        if result and 'answer' in result:
            formatted_answer = self.correct_grammar(result['answer'])
            return formatted_answer
        return "No answer found."

    def update_conversation_context(self, intent, entities, response):
        self.conversation_context['last_intent'] = intent
        self.conversation_context['last_entities'] = entities
        self.conversation_context['last_response'] = response

    def handle_user_query(self, user_query):
        # Fetch intent and entities from Wit.ai
        intent, entities = self.fetch_from_witai(user_query)

        # If specific intent is found, then process accordingly
        if intent in ['get_contribution_between_subject_and_context',
                      'get_definition_of_subject',
                      'get_examples_of_benefits',
                      'get_examples_of_influence',
                      'query_relationship_between_subject_and_context']:
            # Here, handle the extraction and usage of multiple entities
            matching_articles = self.search_articles(entities)
            response = self.generate_response(intent, matching_articles, entities)
            self.update_conversation_context(intent, entities, response)
        else:
            response = (
                "Hmm, I'm not quite sure what you're asking. Could you provide more detail or ask about something "
                "else?")

        return response

    # Add other methods like search_articles, generate_response, etc.


app = Flask(__name__)
CORS(app, supports_credentials=True)
chatbot_service = ChatbotService()


@app.route('/query', methods=['POST'])
def handle_query():
    user_input = request.json.get('input')
    response = chatbot_service.handle_user_query(user_input)
    print(response)
    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
