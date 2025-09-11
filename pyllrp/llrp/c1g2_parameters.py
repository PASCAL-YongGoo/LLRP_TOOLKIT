"""
EPC Class1 Generation2 (C1G2) Air Protocol Parameters

Implementation of C1G2-specific parameters for advanced EPC Gen2 tag operations
"""

import struct
from typing import List, Optional
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


# Extend ParameterType with C1G2 parameters
class C1G2ParameterType:
    """C1G2 Air Protocol parameter types"""
    C1G2_INVENTORY_COMMAND = 330
    C1G2_FILTER = 331
    C1G2_TAG_INVENTORY_MASK = 332
    C1G2_TAG_INVENTORY_STATE_AWARE = 333
    C1G2_RF_CONTROL = 334
    C1G2_SINGULATION_CONTROL = 335
    C1G2_TAG_SPEC = 336
    
    # C1G2 Target and Action values
    C1G2_TARGET_TAG = 337
    C1G2_AUTO_GAIN_CONTROL = 338
    C1G2_FIXED_GAIN = 339


@dataclass
class C1G2InventoryCommand(LLRPParameter):
    """C1G2 Inventory Command Parameter - Controls Gen2 inventory behavior"""
    
    def __init__(self):
        super().__init__(C1G2ParameterType.C1G2_INVENTORY_COMMAND)
        self.tag_inventory_state_aware = False
        self.c1g2_filter = []  # List of C1G2Filter parameters
        self.c1g2_rf_control = None
        self.c1g2_singulation_control = None
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode C1G2 inventory command"""
        # Flags byte
        flags = 0
        if self.tag_inventory_state_aware:
            flags |= 0x80
        
        data = struct.pack('!B', flags)
        
        # Add filters
        for filter_param in self.c1g2_filter:
            data += filter_param.encode()
        
        # Add RF control
        if self.c1g2_rf_control:
            data += self.c1g2_rf_control.encode()
        
        # Add singulation control
        if self.c1g2_singulation_control:
            data += self.c1g2_singulation_control.encode()
        
        # Add custom parameters
        for custom in self.custom_parameters:
            data += custom.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 inventory command"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_INVENTORY_COMMAND:
            return 0
        
        offset = header_len
        
        # Parse flags
        if len(data) >= offset + 1:
            flags = struct.unpack('!B', data[offset:offset+1])[0]
            self.tag_inventory_state_aware = bool(flags & 0x80)
            offset += 1
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == C1G2ParameterType.C1G2_FILTER:
                filter_param = C1G2Filter()
                filter_param.decode(data[offset:offset+sub_param_length])
                self.c1g2_filter.append(filter_param)
            elif sub_param_type == C1G2ParameterType.C1G2_RF_CONTROL:
                self.c1g2_rf_control = C1G2RFControl()
                self.c1g2_rf_control.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == C1G2ParameterType.C1G2_SINGULATION_CONTROL:
                self.c1g2_singulation_control = C1G2SingulationControl()
                self.c1g2_singulation_control.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


@dataclass
class C1G2Filter(LLRPParameter):
    """C1G2 Filter Parameter - Filter tags based on memory content"""
    
    def __init__(self, filter_type: int = 1, memory_bank: int = 1, 
                 bit_pointer: int = 32, bit_length: int = 0, filter_data: bytes = b''):
        super().__init__(C1G2ParameterType.C1G2_FILTER)
        self.filter_type = filter_type  # 1=All_EPC, 2=Non_EPC, 3=Memory_Bank_Filter
        self.memory_bank = memory_bank  # 0=Reserved, 1=EPC, 2=TID, 3=User
        self.bit_pointer = bit_pointer  # Starting bit address
        self.bit_length = bit_length    # Length in bits
        self.filter_data = filter_data  # Filter pattern data
        self.c1g2_tag_inventory_mask = None
        self.c1g2_tag_inventory_state_aware = None
    
    def encode(self) -> bytes:
        """Encode C1G2 filter"""
        data = struct.pack('!BHHH',
                          self.filter_type,
                          self.memory_bank,
                          self.bit_pointer,
                          self.bit_length)
        
        # Add filter data
        data += self.filter_data
        
        # Add sub-parameters
        if self.c1g2_tag_inventory_mask:
            data += self.c1g2_tag_inventory_mask.encode()
        
        if self.c1g2_tag_inventory_state_aware:
            data += self.c1g2_tag_inventory_state_aware.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 filter"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_FILTER:
            return 0
        
        offset = header_len
        
        # Parse fixed fields
        if len(data) >= offset + 7:
            self.filter_type, self.memory_bank, self.bit_pointer, self.bit_length = struct.unpack(
                '!BHHH', data[offset:offset+7])
            offset += 7
        
        # Calculate filter data length in bytes
        filter_data_bytes = (self.bit_length + 7) // 8
        if len(data) >= offset + filter_data_bytes:
            self.filter_data = data[offset:offset+filter_data_bytes]
            offset += filter_data_bytes
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == C1G2ParameterType.C1G2_TAG_INVENTORY_MASK:
                self.c1g2_tag_inventory_mask = C1G2TagInventoryMask()
                self.c1g2_tag_inventory_mask.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == C1G2ParameterType.C1G2_TAG_INVENTORY_STATE_AWARE:
                self.c1g2_tag_inventory_state_aware = C1G2TagInventoryStateAware()
                self.c1g2_tag_inventory_state_aware.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


@dataclass
class C1G2TagInventoryMask(LLRPParameter):
    """C1G2 Tag Inventory Mask Parameter - Mask for tag matching"""
    
    def __init__(self, memory_bank: int = 1, bit_pointer: int = 32, 
                 mask_data: bytes = b''):
        super().__init__(C1G2ParameterType.C1G2_TAG_INVENTORY_MASK)
        self.memory_bank = memory_bank
        self.bit_pointer = bit_pointer
        self.mask_data = mask_data
    
    def encode(self) -> bytes:
        """Encode tag inventory mask"""
        data = struct.pack('!HH', self.memory_bank, self.bit_pointer)
        data += self.mask_data
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode tag inventory mask"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_TAG_INVENTORY_MASK:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 4:
            self.memory_bank, self.bit_pointer = struct.unpack('!HH', data[offset:offset+4])
            offset += 4
        
        # Read remaining data as mask
        if offset < param_length:
            mask_length = param_length - offset
            if len(data) >= offset + mask_length:
                self.mask_data = data[offset:offset+mask_length]
        
        return param_length


@dataclass
class C1G2TagInventoryStateAware(LLRPParameter):
    """C1G2 Tag Inventory State Aware Parameter - State-aware inventory"""
    
    def __init__(self, tag_state: int = 0, session: int = 0):
        super().__init__(C1G2ParameterType.C1G2_TAG_INVENTORY_STATE_AWARE)
        self.tag_state = tag_state  # 0=A, 1=B
        self.session = session      # Session number (0-3)
    
    def encode(self) -> bytes:
        """Encode tag inventory state aware"""
        data = struct.pack('!BB', self.tag_state, self.session)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode tag inventory state aware"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_TAG_INVENTORY_STATE_AWARE:
            return 0
        
        offset = header_len
        if len(data) >= offset + 2:
            self.tag_state, self.session = struct.unpack('!BB', data[offset:offset+2])
        
        return param_length


@dataclass
class C1G2RFControl(LLRPParameter):
    """C1G2 RF Control Parameter - RF transmission parameters"""
    
    def __init__(self, mode_index: int = 0, tari: int = 0):
        super().__init__(C1G2ParameterType.C1G2_RF_CONTROL)
        self.mode_index = mode_index  # RF mode index from reader capabilities
        self.tari = tari              # Tari value in nanoseconds
    
    def encode(self) -> bytes:
        """Encode C1G2 RF control"""
        data = struct.pack('!HH', self.mode_index, self.tari)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 RF control"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_RF_CONTROL:
            return 0
        
        offset = header_len
        if len(data) >= offset + 4:
            self.mode_index, self.tari = struct.unpack('!HH', data[offset:offset+4])
        
        return param_length


@dataclass
class C1G2SingulationControl(LLRPParameter):
    """C1G2 Singulation Control Parameter - Controls tag singulation process"""
    
    def __init__(self, session: int = 0, tag_population: int = 32, 
                 tag_transit_time: int = 0):
        super().__init__(C1G2ParameterType.C1G2_SINGULATION_CONTROL)
        self.session = session                    # Session number (0-3)
        self.tag_population = tag_population      # Expected tag population
        self.tag_transit_time = tag_transit_time  # Tag transit time in milliseconds
        self.c1g2_tag_inventory_state_aware = None
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode C1G2 singulation control"""
        data = struct.pack('!BHI', 
                          self.session,
                          self.tag_population,
                          self.tag_transit_time)
        
        # Add sub-parameters
        if self.c1g2_tag_inventory_state_aware:
            data += self.c1g2_tag_inventory_state_aware.encode()
        
        for custom in self.custom_parameters:
            data += custom.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 singulation control"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_SINGULATION_CONTROL:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 7:
            self.session, self.tag_population, self.tag_transit_time = struct.unpack(
                '!BHI', data[offset:offset+7])
            offset += 7
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == C1G2ParameterType.C1G2_TAG_INVENTORY_STATE_AWARE:
                self.c1g2_tag_inventory_state_aware = C1G2TagInventoryStateAware()
                self.c1g2_tag_inventory_state_aware.decode(data[offset:offset+sub_param_length])
            
            offset += sub_param_length
        
        return param_length


