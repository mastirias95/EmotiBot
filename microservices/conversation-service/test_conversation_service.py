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

# Mock external dependencies
with patch('redis.Redis') as mock_redis, \
     patch('prometheus_flask_exporter.PrometheusMetrics', MockPrometheusMetrics), \
     patch.dict('sys.modules', {'message_queue': MagicMock()}):
    
    mock_redis.return_value.ping.return_value = True
    
    # Now import the app
    from app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    return app.test_client()


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


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 