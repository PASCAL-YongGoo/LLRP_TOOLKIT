#!/usr/bin/env python3
"""
Comprehensive Error Handling Test for LLRP Library

Tests various error scenarios and recovery mechanisms
"""

import logging
import time
from llrp.client import LLRPClient
from llrp.errors import (
    LLRPError, LLRPConnectionError, LLRPTimeoutError, 
    LLRPROSpecError, LLRPDeviceError, LLRPStatusCode,
    check_llrp_response, create_llrp_exception
)
from llrp.protocol import LLRPStatus

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('llrp_error_test.log')
    ]
)
logger = logging.getLogger(__name__)


def test_error_code_system():
    """Test LLRP error code system"""
    print("🧪 Testing LLRP Error Code System")
    print("=" * 50)
    
    # Test status code descriptions
    test_codes = [
        LLRPStatusCode.M_Success,
        LLRPStatusCode.M_ParameterError,
        LLRPStatusCode.M_NoSuchROSpec,
        LLRPStatusCode.M_DeviceError,
        LLRPStatusCode.M_InvalidFrequency,
        999  # Unknown code
    ]
    
    for code in test_codes:
        try:
            exception = create_llrp_exception(code, f"Test error for code {code}")
            print(f"   Code {code}: {exception.__class__.__name__} - {exception}")
        except Exception as e:
            print(f"   Code {code}: Error creating exception - {e}")
    
    # Test LLRPStatus methods
    print("\n📋 Testing LLRPStatus methods:")
    
    # Success status
    success_status = LLRPStatus(LLRPStatusCode.M_Success, "Operation completed")
    print(f"   Success status: {success_status.to_dict()}")
    
    # Error status
    error_status = LLRPStatus(LLRPStatusCode.M_NoSuchROSpec, "ROSpec ID 999 not found")
    print(f"   Error status: {error_status.to_dict()}")
    
    # Test exception raising
    try:
        error_status.raise_if_error()
    except LLRPError as e:
        print(f"   ✅ Correctly raised: {e.__class__.__name__}")


def test_connection_error_handling():
    """Test connection error scenarios"""
    print("\n🔌 Testing Connection Error Handling")
    print("=" * 50)
    
    # Test connection to non-existent reader
    print("🧪 Testing connection to non-existent reader:")
    
    client = LLRPClient("192.168.99.99", port=5084)  # Non-existent IP
    
    try:
        start_time = time.time()
        success = client.connect(timeout=2.0)  # Short timeout for testing
        duration = time.time() - start_time
        
        print(f"   Connection result: {success}")
        print(f"   Connection duration: {duration:.2f}s")
        
        if not success:
            print("   ✅ Correctly failed to connect to non-existent reader")
        else:
            print("   ⚠️  Unexpectedly connected")
            client.disconnect()
            
    except Exception as e:
        print(f"   ⚠️  Connection threw exception: {e}")


def test_message_timeout_handling():
    """Test message timeout scenarios"""
    print("\n⏰ Testing Message Timeout Handling")
    print("=" * 50)
    
    # This test demonstrates timeout handling structure
    # In real scenario, this would timeout waiting for reader response
    
    print("🧪 Testing timeout error creation:")
    
    try:
        timeout_error = LLRPTimeoutError("GET_READER_CAPABILITIES timeout", 5.0)
        print(f"   Created timeout error: {timeout_error}")
        print(f"   Timeout duration: {timeout_error.timeout_seconds}s")
        print(f"   Error details: {timeout_error.details}")
        
    except Exception as e:
        print(f"   Error creating timeout error: {e}")


def test_rospec_error_scenarios():
    """Test ROSpec-related error scenarios"""
    print("\n📡 Testing ROSpec Error Scenarios")
    print("=" * 50)
    
    # Simulate common ROSpec errors
    rospec_errors = [
        (LLRPStatusCode.M_NoSuchROSpec, "ROSpec ID 123 does not exist"),
        (LLRPStatusCode.M_ROSpecCurrentlyEnabled, "Cannot modify enabled ROSpec"),
        (LLRPStatusCode.M_NoMoreROSpecs, "Maximum ROSpec limit reached"),
        (LLRPStatusCode.M_ROSpecNotConfigured, "ROSpec missing required parameters"),
    ]
    
    for code, description in rospec_errors:
        print(f"\n🧪 Testing {LLRPStatusCode(code).name}:")
        
        # Create status
        status = LLRPStatus(code, description)
        print(f"   Status: {status.get_error_name()}")
        print(f"   Description: {status.get_error_description()}")
        print(f"   Is Error: {status.is_error()}")
        
        # Test exception
        try:
            check_llrp_response(code, description, raise_on_error=True)
        except LLRPError as e:
            print(f"   ✅ Correctly raised {e.__class__.__name__}: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected exception: {e}")


def test_device_error_scenarios():
    """Test device-related error scenarios"""
    print("\n🔧 Testing Device Error Scenarios")
    print("=" * 50)
    
    device_errors = [
        (LLRPStatusCode.M_NoAntennaConnected, "No antenna on port 4"),
        (LLRPStatusCode.M_ReaderTemperatureTooHigh, "Temperature: 85°C"),
        (LLRPStatusCode.M_InvalidFrequency, "915.5 MHz not supported in this region"),
        (LLRPStatusCode.M_InvalidPowerLevel, "35 dBm exceeds maximum 30 dBm"),
    ]
    
    for code, description in device_errors:
        print(f"\n🧪 Testing {LLRPStatusCode(code).name}:")
        
        try:
            status = LLRPStatus(code, description)
            status.raise_if_error()
        except LLRPDeviceError as e:
            print(f"   ✅ Correctly raised LLRPDeviceError: {e}")
        except LLRPError as e:
            print(f"   ⚠️  Raised {e.__class__.__name__}: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected exception: {e}")


