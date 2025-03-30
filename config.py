import os

class Config:
    # MongoDB Configuration
    MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/andikar')
    
    # JWT Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Humanizer API
    HUMANIZER_API_URL = os.environ.get('HUMANIZER_API_URL', 'https://api.example.com/humanize')
    
    # User Plans
    PLANS = {
        'free': {
            'name': 'Free',
            'words_limit': 500,
            'price': 0
        },
        'basic': {
            'name': 'Basic',
            'words_limit': 1500,
            'price': 500
        },
        'premium': {
            'name': 'Premium',
            'words_limit': 8000,
            'price': 2000
        }
    }