import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key found: {api_key is not None}")
if api_key:
    print(f"API Key starts with: {api_key[:10]}...")
else:
    print("API Key is None") 