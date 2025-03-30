# Andikar AI Backend v2.2

Backend service for the Andikar AI Frontend application, designed to humanize AI-generated text.

## Features

- User registration and authentication
- Text humanization API
- MongoDB integration for data storage

## Requirements

- Python 3.8+
- MongoDB

## Configuration

The application uses environment variables for configuration:

- `MONGODB_URI`: MongoDB connection string
- `SECRET_KEY`: Secret key for JWT encoding
- `HUMANIZER_API_URL`: URL for humanizer API service
- `PORT`: Port for the application to run on (default: 5000)

## API Endpoints

### Authentication

- `POST /api/register`: Register a new user
  - Request: `{ "username": "user", "email": "user@example.com", "password": "password" }`
  - Response: `{ "success": true, "message": "User registered successfully", "user_id": "id" }`

- `POST /api/login`: Login and get JWT token
  - Request: `{ "username": "user", "password": "password" }`
  - Response: `{ "success": true, "message": "Login successful", "user": {...}, "access_token": "token" }`

### Humanization

- `POST /api/humanize`: Humanize text (requires JWT token)
  - Request: `{ "text": "Text to humanize" }`
  - Response: `{ "success": true, "message": "Text humanized successfully", "humanized_text": "Humanized text", "user": {...} }`

### System

- `GET /api/status`: Check API status
  - Response: `{ "status": "online", "humanizer_api": "online" }`