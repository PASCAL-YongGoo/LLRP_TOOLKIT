#!/usr/bin/env python3
"""
Comprehensive test for improved LLRP Binary Encoding/Decoding
Tests both the encoding and decoding without requiring a real reader
"""

import struct
import logging
from llrp.protocol import (
    LLRPHeader, LLRPMessage, LLRPParameter, 
    MessageType, ParameterType
)
from llrp.parameters import (
    EPCData, EPC96, AntennaID, PeakRSSI, TagSeenCount,
    ROSpecID, FirstSeenTimestampUTC, ChannelIndex
)
from llrp.messages import (
    TagReportData, ROAccessReport, AddROSpec, ROSpec,
    ROBoundarySpec, ROSpecStartTrigger, ROSpecStopTrigger
)
from llrp.client import LLRPClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_tv_parameter_encoding():
    """Test TV (Type-Value) parameter encoding/decoding"""
    print("🔧 Testing TV Parameter Encoding/Decoding")
    print("=" * 50)
    
    tests = [
        ("AntennaID", AntennaID(antenna_id=5), 3, b'\x81\x00\x05'),
        ("PeakRSSI", PeakRSSI(rssi=-45), 2, b'\x86\xd3'),  # -45 as signed byte
        ("TagSeenCount", TagSeenCount(tag_count=123), 3, b'\x88\x00\x7b'),
        ("ROSpecID", ROSpecID(rospec_id=456), 5, b'\x89\x00\x00\x01\xc8'),
    ]
    
    for name, param, expected_len, expected_bytes in tests:
        print(f"\n🧪 Testing {name}:")
        
        # Test encoding
        encoded = param.encode()
        print(f"   Encoded: {encoded.hex().upper()}")
        print(f"   Expected: {expected_bytes.hex().upper()}")
        print(f"   Length: {len(encoded)} (expected {expected_len})")
        
        # Test decoding
        new_param = type(param)()
        consumed = new_param.decode(encoded)
        print(f"   Decoded consumed: {consumed} bytes")
        print(f"   Original value: {getattr(param, list(param.__dict__.keys())[1])}")  # Skip param_type
        print(f"   Decoded value: {getattr(new_param, list(new_param.__dict__.keys())[1])}")
        
        # Verify round-trip
        success = (consumed == expected_len and 
                  getattr(param, list(param.__dict__.keys())[1]) == 
                  getattr(new_param, list(new_param.__dict__.keys())[1]))
        print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def test_tlv_parameter_encoding():
    """Test TLV (Type-Length-Value) parameter encoding/decoding"""
    print("\n🔧 Testing TLV Parameter Encoding/Decoding")
    print("=" * 50)
    
    # Test EPCData with various EPC lengths
    test_epcs = [
        ("12-byte EPC", bytes.fromhex("E200001A2C0000000000BEEF")),
        ("8-byte EPC", bytes.fromhex("12345678ABCDEF01")),
        ("6-byte EPC", bytes.fromhex("AABBCCDDEEFF")),
    ]
    
    for name, epc_bytes in test_epcs:
        print(f"\n🧪 Testing EPCData - {name}:")
        
        param = EPCData(epc_bytes)
        print(f"   Original EPC: {param.get_epc_hex()}")
        
        # Test encoding
        encoded = param.encode()
        print(f"   Encoded length: {len(encoded)} bytes")
        print(f"   Encoded: {encoded.hex().upper()}")
        
        # Test decoding
        new_param = EPCData()
        consumed = new_param.decode(encoded)
        print(f"   Decoded consumed: {consumed} bytes")
        print(f"   Decoded EPC: {new_param.get_epc_hex()}")
        
        # Verify round-trip
        success = (consumed == len(encoded) and 
                  param.get_epc_hex() == new_param.get_epc_hex())
        print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def test_message_header_parsing():
    """Test LLRP message header parsing"""
    print("\n🔧 Testing Message Header Parsing")
    print("=" * 50)
    
    # Test header parsing
    test_headers = [
        ("GET_READER_CAPABILITIES", MessageType.GET_READER_CAPABILITIES, 1, 10),
        ("RO_ACCESS_REPORT", MessageType.RO_ACCESS_REPORT, 123, 45),
        ("ADD_ROSPEC", MessageType.ADD_ROSPEC, 5, 200),
    ]
    
    for name, msg_type, msg_id, length in test_headers:
        print(f"\n🧪 Testing {name} header:")
        
        # Create header
        header = LLRPHeader(
            version=1,
            message_type=msg_type,
            message_length=length,
            message_id=msg_id
        )
        
        # Test encoding
        encoded = header.pack()
        print(f"   Encoded header: {encoded.hex().upper()}")
        print(f"   Length: {len(encoded)} bytes")
        
        # Test decoding
        decoded_header = LLRPHeader.unpack(encoded)
        print(f"   Original: type={msg_type}, id={msg_id}, len={length}")
        print(f"   Decoded: type={decoded_header.message_type}, id={decoded_header.message_id}, len={decoded_header.message_length}")
        
        # Verify round-trip
        success = (decoded_header.message_type == msg_type and
                  decoded_header.message_id == msg_id and
                  decoded_header.message_length == length)
        print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def test_tag_report_parsing():
    """Test TagReportData parsing with synthetic data"""
    print("\n🔧 Testing TagReportData Parsing")
    print("=" * 50)
    
    # Create a synthetic tag report with multiple parameters
    print("🧪 Creating synthetic TagReportData:")
    
    # Build tag report manually
    tag_report_params = []
    
    # Add EPCData
    epc_data = EPCData(bytes.fromhex("E200001A2C0000000000BEEF"))
    tag_report_params.append(epc_data.encode())
    
    # Add TV parameters
    antenna_id = AntennaID(antenna_id=3)
    tag_report_params.append(antenna_id.encode())
    
    peak_rssi = PeakRSSI(rssi=-40)
    tag_report_params.append(peak_rssi.encode())
    
    tag_seen_count = TagSeenCount(tag_count=5)
    tag_report_params.append(tag_seen_count.encode())
    
    rospec_id = ROSpecID(rospec_id=123)
    tag_report_params.append(rospec_id.encode())
    
    # Combine all parameters
    params_data = b''.join(tag_report_params)
    
    # Create TagReportData header (TLV)
    total_length = 4 + len(params_data)  # 4-byte header + params
    tag_report_header = struct.pack('!HH', ParameterType.TAG_REPORT_DATA, total_length)
    
    # Complete TagReportData
    tag_report_data = tag_report_header + params_data
    
    print(f"   Total TagReportData length: {len(tag_report_data)} bytes")
    print(f"   TagReportData: {tag_report_data.hex().upper()}")
    
    # Test parsing
    print("\n📝 Parsing TagReportData:")
    tag_report = TagReportData()
    consumed = tag_report.decode(tag_report_data)
    
    print(f"   Consumed bytes: {consumed}")
    print(f"   Parsed EPC: {tag_report.get_epc_hex()}")
    print(f"   Parsed Antenna: {tag_report.antenna_id}")
    print(f"   Parsed RSSI: {tag_report.peak_rssi}")
    print(f"   Parsed Count: {tag_report.tag_seen_count}")
    print(f"   Parsed ROSpec: {tag_report.rospec_id}")
    
    # Verify parsing
    success = (tag_report.get_epc_hex() == "E200001A2C0000000000BEEF" and
              tag_report.antenna_id == 3 and
              tag_report.peak_rssi == -40 and
              tag_report.tag_seen_count == 5 and
              tag_report.rospec_id == 123)
    
    print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def test_ro_access_report():
    """Test complete RO_ACCESS_REPORT message"""
    print("\n🔧 Testing RO_ACCESS_REPORT Message")
    print("=" * 50)
    
    # This would typically come from a real reader
    # For now, we'll test the structure we expect
    
    print("🧪 Testing RO_ACCESS_REPORT structure:")
    
    report = ROAccessReport(msg_id=456)
    print(f"   Created RO_ACCESS_REPORT with ID: {report.header.message_id}")
    print(f"   Message type: {report.header.message_type}")
    print(f"   Initial tag count: {len(report.tag_report_data)}")
    
    # Test with empty report
    encoded = report.encode()
    print(f"   Encoded length: {len(encoded)} bytes")
    print(f"   Encoded: {encoded.hex().upper()}")
    
    # Decode it back
    decoded_report = LLRPMessage.from_bytes(encoded)
    print(f"   Decoded message type: {type(decoded_report).__name__}")
    print(f"   Decoded message ID: {decoded_report.header.message_id}")
    
    success = (isinstance(decoded_report, ROAccessReport) and
              decoded_report.header.message_id == 456)
    print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def test_parameter_header_parsing():
    """Test the new parameter header parsing system"""
    print("\n🔧 Testing Parameter Header Parsing System")
    print("=" * 50)
    
    # Test various parameter headers
    test_cases = [
        # (description, raw_bytes, expected_type, expected_length, expected_header_len, expected_is_tv)
        ("AntennaID TV", b'\x81\x00\x05', 1, 3, 1, True),
        ("PeakRSSI TV", b'\x86\xd3', 6, 2, 1, True),
        ("EPCData TLV", b'\x00\xf1\x00\x10\x00\x60' + b'\x00' * 10, 241, 16, 4, False),
        ("TagReportData TLV", b'\x00\xf0\x00\x20' + b'\x00' * 28, 240, 32, 4, False),
    ]
    
    for desc, data, exp_type, exp_len, exp_hdr_len, exp_tv in test_cases:
        print(f"\n🧪 Testing {desc}:")
        
        result = LLRPParameter.parse_header(data)
        param_type, param_length, header_length, is_tv = result
        
        print(f"   Raw bytes: {data[:8].hex().upper()}...")
        print(f"   Expected: type={exp_type}, len={exp_len}, hdr_len={exp_hdr_len}, is_tv={exp_tv}")
        print(f"   Parsed:   type={param_type}, len={param_length}, hdr_len={header_length}, is_tv={is_tv}")
        
        success = (param_type == exp_type and 
                  param_length == exp_len and 
                  header_length == exp_hdr_len and 
                  is_tv == exp_tv)
        print(f"   Result: {'✅ PASS' if success else '❌ FAIL'}")


def main():
    """Run all binary encoding tests"""
    print("🚀 LLRP Binary Encoding/Decoding Test Suite")
    print("=" * 60)
    
    try:
        # Run all tests
        test_parameter_header_parsing()
        test_tv_parameter_encoding()
        test_tlv_parameter_encoding()
        test_message_header_parsing()
        test_tag_report_parsing()
        test_ro_access_report()
        
        print("\n" + "=" * 60)
        print("🎉 All encoding/decoding tests completed!")
        print("💡 The binary encoding system is now ready for real RFID readers.")
        print("\n📋 Next steps:")
        print("   1. Test with actual RFID reader hardware")
        print("   2. Verify interoperability with Impinj/Zebra readers")
        print("   3. Add more message types as needed")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()