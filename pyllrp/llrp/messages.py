"""
LLRP Message Definitions
"""

import struct
from typing import Optional, List, Any
from dataclasses import dataclass
from .protocol import (
    LLRPMessage, LLRPParameter, LLRPStatus,
    MessageType, ParameterType, AirProtocol
)


# ROSpec related parameters

@dataclass
class ROSpec(LLRPParameter):
    """ROSpec Parameter"""
    
    def __init__(self, rospec_id: int = 1, priority: int = 0, 
                 current_state: int = 0):
        super().__init__(ParameterType.ROSPEC)
        self.rospec_id = rospec_id
        self.priority = priority
        self.current_state = current_state
        self.ro_boundary_spec = None
        self.spec_parameters = []
        self.ro_report_spec = None
    
    def encode(self) -> bytes:
        # Encode fixed fields
        data = struct.pack('!IBB', self.rospec_id, self.priority, self.current_state)
        
        # Encode sub-parameters
        if self.ro_boundary_spec:
            data += self.ro_boundary_spec.encode()
        
        for spec in self.spec_parameters:
            data += spec.encode()
            
        if self.ro_report_spec:
            data += self.ro_report_spec.encode()
        
        # Add header
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class ROBoundarySpec(LLRPParameter):
    """ROBoundarySpec Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.RO_BOUNDARY_SPEC)
        self.rospec_start_trigger = None
        self.rospec_stop_trigger = None
    
    def encode(self) -> bytes:
        data = b''
        
        if self.rospec_start_trigger:
            data += self.rospec_start_trigger.encode()
        if self.rospec_stop_trigger:
            data += self.rospec_stop_trigger.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class ROSpecStartTrigger(LLRPParameter):
    """ROSpec Start Trigger"""
    
    def __init__(self, trigger_type: int = 0, gpi_event=None, periodic=None):
        super().__init__(ParameterType.ROSPEC_START_TRIGGER)
        self.trigger_type = trigger_type  # 0=Null, 1=Immediate, 2=Periodic, 3=GPI
        self.gpi_event = gpi_event
        self.periodic = periodic
    
    def encode(self) -> bytes:
        data = struct.pack('!B', self.trigger_type)
        
        if self.trigger_type == 2 and self.periodic:
            # Add periodic trigger parameters
            data += struct.pack('!II', self.periodic['offset'], self.periodic['period'])
        elif self.trigger_type == 3 and self.gpi_event:
            # Add GPI trigger parameters
            data += self.gpi_event.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class ROSpecStopTrigger(LLRPParameter):
    """ROSpec Stop Trigger"""
    
    def __init__(self, trigger_type: int = 0, duration_ms: int = 0):
        super().__init__(ParameterType.ROSPEC_STOP_TRIGGER)
        self.trigger_type = trigger_type  # 0=Null, 1=Duration, 2=GPI
        self.duration_ms = duration_ms
    
    def encode(self) -> bytes:
        data = struct.pack('!B', self.trigger_type)
        
        if self.trigger_type == 1:
            data += struct.pack('!I', self.duration_ms)
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class AISpec(LLRPParameter):
    """Antenna Inventory Spec"""
    
    def __init__(self, antenna_ids: List[int] = None):
        super().__init__(ParameterType.AI_SPEC)
        self.antenna_ids = antenna_ids or [0]  # 0 = all antennas
        self.ai_spec_stop_trigger = None
        self.inventory_parameter_specs = []
    
    def encode(self) -> bytes:
        # Encode antenna count and IDs
        data = struct.pack('!H', len(self.antenna_ids))
        for antenna_id in self.antenna_ids:
            data += struct.pack('!H', antenna_id)
        
        # Add stop trigger
        if self.ai_spec_stop_trigger:
            data += self.ai_spec_stop_trigger.encode()
        
        # Add inventory specs
        for spec in self.inventory_parameter_specs:
            data += spec.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class AISpecStopTrigger(LLRPParameter):
    """AISpec Stop Trigger"""
    
    def __init__(self, trigger_type: int = 0, duration_ms: int = 0,
                 tag_observation_count: int = 0):
        super().__init__(ParameterType.AI_SPEC_STOP_TRIGGER)
        self.trigger_type = trigger_type  # 0=Null, 1=Duration, 2=GPI, 3=TagObservation
        self.duration_ms = duration_ms
        self.tag_observation_count = tag_observation_count
    
    def encode(self) -> bytes:
        data = struct.pack('!B', self.trigger_type)
        
        if self.trigger_type == 1:
            data += struct.pack('!I', self.duration_ms)
        elif self.trigger_type == 3:
            data += struct.pack('!I', self.tag_observation_count)
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class InventoryParameterSpec(LLRPParameter):
    """Inventory Parameter Specification"""
    
    def __init__(self, spec_id: int = 1, protocol_id: int = AirProtocol.EPC_GLOBAL_CLASS1_GEN2):
        super().__init__(ParameterType.INVENTORY_PARAMETER_SPEC)
        self.spec_id = spec_id
        self.protocol_id = protocol_id
        self.antenna_configuration = []
    
    def encode(self) -> bytes:
        data = struct.pack('!HB', self.spec_id, self.protocol_id)
        
        # Add antenna configurations
        for config in self.antenna_configuration:
            data += config.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class ROReportSpec(LLRPParameter):
    """RO Report Specification"""
    
    def __init__(self, trigger: int = 1, n_value: int = 0):
        super().__init__(ParameterType.RO_REPORT_SPEC)
        self.trigger = trigger  # 0=None, 1=EndOfROSpec, 2=EndOfAISpec, 3=NTagsOrEndOfROSpec
        self.n_value = n_value  # Number of tags for trigger type 3
        self.tag_report_content_selector = None
    
    def encode(self) -> bytes:
        data = struct.pack('!B', self.trigger)
        
        if self.trigger == 3:
            data += struct.pack('!H', self.n_value)
        
        if self.tag_report_content_selector:
            data += self.tag_report_content_selector.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data


@dataclass
class TagReportContentSelector(LLRPParameter):
    """Tag Report Content Selector"""
    
    def __init__(self):
        super().__init__(ParameterType.TAG_REPORT_CONTENT_SELECTOR)
        self.enable_rospec_id = True
        self.enable_spec_index = True
        self.enable_inventory_parameter_spec_id = True
        self.enable_antenna_id = True
        self.enable_channel_index = True
        self.enable_peak_rssi = True
        self.enable_first_seen_timestamp = True
        self.enable_last_seen_timestamp = True
        self.enable_tag_seen_count = True
        self.enable_access_spec_id = False
    
    def encode(self) -> bytes:
        # Pack all boolean flags into 2 bytes
        flags = 0
        if self.enable_rospec_id: flags |= 0x8000
        if self.enable_spec_index: flags |= 0x4000
        if self.enable_inventory_parameter_spec_id: flags |= 0x2000
        if self.enable_antenna_id: flags |= 0x1000
        if self.enable_channel_index: flags |= 0x0800
        if self.enable_peak_rssi: flags |= 0x0400
        if self.enable_first_seen_timestamp: flags |= 0x0200
        if self.enable_last_seen_timestamp: flags |= 0x0100
        if self.enable_tag_seen_count: flags |= 0x0080
        if self.enable_access_spec_id: flags |= 0x0040
        
        data = struct.pack('!H', flags)
        header = self.encode_header(4 + len(data))
        return header + data


# ROSpec Messages

@dataclass
class AddROSpec(LLRPMessage):
    """ADD_ROSPEC Message"""
    
    def __init__(self, msg_id: int = 0, rospec: ROSpec = None):
        super().__init__(MessageType.ADD_ROSPEC, msg_id)
        self.rospec = rospec
        if rospec:
            self.parameters = [rospec]
    
    def decode_parameters(self, data: bytes):
        # Decode ROSpec parameter
        pass


@dataclass
class AddROSpecResponse(LLRPMessage):
    """ADD_ROSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ADD_ROSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        # Decode LLRPStatus
        if len(data) >= 8:
            self.llrp_status = LLRPStatus()
            self.llrp_status.decode(data)


