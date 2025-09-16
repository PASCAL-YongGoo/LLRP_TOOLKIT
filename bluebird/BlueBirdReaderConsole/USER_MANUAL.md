# BlueBird RFID Reader Console Application

FR900 RFID 리더를 위한 콘솔 기반 인벤토리 애플리케이션입니다.

## 📋 목차

- [기본 기능](#기본-기능)
- [설정 파일 구조](#설정-파일-구조)
- [인벤토리 모드](#인벤토리-모드)
- [사용자 제어 명령](#사용자-제어-명령)
- [설정 방법](#설정-방법)
- [사용 예시](#사용-예시)
- [문제 해결](#문제-해결)

---

## 🚀 기본 기능

### ✅ 핵심 기능
- **FR900 RFID 리더 연결** - TCP/IP를 통한 안정적인 연결
- **EPC 태그 인벤토리** - 실시간 태그 읽기 및 표시
- **실시간 통계** - 초당 읽기 속도, 총/고유 태그 수 추적
- **중복 제거** - 고유 태그 식별 및 읽기 횟수 카운팅
- **JSON 기반 설정** - 모든 설정값 외부 파일로 관리
- **상세한 최종 보고서** - 읽은 태그 목록 및 통계 정보

### 📊 표시 정보
- **EPC 값** - 태그의 고유 식별자
- **안테나 포트** - 태그를 읽은 안테나 번호
- **RSSI** - 신호 강도 (dBm)
- **읽기 횟수** - 각 태그별 감지 횟수
- **실시간 통계** - 매초 업데이트되는 성능 지표

---

## ⚙️ 설정 파일 구조

모든 설정은 `config.json` 파일에서 관리됩니다.

### 📡 연결 설정 (Connection)
```json
{
  "connection": {
    "hostname": "192.168.10.106",    // 리더 IP 주소
    "connectionTimeoutMs": 30000,    // 연결 타임아웃 (밀리초)
    "keepalive": {
      "enabled": true,               // Keep-alive 활성화
      "periodInMs": 10000,          // Keep-alive 주기
      "timeoutMs": 15000            // Keep-alive 타임아웃
    }
  }
}
```

### 📻 안테나 설정 (Antennas)
```json
{
  "antennas": {
    "isAutoDetect": false,           // 자동 안테나 감지
    "autoDetectPower": 30.0,         // 자동 감지 시 전력
    "maxRxSensitivity": true,        // 최대 수신 감도 사용
    "rxSensitivity": -70.0,          // 수신 감도 (dBm)
    "ports": {
      "antenna1": {
        "isEnabled": true,           // 안테나 활성화
        "maxTxPower": false,         // 최대 전력 사용 여부
        "txPower": 14.0             // 송신 전력 (dBm)
      }
      // antenna2 ~ antenna8 동일한 구조
    }
  }
}
```

### 🎛️ 리더 모드 설정 (Reader Mode)
```json
{
  "readerMode": {
    "modeIndex": 1,                  // 0=Mode0, 1=Mode1, 2=Mode2, 3=Mode3
    "session": 0,                    // 0=Session0, 1=Session1, 2=Session2, 3=Session3
    "tagPopulationEstimate": 30      // 태그 개체수 추정값
  }
}
```

### 📊 리포트 설정 (Report)
```json
{
  "report": {
    "includeAntennaPortNumber": true, // 안테나 포트 번호 포함
    "includePeakRssi": true,         // 피크 RSSI 포함
    "includePcBits": true,           // PC 비트 포함
    "includeTID": false              // TID 포함 여부
  }
}
```

---

## ⏱️ 인벤토리 모드

### 1. 📅 고정 시간 모드 (FixedDuration)
지정된 시간 동안 인벤토리를 실행합니다.

```json
{
  "inventory": {
    "mode": "FixedDuration",
    "fixedDurationMs": 600000        // 10분 (600,000ms)
  }
}
```

**사용 시나리오:**
- 정확한 시간 동안 테스트하고 싶을 때
- 반복 가능한 테스트를 위해

### 2. ♾️ 무한 모드 (Infinite)
사용자가 수동으로 중지할 때까지 계속 실행합니다.

```json
{
  "inventory": {
    "mode": "Infinite",
    "infiniteMode": {
      "enabled": true,
      "maxDurationMs": 86400000,     // 24시간 최대 제한
      "heartbeatIntervalMs": 10000   // 10초마다 상태 확인
    }
  }
}
```

**사용 시나리오:**
- 장시간 모니터링이 필요할 때
- 태그 감지 패턴 분석을 위해
- 24/7 운영 환경에서

### 3. 🖱️ 수동 정지 모드 (ManualStop)
실시간 키보드 명령으로 제어합니다.

```json
{
  "inventory": {
    "mode": "ManualStop",
    "manualStop": {
      "enabled": true,
      "showInstructions": true,
      "instructions": "Press 'q' to stop inventory, 'r' to restart, 's' for statistics"
    }
  }
}
```

**사용 시나리오:**
- 인터랙티브한 테스트가 필요할 때
- 실시간으로 시작/정지를 제어하고 싶을 때

### 4. 🏷️ 태그 개수 기반 정지 (TagCount)
지정된 개수의 태그를 읽으면 자동으로 정지합니다.

```json
{
  "inventory": {
    "mode": "TagCount",
    "tagCountStop": {
      "enabled": true,
      "targetTagCount": 100,         // 100개 태그까지
      "uniqueTagsOnly": true,        // 고유 태그만 카운트
      "timeoutMs": 300000           // 5분 타임아웃
    }
  }
}
```

**사용 시나리오:**
- 특정 개수의 태그만 수집하고 싶을 때
- 샘플링 테스트를 위해

### 5. ⏱️ 태그 개수 + 타임아웃 (TagCountWithTimeout)
태그 개수 목표와 최대 시간 제한을 함께 적용합니다.

```json
{
  "inventory": {
    "mode": "TagCountWithTimeout",
    "tagCountStop": {
      "enabled": true,
      "targetTagCount": 50,
      "timeoutMs": 120000            // 2분 또는 50개 태그 중 먼저 도달하는 조건
    }
  }
}
```

---

## ⌨️ 사용자 제어 명령

### 키보드 명령어
```json
{
  "ui": {
    "userInput": {
      "keyCommands": {
        "quit": "q",          // 인벤토리 종료
        "restart": "r",       // 인벤토리 재시작
        "statistics": "s",    // 현재 통계 표시
        "pause": "p",         // 인벤토리 일시정지
        "resume": "c",        // 인벤토리 계속
        "export": "e"         // 현재 데이터 내보내기
      }
    }
  }
}
```

### 명령어 사용법
- **[q]** - 인벤토리를 중지하고 프로그램 종료
- **[r]** - 현재 인벤토리를 중지하고 새로 시작
- **[s]** - 현재까지의 통계 정보 표시
- **[p]** - 인벤토리 일시정지 (리더 정지)
- **[c]** - 일시정지된 인벤토리 재개
- **[e]** - 현재 수집된 데이터를 파일로 내보내기

---

## 🔧 설정 방법

### 1. 기본 설정 변경
`config.json` 파일을 텍스트 에디터로 열어 수정:

```bash
# 리더 IP 주소 변경
"hostname": "192.168.1.100"

# 안테나 전력 조정
"txPower": 20.0

# 인벤토리 시간 변경 (30초)
"fixedDurationMs": 30000
```

### 2. 사전 정의된 시간 사용
```json
{
  "customDurations": {
    "presets": [
      {"name": "30 seconds", "durationMs": 30000},
      {"name": "1 minute", "durationMs": 60000},
      {"name": "5 minutes", "durationMs": 300000},
      {"name": "10 minutes", "durationMs": 600000}
    ]
  }
}
```

### 3. 여러 안테나 활성화
```json
{
  "antennas": {
    "ports": {
      "antenna1": {"isEnabled": true, "txPower": 14.0},
      "antenna2": {"isEnabled": true, "txPower": 16.0},
      "antenna3": {"isEnabled": false, "txPower": 30.0}
    }
  }
}
```

---

## 📝 사용 예시

### 예시 1: 5분간 인벤토리 실행
```json
{
  "inventory": {
    "mode": "FixedDuration",
    "fixedDurationMs": 300000
  }
}
```
**실행 결과:**
```
=== FR900 RFID Reader Inventory ===
Connecting to 192.168.10.106...
Connected successfully!
Reader settings configured!
Antenna 1: 14.0 dBm

Starting 300-second inventory...
EPC Tags Found:
================
[1s] Rate: 0 tags/s | Total: 0 | Unique: 0
[2s] Rate: 5 tags/s | Total: 5 | Unique: 3
EPC: E20000123456789012345678 | Antenna: 1 | RSSI: -45
...
```

### 예시 2: 무한 모드 실행
```json
{
  "inventory": {
    "mode": "Infinite",
    "infiniteMode": {"enabled": true}
  }
}
```
**실행 결과:**
```
Running in infinite mode (press 'q' to stop)
Commands: [q]uit, [r]estart, [s]tatistics, [p]ause, [c]ontinue, [e]xport
EPC Tags Found:
================
[계속 실행됨...]
```

### 예시 3: 50개 태그까지만 수집
```json
{
  "inventory": {
    "mode": "TagCount",
    "tagCountStop": {
      "enabled": true,
      "targetTagCount": 50,
      "uniqueTagsOnly": true
    }
  }
}
```

---

## 🔍 문제 해결

### 연결 문제
**증상:** "Unable to connect to specified reader"
**해결방법:**
1. 리더 IP 주소 확인
2. 네트워크 연결 상태 확인
3. 방화벽 설정 확인
4. config.json의 hostname 설정 확인

### 태그가 읽히지 않는 경우
**증상:** "No tags detected during inventory"
**가능한 원인:**
- 안테나 범위에 RFID 태그가 없음
- 태그가 EPC Gen2 호환이 아님
- 안테나 연결 문제
- RF 간섭

**해결방법:**
1. 안테나 전력 증가: `"txPower": 30.0`
2. 수신 감도 조정: `"rxSensitivity": -80.0`
3. 안테나 연결 상태 확인
4. 다른 세션 시도: `"session": 1`

### 성능 문제
**증상:** 느린 태그 읽기 속도
**해결방법:**
1. 리더 모드 변경: `"modeIndex": 3` (Mode 3)
2. 태그 개체수 조정: `"tagPopulationEstimate": 10`
3. 통계 업데이트 주기 조정: `"statisticsUpdateIntervalMs": 2000`

---

## 📊 출력 예시

### 정상 실행 시
```
=== FR900 RFID Reader Inventory ===
Connecting to 192.168.10.106...
Connected successfully!
Reader settings configured!
Antenna 1: 14.0 dBm

Starting 600-second inventory...
EPC Tags Found:
================
[1s] Rate: 0 tags/s | Total: 0 | Unique: 0
[2s] Rate: 8 tags/s | Total: 8 | Unique: 3
EPC: E20000123456789012345678 | Antenna: 1 | RSSI: -42
EPC: E20000987654321098765432 | Antenna: 1 | RSSI: -38
[3s] Rate: 12 tags/s | Total: 20 | Unique: 5
...

==================================================
INVENTORY COMPLETE - FINAL REPORT
==================================================
Duration: 600.1 seconds
Total tags read: 1,247
Unique tags found: 23
Average rate: 2.1 tags/second

Unique EPC List:
------------------------------
EPC: E20000123456789012345678 (Read 87 times)
EPC: E20000987654321098765432 (Read 156 times)
EPC: E2000055AA44BB33CC22DD11 (Read 23 times)
...
```

### 태그가 없을 때
```
==================================================
INVENTORY COMPLETE - FINAL REPORT
==================================================
Duration: 600.1 seconds
Total tags read: 0
Unique tags found: 0
Average rate: 0.0 tags/second

No tags detected during inventory.
Possible causes:
- No RFID tags in antenna range
- Tags not EPC Gen2 compatible
- Antenna connection issues
- RF interference
```

---

## 📝 로깅 기능

### 로그 레벨
프로그램은 5가지 로그 레벨을 지원합니다:

| 레벨 | 설명 | 사용 예시 |
|------|------|----------|
| **Debug** | 디버깅 정보 | 상세한 프로그램 동작 추적 |
| **Info** | 일반 정보 | 정상적인 동작 기록 |
| **Warning** | 경고 | 주의가 필요한 상황 |
| **Error** | 오류 | 복구 가능한 오류 |
| **Critical** | 심각 | 프로그램 종료 필요한 오류 |

### 로그 설정
```json
{
  "logging": {
    "enableConsoleLogging": true,      // 콘솔 출력 활성화
    "enableFileLogging": true,         // 파일 로깅 활성화
    "logLevel": "Info",                // 최소 로그 레벨
    "logFilePath": "logs/rfid_reader.log",  // 로그 파일 경로
    "maxLogFileSize": 10485760,        // 최대 파일 크기 (10MB)
    "keepLogDays": 7,                  // 로그 보관 일수
    "includeTimestamp": true,          // 타임스탬프 포함
    "includeLogLevel": true,           // 로그 레벨 표시
    "dateFormat": "yyyy-MM-dd HH:mm:ss.fff",  // 시간 형식
    "rotateLogFiles": true,            // 파일 자동 회전
    "maxLogFiles": 10,                 // 최대 파일 개수
    "logTagData": true,                // 태그 데이터 로깅
    "logStatistics": true,             // 통계 로깅
    "logConnectionEvents": true,       // 연결 이벤트 로깅
    "logErrors": true                  // 오류 로깅
  }
}
```

### 로그 파일 형식
```
[2024-01-15 14:30:15.123] [Info    ] === FR900 RFID Reader Inventory ===
[2024-01-15 14:30:15.456] [Info    ] Connecting to 192.168.10.106...
[2024-01-15 14:30:16.789] [Info    ] CONNECTION: CONNECT 192.168.10.106 - SUCCESS
[2024-01-15 14:30:17.012] [Info    ] TAG: EPC=E20000123456789012345678, Antenna=1, RSSI=-45.0, Count=1
[2024-01-15 14:30:18.000] [Info    ] STATS: Total=15, Unique=3, Rate=15.0 tags/s
```

### 로그 파일 관리

#### 자동 회전 (Rotation)
- 파일이 `maxLogFileSize`를 초과하면 자동으로 새 파일 생성
- 파일명 형식: `rfid_reader_YYYYMMDD_HHMMSS_001.log`

#### 자동 정리 (Cleanup)
- `keepLogDays` 이전의 로그 파일 자동 삭제
- `maxLogFiles`를 초과하면 오래된 파일부터 삭제

#### 로그 디렉토리 구조
```
logs/
├── rfid_reader_20240115_143015.log    (현재 로그)
├── rfid_reader_20240115_120000.log    (이전 로그)
├── rfid_reader_20240114_093000.log
└── archive/                            (보관 폴더)
    └── rfid_reader_20240101.zip
```

### 로그 카테고리
특정 카테고리만 로깅하도록 설정 가능:

```json
{
  "logCategories": {
    "connection": true,   // 연결 관련 로그
    "inventory": true,    // 인벤토리 동작 로그
    "tags": true,        // 태그 데이터 로그
    "statistics": true,   // 통계 정보 로그
    "settings": true,     // 설정 변경 로그
    "errors": true,       // 오류 로그
    "debug": false       // 디버그 정보 (기본 비활성화)
  }
}
```

### 로그 분석 도구
로그 파일에서 특정 정보 추출하기:

#### 특정 EPC 태그 검색
```bash
findstr "E20000123456789012345678" logs\*.log
```

#### 오류만 필터링
```bash
findstr "[Error" logs\*.log
```

#### 통계 정보만 추출
```bash
findstr "STATS:" logs\*.log > statistics.txt
```

### 성능 고려사항

#### 버퍼링
- 로그는 100개씩 버퍼에 저장 후 1초마다 파일에 기록
- 즉시 기록이 필요한 경우 `flushIntervalMs`를 0으로 설정

#### 디스크 공간
- 10MB × 10개 파일 = 최대 100MB 사용
- 압축 활성화 시 약 10% 크기로 감소

#### 성능 영향
- 파일 로깅 활성화 시 약 2-5% CPU 사용 증가
- 태그 로깅 활성화 시 고속 읽기(>1000 tags/s)에서 약간의 지연 가능

---

## 📅 버전 히스토리

### v1.0.0 - 기본 인벤토리 기능
- FR900 리더 연결
- 기본 태그 읽기
- 실시간 통계

### v1.1.0 - JSON 설정 시스템
- 모든 설정값 외부화
- 설정 파일 자동 생성
- 오류 처리 개선

### v1.2.0 - 유연한 인벤토리 모드
- 5가지 인벤토리 모드 추가
- 무한 모드 지원
- 사용자 제어 명령 추가
- 태그 개수 기반 정지 기능

### v1.3.0 - 포괄적 로깅 시스템
- 5단계 로그 레벨 지원
- 자동 파일 회전 및 정리
- 카테고리별 로깅 제어
- 성능 최적화된 버퍼링
- 로그 파일 압축 지원

### v1.4.0 - RSSI 통계 분석 시스템
- 올바른 dBm 평균 계산 (로그 스케일 변환)
- 다양한 평균 방식: 산술평균, 가중평균, 필터링된 평균, 중앙값
- 표준편차 및 이상치 제거 기능
- 최근 50개 값 기반 이동평균 시스템

### v1.5.0 - 태그 움직임 감지 시스템
- RSSI 변화 패턴 기반 움직임 분석
- 태그 상태 판단: 정지, 이동중, 접근중, 멀어짐, 미약한움직임
- 실시간 움직임 상태 디스플레이
- 선형 추세 분석 및 최근 변동성 계산

### v1.6.0 - 다중 태그 동시 디스플레이
- 여러 태그 동시 읽기 시 각각 독립된 줄에 표시
- 실시간 개별 태그 카운트 업데이트
- 스레드 안전 디스플레이 시스템
- 태그별 고정 줄 위치 할당

---

## 🔬 고급 RSSI 분석 기능

### RSSI 통계 정보 표시
프로그램은 각 태그에 대해 다음과 같은 RSSI 통계를 제공합니다:

#### 실시간 디스플레이
```
EPC: 850470... | Ant: 1 | RSSI: -58.0 (F:-58.2 ±0.8) | Count: 15 | 상태: 정지
```
- **현재 RSSI**: 가장 최근 읽힌 신호 강도
- **F (Filtered)**: 이상치 제거된 평균 (평균 ± 2σ 범위)
- **±StdDev**: 표준편차 (신호 안정성 지표)
- **상태**: 태그의 움직임 상태

#### 최종 보고서 통계
```
EPC: 850470002290434B3257303200700105
  Count: 2468 reads
  RSSI Stats: Mean:-52.4(vs-52.8) Median:-52.1 Filtered:-52.3 Weighted:-52.2 StdDev:1.20 Range:[-55.0~-49.0] n=50
  Movement: 상태:정지 (편차:1.2 추세:0.02 최근변동:0.8)
```

### RSSI 평균 계산 방식

#### 1. 올바른 dBm 평균 (Mean)
dBm은 로그 스케일이므로 mW로 변환 후 평균 계산:
```
mW = 10^(dBm/10)
평균_mW = Σ(mW) / n
평균_dBm = 10 * log10(평균_mW)
```

#### 2. 비교용 산술평균 (vs값)
단순 dBm 값의 산술평균 (참고용)

#### 3. 필터링된 평균 (Filtered)
평균 ± 2σ 범위 내 값만 사용하여 이상치 제거

#### 4. 가중평균 (Weighted)
최근 값에 더 높은 가중치 부여 (지수적 감소: 0.9^n)

#### 5. 중앙값 (Median)
이상치에 가장 덜 민감한 중간값

### 태그 움직임 감지 알고리즘

#### 판단 기준
| 상태 | 조건 | 의미 |
|------|------|------|
| **정지** | 표준편차 < 1.0 & 최근변동 < 0.8 | 태그가 정지 상태 |
| **이동중** | 표준편차 > 3.0 또는 최근변동 > 2.5 | 활발한 움직임 |
| **접근중** | 추세 기울기 > +0.5 | RSSI 증가 (가까워짐) |
| **멀어짐** | 추세 기울기 < -0.5 | RSSI 감소 (멀어짐) |
| **미약한움직임** | 기타 | 약간의 위치 변화 |

#### 계산 지표
- **표준편차**: 전체 RSSI 값의 변동성
- **최근변동성**: 최근 10개 값의 표준편차
- **추세 기울기**: 선형 회귀로 계산한 RSSI 변화 방향
- **샘플 수**: 최근 50개 값까지 유지

### 다중 태그 처리
- 각 태그는 독립된 화면 줄에 표시
- 동시 읽기 시에도 개별 카운트 실시간 업데이트
- 스레드 안전 디스플레이 시스템
- 태그별 고유한 통계 및 움직임 분석

---

**💡 Tip:** 새로운 기능이 추가될 때마다 이 문서가 자동으로 업데이트됩니다.