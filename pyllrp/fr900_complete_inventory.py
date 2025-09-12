#!/usr/bin/env python3
"""
FR900 Complete Inventory Program
지금까지 검증된 내용을 바탕으로 만든 완전한 RFID 인벤토리 시스템

Flow: Connect -> Inventory Start -> Reading Tags -> Inventory Stop -> Disconnect
"""

import socket
import struct
import time
import logging
import binascii
import threading
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FR900InventoryClient:
    """FR900 RFID Reader - Complete Inventory System"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1
        self.keepalive_thread = None
        self.keepalive_stop = False
        self.rospec_id = 0x04D2  # 1234 - 검증된 ROSpec ID
        
    def connect(self):
        """FR900에 연결"""
        try:
            logger.info(f"FR900에 연결 시도: {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            
            # 초기 Reader Event Notification 수신
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x3F:
                logger.info("✅ FR900 연결 성공 및 초기 이벤트 수신")
                self.start_keepalive()
                return True
            else:
                logger.error("❌ 예상하지 못한 초기 메시지")
                return False
                
        except Exception as e:
            logger.error(f"❌ 연결 실패: {e}")
            return False
    
    def send_raw_message(self, raw_hex):
        """raw hex 데이터 전송 (메시지 ID 자동 업데이트)"""
        data = bytes.fromhex(raw_hex.replace(' ', ''))
        
        # 메시지 ID를 현재 값으로 업데이트 (오프셋 6-9 바이트)
        if len(data) >= 10:
            msg_id = self.message_id
            self.message_id += 1
            # 메시지 ID를 빅엔디안으로 패킹해서 교체
            data = data[:6] + struct.pack('!I', msg_id) + data[10:]
            
        self.socket.send(data)
        logger.debug(f"TX Raw: {raw_hex} (ID updated to {msg_id if len(data) >= 10 else 'N/A'})")
        return msg_id if len(data) >= 10 else None
    def send_message(self, msg_type, msg_data=b''):
        """LLRP 메시지 전송"""
        msg_id = self.message_id
        self.message_id += 1
        
        type_field = 0x0400 | msg_type
        length = 10 + len(msg_data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + msg_data
        
        self.socket.send(message)
        logger.debug(f"TX: Type=0x{msg_type:02X}, Length={length}, ID={msg_id}")
        return msg_id
    
    def recv_message(self, expected_type=None):
        """LLRP 메시지 수신 (KEEPALIVE 자동 처리)"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                self.socket.settimeout(15.0)
                header = self.socket.recv(10)
                if len(header) < 10:
                    continue
                
                type_field, msg_len, msg_id = struct.unpack('!HII', header)
                msg_type = type_field & 0xFF
                
                remaining = msg_len - 10
                data = b''
                while len(data) < remaining:
                    chunk = self.socket.recv(remaining - len(data))
                    if not chunk:
                        break
                    data += chunk
                
                logger.debug(f"RX: Type=0x{msg_type:02X}, Length={msg_len}, ID={msg_id}")
                
                # KEEPALIVE(0x3E) 처리 - ACK 전송하고 다음 메시지 대기
                if msg_type == 0x3E:
                    logger.debug("KEEPALIVE 수신, ACK 전송")
                    ack_data = struct.pack('!HII', 0x0448, 10, msg_id)  # KEEPALIVE_ACK
                    self.socket.send(ack_data)
                    continue  # 다음 메시지 대기
                
                return msg_type, msg_id, data
                
            except socket.timeout:
                logger.debug("메시지 수신 타임아웃")
                return None, None, None
            except Exception as e:
                logger.debug(f"수신 오류: {e}")
                return None, None, None
        
        logger.warning(f"최대 시도 횟수({max_attempts}) 초과")
        return None, None, None
    
    def start_keepalive(self):
        """Keepalive 스레드 시작"""
        if self.keepalive_thread is None or not self.keepalive_thread.is_alive():
            self.keepalive_stop = False
            self.keepalive_thread = threading.Thread(target=self._keepalive_worker, daemon=True)
            self.keepalive_thread.start()
            logger.debug("Keepalive 시작")
    
    def stop_keepalive(self):
        """Keepalive 스레드 중지"""
        self.keepalive_stop = True
        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=2)
            logger.debug("Keepalive 중지")
    
    def _keepalive_worker(self):
        """Keepalive 작업자 스레드"""
        while not self.keepalive_stop and self.socket:
            try:
                time.sleep(30)  # 30초마다 keepalive 전송
                if not self.keepalive_stop and self.socket:
                    self.send_message(0x3E, b'')
                    # ACK는 선택적으로 처리
            except:
                break
    
    def initialize_reader(self):
        """리더 초기화 - 실제 패킷 데이터 사용"""
        logger.info("리더 초기화 중...")
        
        # 1. GET_READER_CAPABILITIES (Line 5-6)
        logger.info("1. 리더 성능 정보 요청")
        self.send_raw_message("04 01 00 00 00 0b 00 00 00 01 00")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x0B:
            logger.error("❌ 리더 성능 정보 수신 실패")
            return False
        logger.info("✅ 리더 성능 정보 수신 완료")
        
        # 2. SET_READER_CONFIG 기본 (Line 122-123)
        logger.info("2. 기본 리더 설정 적용")
        self.send_raw_message("04 03 00 00 00 0b 00 00 00 02 80")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x0D:
            logger.error("❌ 리더 설정 실패")
            return False
        logger.info("✅ 기본 리더 설정 완료")
        
        # 3. DELETE_ROSPEC (Line 129-130)
        logger.info("3. 기존 ROSpec 정리")
        self.send_raw_message("04 15 00 00 00 0e 00 00 00 03 00 00 00 00")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x1F:
            logger.error("❌ ROSpec 정리 실패")
            return False
        logger.info("✅ 기존 ROSpec 정리 완료")
        
        # 4. DELETE_ACCESSSPEC (Line 136-137)
        logger.info("4. 기존 AccessSpec 정리")
        self.send_raw_message("04 29 00 00 00 0e 00 00 00 04 00 00 00 00")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x33:
            logger.error("❌ AccessSpec 정리 실패")
            return False
        logger.info("✅ 기존 AccessSpec 정리 완료")
        
        # 5. Detailed SET_READER_CONFIG (Line 143-151)
        logger.info("5. 상세 리더 설정 적용")
        detailed_config = "04 03 00 00 00 70 00 00 00 05 00 00 f4 00 20 00 f5 00 07 00 08 80 00 f5 00 07 00 01 80 00 f5 00 07 00 03 80 00 f5 00 07 00 02 80 00 ed 00 12 02 00 01 00 ee 00 0b 00 00 01 5c 00 05 00 00 ef 00 05 01 00 dc 00 09 01 00 00 27 10 00 e1 00 08 00 01 00 00 00 e1 00 08 00 02 00 00 00 e1 00 08 00 03 00 00 00 e1 00 08 00 04 00 00 00 e2 00 05 00"
        self.send_raw_message(detailed_config)
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x0D:
            logger.error("❌ 상세 리더 설정 실패")
            return False
        logger.info("✅ 상세 리더 설정 완료")
        
        logger.info("✅ 리더 초기화 완료")
        return True
    
    def create_inventory_rospec(self):
        """실제 성공 ADD_ROSPEC 패킷 사용"""
        logger.info("인벤토리 ROSpec 생성 중...")
        
        # 실제 성공한 ADD_ROSPEC 패킷 (Line 251-258)
        # TODO: TagReportContentSelector에 EnablePeakRSSI 추가 고려
        add_rospec_hex = "04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00 00 00"
        
        logger.info(f"ROSpec 추가 중... (실제 패킷 사용)")
        self.send_raw_message(add_rospec_hex)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✅ ROSpec 추가 성공")
            return True
        else:
            msg_type_str = f"0x{msg_type:02X}" if msg_type is not None else "None"
            logger.error(f"❌ ROSpec 추가 실패: 응답 타입 {msg_type_str}")
            return False
    
    def start_inventory(self):
        """실제 패킷 기반 인벤토리 시작"""
        logger.info("인벤토리 시작 중...")
        
        # 1. ENABLE_ROSPEC (Line 264-265)
        logger.info("1. ROSpec 활성화")
        self.send_raw_message("04 18 00 00 00 0e 00 00 27 11 00 00 04 d2")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x22:
            msg_type_str = f"0x{msg_type:02X}" if msg_type is not None else "None"
            logger.error(f"❌ ROSpec 활성화 실패: 응답 타입 {msg_type_str}")
            return False
        logger.info("✅ ROSpec 활성화 완료")
        
        # 2. START_ROSPEC (Line 292-293)
        logger.info("2. ROSpec 시작")
        self.send_raw_message("04 16 00 00 00 0e 00 00 27 0d 00 00 04 d2")
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x20:
            msg_type_str = f"0x{msg_type:02X}" if msg_type is not None else "None"
            logger.error(f"❌ ROSpec 시작 실패: 응답 타입 {msg_type_str}")
            return False
        logger.info("✅ ROSpec 시작 완료 - 인벤토리 활성화됨")
        
        return True
    
    def read_tags(self, duration=None, mode="single"):
        """태그 읽기 (단일 실행 또는 연속 실행)"""
        if mode == "single" and duration:
            logger.info(f"태그 읽기 시작 (단일 실행: {duration}초)")
            return self._read_tags_single(duration)
        else:
            logger.info("태그 읽기 시작 (연속 실행 - Ctrl+C로 중지)")
            return self._read_tags_continuous()
    
    def _read_tags_single(self, duration):
        """단일 실행 모드 (지정된 시간 동안)"""
        start_time = time.time()
        end_time = start_time + duration
        
        tag_reports = []
        unique_epcs = set()
        reader_events = 0
        
        self.socket.settimeout(1.0)
        
        print("\n" + "="*60)
        print(f" RFID 인벤토리 실행 중... ({duration}초)")
        print("="*60)
        
        while time.time() < end_time:
            msg_type, msg_id, data = self.recv_message()
            
            if msg_type is None:
                continue
            
            if msg_type == 0x3D:  # RO_ACCESS_REPORT (태그 발견)
                tag_reports.append(data)
                
                # 전체 태그 정보 추출
                tag_info = self.extract_tag_info_from_report(data)
                epc = tag_info.get('epc')
                if epc:
                    unique_epcs.add(epc)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    # RSSI 정보 추가 표시
                    rssi_str = ""
                    if tag_info.get('rssi') is not None:
                        rssi_str = f" (RSSI: {tag_info['rssi']} dBm)"
                    
                    antenna_str = ""
                    if tag_info.get('antenna_id') is not None:
                        antenna_str = f" [Ant: {tag_info['antenna_id']}]"
                    
                    print(f"[{timestamp}] 태그 발견: {epc}{rssi_str}{antenna_str}")
                else:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp}] 태그 리포트 수신 (EPC 추출 실패)")
                    
            elif msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                reader_events += 1
                logger.debug("Reader Event 수신")
        
        print("="*60)
        
        results = {
            'mode': 'single',
            'duration': duration,
            'total_reports': len(tag_reports),
            'unique_epcs': list(unique_epcs),
            'unique_count': len(unique_epcs),
            'reader_events': reader_events,
            'read_rate': len(tag_reports) / duration if duration > 0 else 0
        }
        
        logger.info(f"단일 실행 완료: {results['total_reports']}개 리포트, {results['unique_count']}개 고유 EPC")
        return results
    
    def _read_tags_continuous(self):
        """연속 실행 모드 (수동 중지까지)"""
        start_time = time.time()
        tag_reports = []
        unique_epcs = set()
        reader_events = 0
        
        self.socket.settimeout(1.0)
        
        print("\n" + "="*60)
        print(" RFID 인벤토리 연속 실행 중... (Ctrl+C로 중지)")
        print("="*60)
        
        try:
            while True:
                msg_type, msg_id, data = self.recv_message()
                
                if msg_type is None:
                    continue
                
                if msg_type == 0x3D:  # RO_ACCESS_REPORT (태그 발견)
                    tag_reports.append(data)
                    
                    # 전체 태그 정보 추출
                    tag_info = self.extract_tag_info_from_report(data)
                    epc = tag_info.get('epc')
                    if epc:
                        unique_epcs.add(epc)
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        
                        # RSSI 정보 추가 표시
                        rssi_str = ""
                        if tag_info.get('rssi') is not None:
                            rssi_str = f" (RSSI: {tag_info['rssi']} dBm)"
                        
                        antenna_str = ""
                        if tag_info.get('antenna_id') is not None:
                            antenna_str = f" [Ant: {tag_info['antenna_id']}]"
                        
                        print(f"[{timestamp}] 태그 발견: {epc}{rssi_str}{antenna_str}")
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp}] 태그 리포트 수신 (EPC 추출 실패)")
                        
                elif msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                    reader_events += 1
                    logger.debug("Reader Event 수신")
                    
        except KeyboardInterrupt:
            print("\n연속 실행 중지됨 (Ctrl+C)")
        
        print("="*60)
        
        duration = time.time() - start_time
        results = {
            'mode': 'continuous',
            'duration': duration,
            'total_reports': len(tag_reports),
            'unique_epcs': list(unique_epcs),
            'unique_count': len(unique_epcs),
            'reader_events': reader_events,
            'read_rate': len(tag_reports) / duration if duration > 0 else 0
        }
        
        logger.info(f"연속 실행 완료: {results['total_reports']}개 리포트, {results['unique_count']}개 고유 EPC")
        return results
    
    def extract_tag_info_from_report(self, data):
        """RO_ACCESS_REPORT에서 EPC, RSSI, 기타 정보 추출"""
        try:
            tag_info = {
                'epc': None,
                'rssi': None,
                'antenna_id': None,
                'first_seen_time': None,
                'peak_rssi': None,
                'channel_index': None
            }
            
            # TagReportData 파라미터 (0x00F0) 검색
            for i in range(len(data) - 6):
                if data[i:i+2] == b'\x00\xf0':  # TagReportData parameter
                    param_len = struct.unpack('!H', data[i+2:i+4])[0]
                    logger.debug(f"TagReportData 발견: 위치 {i}, 길이 {param_len}")
                    
                    # TagReportData 내부 파라미터들 파싱
                    tag_data = data[i+4:i+4+param_len-4]
                    tag_info.update(self._parse_tag_report_data(tag_data))
                    break
            
            return tag_info
        except Exception as e:
            logger.debug(f"태그 정보 추출 전체 오류: {e}")
            return {'epc': None, 'rssi': None}
    
    def _parse_tag_report_data(self, tag_data):
        """TagReportData 내부 파라미터들 파싱"""
        info = {}
        i = 0
        
        while i < len(tag_data):
            try:
                # TV Parameter 체크 (최상위 비트가 1이면 TV format)
                if i < len(tag_data) and tag_data[i] & 0x80:
                    # TV Parameter (Type-Value, 길이 없음)
                    tv_type = tag_data[i] & 0x7F  # 하위 7비트가 타입
                    i += 1
                    
                    if tv_type == 0x01:  # Antenna ID
                        if i < len(tag_data):
                            info['antenna_id'] = tag_data[i]
                            logger.debug(f"Antenna ID: {info['antenna_id']}")
                            i += 1
                    
                    elif tv_type == 0x06:  # Peak RSSI
                        if i < len(tag_data):
                            rssi_raw = tag_data[i]
                            # signed byte 변환
                            info['rssi'] = rssi_raw - 256 if rssi_raw > 127 else rssi_raw
                            logger.debug(f"Peak RSSI: {info['rssi']} dBm (raw=0x{rssi_raw:02X})")
                            i += 1
                    
                    elif tv_type == 0x0C:  # C1G2 PC
                        if i + 1 < len(tag_data):
                            pc = (tag_data[i] << 8) | tag_data[i+1]
                            info['pc'] = pc
                            logger.debug(f"C1G2 PC: 0x{pc:04X}")
                            i += 2
                    
                    else:
                        # 알 수 없는 TV 파라미터, 1바이트로 가정하고 건너뛰기
                        logger.debug(f"Unknown TV parameter: type=0x{tv_type:02X}")
                        i += 1
                
                # TLV Parameter (최상위 비트가 0)
                elif i + 4 <= len(tag_data):
                    param_type = struct.unpack('!H', tag_data[i:i+2])[0]
                    param_len = struct.unpack('!H', tag_data[i+2:i+4])[0]
                    
                    if param_len < 4 or i + param_len > len(tag_data):
                        break
                    
                    param_data = tag_data[i+4:i+param_len]
                    logger.debug(f"TLV 파라미터: Type=0x{param_type:04X}, Length={param_len}")
                    
                    if param_type == 0x00F1:  # EPC-96
                        if len(param_data) >= 2:
                            epc_bytes = param_data[2:]  # flags 건너뛰기
                            info['epc'] = binascii.hexlify(epc_bytes).decode().upper()
                            logger.debug(f"EPC 추출: {info['epc']}")
                
                    elif param_type == 0x0081:  # FirstSeenTimestampUTC
                        if len(param_data) >= 8:
                            timestamp = struct.unpack('!Q', param_data)[0]
                            info['first_seen_time'] = timestamp
                            logger.debug(f"FirstSeenTime: {timestamp}")
                    
                    elif param_type == 0x0082:  # LastSeenTimestampUTC
                        if len(param_data) >= 8:
                            timestamp = struct.unpack('!Q', param_data)[0]
                            info['last_seen_time'] = timestamp
                
                    # Vendor-specific parameters
                    elif param_type == 0x03FF:  # Custom/Vendor parameter
                        logger.debug(f"Vendor parameter length: {param_len}")
                        # Bluebird vendor-specific data에 count 값이 있음
                        if len(param_data) >= 4:
                            vendor_id = struct.unpack('!I', param_data[0:4])[0]
                            if vendor_id == 0x5E95:  # Bluebird vendor ID
                                logger.debug("Bluebird vendor parameter 발견")
                                # Custom parameter에서 count 값 추출
                                if len(param_data) >= 10:
                                    byte9 = param_data[9]   # count 값
                                    info['tag_count'] = byte9
                                    logger.debug(f"Tag count: {byte9}")
                    
                    i += param_len
                
                else:
                    # 인식할 수 없는 데이터, 1바이트씩 건너뛰기
                    i += 1
                
            except Exception as e:
                logger.debug(f"파라미터 파싱 오류 (offset {i}): {e}")
                i += 1  # 다음 바이트로
        
        return info
    
    def extract_epc_from_report(self, data):
        """RO_ACCESS_REPORT에서 EPC만 추출 (기존 호환성)"""
        tag_info = self.extract_tag_info_from_report(data)
        return tag_info.get('epc')
    
    def _extract_epc_from_tag_data(self, tag_data):
        """TagReportData 내에서 EPC 추출"""
        try:
            for i in range(len(tag_data) - 6):
                if tag_data[i:i+2] == b'\x00\xf1':  # EPC-96 in TagReportData
                    param_len = struct.unpack('!H', tag_data[i+2:i+4])[0]
                    if param_len >= 6:
                        epc_start = i + 6
                        epc_len = param_len - 6
                        if epc_start + epc_len <= len(tag_data):
                            epc_bytes = tag_data[epc_start:epc_start+epc_len]
                            return binascii.hexlify(epc_bytes).decode().upper()
            return None
        except:
            return None
    
    def stop_inventory(self):
        """인벤토리 중지"""
        logger.info("인벤토리 중지 중...")
        
        # DISABLE_ROSPEC (Line 333-334)
        self.send_raw_message("04 19 00 00 00 0e 00 00 27 0e 00 00 04 d2")
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x23:  # DISABLE_ROSPEC_RESPONSE
            logger.info("✅ ROSpec 중지 완료")
            return True
        else:
            msg_type_str = f"0x{msg_type:02X}" if msg_type is not None else "None"
            logger.warning(f"ROSpec 중지 응답: 타입 {msg_type_str}")
            return False
    
    def cleanup(self):
        """정리 작업"""
        logger.info("정리 작업 중...")
        
        try:
            # ROSpec 삭제
            self.send_message(0x15, struct.pack('!I', self.rospec_id))
            msg_type, msg_id, data = self.recv_message()
            
            # AccessSpec 삭제  
            self.send_message(0x29, struct.pack('!I', 0))
            msg_type, msg_id, data = self.recv_message()
            
            logger.info("✅ 정리 작업 완료")
        except:
            logger.warning("정리 작업 중 일부 오류 발생 (무시)")
    
    def disconnect(self):
        """연결 해제"""
        logger.info("연결 해제 중...")
        
        # Keepalive 중지
        self.stop_keepalive()
        
        if self.socket:
            try:
                # CLOSE_CONNECTION
                self.send_message(0x0E, b'')
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x10:
                    logger.info("✅ 정상적으로 연결 해제")
            except:
                logger.debug("연결 해제 중 소켓 오류 (무시)")
            
            self.socket.close()
            self.socket = None
        
        logger.info("✅ 연결 해제 완료")


