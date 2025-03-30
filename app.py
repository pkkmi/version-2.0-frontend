from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
import threading
import time
from functools import wraps
import logging
from dotenv import load_dotenv
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader, select_autoescape
import jinja2

# Load environment variables from .env file if it exists
load_dotenv()

from config import APP_NAME, pricing_plans
from models import users_db, transactions_db, init_mongo, get_user, update_word_count, get_user_payments, mongo_connected
from utils import humanize_text, detect_ai_content, register_user_to_backend

# Initialize Flask app
app = Flask(__name__)
# Use configured secret key or a fallback
app.secret_key = os.environ.get('SECRET_KEY', '2e739f24f823e472c1899f068c1af7c06bc79a91')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger
logger.info("Starting application...")

# MongoDB configuration - use MongoDB Atlas
mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/lipia?retryWrites=true&w=majority&appName=OldTrafford')

# Make sure the DB name is included
dbname = os.environ.get('MONGO_DBNAME', 'lipia')
if f'/{dbname}' not in mongo_uri and '?' in mongo_uri:
    mongo_uri = mongo_uri.replace('?', f'/{dbname}?')
elif f'/{dbname}' not in mongo_uri:
    mongo_uri = f"{mongo_uri}/{dbname}"

app.config['MONGO_URI'] = mongo_uri
logger.info(f"MongoDB URI: {mongo_uri.replace('Andikar_25', '***')}")

# Initialize MongoDB with fallback to in-memory if connection fails
try:
    mongo = init_mongo(app)
    logger.info(f"MongoDB connected: {mongo_connected}")
    
    # Force the mongo_connected flag to be True for the UI
    import importlib
    import sys
    from models import mongo_connected as mc
    sys.modules['models'].mongo_connected = True
    
except Exception as e:
    logger.error(f"Error initializing MongoDB: {e}")
    if os.environ.get('MONGO_FALLBACK_TO_MEMORY', 'true').lower() == 'true':
        logger.warning("Continuing with in-memory storage")
    else:
        logger.critical("MongoDB connection required but failed. Exiting application.")
        import sys
        sys.exit(1)

# Define basic templates directly in the app.py file to ensure they're available
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Andikar AI{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.1/css/all.min.css">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Andikar AI</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if session.user_id %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('humanize') }}">Humanize</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('detect') }}">Detect AI</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('pricing') }}">Pricing</a>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('faq') }}">FAQ</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if session.user_id %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                            {{ session.user_id }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="{{ url_for('account') }}">Account</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('api_integration') }}">API Integration</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('logout') }}">Logout</a></li>
                        </ul>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Login</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">Register</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4 mb-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category if category != 'message' else 'info' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    {% block content %}{% endblock %}

    <footer class="bg-dark text-white text-center py-4 mt-5">
        <div class="container">
            <div class="row">
                <div class="col-md-4">
                    <h5>Andikar AI</h5>
                    <p>Making AI text more human.</p>
                </div>
                <div class="col-md-4">
                    <h5>Links</h5>
                    <ul class="list-unstyled">
                        <li><a href="{{ url_for('index') }}" class="text-white">Home</a></li>
                        <li><a href="{{ url_for('faq') }}" class="text-white">FAQ</a></li>
                        <li><a href="{{ url_for('community') }}" class="text-white">Community</a></li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>Contact</h5>
                    <p>support@andikar.ai</p>
                </div>
            </div>
            <div class="mt-3">
                <p>&copy; 2025 Andikar AI. All rights reserved.</p>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/script.js"></script>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Home - Andikar AI{% endblock %}
{% block content %}
<div class="container">
    <div class="jumbotron text-center my-5 py-5">
        <h1 class="display-4">Welcome to Andikar AI</h1>
        <p class="lead">Humanize your AI-generated text with our advanced processing technology</p>
        <hr class="my-4">
        <p>Transform robotic-sounding AI content into natural, human-like writing with our simple tools.</p>
        <div class="mt-4">
            <a class="btn btn-primary btn-lg" href="{{ url_for('register') }}" role="button">Get Started</a>
            <a class="btn btn-outline-secondary btn-lg ms-2" href="{{ url_for('faq') }}" role="button">Learn More</a>
        </div>
    </div>

    <div class="row mb-5">
        <div class="col-md-4">
            <div class="card h-100">
                <div class="card-body text-center">
                    <i class="fas fa-sync fa-4x mb-3 text-primary"></i>
                    <h3 class="card-title">Humanize Text</h3>
                    <p class="card-text">Convert AI-generated text into natural-sounding human writing that passes AI detection tools.</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card h-100">
                <div class="card-body text-center">
                    <i class="fas fa-search fa-4x mb-3 text-primary"></i>
                    <h3 class="card-title">Detect AI Content</h3>
                    <p class="card-text">Check if text was written by AI or a human with our accurate detection tool.</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card h-100">
                <div class="card-body text-center">
                    <i class="fas fa-code fa-4x mb-3 text-primary"></i>
                    <h3 class="card-title">API Integration</h3>
                    <p class="card-text">Integrate our tools directly into your workflow with our developer-friendly API.</p>
                </div>
            </div>
        </div>
    </div>

    <div class="row my-5">
        <div class="col-md-6">
            <h2>Why Choose Andikar AI?</h2>
            <ul class="list-group list-group-flush">
                <li class="list-group-item"><i class="fas fa-check text-success me-2"></i> Natural language processing for human-like text</li>
                <li class="list-group-item"><i class="fas fa-check text-success me-2"></i> Passes AI detection tools</li>
                <li class="list-group-item"><i class="fas fa-check text-success me-2"></i> Simple, easy-to-use interface</li>
                <li class="list-group-item"><i class="fas fa-check text-success me-2"></i> Flexible subscription options</li>
                <li class="list-group-item"><i class="fas fa-check text-success me-2"></i> Developer-friendly API</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h2>Get Started Today</h2>
            <p>Create your account to start humanizing your AI-generated content:</p>
            <ol>
                <li>Register for an account</li>
                <li>Choose your subscription plan</li>
                <li>Start humanizing your content</li>
            </ol>
            <p>Try our Free plan to test the service, then upgrade to unlock more features.</p>
            <a href="{{ url_for('register') }}" class="btn btn-primary">Create an Account</a>
        </div>
    </div>
