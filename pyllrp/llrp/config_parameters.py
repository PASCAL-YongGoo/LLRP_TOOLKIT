"""
LLRP Reader Configuration Parameters

Implementation of configuration-related parameters for GET/SET_READER_CONFIG
"""

import struct
from typing import List, Optional
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


# Extend ParameterType with configuration parameters
class ConfigParameterType:
    """Configuration parameter types"""
    ANTENNA_PROPERTIES = 221
    ANTENNA_CONFIGURATION = 222
    RF_RECEIVER = 223
    RF_TRANSMITTER = 224
    GPI_PORT_CURRENT_STATE = 225
    GPO_WRITE_DATA = 226
    KEEPALIVE_SPEC = 227
    GPI_TRIGGER_VALUE = 228
    GPO_TRIGGER_VALUE = 229
    EVENTS_AND_REPORTS = 230


@dataclass
class AntennaProperties(LLRPParameter):
    """Antenna Properties Parameter - Read-only antenna information"""
    
    def __init__(self, antenna_id: int = 0, antenna_connected: bool = False, antenna_gain: int = 0):
        super().__init__(ConfigParameterType.ANTENNA_PROPERTIES)
        self.antenna_id = antenna_id
        self.antenna_connected = antenna_connected
        self.antenna_gain = antenna_gain  # In dBi * 100 (e.g., 600 = 6.0 dBi)
    
    def encode(self) -> bytes:
        """Encode antenna properties"""
        data = struct.pack('!HBH', 
                          self.antenna_id,
                          1 if self.antenna_connected else 0,
                          self.antenna_gain)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode antenna properties"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.ANTENNA_PROPERTIES:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 5:
            self.antenna_id, connected_byte, self.antenna_gain = struct.unpack(
                '!HBH', data[payload_start:payload_start+5])
            self.antenna_connected = bool(connected_byte)
        
        return param_length


@dataclass
class RFReceiver(LLRPParameter):
    """RF Receiver Configuration Parameter"""
    
    def __init__(self, receiver_sensitivity: int = 0):
        super().__init__(ConfigParameterType.RF_RECEIVER)
        self.receiver_sensitivity = receiver_sensitivity  # In dBm * 100
    
    def encode(self) -> bytes:
        """Encode RF receiver configuration"""
        data = struct.pack('!h', self.receiver_sensitivity)  # signed 16-bit
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode RF receiver configuration"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.RF_RECEIVER:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 2:
            self.receiver_sensitivity = struct.unpack('!h', data[payload_start:payload_start+2])[0]
        
        return param_length


@dataclass
class RFTransmitter(LLRPParameter):
    """RF Transmitter Configuration Parameter"""
    
    def __init__(self, hop_table_id: int = 0, channel_index: int = 0, transmit_power: int = 0):
        super().__init__(ConfigParameterType.RF_TRANSMITTER)
        self.hop_table_id = hop_table_id
        self.channel_index = channel_index
        self.transmit_power = transmit_power  # In dBm * 100 (e.g., 2500 = 25.0 dBm)
    
    def encode(self) -> bytes:
        """Encode RF transmitter configuration"""
        data = struct.pack('!HHH', 
                          self.hop_table_id,
                          self.channel_index, 
                          self.transmit_power)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode RF transmitter configuration"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.RF_TRANSMITTER:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 6:
            self.hop_table_id, self.channel_index, self.transmit_power = struct.unpack(
                '!HHH', data[payload_start:payload_start+6])
        
        return param_length
    
    def get_power_dbm(self) -> float:
        """Get transmit power in dBm"""
        return self.transmit_power / 100.0
    
    def set_power_dbm(self, power_dbm: float):
        """Set transmit power in dBm"""
        self.transmit_power = int(power_dbm * 100)


