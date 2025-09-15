#!/usr/bin/env python3
"""
FR900 with esitarski/pyllrp - Direct TagInventory Usage
=======================================================

esitarski/pyllrp의 TagInventory 클래스를 직접 사용하여 EPC 값 읽기
설정 없이 기본 동작만으로 성공시키기
"""

import sys
import time
import logging
from datetime import datetime

# esitarski/pyllrp 라이브러리 임포트
sys.path.insert(0, 'esitarski_pyllrp')

try:
    from esitarski_pyllrp.pyllrp.TagInventory import TagInventory
    from esitarski_pyllrp.pyllrp.AutoDetect import AutoDetect
    from esitarski_pyllrp.pyllrp.pyllrp import HexFormatToStr
except ImportError as e:
    print(f"esitarski/pyllrp 라이브러리를 찾을 수 없습니다: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FR900DirectInventory:
    """FR900용 직접 TagInventory 사용"""
    
    def __init__(self, reader_ip):
        self.reader_ip = reader_ip
        self.total_reads = 0
        self.unique_tags = set()
        
    def simple_read_once(self):
        """가장 간단한 한번 읽기"""
        logger.info("=== 기본 태그 인벤토리 (한번 읽기) ===")
        
        try:
            # 기본 설정으로 TagInventory 생성 - 아무 설정 없이
            ti = TagInventory(host=self.reader_ip)
            
            logger.info(f"📡 리더 {self.reader_ip}에 연결 중...")
            ti.Connect()
            logger.info("✅ 연결 성공")
            
            logger.info("🔄 태그 인벤토리 실행 중...")
            tag_inventory, other_messages = ti.GetTagInventory()
            
            logger.info(f"📊 결과: {len(tag_inventory)}개 태그 발견")
            
            if tag_inventory:
                logger.info("🏷️  발견된 EPC 값들:")
                for i, epc in enumerate(tag_inventory, 1):
                    logger.info(f"   {i}. {epc}")
                    self.unique_tags.add(epc)
                
                # 상세 정보도 출력
                if ti.tagDetail:
                    logger.info("📝 상세 태그 정보:")
                    for i, detail in enumerate(ti.tagDetail, 1):
                        epc = detail.get('Tag', 'Unknown')
                        antenna = detail.get('AntennaID', 'N/A')  
                        rssi = detail.get('PeakRSSI', 'N/A')
                        timestamp = detail.get('FirstSeenTimestampUTC', 'N/A')
                        
                        logger.info(f"   태그 {i}: EPC={epc}")
                        logger.info(f"            안테나={antenna}, RSSI={rssi}")
                
                success = True
            else:
                logger.warning("⚠️ 발견된 태그가 없습니다")
                success = False
            
            # 기타 메시지 정보
            if other_messages:
                logger.info(f"📩 기타 메시지: {len(other_messages)}개")
            
            ti.Disconnect()
            logger.info("✅ 연결 해제 완료")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 태그 읽기 실패: {e}")
            return False
    
    def read_with_power_levels(self):
        """다양한 파워 레벨에서 테스트"""
        logger.info("=== 다양한 파워 레벨 테스트 ===")
        
        power_levels = [20, 30, 50]  # 낮은 파워부터 시도
        
        for power in power_levels:
            logger.info(f"🔋 전송 파워 {power} 테스트 중...")
            
            try:
                ti = TagInventory(
                    host=self.reader_ip,
                    transmitPower=power
                )
                
                ti.Connect()
                tag_inventory, _ = ti.GetTagInventory()
                ti.Disconnect()
                
                if tag_inventory:
                    logger.info(f"✅ 전력 {power}: {len(tag_inventory)}개 태그 발견")
                    for epc in tag_inventory:
                        logger.info(f"   📡 EPC: {epc}")
                        self.unique_tags.add(epc)
                    return True
                else:
                    logger.info(f"⚠️ 전력 {power}: 태그 없음")
                
                time.sleep(1)  # 잠깐 대기
                
            except Exception as e:
                logger.error(f"전력 {power} 테스트 실패: {e}")
        
        return len(self.unique_tags) > 0
    
    def multiple_attempts(self, attempts=5):
        """여러 번 시도하여 태그 찾기"""
        logger.info(f"=== {attempts}번 반복 시도 ===")
        
        success_count = 0
        
        for attempt in range(1, attempts + 1):
            logger.info(f"🔄 시도 {attempt}/{attempts}")
            
            try:
                ti = TagInventory(host=self.reader_ip)
                ti.Connect()
                tag_inventory, _ = ti.GetTagInventory()
                ti.Disconnect()
                
                if tag_inventory:
                    success_count += 1
                    logger.info(f"✅ 시도 {attempt}: {len(tag_inventory)}개 태그 발견")
                    for epc in tag_inventory:
                        logger.info(f"   📡 EPC: {epc}")
                        self.unique_tags.add(epc)
                else:
                    logger.info(f"⚠️ 시도 {attempt}: 태그 없음")
                
                time.sleep(2)  # 시도 간 대기
                
            except Exception as e:
                logger.error(f"시도 {attempt} 실패: {e}")
        
        logger.info(f"📊 결과: {attempts}번 중 {success_count}번 성공")
        logger.info(f"🏷️  총 고유 태그 수: {len(self.unique_tags)}")
        
        return success_count > 0
    
    def continuous_monitoring(self, duration=30):
        """연속 모니터링"""
        logger.info(f"=== {duration}초 연속 모니터링 ===")
        
        start_time = time.time()
        attempt_count = 0
        success_count = 0
        
        while (time.time() - start_time) < duration:
            attempt_count += 1
            elapsed = time.time() - start_time
            
            logger.info(f"🔄 읽기 {attempt_count} (경과: {elapsed:.1f}초)")
            
            try:
                ti = TagInventory(host=self.reader_ip)
                ti.Connect()
                tag_inventory, _ = ti.GetTagInventory()
                ti.Disconnect()
                
                if tag_inventory:
                    success_count += 1
                    logger.info(f"✅ {len(tag_inventory)}개 태그 발견!")
                    for epc in tag_inventory:
                        logger.info(f"   📡 EPC: {epc}")
                        self.unique_tags.add(epc)
                else:
                    logger.info("⚠️ 이번엔 태그 없음")
                
                time.sleep(3)  # 3초 간격
                
            except Exception as e:
                logger.error(f"읽기 {attempt_count} 실패: {e}")
                time.sleep(5)  # 오류시 더 오래 대기
        
        total_time = time.time() - start_time
        logger.info(f"📊 연속 모니터링 완료:")
        logger.info(f"   총 시간: {total_time:.1f}초")
        logger.info(f"   총 시도: {attempt_count}번")
        logger.info(f"   성공: {success_count}번")
        logger.info(f"   성공률: {success_count/attempt_count*100:.1f}%")
        logger.info(f"   고유 태그: {len(self.unique_tags)}개")
        
        return success_count > 0

def main():
    """메인 함수"""
    print("FR900 esitarski/pyllrp Direct TagInventory 테스트")
    print("===============================================")
    
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
    inventory = FR900DirectInventory(reader_ip)
    
    tests = [
        ("한번 읽기", inventory.simple_read_once),
        ("파워 레벨 테스트", inventory.read_with_power_levels),
        ("5번 반복", lambda: inventory.multiple_attempts(5)),
        ("30초 연속 모니터링", lambda: inventory.continuous_monitoring(30))
    ]
    
    success_any = False
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*60}")
            result = test_func()
            
            if result:
                success_any = True
                logger.info(f"✅ {test_name} 성공!")
            else:
                logger.info(f"⚠️ {test_name} 실패")
            
        except KeyboardInterrupt:
            logger.info(f"\n🛑 사용자가 {test_name}를 중지했습니다")
            break
        except Exception as e:
            logger.error(f"❌ {test_name} 중 예외: {e}")
        
        time.sleep(3)  # 테스트 간 대기
    
    # 최종 결과
    logger.info(f"\n{'='*60}")
    logger.info("🎯 최종 결과:")
    if inventory.unique_tags:
        logger.info(f"🎉 성공! 총 {len(inventory.unique_tags)}개의 고유 EPC 값 발견:")
        for i, epc in enumerate(inventory.unique_tags, 1):
            logger.info(f"   {i}. {epc}")
        print(f"\n🎉 성공! {len(inventory.unique_tags)}개 EPC 값 읽기 완료!")
        return 0
    else:
        logger.warning("😞 EPC 값을 읽지 못했습니다")
        logger.info("💡 다음을 확인해보세요:")
        logger.info("   - 태그가 리더 읽기 범위 내에 있는지")
        logger.info("   - 리더 전원이 켜져있는지")  
        logger.info("   - 네트워크 연결이 정상인지")
        print("\n😞 EPC 값을 읽지 못했습니다")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 프로그램을 종료합니다.")
        sys.exit(0)