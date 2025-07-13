#!/usr/bin/env python3
# =============================================================================
# QuranBot - Discord API Monitor Test
# =============================================================================
# Test script to verify Discord API monitoring functionality
# =============================================================================

import sys
import json
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_discord_monitor():
    """Test Discord API monitor functionality"""
    try:
        from src.utils.discord_api_monitor import get_discord_monitor
        
        print("🔗 Testing Discord API Monitor...")
        
        # Get monitor instance
        monitor = get_discord_monitor()
        
        if monitor is None:
            print("❌ Discord API Monitor not initialized")
            print("   This is expected if bot is not running")
            return False
        
        # Test health status
        print("\n📊 Testing Health Status:")
        health = monitor.get_current_health()
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Is Healthy: {health.get('is_healthy', False)}")
        print(f"   Response Time: {health.get('avg_response_time', 0):.3f}s")
        print(f"   Rate Limit Usage: {health.get('rate_limit_usage', 0):.1%}")
        
        # Test API metrics
        print("\n📈 Testing API Metrics:")
        metrics = monitor.get_api_metrics_summary()
        print(f"   Total Calls: {metrics.get('total_calls', 0)}")
        print(f"   Average Response Time: {metrics.get('avg_response_time', 0):.3f}s")
        print(f"   Error Rate: {metrics.get('error_rate', 0):.1%}")
        
        # Test gateway status
        print("\n🌐 Testing Gateway Status:")
        gateway = monitor.get_gateway_status()
        print(f"   Connected: {gateway.get('connected', False)}")
        print(f"   Latency: {gateway.get('latency', 'N/A')}")
        print(f"   Reconnects: {gateway.get('reconnect_count', 0)}")
        
        print("\n✅ Discord API Monitor test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure the Discord API monitor module exists")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_web_dashboard_integration():
    """Test web dashboard integration"""
    try:
        print("\n🌐 Testing Web Dashboard Integration...")
        
        # Test if we can import the dashboard functions
        sys.path.append(str(project_root / "tools"))
        from web_dashboard import get_discord_api_health, get_discord_gateway_status
        
        print("   ✅ Dashboard functions imported successfully")
        
        # Test health function
        print("\n📊 Testing Dashboard Health Function:")
        health = get_discord_api_health()
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Is Healthy: {health.get('is_healthy', False)}")
        
        # Test gateway function
        print("\n🌐 Testing Dashboard Gateway Function:")
        gateway = get_discord_gateway_status()
        print(f"   Connected: {gateway.get('connected', False)}")
        print(f"   Latency: {gateway.get('latency', 'N/A')}")
        
        print("\n✅ Web dashboard integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test error: {e}")
        return False

def test_data_persistence():
    """Test data persistence functionality"""
    try:
        print("\n💾 Testing Data Persistence...")
        
        from src.utils.discord_api_monitor import MONITOR_DATA_FILE
        
        if MONITOR_DATA_FILE.exists():
            print(f"   ✅ Monitor data file exists: {MONITOR_DATA_FILE}")
            
            # Check file content
            with open(MONITOR_DATA_FILE, 'r') as f:
                data = json.load(f)
            
            print(f"   📊 Health history entries: {len(data.get('health_history', []))}")
            print(f"   📈 API metrics entries: {len(data.get('api_metrics', []))}")
            print(f"   🌐 Gateway metrics entries: {len(data.get('gateway_metrics', []))}")
            print(f"   📊 Rate limit buckets: {len(data.get('rate_limit_buckets', {}))}")
            
        else:
            print(f"   ℹ️  Monitor data file doesn't exist yet: {MONITOR_DATA_FILE}")
            print("   This is expected if bot hasn't run or no data collected yet")
        
        print("\n✅ Data persistence test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Data persistence test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 QuranBot Discord API Monitor Test Suite")
    print("=" * 50)
    
    tests = [
        ("Discord Monitor Core", test_discord_monitor),
        ("Web Dashboard Integration", test_web_dashboard_integration),
        ("Data Persistence", test_data_persistence),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Discord API monitoring is ready!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 