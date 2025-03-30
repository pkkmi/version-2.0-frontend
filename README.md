# Andikar AI - Version 2.0 Frontend

Version 2.0 frontend of Andikar AI Flask frontend application for humanizing AI-generated text with MongoDB Atlas persistence and enhanced payment processing.

## Latest Updates

### MongoDB Atlas Integration
- Now exclusively using MongoDB Atlas for persistent data storage
- Removed Railway MongoDB references
- Improved connection and authentication handling

### Revised Pricing Plans
- **Free**: 500 words per round ($0)
- **Basic**: 1,500 words per round ($20)
- **Premium**: 8,000 words per round ($30)

### Streamlined Payment System
- Single payment point under the Pricing page
- Integrated payment options directly in the pricing UI
- Clearer payment status indicators throughout the application
- Automatic processing for free plans

## Payment System Features

The application now features an enhanced payment system with:

1. **Consolidated Payment Flow**:
   - All payment options accessible from Pricing page
   - Modal-based payment interface
   - Clear status indicators

2. **Multiple Payment Options**:
   - Direct payment with phone number input
   - External payment page with verification

3. **Real-time Payment Tracking**:
   - Background callback processing
   - Live payment status updates
   - Automatic word credit updates on successful payment

4. **Improved Phone Number Handling**:
   - Automatic phone number formatting
   - Support for multiple formats (07XXXXXXXX, 254XXXXXXXXX)
   - Client-side validation

5. **Robust Error Handling**:
   - Graceful fallback to manual processing
   - Detailed error logging
   - User-friendly error messages

6. **Transaction Management**:
   - MongoDB Atlas persistence with in-memory fallback
   - Detailed transaction records
   - Payment history in user account

## Architecture

This application uses a hybrid storage approach:

- **Primary Storage**: MongoDB Atlas for persistent data storage
- **Fallback Storage**: In-memory backup when MongoDB is unavailable
- **Data Synchronization**: Automatic syncing from in-memory to MongoDB when connection is established
- **Background Reconnection**: Continuous attempts to reconnect to MongoDB

## Key Features

- **MongoDB Atlas Integration**: Persistent storage using MongoDB Atlas
- **Payment Processing**: Integration with Lipia payment API with fallback mechanisms
- **Word Credits System**: Track and manage word usage with a credit-based system
- **Resilient Operation**: Application works even when MongoDB is temporarily unavailable
- **User-Friendly Interface**: Clear payment status and subscription information

## MongoDB Configuration

This application supports a robust MongoDB Atlas connection with fallback to in-memory storage:

- **Connection Timeouts**: Short timeouts prevent application hangs (15 seconds)
- **Authentication Support**: Uses MongoDB authentication with username/password
- **Automatic Reconnection**: Background thread attempts reconnection every 10 seconds
- **Index Creation**: Creates necessary indexes when connection is established
- **Data Synchronization**: In-memory data is synced to MongoDB when reconnected

## MongoDB Connection String

The application uses the MongoDB Atlas connection string:

```
mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/lipia?retryWrites=true&w=majority&appName=OldTrafford
```

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
MONGO_URI=mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/lipia?retryWrites=true&w=majority&appName=OldTrafford
MONGO_DBNAME=lipia
MONGO_RETRY_DELAY=10
MONGO_TIMEOUT=15
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
- `POST /payment/validate-phone`: Validate phone number format
- `POST /payment/cancel/<checkout_id>`: Cancel a pending payment

## Diagnostics

- `/health`: Simple health check endpoint (shows MongoDB connection status)
- `/api-test`: Diagnostic endpoint for API connections

## Subscription Plans

The application offers the following subscription plans:

- **Free**: 500 words per round ($0)
- **Basic**: 1,500 words per round ($20)
- **Premium**: 8,000 words per round ($30)

## Demo Account

A demo account is available for testing:

- **Username**: demo
- **Password**: demo

This account has the Basic plan with 1,375 remaining words.

## Troubleshooting MongoDB Connections

If you're having issues with MongoDB connectivity:

1. **Check Connection String Format**: 
   - Verify the database name is included in the URI

2. **Check Logs for Specific Errors**:
   - "Authentication failed" - Check credentials
   - "Connection reset by peer" - Network connectivity issues
   - "Cannot connect to MongoDB" - Check MongoDB Atlas service status

3. **Verify Environment Variables**:
   - `MONGO_URI` - Connection string
   - `MONGO_TIMEOUT` - Connection timeout in seconds

4. **Check MongoDB Atlas Service**:
   - Verify MongoDB Atlas service is running
   - Check for any service outages

5. **Other MongoDB Troubleshooting**:
   - Try connecting with MongoDB Compass using the connection string
   - Run `mongosh` command with the MongoDB URL to test direct connectivity

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
