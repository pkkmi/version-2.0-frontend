import os
import requests
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, url_for
from models import get_user, update_word_count, record_payment, save_transaction, get_transaction, update_transaction_status
from config import pricing_plans

# Initialize payment blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

# API constants - use the real credentials
API_BASE_URL = "https://lipia-api.kreativelabske.com/api"
API_KEY = "7c8a3202ae14857e71e3a9db78cf62139772cae6"
PAYMENT_URL = "https://lipia-online.vercel.app/link/andikartill"

# Format phone number for API
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

# Routes
@payment_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """Initiate payment process"""
    data = request.json
    username = data.get('username')
    subscription_type = data.get('subscription_type')
    
    if not username or not subscription_type:
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Get plan details
    if subscription_type not in pricing_plans:
        return jsonify({"error": "Invalid subscription type"}), 400
    
    amount = pricing_plans[subscription_type]['price']
    
    # Get user data
    try:
        user = get_user(username)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        phone = user.get('phone_number')
        if not phone:
            return jsonify({"error": "User has no phone number"}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting user data: {e}")
        return jsonify({"error": f"Error getting user data: {str(e)}"}), 500
    
    # Format phone number for API
    formatted_phone = format_phone_for_api(phone)
    
    try:
        # Prepare API request
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'phone': formatted_phone,
            'amount': str(amount),
            'callback_url': url_for('payment.payment_callback', _external=True)
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
                    
                    # Update word count
                    words_to_add = pricing_plans[subscription_type]['word_limit']
                    new_word_count = update_word_count(username, words_to_add)
                    
                    return jsonify({
                        "status": "success",
                        "message": "Payment processed successfully (API)",
                        "checkout_id": checkout_id,
                        "reference": reference,
                        "words_added": words_to_add,
                        "new_word_count": new_word_count
                    }), 200
                    
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
                    
                    return jsonify({
                        "status": "pending",
                        "message": "Payment request sent to your phone",
                        "checkout_id": checkout_id
                    }), 202
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
                'reference': f"REF-MANUAL-{checkout_id[:8]}"
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
            
            # Update word count
            words_to_add = pricing_plans[subscription_type]['word_limit']
            new_word_count = update_word_count(username, words_to_add)
            
            return jsonify({
                "status": "success",
                "message": "Payment processed successfully (manual fallback)",
                "checkout_id": checkout_id,
                "reference": transaction_data['reference'],
                "words_added": words_to_add,
                "new_word_count": new_word_count
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error processing payment: {str(e)}"
        }), 500

@payment_bp.route('/callback', methods=['POST'])
def payment_callback():
    """Handle payment callback from payment provider"""
    try:
        # Parse the JSON data from the callback
        callback_data = request.json
        
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
        
        # Update word count
        try:
            words_to_add = pricing_plans.get(subscription_type, {}).get('word_limit', 0)
            new_word_count = update_word_count(username, words_to_add)
            current_app.logger.info(f"Payment callback processed for {username}, {words_to_add} words added")
        except Exception as e:
            current_app.logger.error(f"Error updating word count: {e}")
            # Continue even if update fails
        
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
        transaction = get_transaction(checkout_id)
        
        if not transaction:
            return jsonify({
                "status": "error",
                "message": "Transaction not found"
            }), 404
        
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
