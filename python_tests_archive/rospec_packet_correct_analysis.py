#!/usr/bin/env python3
"""
ROSpec 패킷 정확한 구조 분석
==========================

우리가 FR900에서 성공한 98바이트 ROSpec 패킷을 LLRP 표준에 맞게 정확히 분석
"""

import struct

def analyze_rospec_correctly():
    """성공한 ROSpec 패킷을 LLRP 표준에 맞게 정확히 분석"""
    
    # 우리가 성공한 98바이트 ROSpec 데이터
    rospec_hex = (
        "00b10062000004d2000000b2001200b300050000b60009000000000000b70046"
        "0001000100b80009000000000000ba003504d20100de002e000100df00060001"
        "00e0000a000100010078014a001800014f0008000100000150000b00001e0000"
        "0000"
    )
    
    rospec_data = bytes.fromhex(rospec_hex)
    print("=" * 80)
    print("FR900 성공 ROSpec 패킷 정확한 분석")
    print("=" * 80)
    print(f"전체 패킷 크기: {len(rospec_data)} 바이트")
    print(f"16진수: {rospec_hex}")
    print()
    
    pos = 0
    
    # 1. ROSpec Parameter (0x00B1)
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]  # 빅 엔디안
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    rospec_id = struct.unpack('>L', rospec_data[pos+4:pos+8])[0]
    current_state = rospec_data[pos+8]
    
    print("1. 📋 ROSpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type}) - ROSpec")
    print(f"   길이: {param_length} 바이트")
    print(f"   ROSpec ID: {rospec_id}")
    print(f"   상태: {current_state} (0=Disabled)")
    print()
    pos = 9  # 헤더(4) + ROSpecID(4) + State(1) = 9
    
    # 2. ROBoundarySpec Parameter (0x00B2)
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print("2. 🔄 ROBoundarySpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type})")
    print(f"   길이: {param_length} 바이트")
    pos += 4
    
    # ROSpecStartTrigger (0x00B3)
    start_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    start_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    start_trigger = rospec_data[pos+4]
    print(f"   🚀 ROSpecStartTrigger:")
    print(f"     타입: 0x{start_type:04X}, 길이: {start_length}")
    print(f"     트리거: {start_trigger} (0=Immediate)")
    pos += 5
    
    # ROSpecStopTrigger (0x00B6) 
    stop_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    stop_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    stop_trigger = rospec_data[pos+4]
    print(f"   🛑 ROSpecStopTrigger:")
    print(f"     타입: 0x{stop_type:04X}, 길이: {stop_length}")
    print(f"     트리거: {stop_trigger} (0=Null)")
    pos += 9  # 길이가 9바이트
    print()
    
    # 3. AISpec Parameter (0x00B7)
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print("3. 📡 AISpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type})")
    print(f"   길이: {param_length} 바이트")
    pos += 4
    
    # AntennaID 개수와 리스트
    antenna_count = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    pos += 2
    antenna_ids = []
    for i in range(antenna_count):
        antenna_id = struct.unpack('>H', rospec_data[pos:pos+2])[0]
        antenna_ids.append(antenna_id)
        pos += 2
    print(f"   안테나 개수: {antenna_count}")
    print(f"   안테나 ID: {antenna_ids}")
    
    # AISpecStopTrigger (0x00B8)
    stop_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    stop_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    stop_trigger = rospec_data[pos+4]
    print(f"   🛑 AISpecStopTrigger:")
    print(f"     타입: 0x{stop_type:04X}, 길이: {stop_length}")
    print(f"     트리거: {stop_trigger} (0=Null)")
    pos += 9  # 길이가 9바이트
    
    # InventoryParameterSpec (0x00BA)
    inv_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    inv_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    inv_id = struct.unpack('>H', rospec_data[pos+4:pos+6])[0]
    protocol_id = rospec_data[pos+6]
    print(f"   📊 InventoryParameterSpec:")
    print(f"     타입: 0x{inv_type:04X}, 길이: {inv_length}")
    print(f"     ID: {inv_id}")
    print(f"     프로토콜: {protocol_id} (1=EPCGlobalClass1Gen2)")
    pos += 7
    print()
    
    # 4. ROReportSpec Parameter (0x00DE)
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    report_trigger = rospec_data[pos+4]
    n_value = struct.unpack('>H', rospec_data[pos+5:pos+7])[0]
    print("4. 📊 ROReportSpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type})")
    print(f"   길이: {param_length} 바이트")
    print(f"   리포트 트리거: {report_trigger} (1=Upon_N_Tags_Or_End_Of_ROSpec)")
    print(f"   N 값: {n_value} (태그 개수)")
    pos += 7
    
    # TagReportContentSelector (0x00DF)
    content_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    content_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print(f"   🏷️  TagReportContentSelector:")
    print(f"     타입: 0x{content_type:04X}, 길이: {content_length}")
    pos += 4
    
    # Enable 플래그들 - TV Parameters
    remaining_bytes = rospec_data[pos:]
    print(f"   📋 Enable 플래그들 (TV Parameters):")
    
    tv_pos = 0
    while tv_pos < len(remaining_bytes) - 1:
        tv_type = remaining_bytes[tv_pos]
        tv_value = remaining_bytes[tv_pos + 1]
        
        # TV 파라미터 의미 해석
        tv_meanings = {
            0x00: "Reserved/Padding",
            0x01: "EnableROSpecID", 
            0x02: "EnableSpecIndex",
            0x03: "EnableInventoryParameterSpecID",
            0x04: "EnableAntennaID", 
            0x05: "EnableChannelIndex",
            0x06: "EnablePeakRSSI",
            0x07: "EnableFirstSeenTimestamp",
            0x08: "EnableLastSeenTimestamp",
            0x09: "EnableTagSeenCount",
            # ... 더 많은 TV 타입들
        }
        
        meaning = tv_meanings.get(tv_type, f"Unknown_0x{tv_type:02X}")
        print(f"     TV 0x{tv_type:02X}: {meaning} = {tv_value}")
        tv_pos += 2
    
    print()
    print("=" * 80)
    print("🎯 핵심 설정 요약")
    print("=" * 80)
    print(f"ROSpec ID: {rospec_id}")
    print(f"시작: Immediate (즉시 시작)")
    print(f"종료: Null (무한 실행)")
    print(f"안테나: {antenna_ids if antenna_ids else '모든 안테나'}")
    print(f"프로토콜: EPCGlobalClass1Gen2")
    print(f"리포트: {n_value}개 태그마다 보고")
    print(f"패킷 크기: {len(rospec_data)} 바이트")

