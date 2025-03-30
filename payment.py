# Updated payment.py with Lipia payment functionality

from flask import Blueprint, request, jsonify, current_app, url_for, render_template, flash, redirect, session
import os
import requests
import json
import uuid
import queue
import threading
import socket
import time
from datetime import datetime
from models import get_user, update_word_count, record_payment, save_transaction, get_transaction, update_transaction_status
from config import pricing_plans

# Initialize payment blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

# API constants - use the real credentials from Python script
API_BASE_URL = os.environ.get('LIPIA_API_URL', "https://lipia-api.kreativelabske.com/api")
API_KEY = os.environ.get('LIPIA_API_KEY', "7c8a3202ae14857e71e3a9db78cf62139772cae6")
PAYMENT_URL = os.environ.get('PAYMENT_URL', "https://lipia-online.vercel.app/link/andikartill")

# Global callback queue for communication between server and request handlers
CALLBACK_QUEUE = queue.Queue()
ACTIVE_TRANSACTIONS = {}

# Callback server setup
CALLBACK_HOST = "0.0.0.0"  # Listen on all interfaces
CALLBACK_PORT = int(os.environ.get('CALLBACK_PORT', 8000))
callback_server = None
callback_thread = None

# Format phone number for API (same as in Python script)
def format_phone_for_api(phone):
    """Format phone number to 07XXXXXXXX format required by API"""
    # Ensure phone is a string
    phone = str(phone)

    # Remove any spaces, quotes or special characters
    phone = ''.join(c for c in phone if c.isdigit())

    # If it starts with 254, convert to local format
    if phone.startswith('254'):
        phone = '0' + phone[3:]

    # Make sure it starts with 0
    if not phone.startswith('0'):
        phone = '0' + phone

    # Ensure it's exactly 10 digits (07XXXXXXXX)
    if len(phone) > 10:
        phone = phone[:10]
    elif len(phone) < 10:
        current_app.logger.warning(f"Phone number {phone} is shorter than expected")

    current_app.logger.debug(f"Original phone: {phone} -> Formatted for API: {phone}")
    return phone

# Import socket and HTTPServer for callback server
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    current_app.logger.error("Failed to import HTTPServer. Callbacks may not work.")

# Callback server handler
class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to use Flask logger
        if hasattr(current_app, 'logger'):
            current_app.logger.info(format % args)
        else:
            BaseHTTPRequestHandler.log_message(self, format, *args)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Lipia Callback Server')

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Parse the JSON data from the callback
            callback_data = json.loads(post_data.decode('utf-8'))
            if hasattr(current_app, 'logger'):
                current_app.logger.info(f"Received payment callback: {callback_data}")
            
            # Put in queue for processing
            CALLBACK_QUEUE.put(callback_data)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
            
        except Exception as e:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error in callback handler: {e}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

# Start callback server in a separate thread
def run_callback_server(host, port):
    try:
        server = HTTPServer((host, port), CallbackHandler)
        if hasattr(current_app, 'logger'):
            current_app.logger.info(f"Starting callback server on {host}:{port}")
        server.serve_forever()
    except Exception as e:
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error starting callback server: {e}")

# Find an available port for the callback server
def find_available_port(start_port=8000, end_port=9000):
    global CALLBACK_PORT
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in range(start_port, end_port):
        try:
            s.bind((CALLBACK_HOST, port))
            s.close()
            CALLBACK_PORT = port
            return port
        except Exception:
            continue
    s.close()
    return None

# Process callback data
def process_payment_callback(callback_data):
    """Process payment callback data"""
    try:
        checkout_id = callback_data.get('CheckoutRequestID')
        if not checkout_id:
            current_app.logger.warning("Callback missing CheckoutRequestID")
            return False

        # Look up transaction
        transaction = get_transaction(checkout_id)
        if not transaction:
            current_app.logger.warning(f"Transaction not found for checkout_id: {checkout_id}")
            return False

        # Update transaction status
        reference = callback_data.get('reference')
        update_transaction_status(checkout_id, 'completed', reference)

        # Update payment record
        username = transaction['username']
        amount = transaction['amount']
        subscription_type = transaction['subscription_type']

        # Record payment
        record_payment(
            username,
            amount,
            subscription_type,
            'completed',
            reference,
            checkout_id
        )

        # Update word count based on subscription type (same as Python script)
        words_to_add = 100 if subscription_type == 'basic' else 1000
        
        new_word_count = update_word_count(username, words_to_add)

        # Update ACTIVE_TRANSACTIONS
        ACTIVE_TRANSACTIONS[checkout_id] = 'completed'

        current_app.logger.info(f"Payment processed for user {username}, added {words_to_add} words")
        return True
    except Exception as e:
        current_app.logger.error(f"Error processing callback: {e}")
        return False