@dataclass
class EnableROSpec(LLRPMessage):
    """ENABLE_ROSPEC Message"""
    
    def __init__(self, msg_id: int = 0, rospec_id: int = 0):
        super().__init__(MessageType.ENABLE_ROSPEC, msg_id)
        self.rospec_id = rospec_id
    
    def encode(self) -> bytes:
        data = struct.pack('!I', self.rospec_id)
        self.header.message_length = 14  # 10 header + 4 bytes
        return self.header.pack() + data
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 4:
            self.rospec_id = struct.unpack('!I', data[:4])[0]


@dataclass
class EnableROSpecResponse(LLRPMessage):
    """ENABLE_ROSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ENABLE_ROSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 8:
            self.llrp_status = LLRPStatus()
            self.llrp_status.decode(data)


@dataclass
class StartROSpec(LLRPMessage):
    """START_ROSPEC Message"""
    
    def __init__(self, msg_id: int = 0, rospec_id: int = 0):
        super().__init__(MessageType.START_ROSPEC, msg_id)
        self.rospec_id = rospec_id
    
    def encode(self) -> bytes:
        data = struct.pack('!I', self.rospec_id)
        self.header.message_length = 14
        return self.header.pack() + data
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 4:
            self.rospec_id = struct.unpack('!I', data[:4])[0]


@dataclass
class StartROSpecResponse(LLRPMessage):
    """START_ROSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.START_ROSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 8:
            self.llrp_status = LLRPStatus()
            self.llrp_status.decode(data)


@dataclass  
class StopROSpec(LLRPMessage):
    """STOP_ROSPEC Message"""
    
    def __init__(self, msg_id: int = 0, rospec_id: int = 0):
        super().__init__(MessageType.STOP_ROSPEC, msg_id)
        self.rospec_id = rospec_id
    
    def encode(self) -> bytes:
        data = struct.pack('!I', self.rospec_id)
        self.header.message_length = 14
        return self.header.pack() + data
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 4:
            self.rospec_id = struct.unpack('!I', data[:4])[0]