def show_parameter_types():
    """LLRP 파라미터 타입들"""
    print("\n" + "=" * 80)
    print("📚 LLRP Parameter Types (16진수)")
    print("=" * 80)
    
    types = {
        0x00B1: "ROSpec_Parameter",
        0x00B2: "ROBoundarySpec_Parameter", 
        0x00B3: "ROSpecStartTrigger_Parameter",
        0x00B6: "ROSpecStopTrigger_Parameter",
        0x00B7: "AISpec_Parameter",
        0x00B8: "AISpecStopTrigger_Parameter",
        0x00BA: "InventoryParameterSpec_Parameter",
        0x00DE: "ROReportSpec_Parameter",
        0x00DF: "TagReportContentSelector_Parameter",
        0x00E0: "AISpecStopTriggerType",
        # TV Parameters는 1바이트
        0x01: "EnableROSpecID (TV)",
        0x02: "EnableSpecIndex (TV)",
        0x03: "EnableInventoryParameterSpecID (TV)",
        0x04: "EnableAntennaID (TV)",
        0x05: "EnableChannelIndex (TV)", 
        0x06: "EnablePeakRSSI (TV)",
        0x07: "EnableFirstSeenTimestamp (TV)",
        0x08: "EnableLastSeenTimestamp (TV)",
        0x09: "EnableTagSeenCount (TV)",
    }
    
    for type_id, description in types.items():
        if type_id < 0x100:  # TV Parameter
            print(f"  0x{type_id:02X}: {description}")
        else:  # TLV Parameter
            print(f"0x{type_id:04X}: {description}")

def why_this_rospec_works():
    """이 ROSpec이 FR900에서 작동하는 이유"""
    print("\n" + "=" * 80)
    print("✅ 이 ROSpec이 FR900에서 성공하는 이유")
    print("=" * 80)
    
    reasons = [
        "1. 올바른 LLRP 1.1 표준 준수",
        "2. 필수 파라미터 모두 포함",
        "3. 정확한 TLV 구조 (Type-Length-Value)",
        "4. 적절한 바이트 정렬",
        "5. EPCGlobalClass1Gen2 프로토콜 명시", 
        "6. TV 파라미터로 리포트 내용 제어",
        "7. FR900이 이해할 수 있는 파라미터 조합",
        "8. 무한 실행 설정 (Null 트리거)",
        "9. 즉시 시작 설정 (Immediate 트리거)",
        "10. 적절한 패킷 크기 (98 바이트)"
    ]
    
    for reason in reasons:
        print(f"  {reason}")
    
    print("\n💡 핵심: FR900은 표준 LLRP를 완벽 지원하므로")
    print("   표준에 맞게 구성된 이 ROSpec을 성공적으로 처리합니다!")

if __name__ == "__main__":
    analyze_rospec_correctly()
    show_parameter_types()
    why_this_rospec_works()