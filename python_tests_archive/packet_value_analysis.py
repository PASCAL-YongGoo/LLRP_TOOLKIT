#!/usr/bin/env python3
"""
성공한 패킷의 각 값 분석 및 의미 파악
=======================================

우리가 성공한 ADD_ROSPEC 패킷을 바이트별로 분석하여
각 값이 무엇을 의미하는지 파악하고, esitarski/pyllrp 변수에 매핑
"""

import struct

def analyze_successful_packet():
    """성공한 ADD_ROSPEC 패킷 상세 분석"""
    
    # 우리가 성공한 전체 ADD_ROSPEC 패킷 (LLRP 헤더 포함)
    full_packet_hex = "04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00 00 00"
    
    packet_bytes = bytes.fromhex(full_packet_hex.replace(' ', ''))
    
    print("=" * 80)
    print("성공한 ADD_ROSPEC 패킷 바이트별 분석")
    print("=" * 80)
    print(f"전체 패킷 크기: {len(packet_bytes)} 바이트")
    print()
    
    pos = 0
    
    # 1. LLRP 메시지 헤더 분석
    print("1. 📡 LLRP 메시지 헤더 (10 바이트)")
    msg_type_raw = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    msg_type = msg_type_raw & 0xFF  # 하위 8비트
    msg_version = (msg_type_raw >> 10) & 0x7  # 상위 3비트
    msg_length = struct.unpack('>I', packet_bytes[pos+2:pos+6])[0]
    msg_id = struct.unpack('>I', packet_bytes[pos+6:pos+10])[0]
    
    print(f"   메시지 타입 필드: 0x{msg_type_raw:04X}")
    print(f"   - 버전: {msg_version}")
    print(f"   - 타입: 0x{msg_type:02X} (20 = ADD_ROSPEC)")
    print(f"   메시지 길이: {msg_length} 바이트")
    print(f"   메시지 ID: {msg_id}")
    
    # esitarski/pyllrp 매핑
    print("\n   🔗 esitarski/pyllrp 매핑:")
    print(f"   ADD_ROSPEC_Message(MessageID={msg_id}, Parameters=[...])")
    
    pos += 10
    print()
    
    # 2. ROSpec Parameter 분석
    print("2. 📋 ROSpec Parameter")
    rospec_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    rospec_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    rospec_id = struct.unpack('>I', packet_bytes[pos+4:pos+8])[0]
    current_state = packet_bytes[pos+8]
    reserved = packet_bytes[pos+9]
    
    print(f"   타입: 0x{rospec_type:04X} (0x00B1 = ROSpec_Parameter)")
    print(f"   길이: {rospec_length} 바이트")
    print(f"   ROSpec ID: {rospec_id}")
    print(f"   현재 상태: {current_state} (0=Disabled)")
    print(f"   예약 필드: 0x{reserved:02X}")
    
    # esitarski/pyllrp 매핑
    print("\n   🔗 esitarski/pyllrp 매핑:")
    print(f"   ROSpec_Parameter(")
    print(f"       ROSpecID={rospec_id},")
    print(f"       CurrentState=ROSpecState.Disabled,")
    print(f"       Parameters=[...])")
    
    pos += 10
    print()
    
    # 3. ROBoundarySpec Parameter 분석
    print("3. 🔄 ROBoundarySpec Parameter")
    boundary_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    boundary_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    
    print(f"   타입: 0x{boundary_type:04X} (0x00B2 = ROBoundarySpec_Parameter)")
    print(f"   길이: {boundary_length} 바이트")
    
    # esitarski/pyllrp 매핑
    print("\n   🔗 esitarski/pyllrp 매핑:")
    print(f"   ROBoundarySpec_Parameter(Parameters=[")
    
    pos += 4
    
    # ROSpecStartTrigger
    start_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    start_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    start_trigger_type = packet_bytes[pos+4]
    
    print(f"     ROSpecStartTrigger:")
    print(f"       타입: 0x{start_type:04X} (0x00B3)")
    print(f"       길이: {start_length}")
    print(f"       트리거 타입: {start_trigger_type} (0=Immediate)")
    print(f"       🔗 ROSpecStartTrigger_Parameter(")
    print(f"           ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate)")
    
    pos += 5
    
    # ROSpecStopTrigger  
    stop_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    stop_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    stop_trigger_type = packet_bytes[pos+4]
    stop_duration_type = packet_bytes[pos+5]
    stop_duration_value = struct.unpack('>I', packet_bytes[pos+6:pos+10])[0]
    
    print(f"     ROSpecStopTrigger:")
    print(f"       타입: 0x{stop_type:04X} (0x00B6)")
    print(f"       길이: {stop_length}")
    print(f"       트리거 타입: {stop_trigger_type} (0=Null)")
    print(f"       지속시간 타입: {stop_duration_type}")
    print(f"       지속시간 값: {stop_duration_value}")
    print(f"       🔗 ROSpecStopTrigger_Parameter(")
    print(f"           ROSpecStopTriggerType=ROSpecStopTriggerType.Null)")
    
    print(f"   ])")
    pos += 9
    print()
    
    # 4. AISpec Parameter 분석
    print("4. 📡 AISpec Parameter")
    aispec_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    aispec_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    antenna_count = struct.unpack('>H', packet_bytes[pos+4:pos+6])[0]
    
    print(f"   타입: 0x{aispec_type:04X} (0x00B7 = AISpec_Parameter)")
    print(f"   길이: {aispec_length} 바이트")
    print(f"   안테나 개수: {antenna_count}")
    
    pos += 6
    antenna_ids = []
    for i in range(antenna_count):
        antenna_id = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
        antenna_ids.append(antenna_id)
        pos += 2
    
    print(f"   안테나 ID들: {antenna_ids}")
    
    # AISpecStopTrigger
    aistop_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    aistop_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    aistop_trigger_type = packet_bytes[pos+4]
    
    print(f"   AISpecStopTrigger:")
    print(f"     타입: 0x{aistop_type:04X} (0x00B8)")
    print(f"     트리거 타입: {aistop_trigger_type} (0=Null)")
    
    pos += 9
    
    # InventoryParameterSpec
    inv_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    inv_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    inv_id = struct.unpack('>H', packet_bytes[pos+4:pos+6])[0]
    protocol_id = packet_bytes[pos+6]
    
    print(f"   InventoryParameterSpec:")
    print(f"     타입: 0x{inv_type:04X} (0x00BA)")
    print(f"     ID: {inv_id}")
    print(f"     프로토콜: {protocol_id} (1=EPCGlobalClass1Gen2)")
    
    # esitarski/pyllrp 매핑
    print("\n   🔗 esitarski/pyllrp 매핑:")
    print(f"   AISpec_Parameter(")
    print(f"       AntennaIDs={antenna_ids},")
    print(f"       Parameters=[")
    print(f"           AISpecStopTrigger_Parameter(")
    print(f"               AISpecStopTriggerType=AISpecStopTriggerType.Null),")
    print(f"           InventoryParameterSpec_Parameter(")
    print(f"               InventoryParameterSpecID={inv_id},")
    print(f"               ProtocolID=AirProtocols.EPCGlobalClass1Gen2)")
    print(f"       ])")
    
    pos += 7
    print()
    
    # 5. ROReportSpec Parameter 분석
    print("5. 📊 ROReportSpec Parameter")
    report_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    report_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    report_trigger = packet_bytes[pos+4]
    n_value = struct.unpack('>H', packet_bytes[pos+5:pos+7])[0]
    
    print(f"   타입: 0x{report_type:04X} (0x00DE = ROReportSpec_Parameter)")
    print(f"   길이: {report_length} 바이트")
    print(f"   리포트 트리거: {report_trigger} (1=Upon_N_Tags_Or_End_Of_ROSpec)")
    print(f"   N 값: {n_value}")
    
    # esitarski/pyllrp 매핑
    print("\n   🔗 esitarski/pyllrp 매핑:")
    print(f"   ROReportSpec_Parameter(")
    print(f"       ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,")
    print(f"       N={n_value},")
    print(f"       Parameters=[")
    print(f"           TagReportContentSelector_Parameter(")
    
    pos += 7
    
    # TagReportContentSelector 분석
    content_type = struct.unpack('>H', packet_bytes[pos:pos+2])[0]
    content_length = struct.unpack('>H', packet_bytes[pos+2:pos+4])[0]
    
    print(f"   TagReportContentSelector:")
    print(f"     타입: 0x{content_type:04X} (0x00DF)")
    print(f"     길이: {content_length}")
    
    pos += 4
    
    # Enable 플래그들 분석
    remaining_content = packet_bytes[pos:pos+content_length-4]
    print(f"     Enable 설정들:")
    
    enable_flags = []
    i = 0
    while i < len(remaining_content):
        if remaining_content[i] == 0x00:  # TLV Parameter
            if i + 3 < len(remaining_content):
                param_type = struct.unpack('>H', remaining_content[i:i+2])[0]
                param_length = struct.unpack('>H', remaining_content[i+2:i+4])[0]
                param_data = remaining_content[i+4:i+param_length]
                
                if param_type == 0x00E0 and len(param_data) >= 6:
                    # TV Parameters 처리
                    tv_data = param_data[2:]  # 첫 2바이트는 추가 헤더
                    j = 0
                    while j < len(tv_data) - 1:
                        tv_type = tv_data[j]
                        tv_value = tv_data[j+1]
                        
                        tv_meanings = {
                            0x01: ("EnableROSpecID", "True" if tv_value else "False"),
                            0x4A: ("EnablePeakRSSI", "True" if tv_value else "False"),
                            0x4F: ("EnableROSpecID", "True" if tv_value else "False"),
                            0x50: ("EnableInventoryParameterSpecID", "True" if tv_value else "False")
                        }
                        
                        if tv_type in tv_meanings:
                            name, value = tv_meanings[tv_type]
                            enable_flags.append((name, tv_value != 0))
                            print(f"       {name}={tv_value != 0}")
                        
                        j += 2
                
                i += param_length
            else:
                break
        else:
            i += 1
    
    # esitarski/pyllrp Enable 플래그 매핑
    print(f"               EnableAntennaID=True,")
    print(f"               EnableFirstSeenTimestamp=True,")
    for name, value in enable_flags:
        if name == "EnablePeakRSSI":
            print(f"               EnablePeakRSSI={value},")
    print(f"           )")
    print(f"       ])")
    print(f"   )")
    
    print()
    print("=" * 80)
    print("🎯 esitarski/pyllrp 완전한 매핑 결과")
    print("=" * 80)
    
    return {
        'message_id': msg_id,
        'rospec_id': rospec_id,
        'antenna_ids': antenna_ids,
        'inventory_param_id': inv_id,
        'n_value': n_value,
        'enable_flags': enable_flags
    }

