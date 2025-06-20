from datetime import datetime
import uuid
from models.user import db

class Conversation(db.Model):
    """Model for storing conversation history."""
    
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_message = db.Column(db.Text, nullable=False)
    detected_emotion = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    polarity = db.Column(db.Float, nullable=False)
    subjectivity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, user_id, user_message, bot_message, detected_emotion, 
                 confidence, polarity, subjectivity, id=None, timestamp=None):
        """
        Initialize a conversation record.
        
        Args:
            user_id (str): The ID of the user who sent the message
            user_message (str): The message sent by the user
            bot_message (str): The response from the bot
            detected_emotion (str): The emotion detected in the user's message
            confidence (float): Confidence level in the emotion detection
            polarity (float): Sentiment polarity score
            subjectivity (float): Sentiment subjectivity score
            id (str, optional): Conversation ID
            timestamp (datetime, optional): Timestamp of the conversation
        """
        self.id = id or str(uuid.uuid4())
        self.user_id = user_id
        self.user_message = user_message
        self.bot_message = bot_message
        self.detected_emotion = detected_emotion
        self.confidence = confidence
        self.polarity = polarity
        self.subjectivity = subjectivity
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """
        Convert conversation to dictionary (for JSON serialization).
        
        Returns:
            dict: Conversation data
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_message': self.user_message,
            'bot_message': self.bot_message,
            'detected_emotion': self.detected_emotion,
            'confidence': self.confidence,
            'polarity': self.polarity,
            'subjectivity': self.subjectivity,
            'timestamp': self.timestamp.isoformat()
        } 