# Andikar AI - Version 2.0 Frontend

Version 2.0 frontend of Andikar AI Flask frontend application for humanizing AI-generated text with MongoDB persistence and payment processing.

## Architecture

This application uses a hybrid storage approach:

- **Primary Storage**: MongoDB for persistent data storage
- **Fallback Storage**: In-memory backup when MongoDB is unavailable
- **Data Synchronization**: Automatic syncing from in-memory to MongoDB when connection is established
- **Background Reconnection**: Continuous attempts to reconnect to MongoDB

## Key Features

- **MongoDB Integration**: Persistent storage using MongoDB
- **Payment Processing**: Integration with Lipia payment API with fallback mechanisms
- **Word Credits System**: Track and manage word usage with a credit-based system
- **Resilient Operation**: Application works even when MongoDB is temporarily unavailable
- **Real-time Status**: Dashboard shows current storage type (MongoDB or In-memory)

## MongoDB Configuration

This application supports a robust MongoDB connection with fallback to in-memory storage:

- **Connection Timeouts**: Short timeouts prevent application hangs (3-5 seconds)
- **Authentication Support**: Uses MongoDB authentication with username/password
- **Automatic Reconnection**: Background thread attempts reconnection every 10 seconds
- **Index Creation**: Creates necessary indexes when connection is established
- **Data Synchronization**: In-memory data is synced to MongoDB when reconnected
- **Status Indication**: Dashboard displays current storage type

## Payment System

The application uses Lipia for payment processing. The payment URL is:

```
https://lipia-online.vercel.app/link/andikartill
```

The API key is:

```
7c8a3202ae14857e71e3a9db78cf62139772cae6
```

## Environment Variables

The application uses the following environment variables (create a `.env` file with these values):

```
# Flask app settings
SECRET_KEY=2e739f24f823e472c1899f068c1af7c06bc79a91
PORT=8080

# API endpoints
HUMANIZER_API_URL=https://web-production-3db6c.up.railway.app
ADMIN_API_URL=https://railway-test-api-production.up.railway.app

# MongoDB connection
MONGO_URI=mongodb://mongo:tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@metro.proxy.rlwy.net:52335/lipia
MONGO_DBNAME=lipia
MONGO_RETRY_DELAY=10
MONGO_TIMEOUT=3
MONGO_TEST_ON_STARTUP=true
MONGO_FALLBACK_TO_MEMORY=true

# Payment API
LIPIA_API_URL=https://lipia-api.kreativelabske.com/api
LIPIA_API_KEY=7c8a3202ae14857e71e3a9db78cf62139772cae6
PAYMENT_URL=https://lipia-online.vercel.app/link/andikartill
```

## MongoDB Collections

The application uses the following MongoDB collections:

- **users**: User information and subscription details
- **payments**: Payment records and transaction history
- **transactions**: Detailed transaction processing data

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pkkmi/version-2.0-frontend.git
cd version-2.0-frontend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with the environment variables shown above

5. Run the application:
```bash
python app.py
```

6. For production use with Gunicorn:
```bash
gunicorn -c gunicorn_config.py app:app
```

## Deployment on Railway

This application is configured for deployment on Railway. To deploy:

1. Connect your GitHub repository to Railway
2. Set up the required environment variables in Railway
3. Railway will automatically detect the Procfile and deploy the application

## API Endpoints

The application provides the following API endpoints:

### Authentication

- `POST /api/register`: Register a new user
- `POST /api/login`: Log in a user
- `POST /api/logout`: Log out the current user
- `GET /api/user`: Get current user data
- `POST /api/user/update`: Update user data
- `POST /api/user/consume-words`: Consume words from user's account

### Payment Processing

- `POST /payment/initiate`: Initiate a payment
- `POST /payment/callback`: Handle payment callback from payment provider
- `GET /payment/check/<checkout_id>`: Check payment status

## Diagnostics

- `/health`: Simple health check endpoint (shows MongoDB connection status)
- `/api-test`: Diagnostic endpoint for API connections

## Subscription Plans

The application offers the following subscription plans:

- **Free**: 500 words per round (KES 0)
- **Basic**: 1,500 words per round (KES 500)
- **Premium**: 8,000 words per round (KES 2,000)

## Demo Account

A demo account is available for testing:

- **Username**: demo
- **Password**: demo

This account has the Basic plan with 1,375 remaining words.

## Troubleshooting

### MongoDB Connection Issues

If MongoDB connection fails:

1. Check that your MongoDB credentials are correct in the `.env` file
2. Make sure the MongoDB URI format includes the database name: `mongodb://user:pass@host:port/lipia`
3. Verify network connectivity to the MongoDB server
4. Check MongoDB logs for authentication failures
5. The application will automatically fall back to in-memory storage if enabled

### MongoDB Status Monitoring

You can monitor the MongoDB connection status in two ways:

1. Check the application logs for MongoDB connection messages
2. Visit the `/health` endpoint to see the current MongoDB connection status
3. Look at the dashboard page where it shows "Storage: MongoDB" or "Storage: In-memory"

### Payment Issues

If payment processing fails:

1. Check the Lipia API key in the environment variables
2. Verify the payment URL is correct
3. Check network connectivity to the payment API
4. Look for error messages in the application logs
5. The application will automatically fall back to manual payment processing

## Security Notes

- The SECRET_KEY is used for Flask session encryption - use a unique value in production
- MongoDB credentials should be kept secure and not exposed in public repositories
- Payment API keys should be treated as sensitive information

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License.
