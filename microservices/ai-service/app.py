"""
AI Service - Handles integration with Google Gemini API and provides intelligent responses.
Integrates with Auth Service for user validation and provides context-aware AI responses.
"""

from flask import Flask, request, jsonify
import google.generativeai as genai
import os
import logging
import requests
import json
from datetime import datetime, timedelta
from prometheus_flask_exporter import PrometheusMetrics
import redis
import sys
from flask_cors import CORS

# Add shared-libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared-libs'))

# Try to import message queue, handle gracefully if not available
try:
    from message_queue import get_queue_client
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    get_queue_client = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS for all routes
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)

# Prometheus metrics
metrics = PrometheusMetrics(app)

# Service URLs
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8002')
SERVICE_SECRET = os.environ.get('SERVICE_SECRET', 'default-service-secret')

# Google Gemini Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    logger.info("Gemini AI configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not provided - AI responses will be limited")

# Redis setup for caching
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'redis'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

if not RABBITMQ_AVAILABLE:
    logger.warning("Message queue library not available, running without RabbitMQ")

# RabbitMQ setup
if RABBITMQ_AVAILABLE and get_queue_client:
    try:
        queue_client = get_queue_client('ai-service')
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
        queue_client = None
else:
    queue_client = None
    logger.info("RabbitMQ not available - running in standalone mode")

def validate_service_token():
    """Validate service-to-service authentication token."""
    auth_header = request.headers.get('Authorization')
    service_name = request.headers.get('X-Service-Name')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ')[1]
    
    try:
        import jwt
        payload = jwt.decode(token, SERVICE_SECRET, algorithms=['HS256'])
        return payload.get('service') == service_name
    except jwt.InvalidTokenError:
        return False

