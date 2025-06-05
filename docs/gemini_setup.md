# Gemini LLM Integration Setup

## Overview
EmotiBot now supports Google's Gemini LLM for enhanced conversational AI capabilities. This integration provides:

- **Natural Conversations**: Context-aware, personalized responses
- **Emotional Intelligence**: Responses tailored to detected emotions
- **Conversation Memory**: Maintains context across multiple messages
- **Mood Insights**: AI-generated analysis of emotional patterns

## Getting Started

### 1. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Configure EmotiBot

#### Option A: Environment Variable (Recommended)
```bash
# Set environment variable
export GEMINI_API_KEY="your_api_key_here"

# Or add to .env file
echo "GEMINI_API_KEY=your_api_key_here" >> .env
```

#### Option B: Direct Configuration
```python
# In your application startup
from services.gemini_service import GeminiService
gemini_service = GeminiService(api_key="your_api_key_here")
```

### 3. Restart Application
```bash
python app.py
```

## Features

### Enhanced Chat Responses
- Contextual responses based on conversation history
- Emotion-aware reply generation
- Natural language understanding

### Mood Insights (Authenticated Users)
```http
GET /api/conversations/insights
Authorization: Bearer <your_jwt_token>
```

Returns AI-generated insights about emotional patterns.

## Fallback Behavior

If no API key is provided or the service is unavailable:
- EmotiBot falls back to pre-written responses
- All core functionality remains available
- No errors or service interruptions

## API Costs

Gemini API pricing (as of 2024):
- **Free tier**: 60 requests per minute
- **Paid tier**: $0.00025 per 1K characters

For typical EmotiBot usage:
- ~50-100 characters per request
- Very cost-effective for personal/demo use

## Security Notes

- Never commit API keys to version control
- Use environment variables in production
- Monitor API usage in Google Cloud Console
- Rotate keys periodically

## Testing

Test Gemini integration:
```bash
# With API key set
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "I am feeling really excited about this project!"}'
```

You should see more natural, contextual responses compared to the basic fallback responses. 