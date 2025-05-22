from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

class EmotionService:
    """Service for detecting emotions in text."""
    
    # Emotions mapped to sentiment polarity and subjectivity ranges
    EMOTIONS = {
        'happy': {'polarity': (0.5, 1.0), 'subjectivity': (0.4, 1.0)},
        'sad': {'polarity': (-1.0, -0.3), 'subjectivity': (0.4, 1.0)},
        'angry': {'polarity': (-1.0, -0.6), 'subjectivity': (0.6, 1.0)},
        'surprised': {'polarity': (0.3, 1.0), 'subjectivity': (0.7, 1.0)},
        'fearful': {'polarity': (-0.8, -0.4), 'subjectivity': (0.5, 1.0)},
        'neutral': {'polarity': (-0.2, 0.2), 'subjectivity': (0.0, 0.4)}
    }
    
    @classmethod
    def detect_emotion(cls, text):
        """
        Detect emotion from text using TextBlob sentiment analysis.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: Detected emotion with confidence score
        """
        if not text:
            return {'emotion': 'neutral', 'confidence': 1.0}
        
        try:
            # Analyze sentiment
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            logger.debug(f"Text: '{text}' - Polarity: {polarity}, Subjectivity: {subjectivity}")
            
            # Find the matching emotion
            detected_emotion = cls._match_emotion(polarity, subjectivity)
            
            # Calculate a simple confidence score
            confidence = cls._calculate_confidence(detected_emotion, polarity, subjectivity)
            
            return {
                'emotion': detected_emotion,
                'confidence': confidence,
                'polarity': polarity,
                'subjectivity': subjectivity
            }
            
        except Exception as e:
            logger.error(f"Error detecting emotion: {str(e)}")
            return {'emotion': 'neutral', 'confidence': 0.5}
    
    @classmethod
    def _match_emotion(cls, polarity, subjectivity):
        """Match sentiment values to an emotion."""
        
        # Default to neutral if nothing matches
        matched_emotion = 'neutral'
        
        for emotion, ranges in cls.EMOTIONS.items():
            pol_range = ranges['polarity']
            subj_range = ranges['subjectivity']
            
            if (pol_range[0] <= polarity <= pol_range[1] and 
                subj_range[0] <= subjectivity <= subj_range[1]):
                matched_emotion = emotion
                break
        
        return matched_emotion
    
    @classmethod
    def _calculate_confidence(cls, emotion, polarity, subjectivity):
        """Calculate a confidence score for the detected emotion."""
        if emotion == 'neutral':
            # For neutral, confidence decreases as we move away from center
            return 1.0 - abs(polarity) * 2
        else:
            # For other emotions, confidence increases with subjectivity
            # and with distance from neutral polarity
            return min(abs(polarity) * 1.5, subjectivity * 1.3, 1.0) 