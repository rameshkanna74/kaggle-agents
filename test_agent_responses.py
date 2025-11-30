import requests
import json

def query(text, email="alice@example.com"):
    print(f"\nQuery: {text}")
    try:
        response = requests.post(
            "http://localhost:8000/query",
            json={
                "text": text,
                "user_email": email,
                "session_id": "test"
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
            print(f"Confidence: {data.get('confidence')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

# Test cases
query("who am i") 
query("I am getting API 401 errors")
