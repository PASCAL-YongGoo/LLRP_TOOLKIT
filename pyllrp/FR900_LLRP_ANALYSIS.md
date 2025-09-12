# Bluebird FR900 LLRP 통신 분석 보고서

## 1. 개요

Bluebird FR900 RFID 리더의 LLRP (Low Level Reader Protocol) 1.1 구현을 분석하고, Python 기반 완전한 인벤토리 프로그램을 개발했습니다.

### 주요 발견사항
- FR900은 **LLRP 1.1 표준을 완벽히 준수**
- 표준 LLRP 메시지 + Bluebird 고유 Custom Parameter 사용
- RSSI는 표준 TV Parameter로 전송
- 메시지 타입에 0x04 prefix 사용 (0x0400 | type)

## 2. FR900 LLRP 특징

### 2.1 메시지 구조
```
Type(2) + Length(4) + Message ID(4) + Parameters
```
- Type 필드: `0x04XX` 형식 (예: 0x0401 = GET_READER_CAPABILITIES)
- 표준 LLRP 메시지 ID 사용

### 2.2 통신 흐름
```
1. Connect (TCP 5084)
2. Reader Event Notification 수신
3. GET_READER_CAPABILITIES
4. SET_READER_CONFIG (기본)
5. DELETE_ROSPEC (정리)
6. DELETE_ACCESSSPEC (정리)
7. SET_READER_CONFIG (상세)
8. ADD_ROSPEC
9. ENABLE_ROSPEC
10. START_ROSPEC
11. RO_ACCESS_REPORT 수신 (태그 데이터)
12. DISABLE_ROSPEC
13. CLOSE_CONNECTION
```

### 2.3 Keepalive 메커니즘
- 30초 간격으로 KEEPALIVE (0x3E) 전송
- KEEPALIVE_ACK (0x48) 응답 필요

## 3. RO_ACCESS_REPORT 구조

### 3.1 전체 구조
```
04 3D [Length] [ID] [TagReportData]
```

### 3.2 TagReportData 파라미터
```
00 F0 [Length]
├── EPC-96 (TLV): 00 F1 [Len] [Flags] [EPC Data]
├── Antenna ID (TV): 81 [Value]
├── Peak RSSI (TV): 86 [Value]  ← RSSI 위치!
├── C1G2 PC (TV): 8C [PC_H] [PC_L]
└── Custom (TLV): 03 FF [Len] 00 00 5E 95 [Data] [Count]
```

### 3.3 파라미터 타입
- **TV (Type-Value)**: 최상위 비트 = 1, 길이 필드 없음
  - 0x81: Antenna ID (1 byte)
  - 0x86: Peak RSSI (1 byte, signed)
  - 0x8C: C1G2 PC (2 bytes)

- **TLV (Type-Length-Value)**: 최상위 비트 = 0
  - 0x00F0: TagReportData
  - 0x00F1: EPC-96
  - 0x03FF: Custom Parameter

## 4. RSSI 및 Custom Parameter

### 4.1 RSSI 추출
```python
# TV Parameter 0x86에서 추출
if tv_type == 0x06:  # Peak RSSI
    rssi_raw = data[i]  # 예: 0xB4 = 180
    rssi = rssi_raw - 256 if rssi_raw > 127 else rssi_raw
    # 결과: -76 dBm
```

### 4.2 Bluebird Custom Parameter
```
03 FF 00 0E 00 00 5E 95 00 00 00 38 00 [Count]
                     ↑                    ↑
                Vendor ID               Tag Count
```
- Vendor ID: 0x00005E95 (Bluebird)
- 마지막 바이트: 태그 읽은 횟수

## 5. 검증된 ROSpec 구성

### 5.1 성공한 ADD_ROSPEC 패킷
```hex
04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00 
04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00 
09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8 
00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de 
00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01 
00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00 
00 01 50 00 0b 00 00 1e 00 00 00 00
```

### 5.2 ROSpec 구성 요소
- ROSpec ID: 0x04D2 (1234)
- Priority: 0
- Current State: Disabled
- ROBoundarySpec: Immediate start/stop
- SpecParameter: 단일 안테나 구성

## 6. 실제 측정 데이터 예시

### Bluebird 툴 측정 결과
| No | EPC | Antenna | RSSI | Count |
|----|-----|---------|------|-------|
| 1 | 8504700013684D573243363207702205 | 2 | -78 dBm | 33 |
| 2 | 85047000049050503155303400702300 | 2 | -71 dBm | 33 |
| 3 | 85A2700015374B573547303104300101 | 2 | -84 dBm | 7 |
| 4 | 85047000053850503155303400702300 | 2 | -81 dBm | 20 |
| 5 | 8504700001354D54314B553300702500 | 2 | -78 dBm | 9 |

### Wireshark 검증
```
Peak RSSI: 179 (0xB3) → -77 dBm
Antenna ID: 2
Count: 9
```

## 7. 구현된 프로그램

### 7.1 FR900 Complete Inventory (`fr900_complete_inventory.py`)

**주요 기능:**
- 완전한 LLRP 통신 구현
- 실시간 RSSI 표시
- 단일/연속 실행 모드
- Keepalive 자동 처리
- TV/TLV 파라미터 정확한 파싱

**사용법:**
```bash
python fr900_complete_inventory.py

# 모드 선택
1. 한번만 실행 (2초)
2. 연속 실행 (Ctrl+C로 중지)
```

**출력 예시:**
```
[13:42:15.123] 태그 발견: 8504700013684D573243363207702205 (RSSI: -78 dBm) [Ant: 2]
```

## 8. 결론

### 8.1 FR900 LLRP 준수도
- ✅ LLRP 1.1 표준 완벽 준수
- ✅ 표준 메시지 구조 사용
- ✅ TV/TLV 파라미터 정확한 구현
- ✅ Vendor Extension 적절히 활용

### 8.2 특이사항
- 메시지 타입에 0x04 prefix 사용 (하위 호환성?)
- RSSI는 표준 TV Parameter (0x86) 사용
- Tag count는 Custom Parameter에 포함
- Extended SET_READER_CONFIG로 성능 최적화

### 8.3 개발 성과
- PyLLRP 라이브러리 문법 오류 수정
- FR900 전용 통신 프로그램 구현
- RSSI 실시간 추출 성공
- 완전한 인벤토리 워크플로우 구현

## 9. 참고 자료

### 파일 목록
- `fr900_complete_inventory.py`: 최종 구현 프로그램
- `LLRP_WIRESHARK_LOG.txt`: Wireshark 캡처 로그
- `hex dump_20250912.txt`: 실제 패킷 덤프
- `test_archive/`: 개발 과정 테스트 파일들

### LLRP 표준 문서
- EPCglobal LLRP 1.1 Specification
- LLRP Parameter Type Registry

---
*작성일: 2025-09-12*
*작성자: Claude Code Assistant*