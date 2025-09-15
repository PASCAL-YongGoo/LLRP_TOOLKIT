#!/usr/bin/env python3
"""
ROSpec 패킷 구조 분석
===================

우리가 FR900에서 성공한 98바이트 ROSpec 패킷을 상세히 분석
"""

import struct

def analyze_rospec_packet():
    """성공한 ROSpec 패킷 분석"""
    
    # 우리가 성공한 98바이트 ROSpec 데이터
    rospec_hex = (
        "00b10062000004d2000000b2001200b300050000b60009000000000000b70046"
        "0001000100b80009000000000000ba003504d20100de002e000100df00060001"
        "00e0000a000100010078014a001800014f0008000100000150000b00001e0000"
        "0000"
    )
    
    rospec_data = bytes.fromhex(rospec_hex)
    print(f"전체 ROSpec 패킷 크기: {len(rospec_data)} 바이트")
    print(f"16진수 데이터: {rospec_hex}")
    print()
    
    # 패킷을 단계별로 분석
    pos = 0
    
    print("=" * 80)
    print("ROSpec 패킷 상세 분석")
    print("=" * 80)
    
    # 1. ROSpec Parameter 헤더 (TLV)
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print(f"1. ROSpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type}) - ROSpec_Parameter")
    print(f"   길이: {param_length} 바이트")
    pos += 4
    
    # ROSpec ID와 Current State
    rospec_id = struct.unpack('>L', rospec_data[pos:pos+4])[0]
    current_state = rospec_data[pos+4]
    print(f"   ROSpec ID: {rospec_id} (0x{rospec_id:04X})")
    print(f"   Current State: {current_state} (0=Disabled)")
    pos += 5
    print()
    
    # 2. ROBoundarySpec Parameter
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print(f"2. ROBoundarySpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type}) - ROBoundarySpec_Parameter")
    print(f"   길이: {param_length} 바이트")
    pos += 4
    
    # ROSpecStartTrigger
    start_trigger_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    start_trigger_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    start_trigger_value = rospec_data[pos+4]
    print(f"   ROSpecStartTrigger:")
    print(f"     타입: 0x{start_trigger_type:04X}, 길이: {start_trigger_length}")
    print(f"     값: {start_trigger_value} (0=Immediate)")
    pos += 5
    
    # ROSpecStopTrigger
    stop_trigger_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    stop_trigger_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    stop_trigger_value = rospec_data[pos+4]
    print(f"   ROSpecStopTrigger:")
    print(f"     타입: 0x{stop_trigger_type:04X}, 길이: {stop_trigger_length}")
    print(f"     값: {stop_trigger_value} (0=Null)")
    pos += 5
    print()
    
    # 3. AISpec Parameter
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print(f"3. AISpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type}) - AISpec_Parameter")
    print(f"   길이: {param_length} 바이트")
    pos += 4
    
    # Antenna ID 리스트
    antenna_count = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    pos += 2
    antenna_ids = []
    for i in range(antenna_count):
        antenna_id = struct.unpack('>H', rospec_data[pos:pos+2])[0]
        antenna_ids.append(antenna_id)
        pos += 2
    print(f"   안테나 ID 개수: {antenna_count}")
    print(f"   안테나 ID들: {antenna_ids}")
    
    # AISpecStopTrigger
    stop_trigger_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    stop_trigger_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    stop_trigger_value = rospec_data[pos+4]
    print(f"   AISpecStopTrigger:")
    print(f"     타입: 0x{stop_trigger_type:04X}, 길이: {stop_trigger_length}")
    print(f"     값: {stop_trigger_value} (0=Null)")
    pos += 5
    
    # InventoryParameterSpec
    inv_param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    inv_param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    inv_param_id = struct.unpack('>H', rospec_data[pos+4:pos+6])[0]
    protocol_id = rospec_data[pos+6]
    print(f"   InventoryParameterSpec:")
    print(f"     타입: 0x{inv_param_type:04X}, 길이: {inv_param_length}")
    print(f"     ID: {inv_param_id}")
    print(f"     프로토콜 ID: {protocol_id} (1=EPCGlobalClass1Gen2)")
    pos += 7
    print()
    
    # 4. ROReportSpec Parameter
    param_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    param_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    report_trigger = rospec_data[pos+4]
    n_value = struct.unpack('>H', rospec_data[pos+5:pos+7])[0]
    print(f"4. ROReportSpec Parameter")
    print(f"   타입: 0x{param_type:04X} ({param_type}) - ROReportSpec_Parameter")
    print(f"   길이: {param_length} 바이트")
    print(f"   리포트 트리거: {report_trigger} (1=Upon_N_Tags_Or_End_Of_ROSpec)")
    print(f"   N 값: {n_value}")
    pos += 7
    
    # TagReportContentSelector
    content_type = struct.unpack('>H', rospec_data[pos:pos+2])[0]
    content_length = struct.unpack('>H', rospec_data[pos+2:pos+4])[0]
    print(f"   TagReportContentSelector:")
    print(f"     타입: 0x{content_type:04X}, 길이: {content_length}")
    pos += 4
    
    # Enable 플래그들 - TV 파라미터들
    enable_flags = rospec_data[pos:pos+content_length-4]
    print(f"     Enable 플래그들 ({len(enable_flags)} 바이트):")
    
    # TV 파라미터 파싱
    flag_pos = 0
    while flag_pos < len(enable_flags):
        if flag_pos + 1 < len(enable_flags):
            tv_type = enable_flags[flag_pos]
            tv_value = enable_flags[flag_pos + 1]
            
            tv_descriptions = {
                0x4F: "EnableROSpecID",
                0x50: "EnableInventoryParameterSpecID", 
                # 추가 TV 타입들...
            }
            
            desc = tv_descriptions.get(tv_type, f"Unknown_TV_Type_0x{tv_type:02X}")
            print(f"       TV 타입 0x{tv_type:02X}: {desc} = {tv_value}")
            flag_pos += 2
        else:
            break
    
    pos += content_length - 4
    print()
    
    print("=" * 80)
    print("분석 완료!")
    print("=" * 80)
    
    # 핵심 설정 요약
    print("핵심 ROSpec 설정 요약:")
    print(f"• ROSpec ID: {rospec_id}")
    print(f"• 시작 트리거: Immediate (즉시 시작)")
    print(f"• 중지 트리거: Null (무한 실행)")
    print(f"• 안테나: {antenna_ids}")
    print(f"• 프로토콜: EPCGlobalClass1Gen2")
    print(f"• 리포트: N={n_value}개 태그마다 보고")
    print(f"• 전체 패킷 크기: {len(rospec_data)} 바이트")