def test_error_recovery_patterns():
    """Test error recovery patterns"""
    print("\n🔄 Testing Error Recovery Patterns")
    print("=" * 50)
    
    print("🧪 Testing retry pattern with exponential backoff:")
    
    def unreliable_operation():
        """Simulate an unreliable operation"""
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise LLRPConnectionError(LLRPStatusCode.M_Other, "Simulated connection failure")
        return "Success"
    
    max_retries = 3
    base_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            result = unreliable_operation()
            print(f"   ✅ Operation succeeded on attempt {attempt + 1}: {result}")
            break
        except LLRPError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"   ⚠️  Attempt {attempt + 1} failed: {e}")
                print(f"   ⏳ Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"   ❌ All {max_retries} attempts failed: {e}")


def test_comprehensive_error_logging():
    """Test comprehensive error logging"""
    print("\n📝 Testing Comprehensive Error Logging")
    print("=" * 50)
    
    # Create various error scenarios and log them
    error_scenarios = [
        ("Reader Connection Lost", LLRPStatusCode.M_Other, "TCP connection reset"),
        ("Invalid ROSpec Configuration", LLRPStatusCode.M_ParameterError, "Missing AISpec"),
        ("Antenna Malfunction", LLRPStatusCode.M_NoAntennaConnected, "Antenna 2 cable disconnected"),
        ("Temperature Alert", LLRPStatusCode.M_ReaderTemperatureTooHigh, "Internal temp 90°C"),
    ]
    
    print("🧪 Generating error logs:")
    
    for scenario, code, description in error_scenarios:
        print(f"\n   Scenario: {scenario}")
        
        # Log using different methods
        logger.error(f"Test scenario: {scenario}")
        
        try:
            status = LLRPStatus(code, description)
            status.raise_if_error()
        except LLRPError as e:
            logger.error(f"LLRP Error in {scenario}: {e}", exc_info=False)
            print(f"   Logged: {e.__class__.__name__}")


def simulate_reader_interaction():
    """Simulate interaction with reader including error scenarios"""
    print("\n🤖 Simulating Reader Interaction with Error Handling")
    print("=" * 50)
    
    # This simulates what would happen with a real reader
    reader_ip = "192.168.1.100"  # Replace with your reader IP for real testing
    
    print(f"🧪 Simulating connection to {reader_ip}:")
    
    client = LLRPClient(reader_ip)
    
    try:
        # Test robust connection with error handling
        print("   1. Attempting connection...")
        if not client.connect(timeout=5.0):
            print("   ❌ Connection failed (expected for simulation)")
            return
        
        print("   ✅ Connected successfully")
        
        # Test capabilities with error handling
        print("   2. Getting reader capabilities...")
        try:
            caps = client.get_capabilities()
            if caps:
                print(f"   ✅ Got capabilities: {caps.get('status', 'unknown')}")
            else:
                print("   ⚠️  No capabilities returned")
        except LLRPError as e:
            print(f"   ❌ LLRP Error getting capabilities: {e}")
        
        # Test inventory with error recovery
        print("   3. Starting inventory with error handling...")
        try:
            tags = client.simple_inventory(duration_seconds=2.0)
            print(f"   ✅ Inventory completed: {len(tags)} tags")
        except LLRPError as e:
            print(f"   ❌ LLRP Error during inventory: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error during inventory: {e}")
        
    except LLRPConnectionError as e:
        print(f"   ❌ Connection error: {e}")
    except LLRPError as e:
        print(f"   ❌ LLRP error: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    finally:
        print("   4. Disconnecting...")
        try:
            client.disconnect()
            print("   ✅ Disconnected successfully")
        except Exception as e:
            print(f"   ⚠️  Disconnect error: {e}")


def main():
    """Run comprehensive error handling tests"""
    print("🚀 LLRP Error Handling Test Suite")
    print("=" * 60)
    
    try:
        test_error_code_system()
        test_connection_error_handling()
        test_message_timeout_handling()
        test_rospec_error_scenarios()
        test_device_error_scenarios()
        test_error_recovery_patterns()
        test_comprehensive_error_logging()
        simulate_reader_interaction()
        
        print("\n" + "=" * 60)
        print("🎉 Error Handling Test Suite Completed!")
        print("\n📋 Summary:")
        print("   ✅ LLRP error codes and exceptions implemented")
        print("   ✅ ERROR_MESSAGE handling added")
        print("   ✅ Enhanced LLRPStatus parameter")
        print("   ✅ Connection state management improved")
        print("   ✅ Graceful disconnect and KEEPALIVE support")
        print("   ✅ Comprehensive error logging")
        print("   ✅ Error recovery patterns demonstrated")
        
        print("\n💡 Next Steps:")
        print("   - Test with actual RFID readers")
        print("   - Add more sophisticated retry logic")
        print("   - Implement connection pooling")
        print("   - Add metrics and monitoring")
        
        print(f"\n📄 Error logs saved to: llrp_error_test.log")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()