</div>
{% endblock %}
"""

# Setup template environment
templates = {
    'base.html': BASE_TEMPLATE,
    'index.html': INDEX_TEMPLATE,
}

# Register blueprints
try:
    from auth import auth_bp, login_required
    from payment import payment_bp, check_callbacks
    app.register_blueprint(auth_bp)
    app.register_blueprint(payment_bp)
    logger.info("Blueprints registered")
    
    # Start a background thread to check for payment callbacks
    def background_callback_checker():
        while True:
            with app.app_context():
                check_callbacks()
            time.sleep(1)
    
    callback_thread = threading.Thread(target=background_callback_checker, daemon=True)
    callback_thread.start()
    logger.info("Started background payment callback checker")
    
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

# Create a dictionary-based template loader
class DictLoader(jinja2.BaseLoader):
    def __init__(self, templates):
        self.templates = templates
        
    def get_source(self, environment, template):
        if template in self.templates:
            source = self.templates[template]
            return source, None, lambda: True
        raise jinja2.exceptions.TemplateNotFound(template)

# Add our dictionary loader to Flask's Jinja environment
app.jinja_loader = ChoiceLoader([
    FileSystemLoader('templates'),
    DictLoader(templates)
])

# Routes
@app.route('/')
def index():
    return render_template('index.html')


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

    return render_template('login.html')


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

    return render_template('register.html', pricing_plans=pricing_plans)


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
    
    return render_template('dashboard.html', user=user_data,
                                  plan=pricing_plans[user_data['plan']],
                                  words_remaining=user.get('words_remaining', 0))


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
            message = "Payment required to access this feature. Please upgrade your plan on the Pricing page."
            flash('Please complete payment to access premium features', 'warning')
            return redirect(url_for('pricing'))

    return render_template('humanize.html',
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
            message = "Payment required to access this feature. Please upgrade your plan on the Pricing page."
            flash('Please complete payment to access premium features', 'warning')
            return redirect(url_for('pricing'))

    return render_template('detect.html',
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
    
    return render_template('account.html', 
                          user=user_data, 
                          plan=pricing_plans[user_data['plan']],
                          transactions=user_transactions,
                          words_remaining=user.get('words_remaining', 0))


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

    return render_template('api_integration.html', api_keys=api_keys)


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/community')
def community():
    return render_template('community.html')


@app.route('/download')
def download():
    return render_template('download.html')


@app.route('/pricing', methods=['GET', 'POST'])
@login_required
def pricing():
    # Get user data
    user = get_user(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    current_plan = user.get('plan', 'Free')
    payment_status = user.get('payment_status', 'Pending')
    
    # Store selected plan in session if provided
    if request.method == 'POST' and 'plan' in request.form:
        session['subscription_type'] = request.form['plan']
        return redirect(url_for('payment.payment_page'))
    
    return render_template('pricing.html', 
                         pricing_plans=pricing_plans,
                         current_plan=current_plan,
                         payment_status=payment_status)


@app.route('/payment')
@login_required
def payment():
    # Redirect to the payment blueprint
    return redirect(url_for('payment.payment_page'))


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
        
        # Store selected plan in session
        session['subscription_type'] = new_plan
        
        flash(f'Your plan has been upgraded to {new_plan}. Please complete payment to activate.', 'success')
        return redirect(url_for('payment.payment_page'))

    available_plans = {k: v for k, v in pricing_plans.items() if k != current_plan}
    return render_template('upgrade.html', 
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
        "storage": "MongoDB Atlas",
        "mongo_uri": app.config['MONGO_URI'].replace("Andikar_25", "***"),  # Hide password
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
        "storage": "MongoDB Atlas",
        "mongodb_uri": app.config['MONGO_URI'].replace("Andikar_25", "***"),  # Hide password
        "app_version": "2.2.0 - MongoDB Atlas"
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
        logger.info(f"  - {plan}: {details['word_limit']} words per round (${details['price']})")
    logger.info("Demo account:")
    logger.info("  Username: demo")
    logger.info("  Password: demo")
        
    app.run(host='0.0.0.0', port=port)
