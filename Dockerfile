# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set environment variables:
# Python won't try to write .pyc files on the import of source modules
# Python outputs its output straight to the terminal without buffering it first
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory to /app in the container
WORKDIR /app

# Install system dependencies (if any)
# For example, you might need gcc to compile certain Python packages, or other utilities.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable to configure Flask to run in development mode
ENV FLASK_ENV=development

# Run the application:
# Use Gunicorn as the WSGI server to serve the Flask app (more robust and suited for production than Flask's built-in server)
CMD ["gunicorn", "--config", "gunicorn-config.py", "wsgi:app"]
