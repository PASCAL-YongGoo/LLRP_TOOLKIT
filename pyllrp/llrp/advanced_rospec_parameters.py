"""
Advanced ROSpec Parameters

Implementation of advanced ROSpec-related parameters for sophisticated RFID operations
"""

import struct
from typing import List, Optional
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


# Extend ParameterType with advanced ROSpec parameters
class AdvancedROSpecParameterType:
    """Advanced ROSpec parameter types"""
    PERIODIC_TRIGGER_VALUE = 188
    GPI_TRIGGER_VALUE = 189
    TAG_OBSERVATION_TRIGGER = 190
    RF_SURVEY_SPEC = 191
    LOOP_SPEC = 192
    
    # AISpec trigger parameters
    TAG_OBSERVATION_TRIGGER_VALUE = 193
    
    # Advanced stop triggers
    GPI_TRIGGER_VALUE_STOP = 194
    TAG_OBSERVATION_TRIGGER_STOP = 195
    
    # RF Control and Survey
    RF_SURVEY_SPEC_STOP_TRIGGER = 196
    

@dataclass
class PeriodicTriggerValue(LLRPParameter):
    """Periodic Trigger Value Parameter - For time-based ROSpec starting"""
    
    def __init__(self, offset: int = 0, period: int = 0):
        super().__init__(AdvancedROSpecParameterType.PERIODIC_TRIGGER_VALUE)
        self.offset = offset  # Milliseconds to wait before first trigger
        self.period = period  # Period between triggers in milliseconds (0 = single shot)
        self.utc_timestamp = None  # Optional absolute start time
    
    def encode(self) -> bytes:
        """Encode periodic trigger value"""
        data = struct.pack('!II', self.offset, self.period)
        
        # Add UTC timestamp if present
        if self.utc_timestamp:
            data += self.utc_timestamp.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode periodic trigger value"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.PERIODIC_TRIGGER_VALUE:
            return 0
        
        offset = header_len
        if len(data) >= offset + 8:
            self.offset, self.period = struct.unpack('!II', data[offset:offset+8])
            offset += 8
        
        # Parse sub-parameters (UTC timestamp if present)
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == ParameterType.UTC_TIMESTAMP:
                from .parameters import UTCTimestamp
                self.utc_timestamp = UTCTimestamp()
                self.utc_timestamp.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


@dataclass
class GPITriggerValue(LLRPParameter):
    """GPI Trigger Value Parameter - For GPIO-based ROSpec triggering"""
    
    def __init__(self, gpi_port_num: int = 1, gpi_event: bool = True, timeout: int = 0):
        super().__init__(AdvancedROSpecParameterType.GPI_TRIGGER_VALUE)
        self.gpi_port_num = gpi_port_num  # GPI port number
        self.gpi_event = gpi_event  # True=High, False=Low
        self.timeout = timeout  # Timeout in milliseconds (0 = no timeout)
    
    def encode(self) -> bytes:
        """Encode GPI trigger value"""
        data = struct.pack('!HBI', 
                          self.gpi_port_num,
                          1 if self.gpi_event else 0,
                          self.timeout)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode GPI trigger value"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.GPI_TRIGGER_VALUE:
            return 0
        
        offset = header_len
        if len(data) >= offset + 7:
            self.gpi_port_num, gpi_event_byte, self.timeout = struct.unpack('!HBI', data[offset:offset+7])
            self.gpi_event = bool(gpi_event_byte)
        
        return param_length


@dataclass
class TagObservationTrigger(LLRPParameter):
    """Tag Observation Trigger Parameter - Trigger based on tag observation patterns"""
    
    def __init__(self, trigger_type: int = 1, num_tags: int = 1, 
                 num_attempts: int = 0, timeout: int = 0):
        super().__init__(AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER)
        self.trigger_type = trigger_type  # 1=Upon_Seeing_N_Tags_Or_Timeout
        self.num_tags = num_tags  # Number of unique tags to see
        self.num_attempts = num_attempts  # Number of attempts (0 = infinite)
        self.timeout = timeout  # Timeout in milliseconds (0 = no timeout)
        self.enable_rospec_id = 0  # ROSpec to enable when triggered
    
    def encode(self) -> bytes:
        """Encode tag observation trigger"""
        data = struct.pack('!BHHII',
                          self.trigger_type,
                          self.num_tags,
                          self.num_attempts,
                          self.timeout,
                          self.enable_rospec_id)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode tag observation trigger"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER:
            return 0
        
        offset = header_len
        if len(data) >= offset + 13:
            self.trigger_type, self.num_tags, self.num_attempts, self.timeout, self.enable_rospec_id = struct.unpack(
                '!BHHII', data[offset:offset+13])
        
        return param_length


