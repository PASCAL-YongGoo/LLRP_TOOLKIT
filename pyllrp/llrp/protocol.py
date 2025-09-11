"""
Pure Python LLRP Protocol Implementation
Based on LLRP v1.0.1 specification
"""

import struct
import socket
import threading
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# LLRP Message Types
class MessageType(IntEnum):
    # Reader to Client
    GET_READER_CAPABILITIES_RESPONSE = 11
    ADD_ROSPEC_RESPONSE = 30
    DELETE_ROSPEC_RESPONSE = 31
    START_ROSPEC_RESPONSE = 32
    STOP_ROSPEC_RESPONSE = 33
    ENABLE_ROSPEC_RESPONSE = 34
    DISABLE_ROSPEC_RESPONSE = 35
    GET_ROSPECS_RESPONSE = 36
    ADD_ACCESSSPEC_RESPONSE = 50
    DELETE_ACCESSSPEC_RESPONSE = 51
    ENABLE_ACCESSSPEC_RESPONSE = 52
    DISABLE_ACCESSSPEC_RESPONSE = 53
    GET_ACCESSSPECS_RESPONSE = 54
    GET_READER_CONFIG_RESPONSE = 12
    SET_READER_CONFIG_RESPONSE = 13
    CLOSE_CONNECTION_RESPONSE = 14
    GET_REPORT = 60
    RO_ACCESS_REPORT = 61
    KEEPALIVE = 62
    READER_EVENT_NOTIFICATION = 63
    ERROR_MESSAGE = 100
    
    # Client to Reader  
    GET_READER_CAPABILITIES = 1
    ADD_ROSPEC = 20
    DELETE_ROSPEC = 21
    START_ROSPEC = 22
    STOP_ROSPEC = 23
    ENABLE_ROSPEC = 24
    DISABLE_ROSPEC = 25
    GET_ROSPECS = 26
    ADD_ACCESSSPEC = 40
    DELETE_ACCESSSPEC = 41
    ENABLE_ACCESSSPEC = 42
    DISABLE_ACCESSSPEC = 43
    GET_ACCESSSPECS = 44
    GET_READER_CONFIG = 2
    SET_READER_CONFIG = 3
    CLOSE_CONNECTION = 4
    KEEPALIVE_ACK = 72
    ENABLE_EVENTS_AND_REPORTS = 64
    
    # Custom
    CUSTOM_MESSAGE = 1023


# Parameter Types
class ParameterType(IntEnum):
    # Timestamps
    UTC_TIMESTAMP = 128
    UPTIME = 129
    
    # Capabilities
    GENERAL_DEVICE_CAPABILITIES = 137
    LLRP_CAPABILITIES = 142
    REGULATORY_CAPABILITIES = 143
    UHF_BAND_CAPABILITIES = 144
    AIR_PROTOCOL_LLRP_CAPABILITIES = 169
    
    # ROSpec
    ROSPEC = 177
    RO_BOUNDARY_SPEC = 178
    ROSPEC_START_TRIGGER = 179
    ROSPEC_STOP_TRIGGER = 182
    AI_SPEC = 183
    AI_SPEC_STOP_TRIGGER = 184
    INVENTORY_PARAMETER_SPEC = 186
    RF_SURVEY_SPEC = 187
    LOOP_SPEC = 188
    
    # Reporting
    RO_REPORT_SPEC = 237
    TAG_REPORT_CONTENT_SELECTOR = 238
    ACCESS_REPORT_SPEC = 239
    TAG_REPORT_DATA = 240
    EPC_96 = 13
    EPC_DATA = 241
    
    # Tag Report Fields
    ROSPEC_ID = 9
    SPEC_INDEX = 14
    INVENTORY_PARAMETER_SPEC_ID = 10
    ANTENNA_ID = 1
    PEAK_RSSI = 6
    CHANNEL_INDEX = 7
    FIRST_SEEN_TIMESTAMP_UTC = 2
    FIRST_SEEN_TIMESTAMP_UPTIME = 3
    LAST_SEEN_TIMESTAMP_UTC = 4
    LAST_SEEN_TIMESTAMP_UPTIME = 5
    TAG_SEEN_COUNT = 8
    ACCESS_SPEC_ID = 16
    
    # Configuration
    ANTENNA_CONFIGURATION = 222
    ANTENNA_PROPERTIES = 221
    RF_RECEIVER = 223
    RF_TRANSMITTER = 224
    
    # Event Parameters
    READER_EVENT_NOTIFICATION_DATA = 246
    CONNECTION_ATTEMPT_EVENT = 256
    CONNECTION_CLOSE_EVENT = 257
    ANTENNA_EVENT = 258
    READER_EXCEPTION_EVENT = 262
    ROSPEC_EVENT = 263
    AI_SPEC_EVENT = 264
    REPORT_BUFFER_LEVEL_WARNING_EVENT = 265
    REPORT_BUFFER_OVERFLOW_ERROR_EVENT = 266
    
    # Custom
    CUSTOM = 1023


