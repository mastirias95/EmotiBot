#!/usr/bin/env python3
"""
EmotiBot Load Testing Suite
Comprehensive load testing for scalable architecture validation
"""

import asyncio
import time
import random
import json
import csv
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import threading
import requests
import ssl

# Import optional dependencies with fallback
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ aiohttp not available. Install with: pip install aiohttp")

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️ websocket-client not available. Install with: pip install websocket-client")

@dataclass
class TestResult:
    """Data class to store individual test results"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    error: Optional[str] = None
    response_size: int = 0
    timestamp: float = 0

@dataclass
class LoadTestConfig:
    """Configuration for load testing parameters"""
    base_url: str = "http://localhost:5001"
    concurrent_users: int = 100
    test_duration: int = 60  # seconds
    ramp_up_time: int = 10   # seconds
    endpoints: List[str] = None
    auth_token: Optional[str] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = [
                "/health",
                "/api/analyze",
                "/api/auth/login",
                "/api/conversations/history"
            ]

class EmotiBotLoadTester:
    """Comprehensive load testing for EmotiBot application"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.websocket_results: List[TestResult] = []
        self.start_time = 0
        self.test_data = self._generate_test_data()
        
    def _generate_test_data(self) -> Dict:
        """Generate realistic test data for various endpoints"""
        emotions = [
            "I'm feeling really excited about this new project!",
            "I'm quite frustrated with how things are going.",
            "This situation makes me very anxious and worried.",
            "I feel incredibly happy and grateful today!",
            "I'm disappointed with the recent developments.",
            "This news makes me feel surprised and curious.",
            "I'm feeling overwhelmed with all the work.",
            "I feel peaceful and content with life right now."
        ]
        
        return {
            "emotion_texts": emotions,
            "login_data": {
                "username": "testuser",
                "password": "testpass123"
            },
            "register_data": {
                "username": f"user_{random.randint(1000, 9999)}",
                "email": f"test_{random.randint(1000, 9999)}@example.com",
                "password": "password123"
            }
        }
    
    async def _make_request(self, session, endpoint: str, method: str = "GET", data: Dict = None) -> TestResult:
        """Make an asynchronous HTTP request and measure performance"""
        start_time = time.time()
        url = f"{self.config.base_url}{endpoint}"
        
        headers = {}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        
        try:
            if method.upper() == "POST":
                async with session.post(url, json=data, headers=headers) as response:
                    content = await response.read()
                    response_time = time.time() - start_time
                    
                    return TestResult(
                        endpoint=endpoint,
                        method=method,
                        response_time=response_time,
                        status_code=response.status,
                        success=response.status < 400,
                        response_size=len(content),
                        timestamp=start_time
                    )
            else:
                async with session.get(url, headers=headers) as response:
                    content = await response.read()
                    response_time = time.time() - start_time
                    
                    return TestResult(
                        endpoint=endpoint,
                        method=method,
                        response_time=response_time,
                        status_code=response.status,
                        success=response.status < 400,
                        response_size=len(content),
                        timestamp=start_time
                    )
                    
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=0,
                success=False,
                error=str(e),
                timestamp=start_time
            )
    
    async def _simulate_user_journey(self, session, user_id: int):
        """Simulate a realistic user journey through the application"""
        journey_results = []
        
        # 1. Health check
        result = await self._make_request(session, "/health")
        journey_results.append(result)
        
        # 2. Emotion analysis requests (multiple)
        for _ in range(random.randint(3, 8)):
            emotion_text = random.choice(self.test_data["emotion_texts"])
            result = await self._make_request(
                session, 
                "/api/analyze", 
                "POST", 
                {"text": emotion_text}
            )
            journey_results.append(result)
            
            # Random delay between requests (0.5-3 seconds)
            await asyncio.sleep(random.uniform(0.5, 3.0))
        
        # 3. Authentication attempt (some users)
        if random.random() < 0.3:  # 30% of users try to login
            result = await self._make_request(
                session,
                "/api/auth/login",
                "POST",
                self.test_data["login_data"]
            )
            journey_results.append(result)
        
        return journey_results
    
    async def run_async_load_test(self) -> List[TestResult]:
        """Run the main asynchronous load test"""
        if not AIOHTTP_AVAILABLE:
            print("❌ Cannot run async load test - aiohttp not available")
            return self.run_sync_load_test()
        
        print(f"🚀 Starting async load test with {self.config.concurrent_users} concurrent users...")
        print(f"📊 Test duration: {self.config.test_duration}s, Ramp-up: {self.config.ramp_up_time}s")
        
        connector = aiohttp.TCPConnector(limit=self.config.concurrent_users + 10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            # Gradually ramp up users
            for i in range(self.config.concurrent_users):
                # Calculate delay for ramp-up
                delay = (i / self.config.concurrent_users) * self.config.ramp_up_time
                
                task = asyncio.create_task(self._delayed_user_simulation(session, i, delay))
                tasks.append(task)
            
            # Wait for all tasks to complete or timeout
            results = []
            try:
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.config.test_duration + self.config.ramp_up_time + 30
                )
                
                for task_result in completed_tasks:
                    if isinstance(task_result, list):
                        results.extend(task_result)
                        
            except asyncio.TimeoutError:
                print("⚠️ Test timed out, collecting partial results...")
                for task in tasks:
                    if not task.done():
                        task.cancel()
            
            return results
    
    async def _delayed_user_simulation(self, session, user_id: int, delay: float):
        """Start user simulation after a delay for ramp-up"""
        await asyncio.sleep(delay)
        
        end_time = time.time() + self.config.test_duration
        all_results = []
        
        while time.time() < end_time:
            journey_results = await self._simulate_user_journey(session, user_id)
            all_results.extend(journey_results)
            
            # Brief pause between journey cycles
            await asyncio.sleep(random.uniform(1, 3))
        
        return all_results
    
    def run_sync_load_test(self) -> List[TestResult]:
        """Run a synchronous load test as fallback when aiohttp is not available"""
        print(f"🚀 Starting sync load test with {self.config.concurrent_users} concurrent users...")
        print(f"📊 Test duration: {self.config.test_duration}s, Ramp-up: {self.config.ramp_up_time}s")
        
        all_results = []
        
        def sync_user_simulation(user_id: int, delay: float):
            import time
            time.sleep(delay)  # Ramp-up delay
            
            end_time = time.time() + self.config.test_duration
            user_results = []
            
            session = requests.Session()
            
            while time.time() < end_time:
                # Health check
                try:
                    start_time = time.time()
                    response = session.get(f"{self.config.base_url}/health", timeout=10)
                    response_time = time.time() - start_time
                    
                    user_results.append(TestResult(
                        endpoint="/health",
                        method="GET",
                        response_time=response_time,
                        status_code=response.status_code,
                        success=response.status_code < 400,
                        timestamp=start_time
                    ))
                except Exception as e:
                    user_results.append(TestResult(
                        endpoint="/health",
                        method="GET",
                        response_time=10.0,
                        status_code=0,
                        success=False,
                        error=str(e),
                        timestamp=time.time()
                    ))
                
                # Emotion analysis
                for _ in range(random.randint(2, 5)):
                    emotion_text = random.choice(self.test_data["emotion_texts"])
                    try:
                        start_time = time.time()
                        response = session.post(
                            f"{self.config.base_url}/api/analyze",
                            json={"text": emotion_text},
                            timeout=10
                        )
                        response_time = time.time() - start_time
                        
                        user_results.append(TestResult(
                            endpoint="/api/analyze",
                            method="POST",
                            response_time=response_time,
                            status_code=response.status_code,
                            success=response.status_code < 400,
                            timestamp=start_time
                        ))
                    except Exception as e:
                        user_results.append(TestResult(
                            endpoint="/api/analyze",
                            method="POST",
                            response_time=10.0,
                            status_code=0,
                            success=False,
                            error=str(e),
                            timestamp=time.time()
                        ))
                    
                    time.sleep(random.uniform(0.5, 2.0))  # Delay between requests
                
                time.sleep(random.uniform(1, 3))  # Delay between journey cycles
            
            return user_results
        
        # Run with ThreadPoolExecutor for concurrency
        with ThreadPoolExecutor(max_workers=self.config.concurrent_users) as executor:
            futures = []
            
            for i in range(self.config.concurrent_users):
                delay = (i / self.config.concurrent_users) * self.config.ramp_up_time
                future = executor.submit(sync_user_simulation, i, delay)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"⚠️ User simulation failed: {e}")
        
        return all_results
    
    def test_websocket_performance(self) -> List[TestResult]:
        """Test WebSocket connection performance"""
        if not WEBSOCKET_AVAILABLE:
            print("⚠️ Skipping WebSocket tests - websocket-client not available")
            return []
        
        print("🔌 Testing WebSocket performance...")
        
        websocket_results = []
        
        def websocket_test():
            try:
                start_time = time.time()
                ws_url = self.config.base_url.replace("http", "ws") + "/socket.io/?transport=websocket"
                
                ws = websocket.create_connection(
                    ws_url,
                    timeout=10,
                    sslopt={"cert_reqs": ssl.CERT_NONE} if "wss" in ws_url else None
                )
                
                connect_time = time.time() - start_time
                
                # Send test message
                test_message = json.dumps({
                    "type": "emotion_update",
                    "data": {"emotion": "happy", "confidence": 0.85}
                })
                
                message_start = time.time()
                ws.send(test_message)
                response = ws.recv()
                message_time = time.time() - message_start
                
                ws.close()
                
                websocket_results.extend([
                    TestResult(
                        endpoint="/socket.io",
                        method="CONNECT",
                        response_time=connect_time,
                        status_code=200,
                        success=True,
                        timestamp=start_time
                    ),
                    TestResult(
                        endpoint="/socket.io",
                        method="MESSAGE",
                        response_time=message_time,
                        status_code=200,
                        success=True,
                        timestamp=message_start
                    )
                ])
                
            except Exception as e:
                websocket_results.append(
                    TestResult(
                        endpoint="/socket.io",
                        method="CONNECT",
                        response_time=10.0,
                        status_code=0,
                        success=False,
                        error=str(e),
                        timestamp=time.time()
                    )
                )
        
        # Test WebSocket with multiple concurrent connections
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(websocket_test) for _ in range(20)]
            for future in as_completed(futures):
                future.result()
        
        return websocket_results
    
    def stress_test_database(self) -> List[TestResult]:
        """Perform database stress testing through API calls"""
        print("💾 Running database stress test...")
        
        stress_results = []
        
        def database_stress_worker():
            session = requests.Session()
            
            for _ in range(50):  # Each worker makes 50 requests
                try:
                    # Test emotion analysis (writes to DB)
                    start_time = time.time()
                    response = session.post(
                        f"{self.config.base_url}/api/analyze",
                        json={"text": random.choice(self.test_data["emotion_texts"])},
                        timeout=10
                    )
                    response_time = time.time() - start_time
                    
                    stress_results.append(TestResult(
                        endpoint="/api/analyze",
                        method="POST",
                        response_time=response_time,
                        status_code=response.status_code,
                        success=response.status_code < 400,
                        timestamp=start_time
                    ))
                    
                except Exception as e:
                    stress_results.append(TestResult(
                        endpoint="/api/analyze",
                        method="POST",
                        response_time=10.0,
                        status_code=0,
                        success=False,
                        error=str(e),
                        timestamp=time.time()
                    ))
        
        # Run stress test with high concurrency
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(database_stress_worker) for _ in range(20)]
            for future in as_completed(futures):
                future.result()
        
        return stress_results
    
    def calculate_metrics(self, results: List[TestResult]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        response_times = [r.response_time for r in successful_results]
        
        if not response_times:
            return {"error": "No successful requests"}
        
        # Group results by endpoint
        endpoint_metrics = {}
        for result in results:
            if result.endpoint not in endpoint_metrics:
                endpoint_metrics[result.endpoint] = []
            endpoint_metrics[result.endpoint].append(result)
        
        metrics = {
            "summary": {
                "total_requests": len(results),
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / len(results) * 100,
                "total_test_time": max(r.timestamp for r in results) - min(r.timestamp for r in results),
                "requests_per_second": len(results) / max(1, max(r.timestamp for r in results) - min(r.timestamp for r in results))
            },
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0,
                "p99": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) > 0 else 0,
                "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0
            },
            "endpoint_breakdown": {}
        }
        
        # Calculate per-endpoint metrics
        for endpoint, endpoint_results in endpoint_metrics.items():
            successful_endpoint = [r for r in endpoint_results if r.success]
            endpoint_times = [r.response_time for r in successful_endpoint]
            
            if endpoint_times:
                metrics["endpoint_breakdown"][endpoint] = {
                    "requests": len(endpoint_results),
                    "success_rate": len(successful_endpoint) / len(endpoint_results) * 100,
                    "avg_response_time": statistics.mean(endpoint_times),
                    "p95_response_time": sorted(endpoint_times)[int(len(endpoint_times) * 0.95)] if len(endpoint_times) > 0 else 0
                }
        
        return metrics
    
    def export_results(self, results: List[TestResult], filename: str = "load_test_results.csv"):
        """Export test results to CSV for analysis"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'endpoint', 'method', 'response_time', 'status_code', 'success', 'error', 'response_size']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))
        
        print(f"📊 Results exported to {filename}")
    
    def print_report(self, metrics: Dict):
        """Print a comprehensive test report"""
        print("\n" + "="*60)
        print("📊 EMOTIBOT LOAD TEST REPORT")
        print("="*60)
        
        summary = metrics.get("summary", {})
        response_times = metrics.get("response_times", {})
        
        print(f"\n🎯 SUMMARY")
        print(f"Total Requests: {summary.get('total_requests', 0):,}")
        print(f"Successful Requests: {summary.get('successful_requests', 0):,}")
        print(f"Failed Requests: {summary.get('failed_requests', 0):,}")
        print(f"Success Rate: {summary.get('success_rate', 0):.2f}%")
        print(f"Test Duration: {summary.get('total_test_time', 0):.2f}s")
        print(f"Requests/Second: {summary.get('requests_per_second', 0):.2f}")
        
        print(f"\n⚡ RESPONSE TIMES")
        print(f"Min: {response_times.get('min', 0):.3f}s")
        print(f"Max: {response_times.get('max', 0):.3f}s")
        print(f"Mean: {response_times.get('mean', 0):.3f}s")
        print(f"Median: {response_times.get('median', 0):.3f}s")
        print(f"95th Percentile: {response_times.get('p95', 0):.3f}s")
        print(f"99th Percentile: {response_times.get('p99', 0):.3f}s")
        print(f"Std Deviation: {response_times.get('std_dev', 0):.3f}s")
        
        print(f"\n🎯 ENDPOINT BREAKDOWN")
        endpoint_breakdown = metrics.get("endpoint_breakdown", {})
        for endpoint, stats in endpoint_breakdown.items():
            print(f"\n{endpoint}:")
            print(f"  Requests: {stats.get('requests', 0):,}")
            print(f"  Success Rate: {stats.get('success_rate', 0):.2f}%")
            print(f"  Avg Response Time: {stats.get('avg_response_time', 0):.3f}s")
            print(f"  95th Percentile: {stats.get('p95_response_time', 0):.3f}s")
        
        print("\n" + "="*60)
    
    async def run_comprehensive_load_test(self):
        """Run all load testing scenarios"""
        print("🔥 Starting Comprehensive EmotiBot Load Test")
        print(f"Target: {self.config.base_url}")
        print(f"Configuration: {self.config.concurrent_users} users, {self.config.test_duration}s duration")
        
        all_results = []
        
        # 1. Standard HTTP Load Test
        print("\n1️⃣ Running HTTP Load Test...")
        http_results = await self.run_async_load_test()
        all_results.extend(http_results)
        
        # 2. WebSocket Performance Test
        print("\n2️⃣ Running WebSocket Performance Test...")
        ws_results = self.test_websocket_performance()
        all_results.extend(ws_results)
        
        # 3. Database Stress Test
        print("\n3️⃣ Running Database Stress Test...")
        db_results = self.stress_test_database()
        all_results.extend(db_results)
        
        # Calculate and display metrics
        metrics = self.calculate_metrics(all_results)
        self.print_report(metrics)
        
        # Export results
        self.export_results(all_results, "emotibot_load_test_results.csv")
        
        return all_results, metrics

# Load Testing Scenarios
class LoadTestScenarios:
    """Pre-defined load testing scenarios for different use cases"""
    
    @staticmethod
    def light_load():
        """Light load scenario - normal usage"""
        return LoadTestConfig(
            concurrent_users=10,
            test_duration=30,
            ramp_up_time=5
        )
    
    @staticmethod
    def moderate_load():
        """Moderate load scenario - busy periods"""
        return LoadTestConfig(
            concurrent_users=50,
            test_duration=60,
            ramp_up_time=10
        )
    
    @staticmethod
    def heavy_load():
        """Heavy load scenario - peak usage"""
        return LoadTestConfig(
            concurrent_users=100,
            test_duration=120,
            ramp_up_time=15
        )
    
    @staticmethod
    def stress_test():
        """Stress test scenario - beyond normal capacity"""
        return LoadTestConfig(
            concurrent_users=200,
            test_duration=180,
            ramp_up_time=20
        )

async def main():
    """Main execution function"""
    print("🤖 EmotiBot Load Testing Suite")
    print("Choose a test scenario:")
    print("1. Light Load (10 users, 30s)")
    print("2. Moderate Load (50 users, 60s)")
    print("3. Heavy Load (100 users, 120s)")
    print("4. Stress Test (200 users, 180s)")
    print("5. Custom Configuration")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == "1":
        config = LoadTestScenarios.light_load()
    elif choice == "2":
        config = LoadTestScenarios.moderate_load()
    elif choice == "3":
        config = LoadTestScenarios.heavy_load()
    elif choice == "4":
        config = LoadTestScenarios.stress_test()
    elif choice == "5":
        users = int(input("Number of concurrent users: "))
        duration = int(input("Test duration (seconds): "))
        ramp_up = int(input("Ramp-up time (seconds): "))
        config = LoadTestConfig(
            concurrent_users=users,
            test_duration=duration,
            ramp_up_time=ramp_up
        )
    else:
        config = LoadTestScenarios.moderate_load()
        print("Using default moderate load configuration...")
    
    # Override base URL if needed
    url = input(f"Base URL [{config.base_url}]: ").strip()
    if url:
        config.base_url = url
    
    # Run the load test
    tester = EmotiBotLoadTester(config)
    results, metrics = await tester.run_comprehensive_load_test()
    
    return results, metrics

if __name__ == "__main__":
    asyncio.run(main()) 