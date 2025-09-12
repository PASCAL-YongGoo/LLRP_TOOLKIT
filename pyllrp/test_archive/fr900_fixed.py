#!/usr/bin/env python3
"""
Bluebird FR900 LLRP Test - Fixed ROSpec Implementation
Based on actual hex dump analysis
"""

import socket
import struct
import time
import logging
import binascii

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FR900FixedClient:
    """Bluebird FR900 LLRP Client with correct ROSpec structure"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 0x2700
        
    def connect(self):
        """Connect to FR900 reader"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"✓ Connected to {self.host}:{self.port}")
            
            # Read initial Reader Event Notification
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x3F:
                logger.info("✓ Received Reader Event Notification")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, msg_type, msg_data=b''):
        """Send LLRP message in FR900 format"""
        msg_id = self.message_id
        self.message_id += 1
        
        # FR900 format
        if msg_type == 0x3FF:  # Custom message
            type_field = 0x07FF
        else:
            type_field = 0x0400 | msg_type
            
        length = 10 + len(msg_data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + msg_data
        
        logger.debug(f"TX: Type=0x{type_field:04X}, Len={length}, ID={msg_id}")
        if len(msg_data) <= 50:
            logger.debug(f"    Data: {binascii.hexlify(message).decode()}")
        
        self.socket.send(message)
        return msg_id
    
    def recv_message(self):
        """Receive LLRP message"""
        try:
            header = self.socket.recv(10)
            if len(header) < 10:
                return None, None, None
            
            type_field, msg_len, msg_id = struct.unpack('!HII', header)
            msg_type = type_field & 0xFF if type_field & 0xFF00 == 0x0400 else type_field
            
            remaining = msg_len - 10
            data = b''
            while len(data) < remaining:
                chunk = self.socket.recv(remaining - len(data))
                if not chunk:
                    break
                data += chunk
            
            logger.debug(f"RX: Type=0x{type_field:04X} (0x{msg_type:02X}), Len={msg_len}, ID={msg_id}")
            return msg_type, msg_id, data
            
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None, None, None
    
    def get_capabilities(self):
        """GET_READER_CAPABILITIES"""
        data = struct.pack('!B', 0)  # Request all capabilities
        self.send_message(0x01, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0B:
            logger.info("✓ Capabilities received")
            return True
        return False
    
    def set_reader_config_basic(self):
        """Basic SET_READER_CONFIG"""
        data = struct.pack('!B', 0x80)  # Reset to factory: No
        self.send_message(0x03, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0D:
            logger.info("✓ Reader config set")
            return True
        return False
    
    def delete_all_rospecs(self):
        """DELETE_ROSPEC (all)"""
        data = struct.pack('!I', 0)  # ROSpec ID = 0 (all)
        self.send_message(0x15, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1F:
            logger.info("✓ All ROSpecs deleted")
            return True
        return False
    
    def delete_all_accessspecs(self):
        """DELETE_ACCESSSPEC (all)"""
        data = struct.pack('!I', 0)  # AccessSpec ID = 0 (all)
        self.send_message(0x29, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x33:
            logger.info("✓ All AccessSpecs deleted")
            return True
        return False
    
    def set_reader_config_extended(self):
        """Extended SET_READER_CONFIG from hex dump"""
        # Based on hex dump line 238-245
        data = bytes.fromhex(
            '0000f40020' +      # ReaderEventNotificationSpec
            'f5000700088000' +  # AntennaConfiguration[1]
            'f5000700018000' +  # AntennaConfiguration[2]
            'f5000700038000' +  # AntennaConfiguration[3]
            'f5000700028000' +  # AntennaConfiguration[4]
            'ed001202' +        # ROReportSpec
            '0001' +            # Trigger
            '00ee000b1400015c000540' + # TagReportContentSelector
            '00ef000501' +      # AccessReportSpec
            '00dc00090100002710' +     # KeepaliveSpec
            '00e1000800010000' +       # GPIPortCurrentState[1]
            '00e1000800020000' +       # GPIPortCurrentState[2]
            '00e1000800030000' +       # GPIPortCurrentState[3]
            '00e1000800040000' +       # GPIPortCurrentState[4]
            '00e2000500'               # GPOWriteData
        )
        
        self.send_message(0x03, data)
        
        msg_type, msg_id, resp_data = self.recv_message()
        if msg_type == 0x0D:
            logger.info("✓ Extended reader config set")
            return True
        return False
    
    def add_rospec_simple(self):
        """Add simple ROSpec based on hex dump (2nd version)"""
        # ROSpec structure from hex dump line 251-258
        rospec_data = bytes.fromhex(
            '00b100620000' +    # ROSpec: Type=177, Len=98, ID=1234
            '04d20000' +        # ROSpec ID = 0x04D2 (1234), Priority=0, State=0
            '00b20012' +        # ROBoundarySpec: Type=178, Len=18
            '00b3000500' +      # ROSpecStartTrigger: Type=179, Len=5, Null
            '00b60009000000000000' +  # ROSpecStopTrigger: Type=182, Len=9, Null
            '00b70046' +        # AISpec: Type=183, Len=70
            '000100010' +       # Antenna IDs: Count=1, ID=1
            '00b80009000000000000' +  # AISpecStopTrigger: Type=184, Len=9, Null
            '00ba003504d201' +  # InventoryParameterSpec: Type=186, Len=53, ID=1234, Protocol=1
            '00de002e0001' +    # AntennaConfiguration: Type=222, Len=46, ID=1
            '00df000600010' +   # RFTransmitter: Type=223, Len=6, Power=1
            '00e0000a000100010078' + # RFReceiver: Type=224, Len=10
            '014a001800014f0008000300000150000b00001e0000000000' # C1G2InventoryCommand
        )
        
        self.send_message(0x14, rospec_data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Simple ROSpec added successfully")
            return True
        return False
    
    def enable_rospec(self, rospec_id=0x04D2):
        """ENABLE_ROSPEC"""
        data = struct.pack('!I', rospec_id)
        self.send_message(0x18, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x22:
            logger.info(f"✓ ROSpec {rospec_id} enabled")
            return True
        return False
    
    def send_custom_messages(self):
        """Send Bluebird custom message pair"""
        # First pair (0x270D)
        data = b'\x00\x00\x00\x00\x00'
        msg_id = 0x270D
        
        # Custom message header
        header = struct.pack('!HII', 0x07FF, 15, msg_id)
        message = header + data
        self.socket.send(message)
        logger.debug("Sent custom message 1")
        
        # Receive response
        resp = self.recv_message()
        
        # Second pair (0x270B)
        msg_id = 0x270B
        header = struct.pack('!HII', 0x07FF, 15, msg_id)
        message = header + data
        self.socket.send(message)
        logger.debug("Sent custom message 2")
        
        # Receive response
        resp = self.recv_message()
        
        logger.info("✓ Custom messages exchanged")
        return True
    
    def start_rospec(self, rospec_id=0x04D2):
        """START_ROSPEC"""
        data = struct.pack('!I', rospec_id)
        self.send_message(0x16, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x20:
            logger.info(f"✓ ROSpec {rospec_id} started - Inventory running")
            return True
        return False
    
    def stop_rospec(self, rospec_id=0x04D2):
        """STOP_ROSPEC"""
        data = struct.pack('!I', rospec_id)
        self.send_message(0x17, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x21:
            logger.info(f"✓ ROSpec {rospec_id} stopped")
            return True
        return False
    
    def read_tags(self, duration=5):
        """Read tags and parse EPC data"""
        logger.info(f"Reading tags for {duration} seconds...")
        
        end_time = time.time() + duration
        tag_count = 0
        unique_epcs = set()
        
        self.socket.settimeout(0.5)
        
        while time.time() < end_time:
            msg_type, msg_id, data = self.recv_message()
            
            if msg_type is None:
                continue
            
            if msg_type == 0x3D:  # RO_ACCESS_REPORT
                tag_count += 1
                
                # Simple EPC extraction
                if len(data) > 20:
                    # Look for EPC-96 data pattern
                    for i in range(len(data) - 12):
                        if data[i:i+2] == b'\x00\xf1':  # EPC-96 parameter type
                            try:
                                epc_len = struct.unpack('!H', data[i+2:i+4])[0] - 4
                                if 8 <= epc_len <= 16:
                                    epc = data[i+4:i+4+epc_len]
                                    epc_hex = binascii.hexlify(epc).decode().upper()
                                    unique_epcs.add(epc_hex)
                                    logger.info(f"  Tag #{tag_count}: EPC={epc_hex}")
                                    break
                            except:
                                pass
                    else:
                        logger.debug(f"  Tag report #{tag_count} (no EPC extracted)")
                
            elif msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                logger.debug("  Reader event")
        
        return tag_count, len(unique_epcs)
    
    def disconnect(self):
        """Graceful disconnect"""
        if self.socket:
            try:
                self.send_message(0x0E, b'')  # CLOSE_CONNECTION
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x10:
                    logger.info("✓ Connection closed properly")
            except:
                pass
            
            self.socket.close()
            logger.info("✓ Disconnected")


def main():
    READER_IP = "192.168.10.106"
    
    print("\n" + "="*60)
    print(" Bluebird FR900 LLRP Test - Fixed Implementation")
    print(" Based on actual hex dump analysis")
    print("="*60 + "\n")
    
    client = FR900FixedClient(READER_IP)
    
    try:
        # Phase 1: Connect
        if not client.connect():
            print("Failed to connect")
            return
        
        # Phase 2: Get capabilities
        client.get_capabilities()
        
        # Phase 3: Basic configuration
        client.set_reader_config_basic()
        client.delete_all_rospecs()
        client.delete_all_accessspecs()
        
        # Phase 4: Extended configuration
        client.set_reader_config_extended()
        
        # Phase 5: Add ROSpec
        client.add_rospec_simple()
        client.enable_rospec()
        
        # Phase 6: Custom messages
        client.send_custom_messages()
        
        # Phase 7: Start inventory
        client.enable_rospec()  # Re-enable
        client.start_rospec()
        
        # Phase 8: Read tags
        print("\n" + "-"*50)
        print(" INVENTORY ACTIVE - Reading tags...")
        print("-"*50)
        
        tag_count, unique_count = client.read_tags(duration=8)
        
        print("-"*50)
        print(f"\nResults:")
        print(f"  Total tag reports: {tag_count}")
        print(f"  Unique EPCs found: {unique_count}")
        
        if tag_count > 0:
            read_rate = tag_count / 8.0
            print(f"  Read rate: {read_rate:.1f} tags/second")
            print(f"\n✅ Inventory successful!")
        else:
            print("\n⚠ No tags detected")
        
        # Phase 9: Stop and cleanup
        client.stop_rospec()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
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