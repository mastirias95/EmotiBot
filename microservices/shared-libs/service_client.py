"""
Shared Service Client Library
Provides standardized methods for inter-service communication in the EmotiBot microservices platform.
"""

import requests
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import jwt

logger = logging.getLogger(__name__)

class ServiceClient:
    """Base class for inter-service communication."""
    
    def __init__(self, service_name: str, service_secret: str = None):
        self.service_name = service_name
        self.service_secret = service_secret or os.environ.get('SERVICE_SECRET', 'default-service-secret')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Service-Name': service_name
        })
    
    def _get_service_token(self) -> str:
        """Generate service-to-service authentication token."""
        payload = {
            'service': self.service_name,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, self.service_secret, algorithm='HS256')
    
    def _make_request(self, method: str, url: str, data: Dict = None, timeout: int = 10) -> Tuple[bool, Dict]:
        """Make HTTP request with service authentication."""
        try:
            headers = {
                'Authorization': f'Bearer {self._get_service_token()}',
                'X-Service-Name': self.service_name
            }
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=timeout)
            else:
                return False, {'error': f'Unsupported HTTP method: {method}'}
            
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {'error': f'HTTP {response.status_code}', 'details': response.text}
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout to {url}")
            return False, {'error': 'Request timeout'}
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {url}")
            return False, {'error': 'Connection error'}
        except Exception as e:
            logger.error(f"Request error to {url}: {e}")
            return False, {'error': str(e)}

class AuthServiceClient(ServiceClient):
    """Client for Auth Service communication."""
    
    def __init__(self, auth_service_url: str):
        super().__init__('auth-service')
        self.base_url = auth_service_url.rstrip('/')
    
    def verify_token(self, token: str) -> Tuple[bool, Dict]:
        """Verify user JWT token."""
        return self._make_request('POST', f"{self.base_url}/api/auth/verify", {'token': token})
    
    def get_user_profile(self, user_id: int) -> Tuple[bool, Dict]:
        """Get user profile by ID."""
        return self._make_request('GET', f"{self.base_url}/api/auth/user/{user_id}")
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, Dict]:
        """Register a new user."""
        data = {
            'username': username,
            'email': email,
            'password': password
        }
        return self._make_request('POST', f"{self.base_url}/api/auth/register", data)
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Dict]:
        """Authenticate user and get token."""
        data = {
            'username': username,
            'password': password
        }
        return self._make_request('POST', f"{self.base_url}/api/auth/login", data)

class EmotionServiceClient(ServiceClient):
    """Client for Emotion Service communication."""
    
    def __init__(self, emotion_service_url: str):
        super().__init__('emotion-service')
        self.base_url = emotion_service_url.rstrip('/')
    
    def detect_emotion(self, text: str) -> Tuple[bool, Dict]:
        """Detect emotion in text."""
        data = {'text': text}
        return self._make_request('POST', f"{self.base_url}/api/emotion/detect", data)
    
    def get_emotion_stats(self) -> Tuple[bool, Dict]:
        """Get emotion detection statistics."""
        return self._make_request('GET', f"{self.base_url}/api/emotion/stats")

class ConversationServiceClient(ServiceClient):
    """Client for Conversation Service communication."""
    
    def __init__(self, conversation_service_url: str):
        super().__init__('conversation-service')
        self.base_url = conversation_service_url.rstrip('/')
    
    def create_conversation(self, user_id: int, title: str = None) -> Tuple[bool, Dict]:
        """Create a new conversation."""
        data = {'title': title or 'New Conversation'}
        return self._make_request('POST', f"{self.base_url}/api/conversations", data)
    
    def get_conversations(self, user_id: int) -> Tuple[bool, Dict]:
        """Get user's conversations."""
        return self._make_request('GET', f"{self.base_url}/api/conversations")
    
    def get_messages(self, conversation_id: int) -> Tuple[bool, Dict]:
        """Get messages for a conversation."""
        return self._make_request('GET', f"{self.base_url}/api/conversations/{conversation_id}/messages")
    
    def send_message(self, conversation_id: int, message: str) -> Tuple[bool, Dict]:
        """Send a message to a conversation."""
        data = {'message': message}
        return self._make_request('POST', f"{self.base_url}/api/conversations/{conversation_id}/messages", data)
    
    def get_insights(self) -> Tuple[bool, Dict]:
        """Get conversation insights."""
        return self._make_request('GET', f"{self.base_url}/api/conversations/insights")

