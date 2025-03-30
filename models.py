from flask_pymongo import PyMongo
from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# MongoDB instance
mongo = PyMongo()

class User:
    @staticmethod
    def create_user(username, email, password, plan='free'):
        """Create a new user"""
        user = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'plan': plan,
            'words_used': 0,
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow()
        }
        
        result = mongo.db.users.insert_one(user)
        return str(result.inserted_id)
    
    @staticmethod
    def get_user_by_username(username):
        """Get user by username"""
        return mongo.db.users.find_one({'username': username})
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        return mongo.db.users.find_one({'email': email})
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    @staticmethod
    def verify_password(user, password):
        """Verify user password"""
        if not user or not user.get('password_hash'):
            return False
        return check_password_hash(user['password_hash'], password)
    
    @staticmethod
    def update_last_login(user_id):
        """Update last login timestamp"""
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'last_login': datetime.utcnow()}}
        )
    
    @staticmethod
    def update_words_used(user_id, words_count):
        """Update words used count"""
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$inc': {'words_used': words_count}}
        )
    
    @staticmethod
    def reset_words_used(user_id):
        """Reset words used count"""
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'words_used': 0}}
        )