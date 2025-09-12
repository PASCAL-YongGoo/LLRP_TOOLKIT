#!/usr/bin/env python3
"""
전체 패킷 파일에서 ADD_ROSPEC 데이터를 정확히 추출
"""

def extract_rospec_from_full_packet():
    """전체 패킷 파일에서 ROSpec 데이터 추출"""
    
    # 전체 패킷 파일에서 ADD_ROSPEC 라인들 (266-272)
    lines = [
        "00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3",  # 266
        "00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46",   # 267
        "00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00",   # 268
        "35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01",   # 269
        "00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01",   # 270
        "4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00",   # 271
        "00 00"                                                # 272
    ]
    
    # 공백 제거하고 연결
    rospec_hex = ""
    for line in lines:
        hex_bytes = line.replace(" ", "")
        rospec_hex += hex_bytes
        print(f"Line: {line}")
        print(f"Hex:  {hex_bytes}")
        print()
    
    print(f"Complete ROSpec hex ({len(rospec_hex)//2} bytes):")
    print(rospec_hex)
    print()
    
    # 16진수 유효성 검사
    try:
        rospec_data = bytes.fromhex(rospec_hex)
        print(f"✓ Valid hex string: {len(rospec_data)} bytes")
        return rospec_hex
    except ValueError as e:
        print(f"✗ Invalid hex string: {e}")
        return None

if __name__ == "__main__":
    result = extract_rospec_from_full_packet()
    
    if result:
        print(f"\nFinal ROSpec hex string:")
        print(f'"{result}"')