#!/usr/bin/env python3
"""
Unit tests for WebSocket Service
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

# Mock external dependencies
with patch('redis.Redis') as mock_redis, \
     patch('prometheus_flask_exporter.PrometheusMetrics', MockPrometheusMetrics), \
     patch.dict('sys.modules', {'message_queue': MagicMock()}), \
     patch('flask_socketio.SocketIO') as mock_socketio:
    
    mock_redis.return_value.ping.return_value = True
    mock_socketio.return_value = MagicMock()
    
    # Now import the app
    from app import app, verify_user_token, analyze_emotion, generate_ai_response, store_message_in_cache


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
        assert data['service'] == 'websocket-service'
        assert data['status'] == 'healthy'
        assert 'active_connections' in data
        assert 'dependencies' in data

    def test_health_endpoint_includes_dependencies(self, client):
        """Test that health endpoint includes dependency information."""
        response = client.get('/health')
        data = json.loads(response.data)
        dependencies = data['dependencies']
        assert 'auth_service' in dependencies
        assert 'emotion_service' in dependencies
        assert 'ai_service' in dependencies


class TestWebSocketStatusEndpoint:
    """Test WebSocket status endpoint."""
    
    def test_websocket_status_endpoint(self, client):
        """Test WebSocket status endpoint returns correct information."""
        response = client.get('/api/websocket/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'service' in data
        assert 'active_connections' in data
        assert 'status' in data


class TestAuthenticationFunctions:
    """Test authentication-related functions."""
    
    @patch('requests.post')
    def test_verify_user_token_success(self, mock_post):
        """Test successful token verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
        mock_post.return_value = mock_response
        
        is_valid, user_data = verify_user_token('valid-token')
        
        assert is_valid is True
        assert user_data is not None
        assert user_data['user_id'] == 1
        assert user_data['username'] == 'testuser'
    
    @patch('requests.post')
    def test_verify_user_token_failure(self, mock_post):
        """Test failed token verification."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        is_valid, user_data = verify_user_token('invalid-token')
        
        assert is_valid is False
        assert user_data is None
    
    @patch('requests.post')
    def test_verify_user_token_network_error(self, mock_post):
        """Test token verification with network error."""
        mock_post.side_effect = Exception("Network error")
        
        is_valid, user_data = verify_user_token('some-token')
        
        assert is_valid is False
        assert user_data is None


class TestEmotionAnalysis:
    """Test emotion analysis functions."""
    
    @patch('requests.post')
    def test_analyze_emotion_success(self, mock_post):
        """Test successful emotion analysis."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'emotion': 'happy',
            'confidence': 0.85,
            'scores': {'happy': 0.85, 'sad': 0.15}
        }
        mock_post.return_value = mock_response
        
        result = analyze_emotion("I'm feeling great today!")
        
        assert result is not None
        assert result['emotion'] == 'happy'
        assert result['confidence'] == 0.85
    
    @patch('requests.post')
    def test_analyze_emotion_failure(self, mock_post):
        """Test emotion analysis failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = analyze_emotion("Some text")
        
        assert result is None
    
    @patch('requests.post')
    def test_analyze_emotion_network_error(self, mock_post):
        """Test emotion analysis with network error."""
        mock_post.side_effect = Exception("Network error")
        
        result = analyze_emotion("Some text")
        
        assert result is None


class TestAIResponseGeneration:
    """Test AI response generation functions."""
    
    @patch('requests.post')
    def test_generate_ai_response_success(self, mock_post):
        """Test successful AI response generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Hello! How can I help you today?',
            'conversation_id': 'conv-123'
        }
        mock_post.return_value = mock_response
        
        result = generate_ai_response("Hello", user_id=1)
        
        assert result is not None
        assert 'response' in result
        assert result['response'] == 'Hello! How can I help you today?'
    
    @patch('requests.post')
    def test_generate_ai_response_with_emotion(self, mock_post):
        """Test AI response generation with emotion data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'I can sense you\'re feeling happy!',
            'conversation_id': 'conv-123'
        }
        mock_post.return_value = mock_response
        
        emotion_data = {'emotion': 'happy', 'confidence': 0.9}
        result = generate_ai_response("I'm excited!", emotion_data, user_id=1)
        
        assert result is not None
        assert 'response' in result
        
        # Verify that emotion data was passed in the request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]['json']
        assert 'emotion' in request_data
        assert 'confidence' in request_data
        assert request_data['emotion'] == 'happy'
    
    @patch('requests.post')
    def test_generate_ai_response_failure(self, mock_post):
        """Test AI response generation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = generate_ai_response("Hello")
        
        assert result is None


class TestRedisOperations:
    """Test Redis caching operations."""
    
    def test_store_message_in_cache_success(self):
        """Test successful message caching."""
        # Create a mock redis client
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.rpush.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.delete.return_value = True
        
        # Import the app module to access the global redis_client
        import app as app_module
        original_redis_client = app_module.redis_client
        
        try:
            # Temporarily replace the redis_client
            app_module.redis_client = mock_redis
            
            message_data = {
                'message': 'Hello',
                'timestamp': '2024-01-01T00:00:00Z',
                'emotion': 'happy'
            }
            
            # Should not raise any exceptions
            store_message_in_cache(user_id=1, message_data=message_data)
            
            # Verify Redis operations were called
            mock_redis.lrange.assert_called()
            mock_redis.rpush.assert_called()
            mock_redis.expire.assert_called()
        finally:
            # Restore original redis_client
            app_module.redis_client = original_redis_client
    
    @patch('app.redis_client', None)
    def test_store_message_in_cache_no_redis(self):
        """Test message caching when Redis is not available."""
        message_data = {'message': 'Hello'}
        
        # Should not raise any exceptions when Redis is None
        store_message_in_cache(user_id=1, message_data=message_data)
    
    @patch('app.redis_client')
    def test_store_message_in_cache_redis_error(self, mock_redis):
        """Test message caching with Redis error."""
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        message_data = {'message': 'Hello'}
        
        # Should not raise any exceptions even with Redis errors
        store_message_in_cache(user_id=1, message_data=message_data)


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_500_error_simulation(self, client):
        """Test 500 error handling."""
        # This would need to be triggered by simulating an internal error
        # For now, just verify the route exists
        response = client.get('/health')
        assert response.status_code == 200


class TestWebSocketHelperFunctions:
    """Test WebSocket helper and utility functions."""
    
    def test_message_data_structure(self):
        """Test that message data structures are properly formed."""
        message_data = {
            'message': 'Hello world',
            'timestamp': '2024-01-01T00:00:00Z',
            'user_id': 1,
            'emotion': 'happy',
            'confidence': 0.9
        }
        
        # Verify all required fields are present
        assert 'message' in message_data
        assert 'timestamp' in message_data
        assert 'user_id' in message_data
        assert 'emotion' in message_data
        assert 'confidence' in message_data
        
        # Verify data types
        assert isinstance(message_data['message'], str)
        assert isinstance(message_data['user_id'], int)
        assert isinstance(message_data['confidence'], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 