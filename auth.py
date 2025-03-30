from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, current_app
from functools import wraps
import re
from models import get_user, create_user, update_user, user_exists

# Initialize auth blueprint
auth_bp = Blueprint('auth', __name__)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# API login required decorator
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration"""
    data = request.json
    
    # Validate required fields
    if not all(k in data for k in ['username', 'pin', 'phone']):
        return jsonify({"error": "Missing required fields"}), 400
    
    username = data['username']
    pin = data['pin']
    phone = data['phone']
    
    # Validate PIN (must be 4 digits)
    if not (pin.isdigit() and len(pin) == 4):
        return jsonify({"error": "PIN must be 4 digits"}), 400
    
    # Validate phone number
    phone_pattern = re.compile(r'^0[7][0-9]{8}$')
    if not phone_pattern.match(phone):
        return jsonify({"error": "Phone number must be in the format 07XXXXXXXX"}), 400
    
    # Check if user already exists
    if user_exists(username):
        return jsonify({"error": "Username already exists"}), 409
    
    # Create user
    try:
        create_user(username, pin, phone)
        return jsonify({
            "status": "success",
            "message": "User registered successfully"
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login"""
    data = request.json
    
    # Validate required fields
    if not all(k in data for k in ['username', 'pin']):
        return jsonify({"error": "Missing username or PIN"}), 400
    
    username = data['username']
    pin = data['pin']
    
    # Get user
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Validate PIN
    if user.get('pin') != pin:
        return jsonify({"error": "Invalid PIN"}), 401
    
    # Set session
    session['user_id'] = username
    
    # Return user data (excluding sensitive fields)
    user_data = {
        "username": user.get('username'),
        "words_remaining": user.get('words_remaining', 0),
        "phone_number": user.get('phone_number'),
        "plan": user.get('plan', 'Free'),
        "payment_status": user.get('payment_status', 'Pending')
    }
    
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": user_data
    }), 200

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint for user logout"""
    session.pop('user_id', None)
    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), 200

@auth_bp.route('/api/user', methods=['GET'])
@api_login_required
def api_get_user():
    """API endpoint to get current user data"""
    username = session.get('user_id')
    user = get_user(username)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Return user data (excluding sensitive fields)
    user_data = {
        "username": user.get('username'),
        "words_remaining": user.get('words_remaining', 0),
        "phone_number": user.get('phone_number'),
        "plan": user.get('plan', 'Free'),
        "payment_status": user.get('payment_status', 'Pending'),
        "api_keys": user.get('api_keys', {})
    }
    
    return jsonify({
        "status": "success",
        "user": user_data
    }), 200

@auth_bp.route('/api/user/update', methods=['POST'])
@api_login_required
def api_update_user():
    """API endpoint to update user data"""
    username = session.get('user_id')
    data = request.json
    
    # Fields that can be updated
    allowed_fields = ['phone_number', 'api_keys']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400
    
    try:
        update_user(username, update_data)
        return jsonify({
            "status": "success",
            "message": "User updated successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

@auth_bp.route('/api/user/consume-words', methods=['POST'])
@api_login_required
def api_consume_words():
    """API endpoint to consume words"""
    from models import consume_words
    
    username = session.get('user_id')
    data = request.json
    
    if 'words' not in data:
        return jsonify({"error": "Missing word count"}), 400
    
    try:
        words_to_use = int(data['words'])
        if words_to_use <= 0:
            return jsonify({"error": "Word count must be positive"}), 400
    except ValueError:
        return jsonify({"error": "Invalid word count"}), 400
    
    success, remaining = consume_words(username, words_to_use)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"Used {words_to_use} words",
            "remaining": remaining
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Not enough words",
            "remaining": remaining
        }), 403