@dataclass
class StopROSpecResponse(LLRPMessage):
    """STOP_ROSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.STOP_ROSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 8:
            self.llrp_status = LLRPStatus()
            self.llrp_status.decode(data)


@dataclass
class DeleteROSpec(LLRPMessage):
    """DELETE_ROSPEC Message"""
    
    def __init__(self, msg_id: int = 0, rospec_id: int = 0):
        super().__init__(MessageType.DELETE_ROSPEC, msg_id)
        self.rospec_id = rospec_id  # 0 = delete all
    
    def encode(self) -> bytes:
        data = struct.pack('!I', self.rospec_id)
        self.header.message_length = 14
        return self.header.pack() + data
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 4:
            self.rospec_id = struct.unpack('!I', data[:4])[0]


@dataclass
class DeleteROSpecResponse(LLRPMessage):
    """DELETE_ROSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.DELETE_ROSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        if len(data) >= 8:
            self.llrp_status = LLRPStatus()
            self.llrp_status.decode(data)


# Tag Report Messages  

@dataclass  
class TagReportData(LLRPParameter):
    """Tag Report Data Parameter - Complete Implementation"""
    
    def __init__(self):
        super().__init__(ParameterType.TAG_REPORT_DATA)
        # EPC Information (mandatory)
        self.epc_parameter = None  # EPCData or EPC96
        
        # Optional fields
        self.rospec_id = None
        self.spec_index = None
        self.inventory_parameter_spec_id = None
        self.antenna_id = None
        self.peak_rssi = None
        self.channel_index = None
        self.first_seen_timestamp_utc = None
        self.first_seen_timestamp_uptime = None
        self.last_seen_timestamp_utc = None
        self.last_seen_timestamp_uptime = None
        self.tag_seen_count = None
        self.access_spec_id = None
        
    def decode(self, data: bytes) -> int:
        """Decode tag report data with complete parameter parsing using new header system"""
        from .parameters import PARAMETER_CLASSES
        from .protocol import LLRPParameter
        
        if len(data) < 4:
            return 0
            
        # Parse TagReportData header
        param_type, total_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.TAG_REPORT_DATA:
            return 0
            
        offset = header_len  # Start after TagReportData header
        
        # Parse all sub-parameters
        while offset < total_length and offset < len(data):
            # Parse sub-parameter header
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
                
            # Validate parameter bounds
            if offset + sub_param_length > len(data) or offset + sub_param_length > total_length:
                print(f"Warning: Parameter {sub_param_type} extends beyond bounds, skipping")
                break
            
            # Extract parameter data
            param_data = data[offset:offset+sub_param_length]
            
            # Parse known parameter types
            if sub_param_type in PARAMETER_CLASSES:
                param_obj = PARAMETER_CLASSES[sub_param_type]()
                try:
                    consumed = param_obj.decode(param_data)
                    self._assign_parameter(param_obj)
                except Exception as e:
                    print(f"Warning: Failed to decode parameter {sub_param_type}: {e}")
            else:
                print(f"Debug: Unknown parameter type {sub_param_type}, skipping")
                    
            offset += sub_param_length
            
        return total_length
    
    
    def _assign_parameter(self, param_obj):
        """Assign parsed parameter to appropriate field"""
        from .parameters import (
            EPCData, EPC96, ROSpecID, SpecIndex, InventoryParameterSpecID,
            AntennaID, PeakRSSI, ChannelIndex, FirstSeenTimestampUTC,
            FirstSeenTimestampUptime, LastSeenTimestampUTC, 
            LastSeenTimestampUptime, TagSeenCount, AccessSpecID
        )
        
        if isinstance(param_obj, (EPCData, EPC96)):
            self.epc_parameter = param_obj
        elif isinstance(param_obj, ROSpecID):
            self.rospec_id = param_obj.rospec_id
        elif isinstance(param_obj, SpecIndex):
            self.spec_index = param_obj.spec_index
        elif isinstance(param_obj, InventoryParameterSpecID):
            self.inventory_parameter_spec_id = param_obj.spec_id
        elif isinstance(param_obj, AntennaID):
            self.antenna_id = param_obj.antenna_id
        elif isinstance(param_obj, PeakRSSI):
            self.peak_rssi = param_obj.rssi
        elif isinstance(param_obj, ChannelIndex):
            self.channel_index = param_obj.channel_index
        elif isinstance(param_obj, FirstSeenTimestampUTC):
            self.first_seen_timestamp_utc = param_obj.microseconds
        elif isinstance(param_obj, FirstSeenTimestampUptime):
            self.first_seen_timestamp_uptime = param_obj.microseconds
        elif isinstance(param_obj, LastSeenTimestampUTC):
            self.last_seen_timestamp_utc = param_obj.microseconds
        elif isinstance(param_obj, LastSeenTimestampUptime):
            self.last_seen_timestamp_uptime = param_obj.microseconds
        elif isinstance(param_obj, TagSeenCount):
            self.tag_seen_count = param_obj.tag_count
        elif isinstance(param_obj, AccessSpecID):
            self.access_spec_id = param_obj.access_spec_id
    
    def get_epc_hex(self) -> Optional[str]:
        """Get EPC as hex string"""
        if self.epc_parameter:
            return self.epc_parameter.get_epc_hex()
        return None
    
    def get_first_seen_timestamp(self) -> Optional[int]:
        """Get first seen timestamp (prefer UTC over uptime)"""
        return self.first_seen_timestamp_utc or self.first_seen_timestamp_uptime
    
    def get_last_seen_timestamp(self) -> Optional[int]:
        """Get last seen timestamp (prefer UTC over uptime)"""
        return self.last_seen_timestamp_utc or self.last_seen_timestamp_uptime


