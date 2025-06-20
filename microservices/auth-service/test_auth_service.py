#!/usr/bin/env python3
"""
Unit tests for Auth Service
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock

# Mock environment variables before importing app
os.environ.update({
    'AUTH_DATABASE_URL': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-secret-key',
    'JWT_SECRET_KEY': 'test-jwt-secret-key',
    'SERVICE_SECRET': 'test-service-secret',
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379'
})

# Mock external dependencies
with patch('redis.Redis'), patch('message_queue.get_queue_client'), patch('prometheus_flask_exporter.PrometheusMetrics'):
    from app import app, User, SessionLocal, Base, engine


@pytest.fixture
def test_app():
    """Create test application instance."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield app
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


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
        assert data['service'] == 'auth-service'
        assert 'status' in data
        assert data['status'] == 'healthy'


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_endpoint_success(self, client, sample_user):
        """Test successful user registration."""
        response = client.post('/api/auth/register', json=sample_user)
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert 'message' in data
        assert 'user' in data
        assert data['user']['username'] == sample_user['username']
        assert data['user']['email'] == sample_user['email']
        
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
        
    def test_register_duplicate_username(self, client, sample_user):
        """Test that duplicate username registration fails."""
        # First registration
        client.post('/api/auth/register', json=sample_user)
        
        # Second registration with same username
        response = client.post('/api/auth/register', json=sample_user)
        assert response.status_code == 409


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_success(self, client, sample_user):
        """Test successful login."""
        # Register user first
        client.post('/api/auth/register', json=sample_user)
        
        # Login
        login_data = {
            'username': sample_user['username'],
            'password': sample_user['password']
        }
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'user' in data
        
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
    
    def test_verify_valid_token(self, client, sample_user):
        """Test verification of valid token."""
        # Register and login to get token
        client.post('/api/auth/register', json=sample_user)
        login_response = client.post('/api/auth/login', json={
            'username': sample_user['username'],
            'password': sample_user['password']
        })
        
        login_data = json.loads(login_response.data)
        token = login_data['access_token']
        
        # Verify token
        response = client.post('/api/auth/verify', json={'token': token})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'valid' in data
        assert data['valid'] is True
        assert 'user' in data
        
    def test_verify_invalid_token(self, client):
        """Test verification of invalid token."""
        response = client.post('/api/auth/verify', json={'token': 'invalid_token'})
        assert response.status_code == 401


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation_and_retrieval(self, test_app):
        """Test user model creation and retrieval."""
        with test_app.app_context():
            db = SessionLocal()
            
            # Create user
            user = User(
                username='testuser',
                email='test@example.com',
                hashed_password='hashed_password'
            )
            
            db.add(user)
            db.commit()
            
            # Retrieve user
            retrieved_user = db.query(User).filter(User.username == 'testuser').first()
            assert retrieved_user is not None
            assert retrieved_user.username == 'testuser'
            assert retrieved_user.email == 'test@example.com'
            
            db.close()
            
    def test_user_to_dict(self, test_app):
        """Test user to_dict method."""
        with test_app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                hashed_password='hashed_password'
            )
            
            user_dict = user.to_dict()
            assert isinstance(user_dict, dict)
            assert 'username' in user_dict
            assert 'email' in user_dict
            assert 'is_active' in user_dict
            assert user_dict['username'] == 'testuser'


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/auth/register', 
                             data='{"invalid": json}',
                             content_type='application/json')
        assert response.status_code == 400
        
    def test_missing_content_type(self, client):
        """Test handling of missing content type."""
        response = client.post('/api/auth/register', data='{"test": "data"}')
        assert response.status_code == 400
        
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 