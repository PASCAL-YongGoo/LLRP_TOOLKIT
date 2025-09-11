#!/usr/bin/env python3
"""
Example usage of pure Python LLRP library
"""

import time
import logging
from llrp.client import LLRPClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def tag_callback(tag_info):
    """Callback function called for each tag read"""
    print(f"Tag detected: EPC={tag_info['epc']}, "
          f"Antenna={tag_info['antenna_id']}, "
          f"RSSI={tag_info['rssi']}, "
          f"Count={tag_info['seen_count']}")


def main():
    # Reader configuration
    READER_IP = "192.168.1.100"  # Change to your reader's IP
    
    # Create LLRP client
    reader = LLRPClient(READER_IP)
    
    try:
        # Connect to reader
        print(f"Connecting to reader at {READER_IP}...")
        if not reader.connect():
            print("Failed to connect!")
            return
        
        print("Connected successfully!")
        
        # Get reader capabilities
        print("\nGetting reader capabilities...")
        caps = reader.get_capabilities()
        if caps:
            print(f"Capabilities: {caps}")
        
        # Example 1: Simple inventory for 5 seconds
        print("\n" + "="*50)
        print("Example 1: Simple 5-second inventory")
        print("="*50)
        
        tags = reader.simple_inventory(
            duration_seconds=5.0,
            antenna_ids=None,  # Use all antennas
            tag_callback=tag_callback
        )
        
        print(f"\nTotal tags read: {len(tags)}")
        
        # Show unique tags
        unique_epcs = set(tag['epc'] for tag in tags if tag['epc'])
        print(f"Unique tags: {len(unique_epcs)}")
        for epc in unique_epcs:
            print(f"  - {epc}")
        
        # Example 2: Continuous inventory
        print("\n" + "="*50)
        print("Example 2: Continuous inventory (10 seconds)")
        print("="*50)
        
        # Clear tag list
        reader.tags_read.clear()
        
        # Start continuous reading
        if reader.start_continuous_inventory(tag_callback=tag_callback):
            print("Continuous inventory started. Reading for 10 seconds...")
            time.sleep(10)
            
            # Stop reading
            reader.stop_continuous_inventory()
            print(f"\nTotal tags read: {len(reader.tags_read)}")
        
        # Example 3: Custom ROSpec
        print("\n" + "="*50)
        print("Example 3: Custom ROSpec with specific antennas")
        print("="*50)
        
        # Clear ROSpecs
        reader.clear_rospecs()
        
        # Create custom ROSpec
        rospec = reader.create_basic_rospec(
            rospec_id=789,
            duration_ms=3000,  # 3 seconds
            antenna_ids=[1, 2],  # Only antennas 1 and 2
            report_every_n_tags=5,  # Report every 5 tags
            start_immediate=False
        )
        
        # Add and run ROSpec
        if reader.add_rospec(rospec):
            print("Custom ROSpec added")
            
            if reader.enable_rospec(789):
                print("ROSpec enabled")
                
                if reader.start_rospec(789):
                    print("ROSpec started, reading for 3 seconds...")
                    time.sleep(3.5)
                    
                    reader.stop_rospec(789)
                    print("ROSpec stopped")
        
        # Clean up
        reader.clear_rospecs()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always disconnect
        print("\nDisconnecting...")
        reader.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()