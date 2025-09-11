"""
LLRP Parameter Definitions for Tag Reports
"""

import struct
from typing import Optional
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


@dataclass
class EPCData(LLRPParameter):
    """EPC Data Parameter - Variable length EPC (TLV encoding)"""
    
    def __init__(self, epc_bytes: bytes = b''):
        super().__init__(ParameterType.EPC_DATA)
        self.epc = epc_bytes
    
    def encode(self) -> bytes:
        """Encode EPCData parameter"""
        # EPC length in bits (2 bytes) + EPC data
        epc_bit_count = len(self.epc) * 8
        payload = struct.pack('!H', epc_bit_count) + self.epc
        
        # Add padding to 4-byte boundary (LLRP requirement)
        while len(payload) % 4 != 0:
            payload += b'\x00'
        
        # TLV encoding: 4-byte header + payload
        total_length = 4 + len(payload)
        header = self.encode_header(total_length)
        return header + payload
    
    def decode(self, data: bytes) -> int:
        """Decode EPCData parameter"""
        if len(data) < 6:
            return 0
            
        # Parse header to get total length
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.EPC_DATA:
            return 0
            
        # Read EPC bit count (after header)
        epc_bit_count = struct.unpack('!H', data[header_len:header_len+2])[0]
        epc_byte_count = (epc_bit_count + 7) // 8  # Round up to bytes
        
        # Extract EPC data
        epc_start = header_len + 2
        self.epc = data[epc_start:epc_start+epc_byte_count]
        
        return param_length
    
    def get_epc_hex(self) -> str:
        """Get EPC as hex string"""
        return self.epc.hex().upper()


