from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketService:
    def __init__(self, app=None):
        self.socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
        self.active_users = {}
        self.setup_handlers()

    def init_app(self, app):
        """Initialize with Flask app if not provided in constructor."""
        self.socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
        self.setup_handlers()

    def setup_handlers(self):
        """Set up WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            user_id = get_user_id_from_request()
            if not user_id:
                # For demo purposes, create a demo user ID
                user_id = f"demo_user_{request.sid[:8]}"
                logger.info(f"Creating demo user: {user_id}")
            
            self.active_users[request.sid] = {
                'user_id': user_id,
                'connected_at': datetime.utcnow(),
                'room': str(user_id)
            }
            join_room(str(user_id))
            logger.info(f"Client connected. User ID: {user_id}")
            emit('connection_response', {'status': 'connected', 'user_id': user_id})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            if request.sid in self.active_users:
                user_data = self.active_users.pop(request.sid)
                logger.info(f"Client disconnected. User ID: {user_data['user_id']}")
                leave_room(str(user_data['user_id']))

        @self.socketio.on('analyze_emotion')
        def handle_emotion_analysis(data):
            """Handle real-time emotion analysis requests."""
            if request.sid not in self.active_users:
                emit('error', {'message': 'Unauthorized'})
                return

            text = data.get('text', '')
            if not text:
                emit('error', {'message': 'Text is required'})
                return

            try:
                # Get user data
                user_data = self.active_users[request.sid]
                user_id = user_data['user_id']

                # Get services from app context
                from flask import current_app
                from services.emotion_service import EmotionService
                
                # Analyze emotion
                result = EmotionService.detect_emotion(text)

                # Generate bot response using Gemini
                conversation_history = []
                if hasattr(current_app, 'conversation_service') and not user_id.startswith('demo_user_'):
                    # Only get conversation history for authenticated users
                    conversation_history = current_app.conversation_service.get_user_conversation_history(user_id, limit=5)

                # Generate intelligent response using Gemini
                bot_message = current_app.gemini_service.generate_emotional_response(
                    text, 
                    result['emotion'], 
                    result['confidence'],
                    conversation_history
                )

                # Save the conversation only for authenticated users
                if hasattr(current_app, 'conversation_service') and not user_id.startswith('demo_user_'):
                    current_app.conversation_service.save_conversation(user_id, text, bot_message, result)

                # Emit the response back to the user
                response_data = {
                    'emotion': result['emotion'],
                    'confidence': result['confidence'],
                    'polarity': result.get('polarity', 0),
                    'subjectivity': result.get('subjectivity', 0),
                    'bot_message': bot_message,
                    'timestamp': datetime.utcnow().isoformat()
                }
                emit('emotion_analysis_response', response_data, room=str(user_id))

            except Exception as e:
                logger.error(f"Error in emotion analysis: {str(e)}")
                emit('error', {'message': 'Internal server error'})

        @self.socketio.on('typing')
        def handle_typing(data):
            """Handle typing indicators."""
            if request.sid in self.active_users:
                user_data = self.active_users[request.sid]
                is_typing = data.get('typing', False)
                emit('user_typing', {
                    'user_id': user_data['user_id'],
                    'typing': is_typing
                }, room=str(user_data['user_id']))

        @self.socketio.on('live_emotion_preview')
        def handle_live_emotion_preview(data):
            """Handle real-time emotion preview as user types."""
            if request.sid not in self.active_users:
                logger.warning("Live emotion preview request from unauthorized user")
                return

            text = data.get('text', '').strip()
            if not text or len(text) < 3:  # Only analyze if there's meaningful text
                return

            try:
                from services.emotion_service import EmotionService
                
                # Quick emotion analysis for preview
                result = EmotionService.detect_emotion(text)
                
                # Emit preview data
                preview_data = {
                    'emotion': result['emotion'],
                    'confidence': result['confidence'],
                    'polarity': result.get('polarity', 0),
                    'subjectivity': result.get('subjectivity', 0),
                    'is_preview': True
                }
                
                user_data = self.active_users[request.sid]
                logger.debug(f"Sending emotion preview to user {user_data['user_id']}: {preview_data['emotion']}")
                emit('emotion_preview', preview_data, room=str(user_data['user_id']))

            except Exception as e:
                logger.error(f"Error in live emotion preview: {str(e)}")
                # Don't emit error for preview failures, just log them

        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Handle joining a specific room for private conversations."""
            if request.sid not in self.active_users:
                emit('error', {'message': 'Unauthorized'})
                return
                
            room_name = data.get('room')
            if room_name:
                join_room(room_name)
                user_data = self.active_users[request.sid]
                emit('room_joined', {'room': room_name, 'user_id': user_data['user_id']})

    def get_active_users(self):
        """Get list of currently active users."""
        return list(set(user['user_id'] for user in self.active_users.values()))

def get_user_id_from_request():
    """Extract user ID from request."""
    auth_header = request.args.get('token')
    if not auth_header:
        return None

    try:
        from flask import current_app
        auth_service = current_app.auth_service
        payload = auth_service.decode_token(auth_header)
        return payload.get('sub')
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return None 