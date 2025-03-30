# Andikar AI - Version 2.0 Frontend

Version 2.0 frontend of Andikar AI Flask frontend application for humanizing AI-generated text with payment processing.

## Current Setup

This version uses in-memory storage only (MongoDB is disabled) to ensure reliable operation. Key features include:

- **In-Memory Data Storage**: Fast and reliable storage without external dependencies
- **Manual Payment Processing**: Simple payment system that works without external APIs
- **Word Credits System**: Track and manage word usage with a credit-based system
- **RESTful API Endpoints**: API endpoints for external integration

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
HUMANIZER_API_URL=https://web-production-3db6c.up.railway.app
ADMIN_API_URL=https://railway-test-api-production.up.railway.app
LIPIA_API_URL=https://lipia-api.kreativelabske.com/api
LIPIA_API_KEY=7c8a3202ae14857e71e3a9db78cf62139772cae6
PAYMENT_URL=https://lipia-online.vercel.app/link/andikartill
```

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

4. Run the application:
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
2. **models.py**: Data storage and access functions
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

## Demo Account

A demo account is available for testing:

- **Username**: demo
- **Password**: demo

This account has the Basic plan with 1,375 remaining words.

## Troubleshooting

If you encounter any issues:

1. **Application not starting**: Check the logs for error messages
2. **Payment not processing**: Try the manual verification option
3. **Word count not updating**: Restart the application

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License.