@dataclass
class EPC96(LLRPParameter):
    """EPC-96 Parameter - Fixed 96-bit EPC (TV encoding)"""
    
    def __init__(self, epc_96: int = 0):
        super().__init__(ParameterType.EPC_96)
        self.epc = epc_96
    
    def encode(self) -> bytes:
        """Encode EPC-96 parameter"""
        # TV encoding: 1 byte header + 12 bytes data (96 bits)
        header = self.encode_header(13)
        
        # Convert 96-bit integer to 12 bytes
        data = b''
        temp_epc = self.epc
        for i in range(12):
            data = bytes([(temp_epc >> (8 * (11 - i))) & 0xFF]) + data
        
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode EPC-96 parameter"""
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 13:
            epc_bytes = data[1:13]  # 12 bytes for 96 bits
            
            # Convert to integer
            self.epc = 0
            for byte in epc_bytes:
                self.epc = (self.epc << 8) | byte
                
        return 13
    
    def get_epc_hex(self) -> str:
        """Get EPC as hex string"""
        return f"{self.epc:024X}"


@dataclass
class ROSpecID(LLRPParameter):
    """ROSpec ID Parameter (TV encoding)"""
    
    def __init__(self, rospec_id: int = 0):
        super().__init__(ParameterType.ROSPEC_ID)
        self.rospec_id = rospec_id
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 4 bytes data
        header = self.encode_header(5)
        data = struct.pack('!I', self.rospec_id)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 5:
            self.rospec_id = struct.unpack('!I', data[1:5])[0]
        return 5


@dataclass
class SpecIndex(LLRPParameter):
    """Spec Index Parameter (TV encoding)"""
    
    def __init__(self, spec_index: int = 0):
        super().__init__(ParameterType.SPEC_INDEX)
        self.spec_index = spec_index
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 2 bytes data
        header = self.encode_header(3)
        data = struct.pack('!H', self.spec_index)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 3:
            self.spec_index = struct.unpack('!H', data[1:3])[0]
        return 3


@dataclass
class InventoryParameterSpecID(LLRPParameter):
    """Inventory Parameter Spec ID Parameter"""
    
    def __init__(self, spec_id: int = 0):
        super().__init__(ParameterType.INVENTORY_PARAMETER_SPEC_ID)
        self.spec_id = spec_id
    
    def encode(self) -> bytes:
        header = self.encode_header(6)
        data = struct.pack('!H', self.spec_id)
        return header + data
    
    def decode(self, data: bytes) -> int:
        self.spec_id = struct.unpack('!H', data[4:6])[0]
        return 6


@dataclass
class AntennaID(LLRPParameter):
    """Antenna ID Parameter (TV encoding)"""
    
    def __init__(self, antenna_id: int = 0):
        super().__init__(ParameterType.ANTENNA_ID)
        self.antenna_id = antenna_id
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 2 bytes data
        header = self.encode_header(3)
        data = struct.pack('!H', self.antenna_id)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 3:
            self.antenna_id = struct.unpack('!H', data[1:3])[0]
        return 3


@dataclass
class PeakRSSI(LLRPParameter):
    """Peak RSSI Parameter (TV encoding)"""
    
    def __init__(self, rssi: int = 0):
        super().__init__(ParameterType.PEAK_RSSI)
        self.rssi = rssi  # Signed 8-bit value
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 1 byte data
        header = self.encode_header(2)
        data = struct.pack('!b', self.rssi)  # signed byte
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 2:
            self.rssi = struct.unpack('!b', data[1:2])[0]
        return 2


@dataclass
class ChannelIndex(LLRPParameter):
    """Channel Index Parameter (TV encoding)"""
    
    def __init__(self, channel_index: int = 0):
        super().__init__(ParameterType.CHANNEL_INDEX)
        self.channel_index = channel_index
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 2 bytes data
        header = self.encode_header(3)
        data = struct.pack('!H', self.channel_index)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 3:
            self.channel_index = struct.unpack('!H', data[1:3])[0]
        return 3


@dataclass
class FirstSeenTimestampUTC(LLRPParameter):
    """First Seen Timestamp UTC Parameter (TV encoding)"""
    
    def __init__(self, microseconds: int = 0):
        super().__init__(ParameterType.FIRST_SEEN_TIMESTAMP_UTC)
        self.microseconds = microseconds
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 8 bytes data
        header = self.encode_header(9)
        data = struct.pack('!Q', self.microseconds)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 9:
            self.microseconds = struct.unpack('!Q', data[1:9])[0]
        return 9


@dataclass
class FirstSeenTimestampUptime(LLRPParameter):
    """First Seen Timestamp Uptime Parameter (TV encoding)"""
    
    def __init__(self, microseconds: int = 0):
        super().__init__(ParameterType.FIRST_SEEN_TIMESTAMP_UPTIME)
        self.microseconds = microseconds
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 8 bytes data
        header = self.encode_header(9)
        data = struct.pack('!Q', self.microseconds)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 9:
            self.microseconds = struct.unpack('!Q', data[1:9])[0]
        return 9


@dataclass
class LastSeenTimestampUTC(LLRPParameter):
    """Last Seen Timestamp UTC Parameter (TV encoding)"""
    
    def __init__(self, microseconds: int = 0):
        super().__init__(ParameterType.LAST_SEEN_TIMESTAMP_UTC)
        self.microseconds = microseconds
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 8 bytes data
        header = self.encode_header(9)
        data = struct.pack('!Q', self.microseconds)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 9:
            self.microseconds = struct.unpack('!Q', data[1:9])[0]
        return 9


@dataclass
class LastSeenTimestampUptime(LLRPParameter):
    """Last Seen Timestamp Uptime Parameter (TV encoding)"""
    
    def __init__(self, microseconds: int = 0):
        super().__init__(ParameterType.LAST_SEEN_TIMESTAMP_UPTIME)
        self.microseconds = microseconds
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 8 bytes data
        header = self.encode_header(9)
        data = struct.pack('!Q', self.microseconds)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 9:
            self.microseconds = struct.unpack('!Q', data[1:9])[0]
        return 9


@dataclass
class TagSeenCount(LLRPParameter):
    """Tag Seen Count Parameter (TV encoding)"""
    
    def __init__(self, tag_count: int = 0):
        super().__init__(ParameterType.TAG_SEEN_COUNT)
        self.tag_count = tag_count
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 2 bytes data
        header = self.encode_header(3)
        data = struct.pack('!H', self.tag_count)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 3:
            self.tag_count = struct.unpack('!H', data[1:3])[0]
        return 3


@dataclass
class AccessSpecID(LLRPParameter):
    """Access Spec ID Parameter (TV encoding)"""
    
    def __init__(self, access_spec_id: int = 0):
        super().__init__(ParameterType.ACCESS_SPEC_ID)
        self.access_spec_id = access_spec_id
    
    def encode(self) -> bytes:
        # TV encoding: 1 byte header + 4 bytes data
        header = self.encode_header(5)
        data = struct.pack('!I', self.access_spec_id)
        return header + data
    
    def decode(self, data: bytes) -> int:
        # TV parameter: data starts right after 1-byte header
        if len(data) >= 5:
            self.access_spec_id = struct.unpack('!I', data[1:5])[0]
        return 5


# Parameter type to class mapping for parsing
PARAMETER_CLASSES = {
    ParameterType.EPC_DATA: EPCData,
    ParameterType.EPC_96: EPC96,
    ParameterType.ROSPEC_ID: ROSpecID,
    ParameterType.SPEC_INDEX: SpecIndex,
    ParameterType.INVENTORY_PARAMETER_SPEC_ID: InventoryParameterSpecID,
    ParameterType.ANTENNA_ID: AntennaID,
    ParameterType.PEAK_RSSI: PeakRSSI,
    ParameterType.CHANNEL_INDEX: ChannelIndex,
    ParameterType.FIRST_SEEN_TIMESTAMP_UTC: FirstSeenTimestampUTC,
    ParameterType.FIRST_SEEN_TIMESTAMP_UPTIME: FirstSeenTimestampUptime,
    ParameterType.LAST_SEEN_TIMESTAMP_UTC: LastSeenTimestampUTC,
    ParameterType.LAST_SEEN_TIMESTAMP_UPTIME: LastSeenTimestampUptime,
    ParameterType.TAG_SEEN_COUNT: TagSeenCount,
    ParameterType.ACCESS_SPEC_ID: AccessSpecID,
}