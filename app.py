from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
from functools import wraps

from config import APP_NAME, pricing_plans
from models import users_db, transactions_db
from utils import humanize_text, detect_ai_content, register_user_to_backend
from templates import html_templates

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)))

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

        # Check if user exists (simplified for demo)
        if username in users_db and users_db[username]['password'] == password:
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
        
        # Additional fields - we'll add these for our backend registration
        email = f"{username}@example.com"  # In a real app, you'd collect this from the form
        phone = None  # In a real app, you might collect phone number

        if username in users_db:
            flash('Username already exists', 'error')
        else:
            # Set payment status (Free tier is automatically Paid)
            payment_status = 'Paid' if plan_type == 'Free' else 'Pending'

            # Save user to in-memory database
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

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    user_data = users_db[session['user_id']]
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['plan']])


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    payment_required = users_db[session['user_id']]['payment_status'] == 'Pending' and users_db[session['user_id']][
        'plan'] != 'Free'

    if request.method == 'POST':
        original_text = request.form['original_text']
        user_type = users_db[session['user_id']]['plan']

        # Only process if payment not required or on Free plan
        if not payment_required:
            humanized_text, message = humanize_text(original_text, user_type)

            # Update word usage
            users_db[session['user_id']]['words_used'] += len(original_text.split())
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['humanize.html'],
                                  message=message,
                                  humanized_text=humanized_text,
                                  payment_required=payment_required,
                                  word_limit=pricing_plans[users_db[session['user_id']]['plan']]['word_limit'])


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    payment_required = users_db[session['user_id']]['payment_status'] == 'Pending' and users_db[session['user_id']][
        'plan'] != 'Free'

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
    user_data = users_db[session['user_id']]
    user_transactions = [t for t in transactions_db if t['user_id'] == session['user_id']]
    return render_template_string(html_templates['account.html'], user=user_data, plan=pricing_plans[user_data['plan']],
                                  transactions=user_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    if request.method == 'POST':
        gpt_zero_key = request.form.get('gpt_zero_key', '')
        originality_key = request.form.get('originality_key', '')

        # Update API keys
        users_db[session['user_id']]['api_keys']['gpt_zero'] = gpt_zero_key
        users_db[session['user_id']]['api_keys']['originality'] = originality_key

        flash('API keys updated successfully!', 'success')
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                  api_keys=users_db[session['user_id']]['api_keys'])


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
        amount = pricing_plans[users_db[session['user_id']]['plan']]['price']

        # Simulate M-PESA payment
        transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

        transactions_db.append({
            'transaction_id': transaction_id,
            'user_id': session['user_id'],
            'phone_number': phone_number,
            'amount': amount,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Completed'
        })

        users_db[session['user_id']]['payment_status'] = 'Paid'
        flash(f'Payment of KES {amount} successful! Transaction ID: {transaction_id}', 'success')
        
        # When a payment is completed, update user profile in backend
        try:
            email = f"{session['user_id']}@example.com"  # This would be the real email in a production app
            register_user_to_backend(
                username=session['user_id'],
                email=email,
                phone=phone_number,
                plan_type=users_db[session['user_id']]['plan']
            )
        except Exception as e:
            print(f"Error updating user profile in backend: {e}")
            
        return redirect(url_for('account'))

    return render_template_string(html_templates['payment.html'],
                                  plan=pricing_plans[users_db[session['user_id']]['plan']])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        users_db[session['user_id']]['plan'] = new_plan
        users_db[session['user_id']]['payment_status'] = 'Pending'
        flash(f'Your plan has been upgraded to {new_plan}. Please make payment to activate.', 'success')
        return redirect(url_for('payment'))

    current_plan = users_db[session['user_id']]['plan']
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
    
    app.run(host='0.0.0.0', port=port)
