"""
Conversation Service - Handles chat history, conversation management, and message processing.
Integrates with Auth, Emotion, and AI services for complete conversation flow.
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import logging
import os
import requests
import json
from prometheus_flask_exporter import PrometheusMetrics
import redis
import sys

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

# Database setup
DATABASE_URL = os.environ.get('CONVERSATION_DATABASE_URL', 'postgresql://conv_user:conv_pass@conversation-db:5432/conversationdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Service URLs
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8002')
EMOTION_SERVICE_URL = os.environ.get('EMOTION_SERVICE_URL', 'http://emotion-service:8003')
AI_SERVICE_URL = os.environ.get('AI_SERVICE_URL', 'http://ai-service:8005')
SERVICE_SECRET = os.environ.get('SERVICE_SECRET', 'default-service-secret')

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
        queue_client = get_queue_client('conversation-service')
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
        queue_client = None
else:
    queue_client = None
    logger.info("RabbitMQ not available - running in standalone mode")

# Database Models
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for archived
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': bool(self.is_active),
            'message_count': len(self.messages)
        }

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    sender_type = Column(String(20), nullable=False)  # 'user' or 'bot'
    emotion = Column(String(50), nullable=True)
    emotion_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'content': self.content,
            'sender_type': self.sender_type,
            'emotion': self.emotion,
            'emotion_confidence': self.emotion_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
                'X-Service-Name': 'conversation-service'
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
                'X-Service-Name': 'conversation-service'
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

def generate_ai_response(message, emotion_data=None):
    """Generate AI response using AI Service."""
    try:
        payload = {
            'message': message,
            'context': 'conversation'
        }
        if emotion_data:
            payload['emotion'] = emotion_data.get('emotion')
            payload['confidence'] = emotion_data.get('confidence')
        
        response = requests.post(
            f"{AI_SERVICE_URL}/api/ai/generate",
            headers={
                'Content-Type': 'application/json',
                'X-Service-Name': 'conversation-service'
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

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Number of health check requests')
def health_check():
    """Health check endpoint."""
    queue_healthy = queue_client.ensure_connection() if queue_client else False
    
    return jsonify({
        'service': 'conversation-service',
        'status': 'healthy',
        'queue_connection': queue_healthy,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/conversations', methods=['GET'])
@metrics.counter('conversation_list_requests', 'Number of conversation list requests')
def get_conversations():
    """Get user's conversations."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == 1
        ).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify({
            'conversations': [conv.to_dict() for conv in conversations]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({'error': 'Failed to fetch conversations'}), 500
    finally:
        db.close()

@app.route('/api/conversations', methods=['POST'])
@metrics.counter('conversation_create_requests', 'Number of conversation creation requests')
def create_conversation():
    """Create a new conversation."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    data = request.get_json()
    title = data.get('title', 'New Conversation')
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        conversation = Conversation(
            user_id=user_id,
            title=title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # Publish conversation creation event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_conversation_created(conversation.to_dict())
                logger.info(f"Published conversation creation event for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to publish conversation creation event: {e}")
        
        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        
        return jsonify({
            'message': 'Conversation created successfully',
            'conversation': conversation.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}")
        return jsonify({'error': 'Failed to create conversation'}), 500
    finally:
        db.close()

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@metrics.counter('message_list_requests', 'Number of message list requests')
def get_messages(conversation_id):
    """Get messages for a conversation."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        return jsonify({
            'conversation': conversation.to_dict(),
            'messages': [msg.to_dict() for msg in messages]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return jsonify({'error': 'Failed to fetch messages'}), 500
    finally:
        db.close()

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@metrics.counter('message_create_requests', 'Number of message creation requests')
def send_message(conversation_id):
    """Send a message and get AI response."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    data = request.get_json()
    content = data.get('message', '').strip()
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Analyze emotion
        emotion_data = analyze_emotion(content)
        
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=content,
            sender_type='user',
            emotion=emotion_data.get('emotion') if emotion_data else None,
            emotion_confidence=emotion_data.get('confidence') if emotion_data else None
        )
        db.add(user_message)
        
        # Generate AI response
        ai_response_data = generate_ai_response(content, emotion_data)
        ai_response_content = ai_response_data.get('response', 'I apologize, but I am unable to respond at the moment.') if ai_response_data else 'I apologize, but I am unable to respond at the moment.'
        
        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=ai_response_content,
            sender_type='bot'
        )
        db.add(ai_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Publish message sent event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_message_sent({
                    'conversation_id': conversation_id,
                    'user_id': user_id,
                    'user_message': user_message.to_dict(),
                    'ai_message': ai_message.to_dict(),
                    'emotion_data': emotion_data,
                    'timestamp': datetime.utcnow().isoformat()
                })
                logger.info(f"Published message sent event for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to publish message sent event: {e}")
        
        logger.info(f"Message sent in conversation {conversation_id} by user {user_id}")
        
        return jsonify({
            'message': 'Message sent successfully',
            'user_message': user_message.to_dict(),
            'ai_response': ai_message.to_dict(),
            'emotion_analysis': emotion_data
        }), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error sending message: {e}")
        return jsonify({'error': 'Failed to send message'}), 500
    finally:
        db.close()

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@metrics.counter('conversation_delete_requests', 'Number of conversation deletion requests')
def delete_conversation(conversation_id):
    """Delete a conversation (soft delete)."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        conversation.is_active = 0
        db.commit()
        
        # Publish conversation deletion event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_event('conversation.deleted', {
                    'conversation_id': conversation_id,
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                logger.info(f"Published conversation deletion event for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to publish conversation deletion event: {e}")
        
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")
        
        return jsonify({'message': 'Conversation deleted successfully'}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({'error': 'Failed to delete conversation'}), 500
    finally:
        db.close()

@app.route('/api/conversations/insights', methods=['GET'])
@metrics.counter('insights_requests', 'Number of conversation insights requests')
def get_conversation_insights():
    """Get conversation insights and analytics."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = auth_header.split(' ')[1]
    is_valid, user_data = verify_user_token(token)
    
    if not is_valid:
        return jsonify({'error': 'Invalid token'}), 401
    
    user_id = user_data.get('user_id')
    
    db = SessionLocal()
    try:
        # Get conversation statistics
        total_conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == 1
        ).count()
        
        total_messages = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == 1
        ).count()
        
        # Get emotion distribution
        emotion_stats = db.query(
            Message.emotion,
            db.func.count(Message.id).label('count')
        ).join(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == 1,
            Message.emotion.isnot(None)
        ).group_by(Message.emotion).all()
        
        # Get recent activity
        recent_messages = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_active == 1
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        insights = {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'emotion_distribution': {stat.emotion: stat.count for stat in emotion_stats},
            'recent_activity': [msg.to_dict() for msg in recent_messages],
            'average_messages_per_conversation': total_messages / total_conversations if total_conversations > 0 else 0
        }
        
        # Publish conversation insights event to RabbitMQ
        if queue_client:
            try:
                queue_client.publish_conversation_updated({
                    'user_id': user_id,
                    'insights': insights,
                    'timestamp': datetime.utcnow().isoformat()
                })
                logger.info(f"Published conversation insights event for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to publish conversation insights event: {e}")
        
        return jsonify(insights), 200
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return jsonify({'error': 'Failed to fetch insights'}), 500
    finally:
        db.close()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8004, debug=False) 