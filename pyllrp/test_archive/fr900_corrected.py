#!/usr/bin/env python3
"""
FR900 Corrected Implementation - Clean packet data from hex dump
Removes address offsets and uses actual packet data only
"""

import socket
import struct
import time
import logging
import binascii
import threading

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class FR900CorrectedClient:
    """FR900 LLRP Client with corrected packet data (no offset addresses)"""
    
    def __init__(self, host, port=5084):
        self.host = host
        self.port = port
        self.socket = None
        self.message_id = 1
        self.keepalive_thread = None
        self.keepalive_stop = False
        
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
        """Send LLRP message"""
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
        """Receive LLRP message"""
        try:
            self.socket.settimeout(15.0)  # Longer timeout for ROSpec operations
            header = self.socket.recv(10)
            if len(header) < 10:
                logger.debug(f"Short header received: {len(header)} bytes")
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
            
            logger.debug(f"RX: Type=0x{type_field:04X} (0x{msg_type:02X}), Len={msg_len}, ID={msg_id}")
            if data and len(data) <= 100:
                logger.debug(f"    Data: {binascii.hexlify(data).decode()}")
            return msg_type, msg_id, data
            
        except socket.timeout:
            logger.debug("Socket timeout - no response received")
            return None, None, None
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None, None, None
    
    def get_capabilities(self):
        """GET_READER_CAPABILITIES"""
        logger.info("Getting reader capabilities...")
        data = struct.pack('!B', 0)  # Request all capabilities
        self.send_message(0x01, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0B:
            logger.info("✓ Capabilities received")
            self.parse_capabilities(data)
            return True
        return False
    
    def parse_capabilities(self, data):
        """Parse capabilities to find antenna information"""
        logger.info("Analyzing FR900 capabilities...")
        
        # Look for antenna capabilities in the response
        offset = 0
        while offset < len(data) - 4:
            try:
                param_type = struct.unpack('!H', data[offset:offset+2])[0]
                param_len = struct.unpack('!H', data[offset+2:offset+4])[0]
                
                # Antenna capabilities (typically type 0x8B)
                if param_type == 0x8B:  # AntennaCapabilities
                    if param_len >= 8:
                        antenna_id = struct.unpack('!H', data[offset+4:offset+6])[0]
                        logger.info(f"  Found antenna: ID={antenna_id}")
                
                # General Device Capabilities (type 0x89)  
                elif param_type == 0x89:
                    logger.info(f"  General device capabilities found")
                
                # LLRP Capabilities (type 0x8D)
                elif param_type == 0x8D:
                    logger.info(f"  LLRP capabilities found")
                
                offset += param_len
                
            except:
                break
        
        logger.info("Capability analysis complete")
    
    def set_reader_config(self):
        """SET_READER_CONFIG - Basic configuration"""
        logger.info("Setting basic reader config...")
        
        # ResetToFactoryDefault: No (0x00)
        data = struct.pack('!B', 0x00)
        self.send_message(0x03, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x0D:
            logger.info("✓ Reader config set")
            return True
        return False
    
    def delete_all_rospecs(self):
        """DELETE_ROSPEC (all)"""
        logger.info("Deleting all ROSpecs...")
        data = struct.pack('!I', 0)  # ROSpec ID = 0 (all)
        self.send_message(0x15, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1F:
            logger.info("✓ All ROSpecs deleted")
            return True
        return False
    
    def delete_all_accessspecs(self):
        """DELETE_ACCESSSPEC (all)"""
        logger.info("Deleting all AccessSpecs...")
        data = struct.pack('!I', 0)  # AccessSpec ID = 0 (all)
        self.send_message(0x29, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x33:
            logger.info("✓ All AccessSpecs deleted")
            return True
        return False
    
    def set_reader_config_extended(self):
        """Extended SET_READER_CONFIG - Clean data from hex dump"""
        logger.info("Setting extended reader config...")
        
        # Extracted clean data from hex dump (removing address offsets)
        # Line 238-245: SET_READER_CONFIG with full configuration
        hex_data = (
            "0000f40020" +
            "f5000700088000" +
            "f5000700018000" +
            "f5000700038000" +
            "f5000700028000" +
            "ed001202" +
            "0001" +
            "00ee000b1400015c000540" +
            "00ef000501" +
            "00dc00090100002710" +
            "00e1000800010000" +
            "00e1000800020000" +
            "00e1000800030000" +
            "00e1000800040000" +
            "00e2000500"
        )
        
        data = bytes.fromhex(hex_data)
        self.send_message(0x03, data)
        
        msg_type, msg_id, resp_data = self.recv_message()
        if msg_type == 0x0D:
            logger.info("✓ Extended reader config set")
            return True
        return False
    
    def add_rospec_corrected(self):
        """ADD_ROSPEC with clean data from hex dump"""
        logger.info("Adding ROSpec with corrected data...")
        
        # Clean hex dump data from lines 253-260 (ADD_ROSPEC message body only)
        # Line 253: 04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00
        # Line 254: 04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00
        # Line 255: 09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8
        # Line 256: 00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de
        # Line 257: 00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01
        # Line 258: 00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00
        # Line 259: 00 01 50 00 0b 00 00 1e 00 00 00 00
        
        # Direct extraction from clean hex dump lines 253-259
        # Line 253: 04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00
        # Line 254: 04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00  
        # Line 255: 09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8
        # Line 256: 00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de
        # Line 257: 00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01
        # Line 258: 00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00
        # Line 259: 00 01 50 00 0b 00 00 1e 00 00 00 00
        
        # Extract exact bytes from clean hex dump (line 253-259), removing spaces and joining
        # Line 253: 04 14 00 00 00 6c 00 00 27 10 00 b1 00 62 00 00 -> remove header -> 00b1006200
        # Line 254: 04 d2 00 00 00 b2 00 12 00 b3 00 05 00 00 b6 00 -> 04d2000000b200120b30005000b600
        # Line 255: 09 00 00 00 00 00 00 b7 00 46 00 01 00 01 00 b8 -> 09000000000000b7004600010001000b8
        # Line 256: 00 09 00 00 00 00 00 00 ba 00 35 04 d2 01 00 de -> 0009000000000000ba003504d20100de
        # Line 257: 00 2e 00 01 00 df 00 06 00 01 00 e0 00 0a 00 01 -> 002e000100df00060001000e000a0001
        # Line 258: 00 01 00 78 01 4a 00 18 00 01 4f 00 08 00 01 00 -> 00010078014a001800014f0008000100
        # Line 259: 00 01 50 00 0b 00 00 1e 00 00 00 00           -> 0001500000b00001e00000000
        
        rospec_hex_clean = (
            "00b10062000004d2000000b200120b30005000b600" +
            "09000000000000b7004600010001000b8" +
            "0009000000000000ba003504d20100de" +
            "002e000100df00060001000e000a0001" +
            "00010078014a001800014f0008000100" +
            "0001500000b00001e00000000"
        )
        
        rospec_data = bytes.fromhex(rospec_hex_clean)
        
        logger.info(f"Sending corrected ROSpec: {len(rospec_data)} bytes")
        logger.debug(f"ROSpec hex: {rospec_hex_clean}")
        
        self.send_message(0x14, rospec_data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Corrected ROSpec added successfully!")
            return True
        else:
            if msg_type is None:
                logger.error("ROSpec failed: No response received")
            else:
                logger.error(f"ROSpec failed with response: 0x{msg_type:02X}")
            if data:
                logger.error(f"Response data: {binascii.hexlify(data).decode()}")
        return False
    
    def start_keepalive(self):
        """Start keepalive thread"""
        if self.keepalive_thread is None or not self.keepalive_thread.is_alive():
            self.keepalive_stop = False
            self.keepalive_thread = threading.Thread(target=self._keepalive_worker, daemon=True)
            self.keepalive_thread.start()
            logger.info("✓ Keepalive thread started")
    
    def stop_keepalive(self):
        """Stop keepalive thread"""
        self.keepalive_stop = True
        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=2)
            logger.info("✓ Keepalive thread stopped")
    
    def _keepalive_worker(self):
        """Keepalive worker thread"""
        while not self.keepalive_stop and self.socket:
            try:
                # Send KEEPALIVE every 30 seconds
                time.sleep(30)
                if not self.keepalive_stop and self.socket:
                    logger.debug("Sending keepalive...")
                    self.send_message(0x3E, b'')
                    
                    # Try to receive KEEPALIVE_ACK
                    original_timeout = self.socket.gettimeout()
                    self.socket.settimeout(2.0)
                    try:
                        msg_type, msg_id, data = self.recv_message()
                        if msg_type == 0x48:  # KEEPALIVE_ACK
                            logger.debug("✓ Keepalive ACK received")
                    except:
                        logger.debug("Keepalive ACK timeout (normal)")
                    finally:
                        self.socket.settimeout(original_timeout)
            except Exception as e:
                logger.debug(f"Keepalive error: {e}")
                break
    
    def add_rospec_from_full_packet(self):
        """ADD_ROSPEC with exact data from full packet capture"""
        logger.info("Adding ROSpec from full packet capture...")
        
        # From hex_dump_20250912_full packet.txt lines 266-272 (after TCP header)
        # Line 266: 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3
        # Line 267: 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46
        # Line 268: 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00
        # Line 269: 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01
        # Line 270: 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01
        # Line 271: 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00
        # Line 272: 00 00
        
        rospec_hex = (
            "00b1006200000" +  # ROSpec header (note: missing one 0?)
            "4d2000000b200120b3" +
            "000500000b600090000000000000b70046" +
            "000100010b80009000000000000ba00" +
            "3504d20100de002e000100df00060001" +
            "00e000a000100010078014a001800001" +
            "4f00080001000001500000b00001e0000" +
            "0000"
        )
        
        # Exact ROSpec data from full packet capture (lines 266-272)
        # From: "00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3"
        # To:   "4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00 00 00"
        rospec_hex_exact = (
            "00b1006200000" + "4d2000000b200120b3" +
            "0005000b6000900000000000b70046" +
            "000100010b80009000000000000ba00" +
            "3504d20100de002e000100df00060001" +
            "00e000a00001000100784a001800001" +
            "4f00080001000001500000b00001e0000" +
            "0000"
        )
        
        # Manual extraction from lines 266-272 of full packet file
        # Line 266: 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3  
        # Line 267: 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46
        # Line 268: 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00  
        # Line 269: 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01
        # Line 270: 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01
        # Line 271: 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00
        # Line 272: 00 00
        
        # 정확한 바이트별 추출 (공백 제거하여 연속된 헥사 문자열로)
        # 라인 266: 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3
        # 라인 267: 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46  
        # 라인 268: 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00
        # 라인 269: 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01
        # 라인 270: 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01
        # 라인 271: 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00
        # 라인 272: 00 00
        
        # 원본 패킷에서 공백만 제거하여 정확히 추출
        # 라인 266: 00 b1 00 62 00 00 04 d2 00 00 00 b2 00 12 00 b3
        # 라인 267: 00 05 00 00 b6 00 09 00 00 00 00 00 00 b7 00 46  
        # 라인 268: 00 01 00 01 00 b8 00 09 00 00 00 00 00 00 ba 00
        # 라인 269: 35 04 d2 01 00 de 00 2e 00 01 00 df 00 06 00 01
        # 라인 270: 00 e0 00 0a 00 01 00 01 00 78 01 4a 00 18 00 01
        # 라인 271: 4f 00 08 00 01 00 00 01 50 00 0b 00 00 1e 00 00
        # 라인 272: 00 00
        
        # 정확하게 추출된 98바이트 ROSpec 데이터
        rospec_hex_exact = "00b10062000004d2000000b2001200b300050000b60009000000000000b700460001000100b80009000000000000ba003504d20100de002e000100df0006000100e0000a000100010078014a001800014f0008000100000150000b00001e00000000"
        
        rospec_data = bytes.fromhex(rospec_hex_exact)
        
        logger.info(f"Sending ROSpec from full packet: {len(rospec_data)} bytes")
        logger.debug(f"ROSpec hex: {rospec_hex_exact}")
        
        self.send_message(0x14, rospec_data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Full packet ROSpec added successfully!")
            return True
        else:
            if msg_type is None:
                logger.error("ROSpec failed: No response received")
            else:
                logger.error(f"ROSpec failed with response: 0x{msg_type:02X}")
            if data:
                logger.error(f"Response data: {binascii.hexlify(data).decode()}")
        return False

    def add_rospec_multi_antenna(self):
        """ADD_ROSPEC with 8 antennas (434 bytes) based on Wireshark analysis"""
        logger.info("Adding multi-antenna ROSpec (8 antennas)...")
        
        rospec_data = bytearray()
        
        # ROSpec header (Type=177, ROSpecID=1234)
        rospec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHI', 0x00B1, 0, 1234))  # Type, Length(fix later), ROSpecID
        rospec_data.extend(struct.pack('!BB', 0, 0))  # Priority=0, CurrentState=0
        
        # ROBoundarySpec
        boundary_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B2, 0))  # Type, Length(fix later)
        
        # ROSpecStartTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B3, 5, 0))  # Type, Len=5, Null trigger
        
        # ROSpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B6, 9, 0))  # Type, Len=9, Null trigger
        rospec_data.extend(struct.pack('!I', 0))  # Duration = 0
        
        # Fix ROBoundarySpec length
        boundary_len = len(rospec_data) - boundary_start
        struct.pack_into('!H', rospec_data, boundary_start + 2, boundary_len)
        
        # AISpec 
        aispec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B7, 0))  # Type, Length(fix later)
        
        # 8 antennas (IDs 1-8)
        rospec_data.extend(struct.pack('!H', 8))  # Antenna count = 8
        for antenna_id in range(1, 9):
            rospec_data.extend(struct.pack('!H', antenna_id))  # Antenna ID
        
        # AISpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B8, 9, 0))  # Type, Len=9, Null trigger
        rospec_data.extend(struct.pack('!I', 0))  # Duration = 0
        
        # InventoryParameterSpec
        invparam_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHH', 0x00BA, 0, 1234))  # Type, Length(fix later), InventoryParameterSpecID
        rospec_data.extend(struct.pack('!B', 1))  # Protocol = EPC C1G2
        
        # For each antenna (1-8), add AntennaConfiguration
        for antenna_id in range(1, 9):
            antconfig_start = len(rospec_data)
            rospec_data.extend(struct.pack('!HHH', 0x00DE, 0, antenna_id))  # Type, Length(fix later), AntennaID
            
            # RFReceiver (Type=223)
            rospec_data.extend(struct.pack('!HHH', 0x00DF, 6, 1))  # Type, Len=6, Sensitivity=1
            
            # RFTransmitter (Type=224) 
            rospec_data.extend(struct.pack('!HHHHI', 0x00E0, 10, 1, 1, 120))  # Type, Len=10, HopTableID=1, ChannelIndex=1, Power=120
            
            # C1G2InventoryCommand (Type=330)
            c1g2inv_start = len(rospec_data)
            rospec_data.extend(struct.pack('!HH', 0x014A, 0))  # Type, Length(fix later)
            rospec_data.extend(struct.pack('!B', 0))  # TagInventoryStateAware=0
            
            # C1G2RFControl (Type=335)
            rospec_data.extend(struct.pack('!HHHH', 0x014F, 8, 3, 0))  # Type, Len=8, ModeIndex=3, Tari=0
            
            # C1G2SingulationControl (Type=336)
            rospec_data.extend(struct.pack('!HHHHI', 0x0150, 11, 0, 32, 0))  # Type, Len=11, Session=0, TagPopulation=32, TagTransitTime=0
            
            # Fix C1G2InventoryCommand length
            c1g2inv_len = len(rospec_data) - c1g2inv_start
            struct.pack_into('!H', rospec_data, c1g2inv_start + 2, c1g2inv_len)
            
            # Fix AntennaConfiguration length
            antconfig_len = len(rospec_data) - antconfig_start
            struct.pack_into('!H', rospec_data, antconfig_start + 2, antconfig_len)
        
        # Fix InventoryParameterSpec length
        invparam_len = len(rospec_data) - invparam_start
        struct.pack_into('!H', rospec_data, invparam_start + 2, invparam_len)
        
        # Fix AISpec length
        aispec_len = len(rospec_data) - aispec_start
        struct.pack_into('!H', rospec_data, aispec_start + 2, aispec_len)
        
        # Fix ROSpec length
        rospec_len = len(rospec_data) - rospec_start
        struct.pack_into('!H', rospec_data, rospec_start + 2, rospec_len)
        
        logger.info(f"Sending multi-antenna ROSpec: {len(rospec_data)} bytes")
        logger.debug(f"Expected size: ~434 bytes, Actual: {len(rospec_data)} bytes")
        
        self.send_message(0x14, bytes(rospec_data))
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Multi-antenna ROSpec added successfully!")
            return True
        else:
            if msg_type is None:
                logger.error("Multi-antenna ROSpec failed: No response received")
            else:
                logger.error(f"Multi-antenna ROSpec failed with response: 0x{msg_type:02X}")
            if data:
                logger.error(f"Response data: {binascii.hexlify(data).decode()}")
        return False
    
    def add_rospec_selective_antennas(self, antenna_ids):
        """ADD_ROSPEC with specific antenna IDs (flexible approach)"""
        logger.info(f"Adding ROSpec with antennas: {antenna_ids}")
        
        rospec_data = bytearray()
        
        # ROSpec header (Type=177, ROSpecID=1234)
        rospec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHI', 0x00B1, 0, 1234))
        rospec_data.extend(struct.pack('!BB', 0, 0))  # Priority=0, CurrentState=0
        
        # ROBoundarySpec
        boundary_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B2, 0))
        
        # ROSpecStartTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B3, 5, 0))
        
        # ROSpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B6, 5, 0))
        
        # Fix ROBoundarySpec length
        boundary_len = len(rospec_data) - boundary_start
        struct.pack_into('!H', rospec_data, boundary_start + 2, boundary_len)
        
        # AISpec
        aispec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B7, 0))
        
        # Antenna count and IDs
        rospec_data.extend(struct.pack('!H', len(antenna_ids)))
        for antenna_id in antenna_ids:
            rospec_data.extend(struct.pack('!H', antenna_id))
        
        # AISpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B8, 5, 0))
        
        # InventoryParameterSpec (simplified)
        invparam_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHH', 0x00BA, 0, 1234))
        rospec_data.extend(struct.pack('!B', 1))  # Protocol = EPC C1G2
        
        # Fix lengths
        invparam_len = len(rospec_data) - invparam_start
        struct.pack_into('!H', rospec_data, invparam_start + 2, invparam_len)
        
        aispec_len = len(rospec_data) - aispec_start
        struct.pack_into('!H', rospec_data, aispec_start + 2, aispec_len)
        
        rospec_len = len(rospec_data) - rospec_start
        struct.pack_into('!H', rospec_data, rospec_start + 2, rospec_len)
        
        logger.info(f"Sending {len(antenna_ids)}-antenna ROSpec: {len(rospec_data)} bytes")
        
        self.send_message(0x14, bytes(rospec_data))
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info(f"✓ {len(antenna_ids)}-antenna ROSpec added successfully!")
            return True
        else:
            if msg_type is None:
                logger.error("Selective antenna ROSpec failed: No response received")
            else:
                logger.error(f"Selective antenna ROSpec failed with response: 0x{msg_type:02X}")
            if data:
                logger.error(f"Response data: {binascii.hexlify(data).decode()}")
        return False
    
    def test_antenna_combinations(self):
        """Test different antenna combinations to find what works"""
        test_cases = [
            [1],           # Single antenna
            [1, 2],        # Dual antenna
            [1, 2, 3],     # Triple antenna  
            [1, 2, 3, 4],  # Quad antenna
        ]
        
        results = {}
        
        for antennas in test_cases:
            logger.info(f"\n--- Testing antennas: {antennas} ---")
            
            # Delete any existing ROSpecs
            self.delete_all_rospecs()
            time.sleep(0.5)
            
            # Try to add ROSpec with these antennas
            success = self.add_rospec_selective_antennas(antennas)
            results[str(antennas)] = success
            
            if success:
                logger.info(f"✅ Antennas {antennas}: SUCCESS")
                # Clean up
                self.delete_all_rospecs()
            else:
                logger.info(f"❌ Antennas {antennas}: FAILED")
                
            time.sleep(1)
        
        return results

    def add_rospec_simple(self):
        """ADD_ROSPEC with manually constructed simple structure"""
        logger.info("Adding simple ROSpec...")
        
        # Build ROSpec manually using struct
        rospec_data = bytearray()
        
        # ROSpec (Type=177, ID=1234)
        rospec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHI', 0x00B1, 0, 1234))  # Type, Length(fix later), ROSpecID
        rospec_data.extend(struct.pack('!BB', 0, 0))  # Priority=0, CurrentState=0
        
        # ROBoundarySpec 
        boundary_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B2, 0))  # Type, Length(fix later)
        
        # ROSpecStartTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B3, 5, 0))  # Type, Len=5, Null trigger
        
        # ROSpecStopTrigger - Null  
        rospec_data.extend(struct.pack('!HHB', 0x00B6, 5, 0))  # Type, Len=5, Null trigger
        
        # Fix ROBoundarySpec length
        boundary_len = len(rospec_data) - boundary_start
        struct.pack_into('!H', rospec_data, boundary_start + 2, boundary_len)
        
        # AISpec
        aispec_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HH', 0x00B7, 0))  # Type, Length(fix later)
        rospec_data.extend(struct.pack('!H', 1))  # Antenna count = 1
        rospec_data.extend(struct.pack('!H', 1))  # Antenna ID = 1
        
        # AISpecStopTrigger - Null
        rospec_data.extend(struct.pack('!HHB', 0x00B8, 5, 0))  # Type, Len=5, Null trigger
        
        # InventoryParameterSpec
        invparam_start = len(rospec_data)
        rospec_data.extend(struct.pack('!HHH', 0x00BA, 0, 1234))  # Type, Length(fix later), InventoryParameterSpecID
        rospec_data.extend(struct.pack('!B', 1))  # Protocol = EPC C1G2
        
        # Fix InventoryParameterSpec length
        invparam_len = len(rospec_data) - invparam_start  
        struct.pack_into('!H', rospec_data, invparam_start + 2, invparam_len)
        
        # Fix AISpec length
        aispec_len = len(rospec_data) - aispec_start
        struct.pack_into('!H', rospec_data, aispec_start + 2, aispec_len)
        
        # Fix ROSpec length
        rospec_len = len(rospec_data) - rospec_start
        struct.pack_into('!H', rospec_data, rospec_start + 2, rospec_len)
        
        logger.info(f"Sending simple ROSpec: {len(rospec_data)} bytes")
        logger.debug(f"ROSpec hex: {binascii.hexlify(rospec_data).decode()}")
        
        self.send_message(0x14, bytes(rospec_data))
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x1E:
            logger.info("✓ Simple ROSpec added successfully!")
            return True
        else:
            if msg_type is None:
                logger.error("ROSpec failed: No response received")
            else:
                logger.error(f"ROSpec failed with response: 0x{msg_type:02X}")
            if data:
                logger.error(f"Response data: {binascii.hexlify(data).decode()}")
        return False
    
    def enable_rospec(self, rospec_id=0x04D2):
        """ENABLE_ROSPEC"""
        logger.info("Enabling ROSpec...")
        data = struct.pack('!I', rospec_id)
        self.send_message(0x18, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x22:
            logger.info(f"✓ ROSpec {rospec_id} enabled")
            return True
        return False
    
    def start_rospec(self, rospec_id=0x04D2):
        """START_ROSPEC"""
        logger.info("Starting ROSpec...")
        data = struct.pack('!I', rospec_id)
        self.send_message(0x16, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x20:
            logger.info(f"✓ ROSpec {rospec_id} started")
            return True
        return False
    
    def stop_rospec(self, rospec_id=0x04D2):
        """STOP_ROSPEC"""
        logger.info("Stopping ROSpec...")
        data = struct.pack('!I', rospec_id)
        self.send_message(0x17, data)
        
        msg_type, msg_id, data = self.recv_message()
        if msg_type == 0x21:
            logger.info(f"✓ ROSpec {rospec_id} stopped")
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
            
            if msg_type == 0x3D:  # RO_ACCESS_REPORT
                tag_count += 1
                
                # Extract EPC from tag report
                if len(data) > 20:
                    try:
                        # Look for EPC-96 parameter (0x00F1)
                        for i in range(len(data) - 12):
                            if data[i:i+2] == b'\x00\xf1':
                                epc_len = struct.unpack('!H', data[i+2:i+4])[0] - 4
                                if 8 <= epc_len <= 16:
                                    epc = data[i+4:i+4+epc_len]
                                    epc_hex = binascii.hexlify(epc).decode().upper()
                                    unique_epcs.add(epc_hex)
                                    logger.info(f"  Tag #{tag_count}: EPC={epc_hex}")
                                    break
                        else:
                            logger.debug(f"  Tag report #{tag_count} (no EPC extracted)")
                    except:
                        logger.debug(f"  Tag report #{tag_count} (parse error)")
                
            elif msg_type == 0x3F:  # READER_EVENT_NOTIFICATION
                logger.debug("  Reader event")
        
        return tag_count, len(unique_epcs)
    
    def disconnect(self):
        """Disconnect from reader"""
        # Stop keepalive first
        self.stop_keepalive()
        
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
    print(" FR900 Corrected Test - Clean Packet Data")
    print(" Using hex dump without address offsets")
    print("="*60 + "\n")
    
    client = FR900CorrectedClient(READER_IP)
    
    try:
        # Phase 1: Connect
        if not client.connect():
            print("Failed to connect")
            return
        
        # Phase 2: Start keepalive and basic setup
        client.start_keepalive()
        client.get_capabilities()
        client.set_reader_config()
        client.delete_all_rospecs()
        client.delete_all_accessspecs()
        
        # Phase 3: Skip extended configuration (causes connection drop)
        logger.info("Skipping extended configuration - using basic config only")
        
        # Phase 4: Test antenna combinations
        print("\n" + "="*60)
        print(" FR900 ANTENNA CAPABILITY TESTING")
        print("="*60)
        
        results = client.test_antenna_combinations()
        
        print("\n" + "="*60)
        print(" ANTENNA TEST RESULTS")
        print("="*60)
        
        for antenna_config, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  Antennas {antenna_config}: {status}")
        
        # Find the maximum working antenna configuration
        working_configs = [eval(k) for k, v in results.items() if v]
        if working_configs:
            max_antennas = max(working_configs, key=len)
            print(f"\n🎯 Maximum working configuration: {max_antennas}")
            print(f"📊 FR900 supports up to {len(max_antennas)} antennas simultaneously")
            
            # Test the maximum configuration with actual inventory
            print(f"\n=== Testing inventory with {len(max_antennas)} antennas ===")
            if client.add_rospec_selective_antennas(max_antennas):
                client.enable_rospec()
                client.start_rospec()
                
                print(f"Reading tags with {len(max_antennas)} antennas for 3 seconds...")
                tag_count, unique_count = client.read_tags(duration=3)
                print(f"Results: {tag_count} reports, {unique_count} unique EPCs")
                
                client.stop_rospec()
        else:
            print("\n❌ No working multi-antenna configurations found")
        
        print("\n" + "="*60)
        print(" ANTENNA TESTING COMPLETE")
        print("="*60)
        
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