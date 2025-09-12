#!/usr/bin/env python3
"""
RO_ACCESS_REPORT 전체 구조 재분석
"""
import struct

# Bluebird 툴 결과와 비교
bluebird_results = [
    ("85047000049050503155303400702300", -73, 100),
    ("85047000028250503155303400702300", -77, 80),
    ("8504700001354D54314B553300702500", -78, 60),
    ("85047000032650503155303400702300", -78, 48),
    ("8504700013684D573243363207702205", -77, 99),
]

# 실제 패킷 (hex dump에서)
packet1 = "04 3d 00 00 00 3a 00 00 00 00 00 f0 00 30 00 f1 00 16 00 80 85 04 70 00 04 90 50 50 31 55 30 34 00 70 23 00 81 00 01 86 b7 8c 44 00 03 ff 00 0e 00 00 5e 95 00 00 00 38 00 16"

def analyze_packet(hex_str):
    """패킷 상세 분석"""
    data = bytes.fromhex(hex_str.replace(' ', ''))
    
    print(f"\n전체 패킷 ({len(data)} bytes):")
    print(' '.join(f'{b:02X}' for b in data))
    print()
    
    # TagReportData 이후 부분 분석 (offset 14부터)
    offset = 14  # TagReportData 헤더 이후
    
    # EPC-96 파싱
    epc_type = struct.unpack('!H', data[offset:offset+2])[0]
    epc_len = struct.unpack('!H', data[offset+2:offset+4])[0]
    print(f"EPC-96: Type=0x{epc_type:04X}, Len={epc_len}")
    
    epc_data = data[offset+6:offset+epc_len]  # flags 제외
    print(f"  EPC: {epc_data.hex().upper()}")
    offset += epc_len
    
    # 다음 파라미터들
    print(f"\nEPC 이후 데이터 (offset {offset}):")
    remaining = data[offset:]
    print(' '.join(f'{b:02X}' for b in remaining))
    
    # 바이트 단위 분석
    if len(remaining) >= 2:
        print(f"\n상세 분석:")
        print(f"  [0-1]: {remaining[0]:02X} {remaining[1]:02X}")
        
        # 00 81이 파라미터 타입이라면?
        if remaining[0] == 0x00 and remaining[1] == 0x81:
            print(f"    → Type 0x0081 (FirstSeenTimestampUTC?)")
            
            # 하지만 길이가 이상함 (00 01은 1바이트인데 실제로는 더 많음)
            # 혹시 TV encoding (Type-Value, 길이 없음)?
            print(f"  [2-3]: {remaining[2]:02X} {remaining[3]:02X}")
            print(f"  [4-5]: {remaining[4]:02X} {remaining[5]:02X}")
            print(f"  [6-7]: {remaining[6]:02X} {remaining[7]:02X}")
            
            # 0x86 = 134, 0xB7 = 183
            # RSSI로 변환 가능성?
            val_86 = remaining[2] if len(remaining) > 2 else 0
            val_b7 = remaining[3] if len(remaining) > 3 else 0
            
            print(f"\n  가능한 RSSI 해석:")
            print(f"    0x86({val_86}): {val_86-256 if val_86 > 127 else -val_86} dBm")
            print(f"    0xB7({val_b7}): {val_b7-256 if val_b7 > 127 else -val_b7} dBm")
            
            # B7을 signed byte로: 183 - 256 = -73
            signed_b7 = val_b7 - 256 if val_b7 > 127 else val_b7
            print(f"    → 0xB7을 signed byte로: {signed_b7} dBm ← 이것이 RSSI!")
    
    # Custom parameter
    custom_offset = data.find(b'\x03\xff')
    if custom_offset > 0:
        print(f"\nCustom parameter (offset {custom_offset}):")
        custom_data = data[custom_offset:]
        custom_len = struct.unpack('!H', custom_data[2:4])[0]
        vendor_data = custom_data[8:8+custom_len-8]
        print(f"  Vendor data: {' '.join(f'{b:02X}' for b in vendor_data)}")
        if len(vendor_data) >= 6:
            print(f"    마지막 바이트: 0x{vendor_data[-1]:02X} = {vendor_data[-1]} (count와 일치?)")

if __name__ == "__main__":
    print("="*60)
    print("RO_ACCESS_REPORT 재분석")
    print("="*60)
    
    print("\nBluebird 툴 결과:")
    for epc, rssi, count in bluebird_results[:1]:  # 첫 번째만
        print(f"  EPC: {epc}")
        print(f"  RSSI: {rssi} dBm")
        print(f"  Count: {count}")
    
    analyze_packet(packet1)