#!/usr/bin/env python3
"""
Custom parameter에서 RSSI 분석
"""

# 여러 RO_ACCESS_REPORT의 Custom parameter 데이터
custom_params = [
    "03 ff 00 0e 00 00 5e 95 00 00 00 38 00 16",  # 첫 번째
    "03 ff 00 0e 00 00 5e 95 00 00 00 38 00 62",  # 두 번째  
    "03 ff 00 0e 00 00 5e 95 00 00 00 38 00 53",  # 세 번째
    "03 ff 00 0e 00 00 5e 95 00 00 00 38 00 1a",  # 네 번째
    "03 ff 00 0e 00 00 5e 95 00 00 00 38 00 63",  # 제공된 예시
]

print("Custom Parameter 분석")
print("="*60)

for i, param_hex in enumerate(custom_params, 1):
    data = bytes.fromhex(param_hex.replace(' ', ''))
    
    print(f"\n패킷 #{i}:")
    print(f"  Raw: {param_hex}")
    
    # 파싱
    param_type = (data[0] << 8) | data[1]
    param_len = (data[2] << 8) | data[3]
    vendor_id = (data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]
    
    # Vendor 데이터 (vendor ID 이후)
    vendor_data = data[8:]
    
    print(f"  Type: 0x{param_type:04X} (Custom)")
    print(f"  Length: {param_len}")
    print(f"  Vendor ID: 0x{vendor_id:08X} (Bluebird)")
    print(f"  Vendor Data: {' '.join(f'{b:02X}' for b in vendor_data)}")
    
    # 가능한 RSSI 해석
    if len(vendor_data) >= 6:
        val1 = vendor_data[0]  # 0x00
        val2 = vendor_data[1]  # 0x00
        val3 = vendor_data[2]  # 0x00
        val4 = vendor_data[3]  # 0x38 (56)
        val5 = vendor_data[4]  # 0x00
        val6 = vendor_data[5]  # 변하는 값
        
        print(f"  분석:")
        print(f"    바이트 [0-2]: 0x{val1:02X} {val2:02X} {val3:02X} (항상 0)")
        print(f"    바이트 [3]: 0x{val4:02X} = {val4} (항상 56 - RSSI?)")
        print(f"    바이트 [4]: 0x{val5:02X} = {val5} (항상 0)")
        print(f"    바이트 [5]: 0x{val6:02X} = {val6} (변하는 값)")
        
        # RSSI 가능성
        print(f"  RSSI 추정:")
        print(f"    0x38(56)을 RSSI로: -{val4} dBm = -56 dBm")
        print(f"    0x{val6:02X}({val6})를 RSSI로: -{val6} dBm")

print("\n" + "="*60)
print("결론:")
print("- 바이트[3] (0x38=56)은 모든 패킷에서 동일 → RSSI일 가능성 높음")
print("- 바이트[5]는 각 패킷마다 다름 → 다른 정보(채널, 카운터 등)")
print("- RSSI = -56 dBm (0x38을 음수로 변환)")