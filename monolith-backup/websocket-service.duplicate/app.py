"""
WebSocket Service - Handles real-time communication for EmotiBot microservices.
Provides live chat capabilities with emotion detection and AI response integration.
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging
import os
import sys
import asyncio
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
import redis
import json
import jwt
import uuid

# Add shared libs to path
sys.path.append('/app/shared-libs')
from service_client import get_service_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')

# Configure SocketIO with CORS
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

# Prometheus metrics
metrics = PrometheusMetrics(app)

# Redis setup for session management
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
auth_client = get_service_client('auth-service', 'websocket-service')
emotion_client = get_service_client('emotion-service', 'websocket-service')
ai_client = get_service_client('ai-service', 'websocket-service')
conversation_client = get_service_client('conversation-service', 'websocket-service')

# Track active connections
active_connections = {}
user_rooms = {}

class WebSocketService:
    """Service for managing real-time WebSocket connections and chat."""
    
    @staticmethod
    def authenticate_user(token: str) -> dict:
        """Authenticate user token and return user data."""
        try:
            response = auth_client.post('/api/auth/verify', {'token': token})
            if response.status_code == 200:
                return response.json()['user']
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    @staticmethod
    def store_session(session_id: str, user_data: dict):
        """Store user session in Redis."""
        if redis_client:
            try:
                session_data = {
                    'user_id': user_data['id'],
                    'username': user_data['username'],
                    'connected_at': datetime.utcnow().isoformat(),
                    'session_id': session_id
                }
                redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))
                redis_client.setex(f"user_session:{user_data['id']}", 3600, session_id)
            except Exception as e:
                logger.error(f"Failed to store session: {e}")
    
    @staticmethod
    def get_session(session_id: str) -> dict:
        """Retrieve user session from Redis."""
        if redis_client:
            try:
                session_data = redis_client.get(f"session:{session_id}")
                if session_data:
                    return json.loads(session_data)
            except Exception as e:
                logger.error(f"Failed to get session: {e}")
        return None
    
    @staticmethod
    def remove_session(session_id: str):
        """Remove user session from Redis."""
        if redis_client:
            try:
                session_data = WebSocketService.get_session(session_id)
                if session_data:
                    redis_client.delete(f"session:{session_id}")
                    redis_client.delete(f"user_session:{session_data['user_id']}")
            except Exception as e:
                logger.error(f"Failed to remove session: {e}")
    
    @staticmethod
    async def process_message(message: str, user_data: dict) -> dict:
        """Process incoming message with emotion detection and AI response."""
        try:
            # Step 1: Detect emotion
            emotion_response = emotion_client.post('/api/emotion/detect', {
                'text': message
            }, headers={'Authorization': f"Bearer {user_data.get('token', '')}"})
            
            emotion_data = {}
            if emotion_response.status_code == 200:
                emotion_data = emotion_response.json()
            else:
                logger.warning(f"Emotion detection failed: {emotion_response.status_code}")
                emotion_data = {'emotion': 'neutral', 'confidence': 0.5, 'scores': {}}
            
            # Step 2: Get conversation history for context
            history_response = conversation_client.get('/api/conversations/history?limit=5',
                headers={'Authorization': f"Bearer {user_data.get('token', '')}"})
            
            conversation_history = []
            if history_response.status_code == 200:
                conversation_history = history_response.json().get('conversations', [])
            
            # Step 3: Generate AI response
            ai_response = ai_client.post('/api/ai/generate', {
                'message': message,
                'emotion': emotion_data.get('emotion', 'neutral'),
                'confidence': emotion_data.get('confidence', 0.5),
                'conversation_history': conversation_history
            }, headers={'Authorization': f"Bearer {user_data.get('token', '')}"})
            
            ai_response_text = "I understand what you're saying. How can I help you further?"
            if ai_response.status_code == 200:
                ai_response_text = ai_response.json().get('ai_response', ai_response_text)
            else:
                logger.warning(f"AI response generation failed: {ai_response.status_code}")
            
            # Step 4: Save conversation
            conversation_client.post('/api/conversations', {
                'message': message,
                'bot_response': ai_response_text,
                'emotion_data': emotion_data
            }, headers={'Authorization': f"Bearer {user_data.get('token', '')}"})
            
            return {
                'user_message': message,
                'bot_response': ai_response_text,
                'emotion_data': emotion_data,
                'timestamp': datetime.utcnow().isoformat(),
                'conversation_id': str(uuid.uuid4())
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'user_message': message,
                'bot_response': "I'm having trouble processing your message right now. Please try again.",
                'emotion_data': {'emotion': 'neutral', 'confidence': 0.5},
                'timestamp': datetime.utcnow().isoformat(),
                'error': True
            }

# WebSocket event handlers
@socketio.on('connect')
@metrics.counter('websocket_connections', 'WebSocket connection attempts')
def handle_connect(auth=None):
    """Handle new WebSocket connection."""
    logger.info(f"New WebSocket connection attempt from {request.sid}")
    
    # Don't authenticate on connect, wait for authentication event
    active_connections[request.sid] = {
        'connected_at': datetime.utcnow().isoformat(),
        'authenticated': False,
        'user_data': None
    }
    
    emit('connection_established', {
        'session_id': request.sid,
        'status': 'connected',
        'message': 'Connected to EmotiBot. Please authenticate to start chatting.',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    logger.info(f"WebSocket connection established: {request.sid}")

@socketio.on('authenticate')
@metrics.counter('websocket_auth_attempts', 'WebSocket authentication attempts')
def handle_authenticate(data):
    """Handle user authentication."""
    try:
        token = data.get('token')
        if not token:
            emit('auth_failed', {'error': 'Token required'})
            return
        
        user_data = WebSocketService.authenticate_user(token)
        if not user_data:
            emit('auth_failed', {'error': 'Invalid token'})
            return
        
        # Store user data in session
        user_data['token'] = token
        active_connections[request.sid]['authenticated'] = True
        active_connections[request.sid]['user_data'] = user_data
        
        # Join user to their personal room
        room_name = f"user_{user_data['id']}"
        join_room(room_name)
        user_rooms[request.sid] = room_name
        
        # Store session in Redis
        WebSocketService.store_session(request.sid, user_data)
        
        emit('authenticated', {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'session_id': request.sid,
            'message': f"Welcome back, {user_data['username']}! Ready to chat.",
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"User {user_data['username']} authenticated on session {request.sid}")
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        emit('auth_failed', {'error': 'Authentication failed'})

@socketio.on('send_message')
@metrics.counter('websocket_messages', 'WebSocket messages sent')
@metrics.histogram('websocket_message_processing_time', 'WebSocket message processing time')
def handle_message(data):
    """Handle incoming chat message."""
    connection = active_connections.get(request.sid)
    if not connection or not connection.get('authenticated'):
        emit('error', {'message': 'Authentication required'})
        return
    
    user_data = connection['user_data']
    message = data.get('message', '').strip()
    
    if not message:
        emit('error', {'message': 'Message cannot be empty'})
        return
    
    try:
        # Emit acknowledgment that message was received
        emit('message_received', {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'processing'
        })
        
        # Process message asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                WebSocketService.process_message(message, user_data)
            )
        finally:
            loop.close()
        
        # Emit the complete response
        emit('bot_response', {
            'conversation': result,
            'user': {
                'id': user_data['id'],
                'username': user_data['username']
            },
            'session_id': request.sid
        })
        
        logger.info(f"Processed message for user {user_data['username']}: {message[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        emit('error', {
            'message': 'Failed to process your message. Please try again.',
            'timestamp': datetime.utcnow().isoformat()
        })

@socketio.on('get_conversation_history')
@metrics.counter('websocket_history_requests', 'WebSocket conversation history requests')
def handle_get_history(data):
    """Handle request for conversation history."""
    connection = active_connections.get(request.sid)
    if not connection or not connection.get('authenticated'):
        emit('error', {'message': 'Authentication required'})
        return
    
    user_data = connection['user_data']
    limit = min(data.get('limit', 20), 50)  # Max 50
    
    try:
        response = conversation_client.get(
            f'/api/conversations/history?limit={limit}',
            headers={'Authorization': f"Bearer {user_data['token']}"}
        )
        
        if response.status_code == 200:
            history_data = response.json()
            emit('conversation_history', {
                'conversations': history_data.get('conversations', []),
                'count': history_data.get('count', 0),
                'user_id': user_data['id']
            })
        else:
            emit('error', {'message': 'Failed to retrieve conversation history'})
            
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        emit('error', {'message': 'Failed to retrieve conversation history'})

@socketio.on('get_mood_insights')
@metrics.counter('websocket_insights_requests', 'WebSocket mood insights requests')
def handle_get_insights(data):
    """Handle request for mood insights."""
    connection = active_connections.get(request.sid)
    if not connection or not connection.get('authenticated'):
        emit('error', {'message': 'Authentication required'})
        return
    
    user_data = connection['user_data']
    
    try:
        # Get conversation history first
        history_response = conversation_client.get(
            '/api/conversations/history?limit=20',
            headers={'Authorization': f"Bearer {user_data['token']}"}
        )
        
        conversation_history = []
        if history_response.status_code == 200:
            conversation_history = history_response.json().get('conversations', [])
        
        # Get AI insights
        insights_response = ai_client.post('/api/ai/insights', {
            'conversation_history': conversation_history
        }, headers={'Authorization': f"Bearer {user_data['token']}"})
        
        if insights_response.status_code == 200:
            insights_data = insights_response.json()
            emit('mood_insights', {
                'insights': insights_data.get('insights', ''),
                'conversation_count': insights_data.get('conversation_count', 0),
                'user_id': user_data['id']
            })
        else:
            emit('error', {'message': 'Failed to generate mood insights'})
            
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        emit('error', {'message': 'Failed to generate mood insights'})

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator."""
    connection = active_connections.get(request.sid)
    if not connection or not connection.get('authenticated'):
        return
    
    user_data = connection['user_data']
    room_name = user_rooms.get(request.sid)
    
    if room_name:
        emit('user_typing', {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'typing': data.get('typing', False)
        }, room=room_name, include_self=False)

