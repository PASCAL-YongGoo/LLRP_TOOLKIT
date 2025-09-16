# BlueBird Fixed Reader Console Application

## 개요
BlueBird Fixed Reader API를 사용하여 RFID 태그 인벤토리를 수행하는 C# 콘솔 애플리케이션입니다.

## 기능
- 192.168.10.106 리더에 자동 연결
- 실시간 EPC 태그 읽기
- 태그 정보 표시 (EPC, 안테나, RSSI, 주파수, 위상각)
- 신규 태그와 재인식 태그 구분 표시
- 통계 정보 제공 (총 읽기 수, 고유 태그 수)
- 리더 이벤트 모니터링

## 실행 방법

### 빌드
```bash
cd bluebird/BlueBirdReaderConsole
msbuild BlueBirdReaderConsole.sln
```

### 실행
```bash
cd bin/Debug
BlueBirdReaderConsole.exe
```

## 키보드 명령
- `Q`: 프로그램 종료
- `S`: 통계 정보 표시
- `C`: 화면 지우기

## 주요 설정
- **리더 IP**: 192.168.10.106 (코드에 하드코딩)
- **안테나**: 1번 안테나 활성화
- **송신 출력**: 30 dBm
- **수신 감도**: -70 dBm
- **리더 모드**: Mode3 (고밀도 태그 환경)
- **세션**: 1
- **태그 추정 수**: 256

## 출력 예시
```
[NEW] EPC: E200123456789ABC | Ant: 1 | RSSI: -45.2 dBm | Freq: 920.6 MHz | Phase: 125.3°
[SEEN] EPC: E200123456789ABC | Ant: 1 | RSSI: -44.8 dBm | Freq: 921.2 MHz | Phase: 130.1°
```

## 요구사항
- .NET Framework 4.7.2 이상
- Bluebird.FixedReader.dll (포함됨)
- BlueBird 리더가 네트워크에 연결되어 있어야 함