@dataclass
class C1G2TagSpec(LLRPParameter):
    """C1G2 Tag Spec Parameter - Specifies target tags for access operations"""
    
    def __init__(self, target: int = 4):  # 4 = SL (Selected)
        super().__init__(C1G2ParameterType.C1G2_TAG_SPEC)
        self.target = target  # Target flag: 0=S0, 1=S1, 2=S2, 3=S3, 4=SL
        self.c1g2_target_tag = []  # List of target tag parameters
    
    def encode(self) -> bytes:
        """Encode C1G2 tag spec"""
        data = struct.pack('!B', self.target)
        
        # Add target tag parameters
        for target_tag in self.c1g2_target_tag:
            data += target_tag.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 tag spec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_TAG_SPEC:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 1:
            self.target = struct.unpack('!B', data[offset:offset+1])[0]
            offset += 1
        
        # Parse target tag parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == C1G2ParameterType.C1G2_TARGET_TAG:
                target_tag = C1G2TargetTag()
                target_tag.decode(data[offset:offset+sub_param_length])
                self.c1g2_target_tag.append(target_tag)
            
            offset += sub_param_length
        
        return param_length


@dataclass
class C1G2TargetTag(LLRPParameter):
    """C1G2 Target Tag Parameter - Specifies a specific tag to target"""
    
    def __init__(self, memory_bank: int = 1, match: bool = True,
                 bit_pointer: int = 32, tag_mask: bytes = b'', tag_data: bytes = b''):
        super().__init__(C1G2ParameterType.C1G2_TARGET_TAG)
        self.memory_bank = memory_bank  # Memory bank to match against
        self.match = match              # True=match, False=don't match
        self.bit_pointer = bit_pointer  # Starting bit position
        self.tag_mask = tag_mask        # Mask for matching
        self.tag_data = tag_data        # Data pattern to match
    
    def encode(self) -> bytes:
        """Encode C1G2 target tag"""
        mask_bit_count = len(self.tag_mask) * 8
        data_bit_count = len(self.tag_data) * 8
        
        data = struct.pack('!HBHHHH',
                          self.memory_bank,
                          1 if self.match else 0,
                          self.bit_pointer,
                          mask_bit_count,
                          data_bit_count,
                          0)  # Reserved
        
        # Add mask and data
        data += self.tag_mask
        data += self.tag_data
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 target tag"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != C1G2ParameterType.C1G2_TARGET_TAG:
            return 0
        
        offset = header_len
        
        if len(data) >= offset + 10:
            self.memory_bank, match_byte, self.bit_pointer, mask_bit_count, data_bit_count, reserved = struct.unpack(
                '!HBHHHH', data[offset:offset+10])
            self.match = bool(match_byte)
            offset += 10
            
            # Read mask and data
            mask_byte_count = (mask_bit_count + 7) // 8
            data_byte_count = (data_bit_count + 7) // 8
            
            if len(data) >= offset + mask_byte_count:
                self.tag_mask = data[offset:offset+mask_byte_count]
                offset += mask_byte_count
            
            if len(data) >= offset + data_byte_count:
                self.tag_data = data[offset:offset+data_byte_count]
                offset += data_byte_count
        
        return param_length


