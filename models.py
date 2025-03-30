from flask_pymongo import PyMongo
from datetime import datetime

# MongoDB connection
mongo = PyMongo()

# Simulated database for backwards compatibility during transition
users_db = {}
transactions_db = []

def init_mongo(app):
    """Initialize MongoDB connection"""
    mongo.init_app(app)
    
    # Create indexes
    try:
        mongo.db.users.create_index("username", unique=True)
        mongo.db.payments.create_index("checkout_id", unique=True)
        mongo.db.transactions.create_index([("username", 1), ("timestamp", -1)])
    except Exception as e:
        app.logger.error(f"Error creating MongoDB indexes: {e}")
    
    return mongo

# User models
def get_user(username):
    """Get user by username"""
    return mongo.db.users.find_one({"username": username})

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
    
    return mongo.db.users.insert_one(user)

def update_user(username, update_data):
    """Update user info"""
    return mongo.db.users.update_one(
        {"username": username}, 
        {"$set": update_data}
    )

def update_word_count(username, words_to_add):
    """Update user word count"""
    result = mongo.db.users.update_one(
        {"username": username},
        {"$inc": {"words_remaining": words_to_add}}
    )
    
    # Return the updated count
    user = get_user(username)
    return user.get("words_remaining", 0) if user else 0

def consume_words(username, words_to_use):
    """Consume words from user's account"""
    user = get_user(username)
    if not user:
        return False, 0
    
    current_words = user.get("words_remaining", 0)
    
    if current_words < words_to_use:
        return False, current_words
    
    update_user(username, {"words_remaining": current_words - words_to_use})
    return True, current_words - words_to_use

def user_exists(username):
    """Check if user exists"""
    return mongo.db.users.count_documents({"username": username}) > 0

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
    
    return mongo.db.payments.insert_one(payment)

def get_payment(checkout_id):
    """Get payment by checkout ID"""
    return mongo.db.payments.find_one({"checkout_id": checkout_id})

def update_payment_status(checkout_id, status, reference=None):
    """Update payment status"""
    update_data = {"status": status}
    if reference:
        update_data["reference"] = reference
    
    return mongo.db.payments.update_one(
        {"checkout_id": checkout_id},
        {"$set": update_data}
    )

def get_user_payments(username):
    """Get all payments for a user"""
    return list(mongo.db.payments.find({"username": username}).sort("timestamp", -1))

# Transaction models
def save_transaction(transaction_id, data):
    """Save transaction data"""
    data["_id"] = transaction_id
    return mongo.db.transactions.insert_one(data)

def get_transaction(transaction_id):
    """Get transaction by ID"""
    return mongo.db.transactions.find_one({"_id": transaction_id})

def update_transaction_status(transaction_id, status, reference=None):
    """Update transaction status"""
    update_data = {"status": status}
    if reference:
        update_data["reference"] = reference
    
    return mongo.db.transactions.update_one(
        {"_id": transaction_id},
        {"$set": update_data}
    )
