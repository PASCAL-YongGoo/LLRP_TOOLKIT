#!/usr/bin/env python3
"""
FR900 Minimal Test - Only standard LLRP parameters
Testing if extended config is actually required
"""

import socket
import struct
import time
import logging
import binascii

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FR900MinimalClient:
    """Test with minimal LLRP configuration"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 0x2700
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"✓ Connected to {self.host}:{self.port}")
            
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x3F:
                logger.info("✓ Received Reader Event Notification")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, msg_type, msg_data=b''):
        msg_id = self.message_id
        self.message_id += 1
        
        type_field = 0x0400 | msg_type
        length = 10 + len(msg_data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + msg_data
        
        logger.debug(f"TX: Type=0x{type_field:04X}, Len={length}, ID={msg_id}")
        self.socket.send(message)
        return msg_id
    
    def recv_message(self):
        try:
            header = self.socket.recv(10)
            if len(header) < 10:
                return None, None, None
            
            type_field, msg_len, msg_id = struct.unpack('!HII', header)
            msg_type = type_field & 0xFF
            
            remaining = msg_len - 10
            data = b''
            while len(data) < remaining:
                chunk = self.socket.recv(remaining - len(data))
                if not chunk:
                    break
                data += chunk
            
            logger.debug(f"RX: Type=0x{type_field:04X}, Len={msg_len}, ID={msg_id}")
            return msg_type, msg_id, data
            
        except Exception as e:
            return None, None, None
    
    def test_minimal_rospec(self):
        """Test with absolutely minimal ROSpec"""
        
        # 1. Basic SET_READER_CONFIG (works)
        logger.info("Step 1: Basic reader config")
        data = struct.pack('!B', 0x80)
        self.send_message(0x03, data)
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x0D:
            logger.error("Basic config failed")
            return False
        
        # 2. DELETE_ROSPEC
        logger.info("Step 2: Delete ROSpecs")
        data = struct.pack('!I', 0)
        self.send_message(0x15, data)
        msg_type, msg_id, data = self.recv_message()
        if msg_type != 0x1F:
            logger.error("Delete ROSpec failed")
            return False
        
        # 3. Minimal ADD_ROSPEC (just structure, no extended params)
        logger.info("Step 3: Add minimal ROSpec")
        
        rospec_data = bytearray()
        
        # ROSpec header
        rospec_data.extend(struct.pack('!HHI', 0x00B1, 0, 123))  # Type, Length(will fix), ID=123
        rospec_data.extend(struct.pack('!BB', 0, 0))  # Priority=0, State=0
        
        # ROBoundarySpec
        boundary_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B2, 0))  # Type, Length(will fix)
        
        # ROSpecStartTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B3, 5, 0))  # Type, Len=5, Null trigger
        
        # ROSpecStopTrigger - Null  
        rospec_data.extend(struct.pack('!HHB', 0x00B6, 5, 0))  # Type, Len=5, Null trigger
        
        # Fix ROBoundarySpec length
        boundary_len = len(rospec_data) - boundary_start
        struct.pack_into('!H', rospec_data, boundary_start + 2, boundary_len)
        
        # AISpec (minimal)
        aispec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B7, 0))  # Type, Length(will fix)
        rospec_data.extend(struct.pack('!H', 1))  # Antenna count = 1
        rospec_data.extend(struct.pack('!H', 0))  # Antenna ID = 0 (all)
        
        # AISpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B8, 5, 0))  # Type, Len=5, Null trigger
        
        # InventoryParameterSpec (minimal)
        rospec_data.extend(struct.pack('!HHH', 0x00BA, 8, 123))  # Type, Len=8, SpecID=123
        rospec_data.extend(struct.pack('!B', 1))  # Protocol = EPC C1G2
        
        # Fix AISpec length
        aispec_len = len(rospec_data) - aispec_start
        struct.pack_into('!H', rospec_data, aispec_start + 2, aispec_len)
        
        # Fix ROSpec length
        struct.pack_into('!H', rospec_data, 2, len(rospec_data))
        
        logger.info(f"Sending minimal ROSpec: {len(rospec_data)} bytes")
        self.send_message(0x14, bytes(rospec_data))
        
        msg_type, msg_id, resp_data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Minimal ROSpec accepted!")
            
            # 4. Enable ROSpec
            logger.info("Step 4: Enable ROSpec")
            data = struct.pack('!I', 123)
            self.send_message(0x18, data)
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x22:
                logger.info("✓ ROSpec enabled!")
                
                # 5. Start ROSpec
                logger.info("Step 5: Start ROSpec")
                data = struct.pack('!I', 123)
                self.send_message(0x16, data)
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x20:
                    logger.info("✓ ROSpec started - Reading for 3 seconds...")
                    
                    # Read for a short time
                    self.socket.settimeout(0.5)
                    tag_count = 0
                    start_time = time.time()
                    
                    while time.time() - start_time < 3:
                        msg_type, msg_id, data = self.recv_message()
                        if msg_type == 0x3D:  # RO_ACCESS_REPORT
                            tag_count += 1
                            logger.info(f"  Tag report #{tag_count}")
                        elif msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                            logger.debug("  Reader event")
                    
                    # Stop ROSpec
                    logger.info("Step 6: Stop ROSpec")
                    self.socket.settimeout(10.0)
                    data = struct.pack('!I', 123)
                    self.send_message(0x17, data)
                    msg_type, msg_id, data = self.recv_message()
                    if msg_type == 0x21:
                        logger.info("✓ ROSpec stopped")
                    
                    logger.info(f"Result: {tag_count} tag reports received")
                    return tag_count > 0
        
        logger.error(f"ROSpec failed with response type: 0x{msg_type:02X}")
        return False
    
    def disconnect(self):
        if self.socket:
            try:
                self.send_message(0x0E, b'')
                self.recv_message()
            except:
                pass
            self.socket.close()

def main():
    READER_IP = "192.168.10.106"
    
    print("\n" + "="*60)
    print(" FR900 Minimal Test - Standard LLRP Only")
    print(" Testing if extended config is actually required")
    print("="*60 + "\n")
    
    client = FR900MinimalClient(READER_IP)
    
    try:
        if not client.connect():
            print("Failed to connect")
            return
        
        # Test with minimal configuration
        success = client.test_minimal_rospec()
        
        if success:
            print("\n✅ SUCCESS: FR900 works with minimal LLRP configuration!")
            print("   Extended parameters are NOT required by the reader itself.")
            print("   They are likely client software optimization.")
        else:
            print("\n❌ FAILED: FR900 requires extended configuration")
            print("   The reader enforces additional parameters beyond LLRP standard.")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.disconnect()
        print("\n" + "="*60)
        print(" Test completed")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()