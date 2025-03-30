from flask_pymongo import PyMongo
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure, AutoReconnect
from pymongo import MongoClient
from datetime import datetime
import logging
import time
import threading
import os

# MongoDB connection
mongo = PyMongo()
mongo_connected = False
mongo_client = None
mongo_retry_thread = None

# Fallback in-memory database (only used when MongoDB is unavailable)
users_db = {}
transactions_db = []

def retry_mongo_connection(app):
    """Background thread to retry MongoDB connection"""
    global mongo_connected, mongo_client
    
    retry_delay = int(os.environ.get('MONGO_RETRY_DELAY', 10))
    
    while not mongo_connected:
        try:
            app.logger.info("Attempting to reconnect to MongoDB...")
            
            # Get connection URIs
            primary_uri = app.config.get('MONGO_URI')
            fallback_uri = os.environ.get('MONGO_EXTERNAL_URI')
            timeout = int(os.environ.get('MONGO_TIMEOUT', 15))
            
            # Try both internal and external URIs
            for uri_name, uri in [("Internal", primary_uri), ("External", fallback_uri)]:
                if not uri:
                    continue
                    
                app.logger.info(f"Trying {uri_name} MongoDB connection...")
                
                # Create MongoDB connection options
                mongo_options = {
                    'serverSelectionTimeoutMS': timeout * 1000,
                    'connectTimeoutMS': timeout * 1000,
                    'socketTimeoutMS': timeout * 2000
                }
                
                # Close previous client if it exists
                if mongo_client:
                    try:
                        mongo_client.close()
                    except:
                        pass
                
                # Try to connect with these settings
                try:
                    # Create a new client with proper timeouts
                    mongo_client = MongoClient(
                        uri,
                        **mongo_options
                    )
                    
                    # Test connection with ping
                    db = mongo_client.get_database()
                    db.command('ping')
                    
                    mongo_connected = True
                    app.logger.info(f"Successfully connected to MongoDB using {uri_name} connection!")
                    
                    # Create indexes when connected
                    try:
                        db.users.create_index("username", unique=True)
                        db.payments.create_index("checkout_id", unique=True)
                        db.transactions.create_index([("username", 1), ("timestamp", -1)])
                        app.logger.info("MongoDB indexes created successfully")
                    except Exception as e:
                        app.logger.error(f"Error creating MongoDB indexes: {e}")
                        
                    # Sync in-memory data to MongoDB
                    sync_memory_to_mongo(app)
                    
                    # We've successfully connected, no need to try the fallback
                    break
                    
                except Exception as e:
                    app.logger.warning(f"MongoDB {uri_name} connection failed: {str(e)}")
                    mongo_connected = False
            
            # If we're still not connected after trying both URIs, wait and retry
            if not mongo_connected:
                app.logger.warning(f"All MongoDB connection attempts failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                # We're connected, break out of the retry loop
                break
                
        except Exception as e:
            app.logger.error(f"Unexpected error in MongoDB reconnection thread: {str(e)}")
            time.sleep(retry_delay)

def sync_memory_to_mongo(app):
    """Sync in-memory database to MongoDB when connection is restored"""
    global mongo_client
    
    if not mongo_client or not mongo_connected:
        app.logger.error("Cannot sync to MongoDB: No client available or not connected")
        return
        
    try:
        db = mongo_client.get_database()
        
        # Sync users
        for username, user_data in users_db.items():
            try:
                # Check if user exists in MongoDB
                if db.users.count_documents({"username": username}) == 0:
                    # Create user in MongoDB
                    mongo_user = {
                        "username": username,
                        "pin": user_data.get("password"),
                        "words_remaining": user_data.get("words_remaining", 0),
                        "phone_number": user_data.get("phone_number", "0712345678"),
                        "created_at": datetime.now(),
                        "plan": user_data.get("plan", "Free"),
                        "payment_status": user_data.get("payment_status", "Pending"),
                        "api_keys": user_data.get("api_keys", {})
                    }
                    db.users.insert_one(mongo_user)
                    app.logger.info(f"Synced user {username} to MongoDB")
                else:
                    # Update user in MongoDB
                    db.users.update_one(
                        {"username": username},
                        {"$set": {
                            "words_remaining": user_data.get("words_remaining", 0),
                            "plan": user_data.get("plan", "Free"),
                            "payment_status": user_data.get("payment_status", "Pending"),
                            "api_keys": user_data.get("api_keys", {})
                        }}
                    )
                    app.logger.info(f"Updated user {username} in MongoDB")
            except Exception as e:
                app.logger.error(f"Error syncing user {username} to MongoDB: {e}")
                
        # Sync transactions
        for transaction in transactions_db:
            try:
                # Check if transaction exists in MongoDB
                transaction_id = transaction.get('transaction_id')
                if db.transactions.count_documents({"_id": transaction_id}) == 0:
                    # Create transaction in MongoDB
                    mongo_transaction = {
                        "_id": transaction_id,
                        "username": transaction.get('user_id'),
                        "amount": transaction.get('amount'),
                        "phone": transaction.get('phone_number'),
                        "subscription_type": transaction.get('subscription_type', "unknown"),
                        "timestamp": datetime.now(),
                        "status": transaction.get('status'),
                        "reference": transaction.get('reference', 'N/A')
                    }
                    db.transactions.insert_one(mongo_transaction)
                    app.logger.info(f"Synced transaction {transaction_id} to MongoDB")
                    
                    # Also record as payment
                    db.payments.insert_one({
                        "username": transaction.get('user_id'),
                        "amount": transaction.get('amount'),
                        "reference": transaction.get('reference', 'N/A'),
                        "checkout_id": transaction_id,
                        "subscription_type": transaction.get('subscription_type', "unknown"),
                        "timestamp": datetime.now(),
                        "status": transaction.get('status')
                    })
            except Exception as e:
                app.logger.error(f"Error syncing transaction {transaction.get('transaction_id')} to MongoDB: {e}")
                
        app.logger.info("Memory-to-MongoDB sync completed")
    except Exception as e:
        app.logger.error(f"Error in sync_memory_to_mongo: {e}")
        mongo_connected = False

def init_mongo(app):
    """Initialize MongoDB connection with retry logic"""
    global mongo_connected, mongo_retry_thread, mongo_client
    
    # Make sure we have MongoDB URIs - prefer environment variables over app config
    primary_uri = os.environ.get('MONGO_URI', app.config.get('MONGO_URI'))
    fallback_uri = os.environ.get('MONGO_EXTERNAL_URI')
    timeout = int(os.environ.get('MONGO_TIMEOUT', 15))
    dbname = os.environ.get('MONGO_DBNAME', 'lipia')
    
    # Ensure the URIs have authSource=admin and the database name
    for uri_name, uri in [("Primary", primary_uri), ("Fallback", fallback_uri)]:
        if not uri:
            continue
            
        # Make sure we have the database name in the URI
        if f'/{dbname}' not in uri:
            if '?' in uri:
                uri = uri.replace('?', f'/{dbname}?')
            else:
                uri = f"{uri}/{dbname}"
        
        # Make sure we have authSource=admin
        if 'authSource=' not in uri:
            if '?' in uri:
                uri = f"{uri}&authSource=admin"
            else:
                uri = f"{uri}?authSource=admin"
                
        # Update the URIs
        if uri_name == "Primary":
            primary_uri = uri
        else:
            fallback_uri = uri
    
    # Update environment variables and app config with fixed URIs
    os.environ['MONGO_URI'] = primary_uri
    os.environ['MONGO_EXTERNAL_URI'] = fallback_uri if fallback_uri else ""
    app.config['MONGO_URI'] = primary_uri
    
    app.logger.info(f"MongoDB Primary URI: {primary_uri.replace(':tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@', ':***@')}")
    if fallback_uri:
        app.logger.info(f"MongoDB Fallback URI: {fallback_uri.replace(':tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@', ':***@')}")
    
    # Set MongoDB connection options for Flask-PyMongo
    app.config['MONGO_OPTIONS'] = {
        'serverSelectionTimeoutMS': timeout * 1000,
        'connectTimeoutMS': timeout * 1000,
        'socketTimeoutMS': timeout * 2000
    }
    
    # Try direct connections to both URIs in order
    try:
        for uri_name, uri in [("Primary", primary_uri), ("Fallback", fallback_uri)]:
            if not uri:
                continue
                
            app.logger.info(f"Testing direct connection to {uri_name} MongoDB URI...")
            
            # Create MongoDB connection options
            mongo_options = {
                'serverSelectionTimeoutMS': timeout * 1000,
                'connectTimeoutMS': timeout * 1000,
                'socketTimeoutMS': timeout * 2000
            }
            
            try:
                # Create a direct connection with timeout
                client = MongoClient(
                    uri,
                    **mongo_options
                )
                
                # Test connection with ping
                db = client.get_database()
                db.command('ping')
                
                # Store the client for reuse
                mongo_client = client
                mongo_connected = True
                
                app.logger.info(f"MongoDB {uri_name} connection test successful!")
                
                # Create indexes
                try:
                    db.users.create_index("username", unique=True)
                    db.payments.create_index("checkout_id", unique=True)
                    db.transactions.create_index([("username", 1), ("timestamp", -1)])
                    app.logger.info("MongoDB indexes created successfully")
                except Exception as e:
                    app.logger.error(f"Error creating MongoDB indexes: {e}")
                
                # We've successfully connected, no need to try the fallback
                break
                
            except Exception as e:
                app.logger.warning(f"MongoDB {uri_name} direct connection test failed: {str(e)}")
                mongo_connected = False
                
        # If no direct connection worked, log warning and use in-memory
        if not mongo_connected:
            app.logger.warning("All MongoDB connection attempts failed")
            if os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() == 'true':
                app.logger.warning("Starting with in-memory database as fallback")
            else:
                app.logger.critical("MongoDB connection required but failed. Application may not function correctly.")
            
    except Exception as e:
        app.logger.error(f"Unexpected error initializing MongoDB: {e}")
        mongo_connected = False
        if os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() != 'true':
            raise
    
    # Initialize Flask-PyMongo with the primary URI
    # This is used by some Flask extensions, but we'll use our direct client for actual operations
    mongo.init_app(app)
    
    # Start background thread to retry connection if not connected
    if not mongo_connected and os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() == 'true':
        app.logger.info("Will attempt to reconnect to MongoDB in background")
        
        if not mongo_retry_thread or not mongo_retry_thread.is_alive():
            mongo_retry_thread = threading.Thread(
                target=retry_mongo_connection, 
                args=(app,),
                daemon=True
            )
            mongo_retry_thread.start()
    
    return mongo

# User models
def get_user(username):
    """Get user by username"""
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            user = db.users.find_one({"username": username})
            if user:
                return user
        except Exception as e:
            logging.error(f"MongoDB error in get_user: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
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
    global mongo_connected, mongo_client
    
    # Create user in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            mongo_user = {
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
            db.users.insert_one(mongo_user)
        except Exception as e:
            logging.error(f"MongoDB error in create_user: {e}")
            mongo_connected = False
    
    # Always create in in-memory database as fallback
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
    global mongo_connected, mongo_client
    
    # Update in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            db.users.update_one(
                {"username": username},
                {"$set": update_data}
            )
        except Exception as e:
            logging.error(f"MongoDB error in update_user: {e}")
            mongo_connected = False
    
    # Always update in-memory database
    if username in users_db:
        for key, value in update_data.items():
            if key == "words_remaining":
                users_db[username]["words_remaining"] = value
            elif key == "api_keys":
                users_db[username]["api_keys"] = value
            else:
                users_db[username][key] = value
    return True

def update_word_count(username, words_to_add):
    """Update user word count"""
    global mongo_connected, mongo_client
    
    # Update in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            db.users.update_one(
                {"username": username},
                {"$inc": {"words_remaining": words_to_add}}
            )
            # Get updated count from MongoDB
            user = db.users.find_one({"username": username})
            if user:
                # Also update in-memory database
                if username in users_db:
                    users_db[username]["words_remaining"] = user.get("words_remaining", 0)
                return user.get("words_remaining", 0)
        except Exception as e:
            logging.error(f"MongoDB error in update_word_count: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        users_db[username]["words_remaining"] = current_words + words_to_add
        return current_words + words_to_add
    return 0

def consume_words(username, words_to_use):
    """Consume words from user's account"""
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            user = db.users.find_one({"username": username})
            if user:
                current_words = user.get("words_remaining", 0)
                
                if current_words < words_to_use:
                    return False, current_words
                
                # Update in MongoDB
                db.users.update_one(
                    {"username": username},
                    {"$inc": {"words_remaining": -words_to_use}}
                )
                
                # Also update in-memory database
                if username in users_db:
                    users_db[username]["words_remaining"] = current_words - words_to_use
                    
                return True, current_words - words_to_use
        except Exception as e:
            logging.error(f"MongoDB error in consume_words: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
    if username in users_db:
        current_words = users_db[username].get("words_remaining", 0)
        if current_words < words_to_use:
            return False, current_words
        users_db[username]["words_remaining"] = current_words - words_to_use
        return True, current_words - words_to_use
    return False, 0

def user_exists(username):
    """Check if user exists"""
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            return db.users.count_documents({"username": username}) > 0
        except Exception as e:
            logging.error(f"MongoDB error in user_exists: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
    return username in users_db

# Payment models
def record_payment(username, amount, subscription_type, status='pending', reference='N/A', checkout_id='N/A'):
    """Record a payment attempt"""
    global mongo_connected, mongo_client
    
    payment = {
        "username": username,
        "amount": amount,
        "reference": reference,
        "checkout_id": checkout_id,
        "subscription_type": subscription_type,
        "timestamp": datetime.now(),
        "status": status
    }
    
    # Record in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            db.payments.insert_one(payment)
        except Exception as e:
            logging.error(f"MongoDB error in record_payment: {e}")
            mongo_connected = False
    
    # Always record in in-memory database
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
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            payment = db.payments.find_one({"checkout_id": checkout_id})
            if payment:
                return payment
        except Exception as e:
            logging.error(f"MongoDB error in get_payment: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
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
    global mongo_connected, mongo_client
    
    # Update in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            update_data = {"status": status}
            if reference:
                update_data["reference"] = reference
            
            db.payments.update_one(
                {"checkout_id": checkout_id},
                {"$set": update_data}
            )
        except Exception as e:
            logging.error(f"MongoDB error in update_payment_status: {e}")
            mongo_connected = False
    
    # Always update in-memory database
    for t in transactions_db:
        if t.get('transaction_id') == checkout_id:
            t['status'] = status
            if reference:
                t['reference'] = reference
            return True
    return False

def get_user_payments(username):
    """Get all payments for a user"""
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            payments = list(db.payments.find({"username": username}).sort("timestamp", -1))
            if payments:
                return payments
        except Exception as e:
            logging.error(f"MongoDB error in get_user_payments: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
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

# Transaction models
def save_transaction(transaction_id, data):
    """Save transaction data"""
    global mongo_connected, mongo_client
    
    # Save in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            mongo_data = data.copy()
            mongo_data["_id"] = transaction_id
            db.transactions.insert_one(mongo_data)
        except Exception as e:
            logging.error(f"MongoDB error in save_transaction: {e}")
            mongo_connected = False
    
    # Always save in in-memory database
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
    global mongo_connected, mongo_client
    
    # Try MongoDB first if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            transaction = db.transactions.find_one({"_id": transaction_id})
            if transaction:
                return transaction
        except Exception as e:
            logging.error(f"MongoDB error in get_transaction: {e}")
            mongo_connected = False
    
    # Fallback to in-memory database
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
    global mongo_connected, mongo_client
    
    # Update in MongoDB if connected
    if mongo_connected and mongo_client:
        try:
            db = mongo_client.get_database()
            update_data = {"status": status}
            if reference:
                update_data["reference"] = reference
            
            db.transactions.update_one(
                {"_id": transaction_id},
                {"$set": update_data}
            )
        except Exception as e:
            logging.error(f"MongoDB error in update_transaction_status: {e}")
            mongo_connected = False
    
    # Always update in-memory database
    for t in transactions_db:
        if t.get('transaction_id') == transaction_id:
            t['status'] = status
            if reference:
                t['reference'] = reference
            return True
    return False
