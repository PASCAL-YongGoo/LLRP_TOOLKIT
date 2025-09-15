#!/usr/bin/env python3
"""
FR900 Bluebird RFID Reader Test with esitarski/pyllrp
===================================================

이 프로그램은 esitarski/pyllrp 라이브러리를 사용하여 
FR900 Bluebird RFID 리더와 통신하고 태그 인벤토리를 수행합니다.

Features:
- 자동 연결 및 설정
- 태그 EPC 읽기
- RSSI 값 추출
- 상세한 로깅
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
    from esitarski_pyllrp.pyllrp.TagInventory import TagInventory
    from esitarski_pyllrp.pyllrp.AutoDetect import AutoDetect
except ImportError as e:
    print(f"esitarski/pyllrp 라이브러리를 찾을 수 없습니다: {e}")
    print("esitarski_pyllrp 디렉토리가 있는지 확인하세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fr900_esitarski_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class FR900EsitarskiTest:
    """FR900용 esitarski/pyllrp 테스트 클래스"""
    
    def __init__(self, reader_ip='192.168.10.102'):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        self.start_time = None
        
    def test_autodetect(self):
        """자동 리더 탐지 테스트"""
        logger.info("=== 자동 리더 탐지 테스트 시작 ===")
        try:
            reader_ip, computer_ip = AutoDetect()
            if reader_ip:
                logger.info(f"리더 자동 탐지 성공: {reader_ip}")
                logger.info(f"컴퓨터 IP: {computer_ip}")
                self.reader_ip = reader_ip
                return True
            else:
                logger.warning("자동 탐지 실패 - 기본 IP 사용")
                return False
        except Exception as e:
            logger.error(f"자동 탐지 중 오류: {e}")
            return False
    
    def test_basic_connection(self):
        """기본 연결 테스트"""
        logger.info("=== 기본 연결 테스트 시작 ===")
        try:
            with LLRPConnector() as conn:
                logger.info(f"리더 {self.reader_ip}에 연결 시도...")
                response = conn.connect(self.reader_ip)
                logger.info("연결 성공!")
                logger.info(f"연결 응답: {response}")
                return True
        except Exception as e:
            logger.error(f"연결 실패: {e}")
            return False
    
    def access_report_handler(self, connector, access_report):
        """RO_ACCESS_REPORT 메시지 핸들러"""
        try:
            for tag_data in access_report.getTagData():
                self.tag_count += 1
                epc = HexFormatToStr(tag_data['EPC'])
                
                # 기본 정보
                info = {
                    'count': self.tag_count,
                    'epc': epc,
                    'antenna_id': tag_data.get('AntennaID', 'N/A'),
                    'timestamp': tag_data.get('FirstSeenTimestampUTC', 'N/A')
                }
                
                # RSSI 정보 추출
                if 'PeakRSSI' in tag_data:
                    info['rssi'] = tag_data['PeakRSSI']
                else:
                    info['rssi'] = 'N/A'
                
                # 로그 출력
                logger.info(f"태그 #{info['count']}: EPC={info['epc']}, "
                          f"안테나={info['antenna_id']}, RSSI={info['rssi']} dBm")
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def default_handler(self, connector, message):
        """기타 메시지 핸들러"""
        logger.debug(f"기타 메시지 수신: {type(message).__name__}")
    
    def test_tag_inventory_simple(self):
        """간단한 태그 인벤토리 테스트"""
        logger.info("=== 간단한 태그 인벤토리 테스트 ===")
        try:
            ti = TagInventory(self.reader_ip, transmitPower=30)
            ti.Connect()
            logger.info("TagInventory 연결 성공")
            
            tag_inventory, other_messages = ti.GetTagInventory()
            
            logger.info(f"발견된 태그 수: {len(tag_inventory)}")
            for i, tag in enumerate(tag_inventory, 1):
                logger.info(f"태그 {i}: {tag}")
            
            logger.info(f"기타 메시지 수: {len(other_messages)}")
            
            ti.Disconnect()
            return True
            
        except Exception as e:
            logger.error(f"태그 인벤토리 테스트 실패: {e}")
            return False
    
    def test_continuous_reading(self, duration_seconds=10):
        """연속 태그 읽기 테스트"""
        logger.info(f"=== {duration_seconds}초 연속 태그 읽기 테스트 ===")
        
        try:
            # 연결 설정
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("리더 연결 성공")
            
            # 공장 초기화
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if not response.success():
                logger.error(f"공장 초기화 실패: {response}")
                return False
            
            # 리더 설정
            config_msg = SET_READER_CONFIG_Message(Parameters=[
                AntennaConfiguration_Parameter(AntennaID=0, Parameters=[
                    RFTransmitter_Parameter(
                        TransmitPower=30,
                        HopTableID=1,
                        ChannelIndex=1
                    ),
                    C1G2InventoryCommand_Parameter(Parameters=[
                        C1G2SingulationControl_Parameter(
                            Session=0,
                            TagPopulation=100,
                            TagTransitTime=3000
                        )
                    ])
                ])
            ])
            
            response = self.connector.transact(config_msg)
            if not response.success():
                logger.error(f"리더 설정 실패: {response}")
                return False
            
            # ROSpec 추가
            rospec_id = 123
            add_rospec_msg = ADD_ROSPEC_Message(Parameters=[
                ROSpec_Parameter(
                    ROSpecID=rospec_id,
                    CurrentState=ROSpecState.Disabled,
                    Parameters=[
                        ROBoundarySpec_Parameter(Parameters=[
                            ROSpecStartTrigger_Parameter(
                                ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                            ),
                            ROSpecStopTrigger_Parameter(
                                ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                            )
                        ]),
                        AISpec_Parameter(
                            AntennaIDs=[0],
                            Parameters=[
                                AISpecStopTrigger_Parameter(
                                    AISpecStopTriggerType=AISpecStopTriggerType.Null
                                ),
                                InventoryParameterSpec_Parameter(
                                    InventoryParameterSpecID=1234,
                                    ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                                )
                            ]
                        ),
                        ROReportSpec_Parameter(
                            ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                            N=1,  # 태그 하나씩 즉시 보고
                            Parameters=[
                                TagReportContentSelector_Parameter(
                                    EnableAntennaID=True,
                                    EnableFirstSeenTimestamp=True,
                                    EnablePeakRSSI=True
                                )
                            ]
                        )
                    ]
                )
            ])
            
            response = self.connector.transact(add_rospec_msg)
            if not response.success():
                logger.error(f"ROSpec 추가 실패: {response}")
                return False
            
            # 핸들러 등록
            self.tag_count = 0
            self.start_time = time.time()
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            self.connector.addHandler('default', self.default_handler)
            
            # ROSpec 활성화
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=rospec_id))
            if not response.success():
                logger.error(f"ROSpec 활성화 실패: {response}")
                return False
            
            logger.info("리스너 시작 - 태그 읽기를 시작합니다...")
            self.connector.startListener()
            
            # 지정된 시간동안 대기
            time.sleep(duration_seconds)
            
            # 정리
            logger.info("리스너 중지 중...")
            self.connector.stopListener()
            
            # ROSpec 비활성화
            response = self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=rospec_id))
            
            # ROSpec 삭제
            response = self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=rospec_id))
            
            # 연결 해제
            self.connector.disconnect()
            
            elapsed_time = time.time() - self.start_time
            logger.info(f"테스트 완료: {elapsed_time:.1f}초 동안 {self.tag_count}개 태그 읽음")
            logger.info(f"평균 읽기 속도: {self.tag_count/elapsed_time:.1f} tags/sec")
            
            return True
            
        except Exception as e:
            logger.error(f"연속 읽기 테스트 실패: {e}")
            if self.connector:
                try:
                    self.connector.disconnect()
                except:
                    pass
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("FR900 esitarski/pyllrp 테스트 시작")
        logger.info(f"리더 IP: {self.reader_ip}")
        logger.info(f"테스트 시간: {datetime.now()}")
        
        tests = [
            ("자동 탐지", self.test_autodetect),
            ("기본 연결", self.test_basic_connection),
            ("간단한 인벤토리", self.test_tag_inventory_simple),
            ("연속 읽기 (10초)", lambda: self.test_continuous_reading(10))
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*50}")
                result = test_func()
                results.append((test_name, result))
                logger.info(f"{test_name} 테스트: {'성공' if result else '실패'}")
            except Exception as e:
                logger.error(f"{test_name} 테스트 중 예외 발생: {e}")
                results.append((test_name, False))
        
        # 결과 요약
        logger.info(f"\n{'='*50}")
        logger.info("테스트 결과 요약:")
        for test_name, result in results:
            status = "✅ 성공" if result else "❌ 실패"
            logger.info(f"  {test_name}: {status}")
        
        success_count = sum(1 for _, result in results if result)
        logger.info(f"\n전체 테스트: {success_count}/{len(results)} 성공")
        
        return success_count == len(results)

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp 테스트 프로그램")
    print("=====================================")
    
    # 리더 IP 설정 (필요시 수정)
    reader_ip = "192.168.10.102"  # FR900 기본 IP
    
    # 기본 IP 사용 (비대화형 환경)
    print(f"리더 IP: {reader_ip}")
    
    # 테스트 실행
    tester = FR900EsitarskiTest(reader_ip)
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ 모든 테스트가 성공했습니다!")
    else:
        print("\n❌ 일부 테스트가 실패했습니다. 로그를 확인하세요.")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())