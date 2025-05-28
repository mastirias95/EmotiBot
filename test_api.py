import requests
import json

def test_emotion_analysis():
    url = "http://localhost:5001/api/analyze"
    data = {"text": "I am feeling really excited about this project!"}
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Check if the response contains a bot_message (indicating Gemini is working)
        result = response.json()
        if 'bot_message' in result:
            print(f"\nBot Message: {result['bot_message']}")
            
            # Check for fallback response patterns
            fallback_phrases = [
                "I'm glad you're feeling happy!",
                "I understand you're feeling frustrated.",
                "That is quite surprising! Tell me more about it!",
                "It's okay to feel scared.",
                "I understand how you feel."
            ]
            
            is_fallback = any(phrase in result['bot_message'] for phrase in fallback_phrases)
            
            if is_fallback:
                print("❌ Using fallback response - Gemini not working")
                print("💡 Make sure you've set a valid GEMINI_API_KEY in your .env file")
            else:
                print("✅ Using Gemini response - API working!")
        
    except Exception as e:
        print(f"Error: {e}")

def test_health_endpoint():
    url = "http://localhost:5001/health"
    
    try:
        response = requests.get(url)
        print(f"Health Status Code: {response.status_code}")
        print(f"Health Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing EmotiBot API...")
    print("\n1. Testing health endpoint:")
    health_ok = test_health_endpoint()
    
    print("\n2. Testing emotion analysis:")
    test_emotion_analysis()
    
    print(f"\nResults:")
    print(f"Health endpoint: {'✅ OK' if health_ok else '❌ Failed'}") 