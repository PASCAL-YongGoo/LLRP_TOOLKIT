#!/usr/bin/env python3
"""
READER_EVENT_NOTIFICATION 패킷 분석
=================================

FR900에서 수신한 READER_EVENT_NOTIFICATION 패킷을 상세 분석
"""

import struct
from datetime import datetime

def analyze_reader_event_notification():
    """READER_EVENT_NOTIFICATION 패킷 분석"""
    
    # 패킷 데이터 (LLRP 부분만)
    packet_hex = "04 3f 00 00 00 20 00 00 00 00 00 f6 00 16 00 80 00 0c 00 06 3e 90 aa b9 cc e0 01 00 00 06 00 00"
    packet_data = bytes.fromhex(packet_hex.replace(' ', ''))
    
    print("=" * 80)
    print("READER_EVENT_NOTIFICATION 패킷 분석")
    print("=" * 80)
    print(f"패킷 크기: {len(packet_data)} 바이트")
    print(f"16진수: {packet_hex}")
    print()
    
    pos = 0
    
    # 1. LLRP 메시지 헤더 (10바이트)
    print("1. 📡 LLRP 메시지 헤더")
    msg_type_field = struct.unpack('>H', packet_data[pos:pos+2])[0]
    msg_length = struct.unpack('>I', packet_data[pos+2:pos+6])[0]
    msg_id = struct.unpack('>I', packet_data[pos+6:pos+10])[0]
    
    # 메시지 타입 추출
    msg_version = (msg_type_field >> 10) & 0x7
    msg_type = msg_type_field & 0xFF
    
    print(f"   메시지 타입 필드: 0x{msg_type_field:04X}")
    print(f"   - 버전: {msg_version}")
    print(f"   - 타입: 0x{msg_type:02X} ({msg_type} = READER_EVENT_NOTIFICATION)")
    print(f"   메시지 길이: {msg_length} 바이트")
    print(f"   메시지 ID: {msg_id}")
    print()
    
    pos = 10
    
    # 2. ReaderEventNotificationData Parameter
    print("2. 📋 ReaderEventNotificationData Parameter")
    param_type = struct.unpack('>H', packet_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', packet_data[pos+2:pos+4])[0]
    
    print(f"   파라미터 타입: 0x{param_type:04X} ({param_type})")
    print(f"   파라미터 길이: {param_length} 바이트")
    
    pos += 4
    
    # 3. 내부 파라미터들 분석
    remaining_data = packet_data[pos:]
    print(f"   내부 파라미터 데이터 ({len(remaining_data)} 바이트):")
    print(f"   {remaining_data.hex()}")
    print()
    
    # 내부 파라미터 파싱
    inner_pos = 0
    while inner_pos < len(remaining_data):
        if inner_pos + 4 > len(remaining_data):
            break
            
        inner_type = struct.unpack('>H', remaining_data[inner_pos:inner_pos+2])[0]
        inner_length = struct.unpack('>H', remaining_data[inner_pos+2:inner_pos+4])[0]
        
        print(f"3. 📊 내부 파라미터")
        print(f"   타입: 0x{inner_type:04X} ({inner_type})")
        print(f"   길이: {inner_length} 바이트")
        
        # 파라미터 타입별 해석
        if inner_type == 0x0080:  # UTCTimestamp
            if inner_length >= 12 and inner_pos + inner_length <= len(remaining_data):
                timestamp_data = remaining_data[inner_pos+4:inner_pos+inner_length]
                if len(timestamp_data) >= 8:
                    microseconds = struct.unpack('>Q', timestamp_data[:8])[0]
                    timestamp = datetime.utcfromtimestamp(microseconds / 1000000.0)
                    print(f"   📅 UTCTimestamp:")
                    print(f"     마이크로초: {microseconds}")
                    print(f"     UTC 시간: {timestamp}")
        
        elif inner_type == 0x0006:  # ConnectionAttemptEvent  
            print(f"   🔗 ConnectionAttemptEvent:")
            if inner_length >= 5 and inner_pos + inner_length <= len(remaining_data):
                status_data = remaining_data[inner_pos+4:inner_pos+inner_length]
                if len(status_data) >= 1:
                    status = status_data[0]
                    status_meanings = {
                        0: "Success",
                        1: "Failed_A_Reader_Initiated_Connection_Already_Exists", 
                        2: "Failed_A_Client_Initiated_Connection_Already_Exists",
                        3: "Failed_Any_Other_Connection_Already_Exists",
                        4: "Failed_Parameter_Error",
                        5: "Failed_Reader_Transient_Error",
                        6: "Failed_Reader_Permanent_Error"
                    }
                    status_text = status_meanings.get(status, f"Unknown({status})")
                    print(f"     상태: {status} ({status_text})")
        
        else:
            print(f"   ❓ 알려지지 않은 파라미터 타입")
            if inner_pos + inner_length <= len(remaining_data):
                param_data = remaining_data[inner_pos+4:inner_pos+inner_length]
                print(f"   데이터: {param_data.hex()}")
        
        print()
        inner_pos += inner_length
        
    print("=" * 80)
    print("📊 분석 요약")
    print("=" * 80)
    print(f"🔹 메시지 타입: READER_EVENT_NOTIFICATION (0x{msg_type:02X})")
    print(f"🔹 메시지 ID: {msg_id}")
    print(f"🔹 전체 크기: {msg_length} 바이트")
    print(f"🔹 의미: 리더 연결 이벤트 알림")
    print(f"🔹 용도: 연결 성공/실패 상태 보고")
    
def show_llrp_message_types():
    """LLRP 메시지 타입 참조표"""
    print("\n" + "=" * 80)
    print("📚 LLRP 메시지 타입 참조표")
    print("=" * 80)
    
    message_types = {
        0x01: "GET_READER_CAPABILITIES",
        0x0B: "GET_READER_CAPABILITIES_RESPONSE", 
        0x03: "SET_READER_CONFIG",
        0x0D: "SET_READER_CONFIG_RESPONSE",
        0x14: "ADD_ROSPEC",
        0x1E: "ADD_ROSPEC_RESPONSE",
        0x18: "ENABLE_ROSPEC", 
        0x22: "ENABLE_ROSPEC_RESPONSE",
        0x16: "START_ROSPEC",
        0x20: "START_ROSPEC_RESPONSE",
        0x17: "STOP_ROSPEC",
        0x21: "STOP_ROSPEC_RESPONSE",
        0x19: "DISABLE_ROSPEC",
        0x23: "DISABLE_ROSPEC_RESPONSE",
        0x15: "DELETE_ROSPEC",
        0x1F: "DELETE_ROSPEC_RESPONSE",
        0x3E: "KEEPALIVE",
        0x48: "KEEPALIVE_ACK",
        0x3F: "READER_EVENT_NOTIFICATION",  # 현재 분석 중인 메시지
        0x04: "CLOSE_CONNECTION",
        0x0E: "CLOSE_CONNECTION_RESPONSE",
        0x3D: "RO_ACCESS_REPORT"  # 태그 데이터 리포트
    }
    
    for msg_type, description in sorted(message_types.items()):
        marker = " ← 현재 분석" if msg_type == 0x3F else ""
        print(f"  0x{msg_type:02X} ({msg_type:2d}): {description}{marker}")

def show_parameter_types():
    """LLRP 파라미터 타입 참조표"""
    print("\n" + "=" * 80)
    print("📚 LLRP 파라미터 타입 참조표")
    print("=" * 80)
    
    param_types = {
        0x00F6: "ReaderEventNotificationData",
        0x0080: "UTCTimestamp", 
        0x0006: "ConnectionAttemptEvent",
        0x0007: "AntennaEvent",
        0x0008: "HoppingEvent",
        0x0009: "GPIOEvent",
        0x000A: "ROSpecEvent",
        0x000B: "ReportBufferLevelWarningEvent",
        0x000C: "ReportBufferOverflowErrorEvent",
        0x000D: "ReaderExceptionEvent",
        0x000E: "RFSurveyEvent",
        0x000F: "AISpecEvent",
        0x0010: "ConnectionCloseEvent"
    }
    
    for param_type, description in sorted(param_types.items()):
        marker = " ← 현재 분석" if param_type in [0x00F6, 0x0080, 0x0006] else ""
        print(f"  0x{param_type:04X} ({param_type:3d}): {description}{marker}")

if __name__ == "__main__":
    analyze_reader_event_notification()
    show_llrp_message_types()
    show_parameter_types()