from flask import Flask, request, jsonify
from flask_cors import CORS
from models import mongo, User
from utils import humanize_text, count_words, check_api_status
from config import Config
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Setup CORS
CORS(app, supports_credentials=True)

# Setup MongoDB
mongo.init_app(app)

# Setup JWT
jwt = JWTManager(app)

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Get data from request
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not all([username, email, password]):
        return jsonify({"error": "Username, email, and password are required"}), 400
    
    # Check if username or email already exists
    if User.get_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 400
    
    if User.get_user_by_email(email):
        return jsonify({"error": "Email already registered"}), 400
    
    # Create user
    user_id = User.create_user(username, email, password)
    
    # Return success response
    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "user_id": user_id
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    # Get data from request
    username = data.get('username')
    password = data.get('password')
    
    # Validate input
    if not all([username, password]):
        return jsonify({"error": "Username and password are required"}), 400
    
    # Get user by username
    user = User.get_user_by_username(username)
    
    # Verify password
    if not user or not User.verify_password(user, password):
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Update last login
    User.update_last_login(user['_id'])
    
    # Create JWT token
    access_token = create_access_token(identity=str(user['_id']))
    
    # Return success response with token
    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "plan": user['plan']
        },
        "access_token": access_token
    }), 200

@app.route('/api/humanize', methods=['POST'])
@jwt_required()
def humanize():
    """Humanize text"""
    data = request.get_json()
    
    # Get data from request
    text = data.get('text')
    
    # Get user ID from JWT
    user_id = get_jwt_identity()
    
    # Get user
    user = User.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Count words
    words = count_words(text)
    
    # Get user's plan
    plan = user.get('plan', 'free')
    plan_details = app.config['PLANS'].get(plan)
    
    # Check word limit
    words_used = user.get('words_used', 0)
    words_limit = plan_details.get('words_limit', 500)
    
    if words_used + words > words_limit:
        return jsonify({
            "error": "Word limit exceeded",
            "words_used": words_used,
            "words_limit": words_limit,
            "words_needed": words,
            "upgrade_needed": True
        }), 403
    
    # Humanize text
    result = humanize_text(text)
    
    # Update words used if successful
    if result.get('success'):
        User.update_words_used(user_id, words)
    
    # Add user info to response
    result['user'] = {
        "words_used": words_used + words if result.get('success') else words_used,
        "words_limit": words_limit,
        "plan": plan
    }
    
    return jsonify(result)

@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get user information"""
    # Get user ID from JWT
    user_id = get_jwt_identity()
    
    # Get user
    user = User.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Return user info
    return jsonify({
        "success": True,
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "plan": user['plan'],
            "words_used": user.get('words_used', 0),
            "words_limit": app.config['PLANS'].get(user.get('plan', 'free'), {}).get('words_limit', 500)
        }
    })

@app.route('/api/status', methods=['GET'])
def status():
    """Check API status"""
    api_status = check_api_status()
    
    return jsonify({
        "status": "online",
        "humanizer_api": "online" if api_status else "offline"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)