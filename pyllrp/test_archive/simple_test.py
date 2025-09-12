#!/usr/bin/env python3
"""
Simple LLRP test without full client library
Direct implementation for Bluebird FR900 testing
"""

import socket
import struct
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleLLRPClient:
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1
        
    def connect(self):
        """Connect to LLRP reader"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            
            # Read Reader Event Notification
            data = self.socket.recv(1024)
            if data:
                logger.info(f"Received initial message: {len(data)} bytes")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, msg_type, msg_data=b''):
        """Send LLRP message"""
        msg_id = self.message_id
        self.message_id += 1
        
        # LLRP header: type(2) + length(4) + id(4)
        length = 10 + len(msg_data)
        header = struct.pack('!HII', msg_type, length, msg_id)
        
        message = header + msg_data
        self.socket.send(message)
        logger.info(f"Sent message type=0x{msg_type:04X}, len={length}, id={msg_id}")
        return msg_id
    
    def recv_message(self):
        """Receive LLRP message"""
        # Read header
        header = self.socket.recv(10)
        if len(header) < 10:
            return None
            
        msg_type, msg_len, msg_id = struct.unpack('!HHI', header[:10])
        
        # Read rest of message
        remaining = msg_len - 10
        if remaining > 0:
            data = self.socket.recv(remaining)
        else:
            data = b''
            
        logger.info(f"Received message type=0x{msg_type:04X}, len={msg_len}, id={msg_id}")
        return msg_type, msg_id, data
    
    def get_capabilities(self):
        """Send GET_READER_CAPABILITIES"""
        # Message type 0x0001 = GET_READER_CAPABILITIES
        # RequestedData: 0 = All
        data = struct.pack('!B', 0)
        self.send_message(0x0001, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x000B:  # GET_READER_CAPABILITIES_RESPONSE
            logger.info("Received capabilities response")
            return True
        return False
    
    def delete_all_rospecs(self):
        """Delete all ROSpecs"""
        # Message type 0x0015 = DELETE_ROSPEC
        # ROSpecID: 0 = All
        data = struct.pack('!I', 0)
        self.send_message(0x0015, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x001F:  # DELETE_ROSPEC_RESPONSE
            logger.info("Deleted all ROSpecs")
            return True
        return False
    
    def add_basic_rospec(self):
        """Add a basic ROSpec for inventory"""
        # Simplified ROSpec - just the required fields
        # This is a minimal ROSpec structure
        rospec_id = 1
        priority = 0
        current_state = 0  # Disabled
        
        # Build ROSpec message (simplified)
        rospec_data = struct.pack('!IBB', rospec_id, priority, current_state)
        
        # Add minimal ROBoundarySpec
        # Start trigger: Null (0)
        # Stop trigger: Duration (1) with 5000ms
        boundary_data = struct.pack('!BBHI', 0, 1, 0, 5000)
        
        # Combine all data
        data = rospec_data + boundary_data
        
        # Message type 0x0014 = ADD_ROSPEC
        self.send_message(0x0014, data[:20])  # Send truncated for simplicity
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x001E:  # ADD_ROSPEC_RESPONSE
            logger.info("Added ROSpec")
            return True
        return False
    
    def enable_rospec(self):
        """Enable ROSpec ID 1"""
        # Message type 0x0018 = ENABLE_ROSPEC
        data = struct.pack('!I', 1)  # ROSpec ID = 1
        self.send_message(0x0018, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0022:  # ENABLE_ROSPEC_RESPONSE
            logger.info("Enabled ROSpec")
            return True
        return False
    
    def start_rospec(self):
        """Start ROSpec ID 1"""
        # Message type 0x0016 = START_ROSPEC  
        data = struct.pack('!I', 1)  # ROSpec ID = 1
        self.send_message(0x0016, data)
        
        # Receive response
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0020:  # START_ROSPEC_RESPONSE
            logger.info("Started ROSpec")
            return True
        return False
    
    def stop_rospec(self):
        """Stop ROSpec ID 1"""
        # Message type 0x0017 = STOP_ROSPEC
        data = struct.pack('!I', 1)  # ROSpec ID = 1
        self.send_message(0x0017, data)
        
        # Receive response  
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0021:  # STOP_ROSPEC_RESPONSE
            logger.info("Stopped ROSpec")
            return True
        return False
    
    def read_tags(self, duration=5):
        """Read tags for specified duration"""
        logger.info(f"Reading tags for {duration} seconds...")
        
        end_time = time.time() + duration
        tag_count = 0
        
        self.socket.settimeout(0.5)
        
        while time.time() < end_time:
            try:
                msg_type, msg_id, data = self.recv_message()
                
                # RO_ACCESS_REPORT = 0x003D
                if msg_type == 0x003D:
                    tag_count += 1
                    logger.info(f"Tag report #{tag_count}")
                    
                # READER_EVENT_NOTIFICATION = 0x003F
                elif msg_type == 0x003F:
                    logger.info("Reader event notification")
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error reading: {e}")
                break
        
        return tag_count
    
    def disconnect(self):
        """Disconnect from reader"""
        if self.socket:
            # Send CLOSE_CONNECTION
            # Message type 0x000E = CLOSE_CONNECTION
            self.send_message(0x000E, b'')
            
            try:
                # Try to receive response
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x0010:  # CLOSE_CONNECTION_RESPONSE
                    logger.info("Connection closed properly")
            except:
                pass
            
            self.socket.close()
            logger.info("Disconnected")

def main():
    # FR900 configuration
    READER_IP = "192.168.10.106"
    
    print("="*60)
    print("Simple LLRP Test for Bluebird FR900")
    print("="*60)
    
    client = SimpleLLRPClient(READER_IP)
    
    try:
        # Connect
        if not client.connect():
            print("Failed to connect")
            return
        
        # Get capabilities
        client.get_capabilities()
        
        # Clear ROSpecs
        client.delete_all_rospecs()
        
        # Add and enable ROSpec
        client.add_basic_rospec()
        client.enable_rospec()
        
        # Start inventory
        client.start_rospec()
        
        # Read tags
        tag_count = client.read_tags(duration=5)
        print(f"\nTotal tag reports received: {tag_count}")
        
        # Stop inventory
        client.stop_rospec()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.disconnect()
        print("\nTest completed!")

if __name__ == "__main__":
    main()