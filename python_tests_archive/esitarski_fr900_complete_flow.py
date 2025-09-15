#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Complete Flow Version
===================================================

실제 성공한 통신 과정을 완전히 재현하여 태그 읽기 성공
- GET_READER_CAPABILITIES 추가
- DELETE_ACCESSSPEC 추가  
- START_ROSPEC 추가 (핵심!)
- STOP_ROSPEC 추가
- 완전한 통신 플로우 구현
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

class FR900CompleteFlow:
    """FR900용 완전한 통신 플로우 구현"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        
        # 성공한 패킷에서 추출한 값들
        self.ROSPEC_ID = 1234
        self.ACCESSSPEC_ID = 0  # 일반적으로 0 사용
        self.INVENTORY_PARAM_ID = 1234
        self.ANTENNA_IDS = [1]
        self.REPORT_N_VALUE = 1
        
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
                    'timestamp': tag_data.get('FirstSeenTimestampUTC', 'N/A')
                }
                
                logger.info(f"🏷️  태그 #{info['count']}: {info['epc']}")
                logger.info(f"    📶 RSSI: {info['rssi']} dBm, 📍 안테나: {info['antenna_id']}")
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def step1_get_reader_capabilities(self):
        """1단계: GET_READER_CAPABILITIES"""
        logger.info("📋 1. GET_READER_CAPABILITIES")
        try:
            response = self.connector.transact(GET_READER_CAPABILITIES_Message())
            if response.success():
                logger.info("✅ 리더 기능 정보 수신 성공")
                return True
            else:
                logger.error(f"❌ GET_READER_CAPABILITIES 실패: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ GET_READER_CAPABILITIES 오류: {e}")
            return False
    
    def step2_initial_config(self):
        """2단계: 초기 설정"""
        logger.info("⚙️  2. 초기 리더 설정")
        try:
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if response.success():
                logger.info("✅ 공장 초기화 완료")
                return True
            else:
                logger.error(f"❌ 초기 설정 실패: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ 초기 설정 오류: {e}")
            return False
    
    def step3_cleanup_specs(self):
        """3단계: 기존 Spec 정리"""
        logger.info("🧹 3. 기존 ROSpec/AccessSpec 정리")
        try:
            # ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))  # 모든 ROSpec
            response1 = self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=0))  # 모든 ROSpec
            
            # AccessSpec 정리 
            response2 = self.connector.transact(DELETE_ACCESSSPEC_Message(AccessSpecID=0))  # 모든 AccessSpec
            
            logger.info("✅ ROSpec 및 AccessSpec 정리 완료")
            return True
        except Exception as e:
            logger.error(f"❌ Spec 정리 오류: {e}")
            return False
    
    def step4_create_rospec(self):
        """4단계: ROSpec 생성 및 추가"""
        logger.info("📝 4. ROSpec 생성 및 추가")
        try:
            rospec_msg = ADD_ROSPEC_Message(
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.ROSPEC_ID,
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
                            ROReportSpec_Parameter(
                                ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                                N=self.REPORT_N_VALUE,
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
            
            response = self.connector.transact(rospec_msg)
            if response.success():
                logger.info("✅ ROSpec 추가 성공")
                return True
            else:
                logger.error(f"❌ ROSpec 추가 실패: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ ROSpec 생성 오류: {e}")
            return False
    
    def step5_enable_rospec(self):
        """5단계: ROSpec 활성화"""
        logger.info("🔛 5. ROSpec 활성화")
        try:
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            if response.success():
                logger.info("✅ ROSpec 활성화 완료")
                return True
            else:
                logger.error(f"❌ ROSpec 활성화 실패: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ ROSpec 활성화 오류: {e}")
            return False
    
    def step6_start_rospec(self):
        """6단계: ROSpec 시작 (핵심!)"""
        logger.info("🚀 6. ROSpec 시작 (인벤토리 시작!)")
        try:
            response = self.connector.transact(START_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            if response.success():
                logger.info("✅ ROSpec 시작 - 인벤토리 시작됨!")
                return True
            else:
                logger.error(f"❌ ROSpec 시작 실패: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ ROSpec 시작 오류: {e}")
            return False
    
    def step7_stop_rospec(self):
        """7단계: ROSpec 중지"""
        logger.info("🛑 7. ROSpec 중지")
        try:
            response = self.connector.transact(STOP_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            if response.success():
                logger.info("✅ ROSpec 중지 완료")
                return True
            else:
                logger.error(f"❌ ROSpec 중지 실패: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ ROSpec 중지 오류: {e}")
            return False
    
    def step8_cleanup_and_disconnect(self):
        """8단계: 정리 및 연결 해제"""
        logger.info("🧹 8. 정리 및 연결 해제")
        try:
            # ROSpec 비활성화 및 삭제
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.ROSPEC_ID))
            
            # 연결 해제
            self.connector.disconnect()
            logger.info("✅ 정리 및 연결 해제 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 정리 오류: {e}")
            return False
    
    def run_complete_inventory(self, duration=10):
        """완전한 통신 플로우로 인벤토리 실행"""
        logger.info("=" * 80)
        logger.info("🎯 FR900 완전한 통신 플로우로 태그 읽기!")
        logger.info(f"📡 리더: {self.reader_ip}")
        logger.info(f"⏱️  읽기 시간: {duration}초")
        logger.info("✨ 실제 성공 과정을 완전히 재현")
        logger.info("=" * 80)
        
        try:
            # 연결
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("✅ 리더 연결 성공")
            
            # 1단계: GET_READER_CAPABILITIES
            if not self.step1_get_reader_capabilities():
                raise Exception("GET_READER_CAPABILITIES 실패")
            
            # 2단계: 초기 설정
            if not self.step2_initial_config():
                raise Exception("초기 설정 실패")
            
            # 3단계: Spec 정리
            if not self.step3_cleanup_specs():
                raise Exception("Spec 정리 실패")
            
            # 4단계: ROSpec 생성
            if not self.step4_create_rospec():
                raise Exception("ROSpec 생성 실패")
            
            # 5단계: ROSpec 활성화
            if not self.step5_enable_rospec():
                raise Exception("ROSpec 활성화 실패")
            
            # 6단계: ROSpec 시작 (실제 인벤토리 시작!)
            if not self.step6_start_rospec():
                raise Exception("ROSpec 시작 실패")
            
            # 핸들러 등록
            self.tag_count = 0
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            logger.info("✅ 이벤트 핸들러 등록 완료")
            
            # 리스너 시작
            self.connector.startListener()
            logger.info("🎧 이벤트 리스너 시작")
            
            # 태그 읽기 대기
            logger.info(f"🔄 {duration}초 동안 태그 읽기 중...")
            logger.info("📋 태그를 리더에 가져다 대세요!")
            
            start_time = time.time()
            last_report = start_time
            
            while (time.time() - start_time) < duration:
                current = time.time()
                if current - last_report >= 2:
                    elapsed = current - start_time
                    remaining = duration - elapsed
                    logger.info(f"⏳ {elapsed:.1f}초 경과, {remaining:.1f}초 남음 (태그 {self.tag_count}개)")
                    last_report = current
                time.sleep(0.1)
            
            # 7단계: ROSpec 중지
            if not self.step7_stop_rospec():
                logger.warning("ROSpec 중지 실패 - 강제 진행")
            
            # 리스너 중지
            self.connector.stopListener()
            logger.info("🎧 이벤트 리스너 중지")
            
            # 8단계: 정리
            if not self.step8_cleanup_and_disconnect():
                logger.warning("정리 과정 실패")
            
            # 결과
            elapsed = time.time() - start_time
            logger.info("=" * 80)
            logger.info("📊 완전한 플로우 태그 읽기 결과")
            logger.info(f"⏱️  실행 시간: {elapsed:.1f}초")
            logger.info(f"🏷️  읽은 태그 수: {self.tag_count}개")
            logger.info("🎯 방식: 실제 성공 과정 완전 재현")
            
            if self.tag_count > 0:
                logger.info(f"📈 읽기 속도: {self.tag_count/elapsed:.1f} 태그/초")
                logger.info("🎉 완전한 플로우로 태그 읽기 성공!")
                return True
            else:
                logger.warning("⚠️ 읽은 태그가 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 완전한 플로우 실행 실패: {e}")
            if self.connector:
                try:
                    self.connector.stopListener()
                    self.connector.disconnect()
                except:
                    pass
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp 완전한 통신 플로우")
    print("=====================================")
    print("✨ 실제 성공한 과정을 완전히 재현")
    print("📋 GET_READER_CAPABILITIES → START_ROSPEC 포함")
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
    durations = [10, 20, 30]
    print("\\n읽기 시간 선택:")
    for i, dur in enumerate(durations, 1):
        print(f"{i}. {dur}초")
    
    # 기본값 사용
    choice = 1
    duration = durations[choice-1]
    print(f"선택: {choice} ({duration}초)")
    
    # 테스트 실행
    tester = FR900CompleteFlow(reader_ip)
    success = tester.run_complete_inventory(duration)
    
    if success:
        print(f"\\n🎉 완전한 플로우로 태그 읽기 성공!")
        print("✨ START_ROSPEC으로 실제 인벤토리가 시작되었습니다!")
    else:
        print(f"\\n😞 태그 읽기 실패")
    
    return 0 if success else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\\n\\n🛑 프로그램을 종료합니다.")
        sys.exit(0)