@dataclass
class ROAccessReport(LLRPMessage):
    """RO_ACCESS_REPORT Message - Complete Implementation"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.RO_ACCESS_REPORT, msg_id)
        self.tag_report_data: List[TagReportData] = []
    
    def decode_parameters(self, data: bytes):
        """Decode tag reports with robust parsing"""
        offset = 0
        
        while offset < len(data):
            try:
                if offset + 4 > len(data):
                    break
                
                # Read parameter header
                first_word = struct.unpack('!H', data[offset:offset+2])[0]
                
                # Check if TV or TLV parameter
                if first_word & 0x8000:  # TV parameter
                    param_type = first_word & 0x7F
                    # TV parameters have fixed lengths, most are not used in RO_ACCESS_REPORT
                    param_len = 4  # Default, adjust as needed
                else:  # TLV parameter
                    param_type = first_word & 0x3FF
                    if offset + 4 > len(data):
                        break
                    param_len = struct.unpack('!H', data[offset+2:offset+4])[0]
                
                # Validate parameter length
                if param_len < 4 or offset + param_len > len(data):
                    # Skip invalid parameter
                    offset += 4
                    continue
                
                # Parse TagReportData parameters
                if param_type == ParameterType.TAG_REPORT_DATA:
                    tag_data = TagReportData()
                    consumed = tag_data.decode(data[offset:offset+param_len])
                    if consumed > 0:
                        self.tag_report_data.append(tag_data)
                        offset += consumed
                    else:
                        offset += param_len
                else:
                    # Skip unknown parameters
                    offset += param_len
                    
            except Exception as e:
                # If parsing fails, skip to next possible parameter
                print(f"Warning: Failed to parse parameter at offset {offset}: {e}")
                offset += 4
                
    def get_tag_count(self) -> int:
        """Get total number of tag reports"""
        return len(self.tag_report_data)
    
    def get_unique_epcs(self) -> List[str]:
        """Get list of unique EPCs from all tag reports"""
        epcs = set()
        for tag_data in self.tag_report_data:
            epc = tag_data.get_epc_hex()
            if epc:
                epcs.add(epc)
        return list(epcs)
    
    def get_tags_by_antenna(self, antenna_id: int) -> List[TagReportData]:
        """Get tag reports from specific antenna"""
        return [tag for tag in self.tag_report_data 
                if tag.antenna_id == antenna_id]


@dataclass
class ErrorMessage(LLRPMessage):
    """ERROR_MESSAGE - Sent when reader encounters an error"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ERROR_MESSAGE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode error message parameters"""
        from .protocol import LLRPParameter
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                from .protocol import LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length
    
    def get_error_info(self) -> dict:
        """Get error information as dictionary"""
        if not self.llrp_status:
            return {'error': 'Unknown error'}
            
        return {
            'status_code': self.llrp_status.status_code,
            'error_description': self.llrp_status.error_description,
            'message_id': self.header.message_id
        }


@dataclass
class KeepAlive(LLRPMessage):
    """KEEPALIVE Message - Reader heartbeat"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.KEEPALIVE, msg_id)
    
    def decode_parameters(self, data: bytes):
        """KEEPALIVE has no parameters"""
        pass


@dataclass
class KeepAliveAck(LLRPMessage):
    """KEEPALIVE_ACK Message - Response to reader heartbeat"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.KEEPALIVE_ACK, msg_id)
    
    def decode_parameters(self, data: bytes):
        """KEEPALIVE_ACK has no parameters"""
        pass


@dataclass
class CloseConnection(LLRPMessage):
    """CLOSE_CONNECTION Message - Graceful connection close"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.CLOSE_CONNECTION, msg_id)
    
    def decode_parameters(self, data: bytes):
        """CLOSE_CONNECTION has no parameters"""
        pass


@dataclass
class CloseConnectionResponse(LLRPMessage):
    """CLOSE_CONNECTION_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.CLOSE_CONNECTION_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


# Events and Reports Message