@socketio.on('disconnect')
@metrics.counter('websocket_disconnections', 'WebSocket disconnections')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    connection = active_connections.get(request.sid)
    if connection:
        user_data = connection.get('user_data')
        if user_data:
            logger.info(f"User {user_data['username']} disconnected from session {request.sid}")
        else:
            logger.info(f"Unauthenticated session {request.sid} disconnected")
        
        # Clean up session
        WebSocketService.remove_session(request.sid)
        
        # Leave room
        room_name = user_rooms.get(request.sid)
        if room_name:
            leave_room(room_name)
            del user_rooms[request.sid]
        
        # Remove from active connections
        del active_connections[request.sid]

# HTTP endpoints for health checks and service info
@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Health check requests')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'service': 'websocket-service',
        'status': 'healthy',
        'version': '1.0',
        'active_connections': len(active_connections),
        'authenticated_users': len([c for c in active_connections.values() if c.get('authenticated')]),
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/websocket/stats', methods=['GET'])
@metrics.counter('websocket_stats_requests', 'WebSocket stats requests')
def get_websocket_stats():
    """Get WebSocket service statistics."""
    total_connections = len(active_connections)
    authenticated_connections = len([c for c in active_connections.values() if c.get('authenticated')])
    
    stats = {
        'service': 'websocket-service',
        'total_connections': total_connections,
        'authenticated_connections': authenticated_connections,
        'unauthenticated_connections': total_connections - authenticated_connections,
        'active_rooms': len(user_rooms),
        'uptime': datetime.utcnow().isoformat(),
        'redis_connected': redis_client is not None
    }
    
    return jsonify(stats), 200

@app.route('/api/websocket/connections', methods=['GET'])
@metrics.counter('websocket_connections_requests', 'WebSocket connections list requests')
def get_active_connections():
    """Get list of active connections (admin endpoint)."""
    # This would typically require admin authentication
    connections_info = []
    
    for session_id, connection in active_connections.items():
        connection_info = {
            'session_id': session_id,
            'connected_at': connection['connected_at'],
            'authenticated': connection['authenticated']
        }
        
        if connection['authenticated'] and connection['user_data']:
            connection_info['user'] = {
                'id': connection['user_data']['id'],
                'username': connection['user_data']['username']
            }
        
        connections_info.append(connection_info)
    
    return jsonify({
        'connections': connections_info,
        'total_count': len(connections_info)
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting WebSocket Service...")
    socketio.run(app, host='0.0.0.0', port=8006, debug=False)