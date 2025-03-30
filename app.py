from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
import logging
from functools import wraps
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '2e739f24f823e472c1899f068c1af7c06bc79a91')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger
logger.info("Starting minimal application...")

# Basic user database (in-memory for now)
users = {
    'demo': {
        'password': 'demo',
        'phone_number': '0712345678',
        'plan': 'Basic',
        'words_remaining': 100,
        'payment_status': 'Paid'
    }
}

# Pricing plans
pricing_plans = {
    "Free": {
        "price": 0,
        "word_limit": 500,
        "description": "Free tier with 500 words"
    },
    "Basic": {
        "price": 20,
        "word_limit": 100,
        "description": "Basic plan with 100 words"
    },
    "Premium": {
        "price": 50,
        "word_limit": 1000,
        "description": "Premium plan with 1,000 words"
    }
}

# Login required decorator
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
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
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
        phone = request.form.get('phone', '0712345678')
        
        if username in users:
            flash('Username already exists', 'error')
        else:
            # Create new user
            users[username] = {
                'password': password,
                'phone_number': phone,
                'plan': 'Free',
                'words_remaining': pricing_plans['Free']['word_limit'],
                'payment_status': 'Paid'
            }
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['user_id']
    user_data = users.get(username, {})
    
    return render_template('dashboard.html', 
                          user=user_data,
                          username=username,
                          words_remaining=user_data.get('words_remaining', 0))

@app.route('/payment')
@login_required
def payment():
    username = session['user_id']
    user_data = users.get(username, {})
    
    return render_template('payment.html',
                          user=user_data,
                          pricing_plans=pricing_plans)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    username = session['user_id']
    subscription_type = request.form.get('subscription_type')
    
    if subscription_type not in pricing_plans:
        flash('Invalid subscription type', 'error')
        return redirect(url_for('payment'))
    
    # Simulate payment processing
    plan = pricing_plans[subscription_type]
    users[username]['plan'] = subscription_type
    users[username]['words_remaining'] += plan['word_limit']
    users[username]['payment_status'] = 'Paid'
    
    flash(f'Payment successful! {plan["word_limit"]} words have been added to your account.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "minimal-1.0"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
