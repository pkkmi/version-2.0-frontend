# Andikar AI Frontend

A Flask frontend application for humanizing AI-generated text using the Andikar AI ecosystem.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- [Andikar Humanizer API](https://github.com/granitevolition/text-humanizer-api) running at https://web-production-3db6c.up.railway.app/ or another endpoint

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/granitevolition/andikar-frontend.git
   cd andikar-frontend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```
   cp .env.example .env
   ```
   Edit `.env` file to set the appropriate values, especially:
   - `HUMANIZER_API_URL` - URL to your running Humanizer API service

## Running the Application

Start the Flask development server:
```
python app.py
```

The application will be available at http://localhost:5000/

### Testing the Humanizer API Connection

If you're having problems with the Humanizer API connection, use the diagnostic tool:

```
python test_api.py
```

This script will test the connection to the Humanizer API and provide detailed information about any issues.

## Troubleshooting

### Humanizer API Connection Issues

If the humanizing functionality is not working:

1. Check that the Humanizer API is running at the URL specified in your `.env` file
2. Run `python test_api.py` to diagnose connection issues
3. Verify that the endpoint is correct (should be `/humanize_text`)
4. Check for any network/firewall issues that might block the connection
5. Inspect the logs for detailed error information

The application includes a fallback humanization function if the API is temporarily unavailable.

## Features

- User authentication and registration
- Text humanization using external API
- AI content detection
- User dashboard with usage statistics
- Tiered pricing plans with word limits
- M-Pesa payment integration (simulated)
- API key management for integration

## Project Structure

- `app.py` - Main Flask application
- `utils.py` - Utility functions including API integration
- `models.py` - Data models and in-memory databases
- `templates/` - HTML templates (embedded in templates.py)
- `static/` - CSS and JavaScript files
- `config.py` - Application configuration
- `test_api.py` - Diagnostic tool for API connection

## Deployment

The application is designed to be deployed on Railway.app or similar platform. See the Railway documentation for deployment instructions.
