#!/usr/bin/env python3
"""
Bluebird FR900 LLRP Test
Based on actual packet capture analysis
"""

import socket
import struct
import time
import logging
import binascii

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FR900Client:
    """Bluebird FR900 LLRP Client"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1
        
    def connect(self):
        """Connect to FR900 reader"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"✓ Connected to {self.host}:{self.port}")
            
            # Read initial Reader Event Notification
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                logger.info("✓ Received Reader Event Notification")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, msg_type, msg_data=b''):
        """Send LLRP message in FR900 format"""
        msg_id = self.message_id
        self.message_id += 1
        
        # FR900 uses 0x04 prefix for message type
        type_field = 0x0400 | msg_type
        length = 10 + len(msg_data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + msg_data
        
        logger.debug(f"TX: Type=0x{type_field:04X}, Len={length}, ID={msg_id}")
        logger.debug(f"    Hex: {binascii.hexlify(message).decode()}")
        
        self.socket.send(message)
        return msg_id
    
    def recv_message(self):
        """Receive LLRP message in FR900 format"""
        try:
            # Read 10-byte header
            header = self.socket.recv(10)
            if len(header) < 10:
                logger.error(f"Short header: {len(header)} bytes")
                return None, None, None
            
            # Parse header
            type_field, msg_len, msg_id = struct.unpack('!HII', header)
            
            # Extract actual message type (lower byte)
            msg_type = type_field & 0xFF
            
            # Read message body
            remaining = msg_len - 10
            if remaining > 0:
                data = b''
                while len(data) < remaining:
                    chunk = self.socket.recv(remaining - len(data))
                    if not chunk:
                        break
                    data += chunk
            else:
                data = b''
            
            logger.debug(f"RX: Type=0x{type_field:04X} (0x{msg_type:02X}), Len={msg_len}, ID={msg_id}")
            if data and len(data) <= 100:
                logger.debug(f"    Data: {binascii.hexlify(data).decode()}")
            
            return msg_type, msg_id, data
            
        except socket.timeout:
            return None, None, None
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None, None, None
    
    def get_capabilities(self):
        """Send GET_READER_CAPABILITIES"""
        logger.info("Getting reader capabilities...")
        
        # RequestedData: 0 = All capabilities
        data = struct.pack('!B', 0)
        self.send_message(0x01, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0B:  # GET_READER_CAPABILITIES_RESPONSE
            logger.info("✓ Received capabilities response")
            
            # Parse basic info from response
            if len(data) > 50:
                # Look for model name (around offset 0x2A)
                try:
                    model_start = data.find(b'FR900')
                    if model_start > 0:
                        model_end = data.find(b'\x00', model_start)
                        model = data[model_start:model_end].decode()
                        logger.info(f"  Model: {model}")
                except:
                    pass
            return True
        return False
    
    def send_custom_message(self):
        """Send Bluebird custom message"""
        logger.info("Sending custom message...")
        
        # Bluebird custom message format
        data = b'\x00\x00\x00\x00\x00'
        msg_id = 0x270D  # From log
        
        # Custom message type is 0x3FF (1023)
        type_field = 0x07FF
        length = 10 + len(data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + data
        
        logger.debug(f"TX Custom: {binascii.hexlify(message).decode()}")
        self.socket.send(message)
        
        # Receive response
        header = self.socket.recv(10)
        if len(header) == 10:
            type_field, msg_len, resp_id = struct.unpack('!HII', header)
            
            remaining = msg_len - 10
            if remaining > 0:
                data = self.socket.recv(remaining)
                logger.debug(f"RX Custom: {binascii.hexlify(header + data).decode()}")
                
                # Parse vendor ID
                if len(data) >= 4:
                    vendor_id = struct.unpack('!I', data[:4])[0]
                    if vendor_id == 0x5E95:
                        logger.info("✓ Received Bluebird custom response")
                        return True
        return False
    
    def set_reader_config(self):
        """Send SET_READER_CONFIG"""
        logger.info("Setting reader configuration...")
        
        # ResetToFactoryDefault: No (0x80 from log)
        data = struct.pack('!B', 0x80)
        self.send_message(0x03, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0D:  # SET_READER_CONFIG_RESPONSE
            logger.info("✓ Reader configuration set")
            return True
        return False
    
    def delete_all_rospecs(self):
        """Delete all ROSpecs"""
        logger.info("Deleting all ROSpecs...")
        
        # ROSpecID: 0 = Delete all
        data = struct.pack('!I', 0)
        self.send_message(0x15, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1F:  # DELETE_ROSPEC_RESPONSE
            logger.info("✓ All ROSpecs deleted")
            return True
        return False
    
    def add_rospec(self):
        """Add ROSpec for inventory"""
        logger.info("Adding ROSpec...")
        
        # Simplified ROSpec - using captured structure
        # This is a minimal working ROSpec
        rospec_data = bytes.fromhex(
            '00b10132'  # ROSpec header (Type=177)
            '00000001'  # ROSpec ID = 1
            '00'        # Priority = 0
            '00'        # Current State = 0 (Disabled)
            '00b20014'  # ROBoundarySpec (Type=178, Len=20)
            '00b30005'  # ROSpecStartTrigger (Type=179, Len=5)
            '00'        # Trigger Type = 0 (Null)
            '00b40009'  # ROSpecStopTrigger (Type=180, Len=9)
            '01'        # Trigger Type = 1 (Duration)
            '00001388'  # Duration = 5000ms
            '00b70068'  # AISpec (Type=183, Len=104)
            '01 00'     # Antenna Count + ID
            '00b80005'  # AISpecStopTrigger (Type=184, Len=5)
            '00'        # Trigger Type = 0
            '00ba000c'  # InventoryParameterSpec (Type=186, Len=12)
            '0001'      # Spec ID = 1
            '01'        # Protocol = EPCGlobal Class 1 Gen 2
            '00ed0014'  # ROReportSpec (Type=237, Len=20)
            '02'        # Trigger = 2
            '0001'      # N = 1
            '00ee000d'  # TagReportContentSelector (Type=238, Len=13)
            'c000'      # Enable flags
        )
        
        # Use simplified data for now
        data = struct.pack('!HHI', 177, 10, 1) + struct.pack('!BB', 0, 0)
        self.send_message(0x14, data)
        
        msg_type, msg_id, resp_data = self.recv_message()
        if msg_type == 0x1E:  # ADD_ROSPEC_RESPONSE
            logger.info("✓ ROSpec added")
            return True
        return False
    
    def enable_rospec(self):
        """Enable ROSpec ID 1"""
        logger.info("Enabling ROSpec...")
        
        data = struct.pack('!I', 1)
        self.send_message(0x18, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x22:  # ENABLE_ROSPEC_RESPONSE
            logger.info("✓ ROSpec enabled")
            return True
        return False
    
    def start_rospec(self):
        """Start ROSpec ID 1"""
        logger.info("Starting inventory...")
        
        data = struct.pack('!I', 1)
        self.send_message(0x16, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x20:  # START_ROSPEC_RESPONSE
            logger.info("✓ Inventory started")
            return True
        return False
    
    def stop_rospec(self):
        """Stop ROSpec ID 1"""
        logger.info("Stopping inventory...")
        
        data = struct.pack('!I', 1)
        self.send_message(0x17, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x21:  # STOP_ROSPEC_RESPONSE
            logger.info("✓ Inventory stopped")
            return True
        return False
    
    def read_tags(self, duration=5):
        """Read tags for specified duration"""
        logger.info(f"Reading tags for {duration} seconds...")
        
        end_time = time.time() + duration
        tag_count = 0
        unique_epcs = set()
        
        self.socket.settimeout(0.5)
        
        while time.time() < end_time:
            msg_type, msg_id, data = self.recv_message()
            
            if msg_type is None:
                continue
            
            # RO_ACCESS_REPORT = 0x3D (61)
            if msg_type == 0x3D:
                tag_count += 1
                
                # Try to extract EPC from report
                if len(data) > 20:
                    # Simple EPC extraction (look for EPC-96 pattern)
                    epc_start = data.find(bytes.fromhex('00f1'))
                    if epc_start >= 0 and len(data) > epc_start + 14:
                        epc = data[epc_start+4:epc_start+16]
                        epc_hex = binascii.hexlify(epc).decode()
                        unique_epcs.add(epc_hex)
                        logger.info(f"  Tag #{tag_count}: EPC={epc_hex}")
                    else:
                        logger.debug(f"  Tag report #{tag_count}")
                
            # READER_EVENT_NOTIFICATION = 0x3F (63)
            elif msg_type == 0x3F:
                logger.debug("  Reader event")
        
        return tag_count, len(unique_epcs)
    
    def disconnect(self):
        """Disconnect from reader"""
        if self.socket:
            try:
                # Send CLOSE_CONNECTION
                self.send_message(0x0E, b'')
                
                # Try to receive response
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x10:  # CLOSE_CONNECTION_RESPONSE
                    logger.info("✓ Connection closed properly")
            except:
                pass
            
            self.socket.close()
            logger.info("✓ Disconnected")


def main():
    # FR900 configuration
    READER_IP = "192.168.10.106"
    
    print("\n" + "="*60)
    print(" Bluebird FR900 LLRP Test")
    print(" Based on actual packet capture")
    print("="*60 + "\n")
    
    client = FR900Client(READER_IP)
    
    try:
        # Phase 1: Connection
        if not client.connect():
            print("Failed to connect to reader")
            return
        
        # Phase 2: Get capabilities
        client.get_capabilities()
        
        # Phase 3: Custom messages (Bluebird specific)
        client.send_custom_message()
        time.sleep(0.1)
        client.send_custom_message()
        
        # Phase 4: Configure reader
        client.set_reader_config()
        client.delete_all_rospecs()
        
        # Phase 5: Setup and start inventory
        client.set_reader_config()
        client.add_rospec()
        client.enable_rospec()
        
        # Phase 6: Run inventory
        client.send_custom_message()
        client.send_custom_message()
        
        client.enable_rospec()
        client.start_rospec()
        
        # Read tags
        print("\n" + "-"*40)
        tag_count, unique_count = client.read_tags(duration=7)
        print("-"*40)
        
        print(f"\nResults:")
        print(f"  Total tag reports: {tag_count}")
        print(f"  Unique tags found: {unique_count}")
        
        if tag_count == 0:
            print("\n⚠ No tags detected. Please check:")
            print("  - Tags are present near the antenna")
            print("  - Reader antenna is connected")
            print("  - RF power is enabled")
        
        # Phase 7: Stop and cleanup
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