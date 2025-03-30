import requests
import json
from flask import current_app
import re

def count_words(text):
    """Count the number of words in a text"""
    if not text:
        return 0
    return len(re.findall(r'\S+', text))

def humanize_text(text):
    """Send text to humanizer API and return humanized version"""
    if not text:
        return {"success": False, "message": "No text provided", "humanized_text": ""}
    
    try:
        response = requests.post(
            current_app.config['HUMANIZER_API_URL'],
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "message": "Text humanized successfully",
                "humanized_text": data.get("humanized_text", "")
            }
        else:
            return {
                "success": False,
                "message": f"API error: {response.status_code}",
                "humanized_text": ""
            }
    except requests.exceptions.RequestException as e:
        # Fallback humanization when API is unavailable
        return {
            "success": False, 
            "message": f"Could not connect to humanizer API: {str(e)}", 
            "humanized_text": _basic_humanize(text)
        }

def _basic_humanize(text):
    """Basic humanization function as a fallback"""
    # Very simple fallback humanization
    humanized = text
    
    # Replace common AI patterns
    replacements = [
        (r'\bAI\b', 'I'),
        (r'\bas an AI\b', 'as a writer'),
        (r'\bAs an AI\b', 'As a writer'),
        (r'\bAs an assistant\b', 'As a person'),
        (r'\bas an assistant\b', 'as a person'),
        (r'\bI was created by\b', 'I work with'),
        (r'\bI was designed to\b', 'I aim to'),
        (r'\bMy programming\b', 'My training'),
        (r'\bmy programming\b', 'my training'),
        (r'\bI do not have\b', 'I lack'),
        (r'\bI cannot\b', "I can't"),
        (r'\bI do not possess\b', "I don't have"),
    ]
    
    for pattern, replacement in replacements:
        humanized = re.sub(pattern, replacement, humanized)
    
    return humanized

def check_api_status():
    """Check if the humanizer API is available"""
    try:
        response = requests.get(
            current_app.config['HUMANIZER_API_URL'].split('/humanize')[0] + '/status',
            timeout=5
        )
        return response.status_code == 200
    except:
        return False