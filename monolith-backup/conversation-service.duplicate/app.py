"""
Conversation Service - Handles conversation management and chat history for EmotiBot microservices.
Integrates with Auth, Emotion, and AI services to provide comprehensive conversation tracking.
"""

from flask import Flask, request, jsonify
import logging
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from prometheus_flask_exporter import PrometheusMetrics
import redis
import json

# Add shared libs to path
sys.path.append('/app/shared-libs')
from service_client import get_service_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
metrics = PrometheusMetrics(app)

# Database setup
DATABASE_URL = os.environ.get('CONVERSATION_DATABASE_URL', 'postgresql://conv_user:conv_pass@conversation-db:5432/conversationdb')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
auth_client = get_service_client('auth-service', 'conversation-service')
emotion_client = get_service_client('emotion-service', 'conversation-service')

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=True)
    emotion_data = Column(JSON, nullable=True)
    emotion = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    conversation_type = Column(String, default='chat')  # chat, analysis, feedback
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'bot_response': self.bot_response,
            'emotion_data': self.emotion_data,
            'emotion': self.emotion,
            'confidence': self.confidence,
            'conversation_type': self.conversation_type,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ConversationInsight(Base):
    __tablename__ = "conversation_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    insight_type = Column(String, nullable=False)  # mood_trend, emotion_pattern, conversation_summary
    insight_data = Column(JSON, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'insight_type': self.insight_type,
            'insight_data': self.insight_data,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None
        }

# Create tables
Base.metadata.create_all(bind=engine)

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

class ConversationService:
    """Service for managing conversations and generating insights."""
    
    @staticmethod
    def save_conversation(user_id: int, message: str, bot_response: str = None, emotion_data: dict = None) -> dict:
        """Save a conversation with emotion analysis."""
        db = SessionLocal()
        try:
            conversation = Conversation(
                user_id=user_id,
                message=message,
                bot_response=bot_response,
                emotion_data=emotion_data,
                emotion=emotion_data.get('emotion') if emotion_data else None,
                confidence=emotion_data.get('confidence') if emotion_data else None,
                conversation_type='chat'
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"Saved conversation for user {user_id}")
            return conversation.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save conversation: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_user_conversations(user_id: int, limit: int = 50, offset: int = 0) -> list:
        """Get user's conversation history."""
        # Check cache first
        cache_key = f"conversations:{user_id}:{limit}:{offset}"
        if redis_client:
            cached_conversations = redis_client.get(cache_key)
            if cached_conversations:
                logger.info(f"Returning cached conversations for user {user_id}")
                return json.loads(cached_conversations)
        
        db = SessionLocal()
        try:
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(
                Conversation.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            result = [conv.to_dict() for conv in conversations]
            
            # Cache the result
            if redis_client:
                redis_client.setex(cache_key, 300, json.dumps(result))  # Cache for 5 minutes
            
            return result
            
        finally:
            db.close()
    
    @staticmethod
    def get_emotion_analytics(user_id: int, days: int = 7) -> dict:
        """Get emotion analytics for a user over specified days."""
        db = SessionLocal()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date,
                Conversation.emotion.isnot(None)
            ).all()
            
            if not conversations:
                return {
                    'total_conversations': 0,
                    'emotion_distribution': {},
                    'average_confidence': 0.0,
                    'most_common_emotion': None,
                    'trend': 'no_data'
                }
            
            # Analyze emotions
            emotions = [conv.emotion for conv in conversations]
            confidences = [conv.confidence for conv in conversations if conv.confidence]
            
            emotion_counts = {}
            for emotion in emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Calculate distribution percentages
            total = len(emotions)
            emotion_distribution = {
                emotion: round((count / total) * 100, 1) 
                for emotion, count in emotion_counts.items()
            }
            
            most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else None
            average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
            
            # Simple trend analysis (compare first half vs second half)
            mid_point = len(conversations) // 2
            if mid_point > 0:
                first_half_emotions = [conv.emotion for conv in conversations[mid_point:]]
                second_half_emotions = [conv.emotion for conv in conversations[:mid_point]]
                
                # Count positive emotions (happiness, joy, excitement)
                positive_emotions = {'happiness', 'joy', 'excitement', 'surprise'}
                first_positive = sum(1 for e in first_half_emotions if e in positive_emotions)
                second_positive = sum(1 for e in second_half_emotions if e in positive_emotions)
                
                if second_positive > first_positive:
                    trend = 'improving'
                elif second_positive < first_positive:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient_data'
            
            return {
                'total_conversations': total,
                'emotion_distribution': emotion_distribution,
                'average_confidence': average_confidence,
                'most_common_emotion': most_common_emotion,
                'trend': trend,
                'analysis_period_days': days
            }
            
        finally:
            db.close()
    
    @staticmethod
    def generate_conversation_summary(user_id: int, limit: int = 10) -> dict:
        """Generate a summary of recent conversations."""
        conversations = ConversationService.get_user_conversations(user_id, limit)
        
        if not conversations:
            return {
                'summary': 'No recent conversations to analyze.',
                'total_messages': 0,
                'time_period': 'N/A'
            }
        
        total_messages = len(conversations)
        recent_emotions = [conv['emotion'] for conv in conversations if conv['emotion']]
        recent_messages = [conv['message'][:100] + '...' if len(conv['message']) > 100 else conv['message'] 
                          for conv in conversations[:5]]  # Get first 5 messages
        
        # Calculate time period
        if conversations:
            oldest = datetime.fromisoformat(conversations[-1]['created_at'].replace('Z', '+00:00'))
            newest = datetime.fromisoformat(conversations[0]['created_at'].replace('Z', '+00:00'))
            time_period = f"{(newest - oldest).days} days"
        else:
            time_period = 'N/A'
        
        # Generate simple summary
        emotion_summary = ""
        if recent_emotions:
            emotion_counts = {}
            for emotion in recent_emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            emotion_summary = f"You've been feeling mostly {dominant_emotion} lately. "
        
        summary = f"In your last {total_messages} conversations over {time_period}, {emotion_summary}"
        summary += f"Your recent topics included discussions about various subjects that showed your emotional range."
        
        return {
            'summary': summary,
            'total_messages': total_messages,
            'time_period': time_period,
            'recent_emotions': recent_emotions[:5],
            'sample_messages': recent_messages
        }