def main():
    """메인 함수 - Complete Inventory Workflow"""
    
    READER_IP = "192.168.10.106"  # FR900 IP 주소
    
    print("\n" + "="*70)
    print(" FR900 Complete RFID Inventory System")
    print(" Connect -> Initialize -> Start -> Read Tags -> Stop -> Disconnect")
    print("="*70)
    
    # 인벤토리 모드 선택
    print("\n인벤토리 실행 모드를 선택하세요:")
    print("1. 한번만 실행 (2초)")
    print("2. 연속 실행 (Ctrl+C로 중지)")
    
    while True:
        try:
            choice = input("\n선택 (1 또는 2): ").strip()
            if choice == "1":
                INVENTORY_MODE = "single"
                INVENTORY_DURATION = 2
                break
            elif choice == "2":
                INVENTORY_MODE = "continuous"
                INVENTORY_DURATION = None
                break
            else:
                print("1 또는 2를 입력하세요.")
        except (KeyboardInterrupt, EOFError):
            print("\n프로그램을 종료합니다.")
            return
    
    client = FR900InventoryClient(READER_IP)
    
    try:
        # Phase 1: Connect
        print("\n🔌 Phase 1: FR900 연결 중...")
        if not client.connect():
            print("❌ 연결 실패")
            return
        print("✅ FR900 연결 성공")
        
        # Phase 2: Initialize Reader
        print("\n⚙️  Phase 2: 리더 초기화 중...")
        if not client.initialize_reader():
            print("❌ 리더 초기화 실패")
            return
        print("✅ 리더 초기화 완료")
        
        # Phase 3: Create ROSpec
        print("\n📋 Phase 3: 인벤토리 ROSpec 생성 중...")
        if not client.create_inventory_rospec():
            print("❌ ROSpec 생성 실패")
            return
        print("✅ ROSpec 생성 완료")
        
        # Phase 4: Start Inventory
        print("\n🚀 Phase 4: 인벤토리 시작 중...")
        if not client.start_inventory():
            print("❌ 인벤토리 시작 실패")
            return
        print("✅ 인벤토리 시작 완료")
        
        # Phase 5: Read Tags
        if INVENTORY_MODE == "single":
            print(f"\n📡 Phase 5: 태그 읽기 (단일 실행 - {INVENTORY_DURATION}초)...")
            results = client.read_tags(duration=INVENTORY_DURATION, mode="single")
        else:
            print(f"\n📡 Phase 5: 태그 읽기 (연속 실행)...")
            results = client.read_tags(mode="continuous")
        
        # Phase 6: Stop Inventory  
        print("\n⏹️  Phase 6: 인벤토리 중지 중...")
        client.stop_inventory()
        print("✅ 인벤토리 중지 완료")
        
        # Phase 7: Cleanup
        print("\n🧹 Phase 7: 정리 작업 중...")
        client.cleanup()
        print("✅ 정리 작업 완료")
        
        # Results Summary
        print("\n" + "="*70)
        print(" 📊 인벤토리 결과 요약")
        print("="*70)
        print(f"  실행 모드: {'단일 실행' if results['mode'] == 'single' else '연속 실행'}")
        print(f"  실행 시간: {results['duration']:.1f}초")
        print(f"  총 태그 리포트: {results['total_reports']}개")
        print(f"  고유 EPC 개수: {results['unique_count']}개")
        print(f"  읽기 속도: {results['read_rate']:.1f} 리포트/초")
        print(f"  Reader 이벤트: {results['reader_events']}개")
        
        if results['unique_epcs']:
            print(f"\n  발견된 EPC 목록:")
            for i, epc in enumerate(results['unique_epcs'], 1):
                print(f"    {i:2d}. {epc}")
        else:
            print(f"\n  ⚠️  발견된 태그 없음")
            print(f"     - RFID 태그가 안테나 근처에 있는지 확인")
            print(f"     - 안테나 연결 상태 확인")
        
        print("\n✅ 인벤토리 완료!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
        client.stop_inventory()
        client.cleanup()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        logger.exception("예상치 못한 오류")
        
    finally:
        # Phase 8: Disconnect
        print("\n🔌 Phase 8: 연결 해제 중...")
        client.disconnect()
        print("✅ 연결 해제 완료")
        
        print("\n" + "="*70)
        print(" 프로그램 종료")
        print("="*70)


if __name__ == "__main__":
    main()