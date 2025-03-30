"""
MongoDB connection management for Andikar AI.
"""
import os
import logging
import time
import threading
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# MongoDB configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/lipia?retryWrites=true&w=majority&appName=OldTrafford')
MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'lipia')
MONGO_TIMEOUT = int(os.environ.get('MONGO_TIMEOUT', 15))
MONGO_RETRY_DELAY = int(os.environ.get('MONGO_RETRY_DELAY', 10))
MONGO_FALLBACK_TO_MEMORY = os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() == 'true'

# MongoDB connection state
mongo_client = None
mongo_connected = False
mongo_retry_thread = None

def get_mongo_uri():
    """Get MongoDB connection URI with proper formatting."""
    mongo_uri = MONGO_URI
    
    # Ensure database name is in the URI
    if MONGO_DBNAME not in mongo_uri and '?' in mongo_uri:
        mongo_uri = mongo_uri.replace('?', f'/{MONGO_DBNAME}?')
    elif MONGO_DBNAME not in mongo_uri:
        mongo_uri = f"{mongo_uri}/{MONGO_DBNAME}"
        
    return mongo_uri

def create_mongo_client(mongo_uri):
    """Create a MongoDB client with proper timeout settings."""
    return MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=MONGO_TIMEOUT * 1000,
        connectTimeoutMS=MONGO_TIMEOUT * 1000,
        socketTimeoutMS=MONGO_TIMEOUT * 2000
    )

def test_mongo_connection(client):
    """Test MongoDB connection with a ping command."""
    try:
        db = client.get_database()
        db.command('ping')
        return True
    except Exception:
        return False

def init_mongo(app):
    """Initialize MongoDB connection."""
    global mongo_client, mongo_connected, mongo_retry_thread
    
    # Get properly formatted MongoDB URI
    mongo_uri = get_mongo_uri()
    app.config['MONGO_URI'] = mongo_uri
    
    # Log the URI (with masked password)
    masked_uri = mongo_uri.replace("Andikar_25", "***")
    app.logger.info(f"MongoDB URI: {masked_uri}")
    
    try:
        # Create MongoDB client
        mongo_client = create_mongo_client(mongo_uri)
        
        # Test connection
        if test_mongo_connection(mongo_client):
            mongo_connected = True
            app.logger.info("Successfully connected to MongoDB Atlas!")
            
            # Create indexes
            db = mongo_client.get_database()
            db.users.create_index("username", unique=True)
            db.payments.create_index("checkout_id", unique=True)
            db.transactions.create_index([("username", 1), ("timestamp", -1)])
            app.logger.info("MongoDB indexes created successfully")
        else:
            app.logger.warning("Failed to connect to MongoDB Atlas")
            mongo_connected = False
            
            if MONGO_FALLBACK_TO_MEMORY:
                app.logger.warning("Falling back to in-memory database")
            else:
                app.logger.error("MongoDB connection required but failed")
                raise ConnectionFailure("Could not connect to MongoDB Atlas")
    except Exception as e:
        app.logger.error(f"Error connecting to MongoDB: {e}")
        mongo_connected = False
        
        if MONGO_FALLBACK_TO_MEMORY:
            app.logger.warning("Falling back to in-memory database")
        else:
            raise
    
    # Start background reconnection thread if needed
    if not mongo_connected and MONGO_FALLBACK_TO_MEMORY:
        app.logger.info("Starting background MongoDB reconnection thread")
        
        if not mongo_retry_thread or not mongo_retry_thread.is_alive():
            mongo_retry_thread = threading.Thread(
                target=retry_mongo_connection,
                args=(app,),
                daemon=True
            )
            mongo_retry_thread.start()
    
    return mongo_client

def retry_mongo_connection(app):
    """Background thread to retry MongoDB connection."""
    global mongo_client, mongo_connected
    
    while not mongo_connected:
        try:
            app.logger.info(f"Attempting to reconnect to MongoDB Atlas (retrying in {MONGO_RETRY_DELAY}s)")
            
            # Get MongoDB URI
            mongo_uri = get_mongo_uri()
            
            # Close previous client if it exists
            if mongo_client:
                try:
                    mongo_client.close()
                except:
                    pass
            
            # Create new client and test connection
            mongo_client = create_mongo_client(mongo_uri)
            
            if test_mongo_connection(mongo_client):
                mongo_connected = True
                app.logger.info("Successfully reconnected to MongoDB Atlas!")
                
                # Create indexes when connected
                db = mongo_client.get_database()
                db.users.create_index("username", unique=True)
                db.payments.create_index("checkout_id", unique=True)
                db.transactions.create_index([("username", 1), ("timestamp", -1)])
                app.logger.info("MongoDB indexes created successfully")
                
                # Sync in-memory data to MongoDB
                from models import sync_memory_to_mongo
                sync_memory_to_mongo(app)
                
                # We've successfully reconnected
                break
            else:
                # Still can't connect
                app.logger.warning("MongoDB reconnection attempt failed")
                mongo_connected = False
                time.sleep(MONGO_RETRY_DELAY)
                
        except Exception as e:
            app.logger.error(f"Error in MongoDB reconnection thread: {e}")
            mongo_connected = False
            time.sleep(MONGO_RETRY_DELAY)
