from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
from functools import wraps

from config import APP_NAME, pricing_plans
from models import (users_db, transactions_db, sync_users_with_mongodb, 
                   sync_transactions_with_mongodb, user_exists, get_user, 
                   create_user, update_user, consume_words, update_api_keys)
from utils import humanize_text, detect_ai_content, register_user_to_backend
from templates import html_templates

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)))

# API URL for backend services
LIPIA_API_URL = os.environ.get('LIPIA_API_URL', 'http://localhost:5001/api')
LIPIA_API_KEY = os.environ.get('LIPIA_API_KEY', '7c8a3202ae14857e71e3a9db78cf62139772cae6')

# Sync with MongoDB on startup
sync_users_with_mongodb()
sync_transactions_with_mongodb()

# Login decorator
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
        
        # Try to get user from MongoDB
        user_data = get_user(username)
        
        if user_data and user_data.get('password') == password:
            session['user_id'] = username
            flash('Login successful!', 'success')
            
            # Sync transactions for this user
            sync_transactions_with_mongodb(username)
            
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

        if user_exists(username):
            flash('Username already exists', 'error')
        else:
            # Create user in MongoDB
            created = create_user(
                username=username,
                password=password,
                plan_type=plan_type,
                email=email,
                phone=phone
            )
            
            if created:
                # Sync with MongoDB after creating user
                sync_users_with_mongodb()
                
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
            else:
                flash('Registration failed. Please try again.', 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get latest user data from MongoDB
    user_data = get_user(session['user_id'])
    
    if not user_data:
        # If user not found in MongoDB but exists in session, something is wrong
        session.pop('user_id', None)
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Update in-memory users_db for compatibility
    users_db[session['user_id']] = user_data
    
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['plan']])


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    
    # Get latest user data
    user_data = get_user(session['user_id'])
    payment_required = user_data['payment_status'] == 'Pending' and user_data['plan'] != 'Free'

    if request.method == 'POST':
        original_text = request.form['original_text']
        user_type = user_data['plan']

        # Only process if payment not required or on Free plan
        if not payment_required:
            # Check if user has enough words
            words_count = len(original_text.split())
            
            if words_count <= user_data['words_remaining']:
                humanized_text, message = humanize_text(original_text, user_type)

                # Consume words using MongoDB
                success = consume_words(session['user_id'], words_count)
                
                if success:
                    # Update in-memory users_db
                    users_db[session['user_id']]['words_remaining'] -= words_count
                else:
                    message = "Error updating word count. Please try again."
            else:
                message = f"You need {words_count} words but only have {user_data['words_remaining']} remaining. Please upgrade your plan."
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['humanize.html'],
                                  message=message,
                                  humanized_text=humanized_text,
                                  payment_required=payment_required,
                                  word_limit=pricing_plans[user_data['plan']]['word_limit'],
                                  words_remaining=user_data['words_remaining'])


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    # Get latest user data
    user_data = get_user(session['user_id'])
    payment_required = user_data['payment_status'] == 'Pending' and user_data['plan'] != 'Free'

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
    # Get latest user data
    user_data = get_user(session['user_id'])
    
    # Sync transactions with MongoDB for this user
    sync_transactions_with_mongodb(session['user_id'])
    
    # Filter transactions for this user
    user_transactions = [t for t in transactions_db if t['user_id'] == session['user_id']]
    
    return render_template_string(html_templates['account.html'], user=user_data, plan=pricing_plans[user_data['plan']],
                                  transactions=user_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    if request.method == 'POST':
        gpt_zero_key = request.form.get('gpt_zero_key', '')
        originality_key = request.form.get('originality_key', '')

        # Update API keys in MongoDB
        success = update_api_keys(
            username=session['user_id'],
            gpt_zero_key=gpt_zero_key,
            originality_key=originality_key
        )
        
        if success:
            # Update in-memory user data
            users_db[session['user_id']]['api_keys'] = {
                'gpt_zero': gpt_zero_key,
                'originality': originality_key
            }
            
            flash('API keys updated successfully!', 'success')
        else:
            flash('Failed to update API keys. Please try again.', 'error')
            
        return redirect(url_for('api_integration'))

    # Get latest user data
    user_data = get_user(session['user_id'])
    
    return render_template_string(html_templates['api_integration.html'],
                                  api_keys=user_data['api_keys'])


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
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Get latest user data
        user_data = get_user(session['user_id'])
        amount = pricing_plans[user_data['plan']]['price']

        # Call Lipia Backend API to process payment
        try:
            payment_data = {
                'username': session['user_id'],
                'amount': amount,
                'subscription_type': user_data['plan'].lower(),
                'phone_number': phone_number
            }
            
            headers = {
                'X-API-Key': LIPIA_API_KEY,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{LIPIA_API_URL}/payments", 
                json=payment_data,
                headers=headers
            )
            
            if response.status_code == 200:
                payment_result = response.json()
                
                # Update user payment status
                update_user(
                    username=session['user_id'],
                    data={'payment_status': 'Paid'}
                )
                
                # Sync with MongoDB
                sync_users_with_mongodb()
                sync_transactions_with_mongodb(session['user_id'])
                
                flash(f"Payment of KES {amount} successful! Reference: {payment_result.get('reference')}", 'success')
                return redirect(url_for('account'))
            else:
                flash(f"Payment failed: {response.text}", 'error')
        except Exception as e:
            flash(f"Error processing payment: {str(e)}", 'error')

    # Get latest user data
    user_data = get_user(session['user_id'])
    
    return render_template_string(html_templates['payment.html'],
                                  plan=pricing_plans[user_data['plan']])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update user plan in MongoDB
        update_user(
            username=session['user_id'],
            data={
                'plan': new_plan,
                'payment_status': 'Pending'
            }
        )
        
        # Sync with MongoDB
        sync_users_with_mongodb()
        
        flash(f'Your plan has been upgraded to {new_plan}. Please make payment to activate.', 'success')
        return redirect(url_for('payment'))

    # Get latest user data
    user_data = get_user(session['user_id'])
    current_plan = user_data['plan']
    
    available_plans = {k: v for k, v in pricing_plans.items() if k != current_plan}
    return render_template_string(html_templates['upgrade.html'], current_plan=pricing_plans[current_plan],
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
        
    # Test 4: Check the Lipia API
    try:
        response = requests.get(f"{LIPIA_API_URL}/", timeout=5)
        results["tests"].append({
            "name": "Lipia API root endpoint",
            "success": response.status_code == 200,
            "status": response.status_code,
            "content_type": response.headers.get('content-type', 'Unknown')
        })
    except Exception as e:
        results["tests"].append({
            "name": "Lipia API root endpoint",
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


if __name__ == '__main__':
    # Create demo account if it doesn't exist already
    if not user_exists('demo'):
        create_user(
            username='demo',
            password='demo',
            plan_type='Basic',
            email='demo@example.com',
            phone='0712345678'
        )
        
        # Update demo account to have some words and paid status
        update_user(
            username='demo',
            data={
                'words_remaining': 125,
                'payment_status': 'Paid'
            }
        )
    
    # Sync with MongoDB
    sync_users_with_mongodb()
    sync_transactions_with_mongodb()

    port = int(os.environ.get('PORT', 5000))
    print(f"Starting {APP_NAME} server on port {port}...")
    print("Available plans:")
    for plan, details in pricing_plans.items():
        print(f"  - {plan}: {details['word_limit']} words per round (KES {details['price']})")
    print("\nDemo account:")
    print("  Username: demo")
    print("  Password: demo")
    print(f"\nHumanizer API URL: {os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')}")
    print(f"Lipia API URL: {LIPIA_API_URL}")
    
    app.run(host='0.0.0.0', port=port)