class AirProtocol(IntEnum):
    UNSPECIFIED = 0
    EPC_GLOBAL_CLASS1_GEN2 = 1


@dataclass
class LLRPHeader:
    """LLRP Message Header (10 bytes)"""
    version: int = 1
    message_type: int = 0
    message_length: int = 10
    message_id: int = 0
    
    def pack(self) -> bytes:
        """Pack header into binary format"""
        # First 16 bits: 3 bits reserved, 3 bits version, 10 bits message type
        first_16 = (self.version << 10) | (self.message_type & 0x3FF)
        return struct.pack('!HII', first_16, self.message_length, self.message_id)
    
    @classmethod
    def unpack(cls, data: bytes) -> 'LLRPHeader':
        """Unpack header from binary format"""
        if len(data) < 10:
            raise ValueError("Insufficient data for header")
        
        first_16, length, msg_id = struct.unpack('!HII', data[:10])
        version = (first_16 >> 10) & 0x7
        msg_type = first_16 & 0x3FF
        
        return cls(version, msg_type, length, msg_id)


class LLRPParameter(ABC):
    """Base class for LLRP Parameters with complete TLV/TV support"""
    
    def __init__(self, param_type: int):
        self.param_type = param_type
        # TV encoding is used for specific parameter types (see LLRP spec)
        self.tv_encoded = self._is_tv_parameter(param_type)
    
    def _is_tv_parameter(self, param_type: int) -> bool:
        """Determine if parameter uses TV encoding based on LLRP spec"""
        # TV parameters from LLRP specification
        tv_parameters = {
            1,   # AntennaID
            2,   # FirstSeenTimestampUTC
            3,   # FirstSeenTimestampUptime
            4,   # LastSeenTimestampUTC
            5,   # LastSeenTimestampUptime
            6,   # PeakRSSI
            7,   # ChannelIndex
            8,   # TagSeenCount
            9,   # ROSpecID
            10,  # InventoryParameterSpecID
            11,  # C1G2CRC
            12,  # C1G2PC
            13,  # EPC-96
            14,  # SpecIndex
            15,  # ClientRequestOpSpecResult
            16,  # AccessSpecID
            17,  # C1G2SingulationDetails
            18,  # C1G2WriteMode
        }
        return param_type in tv_parameters
    
    @abstractmethod
    def encode(self) -> bytes:
        """Encode parameter to binary"""
        pass
    
    @abstractmethod
    def decode(self, data: bytes) -> int:
        """Decode parameter from binary, return bytes consumed"""
        pass
    
    def encode_header(self, total_length: int) -> bytes:
        """Encode parameter header (TLV or TV)"""
        if self.tv_encoded:
            # TV encoding: 1 bit (1), 7 bits type, then value directly
            return struct.pack('!B', 0x80 | (self.param_type & 0x7F))
        else:
            # TLV encoding: 6 bits reserved (0), 10 bits type, 16 bits length
            type_field = self.param_type & 0x3FF
            return struct.pack('!HH', type_field, total_length)
    
    @staticmethod
    def parse_header(data: bytes, offset: int = 0) -> tuple:
        """
        Parse parameter header from binary data
        
        Returns:
            (param_type, param_length, header_length, is_tv)
        """
        if len(data) <= offset:
            return None, 0, 0, False
            
        first_byte = data[offset]
        
        if first_byte & 0x80:  # TV parameter (bit 0 = 1)
            param_type = first_byte & 0x7F
            # TV parameter lengths are fixed based on type
            tv_lengths = {
                1: 3,   # AntennaID: 1 header + 2 data
                2: 9,   # FirstSeenTimestampUTC: 1 header + 8 data  
                3: 9,   # FirstSeenTimestampUptime: 1 header + 8 data
                4: 9,   # LastSeenTimestampUTC: 1 header + 8 data
                5: 9,   # LastSeenTimestampUptime: 1 header + 8 data
                6: 2,   # PeakRSSI: 1 header + 1 data
                7: 3,   # ChannelIndex: 1 header + 2 data
                8: 3,   # TagSeenCount: 1 header + 2 data
                9: 5,   # ROSpecID: 1 header + 4 data
                10: 3,  # InventoryParameterSpecID: 1 header + 2 data
                13: 13, # EPC-96: 1 header + 12 data
                14: 3,  # SpecIndex: 1 header + 2 data
                16: 5,  # AccessSpecID: 1 header + 4 data
            }
            param_length = tv_lengths.get(param_type, 2)  # Default minimum
            return param_type, param_length, 1, True
            
        else:  # TLV parameter (bit 0 = 0)
            if len(data) < offset + 4:
                return None, 0, 0, False
                
            # Read type and length
            type_field = struct.unpack('!H', data[offset:offset+2])[0]
            param_type = type_field & 0x3FF  # Lower 10 bits
            param_length = struct.unpack('!H', data[offset+2:offset+4])[0]
            
            return param_type, param_length, 4, False


