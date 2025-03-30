import logging
from datetime import datetime

# Simulated database - this will be our main storage
users_db = {}
transactions_db = []

# These functions work with in-memory data only, no MongoDB
def init_mongo(app):
    """Initialize storage - no MongoDB, just in-memory"""
    app.logger.info("Using in-memory storage only (MongoDB disabled)")
    return None

def get_user(username):
    """Get user by username"""
    if username in users_db:
        return {
            "username": username,
            "pin": users_db[username].get("password"),
            "words_remaining": users_db[username].get("words_remaining", 0),
            "phone_number": users_db[username].get("phone_number", "0712345678"),
            "plan": users_db[username].get("plan", "Free"),
            "payment_status": users_db[username].get("payment_status", "Pending"),
            "api_keys": users_db[username].get("api_keys", {})
        }
    return None

def create_user(username, pin, phone_number):
    """Create a new user"""
    users_db[username] = {
        "password": pin,
        "plan": "Free",
        "joined_date": datetime.now().strftime('%Y-%m-%d'),
        "words_used": 0,
        "words_remaining": 0,
        "phone_number": phone_number,
        "payment_status": "Pending",
        "api_keys": {
            "gpt_zero": "",
            "originality": ""
        }
    }
    return True

def update_user(username, update_data):
    """Update user info"""
    if username in users_db:
        for key, value in update_data.items():
            if key == "words_remaining":
                users_db[username]["words_remaining"] = value
            else:
                users_db[username][key] = value
    return True

def update_word_count(username, words_to_add):
    """Update user word count"""
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        users_db[username]["words_remaining"] = current_words + words_to_add
        return current_words + words_to_add
    return 0

def consume_words(username, words_to_use):
    """Consume words from user's account"""
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        if current_words < words_to_use:
            return False, current_words
        users_db[username]["words_remaining"] = current_words - words_to_use
        return True, current_words - words_to_use
    return False, 0

def user_exists(username):
    """Check if user exists"""
    return username in users_db

# Payment functions
def record_payment(username, amount, subscription_type, status='pending', reference='N/A', checkout_id='N/A'):
    """Record a payment attempt"""
    transactions_db.append({
        'transaction_id': checkout_id,
        'user_id': username,
        'phone_number': users_db.get(username, {}).get('phone_number', '0712345678'),
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': status,
        'reference': reference,
        'subscription_type': subscription_type
    })
    return True

def get_payment(checkout_id):
    """Get payment by checkout ID"""
    for t in transactions_db:
        if t.get('transaction_id') == checkout_id:
            return {
                "username": t.get('user_id'),
                "amount": t.get('amount'),
                "reference": t.get('reference', 'N/A'),
                "checkout_id": checkout_id,
                "timestamp": datetime.now(),
                "status": t.get('status'),
                "subscription_type": t.get('subscription_type', 'unknown')
            }
    return None

def update_payment_status(checkout_id, status, reference=None):
    """Update payment status"""
    for t in transactions_db:
        if t.get('transaction_id') == checkout_id:
            t['status'] = status
            if reference:
                t['reference'] = reference
            return True
    return False

def get_user_payments(username):
    """Get all payments for a user"""
    return [
        {
            "username": t.get('user_id'),
            "amount": t.get('amount'),
            "reference": t.get('reference', 'N/A'),
            "checkout_id": t.get('transaction_id'),
            "timestamp": datetime.now(),
            "status": t.get('status'),
            "subscription_type": t.get('subscription_type', 'unknown')
        }
        for t in transactions_db if t.get('user_id') == username
    ]

# Transaction functions
def save_transaction(transaction_id, data):
    """Save transaction data"""
    transactions_db.append({
        'transaction_id': transaction_id,
        'user_id': data.get('username'),
        'phone_number': data.get('phone'),
        'amount': data.get('amount'),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': data.get('status'),
        'reference': data.get('reference', 'N/A'),
        'subscription_type': data.get('subscription_type', 'unknown')
    })
    return True

def get_transaction(transaction_id):
    """Get transaction by ID"""
    for t in transactions_db:
        if t.get('transaction_id') == transaction_id:
            return {
                "username": t.get('user_id'),
                "amount": t.get('amount'),
                "checkout_id": transaction_id,
                "phone": t.get('phone_number'),
                "timestamp": datetime.now(),
                "status": t.get('status'),
                "reference": t.get('reference', 'N/A'),
                "subscription_type": t.get('subscription_type', 'unknown')
            }
    return None

def update_transaction_status(transaction_id, status, reference=None):
    """Update transaction status"""
    for t in transactions_db:
        if t.get('transaction_id') == transaction_id:
            t['status'] = status
            if reference:
                t['reference'] = reference
            return True
    return False