# Function to check queue for callbacks - called periodically
def check_callbacks():
    """Check for queued callbacks"""
    try:
        while not CALLBACK_QUEUE.empty():
            callback_data = CALLBACK_QUEUE.get_nowait()
            process_payment_callback(callback_data)
    except Exception as e:
        current_app.logger.error(f"Error in check_callbacks: {e}")

# Initialize callback server
def init_callback_server():
    global callback_server, callback_thread, CALLBACK_PORT
    
    # Find available port
    port = find_available_port()
    if not port:
        current_app.logger.error("Could not find available port for callback server")
        return False
    
    current_app.logger.info(f"Starting callback server on port {port}")
    
    # Start server in a thread
    callback_thread = threading.Thread(
        target=run_callback_server, 
        args=(CALLBACK_HOST, port),
        daemon=True
    )
    callback_thread.start()
    
    return True

# Routes
@payment_bp.route('/', methods=['GET'])
def payment_page():
    """Show payment page"""
    # Get user data
    username = session.get('user_id')
    if not username:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    user = get_user(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # Make sure phone number format is clean by removing any quotes
    phone_number = user.get('phone_number', '')
    if isinstance(phone_number, str):
        phone_number = phone_number.strip("'")
        user['phone_number'] = phone_number
    
    # Use subscription type from session or default to Basic
    subscription_type = session.get('subscription_type', 'Basic')
    
    return render_template('payment.html', 
                          plan=pricing_plans[subscription_type],
                          user=user)

@payment_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """Initiate payment process - Implementation directly from Python script"""
    # Check if request is from our frontend or external API
    if request.is_json:
        data = request.json
    else:
        # Handle form data
        data = {
            'username': session.get('user_id'),
            'subscription_type': request.form.get('subscription_type', 'Basic'),
            'phone_number': request.form.get('phone_number')
        }
    
    username = data.get('username')
    subscription_type = data.get('subscription_type').lower()  # Convert to lowercase to match Python script
    phone_override = data.get('phone_number')
    
    if not username or not subscription_type:
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Get plan details
    if subscription_type.capitalize() not in pricing_plans:
        return jsonify({"error": "Invalid subscription type"}), 400
    
    amount = pricing_plans[subscription_type.capitalize()]['price']
    
    # Get user data
    try:
        user = get_user(username)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Use provided phone or get from user data
        if phone_override:
            phone = phone_override
        else:
            phone = user.get('phone_number')
            
        if not phone:
            return jsonify({"error": "User has no phone number"}), 400
            
        # If phone is stored with quotes, remove them
        if isinstance(phone, str):
            phone = phone.strip("'")
    except Exception as e:
        current_app.logger.error(f"Error getting user data: {e}")
        return jsonify({"error": f"Error getting user data: {str(e)}"}), 500
    
    # Format phone number for API
    formatted_phone = format_phone_for_api(phone)
    
    try:
        # If this is the Free plan, process it immediately
        if subscription_type.capitalize() == 'Free' or amount == 0:
            # Generate a transaction ID
            checkout_id = f"FREE-{uuid.uuid4()}"
            
            # Save transaction data
            transaction_data = {
                'checkout_id': checkout_id,
                'username': username,
                'amount': 0,
                'phone': phone,
                'subscription_type': subscription_type,
                'timestamp': datetime.now(),
                'status': 'completed',
                'reference': f"FREE-PLAN-{checkout_id[:8]}"
            }
            
            save_transaction(checkout_id, transaction_data)
            
            # Record payment
            record_payment(
                username,
                0,
                subscription_type,
                'completed',
                transaction_data['reference'],
                checkout_id
            )
            
            # Update user status
            from models import update_user
            update_user(username, {'payment_status': 'Paid'})
            
            # Update word count
            words_to_add = pricing_plans[subscription_type.capitalize()]['word_limit']
            new_word_count = update_word_count(username, words_to_add)
            
            flash(f"Free plan activated! {words_to_add} words have been added to your account.", "success")
            return redirect(url_for('dashboard'))
        
        # For paid plans, proceed with payment API
        # Prepare API request
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Add callback URL to payload
        callback_url = url_for('payment.payment_callback', _external=True)
        
        payload = {
            'phone': formatted_phone,
            'amount': str(amount),
            'callback_url': callback_url
        }
        
        current_app.logger.info(f"Sending payment request with phone: {formatted_phone}, amount: {amount}")
        
        # Send payment request to API
        try:
            # Try the real API first
            response = requests.post(
                f"{API_BASE_URL}/request/stk",
                headers=headers,
                json=payload,
                timeout=15  # Wait up to 15 seconds for response
            )
            
            current_app.logger.info(f"API Response: {response.status_code} - {response.text}")
            
            # Process API response
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('message') == 'callback received successfully' and 'data' in response_data:
                    # API returned success
                    data = response_data['data']
                    checkout_id = data.get('CheckoutRequestID')
                    reference = data.get('refference')  # Note API spelling
                    
                    # Save transaction
                    transaction_data = {
                        'checkout_id': checkout_id,
                        'username': username,
                        'amount': amount,
                        'phone': phone,
                        'subscription_type': subscription_type,
                        'timestamp': datetime.now(),
                        'status': 'completed',
                        'reference': reference
                    }
                    save_transaction(checkout_id, transaction_data)
                    
                    # Record payment
                    record_payment(
                        username,
                        amount,
                        subscription_type,
                        'completed',
                        reference,
                        checkout_id
                    )
                    
                    # Update user status
                    from models import update_user
                    update_user(username, {'payment_status': 'Paid'})
                    
                    # Update word count - modified to match Python script logic
                    words_to_add = 100 if subscription_type == 'basic' else 1000
                    new_word_count = update_word_count(username, words_to_add)
                    
                    flash(f"Payment successful! {words_to_add} words have been added to your account.", "success")
                    return redirect(url_for('dashboard'))
                    
                elif 'data' in response_data and 'CheckoutRequestID' in response_data['data']:
                    # Payment initiated, waiting for callback
                    checkout_id = response_data['data']['CheckoutRequestID']
                    
                    # Save transaction
                    transaction_data = {
                        'checkout_id': checkout_id,
                        'username': username,
                        'amount': amount,
                        'phone': phone,
                        'subscription_type': subscription_type,
                        'timestamp': datetime.now(),
                        'status': 'pending'
                    }
                    save_transaction(checkout_id, transaction_data)
                    
                    # Record pending payment
                    record_payment(
                        username,
                        amount,
                        subscription_type,
                        'pending',
                        'N/A',
                        checkout_id
                    )
                    
                    # Add to ACTIVE_TRANSACTIONS
                    ACTIVE_TRANSACTIONS[checkout_id] = 'pending'
                    
                    # Redirect to payment waiting page
                    return redirect(url_for('payment.payment_waiting', 
                                          checkout_id=checkout_id, 
                                          amount=amount, 
                                          phone=formatted_phone))
                else:
                    # Error in API response
                    raise Exception(f"Unexpected API response: {response_data}")
            else:
                # API returned error status code
                raise Exception(f"API returned status code {response.status_code}: {response.text}")
                
        except Exception as e:
            current_app.logger.error(f"Error with payment API: {e}")
            current_app.logger.info("Falling back to manual payment processing")
            
            # Fall back to manual processing
            checkout_id = f"MANUAL-{uuid.uuid4()}"
            
            # Save transaction data
            transaction_data = {
                'checkout_id': checkout_id,
                'username': username,
                'amount': amount,
                'phone': phone,
                'subscription_type': subscription_type,
                'timestamp': datetime.now(),
                'status': 'completed',
                'reference': f"MANUAL-{checkout_id[:8]}"
            }
            
            save_transaction(checkout_id, transaction_data)
            
            # Record payment
            record_payment(
                username,
                amount,
                subscription_type,
                'completed',
                transaction_data['reference'],
                checkout_id
            )
            
            # Update user status
            from models import update_user
            update_user(username, {'payment_status': 'Paid'})
            
            # Update word count
            words_to_add = 100 if subscription_type == 'basic' else 1000
            new_word_count = update_word_count(username, words_to_add)
            
            flash(f"Payment processed manually. {words_to_add} words have been added to your account.", "success")
            return redirect(url_for('dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {str(e)}")
        flash(f"Error processing payment: {str(e)}", "error")
        return redirect(url_for('payment.payment_page'))

@payment_bp.route('/waiting/<checkout_id>')
def payment_waiting(checkout_id):
    """Show payment waiting screen"""
    amount = request.args.get('amount', '0')
    phone = request.args.get('phone', '')
    
    return render_template('payment_waiting.html', 
                          checkout_id=checkout_id,
                          amount=amount,
                          phone=phone)

@payment_bp.route('/callback', methods=['POST'])
def payment_callback():
    """Handle payment callback from payment provider"""
    try:
        # Parse the JSON data from the callback
        callback_data = request.json
        current_app.logger.info(f"Received payment callback: {callback_data}")
        
        # Put in queue for processing
        CALLBACK_QUEUE.put(callback_data)
        
        # Process immediately
        checkout_id = callback_data.get('CheckoutRequestID')
        if not checkout_id:
            return jsonify({"status": "error", "message": "Missing checkout ID"}), 400
        
        # Look up transaction
        try:
            transaction = get_transaction(checkout_id)
            if not transaction:
                return jsonify({"status": "error", "message": "Transaction not found"}), 404
        except Exception as e:
            current_app.logger.error(f"Error getting transaction: {e}")
            return jsonify({"status": "error", "message": f"Error retrieving transaction: {str(e)}"}), 500
        
        # Update transaction status
        reference = callback_data.get('reference')
        try:
            update_transaction_status(checkout_id, 'completed', reference)
        except Exception as e:
            current_app.logger.error(f"Error updating transaction status: {e}")
            # Continue even if update fails
        
        # Update payment record
        username = transaction['username']
        amount = transaction['amount']
        subscription_type = transaction['subscription_type']
        
        # Record payment
        try:
            record_payment(
                username,
                amount,
                subscription_type,
                'completed',
                reference,
                checkout_id
            )
        except Exception as e:
            current_app.logger.error(f"Error recording payment: {e}")
            # Continue even if record fails
        
        # Update user status
        try:
            from models import update_user
            update_user(username, {'payment_status': 'Paid'})
        except Exception as e:
            current_app.logger.error(f"Error updating user status: {e}")
            # Continue even if update fails
        
        # Update word count
        try:
            # Modified to match Python script logic
            words_to_add = 100 if subscription_type == 'basic' else 1000
            new_word_count = update_word_count(username, words_to_add)
            current_app.logger.info(f"Payment callback processed for {username}, {words_to_add} words added")
        except Exception as e:
            current_app.logger.error(f"Error updating word count: {e}")
            # Continue even if update fails
        
        # Update ACTIVE_TRANSACTIONS
        ACTIVE_TRANSACTIONS[checkout_id] = 'completed'
        
        return jsonify({
            "status": "success",
            "message": "Callback processed successfully"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment callback: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error processing callback: {str(e)}"
        }), 500

@payment_bp.route('/check/<checkout_id>', methods=['GET'])
def check_payment_status(checkout_id):
    """Check payment status"""
    try:
        # Check in-memory ACTIVE_TRANSACTIONS first for faster response
        if checkout_id in ACTIVE_TRANSACTIONS:
            status = ACTIVE_TRANSACTIONS[checkout_id]
            if status == 'completed':
                transaction = get_transaction(checkout_id)
                return jsonify({
                    "status": "success",
                    "transaction": {
                        "checkout_id": checkout_id,
                        "status": "completed",
                        "reference": transaction.get('reference', 'N/A'),
                        "amount": transaction.get('amount', 0),
                        "subscription_type": transaction.get('subscription_type', 'unknown'),
                        "timestamp": datetime.now().isoformat()
                    }
                }), 200
        
        # Fall back to database check
        transaction = get_transaction(checkout_id)
        
        if not transaction:
            return jsonify({
                "status": "error",
                "message": "Transaction not found"
            }), 404
        
        # Update ACTIVE_TRANSACTIONS for future checks
        ACTIVE_TRANSACTIONS[checkout_id] = transaction.get('status', 'unknown')
        
        return jsonify({
            "status": "success",
            "transaction": {
                "checkout_id": checkout_id,
                "status": transaction.get('status', 'unknown'),
                "reference": transaction.get('reference', 'N/A'),
                "amount": transaction.get('amount', 0),
                "subscription_type": transaction.get('subscription_type', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error checking payment status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving transaction: {str(e)}"
        }), 500

@payment_bp.route('/cancel/<checkout_id>', methods=['POST'])
def cancel_payment(checkout_id):
    """Cancel a pending payment"""
    if checkout_id in ACTIVE_TRANSACTIONS:
        ACTIVE_TRANSACTIONS[checkout_id] = 'cancelled'
    
    try:
        update_transaction_status(checkout_id, 'cancelled')
        return jsonify({"status": "success", "message": "Payment cancelled"}), 200
    except Exception as e:
        current_app.logger.error(f"Error cancelling payment: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Start the callback server when this module is imported
init_callback_server()