def verify_user_token(token):
    """Verify user JWT token with Auth Service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-Service-Name': 'ai-service'
            },
            json={'token': token},
            timeout=5
        )
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Auth service communication error: {e}")
        return False, None

def get_cached_response(cache_key):
    """Get cached AI response from Redis."""
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        return json.loads(cached) if cached else None
    except Exception as e:
        logger.error(f"Redis cache error: {e}")
        return None

def cache_response(cache_key, response, ttl=3600):
    """Cache AI response in Redis."""
    if not redis_client:
        return
    
    try:
        redis_client.setex(cache_key, ttl, json.dumps(response))
    except Exception as e:
        logger.error(f"Redis cache error: {e}")

def generate_emotion_aware_response(message, emotion=None, confidence=None, context='general'):
    """Generate AI response based on message and emotion context."""
    
    # Create cache key
    cache_key = f"ai_response:{hash(f'{message}:{emotion}:{context}')}"
    
    # Check cache first
    cached_response = get_cached_response(cache_key)
    if cached_response:
        logger.info("Returning cached AI response")
        return cached_response
    
    if not model:
        # Fallback response when Gemini is not available
        fallback_responses = {
            'happy': [
                "I'm so glad you're feeling happy! 😊 What's making your day special?",
                "Your happiness is contagious! 🌟 What would you like to talk about?",
                "It's wonderful to hear you're in good spirits! ✨"
            ],
            'sad': [
                "I'm sorry you're feeling down. 😔 Would you like to talk about what's bothering you?",
                "It's okay to feel sad sometimes. 💙 I'm here to listen if you need someone to talk to.",
                "I understand this is a difficult time. 🌧️ What can I do to help?"
            ],
            'angry': [
                "I can sense you're frustrated. 😤 Would you like to talk about what happened?",
                "It's natural to feel angry sometimes. 🔥 What's on your mind?",
                "I'm here to listen if you want to vent. 💪"
            ],
            'neutral': [
                "Hello! How are you feeling today? 🤔",
                "I'm here to chat! What's on your mind? 💭",
                "How can I help you today? 😊"
            ],
            'microservices': [
                "Microservices architecture is a great topic! 🏗️ It's an approach where applications are built as a collection of small, independent services that communicate over well-defined APIs. Each service is responsible for a specific business function and can be developed, deployed, and scaled independently.",
                "Great question about microservices! 🔧 This architecture pattern breaks down large applications into smaller, manageable pieces. Benefits include better scalability, technology diversity, and fault isolation. However, it also introduces complexity in service communication and data consistency.",
                "Microservices are fascinating! 🚀 Think of them as building blocks - each service handles one thing well and they work together to create a complete application. This EmotiBot demo is actually built using microservices architecture with separate services for authentication, emotion analysis, AI responses, and more!"
            ],
            'architecture': [
                "Software architecture is the foundation of any good system! 🏛️ It defines how components interact, what patterns to use, and how to structure code for maintainability and scalability.",
                "Architecture is crucial for building robust applications! 📐 Good architecture considers factors like performance, security, maintainability, and future growth.",
                "Great question about architecture! 🎯 It's about making strategic decisions on how to organize and structure software systems to meet both current and future requirements."
            ]
        }
        
        # Simple keyword-based response selection
        message_lower = message.lower()
        if any(word in message_lower for word in ['microservice', 'micro service', 'microservices']):
            response_key = 'microservices'
        elif any(word in message_lower for word in ['architecture', 'design', 'structure', 'pattern']):
            response_key = 'architecture'
        elif emotion and emotion in fallback_responses:
            response_key = emotion
        else:
            response_key = 'neutral'
        
        import random
        response = random.choice(fallback_responses.get(response_key, fallback_responses['neutral']))
        
        result = {
            'response': response,
            'emotion_detected': emotion,
            'confidence': confidence,
            'source': 'intelligent_fallback',
            'cached': False
        }
        
        cache_response(cache_key, result)
        return result
    
    try:
        # Build context-aware prompt
        prompt_parts = []
        
        if context == 'conversation':
            prompt_parts.append("You are EmotiBot, an empathetic AI companion designed to help users with their emotional well-being.")
        
        if emotion and confidence:
            prompt_parts.append(f"The user's message indicates they are feeling {emotion} (confidence: {confidence:.2f}).")
            prompt_parts.append("Respond with empathy and understanding, acknowledging their emotional state.")
        
        prompt_parts.append("User message:")
        prompt_parts.append(message)
        
        prompt_parts.append("\nPlease provide a helpful, empathetic response that:")
        prompt_parts.append("- Shows understanding of their emotional state")
        prompt_parts.append("- Offers support and encouragement")
        prompt_parts.append("- Keeps the conversation engaging")
        prompt_parts.append("- Is appropriate for an emotional support context")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Generate response
        response = model.generate_content(full_prompt)
        
        result = {
            'response': response.text,
            'emotion_detected': emotion,
            'confidence': confidence,
            'source': 'gemini',
            'cached': False
        }
        
        # Cache the response
        cache_response(cache_key, result)
        
        logger.info(f"Generated AI response for emotion: {emotion}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        
        # Fallback response
        fallback = "I'm having trouble processing that right now, but I'm here to listen. How are you feeling?"
        
        result = {
            'response': fallback,
            'emotion_detected': emotion,
            'confidence': confidence,
            'source': 'error_fallback',
            'cached': False
        }
        
        return result

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Number of health check requests')
def health_check():
    """Health check endpoint."""
    queue_healthy = queue_client.ensure_connection() if queue_client else False
    gemini_available = bool(GEMINI_API_KEY)
    
    return jsonify({
        'service': 'ai-service',
        'status': 'healthy',
        'queue_connection': queue_healthy,
        'gemini_available': gemini_available,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/ai/generate', methods=['POST'])
@metrics.counter('ai_generation_requests', 'Number of AI generation requests')
def generate_response():
    """Generate AI response for user message."""
    # Check for authentication but don't require it (demo mode)
    auth_header = request.headers.get('Authorization')
    user_data = None
    user_id = 'anonymous'
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        is_valid, user_data = verify_user_token(token)
        if is_valid and user_data:
            user_id = user_data.get('user_id', 'anonymous')
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    message = data.get('message', '').strip()
    emotion = data.get('emotion')
    confidence = data.get('confidence')
    context = data.get('context', 'general')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Generate AI response
        ai_response = generate_emotion_aware_response(
            message=message,
            emotion=emotion,
            confidence=confidence,
            context=context
        )
        
        logger.info(f"Generated AI response for user {user_id}")
        
        return jsonify(ai_response), 200
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500

@app.route('/api/ai/chat', methods=['POST'])
@metrics.counter('ai_chat_requests', 'Number of AI chat requests')
def chat():
    """Handle chat conversation with AI."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    message = data.get('message', '').strip()
    conversation_history = data.get('history', [])
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    user_id = user_data.get('user_id')
    
    try:
        # Build conversation context
        context_parts = []
        if conversation_history:
            context_parts.append("Previous conversation:")
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                context_parts.append(f"{msg.get('sender', 'user')}: {msg.get('content', '')}")
            context_parts.append("\nCurrent message:")
        else:
            context_parts.append("Starting new conversation:")
        
        context_parts.append(message)
        
        full_context = "\n".join(context_parts)
        
        # Generate response with conversation context
        ai_response = generate_emotion_aware_response(
            message=full_context,
            context='conversation'
        )
        
        logger.info(f"Generated chat response for user {user_id}")
        
        return jsonify(ai_response), 200
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify({'error': 'Failed to process chat'}), 500

@app.route('/api/ai/suggestions', methods=['GET'])
@metrics.counter('ai_suggestion_requests', 'Number of AI suggestion requests')
def get_suggestions():
    """Get conversation starter suggestions."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        suggestions = [
            "How are you feeling today?",
            "What's been on your mind lately?",
            "Is there anything you'd like to talk about?",
            "How was your day?",
            "What made you smile today?",
            "Is there something bothering you?",
            "What are you grateful for today?",
            "How can I help you feel better?"
        ]
        
        import random
        selected_suggestions = random.sample(suggestions, 4)
        
        return jsonify({
            'suggestions': selected_suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return jsonify({'error': 'Failed to get suggestions'}), 500

@app.route('/api/ai/status', methods=['GET'])
@metrics.counter('ai_status_requests', 'Number of AI status requests')
def get_ai_status():
    """Get AI service status and capabilities."""
    try:
        status = {
            'service': 'ai-service',
            'status': 'operational',
            'gemini_available': model is not None,
            'cache_available': redis_client is not None,
            'queue_available': queue_client is not None,
            'timestamp': datetime.utcnow().isoformat(),
            'capabilities': [
                'emotion-aware responses',
                'conversation context',
                'response caching',
                'fallback responses'
            ]
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': 'Failed to get status'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005, debug=False) 