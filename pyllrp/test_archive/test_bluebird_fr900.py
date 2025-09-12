#!/usr/bin/env python3
"""
Bluebird FR900 LLRP Test Script
Based on Wireshark log analysis
"""

import time
import logging
from llrp.client import LLRPClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def tag_callback(tag_info):
    """Callback function called for each tag read"""
    print(f"[TAG] EPC: {tag_info['epc']} | "
          f"Antenna: {tag_info['antenna_id']} | "
          f"RSSI: {tag_info['rssi']} dBm | "
          f"Count: {tag_info['seen_count']}")

def main():
    # FR900 Reader configuration
    READER_IP = "192.168.10.106"  # FR900 reader IP from log
    
    print("="*60)
    print("Bluebird FR900 LLRP Test")
    print("Based on Wireshark log analysis")
    print("="*60)
    
    # Create LLRP client
    reader = LLRPClient(READER_IP)
    
    try:
        # Step 1: Connect to reader
        print(f"\n[1] Connecting to FR900 at {READER_IP}...")
        if not reader.connect():
            print("Failed to connect!")
            return
        print("Connected successfully!")
        
        # Step 2: Get reader capabilities
        print("\n[2] Getting reader capabilities...")
        caps = reader.get_capabilities()
        if caps:
            print(f"Reader Model: {caps.get('model_name', 'Unknown')}")
            print(f"Firmware: {caps.get('firmware_version', 'Unknown')}")
            print(f"Antennas: {caps.get('num_antennas', 'Unknown')}")
        
        # Step 3: Clear existing ROSpecs
        print("\n[3] Clearing existing ROSpecs...")
        reader.clear_rospecs()
        print("ROSpecs cleared")
        
        # Step 4: Configure reader
        print("\n[4] Configuring reader settings...")
        # Set reader configuration (based on log analysis)
        reader.set_reader_config()
        print("Reader configured")
        
        # Step 5: Create and add ROSpec
        print("\n[5] Creating ROSpec for inventory...")
        rospec = reader.create_basic_rospec(
            rospec_id=1,
            duration_ms=0,  # Continuous
            antenna_ids=None,  # All antennas
            report_every_n_tags=1,  # Report each tag immediately
            start_immediate=False
        )
        
        if reader.add_rospec(rospec):
            print("ROSpec added successfully")
        else:
            print("Failed to add ROSpec")
            return
        
        # Step 6: Enable ROSpec
        print("\n[6] Enabling ROSpec...")
        if reader.enable_rospec(1):
            print("ROSpec enabled")
        else:
            print("Failed to enable ROSpec")
            return
        
        # Step 7: Start inventory
        print("\n[7] Starting inventory (10 seconds)...")
        print("-"*40)
        
        # Clear previous tags
        reader.tags_read.clear()
        
        # Start ROSpec
        if reader.start_rospec(1):
            print("Inventory started - Reading tags...")
            
            # Read for 10 seconds
            start_time = time.time()
            while time.time() - start_time < 10:
                time.sleep(0.1)
                # Tags are processed in callback
            
            # Stop ROSpec
            print("\n[8] Stopping inventory...")
            reader.stop_rospec(1)
            print("Inventory stopped")
        else:
            print("Failed to start ROSpec")
        
        # Step 9: Show results
        print("\n" + "="*60)
        print("INVENTORY RESULTS")
        print("="*60)
        
        total_reads = len(reader.tags_read)
        unique_epcs = set(tag['epc'] for tag in reader.tags_read if tag['epc'])
        
        print(f"Total tag reads: {total_reads}")
        print(f"Unique tags found: {len(unique_epcs)}")
        
        if unique_epcs:
            print("\nUnique EPCs:")
            for i, epc in enumerate(unique_epcs, 1):
                print(f"  {i}. {epc}")
        
        # Calculate read rate (similar to log: ~95 reports/sec)
        if total_reads > 0:
            read_rate = total_reads / 10.0
            print(f"\nRead rate: {read_rate:.1f} tags/second")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Step 10: Disconnect
        print("\n[10] Disconnecting from reader...")
        reader.disconnect()
        print("Disconnected")
        print("\nTest completed!")

if __name__ == "__main__":
    main()