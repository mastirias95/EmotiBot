import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing environment variable loading...")
print(f"GEMINI_API_KEY found: {os.getenv('GEMINI_API_KEY') is not None}")
if os.getenv('GEMINI_API_KEY'):
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"API key starts with: {api_key[:10]}...")
    print(f"API key length: {len(api_key)}")
else:
    print("❌ GEMINI_API_KEY not found in environment")

# Check if .env file exists
if os.path.exists('.env'):
    print("✅ .env file exists")
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"✅ .env file content length: {len(content)} characters")
        if 'GEMINI_API_KEY' in content:
            print("✅ GEMINI_API_KEY found in .env file")
        else:
            print("❌ GEMINI_API_KEY not found in .env file")
else:
    print("❌ .env file does not exist") 