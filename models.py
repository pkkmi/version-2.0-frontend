"""
Database models for Andikar Frontend using MongoDB
"""
import os
import datetime
from pymongo import MongoClient

# MongoDB Connection
def get_db():
    """
    Returns a connection to the MongoDB database
    """
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/lipia')
    client = MongoClient(mongo_url)
    db_name = os.environ.get('MONGO_DB_NAME', 'lipia')
    return client[db_name]

# Initialize in-memory data (will be migrated to MongoDB)
users_db = {}
transactions_db = []

# MongoDB User operations
def get_user(username):
    """
    Get user data from MongoDB
    """
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

def get_all_users():
    """
    Get all users from MongoDB
    """
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

def create_user(username, password, plan_type, email=None, phone=None):
    """
    Create a new user in MongoDB
    """
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
    
    try:
        result = db.users.insert_one(user_data)
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def update_user(username, data):
    """
    Update user data in MongoDB
    """
    db = get_db()
    try:
        db.users.update_one({'username': username}, {'$set': data})
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False

def user_exists(username):
    """
    Check if a user exists in MongoDB
    """
    db = get_db()
    return db.users.count_documents({'username': username}) > 0

def get_user_transactions(username):
    """
    Get all transactions for a user from MongoDB
    """
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

def consume_words(username, words_to_use):
    """
    Consume words from a user's account
    """
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

def update_api_keys(username, gpt_zero_key=None, originality_key=None):
    """
    Update API keys for a user
    """
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

# Synchronize in-memory data with MongoDB
def sync_users_with_mongodb():
    """
    Synchronize in-memory users_db with MongoDB on application startup
    """
    global users_db
    users_db = get_all_users()

def sync_transactions_with_mongodb(username=None):
    """
    Synchronize in-memory transactions_db with MongoDB on application startup
    """
    global transactions_db
    
    db = get_db()
    if username:
        # Get transactions for a specific user
        transactions_db = get_user_transactions(username)
    else:
        # Get all transactions
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
