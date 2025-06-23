#!/usr/bin/env python3
"""
Simple unit tests for Auth Service
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
    'AUTH_DATABASE_URL': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-secret-key',
    'JWT_SECRET_KEY': 'test-jwt-secret-key',
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


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123'
    }


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

    def test_auth_health_endpoint(self, client):
        """Test the /api/auth/health endpoint."""
        response = client.get('/api/auth/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'service' in data


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_endpoint_requires_json(self, client):
        """Test that registration requires JSON."""
        response = client.post('/api/auth/register')
        assert response.status_code == 400
        
    def test_register_endpoint_requires_username(self, client):
        """Test that registration requires username."""
        user_data = {'email': 'test@example.com', 'password': 'password123'}
        response = client.post('/api/auth/register', json=user_data)
        assert response.status_code == 400
        
    def test_register_endpoint_requires_email(self, client):
        """Test that registration requires email."""
        user_data = {'username': 'testuser', 'password': 'password123'}
        response = client.post('/api/auth/register', json=user_data)
        assert response.status_code == 400
        
    def test_register_endpoint_requires_password(self, client):
        """Test that registration requires password."""
        user_data = {'username': 'testuser', 'email': 'test@example.com'}
        response = client.post('/api/auth/register', json=user_data)
        assert response.status_code == 400
        
    def test_register_password_length_validation(self, client):
        """Test password length validation."""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'  # Too short
        }
        response = client.post('/api/auth/register', json=user_data)
        assert response.status_code == 400


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 401
        
    def test_login_requires_username(self, client):
        """Test that login requires username."""
        login_data = {'password': 'password'}
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 400
        
    def test_login_requires_password(self, client):
        """Test that login requires password."""
        login_data = {'username': 'testuser'}
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 400


class TestTokenVerification:
    """Test JWT token verification."""
        
    def test_verify_invalid_token(self, client):
        """Test verification of invalid token."""
        response = client.post('/api/auth/verify', json={'token': 'invalid_token'})
        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/auth/register', data='invalid json')
        assert response.status_code == 400
        
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 