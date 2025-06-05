#!/usr/bin/env python3
"""
EmotiBot Load Test Runner
Simple script to execute load tests with predefined configurations
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the tests directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tests'))

try:
    from tests.load_testing import EmotiBotLoadTester, LoadTestConfig, LoadTestScenarios
except ImportError:
    print("❌ Could not import load testing module. Make sure tests/load_testing.py exists.")
    sys.exit(1)

def print_banner():
    """Print the application banner"""
    print("="*60)
    print("🤖 EMOTIBOT LOAD TESTING SUITE")
    print("="*60)
    print("Testing scalable architecture performance")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

def validate_application():
    """Validate that the application is running and accessible"""
    import requests
    
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Application is running and accessible")
            return True
        else:
            print(f"❌ Application returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to application: {e}")
        print("💡 Make sure EmotiBot is running on http://localhost:5001")
        return False

async def run_quick_test():
    """Run a quick smoke test"""
    print("\n🔥 Running Quick Smoke Test...")
    config = LoadTestConfig(
        concurrent_users=5,
        test_duration=15,
        ramp_up_time=3
    )
    
    tester = EmotiBotLoadTester(config)
    results = await tester.run_async_load_test()
    metrics = tester.calculate_metrics(results)
    
    print("\n📊 Quick Test Results:")
    summary = metrics.get("summary", {})
    response_times = metrics.get("response_times", {})
    
    print(f"Total Requests: {summary.get('total_requests', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    print(f"Average Response Time: {response_times.get('mean', 0):.3f}s")
    print(f"95th Percentile: {response_times.get('p95', 0):.3f}s")
    
    return summary.get('success_rate', 0) > 95

async def main():
    """Main execution function"""
    print_banner()
    
    # Validate application is running
    if not validate_application():
        print("\n❌ Cannot proceed with load testing.")
        print("Please start EmotiBot application first:")
        print("  docker-compose up -d")
        print("  or")
        print("  python run_app.py")
        return
    
    print("\nSelect Load Test Scenario:")
    print("1. 🟢 Quick Smoke Test (5 users, 15s)")
    print("2. 🔵 Light Load Test (10 users, 30s)")
    print("3. 🟡 Moderate Load Test (50 users, 60s)")
    print("4. 🟠 Heavy Load Test (100 users, 120s)")
    print("5. 🔴 Stress Test (200 users, 180s)")
    print("6. 🛠️ Comprehensive Test Suite (All scenarios)")
    print("0. Exit")
    
    try:
        choice = input("\nEnter your choice (0-6): ").strip()
    except KeyboardInterrupt:
        print("\n\n👋 Load testing cancelled by user")
        return
    
    if choice == "0":
        print("👋 Goodbye!")
        return
    
    # Get configuration based on choice
    config = None
    test_name = ""
    
    if choice == "1":
        await run_quick_test()
        return
    elif choice == "2":
        config = LoadTestScenarios.light_load()
        test_name = "Light Load Test"
    elif choice == "3":
        config = LoadTestScenarios.moderate_load()
        test_name = "Moderate Load Test"
    elif choice == "4":
        config = LoadTestScenarios.heavy_load()
        test_name = "Heavy Load Test"
    elif choice == "5":
        config = LoadTestScenarios.stress_test()
        test_name = "Stress Test"
    elif choice == "6":
        # Run comprehensive test suite
        print("\n🚀 Running Comprehensive Test Suite...")
        
        scenarios = [
            ("Light Load", LoadTestScenarios.light_load()),
            ("Moderate Load", LoadTestScenarios.moderate_load()),
            ("Heavy Load", LoadTestScenarios.heavy_load()),
        ]
        
        all_results = []
        for scenario_name, scenario_config in scenarios:
            print(f"\n{'='*40}")
            print(f"Running {scenario_name} Test...")
            print(f"{'='*40}")
            
            tester = EmotiBotLoadTester(scenario_config)
            results, metrics = await tester.run_comprehensive_load_test()
            all_results.append((scenario_name, metrics))
            
            print(f"\n✅ {scenario_name} test completed")
        
        # Print summary of all tests
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE TEST SUITE SUMMARY")
        print("="*60)
        
        for scenario_name, metrics in all_results:
            summary = metrics.get("summary", {})
            response_times = metrics.get("response_times", {})
            
            print(f"\n{scenario_name}:")
            print(f"  Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"  Avg Response Time: {response_times.get('mean', 0):.3f}s")
            print(f"  95th Percentile: {response_times.get('p95', 0):.3f}s")
            print(f"  Requests/Second: {summary.get('requests_per_second', 0):.1f}")
        
        print("\n✅ Comprehensive test suite completed!")
        return
    else:
        print("❌ Invalid choice. Please select 0-6.")
        return
    
    # Run single test scenario
    if config:
        print(f"\n🚀 Starting {test_name}...")
        print(f"Configuration: {config.concurrent_users} users, {config.test_duration}s duration")
        
        # Confirm before running heavy tests
        if config.concurrent_users >= 100:
            confirm = input(f"\n⚠️ This will run {config.concurrent_users} concurrent users. Continue? (y/N): ")
            if confirm.lower() != 'y':
                print("Test cancelled.")
                return
        
        tester = EmotiBotLoadTester(config)
        results, metrics = await tester.run_comprehensive_load_test()
        
        # Performance assessment
        summary = metrics.get("summary", {})
        response_times = metrics.get("response_times", {})
        
        success_rate = summary.get('success_rate', 0)
        avg_response_time = response_times.get('mean', 0)
        p95_response_time = response_times.get('p95', 0)
        
        print("\n🎯 PERFORMANCE ASSESSMENT:")
        
        if success_rate >= 99 and p95_response_time < 0.5:
            print("🟢 EXCELLENT - System performing optimally")
        elif success_rate >= 95 and p95_response_time < 1.0:
            print("🟡 GOOD - System performing within acceptable limits")
        elif success_rate >= 90:
            print("🟠 NEEDS ATTENTION - Performance degradation detected")
        else:
            print("🔴 CRITICAL - System performance issues")
        
        print(f"\nNext Steps:")
        if success_rate < 95:
            print("- Investigate error logs")
            print("- Check resource utilization")
            print("- Consider infrastructure scaling")
        if p95_response_time > 1.0:
            print("- Optimize slow endpoints")
            print("- Review database queries")
            print("- Consider caching implementation")
        
        print(f"\n📁 Detailed results saved to: emotibot_load_test_results.csv")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Load testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Load testing failed: {e}")
        sys.exit(1) 