#!/usr/bin/env python3
"""
RO_ACCESS_REPORT 패킷 상세 분석
"""
import struct

def analyze_ro_access_report():
    """RO_ACCESS_REPORT 패킷 분석"""
    
    # 실제 패킷 데이터 (라인 310-313)
    packet_hex = """
    04 3d 00 00 00 3a 00 00 00 00 00 f0 00 30 00 f1
    00 16 00 80 85 04 70 00 04 90 50 50 31 55 30 34
    00 70 23 00 81 00 01 86 b7 8c 44 00 03 ff 00 0e
    00 00 5e 95 00 00 00 38 00 16
    """
    
    # 공백 제거하고 바이트로 변환
    packet_data = bytes.fromhex(packet_hex.replace('\n', '').replace(' ', ''))
    
    print(f"전체 패킷 크기: {len(packet_data)} bytes")
    print("="*60)
    
    # LLRP 헤더 파싱
    offset = 0
    msg_type = struct.unpack('!H', packet_data[offset:offset+2])[0]
    msg_len = struct.unpack('!I', packet_data[offset+2:offset+6])[0]
    msg_id = struct.unpack('!I', packet_data[offset+6:offset+10])[0]
    print(f"LLRP 헤더:")
    print(f"  Type: 0x{msg_type:04X}")
    print(f"  Length: {msg_len}")
    print(f"  Message ID: {msg_id}")
    offset += 10
    
    # TagReportData 파싱
    print("\nTagReportData:")
    tag_type = struct.unpack('!H', packet_data[offset:offset+2])[0]
    tag_len = struct.unpack('!H', packet_data[offset+2:offset+4])[0]
    print(f"  Type: 0x{tag_type:04X}")
    print(f"  Length: {tag_len}")
    offset += 4
    
    # TagReportData 내부 파라미터들
    tag_end = offset + tag_len - 4
    param_offset = offset
    param_count = 1
    
    while param_offset < tag_end:
        print(f"\n  파라미터 #{param_count}:")
        param_type = struct.unpack('!H', packet_data[param_offset:param_offset+2])[0]
        param_len = struct.unpack('!H', packet_data[param_offset+2:param_offset+4])[0]
        
        print(f"    Type: 0x{param_type:04X} ", end="")
        
        # 파라미터 타입별 이름
        if param_type == 0x00F1:
            print("(EPC-96)")
        elif param_type == 0x0081:
            print("(FirstSeenTimestampUTC)")
        elif param_type == 0x0082:
            print("(LastSeenTimestampUTC)")
        elif param_type == 0x0083:
            print("(PeakRSSI)")
        elif param_type == 0x0085:
            print("(AntennaID)")
        elif param_type == 0x03FF:
            print("(Custom/Vendor)")
        else:
            print("(Unknown)")
            
        print(f"    Length: {param_len}")
        
        # 데이터 표시
        if param_len > 4:
            param_data = packet_data[param_offset+4:param_offset+param_len]
            print(f"    Data ({len(param_data)} bytes): {' '.join(f'{b:02x}' for b in param_data)}")
            
            # EPC 데이터 해석
            if param_type == 0x00F1:
                epc_data = param_data[2:]  # Skip flags
                print(f"      EPC: {epc_data.hex().upper()}")
            
            # Vendor 데이터 해석
            elif param_type == 0x03FF:
                if len(param_data) >= 4:
                    vendor_id = struct.unpack('!I', param_data[0:4])[0]
                    print(f"      Vendor ID: 0x{vendor_id:08X} (Bluebird: 0x00005E95)")
                    vendor_data = param_data[4:]
                    print(f"      Vendor Data: {' '.join(f'{b:02x}' for b in vendor_data)}")
                    
                    # Vendor 데이터 내 가능한 RSSI 값 추정
                    if len(vendor_data) >= 2:
                        # 첫 2바이트를 signed short로 해석
                        possible_rssi1 = struct.unpack('!h', vendor_data[0:2])[0]
                        print(f"      Possible RSSI (signed short): {possible_rssi1}")
                        
                        # 첫 바이트를 signed byte로 해석
                        possible_rssi2 = struct.unpack('!b', vendor_data[0:1])[0]
                        print(f"      Possible RSSI (signed byte): {possible_rssi2}")
                        
                        # 0x38 = 56 (decimal) - 이것이 RSSI일 가능성
                        print(f"      Raw bytes: 0x{vendor_data[0]:02X} 0x{vendor_data[1]:02X}")
                        print(f"      As unsigned: {vendor_data[0]}, {vendor_data[1]}")
        
        param_offset += param_len
        param_count += 1

if __name__ == "__main__":
    analyze_ro_access_report()