def compare_with_standard():
    """LLRP 표준과 비교"""
    print("\n" + "=" * 80)
    print("LLRP 표준 구조와 비교")
    print("=" * 80)
    
    print("LLRP Parameter 구조:")
    print("• TLV (Type-Length-Value) 형식")
    print("• 타입: 2바이트 (파라미터 종류 식별)")
    print("• 길이: 2바이트 (전체 파라미터 길이)")
    print("• 값: 가변 길이 (실제 데이터)")
    print()
    
    print("ROSpec의 계층 구조:")
    print("1. ROSpec_Parameter")
    print("   ├── ROSpecID (4바이트)")
    print("   ├── CurrentState (1바이트)")
    print("   ├── ROBoundarySpec_Parameter")
    print("   │   ├── ROSpecStartTrigger_Parameter")
    print("   │   └── ROSpecStopTrigger_Parameter")
    print("   ├── AISpec_Parameter")
    print("   │   ├── AntennaIDs (가변 길이)")
    print("   │   ├── AISpecStopTrigger_Parameter")
    print("   │   └── InventoryParameterSpec_Parameter")
    print("   └── ROReportSpec_Parameter")
    print("       ├── ROReportTrigger (1바이트)")
    print("       ├── N (2바이트)")
    print("       └── TagReportContentSelector_Parameter")
    print()
    
    print("FR900이 성공적으로 처리하는 이 패킷의 특징:")
    print("• 모든 필수 파라미터 포함")
    print("• 올바른 TLV 구조")
    print("• 적절한 길이 계산") 
    print("• EPCGlobalClass1Gen2 프로토콜 지정")
    print("• TV 파라미터로 리포트 내용 제어")

if __name__ == "__main__":
    analyze_rospec_packet()
    compare_with_standard()