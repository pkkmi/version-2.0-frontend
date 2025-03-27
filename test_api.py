#!/usr/bin/env python3
"""
Test script for the Humanizer API connection.
Run this script to verify that your connection to the Humanizer API is working.
"""
import os
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_humanizer_api():
    """Test the connection to the Humanizer API"""
    # Get API URL from environment variable or use default
    api_url = os.environ.get("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
    
    print(f"Testing connection to Humanizer API at: {api_url}")
    
    # Test the root endpoint
    try:
        start_time = time.time()
        response = requests.get(f"{api_url}/", timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Root endpoint: Status {response.status_code} in {elapsed:.2f} seconds")
        print(f"Response type: {response.headers.get('content-type', 'Unknown')}")
        
        if response.status_code != 200:
            print(f"  Warning: Got status code {response.status_code} instead of 200")
    except Exception as e:
        print(f"  Error accessing root endpoint: {str(e)}")
    
    # Test a simple echo request
    sample_text = "This is a test of the Andikar humanizer API connection."
    print("\nTesting echo_text endpoint with sample text...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{api_url}/echo_text", 
            json={"input_text": sample_text},
            timeout=10
        )
        elapsed = time.time() - start_time
        
        print(f"Echo endpoint: Status {response.status_code} in {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Echo response: {data.get('result', 'No result found')}")
            
            if data.get('result') == sample_text:
                print("  Success: Echo endpoint returned the same text that was sent")
            else:
                print("  Warning: Echo endpoint didn't return the exact text that was sent")
        else:
            print(f"  Error: Got status code {response.status_code} instead of 200")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error accessing echo endpoint: {str(e)}")
    
    # Test the actual humanize endpoint
    print("\nTesting humanize_text endpoint with sample text...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{api_url}/humanize_text", 
            json={"input_text": sample_text},
            timeout=30  # Longer timeout for humanize
        )
        elapsed = time.time() - start_time
        
        print(f"Humanize endpoint: Status {response.status_code} in {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Humanized text: {data.get('result', 'No result found')}")
            
            if data.get('result') and data.get('result') != sample_text:
                print("  Success: Text was transformed by the humanizer API")
            else:
                print("  Warning: Humanized text is identical to or missing from the response")
        else:
            print(f"  Error: Got status code {response.status_code} instead of 200")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error accessing humanize endpoint: {str(e)}")

    # Provide recommendations
    print("\nRecommendations:")
    if api_url != "https://web-production-3db6c.up.railway.app":
        print("- You're using a custom API URL. Make sure it's correct.")
    else:
        print("- You're using the default API URL. If you have a different URL, set the HUMANIZER_API_URL environment variable.")
    
    print("- Check that the API service is running and accessible from your network.")
    print("- Verify that the API endpoints are correctly implemented and responding.")
    print("- If using a custom API, check for any authentication requirements.")

if __name__ == "__main__":
    test_humanizer_api()
