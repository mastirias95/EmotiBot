"""
WebSocket Service - Handles real-time communication between users and AI.
Provides WebSocket connections, real-time messaging, and live emotion analysis.
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import logging
import os
import requests
import json
from datetime import datetime
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

if not RABBITMQ_AVAILABLE:
    logger.warning("Message queue library not available, running without RabbitMQ")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS for all routes
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)

# Prometheus metrics
metrics = PrometheusMetrics(app)

# SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Service URLs
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8002')
EMOTION_SERVICE_URL = os.environ.get('EMOTION_SERVICE_URL', 'http://emotion-service:8003')
AI_SERVICE_URL = os.environ.get('AI_SERVICE_URL', 'http://ai-service:8005')
SERVICE_SECRET = os.environ.get('SERVICE_SECRET', 'default-service-secret')

# Redis setup for session management and caching
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
        queue_client = get_queue_client('websocket-service')
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
        queue_client = None
else:
    queue_client = None
    logger.info("RabbitMQ not available - running in standalone mode")

# Active connections tracking
active_connections = {}

def verify_user_token(token):
    """Verify user JWT token with Auth Service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-Service-Name': 'websocket-service'
            },
            json={'token': token},
            timeout=5
        )
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Auth service communication error: {e}")
        return False, None

def analyze_emotion(text):
    """Analyze emotion using Emotion Service."""
    try:
        response = requests.post(
            f"{EMOTION_SERVICE_URL}/api/emotion/detect",
            headers={
                'Content-Type': 'application/json',
                'X-Service-Name': 'websocket-service'
            },
            json={'text': text},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Emotion service communication error: {e}")
        return None

def generate_ai_response(message, emotion_data=None, user_id=None):
    """Generate AI response using AI Service."""
    try:
        payload = {
            'message': message,
            'context': 'realtime'
        }
        if emotion_data:
            payload['emotion'] = emotion_data.get('emotion')
            payload['confidence'] = emotion_data.get('confidence')
        
        response = requests.post(
            f"{AI_SERVICE_URL}/api/ai/generate",
            headers={
                'Content-Type': 'application/json',
                'X-Service-Name': 'websocket-service'
            },
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"AI service communication error: {e}")
        return None

def store_message_in_cache(user_id, message_data):
    """Store message in Redis cache for persistence."""
    if not redis_client:
        return
    
    try:
        cache_key = f"user_messages:{user_id}"
        messages = redis_client.lrange(cache_key, 0, -1)
        messages.append(json.dumps(message_data))
        
        # Keep only last 50 messages
        if len(messages) > 50:
            messages = messages[-50:]
        
        redis_client.delete(cache_key)
        for msg in messages:
            redis_client.rpush(cache_key, msg)
        
        # Set expiration (24 hours)
        redis_client.expire(cache_key, 86400)
        
    except Exception as e:
        logger.error(f"Redis cache error: {e}")

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Number of health check requests')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'service': 'websocket-service',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_connections': len(active_connections),
        'dependencies': {
            'auth_service': AUTH_SERVICE_URL,
            'emotion_service': EMOTION_SERVICE_URL,
            'ai_service': AI_SERVICE_URL
        }
    }), 200

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to EmotiBot WebSocket'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Clean up active connection
    if request.sid in active_connections:
        user_id = active_connections[request.sid].get('user_id')
        if user_id:
            logger.info(f"User {user_id} disconnected")
        del active_connections[request.sid]

