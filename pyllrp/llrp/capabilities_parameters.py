"""
LLRP Reader Capabilities Parameters

Implementation of capability-related parameters for GET_READER_CAPABILITIES_RESPONSE
"""

import struct
from typing import List, Optional
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


@dataclass
class GeneralDeviceCapabilities(LLRPParameter):
    """General Device Capabilities Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.GENERAL_DEVICE_CAPABILITIES)
        self.max_number_of_antenna_supported = 0
        self.can_set_antenna_properties = False
        self.has_utc_clock_capability = False
        self.device_manufacturer_name = ""
        self.model_name = ""
        self.firmware_version = ""
        self.receive_sensitivity_table_entries = []  # List of receive sensitivity values
        self.per_antenna_receive_sensitivity_range = []
        self.gpi_port_capabilities = []
        self.gpo_port_capabilities = []
    
    def encode(self) -> bytes:
        """Encode general device capabilities"""
        # Start with fixed fields
        flags = 0
        if self.can_set_antenna_properties:
            flags |= 0x80
        if self.has_utc_clock_capability:
            flags |= 0x40
            
        data = struct.pack('!HB', self.max_number_of_antenna_supported, flags)
        
        # Add device manufacturer name
        manufacturer_bytes = self.device_manufacturer_name.encode('utf-8')
        data += struct.pack('!H', len(manufacturer_bytes))
        data += manufacturer_bytes
        
        # Add model name  
        model_bytes = self.model_name.encode('utf-8')
        data += struct.pack('!H', len(model_bytes))
        data += model_bytes
        
        # Add firmware version
        firmware_bytes = self.firmware_version.encode('utf-8')
        data += struct.pack('!H', len(firmware_bytes))
        data += firmware_bytes
        
        # Add sub-parameters would go here (receive sensitivity tables, etc.)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode general device capabilities"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.GENERAL_DEVICE_CAPABILITIES:
            return 0
        
        offset = header_len
        
        # Parse fixed fields
        if len(data) >= offset + 3:
            self.max_number_of_antenna_supported, flags = struct.unpack('!HB', data[offset:offset+3])
            self.can_set_antenna_properties = bool(flags & 0x80)
            self.has_utc_clock_capability = bool(flags & 0x40)
            offset += 3
        
        # Parse device manufacturer name
        if len(data) >= offset + 2:
            name_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            if len(data) >= offset + name_len:
                self.device_manufacturer_name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
                offset += name_len
        
        # Parse model name
        if len(data) >= offset + 2:
            name_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            if len(data) >= offset + name_len:
                self.model_name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
                offset += name_len
        
        # Parse firmware version
        if len(data) >= offset + 2:
            version_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            if len(data) >= offset + version_len:
                self.firmware_version = data[offset:offset+version_len].decode('utf-8', errors='ignore')
                offset += version_len
        
        # Parse sub-parameters (receive sensitivity tables, GPI/GPO capabilities, etc.)
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            # Handle sub-parameters here
            # For now, just skip them
            offset += sub_param_length
        
        return param_length


@dataclass
class LLRPCapabilities(LLRPParameter):
    """LLRP Capabilities Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.LLRP_CAPABILITIES)
        self.can_do_rf_survey = False
        self.can_report_buffer_fill_warning = False
        self.supports_client_request_opspec = False
        self.can_stateaware_singulation = False
        self.supports_holding_of_events_and_reports = False
        self.max_num_priority_levels_supported = 0
        self.client_request_opspec_timeout = 0
        self.max_num_rospecs = 0
        self.max_num_spec_parameters_per_rospec = 0
        self.max_num_inventory_parameter_spec_parameters_per_aispec = 0
        self.max_num_access_specs = 0
        self.max_num_op_specs_per_access_spec = 0
    
    def encode(self) -> bytes:
        """Encode LLRP capabilities"""
        # Capability flags
        capability_flags = 0
        if self.can_do_rf_survey:
            capability_flags |= 0x80
        if self.can_report_buffer_fill_warning:
            capability_flags |= 0x40
        if self.supports_client_request_opspec:
            capability_flags |= 0x20
        if self.can_stateaware_singulation:
            capability_flags |= 0x10
        if self.supports_holding_of_events_and_reports:
            capability_flags |= 0x08
        
        data = struct.pack('!BBHIIIII',
                          capability_flags,
                          self.max_num_priority_levels_supported,
                          self.client_request_opspec_timeout,
                          self.max_num_rospecs,
                          self.max_num_spec_parameters_per_rospec,
                          self.max_num_inventory_parameter_spec_parameters_per_aispec,
                          self.max_num_access_specs,
                          self.max_num_op_specs_per_access_spec)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode LLRP capabilities"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.LLRP_CAPABILITIES:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 22:  # 1+1+2+4*5 = 22 bytes
            values = struct.unpack('!BBHIIIII', data[offset:offset+22])
            
            capability_flags = values[0]
            self.can_do_rf_survey = bool(capability_flags & 0x80)
            self.can_report_buffer_fill_warning = bool(capability_flags & 0x40)
            self.supports_client_request_opspec = bool(capability_flags & 0x20)
            self.can_stateaware_singulation = bool(capability_flags & 0x10)
            self.supports_holding_of_events_and_reports = bool(capability_flags & 0x08)
            
            self.max_num_priority_levels_supported = values[1]
            self.client_request_opspec_timeout = values[2]
            self.max_num_rospecs = values[3]
            self.max_num_spec_parameters_per_rospec = values[4]
            self.max_num_inventory_parameter_spec_parameters_per_aispec = values[5]
            self.max_num_access_specs = values[6]
            self.max_num_op_specs_per_access_spec = values[7]
        
        return param_length