@dataclass
class UTCTimestamp(LLRPParameter):
    """UTC Timestamp Parameter"""
    microseconds: int = 0
    
    def __init__(self, microseconds: int = 0):
        super().__init__(ParameterType.UTC_TIMESTAMP)
        self.microseconds = microseconds
    
    def encode(self) -> bytes:
        header = self.encode_header(12)  # 4 bytes header + 8 bytes data
        return header + struct.pack('!Q', self.microseconds)
    
    def decode(self, data: bytes) -> int:
        self.microseconds = struct.unpack('!Q', data[4:12])[0]
        return 12


@dataclass  
class LLRPStatus(LLRPParameter):
    """LLRP Status Parameter - Enhanced with error handling"""
    
    def __init__(self, status_code: int = 0, error_description: str = ""):
        super().__init__(287)  # LLRPStatus type number
        self.status_code = status_code
        self.error_description = error_description
    
    def encode(self) -> bytes:
        """Encode LLRPStatus parameter"""
        desc_bytes = self.error_description.encode('utf-8')
        desc_len = len(desc_bytes)
        
        # Payload: 2 bytes status code + 2 bytes desc length + description
        payload = struct.pack('!HH', self.status_code, desc_len) + desc_bytes
        
        # Add padding to 4-byte boundary
        while len(payload) % 4 != 0:
            payload += b'\x00'
        
        # TLV header + payload
        total_len = 4 + len(payload)
        header = self.encode_header(total_len)
        return header + payload
    
    def decode(self, data: bytes) -> int:
        """Decode LLRPStatus parameter"""
        if len(data) < 8:
            return 0
            
        # Parse header to get total length
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != 287:  # LLRPStatus type
            return 0
        
        # Read status code and description length
        payload_start = header_len
        if len(data) < payload_start + 4:
            return param_length
            
        self.status_code, desc_len = struct.unpack('!HH', data[payload_start:payload_start+4])
        
        # Read description if present
        if desc_len > 0 and len(data) >= payload_start + 4 + desc_len:
            desc_end = payload_start + 4 + desc_len
            self.error_description = data[payload_start+4:desc_end].decode('utf-8', errors='replace')
        else:
            self.error_description = ""
            
        return param_length
    
    def is_success(self) -> bool:
        """Check if status indicates success"""
        from .errors import is_success
        return is_success(self.status_code)
    
    def is_error(self) -> bool:
        """Check if status indicates an error"""
        from .errors import is_error
        return is_error(self.status_code)
    
    def get_error_name(self) -> str:
        """Get human-readable error name"""
        from .errors import LLRPStatusCode
        try:
            return LLRPStatusCode(self.status_code).name
        except ValueError:
            return f"UnknownStatus_{self.status_code}"
    
    def get_error_description(self) -> str:
        """Get complete error description"""
        from .errors import get_error_description
        
        if self.error_description:
            return self.error_description
        return get_error_description(self.status_code)
    
    def raise_if_error(self):
        """Raise appropriate LLRP exception if status indicates error"""
        if self.is_error():
            from .errors import create_llrp_exception
            raise create_llrp_exception(self.status_code, self.get_error_description())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/debugging"""
        return {
            'status_code': self.status_code,
            'status_name': self.get_error_name(),
            'error_description': self.get_error_description(),
            'is_success': self.is_success(),
            'is_error': self.is_error()
        }


class LLRPMessage(ABC):
    """Base class for LLRP Messages"""
    
    def __init__(self, msg_type: int, msg_id: int = 0):
        self.header = LLRPHeader(message_type=msg_type, message_id=msg_id)
        self.parameters: List[LLRPParameter] = []
    
    def encode(self) -> bytes:
        """Encode message to binary"""
        # Encode all parameters
        param_bytes = b''.join(p.encode() for p in self.parameters)
        
        # Update header length
        self.header.message_length = 10 + len(param_bytes)
        
        # Combine header and parameters
        return self.header.pack() + param_bytes
    
    @abstractmethod
    def decode_parameters(self, data: bytes):
        """Decode parameters from binary data"""
        pass
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LLRPMessage':
        """Create message from binary data with improved parsing"""
        if len(data) < 10:
            raise ValueError("Insufficient data for LLRP message header")
            
        header = LLRPHeader.unpack(data)
        
        # Import message classes here to avoid circular imports
        from .messages import MESSAGE_CLASSES
        
        # Create appropriate message class based on type
        msg_class = MESSAGE_CLASSES.get(header.message_type)
        
        if msg_class:
            msg = msg_class(header.message_id)
        else:
            # Unknown message type, create generic message
            msg = LLRPMessage(header.message_type, header.message_id)
        
        msg.header = header
        
        # Decode parameters if any
        if len(data) > 10 and header.message_length > 10:
            try:
                msg.decode_parameters(data[10:header.message_length])
            except Exception as e:
                print(f"Warning: Failed to decode message parameters: {e}")
        
        return msg


@dataclass
class GetReaderCapabilities(LLRPMessage):
    """GET_READER_CAPABILITIES Message"""
    
    def __init__(self, msg_id: int = 1, requested_data: int = 0):
        super().__init__(MessageType.GET_READER_CAPABILITIES, msg_id)
        self.requested_data = requested_data
    
    def encode(self) -> bytes:
        # Add requested data as first byte after header
        param_bytes = struct.pack('!B', self.requested_data)
        self.header.message_length = 11  # 10 header + 1 byte
        return self.header.pack() + param_bytes
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 1:
            self.requested_data = struct.unpack('!B', data[0:1])[0]


@dataclass
class GetReaderCapabilitiesResponse(LLRPMessage):
    """GET_READER_CAPABILITIES_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 1):
        super().__init__(MessageType.GET_READER_CAPABILITIES_RESPONSE, msg_id)
        self.llrp_status: Optional[LLRPStatus] = None
        self.general_device_capabilities = None
        self.llrp_capabilities = None
        self.regulatory_capabilities = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters with complete capability parsing"""
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
            
            param_data = data[offset:offset+param_length]
            
            # Parse known parameters
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(param_data)
            elif param_type == ParameterType.GENERAL_DEVICE_CAPABILITIES:
                from .capabilities_parameters import GeneralDeviceCapabilities
                self.general_device_capabilities = GeneralDeviceCapabilities()
                self.general_device_capabilities.decode(param_data)
                consumed = param_length
            elif param_type == ParameterType.LLRP_CAPABILITIES:
                from .capabilities_parameters import LLRPCapabilities
                self.llrp_capabilities = LLRPCapabilities()
                self.llrp_capabilities.decode(param_data)
                consumed = param_length
            elif param_type == ParameterType.REGULATORY_CAPABILITIES:
                from .capabilities_parameters import RegulatoryCapabilities
                self.regulatory_capabilities = RegulatoryCapabilities()
                self.regulatory_capabilities.decode(param_data)
                consumed = param_length
            elif param_type == ParameterType.AIR_PROTOCOL_LLRP_CAPABILITIES:
                from .capabilities_parameters import AirProtocolLLRPCapabilities
                if not hasattr(self, 'air_protocol_capabilities'):
                    self.air_protocol_capabilities = []
                air_proto_cap = AirProtocolLLRPCapabilities()
                air_proto_cap.decode(param_data)
                self.air_protocol_capabilities.append(air_proto_cap)
                consumed = param_length
            else:
                # Skip unknown parameters
                consumed = param_length
            
            offset += consumed


# Message classes will be registered in messages.py to avoid circular imports


class LLRPConnection:
    """LLRP TCP/IP Connection Handler"""
    
    def __init__(self, host: str, port: int = 5084):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.recv_thread: Optional[threading.Thread] = None
        self.message_handlers: Dict[int, List] = {}
        self.pending_responses: Dict[int, LLRPMessage] = {}
        self.response_events: Dict[int, threading.Event] = {}
        self.next_message_id = 1
        
    def connect(self, timeout: float = 10.0) -> bool:
        """Connect to LLRP reader"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Start receive thread
            self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.recv_thread.start()
            
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from reader"""
        self.connected = False
        if self.socket:
            self.socket.close()
            self.socket = None
        logger.info("Disconnected")
    
    def send_message(self, message: LLRPMessage) -> bool:
        """Send LLRP message"""
        if not self.connected:
            return False
        
        try:
            data = message.encode()
            self.socket.sendall(data)
            logger.debug(f"Sent {message.__class__.__name__} (ID: {message.header.message_id})")
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False
    
    def send_recv(self, message: LLRPMessage, timeout: float = 5.0) -> Optional[LLRPMessage]:
        """Send message and wait for response"""
        msg_id = self.next_message_id
        self.next_message_id += 1
        
        message.header.message_id = msg_id
        
        # Setup response event
        event = threading.Event()
        self.response_events[msg_id] = event
        
        # Send message
        if not self.send_message(message):
            del self.response_events[msg_id]
            return None
        
        # Wait for response
        if event.wait(timeout):
            response = self.pending_responses.pop(msg_id, None)
            del self.response_events[msg_id]
            return response
        else:
            del self.response_events[msg_id]
            logger.error(f"Response timeout for message ID {msg_id}")
            return None
    
    def _receive_loop(self):
        """Receive messages from reader with enhanced error handling"""
        from .messages import ErrorMessage, KeepAlive
        from .errors import LLRPConnectionError, log_llrp_status
        
        buffer = b''
        keepalive_failures = 0
        
        while self.connected:
            try:
                # Receive data with timeout
                data = self.socket.recv(4096)
                if not data:
                    logger.warning("Reader closed connection")
                    break
                
                buffer += data
                
                # Process complete messages
                while len(buffer) >= 10:
                    try:
                        # Parse header
                        header = LLRPHeader.unpack(buffer)
                        
                        # Validate message length
                        if header.message_length < 10 or header.message_length > len(buffer):
                            if header.message_length < 10:
                                logger.error(f"Invalid message length: {header.message_length}")
                                buffer = buffer[1:]  # Skip one byte and try again
                                continue
                            else:
                                # Need more data
                                break
                        
                        # Extract message
                        msg_data = buffer[:header.message_length]
                        buffer = buffer[header.message_length:]
                        
                        # Parse message
                        message = LLRPMessage.from_bytes(msg_data)
                        logger.debug(f"Received {message.__class__.__name__} (ID: {header.message_id})")
                        
                        # Handle special message types
                        if isinstance(message, ErrorMessage):
                            self._handle_error_message(message)
                        elif isinstance(message, KeepAlive):
                            self._handle_keepalive(message)
                            keepalive_failures = 0  # Reset failure count
                        
                        # Handle response
                        if header.message_id in self.response_events:
                            self.pending_responses[header.message_id] = message
                            self.response_events[header.message_id].set()
                        
                        # Call user handlers
                        for handler in self.message_handlers.get(header.message_type, []):
                            try:
                                handler(message)
                            except Exception as handler_error:
                                logger.error(f"Handler error: {handler_error}")
                                
                    except Exception as parse_error:
                        logger.error(f"Message parsing error: {parse_error}")
                        # Try to recover by skipping one byte
                        if len(buffer) > 0:
                            buffer = buffer[1:]
                        
            except socket.timeout:
                keepalive_failures += 1
                if keepalive_failures > 3:
                    logger.error("Too many keepalive failures, disconnecting")
                    break
                    
            except ConnectionResetError:
                logger.warning("Reader reset connection")
                break
                
            except Exception as e:
                if self.connected:
                    logger.error(f"Receive error: {e}")
                    # Try to continue for transient errors
                    import time
                    time.sleep(0.1)
                else:
                    break
        
        logger.info("Receive loop terminated")
        self.connected = False
    
    def _handle_error_message(self, error_msg: 'ErrorMessage'):
        """Handle ERROR_MESSAGE from reader"""
        from .errors import log_llrp_status
        
        error_info = error_msg.get_error_info()
        logger.error(f"Reader Error: {error_info}")
        
        if error_msg.llrp_status:
            log_llrp_status(
                error_msg.llrp_status.status_code,
                error_msg.llrp_status.error_description,
                logging.ERROR
            )
    
    def _handle_keepalive(self, keepalive_msg: 'KeepAlive'):
        """Handle KEEPALIVE message from reader"""
        from .messages import KeepAliveAck
        
        # Send KEEPALIVE_ACK response
        ack = KeepAliveAck(keepalive_msg.header.message_id)
        self.send_message(ack)
        logger.debug(f"Sent KEEPALIVE_ACK for message ID {keepalive_msg.header.message_id}")
    
    def graceful_disconnect(self) -> bool:
        """Gracefully disconnect from reader using CLOSE_CONNECTION"""
        from .messages import CloseConnection
        
        if not self.connected:
            return True
        
        try:
            # Send CLOSE_CONNECTION
            close_msg = CloseConnection(self.next_message_id)
            response = self.send_recv(close_msg, timeout=5.0)
            
            if response:
                logger.info("Graceful disconnect successful")
                return True
            else:
                logger.warning("No response to CLOSE_CONNECTION")
                
        except Exception as e:
            logger.error(f"Graceful disconnect failed: {e}")
        
        finally:
            self.disconnect()
        
        return False
    
    def add_message_handler(self, msg_type: int, handler):
        """Add message handler"""
        if msg_type not in self.message_handlers:
            self.message_handlers[msg_type] = []
        self.message_handlers[msg_type].append(handler)