@socketio.on('authenticate')
def handle_authentication(data):
    """Handle user authentication."""
    try:
        token = data.get('token')
        if not token:
            emit('auth_error', {'error': 'Token is required'})
            return
        
        # Verify token with Auth Service
        is_valid, user_data = verify_user_token(token)
        
        if not is_valid:
            emit('auth_error', {'error': 'Invalid token'})
            return
        
        user_id = user_data.get('user_id')
        username = user_data.get('username')
        
        # Store connection info
        active_connections[request.sid] = {
            'user_id': user_id,
            'username': username,
            'authenticated': True,
            'connected_at': datetime.utcnow().isoformat()
        }
        
        # Join user-specific room
        join_room(f"user_{user_id}")
        
        logger.info(f"User {username} (ID: {user_id}) authenticated")
        
        emit('authenticated', {
            'message': 'Authentication successful',
            'user': {
                'id': user_id,
                'username': username
            }
        })
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        emit('auth_error', {'error': 'Authentication failed'})

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming message from user."""
    try:
        # Check if user is authenticated
        if request.sid not in active_connections:
            emit('error', {'error': 'Not authenticated'})
            return
        
        connection_info = active_connections[request.sid]
        user_id = connection_info.get('user_id')
        username = connection_info.get('username')
        
        message = data.get('message', '').strip()
        if not message:
            emit('error', {'error': 'Message is required'})
            return
        
        logger.info(f"Received message from {username}: {message}")
        
        # Store user message
        user_message_data = {
            'type': 'user',
            'content': message,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'username': username
        }
        
        store_message_in_cache(user_id, user_message_data)
        
        # Emit user message back to client
        emit('message_received', {
            'message': user_message_data,
            'status': 'processing'
        })
        
        # Analyze emotion
        emotion_data = analyze_emotion(message)
        
        # Generate AI response
        ai_response_data = generate_ai_response(message, emotion_data, user_id)
        
        if ai_response_data:
            ai_response = ai_response_data.get('response', 'I apologize, but I am unable to respond at the moment.')
        else:
            ai_response = 'I apologize, but I am unable to respond at the moment.'
        
        # Store AI response
        ai_message_data = {
            'type': 'bot',
            'content': ai_response,
            'timestamp': datetime.utcnow().isoformat(),
            'emotion_analysis': emotion_data,
            'user_id': user_id
        }
        
        store_message_in_cache(user_id, ai_message_data)
        
        # Emit AI response to client
        emit('bot_response', {
            'message': ai_message_data,
            'emotion_analysis': emotion_data
        })
        
        logger.info(f"Sent AI response to {username}")
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        emit('error', {'error': 'Failed to process message'})

@socketio.on('get_history')
def handle_get_history(data):
    """Handle request for message history."""
    try:
        # Check if user is authenticated
        if request.sid not in active_connections:
            emit('error', {'error': 'Not authenticated'})
            return
        
        connection_info = active_connections[request.sid]
        user_id = connection_info.get('user_id')
        
        # Get message history from cache
        if redis_client:
            try:
                cache_key = f"user_messages:{user_id}"
                messages = redis_client.lrange(cache_key, 0, -1)
                
                history = []
                for msg in messages:
                    try:
                        history.append(json.loads(msg))
                    except json.JSONDecodeError:
                        continue
                
                emit('message_history', {
                    'messages': history,
                    'count': len(history)
                })
                
            except Exception as e:
                logger.error(f"Error retrieving history: {e}")
                emit('message_history', {
                    'messages': [],
                    'count': 0
                })
        else:
            emit('message_history', {
                'messages': [],
                'count': 0
            })
        
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        emit('error', {'error': 'Failed to retrieve history'})

@socketio.on('typing_start')
def handle_typing_start():
    """Handle typing indicator start."""
    try:
        if request.sid in active_connections:
            user_id = active_connections[request.sid].get('user_id')
            username = active_connections[request.sid].get('username')
            
            emit('user_typing', {
                'user_id': user_id,
                'username': username,
                'typing': True
            }, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Typing indicator error: {e}")

@socketio.on('typing_stop')
def handle_typing_stop():
    """Handle typing indicator stop."""
    try:
        if request.sid in active_connections:
            user_id = active_connections[request.sid].get('user_id')
            username = active_connections[request.sid].get('username')
            
            emit('user_typing', {
                'user_id': user_id,
                'username': username,
                'typing': False
            }, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Typing indicator error: {e}")

@socketio.on('ping')
def handle_ping():
    """Handle ping for connection health check."""
    emit('pong', {'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/websocket/status', methods=['GET'])
@metrics.counter('websocket_status_requests', 'Number of WebSocket status requests')
def get_websocket_status():
    """Get WebSocket service status."""
    try:
        status = {
            'service': 'websocket-service',
            'status': 'operational',
            'active_connections': len(active_connections),
            'redis_available': redis_client is not None,
            'timestamp': datetime.utcnow().isoformat(),
            'capabilities': [
                'real-time messaging',
                'emotion analysis',
                'AI responses',
                'message history',
                'typing indicators'
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
    socketio.run(app, host='0.0.0.0', port=8006, debug=False) 