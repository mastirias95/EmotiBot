import logging
from models.conversation import Conversation, db
from services.emotion_service import EmotionService

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for handling conversation history and analysis."""
    
    def __init__(self):
        """Initialize the conversation service."""
        pass
    
    def save_conversation(self, user_id, user_message, bot_message, emotion_data):
        """
        Save a conversation record.
        
        Args:
            user_id (str): The ID of the user
            user_message (str): The message from the user
            bot_message (str): The response from the bot
            emotion_data (dict): Emotion analysis results
            
        Returns:
            tuple: (success, message, conversation_data)
        """
        try:
            # Create conversation record
            conversation = Conversation(
                user_id=user_id,
                user_message=user_message,
                bot_message=bot_message,
                detected_emotion=emotion_data['emotion'],
                confidence=emotion_data['confidence'],
                polarity=emotion_data['polarity'],
                subjectivity=emotion_data['subjectivity']
            )
            
            # Save to database
            db.session.add(conversation)
            db.session.commit()
            
            logger.info(f"Saved conversation for user: {user_id}")
            return True, "Conversation saved", conversation.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving conversation: {str(e)}")
            return False, f"Error saving conversation: {str(e)}", None
    
    def get_user_conversation_history(self, user_id, limit=20):
        """
        Get conversation history for a user.
        
        Args:
            user_id (str): The ID of the user
            limit (int): Maximum number of conversations to return
            
        Returns:
            list: List of conversation records
        """
        try:
            conversations = Conversation.query \
                .filter_by(user_id=user_id) \
                .order_by(Conversation.timestamp.desc()) \
                .limit(limit) \
                .all()
            
            return [conversation.to_dict() for conversation in conversations]
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []
    
    def analyze_and_save(self, user_id, user_message, bot_message):
        """
        Analyze a user message and save the conversation with emotion data.
        
        Args:
            user_id (str): The ID of the user
            user_message (str): The message from the user
            bot_message (str): The response from the bot
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            # Analyze emotion
            emotion_data = EmotionService.detect_emotion(user_message)
            
            # Save conversation
            success, message, conversation = self.save_conversation(
                user_id, user_message, bot_message, emotion_data
            )
            
            if not success:
                return False, message, None
            
            return True, "Conversation analyzed and saved", {
                'conversation': conversation,
                'emotion_data': emotion_data
            }
            
        except Exception as e:
            logger.error(f"Error analyzing and saving conversation: {str(e)}")
            return False, f"Error: {str(e)}", None 