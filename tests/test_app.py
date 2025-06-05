#!/usr/bin/env python3
"""
Unit tests for EmotiBot application
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from app import create_app
from services.emotion_service import EmotionService
from services.gemini_service import GeminiService


@pytest.fixture
def app():
    """Create test application instance."""
    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-key'
    os.environ['GEMINI_MOCK_MODE'] = 'true'
    
    app = create_app('testing')
    app.config['TESTING'] = True
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
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
        assert 'status' in data
        assert data['status'] == 'ok'


class TestEmotionAnalysisEndpoint:
    """Test emotion analysis endpoint."""
    
    def test_emotion_analysis_requires_json(self, client):
        """Test that emotion analysis endpoint requires JSON."""
        response = client.post('/api/analyze')
        assert response.status_code == 400
        
    def test_emotion_analysis_requires_text(self, client):
        """Test that emotion analysis requires text field."""
        response = client.post('/api/analyze', 
                             json={})
        assert response.status_code == 400
        
    def test_emotion_analysis_with_valid_text(self, client):
        """Test emotion analysis with valid text."""
        response = client.post('/api/analyze', 
                             json={'text': 'I am feeling happy today!'})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'detected_emotion' in data
        assert 'confidence' in data
        assert 'bot_message' in data


class TestEmotionService:
    """Test emotion service functionality."""
    
    def test_emotion_service_initialization(self):
        """Test that emotion service initializes correctly."""
        service = EmotionService()
        assert service is not None
        
    def test_analyze_emotion_with_happy_text(self):
        """Test emotion analysis with happy text."""
        service = EmotionService()
        result = service.analyze_emotion("I'm so excited and happy!")
        
        assert 'emotion' in result
        assert 'confidence' in result
        assert isinstance(result['confidence'], float)
        assert 0 <= result['confidence'] <= 1


class TestGeminiService:
    """Test Gemini service functionality."""
    
    def test_gemini_service_initialization(self):
        """Test that Gemini service initializes correctly."""
        service = GeminiService()
        assert service is not None
        
    def test_gemini_service_mock_mode(self):
        """Test Gemini service in mock mode."""
        with patch.dict(os.environ, {'GEMINI_MOCK_MODE': 'true'}):
            service = GeminiService()
            assert service.mock_mode is True
            assert service.enabled is False
            
    def test_generate_emotional_response_fallback(self):
        """Test emotional response generation with fallback."""
        service = GeminiService()
        response = service.generate_emotional_response(
            user_message="I'm feeling sad",
            detected_emotion="sad",
            confidence=0.8
        )
        
        assert isinstance(response, str)
        assert len(response) > 0


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_page_loads(self, client):
        """Test that login page loads correctly."""
        response = client.get('/login')
        assert response.status_code == 200
        
    def test_register_page_loads(self, client):
        """Test that register page loads correctly."""
        response = client.get('/register')
        assert response.status_code == 200
        
    def test_register_endpoint_requires_json(self, client):
        """Test that register endpoint requires JSON."""
        response = client.post('/api/auth/register')
        assert response.status_code == 400


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_normal_requests(self, client):
        """Test that rate limiter allows normal request volume."""
        # Make multiple requests within limit
        for _ in range(5):
            response = client.get('/health')
            assert response.status_code == 200


class TestConfiguration:
    """Test application configuration."""
    
    def test_app_has_required_config(self, app):
        """Test that app has required configuration."""
        assert app.config['SECRET_KEY'] is not None
        assert app.config['SQLALCHEMY_DATABASE_URI'] is not None
        
    def test_testing_config_active(self, app):
        """Test that testing configuration is active."""
        assert app.config['TESTING'] is True


if __name__ == '__main__':
    pytest.main([__file__]) 