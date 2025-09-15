#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Final Working Version
====================================================

우리 PyLLRP에서 성공한 방법을 esitarski/pyllrp로 포팅하여 EPC 값을 성공적으로 읽어오는 프로그램
"""

import sys
import time
import logging
import struct
import socket
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

class FR900EsitarskiFinal:
    """FR900용 esitarski/pyllrp 최종 구현"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        self.rospec_id = 0x04D2  # 1234
        
    def access_report_handler(self, connector, access_report):
        """RO_ACCESS_REPORT 메시지 핸들러"""
        try:
            for tag_data in access_report.getTagData():
                self.tag_count += 1
                epc = HexFormatToStr(tag_data['EPC'])
                
                # 기본 정보 추출
                info = {
                    'count': self.tag_count,
                    'epc': epc,
                    'antenna_id': tag_data.get('AntennaID', 'N/A'),
                    'rssi': tag_data.get('PeakRSSI', 'N/A'),
                    'timestamp': tag_data.get('FirstSeenTimestampUTC', 'N/A')
                }
                
                logger.info(f"🏷️  태그 #{info['count']}: EPC={info['epc']}")
                logger.info(f"    안테나={info['antenna_id']}, RSSI={info['rssi']} dBm")
                
                # TV 파라미터에서 추가 RSSI 정보 추출 (FR900 특화)
                self.extract_tv_parameters(access_report)
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def extract_tv_parameters(self, access_report):
        """TV 파라미터에서 추가 정보 추출 (FR900 전용)"""
        try:
            # esitarski/pyllrp에서 raw 바이트 데이터 접근이 가능한지 확인
            # 일단은 기본 정보만 사용
            pass
        except Exception as e:
            logger.debug(f"TV 파라미터 추출 실패: {e}")
    
    def create_minimal_rospec(self):
        """FR900에서 작동하는 최소한의 ROSpec"""
        try:
            # 가장 기본적인 ROSpec - 우리 PyLLRP에서 성공한 구조와 유사하게
            return ADD_ROSPEC_Message(
                MessageID=1,
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.rospec_id,
                        CurrentState=ROSpecState.Disabled,
                        Parameters=[
                            # 경계 조건 - 즉시 시작, 무한 실행
                            ROBoundarySpec_Parameter(Parameters=[
                                ROSpecStartTrigger_Parameter(
                                    ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                                ),
                                ROSpecStopTrigger_Parameter(
                                    ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                                )
                            ]),
                            # 안테나 설정 - 모든 안테나, 무한 실행
                            AISpec_Parameter(
                                AntennaIDs=[0],  # 모든 안테나
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
                            # 리포트 설정 - 태그 하나씩 즉시 보고
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
                ]
            )
        except Exception as e:
            logger.error(f"ROSpec 생성 실패: {e}")
            return None
    
    def test_basic_connection(self):
        """기본 연결 테스트"""
        logger.info("=== 기본 연결 테스트 ===")
        try:
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("✅ 리더 연결 성공")
            logger.info(f"연결 응답: {response}")
            self.connector.disconnect()
            return True
        except Exception as e:
            logger.error(f"연결 실패: {e}")
            return False
    
    def test_factory_reset_only(self):
        """공장 초기화만 테스트"""
        logger.info("=== 공장 초기화 테스트 ===")
        try:
            self.connector = LLRPConnector()
            self.connector.connect(self.reader_ip)
            
            # 공장 초기화
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if response.success():
                logger.info("✅ 공장 초기화 성공")
                result = True
            else:
                logger.error(f"❌ 공장 초기화 실패: {response}")
                result = False
            
            self.connector.disconnect()
            return result
            
        except Exception as e:
            logger.error(f"공장 초기화 테스트 실패: {e}")
            return False
    
    def test_rospec_add_only(self):
        """ROSpec 추가만 테스트"""
        logger.info("=== ROSpec 추가 테스트 ===")
        try:
            self.connector = LLRPConnector()
            self.connector.connect(self.reader_ip)
            
            # 공장 초기화
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if not response.success():
                logger.error(f"공장 초기화 실패: {response}")
                return False
            
            # 기존 ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            
            # ROSpec 생성 및 추가
            rospec_msg = self.create_minimal_rospec()
            if not rospec_msg:
                logger.error("ROSpec 생성 실패")
                return False
            
            response = self.connector.transact(rospec_msg)
            if response.success():
                logger.info("✅ ROSpec 추가 성공")
                
                # 즉시 삭제
                self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
                result = True
            else:
                logger.error(f"❌ ROSpec 추가 실패: {response}")
                result = False
            
            self.connector.disconnect()
            return result
            
        except Exception as e:
            logger.error(f"ROSpec 추가 테스트 실패: {e}")
            return False
    
    def test_full_inventory_cycle(self, duration=5):
        """전체 인벤토리 사이클 테스트"""
        logger.info(f"=== {duration}초 전체 인벤토리 테스트 ===")
        
        try:
            # 1. 연결
            self.connector = LLRPConnector()
            response = self.connector.connect(self.reader_ip)
            logger.info("✅ 리더 연결 성공")
            
            # 2. 공장 초기화
            response = self.connector.transact(SET_READER_CONFIG_Message(ResetToFactoryDefault=True))
            if not response.success():
                logger.error(f"공장 초기화 실패: {response}")
                return False
            logger.info("✅ 공장 초기화 완료")
            
            # 3. 기존 ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            logger.info("✅ 기존 ROSpec 정리 완료")
            
            # 4. ROSpec 추가
            rospec_msg = self.create_minimal_rospec()
            if not rospec_msg:
                logger.error("ROSpec 생성 실패")
                return False
            
            response = self.connector.transact(rospec_msg)
            if not response.success():
                logger.error(f"ROSpec 추가 실패: {response}")
                return False
            logger.info("✅ ROSpec 추가 성공")
            
            # 5. 핸들러 등록
            self.tag_count = 0
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            logger.info("✅ 핸들러 등록 완료")
            
            # 6. ROSpec 활성화
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            if not response.success():
                logger.error(f"ROSpec 활성화 실패: {response}")
                return False
            logger.info("✅ ROSpec 활성화 완료")
            
            # 7. 리스너 시작 및 대기
            logger.info(f"🔄 {duration}초 동안 태그 읽기...")
            self.connector.startListener()
            start_time = time.time()
            time.sleep(duration)
            
            # 8. 정리
            logger.info("🛑 리스너 중지...")
            self.connector.stopListener()
            
            # ROSpec 비활성화 및 삭제
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            
            # 연결 해제
            self.connector.disconnect()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ 테스트 완료: {elapsed:.1f}초 동안 {self.tag_count}개 태그 읽음")
            
            if self.tag_count > 0:
                logger.info(f"📊 평균 읽기 속도: {self.tag_count/elapsed:.1f} tags/sec")
                return True
            else:
                logger.warning("⚠️ 읽은 태그가 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 전체 인벤토리 테스트 실패: {e}")
            if self.connector:
                try:
                    self.connector.disconnect()
                except:
                    pass
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp 최종 EPC 테스트")
    print("====================================")
    
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
    tester = FR900EsitarskiFinal(reader_ip)
    
    tests = [
        ("기본 연결", tester.test_basic_connection),
        ("공장 초기화", tester.test_factory_reset_only),
        ("ROSpec 추가", tester.test_rospec_add_only),
        ("전체 인벤토리 (10초)", lambda: tester.test_full_inventory_cycle(10))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*60}")
            result = test_func()
            results.append((test_name, result))
            logger.info(f"{test_name}: {'✅ 성공' if result else '❌ 실패'}")
            
            if not result and test_name != "전체 인벤토리 (10초)":
                logger.warning(f"{test_name} 실패로 인해 후속 테스트 중단")
                break
                
        except Exception as e:
            logger.error(f"{test_name} 테스트 중 예외: {e}")
            results.append((test_name, False))
        
        time.sleep(2)  # 테스트 간 대기
    
    # 최종 결과
    logger.info(f"\n{'='*60}")
    logger.info("최종 테스트 결과:")
    success_count = 0
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        logger.info(f"  {test_name}: {status}")
        if result:
            success_count += 1
    
    if success_count == len(results) and any(result for _, result in results):
        print(f"\n🎉 모든 테스트 성공! esitarski/pyllrp로 FR900에서 EPC 값 읽기 성공!")
    elif success_count > 0:
        print(f"\n✅ 부분 성공: {success_count}/{len(results)} 테스트 통과")
    else:
        print("\n😞 모든 테스트 실패")
    
    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())