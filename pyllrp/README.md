# PyLLRP - Pure Python LLRP Implementation

순수 파이썬으로 구현된 LLRP (Low Level Reader Protocol) 라이브러리입니다. EPCglobal LLRP v1.0.1 스펙을 기반으로 하며, 외부 의존성 없이 크로스 플랫폼에서 동작합니다.

## 특징

- **순수 파이썬** - DLL이나 네이티브 라이브러리 불필요
- **크로스 플랫폼** - Windows, Linux, macOS에서 동작
- **외부 의존성 없음** - 표준 라이브러리만 사용
- **간편한 설치** - `pip install` 한 번으로 완료
- **사용하기 쉬운 API** - 고수준과 저수준 인터페이스 모두 제공

## 설치

```bash
# 소스에서 설치
cd pyllrp
pip install -e .

# 또는 개발 의존성과 함께
pip install -e .[dev]
```

## 빠른 시작

### 기본 사용법

```python
from llrp import LLRPClient

# RFID 리더에 연결
reader = LLRPClient("192.168.1.100")

if reader.connect():
    # 태그 읽기 콜백 함수
    def on_tag_read(tag_info):
        print(f"Tag: {tag_info['epc']}, RSSI: {tag_info['rssi']}")
    
    # 5초간 태그 읽기
    tags = reader.simple_inventory(
        duration_seconds=5.0,
        tag_callback=on_tag_read
    )
    
    print(f"Total tags read: {len(tags)}")
    
    reader.disconnect()
```

### 연속 읽기

```python
# 연속 읽기 시작
reader.start_continuous_inventory(tag_callback=on_tag_read)

# 10초 후 정지
import time
time.sleep(10)
reader.stop_continuous_inventory()
```

### 고급 사용법

```python
# 커스텀 ROSpec 생성
rospec = reader.create_basic_rospec(
    rospec_id=1,
    duration_ms=5000,
    antenna_ids=[1, 2, 3],  # 특정 안테나만 사용
    report_every_n_tags=10,  # 10개 태그마다 보고
    start_immediate=True
)

# ROSpec 추가 및 실행
reader.add_rospec(rospec)
reader.enable_rospec(1)
```

## API 문서

### LLRPClient

메인 클라이언트 클래스입니다.

#### 생성자
```python
client = LLRPClient(host, port=5084)
```

#### 주요 메서드

- `connect(timeout=10.0)` - 리더에 연결
- `disconnect()` - 연결 해제
- `get_capabilities()` - 리더 기능 조회
- `simple_inventory(duration_seconds, antenna_ids, tag_callback)` - 간단한 인벤토리
- `start_continuous_inventory(antenna_ids, tag_callback)` - 연속 읽기 시작
- `stop_continuous_inventory()` - 연속 읽기 중지
- `clear_rospecs()` - 모든 ROSpec 삭제

## 지원하는 LLRP 기능

### 메시지
- GET_READER_CAPABILITIES / RESPONSE
- ADD_ROSPEC / RESPONSE
- ENABLE_ROSPEC / RESPONSE
- START_ROSPEC / RESPONSE
- STOP_ROSPEC / RESPONSE
- DELETE_ROSPEC / RESPONSE
- RO_ACCESS_REPORT

### 파라미터
- ROSpec
- ROBoundarySpec
- AISpec (Antenna Inventory Spec)
- InventoryParameterSpec
- ROReportSpec
- TagReportContentSelector
- TagReportData

## 예제

전체 예제는 `example.py` 파일을 참조하세요:

```bash
python example.py
```

## 개발

테스트 실행:
```bash
pytest tests/
```

코드 포맷팅:
```bash
black llrp/
```

## 호환성

- Python 3.7+
- Windows, Linux, macOS
- Impinj, Zebra 등 LLRP 호환 RFID 리더

## 라이센스

Apache License 2.0

## 기여하기

1. 이 저장소를 포크합니다
2. 피처 브랜치를 만듭니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -am 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 만듭니다