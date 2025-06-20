"""
AI Service - Handles AI integration with Google Gemini for EmotiBot microservices.
Provides intelligent response generation, mood insights, and contextual AI features.
"""

from flask import Flask, request, jsonify
import logging
import os
import sys
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
import redis
import json
import google.generativeai as genai
from typing import List, Dict, Any

# Add shared libs to path
sys.path.append('/app/shared-libs')
from service_client import get_service_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
metrics = PrometheusMetrics(app)

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

# Service clients
auth_client = get_service_client('auth-service', 'ai-service')

# Configure Gemini AI
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
MOCK_MODE = not GEMINI_API_KEY or GEMINI_API_KEY == 'your_api_key_here'

if not MOCK_MODE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        logger.info("Gemini AI configured successfully")
    except Exception as e:
        logger.warning(f"Gemini AI configuration failed: {e}, switching to mock mode")
        MOCK_MODE = True
else:
    logger.info("Running in mock mode (no Gemini API key configured)")

class AIService:
    """Service for AI-powered response generation and insights."""
    
    # Pre-defined responses for mock mode
    MOCK_RESPONSES = {
        'happy': [
            "That's wonderful to hear! Your positive energy is contagious. What's bringing you such joy today?",
            "I love your enthusiasm! It's great to see you in such a good mood. Keep spreading those positive vibes!",
            "Your happiness is making me smile too! Tell me more about what's making you feel so great."
        ],
        'sad': [
            "I can sense you're going through a tough time. Remember that it's okay to feel sad sometimes. Would you like to talk about what's bothering you?",
            "I'm here for you. Sadness is a natural emotion, and sharing your feelings can often help. What's on your mind?",
            "It sounds like you're having a difficult moment. Take your time, and know that this feeling will pass. How can I support you?"
        ],
        'angry': [
            "I can feel your frustration. It's important to acknowledge these feelings. What's causing this anger?",
            "Strong emotions like anger often signal that something important to you has been affected. Let's talk through it.",
            "I understand you're upset. Taking a deep breath might help. What happened that's making you feel this way?"
        ],
        'fear': [
            "I sense some anxiety in your message. Fear is a natural response to uncertainty. Would sharing your concerns help?",
            "It's brave of you to express your fears. Sometimes talking about what scares us can make it feel less overwhelming.",
            "I'm here to listen. Fear can feel isolating, but you're not alone. What's causing you to feel this way?"
        ],
        'surprise': [
            "Oh wow! It sounds like something unexpected happened. I'd love to hear more about what surprised you!",
            "Surprises can be exciting! Your enthusiasm is evident. Tell me all about what caught you off guard.",
            "That sounds intriguing! Life's surprises can be the most memorable moments. What happened?"
        ],
        'neutral': [
            "Thanks for sharing your thoughts with me. How has your day been so far?",
            "I appreciate you taking the time to chat. What's been on your mind lately?",
            "It's nice to hear from you. Is there anything specific you'd like to discuss today?"
        ]
    }
    
    @classmethod
    def generate_emotional_response(cls, message: str, emotion: str, confidence: float, 
                                  conversation_history: List[Dict] = None) -> str:
        """Generate an emotionally appropriate response to user input."""
        
        if MOCK_MODE:
            return cls._generate_mock_response(emotion, confidence)
        
        try:
            # Build context from conversation history
            context = cls._build_conversation_context(conversation_history)
            
            # Create emotion-aware prompt
            prompt = cls._create_emotional_prompt(message, emotion, confidence, context)
            
            # Generate response with Gemini
            response = model.generate_content(prompt)
            
            if response and response.text:
                generated_response = response.text.strip()
                logger.info(f"Generated AI response for emotion: {emotion}")
                return generated_response
            else:
                logger.warning("Gemini returned empty response, using fallback")
                return cls._generate_mock_response(emotion, confidence)
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return cls._generate_mock_response(emotion, confidence)
    
    @classmethod
    def generate_mood_insights(cls, conversation_history: List[Dict]) -> str:
        """Generate personalized mood insights based on conversation history."""
        
        if not conversation_history:
            return "Start chatting with me to get personalized mood insights based on your conversations!"
        
        if MOCK_MODE:
            return cls._generate_mock_insights(conversation_history)
        
        try:
            # Prepare conversation data for analysis
            emotions = [conv.get('emotion') for conv in conversation_history if conv.get('emotion')]
            messages = [conv.get('message', '')[:200] for conv in conversation_history]  # Limit message length
            
            prompt = f"""
            Based on the following conversation history and emotions, provide personalized mood insights:
            
            Recent emotions detected: {emotions}
            Sample messages: {messages[:5]}  # Limit to 5 messages for context
            
            Please provide:
            1. A summary of the user's emotional patterns
            2. Positive observations about their emotional awareness
            3. Gentle suggestions for emotional wellbeing
            4. Encouragement based on their communication style
            
            Keep the response supportive, insightful, and under 200 words.
            """
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                insights = response.text.strip()
                logger.info("Generated mood insights with Gemini")
                return insights
            else:
                return cls._generate_mock_insights(conversation_history)
                
        except Exception as e:
            logger.error(f"Error generating mood insights: {e}")
            return cls._generate_mock_insights(conversation_history)
    
    @classmethod
    def _generate_mock_response(cls, emotion: str, confidence: float) -> str:
        """Generate a mock response based on emotion."""
        import random
        
        responses = cls.MOCK_RESPONSES.get(emotion, cls.MOCK_RESPONSES['neutral'])
        base_response = random.choice(responses)
        
        # Add confidence-based modifier
        if confidence > 0.8:
            confidence_note = " I can clearly sense your feelings in your message."
        elif confidence > 0.5:
            confidence_note = " I'm picking up on your emotional state."
        else:
            confidence_note = " I'm here to listen and understand."
        
        return base_response + confidence_note
    
    @classmethod
    def _generate_mock_insights(cls, conversation_history: List[Dict]) -> str:
        """Generate mock mood insights."""
        emotions = [conv.get('emotion') for conv in conversation_history if conv.get('emotion')]
        
        if not emotions:
            return "I notice you've been sharing your thoughts with me. Keep expressing yourself - emotional awareness is a sign of growth!"
        
        # Count emotion frequencies
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        most_common = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'neutral'
        total_conversations = len(conversation_history)
        
        insights = f"""Based on your {total_conversations} recent conversations, I've noticed some interesting patterns:
        
        🎯 **Emotional Awareness**: You've been most frequently feeling {most_common}, which shows you're in touch with your emotions.
        
        💪 **Communication Strength**: You express yourself clearly and aren't afraid to share your feelings - that's a valuable skill!
        
        🌱 **Growth Opportunity**: Continue this emotional awareness journey. Every conversation is a step toward better self-understanding.
        
        Keep being open about your feelings - it's helping you grow emotionally!"""
        
        return insights
    
    @classmethod
    def _build_conversation_context(cls, conversation_history: List[Dict]) -> str:
        """Build context string from conversation history."""
        if not conversation_history:
            return "This is a new conversation."
        
        recent_context = []
        for conv in conversation_history[-3:]:  # Last 3 conversations
            user_msg = conv.get('message', '')[:100]  # Limit length
            emotion = conv.get('emotion', 'unknown')
            recent_context.append(f"User said: '{user_msg}' (emotion: {emotion})")
        
        return "Recent conversation context: " + " | ".join(recent_context)
    
    @classmethod
    def _create_emotional_prompt(cls, message: str, emotion: str, confidence: float, context: str) -> str:
        """Create an emotion-aware prompt for Gemini."""
        return f"""
        You are EmotiBot, an empathetic AI assistant specialized in emotional support and understanding.
        
        Context: {context}
        
        The user just said: "{message}"
        Detected emotion: {emotion} (confidence: {confidence:.2f})
        
        Respond with empathy and emotional intelligence. Your response should:
        1. Acknowledge their emotional state appropriately
        2. Be supportive and understanding
        3. Encourage further conversation if appropriate
        4. Be conversational and warm, not clinical
        5. Keep it under 150 words
        
        Match the tone to their emotion - be uplifting for positive emotions, supportive for negative ones.
        """