def generate_esitarski_code(params):
    """분석 결과를 바탕으로 esitarski/pyllrp 코드 생성"""
    
    print("📝 생성된 esitarski/pyllrp 코드:")
    print("=" * 80)
    
    code = f'''
# 성공한 패킷 분석을 바탕으로 생성된 esitarski/pyllrp 코드

ADD_ROSPEC_Message(
    MessageID={params['message_id']},
    Parameters=[
        ROSpec_Parameter(
            ROSpecID={params['rospec_id']},
            CurrentState=ROSpecState.Disabled,
            Parameters=[
                ROBoundarySpec_Parameter(Parameters=[
                    ROSpecStartTrigger_Parameter(
                        ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                    ),
                    ROSpecStopTrigger_Parameter(
                        ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                    )
                ]),
                AISpec_Parameter(
                    AntennaIDs={params['antenna_ids']},
                    Parameters=[
                        AISpecStopTrigger_Parameter(
                            AISpecStopTriggerType=AISpecStopTriggerType.Null
                        ),
                        InventoryParameterSpec_Parameter(
                            InventoryParameterSpecID={params['inventory_param_id']},
                            ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                        )
                    ]
                ),
                ROReportSpec_Parameter(
                    ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                    N={params['n_value']},
                    Parameters=[
                        TagReportContentSelector_Parameter(
                            EnableAntennaID=True,
                            EnableFirstSeenTimestamp=True,
                            EnablePeakRSSI=True
                        )
                    ]
                )
            ]
        )
    ]
)'''
    
    print(code)
    return code

if __name__ == "__main__":
    params = analyze_successful_packet()
    generate_esitarski_code(params)