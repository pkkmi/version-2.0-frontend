from flask_pymongo import PyMongo
from datetime import datetime
import logging

# MongoDB connection
mongo = PyMongo()

# Simulated database for backwards compatibility during transition
users_db = {}
transactions_db = []

def init_mongo(app):
    """Initialize MongoDB connection"""
    try:
        # Set a shorter timeout for MongoDB connections
        app.config['MONGO_OPTIONS'] = {
            'serverSelectionTimeoutMS': 5000,  # 5 seconds
            'connectTimeoutMS': 5000,
            'socketTimeoutMS': 5000
        }
        mongo.init_app(app)
        
        # Test connection immediately
        app.logger.info("Testing MongoDB connection...")
        mongo.db.command('ping')
        app.logger.info("MongoDB connection successful!")
        
        # Create indexes
        try:
            mongo.db.users.create_index("username", unique=True)
            mongo.db.payments.create_index("checkout_id", unique=True)
            mongo.db.transactions.create_index([("username", 1), ("timestamp", -1)])
            app.logger.info("MongoDB indexes created successfully")
        except Exception as e:
            app.logger.error(f"Error creating MongoDB indexes: {e}")
            # Continue even if indexes fail - they're not critical for startup
    except Exception as e:
        app.logger.error(f"MongoDB connection error: {e}")
        app.logger.warning("Starting with in-memory database only!")
    
    return mongo

# Fallback functions that work with or without MongoDB
def get_user(username):
    """Get user by username"""
    try:
        # Try MongoDB first
        if mongo.db:
            user = mongo.db.users.find_one({"username": username})
            if user:
                return user
    except Exception as e:
        logging.error(f"MongoDB error in get_user: {e}")
    
    # Fallback to in-memory
    if username in users_db:
        return {
            "username": username,
            "password": users_db[username].get("password"),
            "words_remaining": 0,
            "phone_number": "0712345678",
            "plan": users_db[username].get("plan", "Free"),
            "payment_status": users_db[username].get("payment_status", "Pending"),
            "api_keys": users_db[username].get("api_keys", {})
        }
    return None

def create_user(username, pin, phone_number):
    """Create a new user"""
    user = {
        "username": username,
        "pin": pin,
        "words_remaining": 0,
        "phone_number": phone_number,
        "created_at": datetime.now(),
        "plan": "Free",
        "payment_status": "Pending",
        "api_keys": {
            "gpt_zero": "",
            "originality": ""
        }
    }
    
    try:
        if mongo.db:
            return mongo.db.users.insert_one(user)
    except Exception as e:
        logging.error(f"MongoDB error in create_user: {e}")
    
    # Fallback to in-memory
    users_db[username] = {
        "password": pin,
        "plan": "Free",
        "joined_date": datetime.now().strftime('%Y-%m-%d'),
        "words_used": 0,
        "payment_status": "Pending",
        "api_keys": {
            "gpt_zero": "",
            "originality": ""
        }
    }
    return True

def update_user(username, update_data):
    """Update user info"""
    try:
        if mongo.db:
            return mongo.db.users.update_one(
                {"username": username}, 
                {"$set": update_data}
            )
    except Exception as e:
        logging.error(f"MongoDB error in update_user: {e}")
    
    # Fallback to in-memory
    if username in users_db:
        for key, value in update_data.items():
            if key == "words_remaining":
                # Special handling for words_remaining
                users_db[username]["words_used"] = value
            else:
                users_db[username][key] = value
    return True

def update_word_count(username, words_to_add):
    """Update user word count"""
    try:
        if mongo.db:
            result = mongo.db.users.update_one(
                {"username": username},
                {"$inc": {"words_remaining": words_to_add}}
            )
            
            # Return the updated count
            user = get_user(username)
            return user.get("words_remaining", 0) if user else 0
    except Exception as e:
        logging.error(f"MongoDB error in update_word_count: {e}")
    
    # Fallback to in-memory
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        users_db[username]["words_remaining"] = current_words + words_to_add
        return current_words + words_to_add
    return 0

def consume_words(username, words_to_use):
    """Consume words from user's account"""
    try:
        if mongo.db:
            user = get_user(username)
            if not user:
                return False, 0
            
            current_words = user.get("words_remaining", 0)
            
            if current_words < words_to_use:
                return False, current_words
            
            update_user(username, {"words_remaining": current_words - words_to_use})
            return True, current_words - words_to_use
    except Exception as e:
        logging.error(f"MongoDB error in consume_words: {e}")
    
    # Fallback to in-memory
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        if current_words < words_to_use:
            return False, current_words
        users_db[username]["words_remaining"] = current_words - words_to_use
        return True, current_words - words_to_use
    return False, 0

