import requests
import sys

def test_application():
    try:
        # Test the main page
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"Main page status code: {response.status_code}")
        
        # Test the API endpoint with a sample message
        api_response = requests.post(
            'http://127.0.0.1:5000/api/analyze',
            json={"text": "I am feeling happy today!"},
            timeout=5
        )
        print(f"API endpoint status code: {api_response.status_code}")
        print(f"API response: {api_response.json()}")
        
        return True
    except Exception as e:
        print(f"Error testing application: {e}")
        return False

if __name__ == "__main__":
    success = test_application()
    sys.exit(0 if success else 1) 