class AIServiceClient(ServiceClient):
    """Client for AI Service communication."""
    
    def __init__(self, ai_service_url: str):
        super().__init__('ai-service')
        self.base_url = ai_service_url.rstrip('/')
    
    def generate_response(self, message: str, emotion: str = None, confidence: float = None, context: str = 'general') -> Tuple[bool, Dict]:
        """Generate AI response."""
        data = {
            'message': message,
            'context': context
        }
        if emotion:
            data['emotion'] = emotion
        if confidence:
            data['confidence'] = confidence
        
        return self._make_request('POST', f"{self.base_url}/api/ai/generate", data)
    
    def chat(self, message: str, history: list = None) -> Tuple[bool, Dict]:
        """Handle chat conversation."""
        data = {
            'message': message,
            'history': history or []
        }
        return self._make_request('POST', f"{self.base_url}/api/ai/chat", data)
    
    def get_suggestions(self) -> Tuple[bool, Dict]:
        """Get conversation starter suggestions."""
        return self._make_request('GET', f"{self.base_url}/api/ai/suggestions")

class WebSocketServiceClient(ServiceClient):
    """Client for WebSocket Service communication."""
    
    def __init__(self, websocket_service_url: str):
        super().__init__('websocket-service')
        self.base_url = websocket_service_url.rstrip('/')
    
    def get_status(self) -> Tuple[bool, Dict]:
        """Get WebSocket service status."""
        return self._make_request('GET', f"{self.base_url}/api/websocket/status")

class ServiceRegistry:
    """Service registry for managing service URLs and clients."""
    
    def __init__(self):
        self.services = {
            'auth': os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8002'),
            'emotion': os.environ.get('EMOTION_SERVICE_URL', 'http://emotion-service:8003'),
            'conversation': os.environ.get('CONVERSATION_SERVICE_URL', 'http://conversation-service:8004'),
            'ai': os.environ.get('AI_SERVICE_URL', 'http://ai-service:8005'),
            'websocket': os.environ.get('WEBSOCKET_SERVICE_URL', 'http://websocket-service:8006')
        }
        
        # Initialize service clients
        self.auth_client = AuthServiceClient(self.services['auth'])
        self.emotion_client = EmotionServiceClient(self.services['emotion'])
        self.conversation_client = ConversationServiceClient(self.services['conversation'])
        self.ai_client = AIServiceClient(self.services['ai'])
        self.websocket_client = WebSocketServiceClient(self.services['websocket'])
    
    def get_service_url(self, service_name: str) -> str:
        """Get service URL by name."""
        return self.services.get(service_name)
    
    def get_client(self, service_name: str) -> ServiceClient:
        """Get service client by name."""
        clients = {
            'auth': self.auth_client,
            'emotion': self.emotion_client,
            'conversation': self.conversation_client,
            'ai': self.ai_client,
            'websocket': self.websocket_client
        }
        return clients.get(service_name)
    
    def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services."""
        health_status = {}
        
        for service_name, url in self.services.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                health_status[service_name] = response.status_code == 200
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status[service_name] = False
        
        return health_status

# Global service registry instance
service_registry = ServiceRegistry()

def get_service_client(service_name: str) -> ServiceClient:
    """Get service client by name."""
    return service_registry.get_client(service_name)

def health_check_services() -> Dict[str, bool]:
    """Check health of all services."""
    return service_registry.health_check_all() 