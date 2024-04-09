<?php
header('Content-Type: application/json');

// API URL
$url = 'http://localhost:5000/query';

// Get JSON input and decode it
$inputJSON = file_get_contents('php://input');
$input = json_decode($inputJSON, true);  // decode as array
$userInput = $input['message'];

// Data to be sent
$data = json_encode(array("input" => $userInput));

// Use cURL for HTTP POST request
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Content-Length: ' . strlen($data)
]);

// Execute cURL session
$response = curl_exec($ch);
if (!$response) {
    die(json_encode(['response' => 'Error: "' . curl_error($ch) . '" - Code: ' . curl_errno($ch)]));
}
curl_close($ch);

// Decode JSON data
$responseData = json_decode($response, true);

// Output the response
echo json_encode(['response' => $responseData['response'] ?: 'No response received.']);
?>
