#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Simple Working Version
====================================================

esitarski/pyllrp의 TagInventory 클래스를 활용하여 가장 간단하게 EPC 값을 읽어오는 프로그램
"""

import sys
import time
import logging
from datetime import datetime

# esitarski/pyllrp 라이브러리 임포트
sys.path.insert(0, 'esitarski_pyllrp')

try:
    from esitarski_pyllrp.pyllrp.pyllrp import *
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

class FR900TagInventoryWrapper:
    """FR900용 TagInventory 래퍼 클래스"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.tag_inventory = None
    
    def test_basic_inventory(self):
        """기본 태그 인벤토리 테스트"""
        logger.info("=== 기본 태그 인벤토리 테스트 ===")
        
        try:
            # 기본 설정으로 TagInventory 생성
            self.tag_inventory = TagInventory(
                host=self.reader_ip,
                transmitPower=30,  # 전송 파워
                receiverSensitivity=1  # 수신 민감도
            )
            
            # 연결
            logger.info(f"리더 {self.reader_ip}에 연결 중...")
            self.tag_inventory.Connect()
            logger.info("✅ 리더 연결 성공")
            
            # 태그 인벤토리 실행
            logger.info("🔄 태그 인벤토리 실행 중...")
            tag_set, other_messages = self.tag_inventory.GetTagInventory()
            
            # 결과 출력
            logger.info(f"📊 발견된 태그 수: {len(tag_set)}")
            if tag_set:
                for i, epc in enumerate(tag_set, 1):
                    logger.info(f"✅ 태그 #{i}: EPC = {epc}")
                    
                # 상세 정보 출력
                logger.info(f"📝 상세 태그 정보 ({len(self.tag_inventory.tagDetail)}개):")
                for i, tag_detail in enumerate(self.tag_inventory.tagDetail, 1):
                    epc = tag_detail.get('Tag', 'N/A')
                    antenna_id = tag_detail.get('AntennaID', 'N/A')
                    rssi = tag_detail.get('PeakRSSI', 'N/A')
                    timestamp = tag_detail.get('FirstSeenTimestampUTC', 'N/A')
                    
                    logger.info(f"  태그 #{i}: EPC={epc}, 안테나={antenna_id}, "
                              f"RSSI={rssi}, 시간={timestamp}")
            else:
                logger.warning("⚠️ 발견된 태그가 없습니다")
            
            # 기타 메시지 정보
            if other_messages:
                logger.info(f"📩 기타 메시지: {len(other_messages)}개")
                for msg in other_messages:
                    logger.info(f"  - {type(msg).__name__}")
            
            # 연결 해제
            self.tag_inventory.Disconnect()
            logger.info("✅ 리더 연결 해제 완료")
            
            return len(tag_set) > 0
            
        except Exception as e:
            logger.error(f"❌ 태그 인벤토리 실패: {e}")
            if self.tag_inventory:
                try:
                    self.tag_inventory.Disconnect()
                except:
                    pass
            return False
    
    def test_different_powers(self):
        """다양한 전력 레벨에서 테스트"""
        logger.info("=== 다양한 전력 레벨 테스트 ===")
        
        power_levels = [10, 20, 30, 50]
        results = {}
        
        for power in power_levels:
            try:
                logger.info(f"🔋 전력 레벨 {power}로 테스트 중...")
                
                ti = TagInventory(
                    host=self.reader_ip,
                    transmitPower=power
                )
                
                ti.Connect()
                tag_set, _ = ti.GetTagInventory()
                ti.Disconnect()
                
                results[power] = len(tag_set)
                logger.info(f"  전력 {power}: {len(tag_set)}개 태그 발견")
                
                if tag_set:
                    for epc in tag_set:
                        logger.info(f"    EPC: {epc}")
                
                time.sleep(1)  # 잠깐 대기
                
            except Exception as e:
                logger.error(f"전력 {power} 테스트 실패: {e}")
                results[power] = -1
        
        # 결과 요약
        logger.info("📊 전력별 테스트 결과 요약:")
        for power, count in results.items():
            if count >= 0:
                logger.info(f"  전력 {power:2d}: {count}개 태그")
            else:
                logger.info(f"  전력 {power:2d}: 실패")
        
        return any(count > 0 for count in results.values())
    
    def test_continuous_reading(self, duration=30, power=30):
        """연속 읽기 테스트"""
        logger.info(f"=== {duration}초 연속 읽기 테스트 (전력={power}) ===")
        
        try:
            ti = TagInventory(
                host=self.reader_ip,
                transmitPower=power,
                defaultAntennas=[1]  # 안테나 1만 사용
            )
            
            ti.Connect()
            logger.info("✅ 연결 성공")
            
            start_time = time.time()
            total_reads = 0
            unique_tags = set()
            
            while (time.time() - start_time) < duration:
                try:
                    tag_set, _ = ti.GetTagInventory()
                    if tag_set:
                        total_reads += len(tag_set)
                        unique_tags.update(tag_set)
                        
                        elapsed = time.time() - start_time
                        logger.info(f"⏱️ {elapsed:.1f}초: {len(tag_set)}개 읽음 "
                                  f"(총 {total_reads}회, 고유 {len(unique_tags)}개)")
                        
                        for epc in tag_set:
                            logger.info(f"   📡 EPC: {epc}")
                    
                    time.sleep(0.5)  # 0.5초 간격
                    
                except Exception as e:
                    logger.error(f"읽기 중 오류: {e}")
                    time.sleep(1)
            
            ti.Disconnect()
            
            elapsed = time.time() - start_time
            logger.info(f"📊 연속 읽기 완료: {elapsed:.1f}초 동안")
            logger.info(f"   총 읽기 횟수: {total_reads}")
            logger.info(f"   고유 태그 수: {len(unique_tags)}")
            logger.info(f"   평균 속도: {total_reads/elapsed:.1f} reads/sec")
            
            if unique_tags:
                logger.info("📝 발견된 고유 태그들:")
                for i, epc in enumerate(unique_tags, 1):
                    logger.info(f"   {i}. {epc}")
            
            return len(unique_tags) > 0
            
        except Exception as e:
            logger.error(f"❌ 연속 읽기 테스트 실패: {e}")
            return False

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp Simple EPC 테스트")
    print("=====================================")
    
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
    wrapper = FR900TagInventoryWrapper(reader_ip)
    
    tests = [
        ("기본 인벤토리", wrapper.test_basic_inventory),
        ("다양한 전력", wrapper.test_different_powers),
        ("연속 읽기", lambda: wrapper.test_continuous_reading(20))  # 20초
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*60}")
            result = test_func()
            results.append((test_name, result))
            logger.info(f"{test_name} 테스트: {'✅ 성공' if result else '❌ 실패'}")
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
    
    logger.info(f"\n전체 성공률: {success_count}/{len(results)}")
    
    if success_count > 0:
        print(f"\n🎉 {success_count}개 테스트 성공! EPC 값 읽기 가능!")
    else:
        print("\n😞 모든 테스트 실패")
    
    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())