@dataclass
class RFSurveySpec(LLRPParameter):
    """RF Survey Spec Parameter - For RF environment surveying"""
    
    def __init__(self, antenna_id: int = 0, start_frequency: int = 902750, 
                 end_frequency: int = 927250, duration: int = 1000):
        super().__init__(AdvancedROSpecParameterType.RF_SURVEY_SPEC)
        self.antenna_id = antenna_id  # 0 = all antennas
        self.start_frequency = start_frequency  # Start frequency in kHz
        self.end_frequency = end_frequency  # End frequency in kHz  
        self.duration = duration  # Duration per frequency in milliseconds
        self.rf_survey_spec_stop_trigger = None
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode RF survey spec"""
        data = struct.pack('!HIII',
                          self.antenna_id,
                          self.start_frequency,
                          self.end_frequency,
                          self.duration)
        
        # Add stop trigger if present
        if self.rf_survey_spec_stop_trigger:
            data += self.rf_survey_spec_stop_trigger.encode()
        
        # Add custom parameters
        for custom in self.custom_parameters:
            data += custom.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode RF survey spec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.RF_SURVEY_SPEC:
            return 0
        
        offset = header_len
        if len(data) >= offset + 14:
            self.antenna_id, self.start_frequency, self.end_frequency, self.duration = struct.unpack(
                '!HIII', data[offset:offset+14])
            offset += 14
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            # Handle RF survey stop triggers and custom parameters
            offset += sub_param_length
        
        return param_length


@dataclass
class LoopSpec(LLRPParameter):
    """Loop Spec Parameter - For repeated ROSpec execution"""
    
    def __init__(self, loop_count: int = 0):
        super().__init__(AdvancedROSpecParameterType.LOOP_SPEC)
        self.loop_count = loop_count  # Number of loops (0 = infinite)
    
    def encode(self) -> bytes:
        """Encode loop spec"""
        data = struct.pack('!I', self.loop_count)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode loop spec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.LOOP_SPEC:
            return 0
        
        offset = header_len
        if len(data) >= offset + 4:
            self.loop_count = struct.unpack('!I', data[offset:offset+4])[0]
        
        return param_length


@dataclass
class GPITriggerValueStop(LLRPParameter):
    """GPI Trigger Value Stop Parameter - For GPI-based ROSpec stopping"""
    
    def __init__(self, gpi_port_num: int = 1, gpi_event: bool = False, timeout: int = 0):
        super().__init__(AdvancedROSpecParameterType.GPI_TRIGGER_VALUE_STOP)
        self.gpi_port_num = gpi_port_num
        self.gpi_event = gpi_event  # Event to trigger stop
        self.timeout = timeout  # Timeout in milliseconds
    
    def encode(self) -> bytes:
        """Encode GPI trigger value stop"""
        data = struct.pack('!HBI',
                          self.gpi_port_num,
                          1 if self.gpi_event else 0,
                          self.timeout)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode GPI trigger value stop"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.GPI_TRIGGER_VALUE_STOP:
            return 0
        
        offset = header_len
        if len(data) >= offset + 7:
            self.gpi_port_num, gpi_event_byte, self.timeout = struct.unpack('!HBI', data[offset:offset+7])
            self.gpi_event = bool(gpi_event_byte)
        
        return param_length


@dataclass
class TagObservationTriggerStop(LLRPParameter):
    """Tag Observation Trigger Stop Parameter - Stop based on tag observations"""
    
    def __init__(self, trigger_type: int = 1, num_tags: int = 1,
                 num_attempts: int = 0, timeout: int = 0):
        super().__init__(AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER_STOP)
        self.trigger_type = trigger_type
        self.num_tags = num_tags
        self.num_attempts = num_attempts
        self.timeout = timeout
    
    def encode(self) -> bytes:
        """Encode tag observation trigger stop"""
        data = struct.pack('!BHHI',
                          self.trigger_type,
                          self.num_tags,
                          self.num_attempts,
                          self.timeout)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode tag observation trigger stop"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER_STOP:
            return 0
        
        offset = header_len
        if len(data) >= offset + 9:
            self.trigger_type, self.num_tags, self.num_attempts, self.timeout = struct.unpack(
                '!BHHI', data[offset:offset+9])
        
        return param_length


# Enhanced ROSpec classes that use advanced triggers

@dataclass
class EnhancedROSpecStartTrigger(LLRPParameter):
    """Enhanced ROSpec Start Trigger with advanced trigger support"""
    
    def __init__(self, trigger_type: int = 0):
        super().__init__(ParameterType.ROSPEC_START_TRIGGER)
        self.trigger_type = trigger_type  # 0=Null, 1=Immediate, 2=Periodic, 3=GPI
        self.periodic_trigger_value = None
        self.gpi_trigger_value = None
    
    def encode(self) -> bytes:
        """Encode enhanced ROSpec start trigger"""
        data = struct.pack('!B', self.trigger_type)
        
        # Add trigger-specific parameters
        if self.trigger_type == 2 and self.periodic_trigger_value:
            data += self.periodic_trigger_value.encode()
        elif self.trigger_type == 3 and self.gpi_trigger_value:
            data += self.gpi_trigger_value.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode enhanced ROSpec start trigger"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.ROSPEC_START_TRIGGER:
            return 0
        
        offset = header_len
        if len(data) >= offset + 1:
            self.trigger_type = struct.unpack('!B', data[offset:offset+1])[0]
            offset += 1
        
        # Parse sub-parameters based on trigger type
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == AdvancedROSpecParameterType.PERIODIC_TRIGGER_VALUE:
                self.periodic_trigger_value = PeriodicTriggerValue()
                self.periodic_trigger_value.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == AdvancedROSpecParameterType.GPI_TRIGGER_VALUE:
                self.gpi_trigger_value = GPITriggerValue()
                self.gpi_trigger_value.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


@dataclass
class EnhancedROSpecStopTrigger(LLRPParameter):
    """Enhanced ROSpec Stop Trigger with advanced trigger support"""
    
    def __init__(self, trigger_type: int = 0, duration_ms: int = 0):
        super().__init__(ParameterType.ROSPEC_STOP_TRIGGER)
        self.trigger_type = trigger_type  # 0=Null, 1=Duration, 2=GPI, 3=Tag_Observation
        self.duration_ms = duration_ms
        self.gpi_trigger_value = None
        self.tag_observation_trigger = None
    
    def encode(self) -> bytes:
        """Encode enhanced ROSpec stop trigger"""
        data = struct.pack('!BI', self.trigger_type, self.duration_ms)
        
        # Add trigger-specific parameters
        if self.trigger_type == 2 and self.gpi_trigger_value:
            data += self.gpi_trigger_value.encode()
        elif self.trigger_type == 3 and self.tag_observation_trigger:
            data += self.tag_observation_trigger.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode enhanced ROSpec stop trigger"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.ROSPEC_STOP_TRIGGER:
            return 0
        
        offset = header_len
        if len(data) >= offset + 5:
            self.trigger_type, self.duration_ms = struct.unpack('!BI', data[offset:offset+5])
            offset += 5
        
        # Parse sub-parameters based on trigger type
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == AdvancedROSpecParameterType.GPI_TRIGGER_VALUE_STOP:
                self.gpi_trigger_value = GPITriggerValueStop()
                self.gpi_trigger_value.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER_STOP:
                self.tag_observation_trigger = TagObservationTriggerStop()
                self.tag_observation_trigger.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


# Advanced ROSpec parameter registry
ADVANCED_ROSPEC_PARAMETER_CLASSES = {
    AdvancedROSpecParameterType.PERIODIC_TRIGGER_VALUE: PeriodicTriggerValue,
    AdvancedROSpecParameterType.GPI_TRIGGER_VALUE: GPITriggerValue,
    AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER: TagObservationTrigger,
    AdvancedROSpecParameterType.RF_SURVEY_SPEC: RFSurveySpec,
    AdvancedROSpecParameterType.LOOP_SPEC: LoopSpec,
    AdvancedROSpecParameterType.GPI_TRIGGER_VALUE_STOP: GPITriggerValueStop,
    AdvancedROSpecParameterType.TAG_OBSERVATION_TRIGGER_STOP: TagObservationTriggerStop,
}