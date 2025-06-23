#!/usr/bin/env python3
"""
Simple unit tests for Conversation Service
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Mock environment variables before importing app
os.environ.update({
    'CONVERSATION_DATABASE_URL': 'sqlite:///:memory:',
    'AUTH_SERVICE_URL': 'http://localhost:8002',
    'EMOTION_SERVICE_URL': 'http://localhost:8003',
    'AI_SERVICE_URL': 'http://localhost:8005',
    'SERVICE_SECRET': 'test-service-secret',
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379'
})

# Create a proper mock for prometheus metrics that handles decorators
class MockPrometheusMetrics:
    def __init__(self, app=None):
        pass
    
    def counter(self, name, description):
        def decorator(func):
            return func
        return decorator
    
    def histogram(self, name, description):
        def decorator(func):
            return func
        return decorator

# Create a mock message queue client that returns serializable values
class MockMessageQueueClient:
    def __init__(self):
        pass
    
    def ensure_connection(self):
        return True
    
    def publish_message(self, queue, message):
        return True
    
    def publish_conversation_created(self, conversation_data):
        return True
    
    def close(self):
        return True

# Mock external dependencies before importing
with patch('redis.Redis') as mock_redis, \
     patch('prometheus_flask_exporter.PrometheusMetrics', MockPrometheusMetrics), \
     patch.dict('sys.modules', {'message_queue': MagicMock()}), \
     patch('requests.post') as mock_requests:
    
    mock_redis.return_value.ping.return_value = True
    
    # Mock requests.post for external service calls
    mock_response = MagicMock()
    mock_response.status_code = 401  # Default to unauthorized
    mock_response.json.return_value = {'error': 'Unauthorized'}
    mock_requests.return_value = mock_response
    
    # Now import the app and replace the queue_client
    from app import app
    
    # Replace the queue_client with our mock
    import app as app_module
    app_module.queue_client = MockMessageQueueClient()


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint_returns_200(self, client):
        """Test that health endpoint returns 200 status."""
        response = client.get('/health')
        assert response.status_code == 200
        
    def test_health_endpoint_returns_json(self, client):
        """Test that health endpoint returns valid JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'service' in data
        assert 'status' in data
        assert 'queue_connection' in data
        assert data['service'] == 'conversation-service'
        assert data['status'] == 'healthy'
        assert data['queue_connection'] is True  # Our mock returns True


class TestConversationEndpoints:
    """Test conversation endpoints."""
    
    def test_conversations_endpoint_requires_auth(self, client):
        """Test that conversations endpoint requires authentication."""
        response = client.get('/api/conversations')
        assert response.status_code == 401
        
    def test_create_conversation_requires_auth(self, client):
        """Test that creating conversation requires authentication."""
        response = client.post('/api/conversations')
        assert response.status_code == 401

    def test_export_conversations_requires_auth(self, client):
        """Test that export endpoint requires authentication."""
        response = client.get('/api/conversations/export')
        assert response.status_code == 401

    def test_clear_conversations_requires_auth(self, client):
        """Test that clear endpoint requires authentication."""
        response = client.delete('/api/conversations/clear')
        assert response.status_code == 401

    @patch('requests.post')
    def test_conversations_endpoint_with_valid_auth(self, mock_post, client):
        """Test conversations endpoint with valid authentication."""
        # Mock successful auth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_post.return_value = mock_response
        
        response = client.get('/api/conversations', headers={
            'Authorization': 'Bearer valid-token'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'conversations' in data

    @patch('requests.post')
    def test_create_conversation_with_valid_auth(self, mock_post, client):
        """Test creating conversation with valid authentication."""
        # Mock successful auth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_post.return_value = mock_response
        
        response = client.post('/api/conversations', 
                             headers={'Authorization': 'Bearer valid-token'},
                             json={'title': 'Test Conversation'})
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data

    def test_conversations_endpoint_missing_header(self, client):
        """Test conversations endpoint without auth header."""
        response = client.get('/api/conversations')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_conversations_endpoint_malformed_header(self, client):
        """Test conversations endpoint with malformed auth header."""
        response = client.get('/api/conversations', headers={
            'Authorization': 'InvalidFormat'
        })
        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON in requests."""
        response = client.post('/api/conversations',
                             headers={
                                 'Authorization': 'Bearer token',
                                 'Content-Type': 'application/json'
                             },
                             data='invalid json')
        # Should return 400 or 401 (auth fails first)
        assert response.status_code in [400, 401]

    def test_missing_json_content_type(self, client):
        """Test handling requests without proper content type."""
        response = client.post('/api/conversations',
                             headers={'Authorization': 'Bearer token'},
                             data='some data')
        assert response.status_code == 401  # Auth fails first


class TestDatabaseOperations:
    """Test database-related functionality."""
    
    @patch('requests.post')
    def test_conversation_model_creation(self, mock_post, client):
        """Test that conversation models can be created properly."""
        # Mock successful auth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_post.return_value = mock_response
        
        # Test conversation creation endpoint
        response = client.post('/api/conversations',
                             headers={'Authorization': 'Bearer valid-token'},
                             json={'title': 'Test DB Conversation'})
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'conversation' in data
        assert data['conversation']['title'] == 'Test DB Conversation'


class TestMessageEndpoints:
    """Test message-related endpoints."""
    
    def test_get_messages_requires_auth(self, client):
        """Test that get messages endpoint requires authentication."""
        response = client.get('/api/conversations/1/messages')
        assert response.status_code == 401

    def test_send_message_requires_auth(self, client):
        """Test that send message endpoint requires authentication."""
        response = client.post('/api/conversations/1/messages')
        assert response.status_code == 401

    @patch('requests.post')
    def test_send_message_requires_content(self, mock_post, client):
        """Test that send message endpoint requires message content."""
        # Mock successful auth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_post.return_value = mock_response
        
        response = client.post('/api/conversations/1/messages',
                             headers={'Authorization': 'Bearer valid-token'},
                             json={'message': ''})  # Empty message
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 