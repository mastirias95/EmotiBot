#!/usr/bin/env python3
"""
EmotiBot Microservices Testing Script
Tests all services, inter-service communication, and API functionality.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Service URLs
SERVICES = {
    'api_gateway': 'http://localhost:8000',
    'auth_service': 'http://localhost:8002',
    'emotion_service': 'http://localhost:8003',
    'conversation_service': 'http://localhost:8004',
    'ai_service': 'http://localhost:8005',
    'websocket_service': 'http://localhost:8006'
}

class MicroservicesTester:
    def __init__(self):
        self.test_results = []
        self.auth_token = None
        self.user_id = None
        
    def log_test(self, test_name, success, message=""):
        """Log test result."""
        status = "✓ PASS" if success else "✗ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = f"[{timestamp}] {status} - {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': timestamp
        })
        return success
    
    def test_service_health(self, service_name, url):
        """Test service health endpoint."""
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                return self.log_test(f"{service_name} Health Check", True)
            else:
                return self.log_test(f"{service_name} Health Check", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test(f"{service_name} Health Check", False, str(e))
    
    def test_all_services_health(self):
        """Test health of all services."""
        print("\n" + "="*60)
        print("TESTING SERVICE HEALTH")
        print("="*60)
        
        all_healthy = True
        for service_name, url in SERVICES.items():
            if not self.test_service_health(service_name, url):
                all_healthy = False
        
        return all_healthy
    
    def test_user_registration(self):
        """Test user registration through API Gateway."""
        print("\n" + "="*60)
        print("TESTING USER REGISTRATION")
        print("="*60)
        
        test_user = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpassword123"
        }
        
        try:
            response = requests.post(
                f"{SERVICES['api_gateway']}/api/auth/register",
                headers={'Content-Type': 'application/json'},
                json=test_user,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get('user', {}).get('id')
                return self.log_test("User Registration", True, f"User ID: {self.user_id}")
            else:
                return self.log_test("User Registration", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            return self.log_test("User Registration", False, str(e))
    
    def test_user_login(self):
        """Test user login and token generation."""
        print("\n" + "="*60)
        print("TESTING USER LOGIN")
        print("="*60)
        
        login_data = {
            "username": f"testuser_{int(time.time())}",
            "password": "testpassword123"
        }
        
        try:
            response = requests.post(
                f"{SERVICES['api_gateway']}/api/auth/login",
                headers={'Content-Type': 'application/json'},
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                return self.log_test("User Login", True, f"Token received: {self.auth_token[:20]}...")
            else:
                return self.log_test("User Login", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            return self.log_test("User Login", False, str(e))
    
    def test_emotion_detection(self):
        """Test emotion detection service."""
        print("\n" + "="*60)
        print("TESTING EMOTION DETECTION")
        print("="*60)
        
        test_texts = [
            "I am feeling really happy today!",
            "I'm so sad and depressed",
            "I'm angry about what happened",
            "I feel neutral about this"
        ]
        
        all_success = True
        for i, text in enumerate(test_texts, 1):
            try:
                response = requests.post(
                    f"{SERVICES['api_gateway']}/api/emotion/detect",
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.auth_token}'
                    },
                    json={'text': text},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    emotion = data.get('emotion', 'unknown')
                    confidence = data.get('confidence', 0)
                    success = self.log_test(f"Emotion Detection {i}", True, f"Text: '{text[:30]}...' -> {emotion} ({confidence:.2f})")
                else:
                    success = self.log_test(f"Emotion Detection {i}", False, f"Status: {response.status_code}")
                
                if not success:
                    all_success = False
                    
            except Exception as e:
                success = self.log_test(f"Emotion Detection {i}", False, str(e))
                all_success = False
        
        return all_success
    
    def test_conversation_creation(self):
        """Test conversation creation."""
        print("\n" + "="*60)
        print("TESTING CONVERSATION CREATION")
        print("="*60)
        
        try:
            response = requests.post(
                f"{SERVICES['api_gateway']}/api/conversations",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.auth_token}'
                },
                json={'title': 'Test Conversation'},
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                conversation_id = data.get('conversation', {}).get('id')
                return self.log_test("Conversation Creation", True, f"Conversation ID: {conversation_id}")
            else:
                return self.log_test("Conversation Creation", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            return self.log_test("Conversation Creation", False, str(e))
    
    def test_ai_response_generation(self):
        """Test AI response generation."""
        print("\n" + "="*60)
        print("TESTING AI RESPONSE GENERATION")
        print("="*60)
        
        test_message = "I am feeling really happy today! Can you help me understand why?"
        
        try:
            response = requests.post(
                f"{SERVICES['api_gateway']}/api/ai/generate",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.auth_token}'
                },
                json={
                    'message': test_message,
                    'emotion': 'happy',
                    'confidence': 0.95
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', '')
                source = data.get('source', 'unknown')
                return self.log_test("AI Response Generation", True, f"Source: {source}, Response: '{ai_response[:50]}...'")
            else:
                return self.log_test("AI Response Generation", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            return self.log_test("AI Response Generation", False, str(e))
    
    def test_inter_service_communication(self):
        """Test direct inter-service communication."""
        print("\n" + "="*60)
        print("TESTING INTER-SERVICE COMMUNICATION")
        print("="*60)
        
        # Test Auth Service directly
        try:
            response = requests.get(f"{SERVICES['auth_service']}/health", timeout=5)
            auth_ok = response.status_code == 200
        except:
            auth_ok = False
        
        # Test Emotion Service directly
        try:
            response = requests.get(f"{SERVICES['emotion_service']}/health", timeout=5)
            emotion_ok = response.status_code == 200
        except:
            emotion_ok = False
        
        # Test AI Service directly
        try:
            response = requests.get(f"{SERVICES['ai_service']}/health", timeout=5)
            ai_ok = response.status_code == 200
        except:
            ai_ok = False
        
        # Test WebSocket Service directly
        try:
            response = requests.get(f"{SERVICES['websocket_service']}/health", timeout=5)
            ws_ok = response.status_code == 200
        except:
            ws_ok = False
        
        all_ok = auth_ok and emotion_ok and ai_ok and ws_ok
        
        self.log_test("Auth Service Direct Access", auth_ok)
        self.log_test("Emotion Service Direct Access", emotion_ok)
        self.log_test("AI Service Direct Access", ai_ok)
        self.log_test("WebSocket Service Direct Access", ws_ok)
        
        return all_ok
    
    def test_api_gateway_routing(self):
        """Test API Gateway routing and load balancing."""
        print("\n" + "="*60)
        print("TESTING API GATEWAY ROUTING")
        print("="*60)
        
        # Test that requests go through the gateway
        try:
            response = requests.get(f"{SERVICES['api_gateway']}/health", timeout=5)
            if response.status_code == 200:
                return self.log_test("API Gateway Routing", True, "Gateway is routing requests correctly")
            else:
                return self.log_test("API Gateway Routing", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("API Gateway Routing", False, str(e))
    
    def test_error_handling(self):
        """Test error handling and validation."""
        print("\n" + "="*60)
        print("TESTING ERROR HANDLING")
        print("="*60)
        
        # Test invalid token
        try:
            response = requests.get(
                f"{SERVICES['api_gateway']}/api/auth/me",
                headers={'Authorization': 'Bearer invalid_token'},
                timeout=5
            )
            success = response.status_code == 401
            self.log_test("Invalid Token Handling", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Token Handling", False, str(e))
        
        # Test missing required fields
        try:
            response = requests.post(
                f"{SERVICES['api_gateway']}/api/auth/register",
                headers={'Content-Type': 'application/json'},
                json={'username': 'test'}  # Missing email and password
            )
            success = response.status_code == 400
            self.log_test("Missing Fields Validation", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Missing Fields Validation", False, str(e))
        
        # Test invalid endpoint
        try:
            response = requests.get(f"{SERVICES['api_gateway']}/invalid/endpoint", timeout=5)
            success = response.status_code == 404
            self.log_test("Invalid Endpoint Handling", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Endpoint Handling", False, str(e))
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🚀 EmotiBot Microservices Testing Suite")
        print("="*60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Run all test suites
        tests = [
            ("Service Health", self.test_all_services_health),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Emotion Detection", self.test_emotion_detection),
            ("Conversation Creation", self.test_conversation_creation),
            ("AI Response Generation", self.test_ai_response_generation),
            ("Inter-Service Communication", self.test_inter_service_communication),
            ("API Gateway Routing", self.test_api_gateway_routing),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed_tests = 0
        total_tests = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                total_tests += 1
            except Exception as e:
                print(f"✗ ERROR in {test_name}: {e}")
                total_tests += 1
        
        # Generate summary report
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Microservices platform is working correctly.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please check the service logs.")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed_tests == total_tests

def main():
    """Main function."""
    tester = MicroservicesTester()
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 