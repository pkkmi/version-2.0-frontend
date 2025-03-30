"""
Database models for Andikar Frontend using MongoDB
"""
import os
import sys
import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# MongoDB Connection with better error handling
def get_db():
    """
    Returns a connection to the MongoDB database with error handling
    """
    try:
        # Try using the Railway MongoDB URL first
        mongo_url = os.environ.get('MONGO_URL', None)
        
        # If not set, try constructing from individual parameters
        if not mongo_url and all([
            os.environ.get('MONGOUSER'),
            os.environ.get('MONGOPASSWORD'),
            os.environ.get('MONGOHOST'),
            os.environ.get('MONGOPORT')
        ]):
            user = os.environ.get('MONGOUSER')
            password = os.environ.get('MONGOPASSWORD')
            host = os.environ.get('MONGOHOST')
            port = os.environ.get('MONGOPORT')
            mongo_url = f"mongodb://{user}:{password}@{host}:{port}"
        
        # Fall back to localhost if nothing else is available
        if not mongo_url:
            mongo_url = 'mongodb://localhost:27017/lipia'
        
        print(f"Connecting to MongoDB at: {mongo_url.split('@')[-1]}")  # Log without credentials
        
        # Use a short timeout for initial connection
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        
        # Force a connection to verify it works
        client.admin.command('ping')
        
        db_name = os.environ.get('MONGO_DB_NAME', 'lipia')
        print(f"Connected to MongoDB successfully, using database: {db_name}")
        return client[db_name]
    
    except ConnectionFailure as e:
        print(f"MongoDB Connection Error: {e}", file=sys.stderr)
        # Don't fail immediately, return a dummy DB that will fail later
        # This allows the app to start even if DB is temporarily unavailable
        class DummyDB:
            def __getattr__(self, name):
                return DummyCollection()
                
        return DummyDB()
        
    except ServerSelectionTimeoutError as e:
        print(f"MongoDB Server Selection Timeout: {e}", file=sys.stderr)
        print("Check your MongoDB connection string and network connectivity", file=sys.stderr)
        # Don't fail immediately, return a dummy DB
        class DummyDB:
            def __getattr__(self, name):
                return DummyCollection()
                
        return DummyDB()
        
    except Exception as e:
        print(f"Unexpected MongoDB Error: {e}", file=sys.stderr)
        # Don't fail immediately, return a dummy DB
        class DummyDB:
            def __getattr__(self, name):
                return DummyCollection()
                
        return DummyDB()

# Dummy collection for when MongoDB is unavailable
class DummyCollection:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None
    
    def find(self, *args, **kwargs):
        return []
    
    def find_one(self, *args, **kwargs):
        return None
    
    def count_documents(self, *args, **kwargs):
        return 0

# Initialize in-memory data (will be migrated to MongoDB)
users_db = {}
transactions_db = []

# MongoDB User operations
def get_user(username):
    """
    Get user data from MongoDB
    """
    try:
        db = get_db()
        user = db.users.find_one({'username': username})
        if user:
            # Convert MongoDB _id to string for JSON serialization
            user['_id'] = str(user['_id'])
            # Map MongoDB fields to the expected frontend structure
            return {
                'username': user['username'],
                'password': user.get('pin', ''),  # Use pin as password
                'plan': user.get('plan', 'Free'),
                'joined_date': user.get('created_at', datetime.datetime.now()).strftime('%Y-%m-%d'),
                'words_used': 0,  # Default value
                'words_remaining': user.get('words_remaining', 0),
                'payment_status': user.get('payment_status', 'Pending'),
                'api_keys': {
                    'gpt_zero': user.get('gpt_zero_key', ''),
                    'originality': user.get('originality_key', '')
                }
            }
        return None
    except Exception as e:
        print(f"Error getting user data: {e}", file=sys.stderr)
        # Return fallback data
        return {
            'username': username,
            'password': '',
            'plan': 'Free',
            'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'words_used': 0,
            'words_remaining': 0,
            'payment_status': 'Pending',
            'api_keys': {
                'gpt_zero': '',
                'originality': ''
            }
        }

def get_all_users():
    """
    Get all users from MongoDB
    """
    try:
        db = get_db()
        users = {}
        for user in db.users.find():
            # Convert MongoDB _id to string for JSON serialization
            user['_id'] = str(user['_id'])
            # Map MongoDB fields to the expected frontend structure
            users[user['username']] = {
                'password': user.get('pin', ''),  # Use pin as password
                'plan': user.get('plan', 'Free'),
                'joined_date': user.get('created_at', datetime.datetime.now()).strftime('%Y-%m-%d'),
                'words_used': 0,  # Default value
                'words_remaining': user.get('words_remaining', 0),
                'payment_status': user.get('payment_status', 'Pending'),
                'api_keys': {
                    'gpt_zero': user.get('gpt_zero_key', ''),
                    'originality': user.get('originality_key', '')
                }
            }
        return users
    except Exception as e:
        print(f"Error getting all users: {e}", file=sys.stderr)
        return {}

