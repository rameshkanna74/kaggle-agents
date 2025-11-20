import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_query(text, email=None):
    print(f"\nTesting /query with: '{text}' (User: {email})")
    payload = {"text": text}
    if email:
        payload["user_email"] = email
    
    try:
        resp = requests.post(f"{BASE_URL}/query", json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Query failed: {e}")

if __name__ == "__main__":
    print("Ensure the server is running (python main.py) before running this script.")
    time.sleep(1)
    
    test_health()
    
    # Test cases based on user requirements
    test_query("How much revenue did we make this month?")
    test_query("Show me all unpaid invoices for this email.", "basic_user@example.com")
    test_query("Cancel my subscription.", "pro_user@example.com")