def verify_user_token():
    """Verify user authentication token with auth service."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    
    try:
        response = auth_client.post('/api/auth/verify', {'token': token})
        if response.status_code == 200:
            return response.json()['user']
        return None
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Health check requests')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'service': 'ai-service',
        'status': 'healthy',
        'version': '1.0',
        'gemini_mode': 'mock' if MOCK_MODE else 'live',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/ai/generate', methods=['POST'])
@metrics.counter('ai_generation_requests', 'AI response generation requests')
@metrics.histogram('ai_generation_duration', 'AI response generation duration')
def generate_response():
    """Generate AI response for user message with emotion context."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    message = data.get('message', '').strip()
    emotion = data.get('emotion', 'neutral')
    confidence = data.get('confidence', 0.5)
    conversation_history = data.get('conversation_history', [])
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Check cache first
    cache_key = f"ai_response:{hash(message)}:{emotion}:{user['id']}"
    if redis_client:
        cached_response = redis_client.get(cache_key)
        if cached_response:
            logger.info(f"Returning cached AI response for user {user['username']}")
            return jsonify(json.loads(cached_response)), 200
    
    try:
        # Generate AI response
        ai_response = AIService.generate_emotional_response(
            message=message,
            emotion=emotion,
            confidence=confidence,
            conversation_history=conversation_history
        )
        
        result = {
            'ai_response': ai_response,
            'user_id': user['id'],
            'input_emotion': emotion,
            'input_confidence': confidence,
            'generated_at': datetime.utcnow().isoformat(),
            'service_mode': 'mock' if MOCK_MODE else 'gemini'
        }
        
        # Cache the result
        if redis_client:
            redis_client.setex(cache_key, 600, json.dumps(result))  # Cache for 10 minutes
        
        logger.info(f"Generated AI response for user {user['username']} with emotion {emotion}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500

@app.route('/api/ai/insights', methods=['POST'])
@metrics.counter('ai_insights_requests', 'AI mood insights requests')
def generate_mood_insights():
    """Generate personalized mood insights based on conversation history."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    conversation_history = data.get('conversation_history', [])
    
    # Check cache first
    history_hash = hash(str(sorted([(c.get('id', 0), c.get('emotion', '')) for c in conversation_history])))
    cache_key = f"ai_insights:{user['id']}:{history_hash}"
    
    if redis_client:
        cached_insights = redis_client.get(cache_key)
        if cached_insights:
            logger.info(f"Returning cached insights for user {user['username']}")
            return jsonify(json.loads(cached_insights)), 200
    
    try:
        # Generate mood insights
        insights = AIService.generate_mood_insights(conversation_history)
        
        result = {
            'insights': insights,
            'user_id': user['id'],
            'conversation_count': len(conversation_history),
            'generated_at': datetime.utcnow().isoformat(),
            'service_mode': 'mock' if MOCK_MODE else 'gemini'
        }
        
        # Cache the result
        if redis_client:
            redis_client.setex(cache_key, 1800, json.dumps(result))  # Cache for 30 minutes
        
        logger.info(f"Generated mood insights for user {user['username']}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        return jsonify({'error': 'Failed to generate insights'}), 500

@app.route('/api/ai/capabilities', methods=['GET'])
@metrics.counter('ai_capabilities_requests', 'AI capabilities requests')
def get_ai_capabilities():
    """Get information about AI service capabilities."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    capabilities = {
        'service_name': 'ai-service',
        'version': '1.0',
        'mode': 'mock' if MOCK_MODE else 'gemini',
        'features': [
            'Emotional response generation',
            'Mood insights analysis',
            'Conversation context awareness',
            'Multi-emotion support',
            'Caching for performance'
        ],
        'supported_emotions': list(AIService.MOCK_RESPONSES.keys()),
        'max_conversation_history': 10,
        'response_cache_duration': '10 minutes',
        'insights_cache_duration': '30 minutes'
    }
    
    return jsonify(capabilities), 200

@app.route('/api/ai/health', methods=['GET'])
@metrics.counter('ai_health_requests', 'AI service health requests')
def get_ai_health():
    """Get detailed health information about AI service."""
    health_info = {
        'service': 'ai-service',
        'status': 'healthy',
        'gemini_api': 'disabled' if MOCK_MODE else 'enabled',
        'redis_cache': 'enabled' if redis_client else 'disabled',
        'last_check': datetime.utcnow().isoformat()
    }
    
    # Test Gemini connection if not in mock mode
    if not MOCK_MODE:
        try:
            test_response = model.generate_content("Hello")
            health_info['gemini_test'] = 'passed' if test_response else 'failed'
        except Exception as e:
            health_info['gemini_test'] = f'failed: {str(e)}'
    
    return jsonify(health_info), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info(f"Starting AI Service in {'mock' if MOCK_MODE else 'Gemini'} mode...")
    app.run(host='0.0.0.0', port=8005, debug=False)