@app.route('/health', methods=['GET'])
@metrics.counter('health_checks', 'Health check requests')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'service': 'conversation-service',
        'status': 'healthy',
        'version': '1.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/conversations', methods=['POST'])
@metrics.counter('conversation_save_requests', 'Conversation save requests')
def save_conversation():
    """Save a new conversation."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    message = data.get('message', '').strip()
    bot_response = data.get('bot_response', '').strip()
    emotion_data = data.get('emotion_data', {})
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        conversation = ConversationService.save_conversation(
            user_id=user['id'],
            message=message,
            bot_response=bot_response,
            emotion_data=emotion_data
        )
        
        # Invalidate cache for this user
        if redis_client:
            pattern = f"conversations:{user['id']}:*"
            for key in redis_client.scan_iter(match=pattern):
                redis_client.delete(key)
        
        logger.info(f"Saved conversation for user {user['username']}")
        return jsonify(conversation), 201
        
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        return jsonify({'error': 'Failed to save conversation'}), 500

@app.route('/api/conversations/history', methods=['GET'])
@metrics.counter('conversation_history_requests', 'Conversation history requests')
def get_conversation_history():
    """Get user's conversation history."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
    offset = max(int(request.args.get('offset', 0)), 0)
    
    try:
        conversations = ConversationService.get_user_conversations(
            user_id=user['id'],
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'conversations': conversations,
            'user_id': user['id'],
            'limit': limit,
            'offset': offset,
            'count': len(conversations)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return jsonify({'error': 'Failed to retrieve conversations'}), 500

@app.route('/api/conversations/analytics', methods=['GET'])
@metrics.counter('conversation_analytics_requests', 'Conversation analytics requests')
def get_conversation_analytics():
    """Get conversation analytics and emotion insights."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    days = min(int(request.args.get('days', 7)), 30)  # Max 30 days
    
    try:
        analytics = ConversationService.get_emotion_analytics(
            user_id=user['id'],
            days=days
        )
        
        return jsonify({
            'user_id': user['id'],
            'analytics': analytics
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500

@app.route('/api/conversations/summary', methods=['GET'])
@metrics.counter('conversation_summary_requests', 'Conversation summary requests')
def get_conversation_summary():
    """Get conversation summary."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    limit = min(int(request.args.get('limit', 10)), 50)
    
    try:
        summary = ConversationService.generate_conversation_summary(
            user_id=user['id'],
            limit=limit
        )
        
        return jsonify({
            'user_id': user['id'],
            'summary': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return jsonify({'error': 'Failed to generate summary'}), 500

@app.route('/api/conversations/search', methods=['GET'])
@metrics.counter('conversation_search_requests', 'Conversation search requests')
def search_conversations():
    """Search conversations by keyword or emotion."""
    user = verify_user_token()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    query = request.args.get('q', '').strip()
    emotion = request.args.get('emotion', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)
    
    if not query and not emotion:
        return jsonify({'error': 'Search query or emotion filter required'}), 400
    
    db = SessionLocal()
    try:
        conversations_query = db.query(Conversation).filter(
            Conversation.user_id == user['id']
        )
        
        if query:
            conversations_query = conversations_query.filter(
                Conversation.message.contains(query)
            )
        
        if emotion:
            conversations_query = conversations_query.filter(
                Conversation.emotion == emotion
            )
        
        conversations = conversations_query.order_by(
            Conversation.created_at.desc()
        ).limit(limit).all()
        
        result = [conv.to_dict() for conv in conversations]
        
        return jsonify({
            'conversations': result,
            'query': query,
            'emotion': emotion,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return jsonify({'error': 'Search failed'}), 500
    finally:
        db.close()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Conversation Service...")
    app.run(host='0.0.0.0', port=8004, debug=False)