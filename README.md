# Andikar AI - Version 2.0 Frontend

Version 2.0 frontend of Andikar AI Flask frontend application for humanizing AI-generated text with MongoDB integration and payment processing.

## New Features

- **MongoDB Integration**: Replaced CSV-based storage with MongoDB
- **Payment Processing**: Integrated with Lipia payment API for subscription management
- **Word Credits System**: Track and manage word usage with a credit-based system
- **RESTful API Endpoints**: Added API endpoints for external integration

## Environment Variables

The application uses the following environment variables:

```
SECRET_KEY=your_secret_key
MONGO_URL=mongodb://username:password@host:port/database
HUMANIZER_API_URL=https://your-humanizer-api.example.com
ADMIN_API_URL=https://your-admin-api.example.com
LIPIA_API_URL=https://lipia-api.kreativelabske.com/api
LIPIA_API_KEY=your_lipia_api_key
```

## MongoDB Setup

The application uses MongoDB for data storage. Make sure you have MongoDB instance running and configure the MONGO_URL environment variable.

### MongoDB Collections

- **users**: User account information and subscription details
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

4. Set up environment variables (create .env file based on .env.example)

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

## Architecture

The application consists of the following components:

1. **app.py**: Main application file with routes and Flask setup
2. **models.py**: MongoDB models and data access functions
3. **auth.py**: Authentication routes and user management
4. **payment.py**: Payment processing and subscription management
5. **utils.py**: Utility functions for text processing and API integration
6. **templates.py**: HTML templates for the web interface
7. **config.py**: Application configuration and pricing plans

## Subscription Plans

The application offers the following subscription plans:

- **Free**: 500 words per round (KES 0)
- **Basic**: 1,500 words per round (KES 500)
- **Premium**: 8,000 words per round (KES 2,000)

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
