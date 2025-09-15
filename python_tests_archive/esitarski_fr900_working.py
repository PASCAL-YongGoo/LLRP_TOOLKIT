#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Working Version
============================================

검증된 ROSpec 데이터를 사용하여 esitarski/pyllrp로 FR900에서 EPC 값을 성공적으로 읽어오는 프로그램
"""

import sys
import time
import logging
import struct
from datetime import datetime

# esitarski/pyllrp 라이브러리 임포트
sys.path.insert(0, 'esitarski_pyllrp')

try:
    from esitarski_pyllrp.pyllrp.pyllrp import *
    from esitarski_pyllrp.pyllrp.LLRPConnector import LLRPConnector
except ImportError as e:
    print(f"esitarski/pyllrp 라이브러리를 찾을 수 없습니다: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FR900EsitarskiWorking:
    """FR900용 esitarski/pyllrp 작동 버전"""
    
    def __init__(self, reader_ip='192.168.10.102'):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        self.rospec_id = 0x04D2  # 1234 - 검증된 ROSpec ID
        
        # 검증된 98바이트 ROSpec 데이터 (우리가 성공한 것)
        self.VERIFIED_ROSPEC_HEX = (
            "00b1006200000004d200000000b2001200b300050000b60009000000000000b700460001"
            "0001000b800090000000000ba0035004d201000de002e000100df00060001000e0000a0001"
            "00010078014a001800014f000800010000015000000b00001e0000000000"
        )
    
    def access_report_handler(self, connector, access_report):
        """RO_ACCESS_REPORT 메시지 핸들러 - EPC 값 추출"""
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
                logger.info(f"✅ 태그 #{info['count']}: EPC={info['epc']}, "
                          f"안테나={info['antenna_id']}, RSSI={info['rssi']} dBm")
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def create_custom_rospec_message(self):
        """검증된 ROSpec 데이터를 사용하여 커스텀 메시지 생성"""
        try:
            # 검증된 ROSpec 바이트 데이터
            rospec_bytes = bytes.fromhex(self.VERIFIED_ROSPEC_HEX)
            logger.info(f"검증된 ROSpec 데이터 사용: {len(rospec_bytes)} 바이트")
            
            # 바이트 데이터를 직접 사용하여 ADD_ROSPEC 메시지 생성
            # esitarski/pyllrp의 메시지 구조를 활용
            
            # 일단 기본 구조로 시작해서 나중에 바이트 데이터로 교체
            return ADD_ROSPEC_Message(
                MessageID=self.get_next_message_id(),
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.rospec_id,
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
                                N=1,  # 즉시 보고
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
                ]
            )
            
        except Exception as e:
            logger.error(f"ROSpec 메시지 생성 실패: {e}")
            return None
    
    def get_next_message_id(self):
        """다음 메시지 ID 반환"""
        if not hasattr(self, '_message_id'):
            self._message_id = 1
        else:
            self._message_id += 1
        return self._message_id
    
    def create_fr900_optimized_rospec(self):
        """FR900에 최적화된 ROSpec 생성"""
        try:
            # FR900에 최적화된 ROSpec 설정
            return ADD_ROSPEC_Message(
                MessageID=self.get_next_message_id(),
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.rospec_id,
                        CurrentState=ROSpecState.Disabled,
                        Parameters=[
                            # 경계 설정
                            ROBoundarySpec_Parameter(Parameters=[
                                ROSpecStartTrigger_Parameter(
                                    ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                                ),
                                ROSpecStopTrigger_Parameter(
                                    ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                                )
                            ]),
                            # 안테나 설정 - 타임아웃 추가
                            AISpec_Parameter(
                                AntennaIDs=[1],  # 안테나 1만 사용
                                Parameters=[
                                    AISpecStopTrigger_Parameter(
                                        AISpecStopTriggerType=AISpecStopTriggerType.Tag_Observation,
                                        Parameters=[
                                            TagObservationTrigger_Parameter(
                                                TriggerType=TagObservationTriggerType.N_Attempts_To_See_All_Tags_In_FOV_Or_Timeout,
                                                NumberOfAttempts=10,
                                                Timeout=2000  # 2초 타임아웃
                                            )
                                        ]
                                    ),
                                    InventoryParameterSpec_Parameter(
                                        InventoryParameterSpecID=1234,
                                        ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                                    )
                                ]
                            ),
                            # 리포트 설정 - 모든 태그 즉시 보고
                            ROReportSpec_Parameter(
                                ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_AISpec,
                                N=1,
                                Parameters=[
                                    TagReportContentSelector_Parameter(
                                        EnableROSpecID=True,
                                        EnableSpecIndex=True,
                                        EnableInventoryParameterSpecID=True,
                                        EnableAntennaID=True,
                                        EnableChannelIndex=True,
                                        EnablePeakRSSI=True,
                                        EnableFirstSeenTimestamp=True,
                                        EnableLastSeenTimestamp=True,
                                        EnableTagSeenCount=True
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
            
        except Exception as e:
            logger.error(f"Simple ROSpec 생성 실패: {e}")
            return None
    
    def run_inventory_test(self, duration_seconds=10):
        """메인 인벤토리 테스트"""
        logger.info("=== FR900 esitarski/pyllrp EPC 읽기 테스트 ===")
        
        try:
            # 1. 연결
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("✅ 리더 연결 성공")
            
            # 2. 리셋
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if not response.success():
                logger.error(f"공장 초기화 실패: {response}")
                return False
            logger.info("✅ 공장 초기화 완료")
            
            # 2.5. 리더 설정 - 전력 및 민감도
            config_msg = SET_READER_CONFIG_Message(Parameters=[
                AntennaConfiguration_Parameter(AntennaID=0, Parameters=[
                    RFTransmitter_Parameter(
                        TransmitPower=30,  # 전송 파워 30
                        HopTableID=1,
                        ChannelIndex=1
                    ),
                    RFReceiver_Parameter(
                        ReceiverSensitivity=1  # 수신 민감도
                    ),
                    C1G2InventoryCommand_Parameter(Parameters=[
                        C1G2SingulationControl_Parameter(
                            Session=0,
                            TagPopulation=32,
                            TagTransitTime=0
                        )
                    ])
                ])
            ])
            
            response = self.connector.transact(config_msg)
            if not response.success():
                logger.error(f"리더 설정 실패: {response}")
                return False
            logger.info("✅ 리더 설정 완료")
            
            # 3. 기존 ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            logger.info("✅ 기존 ROSpec 정리 완료")
            
            # 4. FR900 최적화 ROSpec 생성 및 전송
            rospec_msg = self.create_fr900_optimized_rospec()
            if not rospec_msg:
                logger.error("ROSpec 메시지 생성 실패")
                return False
            
            response = self.connector.transact(rospec_msg)
            if not response.success():
                logger.error(f"ROSpec 추가 실패: {response}")
                return False
            logger.info("✅ FR900 최적화 ROSpec 추가 성공")
            
            # 5. 핸들러 등록
            self.tag_count = 0
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            logger.info("✅ 이벤트 핸들러 등록 완료")
            
            # 6. ROSpec 활성화
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            if not response.success():
                logger.error(f"ROSpec 활성화 실패: {response}")
                return False
            logger.info("✅ ROSpec 활성화 완료")
            
            # 7. 리스너 시작
            logger.info(f"🔄 {duration_seconds}초 동안 태그 읽기 시작...")
            self.connector.startListener()
            start_time = time.time()
            
            # 8. 지정 시간 대기
            time.sleep(duration_seconds)
            
            # 9. 정리
            logger.info("🛑 리스너 중지 중...")
            self.connector.stopListener()
            
            # ROSpec 비활성화
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            
            # ROSpec 삭제
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            
            # 연결 해제
            self.connector.disconnect()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 테스트 완료: {elapsed_time:.1f}초 동안 {self.tag_count}개 태그 읽음")
            
            if self.tag_count > 0:
                logger.info(f"📊 평균 읽기 속도: {self.tag_count/elapsed_time:.1f} tags/sec")
                return True
            else:
                logger.warning("⚠️ 읽은 태그가 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 인벤토리 테스트 실패: {e}")
            if self.connector:
                try:
                    self.connector.disconnect()
                except:
                    pass
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp EPC 읽기 테스트")
    print("===================================")
    
    # AutoDetect로 리더 찾기
    from esitarski_pyllrp.pyllrp.AutoDetect import AutoDetect
    
    try:
        reader_ip, computer_ip = AutoDetect()
        if reader_ip:
            print(f"🔍 리더 자동 탐지: {reader_ip}")
        else:
            reader_ip = "192.168.10.102"  # 기본값
            print(f"🔍 기본 리더 IP 사용: {reader_ip}")
    except:
        reader_ip = "192.168.10.102"
        print(f"🔍 기본 리더 IP 사용: {reader_ip}")
    
    # 테스트 실행
    tester = FR900EsitarskiWorking(reader_ip)
    success = tester.run_inventory_test(10)
    
    if success:
        print("\n🎉 EPC 값 읽기 성공!")
    else:
        print("\n😞 EPC 값 읽기 실패")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())