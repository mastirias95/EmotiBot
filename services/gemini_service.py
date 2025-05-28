import os
import logging
import requests
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for integrating with Google's Gemini LLM API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Google AI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        # Try different model endpoints
        self.model_endpoints = [
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        ]
        self.base_url = self.model_endpoints[0]  # Default to first endpoint
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Gemini API key not found. Gemini features will be disabled.")
            logger.debug(f"Checked environment variable GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY') is not None}")
        else:
            logger.info("Gemini service initialized successfully.")
            logger.debug(f"API key loaded: {self.api_key[:10]}..." if self.api_key else "No API key")
    
    def generate_emotional_response(self, user_message: str, detected_emotion: str, 
                                  confidence: float, conversation_history: list = None) -> str:
        """
        Generate an emotionally intelligent response using Gemini.
        
        Args:
            user_message: The user's message
            detected_emotion: The detected emotion (happy, sad, angry, etc.)
            confidence: Confidence score of emotion detection
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response string
        """
        if not self.enabled:
            return self._get_fallback_response(detected_emotion)
        
        try:
            prompt = self._build_emotional_prompt(user_message, detected_emotion, confidence, conversation_history)
            response = self._call_gemini_api(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            return self._get_fallback_response(detected_emotion)
    
    def _build_emotional_prompt(self, user_message: str, emotion: str, confidence: float, 
                               conversation_history: list = None) -> str:
        """Build a prompt for emotional response generation."""
        
        context = ""
        if conversation_history:
            context = "Previous conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                context += f"User: {msg.get('user_message', '')}\nBot: {msg.get('bot_message', '')}\n"
            context += "\n"
        
        prompt = f"""You are EmotiBot, an empathetic AI companion specialized in emotional support and understanding. 

{context}Current situation:
- User's message: "{user_message}"
- Detected emotion: {emotion} (confidence: {confidence:.2f})

Guidelines for your response:
1. Be empathetic and understanding
2. Acknowledge the user's emotional state
3. Provide appropriate emotional support
4. Ask follow-up questions to encourage conversation
5. Keep responses conversational and supportive (2-3 sentences max)
6. Use appropriate emojis sparingly
7. If the emotion is negative, offer gentle support and coping suggestions
8. If the emotion is positive, celebrate with them and encourage sharing

Respond as EmotiBot with emotional intelligence and care:"""

        return prompt
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Make API call to Gemini."""
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 150,
            }
        }
        
        # Try different endpoints
        last_error = None
        for endpoint in self.model_endpoints:
            try:
                url = f"{endpoint}?key={self.api_key}"
                logger.debug(f"Trying Gemini API endpoint: {endpoint}")
                
                response = requests.post(url, headers=headers, json=data, timeout=10)
                
                # Log the response status and content for debugging
                logger.debug(f"API Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.debug(f"API Response Content: {response.text}")
                
                response.raise_for_status()
                
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    logger.info(f"Successfully got response from {endpoint}")
                    return content.strip()
                else:
                    logger.warning(f"No candidates in response from {endpoint}: {result}")
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to call {endpoint}: {str(e)}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Error processing response from {endpoint}: {str(e)}")
                last_error = e
                continue
        
        # If all endpoints failed, raise the last error
        if last_error:
            raise last_error
        else:
            raise Exception("No response generated by Gemini from any endpoint")
    
    def _get_fallback_response(self, emotion: str) -> str:
        """Get fallback response when Gemini is not available."""
        fallback_responses = {
            'happy': "I'm glad you're feeling happy! 😊 Your positive energy is wonderful!",
            'sad': "I'm here to listen if you want to talk about what's making you sad. 😢 Sometimes sharing helps.",
            'angry': "I understand you're feeling frustrated. Let's work through this together. 😤 Take a deep breath.",
            'surprised': "That is quite surprising! Tell me more about it! 😮 I'm curious to hear more.",
            'fearful': "It's okay to feel scared. You're not alone in this. 😨 What's worrying you?",
            'neutral': "I understand. Please tell me more about how you're feeling. 😐 I'm here to listen."
        }
        return fallback_responses.get(emotion, "I understand how you feel. Tell me more about it.")
    
    def generate_mood_insights(self, conversation_history: list) -> str:
        """Generate insights about user's mood patterns."""
        if not self.enabled or not conversation_history:
            return "Mood insights require more conversation data."
        
        try:
            emotions = [conv.get('detected_emotion', 'neutral') for conv in conversation_history[-10:]]
            emotion_summary = ", ".join(emotions)
            
            prompt = f"""Analyze the following sequence of emotions from a user's recent conversations: {emotion_summary}

Provide a brief, supportive insight about their emotional patterns and suggest one positive coping strategy or encouragement. Keep it under 100 words and be empathetic."""

            return self._call_gemini_api(prompt)
        except Exception as e:
            logger.error(f"Error generating mood insights: {str(e)}")
            return "I notice you've been sharing your feelings with me. That's a great step toward emotional awareness!" 