def user_exists(username):
    """Check if user exists"""
    try:
        if mongo.db:
            return mongo.db.users.count_documents({"username": username}) > 0
    except Exception as e:
        logging.error(f"MongoDB error in user_exists: {e}")
    
    # Fallback to in-memory
    return username in users_db

# Payment models
def record_payment(username, amount, subscription_type, status='pending', reference='N/A', checkout_id='N/A'):
    """Record a payment attempt"""
    payment = {
        "username": username,
        "amount": amount,
        "reference": reference,
        "checkout_id": checkout_id,
        "subscription_type": subscription_type,
        "timestamp": datetime.now(),
        "status": status
    }
    
    try:
        if mongo.db:
            return mongo.db.payments.insert_one(payment)
    except Exception as e:
        logging.error(f"MongoDB error in record_payment: {e}")
    
    # Fallback to in-memory (store in transactions_db)
    transactions_db.append({
        'transaction_id': checkout_id,
        'user_id': username,
        'phone_number': "0712345678",
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': status
    })
    return True

def get_payment(checkout_id):
    """Get payment by checkout ID"""
    try:
        if mongo.db:
            return mongo.db.payments.find_one({"checkout_id": checkout_id})
    except Exception as e:
        logging.error(f"MongoDB error in get_payment: {e}")
    
    # Fallback to in-memory
    for t in transactions_db:
        if t.get('transaction_id') == checkout_id:
            return {
                "username": t.get('user_id'),
                "amount": t.get('amount'),
                "reference": "N/A",
                "checkout_id": checkout_id,
                "timestamp": datetime.now(),
                "status": t.get('status')
            }
    return None

def update_payment_status(checkout_id, status, reference=None):
    """Update payment status"""
    try:
        if mongo.db:
            update_data = {"status": status}
            if reference:
                update_data["reference"] = reference
            
            return mongo.db.payments.update_one(
                {"checkout_id": checkout_id},
                {"$set": update_data}
            )
    except Exception as e:
        logging.error(f"MongoDB error in update_payment_status: {e}")
    
    # Fallback to in-memory
    for t in transactions_db:
        if t.get('transaction_id') == checkout_id:
            t['status'] = status
            return True
    return False

def get_user_payments(username):
    """Get all payments for a user"""
    try:
        if mongo.db:
            return list(mongo.db.payments.find({"username": username}).sort("timestamp", -1))
    except Exception as e:
        logging.error(f"MongoDB error in get_user_payments: {e}")
    
    # Fallback to in-memory
    return [t for t in transactions_db if t.get('user_id') == username]

# Transaction models
def save_transaction(transaction_id, data):
    """Save transaction data"""
    try:
        if mongo.db:
            data["_id"] = transaction_id
            return mongo.db.transactions.insert_one(data)
    except Exception as e:
        logging.error(f"MongoDB error in save_transaction: {e}")
    
    # Fallback to in-memory (reuse payments data structure)
    transactions_db.append({
        'transaction_id': transaction_id,
        'user_id': data.get('username'),
        'phone_number': data.get('phone'),
        'amount': data.get('amount'),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': data.get('status')
    })
    return True

def get_transaction(transaction_id):
    """Get transaction by ID"""
    try:
        if mongo.db:
            return mongo.db.transactions.find_one({"_id": transaction_id})
    except Exception as e:
        logging.error(f"MongoDB error in get_transaction: {e}")
    
    # Fallback to in-memory
    for t in transactions_db:
        if t.get('transaction_id') == transaction_id:
            return {
                "username": t.get('user_id'),
                "amount": t.get('amount'),
                "checkout_id": transaction_id,
                "phone": t.get('phone_number'),
                "timestamp": datetime.now(),
                "status": t.get('status')
            }
    return None

def update_transaction_status(transaction_id, status, reference=None):
    """Update transaction status"""
    try:
        if mongo.db:
            update_data = {"status": status}
            if reference:
                update_data["reference"] = reference
            
            return mongo.db.transactions.update_one(
                {"_id": transaction_id},
                {"$set": update_data}
            )
    except Exception as e:
        logging.error(f"MongoDB error in update_transaction_status: {e}")
    
    # Fallback to in-memory
    for t in transactions_db:
        if t.get('transaction_id') == transaction_id:
            t['status'] = status
            return True
    return False
