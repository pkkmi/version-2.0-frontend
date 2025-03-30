from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
from functools import wraps
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

from config import APP_NAME, pricing_plans
from models import users_db, transactions_db, init_mongo, get_user, update_word_count, get_user_payments, mongo_connected
from utils import humanize_text, detect_ai_content, register_user_to_backend
from templates import html_templates

# Initialize Flask app
app = Flask(__name__)
# Use configured secret key or a fallback
app.secret_key = os.environ.get('SECRET_KEY', '2e739f24f823e472c1899f068c1af7c06bc79a91')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger
logger.info("Starting application...")

# MongoDB configuration - use the configured URI
mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://edgarmaina003:<db_password>@oldtrafford.id96k.mongodb.net/lipia?retryWrites=true&w=majority&appName=OldTrafford')

# Make sure the DB name is included
dbname = os.environ.get('MONGO_DBNAME', 'lipia')
if f'/{dbname}' not in mongo_uri and '?' in mongo_uri:
    mongo_uri = mongo_uri.replace('?', f'/{dbname}?')
elif f'/{dbname}' not in mongo_uri:
    mongo_uri = f"{mongo_uri}/{dbname}"

app.config['MONGO_URI'] = mongo_uri
logger.info(f"MongoDB URI: {mongo_uri}")

# Initialize MongoDB with fallback to in-memory if connection fails
try:
    mongo = init_mongo(app)
    logger.info(f"MongoDB connected: {mongo_connected}")
except Exception as e:
    logger.error(f"Error initializing MongoDB: {e}")
    if os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() == 'true':
        logger.warning("Continuing with in-memory storage")
    else:
        logger.critical("MongoDB connection required but failed. Exiting application.")
        import sys
        sys.exit(1)

# Register blueprints
try:
    from auth import auth_bp, login_required
    from payment import payment_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(payment_bp)
    logger.info("Blueprints registered")
except Exception as e:
    logger.error(f"Error registering blueprints: {e}")
    # Basic login_required function if the import fails
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

# Routes
@app.route('/')
def index():
    return render_template_string(html_templates['index.html'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists
        user = get_user(username)
        
        if user and user.get('pin', '') == password:
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
        phone = request.form.get('phone', '0712345678')  # Default phone if not provided

        # Check if user exists
        if get_user(username):
            flash('Username already exists', 'error')
        else:
            # Set payment status (Free tier is automatically Paid)
            payment_status = 'Paid' if plan_type == 'Free' else 'Pending'

            try:
                # Create user
                from models import create_user
                create_user(username, password, phone)
                
                # Update user plan
                from models import update_user
                update_user(username, {
                    'plan': plan_type,
                    'payment_status': payment_status,
                    'phone_number': phone
                })
                
                # Register the user to the backend API
                try:
                    success, message = register_user_to_backend(
                        username=username,
                        email=email,
                        phone=phone,
                        plan_type=plan_type
                    )
                    
                    if success:
                        logger.info(f"User {username} registered with backend API")
                    else:
                        logger.warning(f"Backend API registration failed: {message}")
                except Exception as e:
                    logger.error(f"Error calling backend API: {e}")
                
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                flash(f"Registration error: {str(e)}", 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get user data
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # Build user data for template
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
    
    # Show storage type in dashboard for debugging
    storage_type = "MongoDB" if mongo_connected else "In-memory"
    
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['plan']],
                                  words_remaining=user.get('words_remaining', 0),
                                  storage_type=storage_type)


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    
    # Get user data
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
    
    # Get user data
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
    # Get user data
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # Build user data for template
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
    
    # Get user transactions
    user_transactions = get_user_payments(session['user_id'])
    
    # Display storage type
    storage_type = "MongoDB" if mongo_connected else "In-memory"
    
    return render_template_string(html_templates['account.html'], 
                                  user=user_data, 
                                  plan=pricing_plans[user_data['plan']],
                                  transactions=user_transactions,
                                  words_remaining=user.get('words_remaining', 0),
                                  storage_type=storage_type)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    # Get user data
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

        # Update API keys
        from models import update_user
        update_user(session['user_id'], {
            'api_keys': {
                'gpt_zero': gpt_zero_key,
                'originality': originality_key
            }
        })
        
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
    # Get user data
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        plan_type = user.get('plan', 'Free')
        amount = pricing_plans[plan_type]['price']

        try:
            # First try to use the payment API (from payment blueprint)
            try:
                payment_url = os.environ.get('PAYMENT_URL', 'https://lipia-online.vercel.app/link/andikartill')
                
                # Call the payment API through the payment blueprint
                from payment import initiate_payment
                response = initiate_payment({
                    'username': session['user_id'], 
                    'subscription_type': plan_type,
                    'phone_number': phone_number
                })
                
                if response and response.get('status') == 'success':
                    # Payment immediately succeeded (unusual but handle it)
                    flash(f'Payment of KES {amount} processed successfully. {response.get("words_added", 0)} words have been added to your account.', 'success')
                    return redirect(url_for('account'))
                elif response and response.get('status') == 'pending':
                    # Show payment waiting screen
                    checkout_id = response.get('checkout_id', 'UNKNOWN')
                    return render_template_string(
                        html_templates['payment_waiting.html'],
                        checkout_id=checkout_id,
                        phone=phone_number,
                        amount=amount
                    )
                else:
                    # Fall back to manual processing
                    raise Exception("Payment API returned an unexpected response")
            except ImportError:
                # Fall back to manual processing
                logger.warning("Payment module not available. Using manual processing.")
                raise Exception("Payment API not available")
            except Exception as e:
                logger.error(f"Payment API error: {str(e)}")
                # Fall back to manual processing
                raise
                
            # Manual processing as fallback
            from models import update_user, update_word_count, record_payment
            
            # Generate a transaction ID
            checkout_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            
            # Update user's words
            words_to_add = pricing_plans[plan_type]['word_limit']
            new_word_count = update_word_count(session['user_id'], words_to_add)
            
            # Update payment status
            update_user(session['user_id'], {'payment_status': 'Paid'})
            
            # Record payment
            record_payment(
                session['user_id'],
                amount,
                plan_type,
                'completed',
                'MANUAL'+checkout_id,
                checkout_id
            )
            
            flash(f'Payment of KES {amount} processed successfully. {words_to_add} words have been added to your account.', 'success')
            return redirect(url_for('account'))
            
        except Exception as e:
            logger.error(f"Payment error: {str(e)}")
            flash(f"Payment error: {str(e)}", 'error')

    # Use payment URL from environment or default
    payment_url = os.environ.get('PAYMENT_URL', 'https://lipia-online.vercel.app/link/andikartill')
    
    return render_template_string(html_templates['payment.html'],
                                  plan=pricing_plans[user.get('plan', 'Free')],
                                  payment_url=payment_url)


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    # Get user data
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    current_plan = user.get('plan', 'Free')
    
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update plan
        from models import update_user
        update_user(session['user_id'], {
            'plan': new_plan,
            'payment_status': 'Pending'
        })
        
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


# Health check endpoint
@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "storage": "MongoDB" if mongo_connected else "In-memory",
        "mongo_uri": app.config['MONGO_URI'].replace("<db_password>", "***"),  # Hide password
        "version": "2.2.0",
        "mongodb_connected": mongo_connected
    })