@dataclass
class AntennaConfiguration(LLRPParameter):
    """Antenna Configuration Parameter"""
    
    def __init__(self, antenna_id: int = 0):
        super().__init__(ConfigParameterType.ANTENNA_CONFIGURATION)
        self.antenna_id = antenna_id
        self.rf_receiver: Optional[RFReceiver] = None
        self.rf_transmitter: Optional[RFTransmitter] = None
        self.antenna_properties: Optional[AntennaProperties] = None
    
    def encode(self) -> bytes:
        """Encode antenna configuration"""
        # Start with antenna ID
        data = struct.pack('!H', self.antenna_id)
        
        # Add sub-parameters
        if self.rf_receiver:
            data += self.rf_receiver.encode()
        
        if self.rf_transmitter:
            data += self.rf_transmitter.encode()
        
        if self.antenna_properties:
            data += self.antenna_properties.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode antenna configuration"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.ANTENNA_CONFIGURATION:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 2:
            self.antenna_id = struct.unpack('!H', data[payload_start:payload_start+2])[0]
        
        # Parse sub-parameters
        offset = payload_start + 2
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == ConfigParameterType.RF_RECEIVER:
                self.rf_receiver = RFReceiver()
                self.rf_receiver.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == ConfigParameterType.RF_TRANSMITTER:
                self.rf_transmitter = RFTransmitter()
                self.rf_transmitter.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == ConfigParameterType.ANTENNA_PROPERTIES:
                self.antenna_properties = AntennaProperties()
                self.antenna_properties.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length
    
    def set_transmit_power(self, power_dbm: float):
        """Set transmit power for this antenna"""
        if not self.rf_transmitter:
            self.rf_transmitter = RFTransmitter()
        self.rf_transmitter.set_power_dbm(power_dbm)
    
    def get_transmit_power(self) -> Optional[float]:
        """Get transmit power for this antenna"""
        if self.rf_transmitter:
            return self.rf_transmitter.get_power_dbm()
        return None


@dataclass
class EventsAndReports(LLRPParameter):
    """Events and Reports Configuration Parameter"""
    
    def __init__(self):
        super().__init__(ConfigParameterType.EVENTS_AND_REPORTS)
        self.hold_events_and_reports_upon_reconnect = False
    
    def encode(self) -> bytes:
        """Encode events and reports configuration"""
        data = struct.pack('!B', 1 if self.hold_events_and_reports_upon_reconnect else 0)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode events and reports configuration"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.EVENTS_AND_REPORTS:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 1:
            hold_byte = struct.unpack('!B', data[payload_start:payload_start+1])[0]
            self.hold_events_and_reports_upon_reconnect = bool(hold_byte)
        
        return param_length


@dataclass
class KeepaliveSpec(LLRPParameter):
    """Keepalive Specification Parameter"""
    
    def __init__(self, keepalive_trigger_type: int = 0, periodic_trigger_value: int = 0):
        super().__init__(ConfigParameterType.KEEPALIVE_SPEC)
        self.keepalive_trigger_type = keepalive_trigger_type  # 0=Null, 1=Periodic
        self.periodic_trigger_value = periodic_trigger_value  # In milliseconds
    
    def encode(self) -> bytes:
        """Encode keepalive specification"""
        data = struct.pack('!BI', self.keepalive_trigger_type, self.periodic_trigger_value)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode keepalive specification"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ConfigParameterType.KEEPALIVE_SPEC:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 5:
            self.keepalive_trigger_type, self.periodic_trigger_value = struct.unpack(
                '!BI', data[payload_start:payload_start+5])
        
        return param_length


# Configuration parameter registry
CONFIG_PARAMETER_CLASSES = {
    ConfigParameterType.ANTENNA_PROPERTIES: AntennaProperties,
    ConfigParameterType.ANTENNA_CONFIGURATION: AntennaConfiguration,
    ConfigParameterType.RF_RECEIVER: RFReceiver,
    ConfigParameterType.RF_TRANSMITTER: RFTransmitter,
    ConfigParameterType.EVENTS_AND_REPORTS: EventsAndReports,
    ConfigParameterType.KEEPALIVE_SPEC: KeepaliveSpec,
}