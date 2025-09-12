#!/usr/bin/env python3
"""
FR900 Standard LLRP Test
Testing with only absolutely required parameters
"""

import socket
import struct
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FR900StandardTest:
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1000
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            
            # Read initial event
            msg_type, msg_id, data = self.recv_message()
            logger.info(f"Initial message: Type=0x{msg_type:02X}")
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
        
        self.socket.send(message)
        logger.debug(f"Sent: Type=0x{msg_type:02X}, ID={msg_id}")
        return msg_id
    
    def recv_message(self):
        try:
            header = self.socket.recv(10)
            if len(header) < 10:
                logger.error("Short header received")
                return None, None, None
            
            type_field, msg_len, msg_id = struct.unpack('!HII', header)
            msg_type = type_field & 0xFF
            
            remaining = msg_len - 10
            data = b''
            if remaining > 0:
                data = self.socket.recv(remaining)
            
            return msg_type, msg_id, data
            
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None, None, None
    
    def test_sequence(self):
        """Test standard LLRP sequence step by step"""
        
        try:
            # Step 1: GET_READER_CAPABILITIES
            logger.info("Step 1: GET_READER_CAPABILITIES")
            self.send_message(0x01, struct.pack('!B', 0))
            msg_type, msg_id, data = self.recv_message()
            if msg_type != 0x0B:
                logger.error(f"Unexpected response: 0x{msg_type:02X}")
                return False
            logger.info("✓ Capabilities OK")
            
            # Step 2: Basic SET_READER_CONFIG
            logger.info("Step 2: Basic SET_READER_CONFIG")
            self.send_message(0x03, struct.pack('!B', 0x80))
            msg_type, msg_id, data = self.recv_message()
            if msg_type != 0x0D:
                logger.error(f"Config failed: 0x{msg_type:02X}")
                return False
            logger.info("✓ Basic config OK")
            
            # Step 3: DELETE_ROSPEC (all)
            logger.info("Step 3: DELETE_ROSPEC")
            self.send_message(0x15, struct.pack('!I', 0))
            msg_type, msg_id, data = self.recv_message()
            if msg_type != 0x1F:
                logger.error(f"Delete ROSpec failed: 0x{msg_type:02X}")
                return False
            logger.info("✓ Delete ROSpec OK")
            
            # Step 4: Skip extended config, go straight to ROSpec
            logger.info("Step 4: ADD_ROSPEC (using exact structure from hex dump)")
            
            # Use the successful ROSpec from hex dump (line 251-258)
            rospec_hex = (
                "00b100620000" +    # ROSpec: Type=177, Len=98, ID=1234
                "04d20000" +        # ROSpec ID = 0x04D2, Priority=0, State=0
                "00b20012" +        # ROBoundarySpec: Type=178, Len=18
                "00b3000500" +      # ROSpecStartTrigger: Type=179, Len=5, Null
                "00b60009000000000000" +  # ROSpecStopTrigger: Type=182, Len=9, Null
                "00b70046" +        # AISpec: Type=183, Len=70
                "000100010" +       # Antenna Count=1, ID=1
                "00b80009000000000000" +  # AISpecStopTrigger: Type=184, Len=9, Null
                "00ba003504d201" +  # InventoryParameterSpec: Type=186, Len=53, ID=1234, Proto=1
                "00de002e0001" +    # AntennaConfiguration: Type=222, Len=46, ID=1
                "00df000600010" +   # RFTransmitter: Type=223, Len=6
                "00e0000a000100010078" + # RFReceiver: Type=224, Len=10
                "014a001800014f0008000300000150000b00001e0000000000"
            )
            
            rospec_data = bytes.fromhex(rospec_hex)
            self.send_message(0x14, rospec_data)
            msg_type, msg_id, data = self.recv_message()
            
            if msg_type == 0x1E:
                logger.info("✓ ROSpec added successfully!")
                
                # Step 5: ENABLE_ROSPEC
                logger.info("Step 5: ENABLE_ROSPEC")
                self.send_message(0x18, struct.pack('!I', 0x04D2))
                msg_type, msg_id, data = self.recv_message()
                if msg_type == 0x22:
                    logger.info("✓ ROSpec enabled!")
                    return True
                else:
                    logger.error(f"Enable failed: 0x{msg_type:02X}")
            else:
                logger.error(f"Add ROSpec failed: 0x{msg_type:02X if msg_type else 'None'}")
            
            return False
            
        except Exception as e:
            logger.error(f"Test sequence failed: {e}")
            return False
    
    def disconnect(self):
        if self.socket:
            try:
                self.send_message(0x0E, b'')
                self.recv_message()
            except:
                pass
            self.socket.close()
            logger.info("Disconnected")

def main():
    READER_IP = "192.168.10.106"
    
    print("\n" + "="*50)
    print("FR900 Standard LLRP Test")
    print("Testing without extended configuration")
    print("="*50)
    
    client = FR900StandardTest(READER_IP)
    
    try:
        if not client.connect():
            print("Connection failed")
            return
        
        success = client.test_sequence()
        
        if success:
            print("\n✅ SUCCESS!")
            print("FR900 accepts standard LLRP without extended config")
            print("Extended parameters are client software optimization")
        else:
            print("\n❌ FAILED")
            print("FR900 may require specific configuration")
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        client.disconnect()
        print("\nTest completed")

if __name__ == "__main__":
    main()