@dataclass
class EnableEventsAndReports(LLRPMessage):
    """ENABLE_EVENTS_AND_REPORTS Message - Enable reader event notifications"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ENABLE_EVENTS_AND_REPORTS, msg_id)
    
    def decode_parameters(self, data: bytes):
        """ENABLE_EVENTS_AND_REPORTS has no parameters"""
        pass


@dataclass
class ReaderEventNotificationData(LLRPParameter):
    """Reader Event Notification Data Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.READER_EVENT_NOTIFICATION_DATA)
        self.timestamp = None
        self.connection_attempt_event = None
        self.connection_close_event = None
        self.llrp_status = None
        self.antenna_event = None
        self.reader_exception_event = None
        self.rospec_event = None
        self.ai_spec_event = None
        self.report_buffer_level_warning_event = None
        self.report_buffer_overflow_error_event = None
    
    def encode(self) -> bytes:
        """Encode reader event notification data"""
        data = b''
        
        # Add timestamp if present
        if self.timestamp:
            data += self.timestamp.encode()
        
        # Add events if present
        if self.connection_attempt_event:
            data += self.connection_attempt_event.encode()
        if self.connection_close_event:
            data += self.connection_close_event.encode()
        if self.llrp_status:
            data += self.llrp_status.encode()
        if self.antenna_event:
            data += self.antenna_event.encode()
        if self.reader_exception_event:
            data += self.reader_exception_event.encode()
        if self.rospec_event:
            data += self.rospec_event.encode()
        if self.ai_spec_event:
            data += self.ai_spec_event.encode()
        if self.report_buffer_level_warning_event:
            data += self.report_buffer_level_warning_event.encode()
        if self.report_buffer_overflow_error_event:
            data += self.report_buffer_overflow_error_event.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode reader event notification data"""
        from .protocol import LLRPParameter, LLRPStatus
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.READER_EVENT_NOTIFICATION_DATA:
            return 0
        
        offset = header_len
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            param_data = data[offset:offset+sub_param_length]
            
            if sub_param_type == ParameterType.UTC_TIMESTAMP:
                from .parameters import UTCTimestamp
                self.timestamp = UTCTimestamp()
                self.timestamp.decode(param_data)
            elif sub_param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                self.llrp_status.decode(param_data)
            elif sub_param_type == ParameterType.CONNECTION_ATTEMPT_EVENT:
                self.connection_attempt_event = ConnectionAttemptEvent()
                self.connection_attempt_event.decode(param_data)
            elif sub_param_type == ParameterType.CONNECTION_CLOSE_EVENT:
                self.connection_close_event = ConnectionCloseEvent()
                self.connection_close_event.decode(param_data)
            elif sub_param_type == ParameterType.ANTENNA_EVENT:
                self.antenna_event = AntennaEvent()
                self.antenna_event.decode(param_data)
            elif sub_param_type == ParameterType.READER_EXCEPTION_EVENT:
                self.reader_exception_event = ReaderExceptionEvent()
                self.reader_exception_event.decode(param_data)
            elif sub_param_type == ParameterType.ROSPEC_EVENT:
                self.rospec_event = ROSpecEvent()
                self.rospec_event.decode(param_data)
            elif sub_param_type == ParameterType.AI_SPEC_EVENT:
                self.ai_spec_event = AISpecEvent()
                self.ai_spec_event.decode(param_data)
            elif sub_param_type == ParameterType.REPORT_BUFFER_LEVEL_WARNING_EVENT:
                self.report_buffer_level_warning_event = ReportBufferLevelWarningEvent()
                self.report_buffer_level_warning_event.decode(param_data)
            elif sub_param_type == ParameterType.REPORT_BUFFER_OVERFLOW_ERROR_EVENT:
                self.report_buffer_overflow_error_event = ReportBufferOverflowErrorEvent()
                self.report_buffer_overflow_error_event.decode(param_data)
            
            offset += sub_param_length
        
        return param_length


@dataclass
class ReaderEventNotification(LLRPMessage):
    """READER_EVENT_NOTIFICATION Message - Reader event notifications"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.READER_EVENT_NOTIFICATION, msg_id)
        self.reader_event_notification_data = None
    
    def decode_parameters(self, data: bytes):
        """Decode reader event notification parameters"""
        from .protocol import LLRPParameter
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
            
            if param_type == ParameterType.READER_EVENT_NOTIFICATION_DATA:
                self.reader_event_notification_data = ReaderEventNotificationData()
                self.reader_event_notification_data.decode(data[offset:offset+param_length])
            
            offset += param_length


# Event Parameter Classes

@dataclass  
class ConnectionAttemptEvent(LLRPParameter):
    """Connection Attempt Event Parameter"""
    
    def __init__(self, status: int = 0):
        super().__init__(ParameterType.CONNECTION_ATTEMPT_EVENT)
        self.status = status  # 0=Success, 1=Failed_A_Reader_Initiated_Connection_Already_Exists
    
    def encode(self) -> bytes:
        data = struct.pack('!H', self.status)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.CONNECTION_ATTEMPT_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 2:
            self.status = struct.unpack('!H', data[payload_start:payload_start+2])[0]
        
        return param_length


