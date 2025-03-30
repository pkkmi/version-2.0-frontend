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

## Payment System

The application uses Lipia for payment processing. The payment URL is:

```
https://lipia-online.vercel.app/link/andikartill
```

## Environment Variables

The application uses the following environment variables:

```
SECRET_KEY=2e739f24f823e472c1899f068c1af7c06bc79a91
PORT=8080
MONGO_URL=mongodb://mongo:tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@mongodb.railway.internal:27017/lipia
MONGO_PUBLIC_URL=mongodb://mongo:tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@metro.proxy.rlwy.net:52335
MONGO_INITDB_ROOT_USERNAME=mongo
MONGO_INITDB_ROOT_PASSWORD=tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg
HUMANIZER_API_URL=https://web-production-3db6c.up.railway.app
ADMIN_API_URL=https://railway-test-api-production.up.railway.app
LIPIA_API_URL=https://lipia-api.kreativelabske.com/api
LIPIA_API_KEY=7c8a3202ae14857e71e3a9db78cf62139772cae6
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
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (or create .env file)

5. Run the application:
```bash
python app.py
```

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

- `/health`: Simple health check endpoint
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

### MongoDB Issues

If MongoDB connection fails:
1. Application will automatically fall back to in-memory storage
2. A background thread will attempt to reconnect to MongoDB
3. When the connection is established, in-memory data will be synced to MongoDB
4. The dashboard will display the current storage type (MongoDB or In-memory)

### Payment Issues

If payment processing fails:
1. The application will automatically fall back to manual payment processing
2. Payments will be marked as completed and words will be added to the user's account
3. Real API integration will be attempted first before falling back to manual processing

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License.
