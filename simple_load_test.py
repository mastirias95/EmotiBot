#!/usr/bin/env python3
"""
Simple EmotiBot Load Testing Script
Uses only basic Python libraries and requests (already in requirements.txt)
"""

import requests
import time
import random
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List
import statistics
from datetime import datetime

@dataclass
class SimpleTestResult:
    """Simple test result data structure"""
    endpoint: str
    response_time: float
    status_code: int
    success: bool
    timestamp: float
    error: str = None

class SimpleLoadTester:
    """Simple load testing implementation using only requests"""
    
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.emotion_texts = [
            "I'm feeling really excited about this new project!",
            "I'm quite frustrated with how things are going.",
            "This situation makes me very anxious and worried.",
            "I feel incredibly happy and grateful today!",
            "I'm disappointed with the recent developments.",
            "This news makes me feel surprised and curious.",
            "I'm feeling overwhelmed with all the work.",
            "I feel peaceful and content with life right now."
        ]
    
    def validate_connection(self) -> bool:
        """Check if the application is accessible"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Application is accessible")
                return True
            else:
                print(f"❌ Application returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to application: {e}")
            return False
    
    def single_user_test(self, user_id: int, duration: int, delay: float = 0) -> List[SimpleTestResult]:
        """Simulate a single user's activity"""
        if delay > 0:
            time.sleep(delay)  # Ramp-up delay
        
        results = []
        session = requests.Session()
        end_time = time.time() + duration
        
        print(f"👤 User {user_id} started")
        
        while time.time() < end_time:
            # Health check
            start_time = time.time()
            try:
                response = session.get(f"{self.base_url}/health", timeout=10)
                response_time = time.time() - start_time
                
                results.append(SimpleTestResult(
                    endpoint="/health",
                    response_time=response_time,
                    status_code=response.status_code,
                    success=response.status_code == 200,
                    timestamp=start_time
                ))
            except Exception as e:
                response_time = time.time() - start_time
                results.append(SimpleTestResult(
                    endpoint="/health",
                    response_time=response_time,
                    status_code=0,
                    success=False,
                    timestamp=start_time,
                    error=str(e)
                ))
            
            # Multiple emotion analysis requests
            for _ in range(random.randint(2, 5)):
                emotion_text = random.choice(self.emotion_texts)
                start_time = time.time()
                
                try:
                    response = session.post(
                        f"{self.base_url}/api/analyze",
                        json={"text": emotion_text},
                        timeout=15
                    )
                    response_time = time.time() - start_time
                    
                    results.append(SimpleTestResult(
                        endpoint="/api/analyze",
                        response_time=response_time,
                        status_code=response.status_code,
                        success=response.status_code == 200,
                        timestamp=start_time
                    ))
                except Exception as e:
                    response_time = time.time() - start_time
                    results.append(SimpleTestResult(
                        endpoint="/api/analyze",
                        response_time=response_time,
                        status_code=0,
                        success=False,
                        timestamp=start_time,
                        error=str(e)
                    ))
                
                # Random delay between requests (realistic user behavior)
                time.sleep(random.uniform(0.5, 2.0))
            
            # Pause between cycles
            time.sleep(random.uniform(1, 3))
        
        print(f"✅ User {user_id} completed ({len(results)} requests)")
        return results
    
    def run_load_test(self, users: int = 10, duration: int = 30, ramp_up: int = 5):
        """Run load test with specified parameters"""
        print("="*60)
        print(f"🚀 STARTING SIMPLE LOAD TEST")
        print("="*60)
        print(f"Target: {self.base_url}")
        print(f"Users: {users}")
        print(f"Duration: {duration}s")
        print(f"Ramp-up: {ramp_up}s")
        print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        if not self.validate_connection():
            return
        
        all_results = []
        
        # Use ThreadPoolExecutor for concurrent users
        with ThreadPoolExecutor(max_workers=users) as executor:
            futures = []
            
            for i in range(users):
                # Calculate ramp-up delay for each user
                delay = (i / users) * ramp_up if users > 1 else 0
                future = executor.submit(self.single_user_test, i+1, duration, delay)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    user_results = future.result()
                    all_results.extend(user_results)
                except Exception as e:
                    print(f"⚠️ User simulation failed: {e}")
        
        self.analyze_results(all_results)
        return all_results
    
    def analyze_results(self, results: List[SimpleTestResult]):
        """Analyze and display test results"""
        if not results:
            print("❌ No results to analyze")
            return
        
        # Basic statistics
        total_requests = len(results)
        successful_requests = len([r for r in results if r.success])
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests) * 100
        
        # Response time analysis
        response_times = [r.response_time for r in results if r.success]
        if not response_times:
            print("❌ No successful requests to analyze")
            return
        
        min_time = min(response_times)
        max_time = max(response_times)
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        
        # Percentiles
        sorted_times = sorted(response_times)
        p95_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99_time = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        
        # Test duration
        start_timestamp = min(r.timestamp for r in results)
        end_timestamp = max(r.timestamp for r in results)
        test_duration = end_timestamp - start_timestamp
        rps = total_requests / test_duration if test_duration > 0 else 0
        
        # Endpoint breakdown
        endpoints = {}
        for result in results:
            if result.endpoint not in endpoints:
                endpoints[result.endpoint] = {"total": 0, "success": 0, "times": []}
            endpoints[result.endpoint]["total"] += 1
            if result.success:
                endpoints[result.endpoint]["success"] += 1
                endpoints[result.endpoint]["times"].append(result.response_time)
        
        # Display results
        print("\n" + "="*60)
        print("📊 LOAD TEST RESULTS")
        print("="*60)
        
        print(f"\n🎯 SUMMARY:")
        print(f"Total Requests: {total_requests:,}")
        print(f"Successful: {successful_requests:,}")
        print(f"Failed: {failed_requests:,}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Test Duration: {test_duration:.1f}s")
        print(f"Requests/Second: {rps:.1f}")
        
        print(f"\n⚡ RESPONSE TIMES:")
        print(f"Min: {min_time:.3f}s")
        print(f"Max: {max_time:.3f}s")
        print(f"Average: {avg_time:.3f}s")
        print(f"Median: {median_time:.3f}s")
        print(f"95th Percentile: {p95_time:.3f}s")
        print(f"99th Percentile: {p99_time:.3f}s")
        
        print(f"\n🎯 ENDPOINT BREAKDOWN:")
        for endpoint, stats in endpoints.items():
            endpoint_success_rate = (stats["success"] / stats["total"]) * 100
            avg_endpoint_time = statistics.mean(stats["times"]) if stats["times"] else 0
            print(f"\n{endpoint}:")
            print(f"  Requests: {stats['total']:,}")
            print(f"  Success Rate: {endpoint_success_rate:.1f}%")
            print(f"  Avg Response Time: {avg_endpoint_time:.3f}s")
        
        # Performance assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT:")
        if success_rate >= 99 and p95_time < 0.5:
            print("🟢 EXCELLENT - System performing optimally")
        elif success_rate >= 95 and p95_time < 1.0:
            print("🟡 GOOD - System performing within acceptable limits")
        elif success_rate >= 90:
            print("🟠 NEEDS ATTENTION - Performance degradation detected")
        else:
            print("🔴 CRITICAL - System performance issues")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if success_rate < 95:
            print("- Investigate error logs for failed requests")
            print("- Check server resource utilization")
            print("- Consider infrastructure scaling")
        if p95_time > 1.0:
            print("- Optimize slow response endpoints")
            print("- Review database query performance")
            print("- Consider implementing caching")
        if success_rate >= 99 and p95_time < 0.5:
            print("- System is performing well, consider increasing load")
            print("- Monitor for sustained performance under load")
        
        print("\n" + "="*60)

