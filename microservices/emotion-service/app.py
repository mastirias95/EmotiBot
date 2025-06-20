"""
Emotion Service - Analyzes text to detect emotions and sentiment.
Provides emotion detection, sentiment analysis, and confidence scoring.
"""

from flask import Flask, request, jsonify
import logging
import os
import sys
from textblob import TextBlob
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
import redis
import json
import requests
import nltk
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

if not RABBITMQ_AVAILABLE:
    logger.warning("Message queue library not available, running without RabbitMQ")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS for all routes
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)

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

# RabbitMQ setup
if RABBITMQ_AVAILABLE and get_queue_client:
    try:
        queue_client = get_queue_client('emotion-service')
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
        queue_client = None
else:
    queue_client = None
    logger.info("RabbitMQ not available - running in standalone mode")

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Service URLs
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8002')
SERVICE_SECRET = os.environ.get('SERVICE_SECRET', 'default-service-secret')

# Emotion categories and keywords
EMOTION_KEYWORDS = {
    'joy': ['happy', 'joy', 'excited', 'delighted', 'pleased', 'thrilled', 'ecstatic', 'elated'],
    'sadness': ['sad', 'depressed', 'melancholy', 'grief', 'sorrow', 'unhappy', 'miserable', 'heartbroken'],
    'anger': ['angry', 'furious', 'irritated', 'annoyed', 'mad', 'rage', 'frustrated', 'outraged'],
    'fear': ['afraid', 'scared', 'terrified', 'anxious', 'worried', 'nervous', 'frightened', 'panicked'],
    'surprise': ['surprised', 'shocked', 'amazed', 'astonished', 'stunned', 'bewildered', 'startled'],
    'disgust': ['disgusted', 'revolted', 'repulsed', 'sickened', 'appalled', 'horrified'],
    'trust': ['trust', 'confident', 'secure', 'reliable', 'faithful', 'loyal', 'dependable'],
    'anticipation': ['excited', 'eager', 'hopeful', 'optimistic', 'enthusiastic', 'looking forward']
}

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
                'X-Service-Name': 'emotion-service'
            },
            json={'token': token},
            timeout=5
        )
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Auth service communication error: {e}")
        return False, None

def detect_emotion_keywords(text):
    """Detect emotion based on keyword matching."""
    text_lower = text.lower()
    emotion_scores = {}
    
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            emotion_scores[emotion] = score
    
    return emotion_scores

def analyze_sentiment(text):
    """Analyze sentiment using TextBlob."""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def get_primary_emotion(emotion_scores, sentiment_polarity):
    """Determine primary emotion based on scores and sentiment."""
    if not emotion_scores:
        # No emotion keywords found, use sentiment
        if sentiment_polarity > 0.3:
            return 'joy', 0.6
        elif sentiment_polarity < -0.3:
            return 'sadness', 0.6
        else:
            return 'neutral', 0.5
    
    # Find emotion with highest score
    primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])
    
    # Calculate confidence based on score and sentiment alignment
    emotion_name, keyword_score = primary_emotion
    max_possible_score = len(EMOTION_KEYWORDS[emotion_name])
    keyword_confidence = keyword_score / max_possible_score
    
    # Adjust confidence based on sentiment alignment
    if emotion_name in ['joy', 'trust', 'anticipation'] and sentiment_polarity > 0:
        sentiment_boost = min(sentiment_polarity, 0.3)
    elif emotion_name in ['sadness', 'fear', 'anger', 'disgust'] and sentiment_polarity < 0:
        sentiment_boost = min(abs(sentiment_polarity), 0.3)
    else:
        sentiment_boost = 0
    
    final_confidence = min(keyword_confidence + sentiment_boost, 1.0)
    
    return emotion_name, final_confidence

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Number of health check requests')
def health_check():
    """Health check endpoint."""
    queue_healthy = queue_client.ensure_connection() if queue_client else False
    
    return jsonify({
        'service': 'emotion-service',
        'status': 'healthy',
        'queue_connection': queue_healthy,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/emotion/detect', methods=['POST'])
@metrics.counter('emotion_detections', 'Number of emotion detection requests')
def detect_emotion():
    """Detect emotion in text."""
    # Verify user token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    # Check cache first
    cache_key = f"emotion:{hash(text)}"
    if redis_client:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            logger.info(f"Emotion analysis result from cache for text: {text[:50]}...")
            return jsonify(result), 200
    
    try:
        # Analyze emotion
        emotion_scores = detect_emotion_keywords(text)
        sentiment_polarity = analyze_sentiment(text)
        primary_emotion, confidence = get_primary_emotion(emotion_scores, sentiment_polarity)
        
        result = {
            'text': text,
            'emotion': primary_emotion,
            'confidence': round(confidence, 3),
            'sentiment': round(sentiment_polarity, 3),
            'emotion_scores': emotion_scores,
            'user_id': user_data.get('user', {}).get('id'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache the result
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(result))  # Cache for 1 hour
        
        # Publish emotion analysis event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_emotion_analyzed({
                    'text': text,
                    'emotion': primary_emotion,
                    'confidence': confidence,
                    'sentiment': sentiment_polarity,
                    'user_id': user_data.get('user', {}).get('id'),
                    'timestamp': datetime.utcnow().isoformat()
                })
                logger.info(f"Published emotion analysis event for text: {text[:50]}...")
            except Exception as e:
                logger.error(f"Failed to publish emotion analysis event: {e}")
        
        logger.info(f"Emotion analysis completed: {primary_emotion} (confidence: {confidence})")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Emotion analysis failed: {e}")
        return jsonify({'error': 'Emotion analysis failed'}), 500

@app.route('/api/emotion/stats', methods=['GET'])
@metrics.counter('emotion_stats_requests', 'Number of emotion statistics requests')
def get_emotion_stats():
    """Get emotion detection statistics."""
    # Verify service token
    if not validate_service_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get stats from Redis
        stats = {}
        if redis_client:
            for emotion in EMOTION_KEYWORDS.keys():
                count = redis_client.get(f"emotion_stats:{emotion}")
                stats[emotion] = int(count) if count else 0
            
            total_analyses = redis_client.get("emotion_stats:total")
            stats['total_analyses'] = int(total_analyses) if total_analyses else 0
        else:
            stats = {emotion: 0 for emotion in EMOTION_KEYWORDS.keys()}
            stats['total_analyses'] = 0
        
        return jsonify({
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get emotion stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/emotion/validate', methods=['POST'])
@metrics.counter('emotion_validations', 'Number of emotion validation requests')
def validate_emotion():
    """Validate emotion detection with user feedback."""
    # Verify user token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    text = data.get('text', '').strip()
    detected_emotion = data.get('detected_emotion', '')
    user_feedback = data.get('user_feedback', '')
    
    if not all([text, detected_emotion, user_feedback]):
        return jsonify({'error': 'Text, detected_emotion, and user_feedback are required'}), 400
    
    try:
        # Store validation data
        validation_data = {
            'text': text,
            'detected_emotion': detected_emotion,
            'user_feedback': user_feedback,
            'user_id': user_data.get('user', {}).get('id'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Publish validation event to RabbitMQ for model improvement
        if queue_client:
            try:
                queue_client.publish_event('emotion.validation', validation_data)
                logger.info(f"Published emotion validation event for text: {text[:50]}...")
            except Exception as e:
                logger.error(f"Failed to publish emotion validation event: {e}")
        
        return jsonify({
            'message': 'Validation recorded successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Emotion validation failed: {e}")
        return jsonify({'error': 'Validation failed'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Emotion Service...")
    app.run(host='0.0.0.0', port=8003, debug=False)