def create_user(username, password, plan_type, email=None, phone=None):
    """
    Create a new user in MongoDB
    """
    try:
        db = get_db()
        
        # Set payment status (Free tier is automatically Paid)
        payment_status = 'Paid' if plan_type == 'Free' else 'Pending'
        
        # Determine initial word count based on plan
        initial_words = 500 if plan_type == 'Free' else 0
        
        user_data = {
            'username': username,
            'pin': password,  # Store password as pin
            'plan': plan_type,
            'created_at': datetime.datetime.now(),
            'words_remaining': initial_words,
            'payment_status': payment_status,
            'email': email,
            'phone_number': phone,
            'gpt_zero_key': '',
            'originality_key': ''
        }
        
        result = db.users.insert_one(user_data)
        return True
    except Exception as e:
        print(f"Error creating user: {e}", file=sys.stderr)
        return False

def update_user(username, data):
    """
    Update user data in MongoDB
    """
    try:
        db = get_db()
        db.users.update_one({'username': username}, {'$set': data})
        return True
    except Exception as e:
        print(f"Error updating user: {e}", file=sys.stderr)
        return False

def user_exists(username):
    """
    Check if a user exists in MongoDB
    """
    try:
        db = get_db()
        return db.users.count_documents({'username': username}) > 0
    except Exception as e:
        print(f"Error checking if user exists: {e}", file=sys.stderr)
        return False

def get_user_transactions(username):
    """
    Get all transactions for a user from MongoDB
    """
    try:
        db = get_db()
        transactions = []
        for transaction in db.payments.find({'username': username}).sort('timestamp', -1):
            # Convert MongoDB _id to string for JSON serialization
            transaction['_id'] = str(transaction['_id'])
            # Convert timestamp to string
            if 'timestamp' in transaction and isinstance(transaction['timestamp'], datetime.datetime):
                transaction['timestamp'] = transaction['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Map MongoDB fields to the expected frontend structure
            transactions.append({
                'transaction_id': transaction.get('checkout_id', 'TX' + str(transaction['_id'])[-8:]),
                'user_id': transaction['username'],
                'phone_number': transaction.get('phone', ''),
                'amount': transaction.get('amount', 0),
                'date': transaction.get('timestamp', ''),
                'status': transaction.get('status', 'Pending')
            })
        
        return transactions
    except Exception as e:
        print(f"Error getting user transactions: {e}", file=sys.stderr)
        return []

def consume_words(username, words_to_use):
    """
    Consume words from a user's account
    """
    try:
        db = get_db()
        user = db.users.find_one({'username': username})
        
        if not user:
            return False
        
        current_words = user.get('words_remaining', 0)
        
        if current_words < words_to_use:
            return False
        
        new_word_count = current_words - words_to_use
        
        db.users.update_one(
            {'username': username}, 
            {'$set': {'words_remaining': new_word_count}}
        )
        
        return True
    except Exception as e:
        print(f"Error consuming words: {e}", file=sys.stderr)
        return False

def update_api_keys(username, gpt_zero_key=None, originality_key=None):
    """
    Update API keys for a user
    """
    try:
        db = get_db()
        update_data = {}
        
        if gpt_zero_key is not None:
            update_data['gpt_zero_key'] = gpt_zero_key
        
        if originality_key is not None:
            update_data['originality_key'] = originality_key
        
        if update_data:
            db.users.update_one({'username': username}, {'$set': update_data})
            return True
        
        return False
    except Exception as e:
        print(f"Error updating API keys: {e}", file=sys.stderr)
        return False

# Synchronize in-memory data with MongoDB
def sync_users_with_mongodb():
    """
    Synchronize in-memory users_db with MongoDB on application startup
    """
    try:
        global users_db
        print("Syncing users with MongoDB...")
        users_db = get_all_users()
        print(f"Synced {len(users_db)} users from MongoDB")
    except Exception as e:
        print(f"Error syncing users with MongoDB: {e}", file=sys.stderr)

def sync_transactions_with_mongodb(username=None):
    """
    Synchronize in-memory transactions_db with MongoDB on application startup
    """
    try:
        global transactions_db
        
        db = get_db()
        if username:
            # Get transactions for a specific user
            print(f"Syncing transactions for user: {username}")
            transactions_db = get_user_transactions(username)
            print(f"Synced {len(transactions_db)} transactions for user {username}")
        else:
            # Get all transactions
            print("Syncing all transactions...")
            transactions_db = []
            for transaction in db.payments.find().sort('timestamp', -1):
                # Convert MongoDB _id to string for JSON serialization
                transaction['_id'] = str(transaction['_id'])
                # Convert timestamp to string
                if 'timestamp' in transaction and isinstance(transaction['timestamp'], datetime.datetime):
                    transaction['timestamp'] = transaction['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                
                # Map MongoDB fields to the expected frontend structure
                transactions_db.append({
                    'transaction_id': transaction.get('checkout_id', 'TX' + str(transaction['_id'])[-8:]),
                    'user_id': transaction['username'],
                    'phone_number': transaction.get('phone', ''),
                    'amount': transaction.get('amount', 0),
                    'date': transaction.get('timestamp', ''),
                    'status': transaction.get('status', 'Pending')
                })
            print(f"Synced {len(transactions_db)} total transactions")
    except Exception as e:
        print(f"Error syncing transactions with MongoDB: {e}", file=sys.stderr)
