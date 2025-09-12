#!/usr/bin/env python3
"""
LLRP Standard Compliant Test for Bluebird FR900
Based on LLRP 1.1 specification
"""

import socket
import struct
import time
import logging
import binascii

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LLRPStandardClient:
    """LLRP 1.1 Standard Compliant Client"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1000
        
    def connect(self):
        """Connect to LLRP reader"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            
            # Read initial Reader Event Notification
            msg_type, msg_id, data = self.recv_message()
            if msg_type == 0x003F:  # READER_EVENT_NOTIFICATION
                logger.info("Received Reader Event Notification")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, msg_type, msg_data=b''):
        """Send LLRP message with correct header format"""
        msg_id = self.message_id
        self.message_id += 1
        
        # LLRP header per spec: 
        # - Message Type: 10 bits (stored in 16 bits with version)
        # - Message Length: 32 bits 
        # - Message ID: 32 bits
        # Total header: 10 bytes
        
        # Type field: 3 bit version (=1) + 10 bit type + 3 bit reserved
        type_field = (1 << 13) | (msg_type << 3)  # Version 1, Type, Reserved 0
        length = 10 + len(msg_data)
        
        header = struct.pack('!HII', type_field, length, msg_id)
        message = header + msg_data
        
        logger.debug(f"Sending: Type=0x{msg_type:04X}, Len={length}, ID={msg_id}")
        logger.debug(f"Header hex: {binascii.hexlify(header).decode()}")
        logger.debug(f"Data hex: {binascii.hexlify(msg_data).decode()}")
        
        self.socket.send(message)
        return msg_id
    
    def recv_message(self):
        """Receive LLRP message with correct header parsing"""
        try:
            # Read 10-byte header
            header = self.socket.recv(10)
            if len(header) < 10:
                logger.error(f"Short header: {len(header)} bytes")
                return None, None, None
            
            logger.debug(f"Received header: {binascii.hexlify(header).decode()}")
            
            # Parse header
            type_field, msg_len, msg_id = struct.unpack('!HII', header)
            
            # Extract message type (bits 5-14)
            msg_type = (type_field >> 3) & 0x3FF
            
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
            
            logger.info(f"Received: Type=0x{msg_type:04X}, Len={msg_len}, ID={msg_id}")
            if data:
                logger.debug(f"Data hex: {binascii.hexlify(data).decode()}")
            
            return msg_type, msg_id, data
            
        except socket.timeout:
            logger.warning("Receive timeout")
            return None, None, None
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None, None, None
    
    def get_capabilities(self):
        """Send GET_READER_CAPABILITIES per LLRP spec"""
        # Message type 1 = GET_READER_CAPABILITIES
        # RequestedData: 0 = All capabilities
        data = struct.pack('!B', 0)
        self.send_message(0x0001, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x000B:  # GET_READER_CAPABILITIES_RESPONSE
            logger.info("✓ Received capabilities response")
            return True
        else:
            logger.error(f"Unexpected response type: 0x{msg_type:04X}")
        return False
    
    def set_reader_config(self):
        """Send SET_READER_CONFIG"""
        # Message type 3 = SET_READER_CONFIG
        # Reset to factory: No (0)
        data = struct.pack('!B', 0)
        self.send_message(0x0003, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x000D:  # SET_READER_CONFIG_RESPONSE
            logger.info("✓ Set reader config successful")
            return True
        return False
    
    def delete_all_rospecs(self):
        """Delete all ROSpecs"""
        # Message type 21 = DELETE_ROSPEC
        # ROSpecID: 0 = Delete all
        data = struct.pack('!I', 0)
        self.send_message(0x0015, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x001F:  # DELETE_ROSPEC_RESPONSE
            logger.info("✓ Deleted all ROSpecs")
            return True
        return False
    
    def add_rospec(self):
        """Add a minimal ROSpec"""
        # Message type 20 = ADD_ROSPEC
        # Build minimal valid ROSpec
        rospec_data = bytearray()
        
        # ROSpec parameter header (Type=177, Length will be calculated)
        rospec_type = 177
        
        # ROSpec fields
        rospec_id = 123
        priority = 0
        current_state = 0  # Disabled
        
        rospec_body = struct.pack('!IBB', rospec_id, priority, current_state)
        
        # ROBoundarySpec (Type=178)
        boundary_type = 178
        
        # ROSpecStartTrigger (Type=179): Null trigger
        start_trigger = struct.pack('!HHB', 179, 5, 0)  # Type, Length=5, TriggerType=0
        
        # ROSpecStopTrigger (Type=180): Null trigger  
        stop_trigger = struct.pack('!HHB', 180, 5, 0)  # Type, Length=5, TriggerType=0
        
        boundary_body = start_trigger + stop_trigger
        boundary_header = struct.pack('!HH', boundary_type, 4 + len(boundary_body))
        boundary_spec = boundary_header + boundary_body
        
        # Complete ROSpec parameter
        rospec_content = rospec_body + boundary_spec
        rospec_header = struct.pack('!HH', rospec_type, 4 + len(rospec_content))
        rospec_param = rospec_header + rospec_content
        
        self.send_message(0x0014, rospec_param)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x001E:  # ADD_ROSPEC_RESPONSE
            logger.info("✓ Added ROSpec")
            return True
        return False
    
    def enable_rospec(self):
        """Enable ROSpec ID 123"""
        # Message type 24 = ENABLE_ROSPEC
        data = struct.pack('!I', 123)
        self.send_message(0x0018, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0022:  # ENABLE_ROSPEC_RESPONSE
            logger.info("✓ Enabled ROSpec")
            return True
        return False
    
    def start_rospec(self):
        """Start ROSpec ID 123"""
        # Message type 22 = START_ROSPEC
        data = struct.pack('!I', 123)
        self.send_message(0x0016, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0020:  # START_ROSPEC_RESPONSE
            logger.info("✓ Started ROSpec")
            return True
        return False
    
    def stop_rospec(self):
        """Stop ROSpec ID 123"""
        # Message type 23 = STOP_ROSPEC
        data = struct.pack('!I', 123)
        self.send_message(0x0017, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0021:  # STOP_ROSPEC_RESPONSE
            logger.info("✓ Stopped ROSpec")
            return True
        return False
    
    def send_custom_message(self):
        """Send Bluebird custom message"""
        # Message type 1023 = CUSTOM_MESSAGE
        # Bluebird format from log analysis
        vendor_id = 0x00005E95  # Bluebird vendor ID
        subtype = 0x00
        custom_data = b'\x00\x00\x00\x00\x00'
        
        data = struct.pack('!IB', vendor_id, subtype) + custom_data
        self.send_message(0x03FF, data)
        
        msg_type, msg_id, response = self.recv_message()
        if msg_type == 0x03FF:  # CUSTOM_MESSAGE response
            logger.info("✓ Received custom message response")
            if len(response) >= 4:
                resp_vendor = struct.unpack('!I', response[:4])[0]
                logger.info(f"  Vendor ID: 0x{resp_vendor:08X}")
            return True
        return False
    
    def read_tags(self, duration=5):
        """Read tags for specified duration"""
        logger.info(f"Reading tags for {duration} seconds...")
        
        end_time = time.time() + duration
        tag_count = 0
        event_count = 0
        
        self.socket.settimeout(0.5)
        
        while time.time() < end_time:
            msg_type, msg_id, data = self.recv_message()
            
            if msg_type is None:
                continue
            
            # RO_ACCESS_REPORT = 61
            if msg_type == 0x003D:
                tag_count += 1
                logger.debug(f"Tag report #{tag_count}")
                
            # READER_EVENT_NOTIFICATION = 63
            elif msg_type == 0x003F:
                event_count += 1
                logger.debug(f"Reader event #{event_count}")
        
        return tag_count, event_count
    
    def disconnect(self):
        """Disconnect from reader"""
        if self.socket:
            try:
                # Send CLOSE_CONNECTION (type 14)
                self.send_message(0x000E, b'')
                
                # Try to receive response
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x0010:  # CLOSE_CONNECTION_RESPONSE
                    logger.info("✓ Connection closed properly")
            except:
                pass
            
            self.socket.close()
            logger.info("Disconnected")


def main():
    # FR900 configuration
    READER_IP = "192.168.10.106"
    
    print("="*60)
    print("LLRP 1.1 Standard Test for Bluebird FR900")
    print("="*60)
    
    client = LLRPStandardClient(READER_IP)
    
    try:
        # Phase 1: Connection and Setup
        print("\n[Phase 1: Connection and Setup]")
        if not client.connect():
            print("Failed to connect")
            return
        
        # Get capabilities
        client.get_capabilities()
        
        # Send custom messages (Bluebird specific)
        print("\n[Phase 2: Bluebird Custom Messages]")
        client.send_custom_message()
        time.sleep(0.1)
        client.send_custom_message()
        
        # Configure reader
        print("\n[Phase 3: Reader Configuration]")
        client.set_reader_config()
        client.delete_all_rospecs()
        
        # Setup ROSpec
        print("\n[Phase 4: ROSpec Setup]")
        client.add_rospec()
        client.enable_rospec()
        
        # Start inventory
        print("\n[Phase 5: Tag Inventory]")
        client.start_rospec()
        
        # Read tags
        tag_count, event_count = client.read_tags(duration=5)
        print(f"\nResults:")
        print(f"  Tag reports: {tag_count}")
        print(f"  Reader events: {event_count}")
        
        # Stop inventory
        print("\n[Phase 6: Cleanup]")
        client.stop_rospec()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.disconnect()
        print("\n" + "="*60)
        print("Test completed!")

if __name__ == "__main__":
    main()