from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
from functools import wraps
import logging

from config import APP_NAME, pricing_plans
from models import users_db, transactions_db, init_mongo, get_user, update_word_count, get_user_payments
from utils import humanize_text, detect_ai_content, register_user_to_backend
from templates import html_templates
from auth import auth_bp, login_required
from payment import payment_bp

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)))

# Configure logging
logging.basicConfig(level=logging.INFO)

# MongoDB configuration
app.config['MONGO_URI'] = os.environ.get(
    'MONGO_URL', 
    'mongodb://mongo:tCvrFvMjzkRSNRDlWMLuDexKqVNMpgDg@mongodb.railway.internal:27017/lipia'
)

# Initialize MongoDB
mongo = init_mongo(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(payment_bp)

# Routes
@app.route('/')
def index():
    return render_template_string(html_templates['index.html'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists using MongoDB
        user = get_user(username)
        
        if user and user.get('pin') == password:
            session['user_id'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')

    return render_template_string(html_templates['login.html'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        plan_type = request.form['plan_type']
        
        # Get email and phone from the form
        email = request.form['email']
        phone = request.form.get('phone', None)  # Phone is optional

        # Use MongoDB to check if user exists
        if get_user(username):
            flash('Username already exists', 'error')
        else:
            # Set payment status (Free tier is automatically Paid)
            payment_status = 'Paid' if plan_type == 'Free' else 'Pending'

            # For backwards compatibility during transition
            users_db[username] = {
                'password': password,
                'plan': plan_type,
                'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'words_used': 0,
                'payment_status': payment_status,
                'api_keys': {
                    'gpt_zero': '',
                    'originality': ''
                }
            }
            
            try:
                # Create user in MongoDB
                from models import create_user
                create_user(username, password, phone)
                
                # Update user plan
                from models import update_user
                update_user(username, {
                    'plan': plan_type,
                    'payment_status': payment_status,
                    'api_keys': {
                        'gpt_zero': '',
                        'originality': ''
                    }
                })
                
                # Register the user to the backend API
                success, message = register_user_to_backend(
                    username=username,
                    email=email,
                    phone=phone,
                    plan_type=plan_type
                )
                
                if success:
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
                else:
                    # If backend registration fails, we'll still allow the user to proceed
                    # but inform them of the issue
                    flash(f'Local registration successful, but backend sync encountered an issue: {message}', 'warning')
                    return redirect(url_for('login'))
            except Exception as e:
                app.logger.error(f"Error creating user: {str(e)}")
                flash(f"Registration error: {str(e)}", 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # For backwards compatibility
    if session['user_id'] in users_db:
        user_data = users_db[session['user_id']]
    else:
        user_data = {
            'plan': user.get('plan', 'Free'),
            'joined_date': user.get('created_at', datetime.datetime.now()).strftime('%Y-%m-%d'),
            'words_used': 0,
            'payment_status': user.get('payment_status', 'Pending'),
            'api_keys': user.get('api_keys', {
                'gpt_zero': '',
                'originality': ''
            })
        }
        # Add to in-memory DB for compatibility
        users_db[session['user_id']] = user_data
    
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['plan']],
                                  words_remaining=user.get('words_remaining', 0))


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    payment_required = user.get('payment_status') == 'Pending' and user.get('plan') != 'Free'
    words_remaining = user.get('words_remaining', 0)

    if request.method == 'POST':
        original_text = request.form['original_text']
        user_type = user.get('plan', 'Free')

        # Only process if payment not required or on Free plan
        if not payment_required:
            # Check if user has enough words
            word_count = len(original_text.split())
            
            if word_count <= words_remaining or user_type == 'Free':
                humanized_text, message = humanize_text(original_text, user_type)

                # Update word usage
                if user_type != 'Free':
                    from models import consume_words
                    consume_words(session['user_id'], word_count)
                    user = get_user(session['user_id'])  # Refresh user data
                    words_remaining = user.get('words_remaining', 0)
            else:
                message = f"Not enough words remaining. You have {words_remaining} words left, but this text has {word_count} words."
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['humanize.html'],
                                  message=message,
                                  humanized_text=humanized_text,
                                  payment_required=payment_required,
                                  words_remaining=words_remaining,
                                  word_limit=pricing_plans[user.get('plan', 'Free')]['word_limit'])


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    payment_required = user.get('payment_status') == 'Pending' and user.get('plan') != 'Free'

    if request.method == 'POST':
        text = request.form['text']

        # Check payment status for non-free users
        if not payment_required:
            result = detect_ai_content(text)
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['detect.html'],
                                  result=result,
                                  message=message,
                                  payment_required=payment_required)


@app.route('/account')
@login_required
def account():
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # For backwards compatibility
    if session['user_id'] in users_db:
        user_data = users_db[session['user_id']]
    else:
        user_data = {
            'plan': user.get('plan', 'Free'),
            'joined_date': user.get('created_at', datetime.datetime.now()).strftime('%Y-%m-%d'),
            'words_used': 0,
            'payment_status': user.get('payment_status', 'Pending'),
            'api_keys': user.get('api_keys', {
                'gpt_zero': '',
                'originality': ''
            })
        }
    
    # Get user transactions from MongoDB
    user_transactions = get_user_payments(session['user_id'])
    
    # Convert to format expected by template
    formatted_transactions = []
    for t in user_transactions:
        formatted_transactions.append({
            'transaction_id': t.get('checkout_id', 'N/A'),
            'user_id': t.get('username'),
            'phone_number': user.get('phone_number', 'N/A'),
            'amount': t.get('amount', 0),
            'date': t.get('timestamp', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'status': t.get('status', 'Unknown')
        })
    
    # If no transactions in MongoDB, use in-memory DB for now
    if not formatted_transactions:
        formatted_transactions = [t for t in transactions_db if t['user_id'] == session['user_id']]
    
    return render_template_string(html_templates['account.html'], 
                                  user=user_data, 
                                  plan=pricing_plans[user_data['plan']],
                                  transactions=formatted_transactions,
                                  words_remaining=user.get('words_remaining', 0))


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    api_keys = user.get('api_keys', {
        'gpt_zero': '',
        'originality': ''
    })
    
    if request.method == 'POST':
        gpt_zero_key = request.form.get('gpt_zero_key', '')
        originality_key = request.form.get('originality_key', '')

        # Update API keys in MongoDB
        from models import update_user
        update_user(session['user_id'], {
            'api_keys': {
                'gpt_zero': gpt_zero_key,
                'originality': originality_key
            }
        })
        
        # For backwards compatibility
        if session['user_id'] in users_db:
            users_db[session['user_id']]['api_keys']['gpt_zero'] = gpt_zero_key
            users_db[session['user_id']]['api_keys']['originality'] = originality_key

        flash('API keys updated successfully!', 'success')
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                  api_keys=api_keys)


@app.route('/faq')
def faq():
    return render_template_string(html_templates['faq.html'])


@app.route('/community')
def community():
    return render_template_string(html_templates['community.html'])


@app.route('/download')
def download():
    return render_template_string(html_templates['download.html'])


@app.route('/pricing')
@login_required
def pricing():
    return render_template_string(html_templates['pricing.html'], pricing_plans=pricing_plans)


@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        plan_type = user.get('plan', 'Free')
        amount = pricing_plans[plan_type]['price']

        # Simulate M-PESA payment with our new payment system
        try:
            # Send request to payment API
            response = requests.post(
                url_for('payment.initiate_payment', _external=True),
                json={
                    'username': session['user_id'],
                    'subscription_type': plan_type
                },
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                # Payment was immediately successful
                result = response.json()
                flash(f"Payment of KES {amount} successful! Reference: {result.get('reference')}", 'success')
                return redirect(url_for('account'))
            elif response.status_code == 202:
                # Payment is pending, show waiting screen
                result = response.json()
                checkout_id = result.get('checkout_id')
                
                # In a real implementation, you would redirect to a waiting page
                # For now, just show a message
                flash(f"Payment request sent to your phone. Please check your phone and approve the payment.", 'info')
                
                # Store checkout_id in session for later reference
                session['active_checkout_id'] = checkout_id
                
                return render_template_string(html_templates['payment_waiting.html'],
                                            checkout_id=checkout_id,
                                            amount=amount,
                                            phone=phone_number)
            else:
                # Payment failed
                flash(f"Payment failed: {response.json().get('message', 'Unknown error')}", 'error')
        except Exception as e:
            app.logger.error(f"Payment error: {str(e)}")
            flash(f"Payment error: {str(e)}", 'error')

    return render_template_string(html_templates['payment.html'],
                                  plan=pricing_plans[user.get('plan', 'Free')])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    # Get user data from MongoDB
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    current_plan = user.get('plan', 'Free')
    
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update plan in MongoDB
        from models import update_user
        update_user(session['user_id'], {
            'plan': new_plan,
            'payment_status': 'Pending'
        })
        
        # For backwards compatibility
        if session['user_id'] in users_db:
            users_db[session['user_id']]['plan'] = new_plan
            users_db[session['user_id']]['payment_status'] = 'Pending'
        
        flash(f'Your plan has been upgraded to {new_plan}. Please make payment to activate.', 'success')
        return redirect(url_for('payment'))

    available_plans = {k: v for k, v in pricing_plans.items() if k != current_plan}
    return render_template_string(html_templates['upgrade.html'], 
                                  current_plan=pricing_plans[current_plan],
                                  available_plans=available_plans)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# Diagnostic endpoint for the API connection
@app.route('/api-test')
def api_test():
    """Diagnostic endpoint to check the humanizer API connection"""
    api_url = os.environ.get("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
    sample_text = "This is a test of the Andikar humanizer API connection."
    results = {
        "api_url": api_url,
        "tests": []
    }
    
    # Test 1: Check the root endpoint
    try:
        response = requests.get(f"{api_url}/", timeout=5)
        results["tests"].append({
            "name": "Root endpoint",
            "success": response.status_code == 200,
            "status": response.status_code,
            "content_type": response.headers.get('content-type', 'Unknown')
        })
    except Exception as e:
        results["tests"].append({
            "name": "Root endpoint",
            "success": False,
            "error": str(e)
        })
        
    # Test 2: Check the echo endpoint
    try:
        response = requests.post(f"{api_url}/echo_text", json={"input_text": sample_text}, timeout=5)
        results["tests"].append({
            "name": "Echo endpoint",
            "success": response.status_code == 200,
            "status": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text[:100]
        })
    except Exception as e:
        results["tests"].append({
            "name": "Echo endpoint",
            "success": False,
            "error": str(e)
        })
        
    # Test 3: Check the humanize endpoint
    try:
        response = requests.post(f"{api_url}/humanize_text", json={"input_text": sample_text}, timeout=15)
        results["tests"].append({
            "name": "Humanize endpoint",
            "success": response.status_code == 200,
            "status": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text[:100]
        })
    except Exception as e:
        results["tests"].append({
            "name": "Humanize endpoint",
            "success": False,
            "error": str(e)
        })
        
    # Test 4: Check the admin API registration endpoint
    admin_api_url = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
    try:
        # Just check if the endpoint is reachable, don't actually register
        response = requests.get(f"{admin_api_url}/", timeout=5)
        results["tests"].append({
            "name": "Admin API root endpoint",
            "success": response.status_code == 200,
            "status": response.status_code,
            "content_type": response.headers.get('content-type', 'Unknown')
        })
    except Exception as e:
        results["tests"].append({
            "name": "Admin API root endpoint",
            "success": False,
            "error": str(e)
        })
    
    # Test 5: MongoDB connection
    try:
        mongo_status = "Connected" if mongo.db else "Not connected"
        results["tests"].append({
            "name": "MongoDB connection",
            "success": mongo.db is not None,
            "status": mongo_status
        })
    except Exception as e:
        results["tests"].append({
            "name": "MongoDB connection",
            "success": False,
            "error": str(e)
        })
    
    # Overall status
    results["overall_success"] = all(test.get("success", False) for test in results["tests"])
    
    return jsonify(results)


# CSS styles
@app.route('/static/style.css')
def serve_css():
    with open('static/style.css', 'r') as file:
        css = file.read()
    return css, 200, {'Content-Type': 'text/css'}


# JavaScript
@app.route('/static/script.js')
def serve_js():
    with open('static/script.js', 'r') as file:
        js = file.read()
    return js, 200, {'Content-Type': 'text/javascript'}


# Add new template for payment waiting screen
html_templates['payment_waiting.html'] = """
{% extends "base.html" %}
{% block title %}Payment Processing{% endblock %}
{% block content %}
<div class="container">
    <h1>Payment Processing</h1>
    <div class="card">
        <div class="card-header">
            <h2>Payment In Progress</h2>
        </div>
        <div class="card-body">
            <p>An M-PESA payment request has been sent to your phone ({{ phone }}).</p>
            <p>Please check your phone and approve the payment of KES {{ amount }}.</p>
            <p>This page will automatically update when the payment is complete.</p>
            <p>Transaction ID: {{ checkout_id }}</p>
            <div id="payment-status">Waiting for payment...</div>
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%"></div>
            </div>
            <button class="btn btn-secondary mt-3" id="cancel-payment">Cancel Payment</button>
        </div>
    </div>
</div>

<script>
// Poll for payment status
let checkCount = 0;
const maxChecks = 120; // 2 minutes at 1-second intervals

function checkPaymentStatus() {
    fetch('/payment/check/{{ checkout_id }}')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const txn = data.transaction;
                if (txn.status === 'completed') {
                    document.getElementById('payment-status').innerHTML = 'Payment completed!';
                    window.location.href = '/account';
                    return;
                }
            }
            
            // Update waiting animation
            checkCount++;
            const dots = '.'.repeat(checkCount % 4);
            document.getElementById('payment-status').innerHTML = `Waiting for payment${dots}`;
            
            // Check if we've reached the timeout
            if (checkCount >= maxChecks) {
                document.getElementById('payment-status').innerHTML = 'Payment request timed out. Please try again.';
                return;
            }
            
            // Check again in 1 second
            setTimeout(checkPaymentStatus, 1000);
        })
        .catch(error => {
            console.error('Error checking payment status:', error);
            setTimeout(checkPaymentStatus, 1000);
        });
}

// Start checking for payment status
checkPaymentStatus();

// Handle cancel button
document.getElementById('cancel-payment').addEventListener('click', function() {
    window.location.href = '/account';
});
</script>
{% endblock %}
"""


if __name__ == '__main__':
    # Add a sample user for quick testing
    users_db['demo'] = {
        'password': 'demo',
        'plan': 'Basic',
        'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'words_used': 125,
        'payment_status': 'Paid',
        'api_keys': {
            'gpt_zero': '',
            'originality': ''
        }
    }

    # Create a sample transaction
    transactions_db.append({
        'transaction_id': 'TXND3M0123456',
        'user_id': 'demo',
        'phone_number': '254712345678',
        'amount': pricing_plans['Basic']['price'],
        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Completed'
    })
    
    # Create the demo user in MongoDB if it doesn't exist
    if not get_user('demo'):
        from models import create_user, update_user
        try:
            create_user('demo', 'demo', '254712345678')
            update_user('demo', {
                'plan': 'Basic',
                'payment_status': 'Paid',
                'words_remaining': 1375,  # Basic plan limit - words used
                'api_keys': {
                    'gpt_zero': '',
                    'originality': ''
                }
            })
            # Record a payment for the demo user
            from models import record_payment
            record_payment(
                'demo',
                pricing_plans['Basic']['price'],
                'Basic',
                'completed',
                'DEMOREF123456',
                'TXND3M0123456'
            )
        except Exception as e:
            app.logger.error(f"Error creating demo user: {str(e)}")

    port = int(os.environ.get('PORT', 5000))
    print(f"Starting {APP_NAME} server on port {port}...")
    print("Available plans:")
    for plan, details in pricing_plans.items():
        print(f"  - {plan}: {details['word_limit']} words per round (KES {details['price']})")
    print("\nDemo account:")
    print("  Username: demo")
    print("  Password: demo")
    print(f"\nHumanizer API URL: {os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')}")
    admin_api_url = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
    print(f"Admin API URL: {admin_api_url}")
    print(f"MongoDB URI: {app.config['MONGO_URI']}")
    
    app.run(host='0.0.0.0', port=port)