@dataclass
class ConnectionCloseEvent(LLRPParameter):
    """Connection Close Event Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.CONNECTION_CLOSE_EVENT)
    
    def encode(self) -> bytes:
        header = self.encode_header(4)
        return header
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        return param_length if param_type == ParameterType.CONNECTION_CLOSE_EVENT else 0


@dataclass
class AntennaEvent(LLRPParameter):
    """Antenna Event Parameter"""
    
    def __init__(self, event_type: int = 0, antenna_id: int = 0):
        super().__init__(ParameterType.ANTENNA_EVENT)
        self.event_type = event_type  # 0=Antenna_Disconnected, 1=Antenna_Connected
        self.antenna_id = antenna_id
    
    def encode(self) -> bytes:
        data = struct.pack('!BH', self.event_type, self.antenna_id)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.ANTENNA_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 3:
            self.event_type, self.antenna_id = struct.unpack('!BH', data[payload_start:payload_start+3])
        
        return param_length


@dataclass
class ReaderExceptionEvent(LLRPParameter):
    """Reader Exception Event Parameter"""
    
    def __init__(self, message: str = "", op_spec_id: int = 0, access_spec_id: int = 0):
        super().__init__(ParameterType.READER_EXCEPTION_EVENT)
        self.message = message
        self.op_spec_id = op_spec_id
        self.access_spec_id = access_spec_id
    
    def encode(self) -> bytes:
        message_bytes = self.message.encode('utf-8')
        data = struct.pack('!HH', len(message_bytes), self.op_spec_id)
        data += message_bytes
        data += struct.pack('!H', self.access_spec_id)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.READER_EXCEPTION_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 4:
            message_len, self.op_spec_id = struct.unpack('!HH', data[payload_start:payload_start+4])
            
            if len(data) >= payload_start + 4 + message_len + 2:
                self.message = data[payload_start+4:payload_start+4+message_len].decode('utf-8', errors='ignore')
                self.access_spec_id = struct.unpack('!H', data[payload_start+4+message_len:payload_start+4+message_len+2])[0]
        
        return param_length


@dataclass
class ROSpecEvent(LLRPParameter):
    """ROSpec Event Parameter"""
    
    def __init__(self, event_type: int = 0, rospec_id: int = 0, preempting_rospec_id: int = 0):
        super().__init__(ParameterType.ROSPEC_EVENT)
        self.event_type = event_type  # 0=Start_Of_ROSpec, 1=End_Of_ROSpec
        self.rospec_id = rospec_id
        self.preempting_rospec_id = preempting_rospec_id
    
    def encode(self) -> bytes:
        data = struct.pack('!BII', self.event_type, self.rospec_id, self.preempting_rospec_id)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.ROSPEC_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 9:
            self.event_type, self.rospec_id, self.preempting_rospec_id = struct.unpack(
                '!BII', data[payload_start:payload_start+9])
        
        return param_length


@dataclass
class AISpecEvent(LLRPParameter):
    """AISpec Event Parameter"""
    
    def __init__(self, event_type: int = 0, rospec_id: int = 0, spec_index: int = 0):
        super().__init__(ParameterType.AI_SPEC_EVENT)
        self.event_type = event_type  # 0=End_Of_AISpec
        self.rospec_id = rospec_id
        self.spec_index = spec_index
    
    def encode(self) -> bytes:
        data = struct.pack('!BIH', self.event_type, self.rospec_id, self.spec_index)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.AI_SPEC_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 7:
            self.event_type, self.rospec_id, self.spec_index = struct.unpack(
                '!BIH', data[payload_start:payload_start+7])
        
        return param_length


@dataclass
class ReportBufferLevelWarningEvent(LLRPParameter):
    """Report Buffer Level Warning Event Parameter"""
    
    def __init__(self, buffer_fill_percentage: int = 0):
        super().__init__(ParameterType.REPORT_BUFFER_LEVEL_WARNING_EVENT)
        self.buffer_fill_percentage = buffer_fill_percentage
    
    def encode(self) -> bytes:
        data = struct.pack('!B', self.buffer_fill_percentage)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.REPORT_BUFFER_LEVEL_WARNING_EVENT:
            return 0
        
        payload_start = header_len
        if len(data) >= payload_start + 1:
            self.buffer_fill_percentage = struct.unpack('!B', data[payload_start:payload_start+1])[0]
        
        return param_length


@dataclass
class ReportBufferOverflowErrorEvent(LLRPParameter):
    """Report Buffer Overflow Error Event Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.REPORT_BUFFER_OVERFLOW_ERROR_EVENT)
    
    def encode(self) -> bytes:
        header = self.encode_header(4)
        return header
    
    def decode(self, data: bytes) -> int:
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        return param_length if param_type == ParameterType.REPORT_BUFFER_OVERFLOW_ERROR_EVENT else 0


# AccessSpec Messages

@dataclass
class AddAccessSpec(LLRPMessage):
    """ADD_ACCESSSPEC Message - Add AccessSpec to reader"""
    
    def __init__(self, msg_id: int = 0, access_spec=None):
        super().__init__(MessageType.ADD_ACCESSSPEC, msg_id)
        self.access_spec = access_spec
    
    def encode_parameters(self) -> bytes:
        """Encode ADD_ACCESSSPEC parameters"""
        if self.access_spec:
            return self.access_spec.encode()
        return b''


@dataclass
class AddAccessSpecResponse(LLRPMessage):
    """ADD_ACCESSSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ADD_ACCESSSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


@dataclass
class EnableAccessSpec(LLRPMessage):
    """ENABLE_ACCESSSPEC Message"""
    
    def __init__(self, msg_id: int = 0, access_spec_id: int = 0):
        super().__init__(MessageType.ENABLE_ACCESSSPEC, msg_id)
        self.access_spec_id = access_spec_id
    
    def encode_parameters(self) -> bytes:
        """Encode ENABLE_ACCESSSPEC parameters"""
        return struct.pack('!I', self.access_spec_id)


@dataclass
class EnableAccessSpecResponse(LLRPMessage):
    """ENABLE_ACCESSSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.ENABLE_ACCESSSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


