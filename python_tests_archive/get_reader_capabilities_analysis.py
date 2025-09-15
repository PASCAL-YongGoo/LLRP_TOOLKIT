#!/usr/bin/env python3
"""
GET_READER_CAPABILITIES 패킷 분석
===============================

04 01 00 00 00 0b 00 00 00 01 00 패킷을 상세 분석
"""

import struct

def analyze_get_reader_capabilities():
    """GET_READER_CAPABILITIES 패킷 분석"""
    
    # 패킷 데이터
    packet_hex = "04 01 00 00 00 0b 00 00 00 01 00"
    packet_data = bytes.fromhex(packet_hex.replace(' ', ''))
    
    print("=" * 80)
    print("GET_READER_CAPABILITIES 패킷 분석")
    print("=" * 80)
    print(f"패킷 크기: {len(packet_data)} 바이트")
    print(f"16진수: {packet_hex}")
    print()
    
    pos = 0
    
    # 1. LLRP 메시지 헤더 (10바이트)
    print("1. 📡 LLRP 메시지 헤더 (10바이트)")
    msg_type_field = struct.unpack('>H', packet_data[pos:pos+2])[0]
    msg_length = struct.unpack('>I', packet_data[pos+2:pos+6])[0]
    msg_id = struct.unpack('>I', packet_data[pos+6:pos+10])[0]
    
    # 메시지 타입 추출
    msg_version = (msg_type_field >> 10) & 0x7
    msg_type = msg_type_field & 0xFF
    
    print(f"   메시지 타입 필드: 0x{msg_type_field:04X}")
    print(f"   - 버전: {msg_version}")
    print(f"   - 타입: 0x{msg_type:02X} ({msg_type} = GET_READER_CAPABILITIES)")
    print(f"   메시지 길이: {msg_length} 바이트")
    print(f"   메시지 ID: {msg_id}")
    print()
    
    pos = 10
    
    # 2. 페이로드 분석 (1바이트)
    if pos < len(packet_data):
        print("2. 📋 페이로드")
        payload = packet_data[pos:]
        print(f"   페이로드 크기: {len(payload)} 바이트")
        print(f"   페이로드 데이터: {payload.hex()}")
        
        if len(payload) >= 1:
            requested_data = payload[0]
            print(f"   RequestedData: 0x{requested_data:02X} ({requested_data})")
            
            # RequestedData 값 해석
            data_meanings = {
                0: "All - 모든 리더 정보",
                1: "General Device Capabilities",
                2: "LLRP Capabilities", 
                3: "Regulatory Capabilities",
                4: "Air Protocol LLRP Capabilities"
            }
            
            meaning = data_meanings.get(requested_data, f"Unknown({requested_data})")
            print(f"   의미: {meaning}")
    else:
        print("2. 📋 페이로드")
        print("   페이로드 없음 (헤더만 있음)")
    
    print()
    print("=" * 80)
    print("📊 분석 요약")
    print("=" * 80)
    print(f"🔹 메시지 타입: GET_READER_CAPABILITIES (0x{msg_type:02X})")
    print(f"🔹 메시지 ID: {msg_id}")
    print(f"🔹 전체 크기: {msg_length} 바이트")
    print(f"🔹 요청 데이터: 모든 리더 정보 (All)")
    print(f"🔹 의미: 리더의 모든 기능 정보 요청")
    print(f"🔹 용도: 리더가 지원하는 기능들을 확인")

def show_llrp_request_flow():
    """LLRP 요청 흐름 설명"""
    print("\n" + "=" * 80)
    print("🔄 LLRP 통신 흐름에서의 위치")
    print("=" * 80)
    
    flow = [
        ("1. TCP 연결", "Client → Reader"),
        ("2. READER_EVENT_NOTIFICATION", "Reader → Client"),
        ("3. GET_READER_CAPABILITIES", "Client → Reader ← 현재 분석 중"),
        ("4. GET_READER_CAPABILITIES_RESPONSE", "Reader → Client"),
        ("5. SET_READER_CONFIG", "Client → Reader"),
        ("6. SET_READER_CONFIG_RESPONSE", "Reader → Client"),
        ("7. ADD_ROSPEC", "Client → Reader"),
        ("8. ADD_ROSPEC_RESPONSE", "Reader → Client"),
        ("9. ENABLE_ROSPEC", "Client → Reader"),
        ("10. START_ROSPEC", "Client → Reader"),
        ("11. RO_ACCESS_REPORT", "Reader → Client (태그 데이터)")
    ]
    
    for step, direction in flow:
        marker = " ← 현재" if "GET_READER_CAPABILITIES" in step and "Client → Reader" in direction else ""
        print(f"   {step}: {direction}{marker}")

def show_expected_response():
    """예상되는 응답"""
    print("\n" + "=" * 80)
    print("📨 예상되는 응답")
    print("=" * 80)
    
    print("GET_READER_CAPABILITIES_RESPONSE (0x0B)에 포함될 정보:")
    print("   • General Device Capabilities")
    print("     - 제조사 정보, 모델명, 소프트웨어 버전")
    print("     - 지원 안테나 개수, 전송 파워 범위")
    print("   • LLRP Capabilities") 
    print("     - 지원하는 LLRP 버전")
    print("     - 최대 ROSpec 개수, 최대 AccessSpec 개수")
    print("   • Regulatory Capabilities")
    print("     - 지원 주파수 대역, 출력 파워 제한")
    print("   • Air Protocol Capabilities")
    print("     - 지원하는 EPC 프로토콜 (Gen2 등)")
    print("     - 태그 메모리 접근 기능")

def show_esitarski_equivalent():
    """esitarski/pyllrp 동등 코드"""
    print("\n" + "=" * 80)
    print("🐍 esitarski/pyllrp 동등 코드")
    print("=" * 80)
    
    code = '''
# esitarski/pyllrp로 동일한 요청 생성
from esitarski_pyllrp.pyllrp.pyllrp import *

# GET_READER_CAPABILITIES 메시지 생성
message = GET_READER_CAPABILITIES_Message(
    MessageID=1,  # 메시지 ID
    RequestedData=GetReaderCapabilitiesRequestedData.All  # 모든 정보 요청
)

# 전송
response = connector.transact(message)

# 응답에서 정보 추출
if response.success():
    # 리더 기능 정보 활용
    capabilities = response.getReaderCapabilities()
    print(f"리더 정보: {capabilities}")
'''
    
    print(code)

if __name__ == "__main__":
    analyze_get_reader_capabilities()
    show_llrp_request_flow()
    show_expected_response()
    show_esitarski_equivalent()