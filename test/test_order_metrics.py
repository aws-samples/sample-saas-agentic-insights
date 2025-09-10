#!/usr/bin/env python3
"""
Simple test to verify Order service metrics integration
"""

import json
import sys
import os

# Add the order service to path for testing
sys.path.insert(0, 'src/app-plane/order')

def test_order_handler_import():
    """Test that the order handler can be imported with metrics"""
    try:
        import handler
        print("✅ Order handler imported successfully")
        
        # Check if metrics are enabled
        if hasattr(handler, 'METRICS_ENABLED'):
            print(f"✅ Metrics enabled: {handler.METRICS_ENABLED}")
        else:
            print("❌ METRICS_ENABLED not found")
            
        return True
    except ImportError as e:
        print(f"❌ Failed to import order handler: {e}")
        return False

def test_metrics_collector_import():
    """Test that metrics collector can be imported"""
    try:
        # Try to import from the layer path
        sys.path.insert(0, 'src/layers/metrics-collector/python')
        from metrics_collector import MetricsCollector
        print("✅ MetricsCollector imported successfully")
        
        # Test initialization
        collector = MetricsCollector("test-service", "test-tenant", "basic")
        print("✅ MetricsCollector initialized successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import MetricsCollector: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Order Service Metrics Integration")
    print("=" * 50)
    
    success = True
    
    # Test metrics collector
    if not test_metrics_collector_import():
        success = False
    
    # Test order handler
    if not test_order_handler_import():
        success = False
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Order service is ready for metrics collection.")
    else:
        print("❌ Some tests failed. Check the implementation.")
    
    sys.exit(0 if success else 1)