def main():
    """Main execution function"""
    print("🤖 EmotiBot Simple Load Testing")
    print("\nAvailable test scenarios:")
    print("1. Quick Test (5 users, 15s)")
    print("2. Light Load (10 users, 30s)")
    print("3. Moderate Load (25 users, 60s)")
    print("4. Heavy Load (50 users, 120s)")
    print("5. Custom Test")
    
    try:
        choice = input("\nSelect test scenario (1-5): ").strip()
    except KeyboardInterrupt:
        print("\n👋 Test cancelled")
        return
    
    tester = SimpleLoadTester()
    
    if choice == "1":
        tester.run_load_test(users=5, duration=15, ramp_up=3)
    elif choice == "2":
        tester.run_load_test(users=10, duration=30, ramp_up=5)
    elif choice == "3":
        tester.run_load_test(users=25, duration=60, ramp_up=10)
    elif choice == "4":
        tester.run_load_test(users=50, duration=120, ramp_up=15)
    elif choice == "5":
        try:
            users = int(input("Number of concurrent users: "))
            duration = int(input("Test duration (seconds): "))
            ramp_up = int(input("Ramp-up time (seconds): "))
            tester.run_load_test(users=users, duration=duration, ramp_up=ramp_up)
        except ValueError:
            print("❌ Invalid input. Using default test.")
            tester.run_load_test()
    else:
        print("❌ Invalid choice. Running default test.")
        tester.run_load_test()

if __name__ == "__main__":
    main() 