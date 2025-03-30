# Andikar AI Frontend with MongoDB Integration

A Flask frontend application for humanizing AI-generated text using the Andikar AI ecosystem, now with MongoDB database integration.

## New Features in This Version

- **MongoDB Integration**: User data, transactions, and payment history are now stored in MongoDB
- **Persistent Storage**: Data persists across application restarts and deployments
- **Enhanced API**: Integration with the Lipia backend service for payment processing
- **Improved Deployment**: Better Railway deployment support with Procfile

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- MongoDB database (can use Railway's MongoDB service)
- [Andikar Humanizer API](https://github.com/granitevolition/text-humanizer-api) running at https://web-production-3db6c.up.railway.app/ or another endpoint
- [Lipia MongoDB Backend](https://github.com/granitevolition/lipia-mongodb-backend) - The backend service for payment processing

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/pkkmi/version-2.0-frontend.git
   cd version-2.0-frontend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
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
   - `MONGO_URL` - MongoDB connection URL
   - `MONGOUSER`, `MONGOPASSWORD`, `MONGOHOST`, `MONGOPORT` - MongoDB connection details
   - `HUMANIZER_API_URL` - URL to your running Humanizer API service
   - `LIPIA_API_URL` - URL to your running Lipia backend service

## Running the Application

Start the Flask development server:
```
python app.py
```

The application will be available at http://localhost:5000/

### Setting up the Lipia Backend

For full functionality, you should also set up the Lipia MongoDB Backend service:

1. Clone the backend repository:
   ```
   git clone https://github.com/granitevolition/lipia-mongodb-backend.git
   cd lipia-mongodb-backend
   ```

2. Install dependencies and set up the backend as per its README instructions

3. Make sure both applications are using the same MongoDB database

## MongoDB Schema

The application uses these MongoDB collections:

- **users**: Stores user accounts, including username, pin, word balance
- **payments**: Records payment transactions
- **transactions**: Tracks payment processing status

## Railway Deployment

This application is optimized for Railway deployment:

1. Create a new Railway project
2. Connect your GitHub repository to Railway
3. Add the MongoDB plugin to your project
4. Configure environment variables in Railway:
   - Set `MONGO_URL` to the value from Railway MongoDB plugin
   - Add all other environment variables from `.env.example`
   - Set `LIPIA_API_URL` to point to your deployed Lipia backend

### Testing the API Connections

The application includes a diagnostic tool:

```
http://your-app-url/api-test
```

This will test the connections to both the Humanizer API and the Lipia Backend API.

## Troubleshooting

### MongoDB Connection Issues

- Verify the MongoDB connection string and credentials
- Check if MongoDB service is running
- Ensure network connectivity to MongoDB server

### API Connection Issues

- Verify that the Humanizer API and Lipia Backend API are running
- Check the URLs in your `.env` file
- Run the API test to diagnose connection issues
- Check for network/firewall issues that might block the connections

## Features

- User authentication and registration with MongoDB storage
- Text humanization using external API
- AI content detection
- User dashboard with usage statistics and MongoDB-backed history
- Tiered pricing plans with word limits
- Payment processing with MongoDB transaction tracking
- Word credit management
- API key management for integration

## Project Structure

- `app.py` - Main Flask application
- `utils.py` - Utility functions including API integration
- `models.py` - Data models with MongoDB integration
- `templates/` - HTML templates (embedded in templates.py)
- `static/` - CSS and JavaScript files
- `config.py` - Application configuration
- `Procfile` - Railway deployment configuration

## Credits

This project is an enhanced version of the Andikar AI Frontend, integrating with MongoDB storage via the Lipia backend service.