@dataclass
class C1G2EPCMemorySelector(LLRPParameter):
    """C1G2 EPC Memory Selector Parameter - Controls EPC memory reporting"""
    
    def __init__(self, enable_crc: bool = True, enable_pc_bits: bool = True, 
                 enable_xpc_bits: bool = False):
        super().__init__(ParameterType.C1G2_EPC_MEMORY_SELECTOR)
        self.enable_crc = enable_crc        # Include CRC-16 in reports
        self.enable_pc_bits = enable_pc_bits    # Include PC bits
        self.enable_xpc_bits = enable_xpc_bits  # Include XPC bits (if supported)
    
    def encode(self) -> bytes:
        """Encode EPC memory selector"""
        flags = 0
        if self.enable_crc:
            flags |= 0x80
        if self.enable_pc_bits:
            flags |= 0x40
        if self.enable_xpc_bits:
            flags |= 0x20
        
        data = struct.pack('!B', flags)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode EPC memory selector"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != ParameterType.C1G2_EPC_MEMORY_SELECTOR:
            return 0
        
        offset = header_len
        if len(data) >= offset + 1:
            flags = struct.unpack('!B', data[offset:offset+1])[0]
            self.enable_crc = bool(flags & 0x80)
            self.enable_pc_bits = bool(flags & 0x40)
            self.enable_xpc_bits = bool(flags & 0x20)
        
        return param_length


# C1G2 parameter registry
C1G2_PARAMETER_CLASSES = {
    C1G2ParameterType.C1G2_INVENTORY_COMMAND: C1G2InventoryCommand,
    C1G2ParameterType.C1G2_FILTER: C1G2Filter,
    C1G2ParameterType.C1G2_TAG_INVENTORY_MASK: C1G2TagInventoryMask,
    C1G2ParameterType.C1G2_TAG_INVENTORY_STATE_AWARE: C1G2TagInventoryStateAware,
    C1G2ParameterType.C1G2_RF_CONTROL: C1G2RFControl,
    C1G2ParameterType.C1G2_SINGULATION_CONTROL: C1G2SingulationControl,
    C1G2ParameterType.C1G2_TAG_SPEC: C1G2TagSpec,
    C1G2ParameterType.C1G2_TARGET_TAG: C1G2TargetTag,
}