@dataclass
class DisableAccessSpec(LLRPMessage):
    """DISABLE_ACCESSSPEC Message"""
    
    def __init__(self, msg_id: int = 0, access_spec_id: int = 0):
        super().__init__(MessageType.DISABLE_ACCESSSPEC, msg_id)
        self.access_spec_id = access_spec_id
    
    def encode_parameters(self) -> bytes:
        """Encode DISABLE_ACCESSSPEC parameters"""
        return struct.pack('!I', self.access_spec_id)


@dataclass
class DisableAccessSpecResponse(LLRPMessage):
    """DISABLE_ACCESSSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.DISABLE_ACCESSSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


@dataclass
class DeleteAccessSpec(LLRPMessage):
    """DELETE_ACCESSSPEC Message"""
    
    def __init__(self, msg_id: int = 0, access_spec_id: int = 0):
        super().__init__(MessageType.DELETE_ACCESSSPEC, msg_id)
        self.access_spec_id = access_spec_id  # 0 = delete all
    
    def encode_parameters(self) -> bytes:
        """Encode DELETE_ACCESSSPEC parameters"""
        return struct.pack('!I', self.access_spec_id)


@dataclass
class DeleteAccessSpecResponse(LLRPMessage):
    """DELETE_ACCESSSPEC_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.DELETE_ACCESSSPEC_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


@dataclass
class GetAccessSpecs(LLRPMessage):
    """GET_ACCESSSPECS Message - Get all AccessSpecs from reader"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.GET_ACCESSSPECS, msg_id)
    
    def decode_parameters(self, data: bytes):
        """GET_ACCESSSPECS has no parameters"""
        pass


@dataclass
class GetAccessSpecsResponse(LLRPMessage):
    """GET_ACCESSSPECS_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.GET_ACCESSSPECS_RESPONSE, msg_id)
        self.llrp_status = None
        self.access_specs = []  # List of AccessSpec parameters
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        from .accessspec_parameters import AccessSpec, AccessSpecParameterType
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
            
            param_data = data[offset:offset+param_length]
            
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(param_data)
            elif param_type == AccessSpecParameterType.ACCESS_SPEC:
                access_spec = AccessSpec()
                access_spec.decode(param_data)
                self.access_specs.append(access_spec)
                consumed = param_length
            else:
                consumed = param_length
            
            offset += consumed


# Reader Configuration Messages

@dataclass
class GetReaderConfig(LLRPMessage):
    """GET_READER_CONFIG Message - Request reader configuration"""
    
    def __init__(self, msg_id: int = 0, antenna_id: int = 0, 
                 requested_configuration: int = 0):
        super().__init__(MessageType.GET_READER_CONFIG, msg_id)
        self.antenna_id = antenna_id  # 0 = all antennas
        self.requested_configuration = requested_configuration  # Bitmask of requested config
    
    def encode_parameters(self) -> bytes:
        """Encode GET_READER_CONFIG parameters"""
        return struct.pack('!HH', self.antenna_id, self.requested_configuration)


@dataclass  
class GetReaderConfigResponse(LLRPMessage):
    """GET_READER_CONFIG_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.GET_READER_CONFIG_RESPONSE, msg_id)
        self.llrp_status = None
        self.antenna_configurations = []  # List of AntennaConfiguration
        self.antenna_properties = []      # List of AntennaProperties
        self.events_and_reports = None    # EventsAndReports config
        self.keepalive_spec = None        # KeepaliveSpec config
    
    def decode_parameters(self, data: bytes):
        """Decode configuration response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        from .config_parameters import (
            CONFIG_PARAMETER_CLASSES, ConfigParameterType
        )
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
            
            param_data = data[offset:offset+param_length]
            
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(param_data)
            elif param_type == ConfigParameterType.ANTENNA_CONFIGURATION:
                from .config_parameters import AntennaConfiguration
                config = AntennaConfiguration()
                config.decode(param_data)
                self.antenna_configurations.append(config)
                consumed = param_length
            elif param_type == ConfigParameterType.ANTENNA_PROPERTIES:
                from .config_parameters import AntennaProperties
                props = AntennaProperties()
                props.decode(param_data)
                self.antenna_properties.append(props)
                consumed = param_length
            elif param_type == ConfigParameterType.EVENTS_AND_REPORTS:
                from .config_parameters import EventsAndReports
                self.events_and_reports = EventsAndReports()
                self.events_and_reports.decode(param_data)
                consumed = param_length
            elif param_type == ConfigParameterType.KEEPALIVE_SPEC:
                from .config_parameters import KeepaliveSpec
                self.keepalive_spec = KeepaliveSpec()
                self.keepalive_spec.decode(param_data)
                consumed = param_length
            else:
                consumed = param_length
                
            offset += consumed


