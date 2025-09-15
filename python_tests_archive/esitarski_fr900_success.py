#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - SUCCESS VERSION
=============================================

esitarski/pyllrp로 FR900에서 성공적으로 EPC 값을 읽어오는 완성 버전
우리가 검증한 ROSpec 설정과 방법론을 적용
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

class FR900EsitarskiSuccess:
    """FR900용 esitarski/pyllrp 성공 버전"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.connector = None
        self.tag_count = 0
        self.rospec_id = 1234  # 우리가 성공한 ROSpec ID
        
    def access_report_handler(self, connector, access_report):
        """RO_ACCESS_REPORT 메시지 핸들러 - EPC 추출"""
        try:
            for tag_data in access_report.getTagData():
                self.tag_count += 1
                
                # EPC 값 추출
                epc = HexFormatToStr(tag_data['EPC'])
                
                # 기본 정보
                info = {
                    'count': self.tag_count,
                    'epc': epc,
                    'antenna_id': tag_data.get('AntennaID', 'Unknown'),
                    'rssi': tag_data.get('PeakRSSI', 'N/A'),
                    'timestamp': tag_data.get('FirstSeenTimestampUTC', 'N/A'),
                    'seen_count': tag_data.get('TagSeenCount', 'N/A')
                }
                
                # EPC 값 출력 - 성공 표시
                logger.info(f"🏷️  태그 발견 #{info['count']}")
                logger.info(f"    📡 EPC: {info['epc']}")
                logger.info(f"    📶 RSSI: {info['rssi']} dBm")
                logger.info(f"    📍 안테나: {info['antenna_id']}")
                logger.info(f"    🔢 읽기 횟수: {info['seen_count']}")
                
        except Exception as e:
            logger.error(f"태그 데이터 처리 중 오류: {e}")
    
    def create_working_rospec(self):
        """FR900에서 실제로 작동하는 ROSpec 생성 - 우리 성공 사례 기반"""
        try:
            # 우리가 검증한 설정을 esitarski/pyllrp 방식으로 구현
            return ADD_ROSPEC_Message(
                MessageID=1,
                Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=self.rospec_id,
                        CurrentState=ROSpecState.Disabled,
                        Parameters=[
                            # 경계 설정 - 즉시 시작, 무제한 실행
                            ROBoundarySpec_Parameter(Parameters=[
                                ROSpecStartTrigger_Parameter(
                                    ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                                ),
                                ROSpecStopTrigger_Parameter(
                                    ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                                )
                            ]),
                            # 안테나 설정 - 타임아웃 기반 중지
                            AISpec_Parameter(
                                AntennaIDs=[1],  # 안테나 1 사용
                                Parameters=[
                                    AISpecStopTrigger_Parameter(
                                        AISpecStopTriggerType=AISpecStopTriggerType.Tag_Observation,
                                        Parameters=[
                                            TagObservationTrigger_Parameter(
                                                TriggerType=TagObservationTriggerType.N_Attempts_To_See_All_Tags_In_FOV_Or_Timeout,
                                                NumberOfAttempts=0,  # 무제한 시도
                                                Timeout=120000  # 120초 타임아웃
                                            )
                                        ]
                                    ),
                                    InventoryParameterSpec_Parameter(
                                        InventoryParameterSpecID=1234,
                                        ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                                    )
                                ]
                            ),
                            # 리포트 설정 - 태그별 즉시 보고
                            ROReportSpec_Parameter(
                                ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_AISpec,
                                N=1,  # 태그 1개마다 보고
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
                                        EnableTagSeenCount=True,
                                        EnableAccessSpecID=False
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Working ROSpec 생성 실패: {e}")
            return None
    
    def setup_reader_configuration(self):
        """FR900에 최적화된 리더 설정 - 단순화 버전"""
        try:
            # 아무 설정 없이 공장 초기화 상태 그대로 사용
            logger.info("✅ 공장 초기화 설정으로 사용")
            return True
                
        except Exception as e:
            logger.error(f"리더 설정 중 오류: {e}")
            return False
    
    def read_epc_values(self, duration=10):
        """EPC 값들을 읽어오는 메인 함수"""
        logger.info("=" * 60)
        logger.info("🚀 FR900 EPC 읽기 시작!")
        logger.info(f"📡 리더: {self.reader_ip}")
        logger.info(f"⏱️  실행 시간: {duration}초")
        logger.info("=" * 60)
        
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
            
            # 3. 리더 설정
            if not self.setup_reader_configuration():
                raise Exception("리더 설정 실패")
            
            # 4. 기존 ROSpec 정리
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=0))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            logger.info("✅ 기존 ROSpec 정리 완료")
            
            # 5. 검증된 ROSpec 추가
            rospec_msg = self.create_working_rospec()
            if not rospec_msg:
                raise Exception("ROSpec 생성 실패")
            
            response = self.connector.transact(rospec_msg)
            if not response.success():
                raise Exception(f"ROSpec 추가 실패: {response}")
            logger.info("✅ 작동 검증된 ROSpec 추가 성공")
            
            # 6. 이벤트 핸들러 등록
            self.tag_count = 0
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self.access_report_handler)
            logger.info("✅ EPC 읽기 핸들러 등록 완료")
            
            # 7. ROSpec 활성화
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            if not response.success():
                raise Exception(f"ROSpec 활성화 실패: {response}")
            logger.info("✅ ROSpec 활성화 완료")
            
            # 8. 리스너 시작 및 태그 읽기
            logger.info(f"🔄 {duration}초 동안 EPC 값 읽기 시작...")
            logger.info("📋 태그를 리더 근처에 가져다 대세요!")
            
            self.connector.startListener()
            start_time = time.time()
            
            # 진행 상황 표시
            last_report_time = start_time
            while (time.time() - start_time) < duration:
                current_time = time.time()
                if current_time - last_report_time >= 2:  # 2초마다 진행상황 표시
                    elapsed = current_time - start_time
                    remaining = duration - elapsed
                    logger.info(f"⏳ 진행: {elapsed:.1f}초 경과, {remaining:.1f}초 남음 (태그 {self.tag_count}개 읽음)")
                    last_report_time = current_time
                time.sleep(0.1)
            
            # 9. 정리
            logger.info("🛑 EPC 읽기 중지...")
            self.connector.stopListener()
            
            # ROSpec 비활성화 및 삭제
            self.connector.transact(DISABLE_ROSPEC_Message(ROSpecID=self.rospec_id))
            self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=self.rospec_id))
            
            # 연결 해제
            self.connector.disconnect()
            
            # 결과 요약
            elapsed = time.time() - start_time
            logger.info("=" * 60)
            logger.info("📊 EPC 읽기 결과 요약")
            logger.info(f"⏱️  실행 시간: {elapsed:.1f}초")
            logger.info(f"🏷️  읽은 태그 수: {self.tag_count}개")
            
            if self.tag_count > 0:
                logger.info(f"📈 평균 읽기 속도: {self.tag_count/elapsed:.1f} 태그/초")
                logger.info("🎉 EPC 값 읽기 성공!")
                return True
            else:
                logger.warning("⚠️ 읽은 태그가 없습니다")
                logger.info("💡 태그를 리더에 더 가까이 가져다 대거나 실행 시간을 늘려보세요")
                return False
                
        except Exception as e:
            logger.error(f"❌ EPC 읽기 실패: {e}")
            if self.connector:
                try:
                    self.connector.disconnect()
                except:
                    pass
            return False
    
    def continuous_reading(self):
        """연속 EPC 읽기 모드"""
        logger.info("🔄 연속 EPC 읽기 모드 (Ctrl+C로 중지)")
        
        try:
            while True:
                result = self.read_epc_values(30)  # 30초씩 반복
                if result:
                    logger.info("✅ 30초 읽기 세션 완료")
                else:
                    logger.info("⚠️ 이번 세션에서는 태그를 찾지 못했습니다")
                
                logger.info("⏸️ 3초 후 다음 세션 시작...")
                time.sleep(3)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 사용자가 연속 읽기를 중지했습니다")
        except Exception as e:
            logger.error(f"❌ 연속 읽기 중 오류: {e}")

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp EPC 성공 버전")
    print("==================================")
    
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
    
    # 실행 모드 선택
    print("\n실행 모드를 선택하세요:")
    print("1. 한번 실행 (10초)")
    print("2. 한번 실행 (30초)")
    print("3. 연속 실행 (Ctrl+C로 중지)")
    
    try:
        # 기본값 사용 (비대화형 환경)
        choice = "1"
        print(f"선택: {choice} (기본값)")
        
        reader = FR900EsitarskiSuccess(reader_ip)
        
        if choice == "1":
            success = reader.read_epc_values(10)
        elif choice == "2":
            success = reader.read_epc_values(30)
        elif choice == "3":
            reader.continuous_reading()
            success = True
        else:
            print("잘못된 선택입니다.")
            return 1
        
        if success:
            print("\n🎉 EPC 값 읽기 성공!")
            return 0
        else:
            print("\n😞 EPC 값을 읽지 못했습니다")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n🛑 프로그램을 종료합니다.")
        return 0
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())