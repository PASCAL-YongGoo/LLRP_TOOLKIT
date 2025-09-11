#!/usr/bin/env python3
"""
Test script demonstrating improved tag report parsing
"""

import logging
from llrp.client import LLRPClient

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def detailed_tag_callback(tag_info):
    """Enhanced callback showing all parsed tag information"""
    print("=" * 60)
    print("🏷️  TAG DETECTED")
    print("=" * 60)
    
    # Basic information
    print(f"EPC: {tag_info['epc']}")
    if tag_info['antenna_id'] is not None:
        print(f"Antenna: {tag_info['antenna_id']}")
    if tag_info['rssi'] is not None:
        print(f"RSSI: {tag_info['rssi']} dBm")
    if tag_info['channel_index'] is not None:
        print(f"Channel: {tag_info['channel_index']}")
    
    # Timing information
    if tag_info['first_seen']:
        print(f"First Seen: {tag_info['first_seen']} μs")
    if tag_info['last_seen']:
        print(f"Last Seen: {tag_info['last_seen']} μs")
    if tag_info['seen_count'] is not None:
        print(f"Seen Count: {tag_info['seen_count']}")
    
    # ROSpec information
    if tag_info['rospec_id'] is not None:
        print(f"ROSpec ID: {tag_info['rospec_id']}")
    if tag_info['spec_index'] is not None:
        print(f"Spec Index: {tag_info['spec_index']}")
    if tag_info['inventory_param_spec_id'] is not None:
        print(f"Inventory Param Spec ID: {tag_info['inventory_param_spec_id']}")
    
    # Access information
    if tag_info['access_spec_id'] is not None:
        print(f"Access Spec ID: {tag_info['access_spec_id']}")
    
    # Detailed timestamps
    if tag_info['first_seen_utc']:
        print(f"First Seen (UTC): {tag_info['first_seen_utc']} μs")
    if tag_info['first_seen_uptime']:
        print(f"First Seen (Uptime): {tag_info['first_seen_uptime']} μs")
    if tag_info['last_seen_utc']:
        print(f"Last Seen (UTC): {tag_info['last_seen_utc']} μs")
    if tag_info['last_seen_uptime']:
        print(f"Last Seen (Uptime): {tag_info['last_seen_uptime']} μs")


def simple_tag_callback(tag_info):
    """Simple callback showing basic information"""
    epc = tag_info['epc'] or 'Unknown'
    antenna = tag_info['antenna_id'] or '?'
    rssi = tag_info['rssi'] or '?'
    count = tag_info['seen_count'] or '?'
    
    print(f"📡 Tag: {epc[:16]}... | Antenna: {antenna} | "
          f"RSSI: {rssi}dBm | Count: {count}")


def main():
    print("🚀 Testing Improved LLRP Tag Report Parsing")
    print("=" * 60)
    
    # Reader configuration - UPDATE THIS IP!
    READER_IP = "192.168.1.100"  # Change to your reader's IP
    
    # Create client
    reader = LLRPClient(READER_IP)
    
    try:
        print(f"📡 Connecting to reader at {READER_IP}...")
        
        if not reader.connect():
            print("❌ Connection failed!")
            print("\n💡 Tips:")
            print("   - Check if reader IP is correct")
            print("   - Ensure reader is powered on and connected")
            print("   - Verify network connectivity")
            return
        
        print("✅ Connected successfully!")
        
        # Get capabilities to verify connection
        print("\n📋 Getting reader capabilities...")
        caps = reader.get_capabilities()
        if caps:
            print("✅ Reader capabilities retrieved")
        else:
            print("⚠️  Could not get capabilities, but continuing...")
        
        print("\n" + "=" * 60)
        print("🔍 SIMPLE TAG READING TEST (5 seconds)")
        print("=" * 60)
        
        # Test 1: Simple reading with basic callback
        print("Starting simple inventory...")
        tags = reader.simple_inventory(
            duration_seconds=5.0,
            antenna_ids=None,
            tag_callback=simple_tag_callback
        )
        
        print(f"\n📊 Results: {len(tags)} total tag reads")
        
        if tags:
            # Show unique EPCs
            unique_epcs = set(tag['epc'] for tag in tags if tag['epc'])
            print(f"🏷️  Unique EPCs: {len(unique_epcs)}")
            
            # Show parsing success rate
            parsed_epcs = sum(1 for tag in tags if tag['epc'])
            success_rate = (parsed_epcs / len(tags)) * 100 if tags else 0
            print(f"✅ EPC Parsing Success: {success_rate:.1f}%")
            
            # Show field availability
            fields_available = {
                'antenna_id': sum(1 for tag in tags if tag['antenna_id'] is not None),
                'rssi': sum(1 for tag in tags if tag['rssi'] is not None),
                'seen_count': sum(1 for tag in tags if tag['seen_count'] is not None),
                'timestamps': sum(1 for tag in tags if tag['first_seen'] is not None),
            }
            
            print(f"📈 Field Availability:")
            for field, count in fields_available.items():
                percentage = (count / len(tags)) * 100 if tags else 0
                print(f"   {field}: {count}/{len(tags)} ({percentage:.1f}%)")
        
        print("\n" + "=" * 60)
        print("🔬 DETAILED TAG READING TEST (5 seconds)")
        print("=" * 60)
        
        # Test 2: Detailed reading with full callback
        print("Starting detailed inventory with full parsing info...")
        reader.tags_read.clear()  # Clear previous results
        
        tags = reader.simple_inventory(
            duration_seconds=5.0,
            antenna_ids=None,
            tag_callback=detailed_tag_callback
        )
        
        print(f"\n📊 Detailed Results: {len(tags)} total tag reads")
        
        # Analysis of parsing quality
        if tags:
            print(f"\n🔍 PARSING ANALYSIS:")
            
            # Group by EPC
            epc_groups = {}
            for tag in tags:
                epc = tag['epc'] or 'Unknown'
                if epc not in epc_groups:
                    epc_groups[epc] = []
                epc_groups[epc].append(tag)
            
            print(f"📋 Tag Summary:")
            for epc, tag_list in epc_groups.items():
                epc_display = epc[:24] + "..." if len(epc) > 24 else epc
                print(f"   {epc_display}: {len(tag_list)} reads")
                
                # Show field completeness for this EPC
                sample = tag_list[0]
                completeness = []
                if sample['antenna_id'] is not None: completeness.append("Antenna")
                if sample['rssi'] is not None: completeness.append("RSSI") 
                if sample['seen_count'] is not None: completeness.append("Count")
                if sample['first_seen'] is not None: completeness.append("Timestamps")
                if sample['rospec_id'] is not None: completeness.append("ROSpec")
                
                print(f"      Fields: {', '.join(completeness) if completeness else 'EPC only'}")
        
        print("\n✅ Tag report parsing test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print("\n🔧 Debug traceback:")
        traceback.print_exc()
    
    finally:
        print("\n🔌 Disconnecting...")
        reader.disconnect()
        print("👋 Test completed!")


if __name__ == "__main__":
    main()