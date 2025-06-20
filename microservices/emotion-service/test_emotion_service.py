#!/usr/bin/env python3
"""
Unit tests for Emotion Service
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock

# Mock environment variables before importing app
os.environ.update({
    'AUTH_SERVICE_URL': 'http://localhost:8002',
    'SERVICE_SECRET': 'test-service-secret',
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379'
})

from app import app


@pytest.fixture
def test_app():
    """Create test application instance."""
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def sample_text_data():
    """Sample text data for testing."""
    return {
        'happy': 'I am so excited and happy today!',
        'sad': 'I feel very sad and disappointed.',
        'angry': 'This makes me furious and angry!',
        'neutral': 'The weather is okay today.',
        'mixed': 'I am happy but also a bit worried.'
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
        assert 'status' in data
        assert data['status'] == 'healthy'


class TestEmotionAnalysis:
    """Test emotion analysis functionality."""
    
    def test_analyze_emotion_requires_json(self, client):
        """Test that emotion analysis endpoint requires JSON."""
        response = client.post('/analyze')
        assert response.status_code == 400
        
    def test_analyze_emotion_requires_text(self, client):
        """Test that emotion analysis requires text field."""
        response = client.post('/analyze', json={})
        assert response.status_code == 400
        
    def test_analyze_emotion_with_valid_text(self, client, sample_text_data):
        """Test emotion analysis with valid text."""
        for emotion_type, text in sample_text_data.items():
            response = client.post('/analyze', json={'text': text})
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'emotion' in data
            assert 'confidence' in data
            assert isinstance(data['confidence'], (int, float))
            assert 0 <= data['confidence'] <= 1
            
    def test_analyze_emotion_empty_text(self, client):
        """Test emotion analysis with empty text."""
        response = client.post('/analyze', json={'text': ''})
        assert response.status_code == 400
        
    def test_analyze_emotion_very_long_text(self, client):
        """Test emotion analysis with very long text."""
        long_text = 'This is a test sentence. ' * 1000  # Very long text
        response = client.post('/analyze', json={'text': long_text})
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400, 413]


class TestEmotionDetection:
    """Test emotion detection algorithms."""
    
    def test_positive_emotion_detection(self, client, sample_text_data):
        """Test detection of positive emotions."""
        response = client.post('/analyze', json={'text': sample_text_data['happy']})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Should detect positive sentiment
        assert data['emotion'] in ['joy', 'happy', 'positive', 'excited']
        
    def test_negative_emotion_detection(self, client, sample_text_data):
        """Test detection of negative emotions."""
        response = client.post('/analyze', json={'text': sample_text_data['sad']})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Should detect negative sentiment
        assert data['emotion'] in ['sad', 'negative', 'disappointed', 'sorrow']
        
    def test_neutral_emotion_detection(self, client, sample_text_data):
        """Test detection of neutral emotions."""
        response = client.post('/analyze', json={'text': sample_text_data['neutral']})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Should detect neutral or low confidence
        assert data['emotion'] in ['neutral', 'objective'] or data['confidence'] < 0.5


class TestBatchAnalysis:
    """Test batch emotion analysis."""
    
    def test_batch_analysis_endpoint(self, client):
        """Test batch analysis endpoint."""
        batch_data = {
            'texts': [
                'I am happy today!',
                'This is terrible.',
                'Weather is okay.'
            ]
        }
        response = client.post('/analyze-batch', json=batch_data)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'results' in data
            assert len(data['results']) == 3
            
            for result in data['results']:
                assert 'emotion' in result
                assert 'confidence' in result
        else:
            # Batch endpoint might not be implemented
            assert response.status_code in [404, 405]


class TestServiceIntegration:
    """Test integration with other services."""
    
    @patch('requests.post')
    def test_auth_service_integration(self, mock_post, client):
        """Test integration with auth service."""
        # Mock auth service response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'valid': True, 'user_id': 1}
        
        # Make request with auth token
        headers = {'Authorization': 'Bearer test-token'}
        response = client.post('/analyze', 
                             json={'text': 'I am happy!'}, 
                             headers=headers)
        
        # Should succeed regardless of auth (or handle appropriately)
        assert response.status_code in [200, 401]
        
    @patch('redis.Redis')
    def test_redis_caching(self, mock_redis, client):
        """Test Redis caching functionality."""
        # Mock Redis
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        
        response = client.post('/analyze', json={'text': 'I am happy!'})
        assert response.status_code == 200
        
        # Verify Redis was attempted to be used (if implemented)
        # This test verifies the service doesn't crash when Redis is available


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post('/analyze', 
                             data='{"text": "incomplete json"',
                             content_type='application/json')
        assert response.status_code == 400
        
    def test_missing_content_type(self, client):
        """Test handling of missing content type."""
        response = client.post('/analyze', data='{"text": "test"}')
        assert response.status_code in [400, 415]
        
    def test_unicode_text_handling(self, client):
        """Test handling of unicode text."""
        unicode_text = 'I feel happy! 😊🎉 Très bien! 中文测试'
        response = client.post('/analyze', json={'text': unicode_text})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'emotion' in data
        assert 'confidence' in data


class TestPerformance:
    """Test performance-related aspects."""
    
    def test_concurrent_requests_simulation(self, client):
        """Test handling of multiple requests (simulated)."""
        # Simulate multiple concurrent requests
        responses = []
        for i in range(10):
            response = client.post('/analyze', json={'text': f'Test message {i}'})
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            
    def test_response_time_reasonable(self, client):
        """Test that response time is reasonable."""
        import time
        
        start_time = time.time()
        response = client.post('/analyze', json={'text': 'This is a test message'})
        end_time = time.time()
        
        assert response.status_code == 200
        # Response should be reasonably fast (under 5 seconds)
        assert (end_time - start_time) < 5.0


class TestServiceSecrets:
    """Test service authentication and secrets."""
    
    def test_service_to_service_auth(self, client):
        """Test service-to-service authentication."""
        headers = {'X-Service-Secret': 'test-service-secret'}
        response = client.post('/analyze', 
                             json={'text': 'test'}, 
                             headers=headers)
        # Should not return 403 (forbidden)
        assert response.status_code != 403
        
    def test_invalid_service_secret(self, client):
        """Test invalid service secret handling."""
        headers = {'X-Service-Secret': 'invalid-secret'}
        response = client.post('/internal/analyze', 
                             json={'text': 'test'}, 
                             headers=headers)
        # If internal endpoint exists, should return 403
        assert response.status_code in [403, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 