@dataclass
class SetReaderConfig(LLRPMessage):
    """SET_READER_CONFIG Message - Configure reader settings"""
    
    def __init__(self, msg_id: int = 0, reset_to_factory_default: bool = False):
        super().__init__(MessageType.SET_READER_CONFIG, msg_id)
        self.reset_to_factory_default = reset_to_factory_default
        self.antenna_configurations = []  # List of AntennaConfiguration
        self.events_and_reports = None    # EventsAndReports config
        self.keepalive_spec = None        # KeepaliveSpec config
    
    def encode_parameters(self) -> bytes:
        """Encode SET_READER_CONFIG parameters"""
        data = struct.pack('!B', 1 if self.reset_to_factory_default else 0)
        
        # Add antenna configurations
        for config in self.antenna_configurations:
            data += config.encode()
            
        # Add events and reports config
        if self.events_and_reports:
            data += self.events_and_reports.encode()
            
        # Add keepalive spec
        if self.keepalive_spec:
            data += self.keepalive_spec.encode()
            
        return data
    
    def add_antenna_config(self, antenna_config):
        """Add antenna configuration"""
        self.antenna_configurations.append(antenna_config)


@dataclass
class SetReaderConfigResponse(LLRPMessage):
    """SET_READER_CONFIG_RESPONSE Message"""
    
    def __init__(self, msg_id: int = 0):
        super().__init__(MessageType.SET_READER_CONFIG_RESPONSE, msg_id)
        self.llrp_status = None
    
    def decode_parameters(self, data: bytes):
        """Decode response parameters"""
        from .protocol import LLRPParameter, LLRPStatus
        
        offset = 0
        while offset < len(data):
            param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data, offset)
            
            if param_type is None:
                break
                
            if param_type == 287:  # LLRPStatus
                self.llrp_status = LLRPStatus()
                consumed = self.llrp_status.decode(data[offset:offset+param_length])
                offset += consumed
            else:
                offset += param_length


# Message class registry - Complete mapping
def _get_message_classes():
    """Get message class registry with lazy import to avoid circular dependencies"""
    from .protocol import GetReaderCapabilities, GetReaderCapabilitiesResponse
    
    return {
        # Reader Capability Messages
        MessageType.GET_READER_CAPABILITIES: GetReaderCapabilities,
        MessageType.GET_READER_CAPABILITIES_RESPONSE: GetReaderCapabilitiesResponse,
        
        # Reader Configuration Messages  
        MessageType.GET_READER_CONFIG: GetReaderConfig,
        MessageType.GET_READER_CONFIG_RESPONSE: GetReaderConfigResponse,
        MessageType.SET_READER_CONFIG: SetReaderConfig,
        MessageType.SET_READER_CONFIG_RESPONSE: SetReaderConfigResponse,
        
        # Events and Reports Messages
        MessageType.ENABLE_EVENTS_AND_REPORTS: EnableEventsAndReports,
        MessageType.READER_EVENT_NOTIFICATION: ReaderEventNotification,
        
        # ROSpec Messages
        MessageType.ADD_ROSPEC: AddROSpec,
        MessageType.ADD_ROSPEC_RESPONSE: AddROSpecResponse,
        MessageType.ENABLE_ROSPEC: EnableROSpec,
        MessageType.ENABLE_ROSPEC_RESPONSE: EnableROSpecResponse,
        MessageType.START_ROSPEC: StartROSpec,
        MessageType.START_ROSPEC_RESPONSE: StartROSpecResponse,
        MessageType.STOP_ROSPEC: StopROSpec,
        MessageType.STOP_ROSPEC_RESPONSE: StopROSpecResponse,
        MessageType.DELETE_ROSPEC: DeleteROSpec,
        MessageType.DELETE_ROSPEC_RESPONSE: DeleteROSpecResponse,
        
        # AccessSpec Messages
        MessageType.ADD_ACCESSSPEC: AddAccessSpec,
        MessageType.ADD_ACCESSSPEC_RESPONSE: AddAccessSpecResponse,
        MessageType.ENABLE_ACCESSSPEC: EnableAccessSpec,
        MessageType.ENABLE_ACCESSSPEC_RESPONSE: EnableAccessSpecResponse,
        MessageType.DISABLE_ACCESSSPEC: DisableAccessSpec,
        MessageType.DISABLE_ACCESSSPEC_RESPONSE: DisableAccessSpecResponse,
        MessageType.DELETE_ACCESSSPEC: DeleteAccessSpec,
        MessageType.DELETE_ACCESSSPEC_RESPONSE: DeleteAccessSpecResponse,
        MessageType.GET_ACCESSSPECS: GetAccessSpecs,
        MessageType.GET_ACCESSSPECS_RESPONSE: GetAccessSpecsResponse,
        
        # Report Messages
        MessageType.RO_ACCESS_REPORT: ROAccessReport,
        
        # Error and Connection Messages
        MessageType.ERROR_MESSAGE: ErrorMessage,
        MessageType.KEEPALIVE: KeepAlive,
        MessageType.KEEPALIVE_ACK: KeepAliveAck,
        MessageType.CLOSE_CONNECTION: CloseConnection,
        MessageType.CLOSE_CONNECTION_RESPONSE: CloseConnectionResponse,
    }

# Create the registry
MESSAGE_CLASSES = _get_message_classes()