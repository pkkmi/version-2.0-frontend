import os
import random
import string
import requests
import json
from datetime import datetime

# API URLs
HUMANIZER_API_URL = os.environ.get("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
ADMIN_API_URL = os.environ.get("ADMIN_API_URL", "https://web-production-a776.up.railway.app") 
AI_DETECTOR_API_URL = os.environ.get("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")
LIPIA_API_URL = os.environ.get('LIPIA_API_URL', 'http://localhost:5001/api')
LIPIA_API_KEY = os.environ.get('LIPIA_API_KEY', '7c8a3202ae14857e71e3a9db78cf62139772cae6')


def humanize_text(text, user_type="Basic"):
    """
    Call the humanizer API to transform AI text into more human-like text.
    
    Args:
        text (str): The text to humanize
        user_type (str): The user's plan type
        
    Returns:
        tuple: (humanized_text, message)
    """
    # Simulate a response for now
    try:
        # Set strength and variation based on plan
        strength = 0.5  # Default for Basic plan
        variation = 0.3
        
        if user_type == "Premium":
            strength = 0.8
            variation = 0.6
        elif user_type == "Free":
            strength = 0.3
            variation = 0.2
        
        # Check if real API is available
        try:
            payload = {"input_text": text}
            response = requests.post(f"{HUMANIZER_API_URL}/humanize_text", json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return result["result"], "Text successfully humanized!"
        except Exception as e:
            print(f"Error calling humanize API: {e}")
            # Fall back to simulated response
        
        # Simulated response
        # Apply some random variations to simulate humanization
        words = text.split()
        word_count = len(words)
        
        # Truncate if over limit based on plan
        limit = 8000 if user_type == "Premium" else 1500 if user_type == "Basic" else 500
        truncated = False
        message = "Text successfully humanized!"
        
        if word_count > limit:
            words = words[:limit]
            truncated = True
            message = f"Text was truncated to {limit} words due to your plan limit."
        
        # Simulate humanization by adding small variations
        for i in range(len(words)):
            if random.random() < 0.1 * strength:  # Change some words
                if words[i].lower() in ['very', 'extremely', 'really']:
                    words[i] = random.choice(['quite', 'rather', 'pretty', 'fairly'])
                elif words[i].lower() in ['good', 'great', 'excellent']:
                    words[i] = random.choice(['nice', 'wonderful', 'fantastic', 'superb'])
                    
        # Add some filler words occasionally
        humanized_words = []
        for word in words:
            humanized_words.append(word)
            if random.random() < 0.03 * variation:
                humanized_words.append(random.choice(['basically', 'actually', 'honestly', 'like', 'you know', 'sort of', 'kind of']))
                
        humanized_text = ' '.join(humanized_words)
        
        # Replace common AI phrases
        replacements = {
            "In conclusion": random.choice(["To sum up", "All things considered", "When all is said and done", "Looking at the big picture"]),
            "It is important to note": random.choice(["Keep in mind", "Don't forget", "Remember", "It's worth remembering"]),
            "In this essay": random.choice(["Here", "In this analysis", "In what follows", "In this discussion"]),
            "This data suggests": random.choice(["This seems to show", "This points to", "This suggests", "This hints at"]),
        }
        
        for old, new in replacements.items():
            humanized_text = humanized_text.replace(old, new)
            
        return humanized_text, message
                
    except Exception as e:
        return "", f"Error: {str(e)}"


def detect_ai_content(text):
    """
    Analyze text to determine if it's likely AI-generated.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Detection results
    """
    try:
        # Simulate detection for now
        # In a real-world scenario, you'd call a real detection API
        text_length = len(text)
        
        # Generate some random scores, but weighted based on text characteristics
        formality_score = random.randint(60, 95)  # Higher formality often indicates AI
        
        # Check for patterns indicative of AI text
        repetition_patterns = text.count("In conclusion") + text.count("It is important to note")
        repetition_score = min(100, repetition_patterns * 10 + random.randint(20, 70))
        
        # Check sentence uniformity
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / max(1, len(sentences))
        
        # AI often has very uniform sentence lengths
        sentence_lengths = [len(s) for s in sentences]
        length_variation = sum(abs(len(s) - avg_sentence_length) for s in sentences) / max(1, len(sentences))
        
        uniformity_score = 100 - min(100, int(length_variation * 2))
        
        # More complex texts might be more likely to be AI-generated
        complexity_factor = len(set(text.lower().split())) / max(1, len(text.lower().split()))
        complexity_adjustment = (1 - complexity_factor) * 20
        
        # Calculate final AI score
        ai_score = int((formality_score + repetition_score + uniformity_score) / 3 + complexity_adjustment)
        ai_score = max(0, min(100, ai_score))
        
        # Human score is inverse
        human_score = 100 - ai_score
        
        return {
            "ai_score": ai_score,
            "human_score": human_score,
            "analysis": {
                "formal_language": formality_score,
                "repetitive_patterns": repetition_score,
                "sentence_uniformity": uniformity_score
            }
        }
    except Exception as e:
        return None


def register_user_to_backend(username, email, phone=None, plan_type=None):
    """
    Register a user to both backend systems:
    1. The original Andikar admin API
    2. The new Lipia MongoDB API
    
    Args:
        username (str): Username
        email (str): User's email
        phone (str, optional): Phone number
        plan_type (str, optional): Subscription plan
        
    Returns:
        tuple: (success, message)
    """
    success_admin = False
    success_lipia = False
    
    # Try to register with Andikar admin API
    try:
        # Prepare the data to send to the admin backend
        registration_data = {
            "name": username,
            "email": email,
            "phone": phone if phone else None,
            "details": {
                "plan_type": plan_type if plan_type else "Free",
                "signup_date": datetime.now().strftime('%Y-%m-%d'),
                "source": "web"
            }
        }
        
        print(f"Attempting to register user to Andikar backend at: {ADMIN_API_URL}/api/register")
        
        # Send the data to the backend API
        response = requests.post(
            f"{ADMIN_API_URL}/api/register", 
            json=registration_data,
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Andikar backend registration response status: {response.status_code}")
        
        if response.status_code == 201:
            success_admin = True
    except Exception as e:
        print(f"Error registering user to Andikar backend: {e}")
    
    # Try to register with Lipia MongoDB API
    try:
        # Format PIN (default to last 4 chars of username if not a phone number)
        pin = ''.join(c for c in phone[-4:] if c.isdigit()) if phone else username[-4:]
        
        # Ensure PIN is exactly 4 digits
        if not (pin.isdigit() and len(pin) == 4):
            pin = ''.join(random.choices('0123456789', k=4))
        
        # Prepare data for Lipia API
        lipia_data = {
            "username": username,
            "pin": pin,
            "phone_number": phone if phone else "0700000000",
            "words_remaining": 500 if plan_type == "Free" else 0
        }
        
        headers = {
            "X-API-Key": LIPIA_API_KEY,
            "Content-Type": "application/json"
        }
        
        print(f"Attempting to register user to Lipia backend at: {LIPIA_API_URL}/users")
        
        # Send the data to the Lipia API
        response = requests.post(
            f"{LIPIA_API_URL}/users", 
            json=lipia_data,
            timeout=15,
            headers=headers
        )
        
        print(f"Lipia backend registration response status: {response.status_code}")
        
        if response.status_code in [201, 409]:  # 409 means user already exists
            success_lipia = True
    except Exception as e:
        print(f"Error registering user to Lipia backend: {e}")
    
    # Return overall success and message
    if success_admin or success_lipia:
        return True, "Registration successful with at least one backend service."
    else:
        return False, "Registration failed with all backend services."