@dataclass
class RegulatoryCapabilities(LLRPParameter):
    """Regulatory Capabilities Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.REGULATORY_CAPABILITIES)
        self.country_code = 0  # ISO 3166-1 country code
        self.communications_standard = 0  # 1=ETSI_302_208, 2=FCC_PART_15, 3=ETSI_300_220
        self.uhf_band_capabilities = []  # List of UHF band capability parameters
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode regulatory capabilities"""
        data = struct.pack('!HH', self.country_code, self.communications_standard)
        
        # Add UHF band capabilities
        for uhf_cap in self.uhf_band_capabilities:
            data += uhf_cap.encode()
        
        # Add custom parameters
        for custom_param in self.custom_parameters:
            data += custom_param.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode regulatory capabilities"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.REGULATORY_CAPABILITIES:
            return 0
        
        offset = header_len
        
        # Parse fixed fields
        if len(data) >= offset + 4:
            self.country_code, self.communications_standard = struct.unpack('!HH', data[offset:offset+4])
            offset += 4
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == ParameterType.UHF_BAND_CAPABILITIES:
                uhf_cap = UHFBandCapabilities()
                uhf_cap.decode(data[offset:offset+sub_param_length])
                self.uhf_band_capabilities.append(uhf_cap)
            else:
                # Handle other sub-parameters or custom parameters
                pass
            
            offset += sub_param_length
        
        return param_length


@dataclass
class UHFBandCapabilities(LLRPParameter):
    """UHF Band Capabilities Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.UHF_BAND_CAPABILITIES)
        self.supported_list = []  # List of supported UHF bands
        self.frequency_information = []  # List of frequency hop tables
        self.air_protocol_uhf_rfmode_table = []
    
    def encode(self) -> bytes:
        """Encode UHF band capabilities"""
        data = b''
        
        # Add supported list
        for supported in self.supported_list:
            data += supported.encode()
        
        # Add frequency information
        for freq_info in self.frequency_information:
            data += freq_info.encode()
        
        # Add air protocol RF mode tables
        for rf_mode_table in self.air_protocol_uhf_rfmode_table:
            data += rf_mode_table.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode UHF band capabilities"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.UHF_BAND_CAPABILITIES:
            return 0
        
        offset = header_len
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            # Handle different UHF band capability sub-parameters
            # For now, just skip them
            offset += sub_param_length
        
        return param_length


@dataclass
class AirProtocolLLRPCapabilities(LLRPParameter):
    """Air Protocol LLRP Capabilities Parameter"""
    
    def __init__(self):
        super().__init__(ParameterType.AIR_PROTOCOL_LLRP_CAPABILITIES)
        self.can_support_block_erase = False
        self.can_support_block_write = False
        self.can_support_block_permalock = False
        self.can_support_tag_recommissioning = False
        self.can_support_uhf_c1g2_custom_parameters = False
        self.can_support_xpc = False
        self.max_num_select_filters_per_query = 0
    
    def encode(self) -> bytes:
        """Encode air protocol LLRP capabilities"""
        # Capability flags
        capability_flags = 0
        if self.can_support_block_erase:
            capability_flags |= 0x80
        if self.can_support_block_write:
            capability_flags |= 0x40
        if self.can_support_block_permalock:
            capability_flags |= 0x20
        if self.can_support_tag_recommissioning:
            capability_flags |= 0x10
        if self.can_support_uhf_c1g2_custom_parameters:
            capability_flags |= 0x08
        if self.can_support_xpc:
            capability_flags |= 0x04
        
        data = struct.pack('!BH', capability_flags, self.max_num_select_filters_per_query)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode air protocol LLRP capabilities"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.AIR_PROTOCOL_LLRP_CAPABILITIES:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 3:  # 1+2 = 3 bytes
            capability_flags, self.max_num_select_filters_per_query = struct.unpack('!BH', data[offset:offset+3])
            
            self.can_support_block_erase = bool(capability_flags & 0x80)
            self.can_support_block_write = bool(capability_flags & 0x40)
            self.can_support_block_permalock = bool(capability_flags & 0x20)
            self.can_support_tag_recommissioning = bool(capability_flags & 0x10)
            self.can_support_uhf_c1g2_custom_parameters = bool(capability_flags & 0x08)
            self.can_support_xpc = bool(capability_flags & 0x04)
        
        return param_length


# Capabilities parameter registry
CAPABILITIES_PARAMETER_CLASSES = {
    ParameterType.GENERAL_DEVICE_CAPABILITIES: GeneralDeviceCapabilities,
    ParameterType.LLRP_CAPABILITIES: LLRPCapabilities,
    ParameterType.REGULATORY_CAPABILITIES: RegulatoryCapabilities,
    ParameterType.UHF_BAND_CAPABILITIES: UHFBandCapabilities,
    ParameterType.AIR_PROTOCOL_LLRP_CAPABILITIES: AirProtocolLLRPCapabilities,
}