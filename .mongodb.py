import os
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mongodb")

# Connection details for MongoDB Atlas
MONGO_USER = os.environ.get('MONGO_USER', 'edgarmaina003')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD', '<db_password>')
MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'lipia')

# MongoDB Atlas connection string
MONGO_URL = os.environ.get('MONGO_URI', 
                           f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@oldtrafford.id96k.mongodb.net/{MONGO_DBNAME}?retryWrites=true&w=majority&appName=OldTrafford")

# Public URL (for external access)
MONGO_PUBLIC_URL = os.environ.get('MONGO_EXTERNAL_URI', 
                                 f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@oldtrafford.id96k.mongodb.net/{MONGO_DBNAME}?retryWrites=true&w=majority&appName=OldTrafford")

# Connection flags
mongo_connected = False
client = None
db = None

def initialize_mongodb():
    """Initialize MongoDB connection using direct pymongo client"""
    global mongo_connected, client, db
    
    # First try public URL
    connection_url = MONGO_PUBLIC_URL
    
    try:
        # Log connection attempt (with masked password)
        masked_url = connection_url.replace(MONGO_PASSWORD, "****")
        logger.info(f"Attempting to connect to MongoDB: {masked_url}")
        
        # Set timeouts
        client = MongoClient(
            connection_url,
            serverSelectionTimeoutMS=3000,  # 3 seconds for server selection
            connectTimeoutMS=3000,          # 3 seconds for connection
            socketTimeoutMS=5000            # 5 seconds for socket operations
        )
        
        # Test connection
        db = client.get_database()
        db.command('ping')
        
        # If we get here, connection is successful
        mongo_connected = True
        logger.info("MongoDB connected successfully!")
        
        # Create indexes
        try:
            db.users.create_index("username", unique=True)
            db.payments.create_index("checkout_id", unique=True)
            db.transactions.create_index([("username", 1), ("timestamp", -1)])
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {e}")
            # Continue even if indexes fail
            
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
        logger.error(f"MongoDB connection failed: {e}")
        
        # Try the internal URL as a fallback
        if connection_url != MONGO_URL:
            logger.info("Trying internal MongoDB URL...")
            try:
                masked_url = MONGO_URL.replace(MONGO_PASSWORD, "****")
                logger.info(f"Attempting to connect to MongoDB: {masked_url}")
                
                client = MongoClient(
                    MONGO_URL,
                    serverSelectionTimeoutMS=3000,  # 3 seconds for server selection
                    connectTimeoutMS=3000,          # 3 seconds for connection
                    socketTimeoutMS=5000            # 5 seconds for socket operations
                )
                
                # Test connection
                db = client.get_database()
                db.command('ping')
                
                # If we get here, connection is successful
                mongo_connected = True
                logger.info("MongoDB connected successfully with internal URL!")
                
                # Create indexes
                try:
                    db.users.create_index("username", unique=True)
                    db.payments.create_index("checkout_id", unique=True)
                    db.transactions.create_index([("username", 1), ("timestamp", -1)])
                    logger.info("MongoDB indexes created successfully")
                except Exception as e:
                    logger.error(f"Error creating MongoDB indexes: {e}")
                    
                return True
                
            except Exception as e2:
                logger.error(f"Both MongoDB connection attempts failed: {e2}")
                mongo_connected = False
        else:
            mongo_connected = False
            
    except Exception as e:
        logger.error(f"Unexpected error initializing MongoDB: {e}")
        mongo_connected = False
        
    return False

# Initialize connection on module import
try:
    initialize_mongodb()
except Exception as e:
    logger.error(f"Error during initialization: {e}")
    mongo_connected = False