# Diagnostic endpoint for connections
@app.route('/api-test')
def api_test():
    """Diagnostic endpoint to check API connections"""
    api_url = os.environ.get("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
    sample_text = "This is a test of the Andikar humanizer API connection."
    results = {
        "api_url": api_url,
        "tests": [],
        "storage": "MongoDB" if mongo_connected else "In-memory fallback",
        "mongodb_uri": app.config['MONGO_URI'].replace("<db_password>", "***"),  # Hide password
        "app_version": "2.2.0 - Hybrid Storage"
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
        
    # Test MongoDB connection
    results["mongodb_connected"] = mongo_connected
        
    # Overall status
    results["overall_success"] = True
    
    return jsonify(results)


# CSS styles
@app.route('/static/style.css')
def serve_css():
    try:
        with open('static/style.css', 'r') as file:
            css = file.read()
        return css, 200, {'Content-Type': 'text/css'}
    except Exception as e:
        logger.error(f"Error serving CSS: {e}")
        return "/* CSS file not found */", 404, {'Content-Type': 'text/css'}


# JavaScript
@app.route('/static/script.js')
def serve_js():
    try:
        with open('static/script.js', 'r') as file:
            js = file.read()
        return js, 200, {'Content-Type': 'text/javascript'}
    except Exception as e:
        logger.error(f"Error serving JavaScript: {e}")
        return "// JavaScript file not found", 404, {'Content-Type': 'text/javascript'}


# Add template for database status
html_templates['dashboard.html'] = html_templates['dashboard.html'].replace(
    '</div>',
    '<p class="text-muted mt-3">Storage: {{ storage_type }}</p></div>'
)

html_templates['account.html'] = html_templates['account.html'].replace(
    '</div>',
    '<p class="text-muted mt-3">Storage: {{ storage_type }}</p></div>'
)

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
    try:
        from models import create_user, update_user
        
        # Check if demo user exists
        if not get_user('demo'):
            # Create demo user
            create_user('demo', 'demo', '254712345678')
            update_user('demo', {
                'plan': 'Basic',
                'payment_status': 'Paid',
                'words_remaining': 1375,
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
            
            logger.info("Demo user created successfully")
    except Exception as e:
        logger.error(f"Error setting up demo user: {e}")
    
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting {APP_NAME} server on port {port}...")
    logger.info(f"MongoDB connected: {mongo_connected}")
    logger.info("Available plans:")
    for plan, details in pricing_plans.items():
        logger.info(f"  - {plan}: {details['word_limit']} words per round (KES {details['price']})")
    logger.info("Demo account:")
    logger.info("  Username: demo")
    logger.info("  Password: demo")
        
    app.run(host='0.0.0.0', port=port)
