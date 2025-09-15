#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Protocol Correct Version
======================================================

성공한 패킷을 분석하여 각 값의 의미를 파악하고,
이를 esitarski/pyllrp의 정확한 프로토콜 변수에 매핑하여 구현
"""

import sys
import time
import logging
from datetime import datetime

# esitarski/pyllrp 라이브러리 임포트
sys.path.insert(0, 'esitarski_pyllrp')

try:
    from esitarski_pyllrp.pyllrp.pyllrp import *
    from esitarski_pyllrp.pyllrp.LLRPConnector import LLRPConnector
    from esitarski_pyllrp.pyllrp.AutoDetect import AutoDetect
except ImportError as e:
    print(f"esitarski/pyllrp 라이브러리를 찾을 수 없습니다: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FR900ProtocolCorrect:
    """FR900용 프로토콜 준수 esitarski/pyllrp 구현"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        
        # 성공한 패킷에서 추출한 핵심 값들
        self.ROSPEC_ID = 1234                    # 0x04D2
        self.INVENTORY_PARAM_ID = 1234           # 0x04D2  
        self.ANTENNA_IDS = [1]                   # 안테나 1번
        self.REPORT_N_VALUE = 1                  # N=1 (즉시 보고)
        
    def access_report_handler(self, connector, access_report):
        """RO_ACCESS_REPORT 메시지 핸들러"""
        try:
            for tag_data in access_report.getTagData():
                self.tag_count += 1
                epc = HexFormatToStr(tag_data['EPC'])
                
                info = {
                    'count': self.tag_count,
                    'epc': epc,
                    'antenna_id': tag_data.get('AntennaID', 'N/A'),
                    'rssi': tag_data.get('PeakRSSI', 'N/A'),
                    'timestamp': tag_data.get('FirstSeenTimestampUTC', 'N/A'),
                    'seen_count': tag_data.get('TagSeenCount', 'N/A')
                }
                
                logger.info(f"🏷️  태그 #{info['count']}: {info['epc']}")
                logger.info(f"    📶 RSSI: {info['rssi']} dBm")
                logger.info(f"    📍 안테나: {info['antenna_id']}")
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def create_protocol_correct_rospec(self):
        """프로토콜을 완전히 준수한 ROSpec 생성 - 성공 패킷 분석 기반"""
        try:
            logger.info("📋 프로토콜 준수 ROSpec 생성 중...")
            logger.info(f"   ROSpec ID: {self.ROSPEC_ID}")
            logger.info(f"   안테나 ID: {self.ANTENNA_IDS}")
            logger.info(f"   인벤토리 파라미터 ID: {self.INVENTORY_PARAM_ID}")
            logger.info(f"   리포트 N값: {self.REPORT_N_VALUE}")
            
            # 성공한 패킷의 정확한 구조를 esitarski/pyllrp로 재현
            rospec_msg = ADD_ROSPEC_Message(
                MessageID=1,  # 메시지 ID는 자동으로 설정됨
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.ROSPEC_ID,
                        CurrentState=ROSpecState.Disabled,
                        Parameters=[
                            # 경계 조건 설정
                            ROBoundarySpec_Parameter(Parameters=[
                                ROSpecStartTrigger_Parameter(
                                    ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                                ),
                                ROSpecStopTrigger_Parameter(
                                    ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                                )
                            ]),
                            # 안테나 인벤토리 설정
                            AISpec_Parameter(
                                AntennaIDs=self.ANTENNA_IDS,
                                Parameters=[
                                    AISpecStopTrigger_Parameter(
                                        AISpecStopTriggerType=AISpecStopTriggerType.Null
                                    ),
                                    InventoryParameterSpec_Parameter(
                                        InventoryParameterSpecID=self.INVENTORY_PARAM_ID,
                                        ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                                    )
                                ]
                            ),
                            # 리포트 설정
                            ROReportSpec_Parameter(
                                ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                                N=self.REPORT_N_VALUE,
                                Parameters=[
                                    TagReportContentSelector_Parameter(
                                        EnableAntennaID=True,
                                        EnableFirstSeenTimestamp=True,
                                        EnablePeakRSSI=True,
                                        EnableLastSeenTimestamp=False,
                                        EnableTagSeenCount=False,
                                        EnableROSpecID=False,
                                        EnableSpecIndex=False,
                                        EnableInventoryParameterSpecID=False,
                                        EnableChannelIndex=False
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
            
            logger.info("✅ 프로토콜 준수 ROSpec 생성 완료")
            return rospec_msg
            
        except Exception as e:
            logger.error(f"❌ ROSpec 생성 실패: {e}")
            return None
    
    def run_protocol_correct_inventory(self, duration=10):
        """프로토콜을 완전히 준수한 방식으로 인벤토리 실행"""
        logger.info("=" * 70)
        logger.info("🚀 프로토콜 준수 FR900 EPC 읽기 시작!")
        logger.info(f"📡 리더: {self.reader_ip}")
        logger.info(f"⏱️  실행 시간: {duration}초")
        logger.info("🔧 방식: esitarski/pyllrp 프로토콜 클래스 사용")
        logger.info("=" * 70)
        
        try:
            # 1. 연결
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("✅ 리더 연결 성공")
            
            # 2. 공장 초기화
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if not response.success():
                raise Exception(f"공장 초기화 실패: {response}")
            logger.info("✅ 공장 초기화 완료")
            
            # 3. 기존 ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            logger.info("✅ 기존 ROSpec 정리 완료")
            
            # 4. 프로토콜 준수 ROSpec 추가
            rospec_msg = self.create_protocol_correct_rospec()
            if not rospec_msg:
                raise Exception("ROSpec 생성 실패")
            
            logger.info("📤 프로토콜 준수 ROSpec 전송 중...")
            response = self.connector.transact(rospec_msg)
            if not response.success():
                logger.error(f"❌ ROSpec 응답: {response}")
                raise Exception(f"ROSpec 추가 실패: {response}")
            logger.info("✅ 프로토콜 준수 ROSpec 추가 성공!")
            
            # 5. 이벤트 핸들러 등록
            self.tag_count = 0
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            logger.info("✅ EPC 읽기 핸들러 등록 완료")
            
            # 6. ROSpec 활성화
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            if not response.success():
                raise Exception(f"ROSpec 활성화 실패: {response}")
            logger.info("✅ ROSpec 활성화 완료")
            
            # 7. 리스너 시작 및 태그 읽기
            logger.info(f"🔄 {duration}초 동안 프로토콜 준수 방식으로 EPC 읽기...")
            logger.info("📋 태그를 리더 근처에 가져다 대세요!")
            
            self.connector.startListener()
            start_time = time.time()
            
            # 진행 상황 표시
            last_report = start_time
            while (time.time() - start_time) < duration:
                current = time.time()
                if current - last_report >= 3:
                    elapsed = current - start_time
                    remaining = duration - elapsed
                    logger.info(f"⏳ {elapsed:.1f}초 경과, {remaining:.1f}초 남음 (태그 {self.tag_count}개)")
                    last_report = current
                time.sleep(0.1)
            
            # 8. 정리
            logger.info("🛑 리스너 중지...")
            self.connector.stopListener()
            
            # ROSpec 비활성화 및 삭제
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            
            # 연결 해제
            self.connector.disconnect()
            
            # 결과 요약
            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info("📊 프로토콜 준수 EPC 읽기 결과")
            logger.info(f"⏱️  실행 시간: {elapsed:.1f}초")
            logger.info(f"🏷️  읽은 태그 수: {self.tag_count}개")
            logger.info(f"🔧 방식: LLRP 표준 완전 준수")
            
            if self.tag_count > 0:
                logger.info(f"📈 읽기 속도: {self.tag_count/elapsed:.1f} 태그/초")
                logger.info("🎉 프로토콜 준수 방식으로 EPC 읽기 성공!")
                return True
            else:
                logger.warning("⚠️ 읽은 태그가 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 프로토콜 준수 EPC 읽기 실패: {e}")
            if self.connector:
                try:
                    self.connector.disconnect()
                except:
                    pass
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp 프로토콜 준수 버전")
    print("=====================================")
    print("✨ 하드코딩 대신 프로토콜 클래스 사용")
    print("📋 성공 패킷 분석 결과를 정확히 매핑")
    print()
    
    # AutoDetect로 리더 찾기
    try:
        reader_ip, computer_ip = AutoDetect()
        if reader_ip:
            print(f"🔍 리더 자동 탐지: {reader_ip}")
        else:
            reader_ip = "192.168.10.102"
            print(f"🔍 기본 리더 IP 사용: {reader_ip}")
    except:
        reader_ip = "192.168.10.102"
        print(f"🔍 기본 리더 IP 사용: {reader_ip}")
    
    # 실행 시간 선택
    durations = [10, 30, 60]
    print("\\n실행 시간 선택:")
    for i, dur in enumerate(durations, 1):
        print(f"{i}. {dur}초")
    
    # 기본값 사용 (비대화형)
    choice = 1
    duration = durations[choice-1]
    print(f"선택: {choice} ({duration}초)")
    
    # 테스트 실행
    tester = FR900ProtocolCorrect(reader_ip)
    success = tester.run_protocol_correct_inventory(duration)
    
    if success:
        print(f"\\n🎉 프로토콜 준수 방식으로 EPC 읽기 성공!")
        print("✨ 이제 하드코딩이 아닌 정상적인 LLRP 프로토콜을 사용합니다!")
    else:
        print(f"\\n😞 EPC 읽기 실패 - 설정을 확인해보세요")
    
    return 0 if success else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\\n\\n🛑 프로그램을 종료합니다.")
        sys.exit(0)