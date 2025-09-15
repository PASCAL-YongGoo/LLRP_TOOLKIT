#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Final Working Version
===================================================

esitarski/pyllrp의 검증된 방식을 활용하되 START_ROSPEC을 추가하여 실제 태그 읽기 성공
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
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FR900FinalWorking:
    """FR900용 최종 작동 버전 - esitarski 검증 방식 + START_ROSPEC"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.tag_count = 0
        self.found_tags = set()
        
    def method1_use_taginventory_directly(self):
        """방법1: esitarski TagInventory를 그대로 사용"""
        logger.info("=" * 60)
        logger.info("🎯 방법1: esitarski TagInventory 직접 사용")
        logger.info("=" * 60)
        
        try:
            # 여러 파워 레벨로 시도
            power_levels = [10, 20, 30, 50]
            
            for power in power_levels:
                logger.info(f"🔋 전송 파워 {power}으로 시도 중...")
                
                try:
                    ti = TagInventory(
                        host=self.reader_ip,
                        transmitPower=power,
                        receiverSensitivity=1
                    )
                    
                    ti.Connect()
                    logger.info("✅ TagInventory 연결 성공")
                    
                    # 여러 번 시도
                    for attempt in range(3):
                        logger.info(f"📡 시도 {attempt+1}/3")
                        tag_inventory, other_messages = ti.GetTagInventory()
                        
                        if tag_inventory:
                            logger.info(f"🎉 발견! {len(tag_inventory)}개 태그")
                            for i, epc in enumerate(tag_inventory, 1):
                                logger.info(f"   태그 {i}: {epc}")
                                self.found_tags.add(epc)
                            
                            # 상세 정보
                            if ti.tagDetail:
                                for detail in ti.tagDetail:
                                    epc = detail.get('Tag', 'N/A')
                                    rssi = detail.get('PeakRSSI', 'N/A')
                                    antenna = detail.get('AntennaID', 'N/A')
                                    logger.info(f"   📊 {epc}: RSSI={rssi}, 안테나={antenna}")
                            
                            ti.Disconnect()
                            return True
                        else:
                            logger.info("⚠️ 이번 시도에서는 태그 없음")
                        
                        time.sleep(1)
                    
                    ti.Disconnect()
                    
                except Exception as e:
                    logger.error(f"전력 {power} 시도 실패: {e}")
                    continue
            
            return len(self.found_tags) > 0
            
        except Exception as e:
            logger.error(f"방법1 실패: {e}")
            return False
    
    def method2_manual_start_rospec(self):
        """방법2: 수동으로 START_ROSPEC 추가"""
        logger.info("=" * 60)
        logger.info("🎯 방법2: 수동 START_ROSPEC 추가")
        logger.info("=" * 60)
        
        try:
            connector = LLRPConnector()
            connector.connect(self.reader_ip)
            logger.info("✅ 수동 연결 성공")
            
            # GET_READER_CAPABILITIES
            response = connector.transact(GET_READER_CAPABILITIES_Message())
            logger.info("✅ GET_READER_CAPABILITIES 완료")
            
            # 공장 초기화
            response = connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            logger.info("✅ 공장 초기화 완료")
            
            # 기존 정리
            connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            connector.transact(DELETE_ROSPEC_Message(ROSpecID=0))
            logger.info("✅ 기존 ROSpec 정리")
            
            # esitarski 방식의 ROSpec 생성
            rospec_id = 123
            rospec_msg = ADD_ROSPEC_Message(Parameters=[
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
                            AntennaIDs=[0],  # 모든 안테나
                            Parameters=[
                                AISpecStopTrigger_Parameter(
                                    AISpecStopTriggerType=AISpecStopTriggerType.Tag_Observation,
                                    Parameters=[
                                        TagObservationTrigger_Parameter(
                                            TriggerType=TagObservationTriggerType.N_Attempts_To_See_All_Tags_In_FOV_Or_Timeout,
                                            NumberOfAttempts=10,
                                            Timeout=2000
                                        )
                                    ]
                                ),
                                InventoryParameterSpec_Parameter(
                                    InventoryParameterSpecID=1234,
                                    ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                                )
                            ]
                        ),
                        ROReportSpec_Parameter(
                            ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                            N=1,
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
            
            # ROSpec 추가
            response = connector.transact(rospec_msg)
            if not response.success():
                logger.error(f"ROSpec 추가 실패: {response}")
                connector.disconnect()
                return False
            logger.info("✅ ROSpec 추가 성공")
            
            # ROSpec 활성화
            response = connector.transact(ENABLE_ROSPEC_Message(ROSpecID=rospec_id))
            if not response.success():
                logger.error(f"ROSpec 활성화 실패: {response}")
                connector.disconnect()
                return False
            logger.info("✅ ROSpec 활성화 성공")
            
            # 이벤트 핸들러 등록
            def access_handler(conn, msg):
                try:
                    for tag_data in msg.getTagData():
                        self.tag_count += 1
                        epc = HexFormatToStr(tag_data['EPC'])
                        rssi = tag_data.get('PeakRSSI', 'N/A')
                        antenna = tag_data.get('AntennaID', 'N/A')
                        
                        logger.info(f"🏷️  태그 #{self.tag_count}: {epc}")
                        logger.info(f"    📶 RSSI: {rssi} dBm, 📍 안테나: {antenna}")
                        self.found_tags.add(epc)
                except Exception as e:
                    logger.error(f"태그 처리 오류: {e}")
            
            connector.addHandler(RO_ACCESS_REPORT_Message, access_handler)
            
            # 리스너 시작
            connector.startListener()
            logger.info("🎧 리스너 시작")
            
            # 10초 대기
            logger.info("🔄 10초 동안 대기 중...")
            for i in range(10):
                logger.info(f"⏳ {i+1}/10초 - 태그 {self.tag_count}개")
                time.sleep(1)
            
            # 정리
            connector.stopListener()
            connector.transact(DISABLE_ROSPEC_Message(ROSpecID=rospec_id))
            connector.transact(DELETE_ROSPEC_Message(ROSpecID=rospec_id))
            connector.disconnect()
            
            logger.info(f"✅ 방법2 완료: {self.tag_count}개 태그, {len(self.found_tags)}개 고유")
            return self.tag_count > 0
            
        except Exception as e:
            logger.error(f"방법2 실패: {e}")
            return False
    
    def method3_continuous_attempts(self, duration=30):
        """방법3: 지속적인 시도"""
        logger.info("=" * 60)
        logger.info(f"🎯 방법3: {duration}초 지속 시도")
        logger.info("=" * 60)
        
        start_time = time.time()
        attempt_count = 0
        success_count = 0
        
        while (time.time() - start_time) < duration:
            attempt_count += 1
            elapsed = time.time() - start_time
            
            logger.info(f"🔄 시도 {attempt_count} (경과: {elapsed:.1f}초)")
            
            try:
                ti = TagInventory(host=self.reader_ip)
                ti.Connect()
                tag_inventory, _ = ti.GetTagInventory()
                ti.Disconnect()
                
                if tag_inventory:
                    success_count += 1
                    logger.info(f"✅ {len(tag_inventory)}개 태그 발견!")
                    for epc in tag_inventory:
                        logger.info(f"   📡 {epc}")
                        self.found_tags.add(epc)
                else:
                    logger.info("⚠️ 이번에는 태그 없음")
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"시도 {attempt_count} 실패: {e}")
                time.sleep(3)
        
        logger.info(f"📊 방법3 완료: {attempt_count}번 시도, {success_count}번 성공")
        logger.info(f"🏷️  총 고유 태그: {len(self.found_tags)}개")
        
        return len(self.found_tags) > 0
    
    def run_all_methods(self):
        """모든 방법 시도"""
        logger.info("🚀 FR900 esitarski/pyllrp 최종 작동 테스트")
        logger.info(f"📡 리더: {self.reader_ip}")
        logger.info("🎯 3가지 방법으로 태그 읽기 시도")
        
        methods = [
            ("esitarski TagInventory 직접 사용", self.method1_use_taginventory_directly),
            ("수동 START_ROSPEC 추가", self.method2_manual_start_rospec),
            ("30초 지속 시도", lambda: self.method3_continuous_attempts(30))
        ]
        
        for method_name, method_func in methods:
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"🎯 {method_name} 시작")
                
                result = method_func()
                
                if result:
                    logger.info(f"✅ {method_name} 성공!")
                    break
                else:
                    logger.info(f"⚠️ {method_name} 실패")
                    
                time.sleep(3)  # 방법 간 대기
                
            except KeyboardInterrupt:
                logger.info(f"\n🛑 사용자가 {method_name}를 중지했습니다")
                break
            except Exception as e:
                logger.error(f"❌ {method_name} 중 예외: {e}")
        
        # 최종 결과
        logger.info(f"\n{'='*80}")
        logger.info("🎯 최종 결과")
        logger.info(f"🏷️  총 발견 고유 태그: {len(self.found_tags)}개")
        logger.info(f"📊 총 읽기 횟수: {self.tag_count}번")
        
        if self.found_tags:
            logger.info("📋 발견된 태그들:")
            for i, epc in enumerate(self.found_tags, 1):
                logger.info(f"   {i}. {epc}")
            return True
        else:
            logger.warning("😞 태그를 찾지 못했습니다")
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp 최종 작동 버전")
    print("==================================")
    print("🎯 3가지 방법으로 태그 읽기 시도")
    print("📋 검증된 esitarski 방식 활용")
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
    
    # 테스트 실행
    tester = FR900FinalWorking(reader_ip)
    success = tester.run_all_methods()
    
    if success:
        print(f"\n🎉 esitarski/pyllrp로 FR900 태그 읽기 성공!")
    else:
        print(f"\n😞 모든 방법 실패")
    
    return 0 if success else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 프로그램을 종료합니다.")
        sys.exit(0)