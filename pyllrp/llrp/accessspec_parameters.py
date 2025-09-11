"""
LLRP AccessSpec Parameters

Implementation of AccessSpec-related parameters for tag read/write/lock operations
"""

import struct
from typing import List, Optional, Union
from dataclasses import dataclass
from .protocol import LLRPParameter, ParameterType


# Extend ParameterType with AccessSpec parameters
class AccessSpecParameterType:
    """AccessSpec parameter types"""
    ACCESS_SPEC = 207
    ACCESS_COMMAND = 208
    ACCESS_REPORT_SPEC = 209
    
    # C1G2 Operations
    C1G2_READ = 331
    C1G2_WRITE = 332
    C1G2_KILL = 333
    C1G2_LOCK = 334
    C1G2_BLOCK_ERASE = 335
    C1G2_BLOCK_WRITE = 336
    
    # OpSpec Results
    C1G2_READ_OP_SPEC_RESULT = 349
    C1G2_WRITE_OP_SPEC_RESULT = 350
    C1G2_KILL_OP_SPEC_RESULT = 351
    C1G2_LOCK_OP_SPEC_RESULT = 352
    C1G2_BLOCK_ERASE_OP_SPEC_RESULT = 353
    C1G2_BLOCK_WRITE_OP_SPEC_RESULT = 354


@dataclass
class AccessSpec(LLRPParameter):
    """AccessSpec Parameter - Defines tag access operations"""
    
    def __init__(self, access_spec_id: int = 1, antenna_id: int = 0, 
                 protocol_id: int = 1, current_state: int = 0):
        super().__init__(AccessSpecParameterType.ACCESS_SPEC)
        self.access_spec_id = access_spec_id
        self.antenna_id = antenna_id  # 0 = all antennas
        self.protocol_id = protocol_id  # 1 = EPCGlobalClass1Gen2
        self.current_state = current_state  # 0=Disabled, 1=Inactive, 2=Active
        self.rospec_id = 0  # ROSpec this AccessSpec is bound to
        self.access_spec_stop_trigger = None
        self.access_command = None
        self.access_report_spec = None
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode AccessSpec"""
        data = struct.pack('!IHBHI', 
                          self.access_spec_id,
                          self.antenna_id,
                          self.protocol_id, 
                          self.current_state,
                          self.rospec_id)
        
        # Add sub-parameters
        if self.access_spec_stop_trigger:
            data += self.access_spec_stop_trigger.encode()
        
        if self.access_command:
            data += self.access_command.encode()
        
        if self.access_report_spec:
            data += self.access_report_spec.encode()
        
        for custom in self.custom_parameters:
            data += custom.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode AccessSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.ACCESS_SPEC:
            return 0
        
        offset = header_len
        
        # Parse fixed fields
        if len(data) >= offset + 11:  # 4+4+1+1+4 = 14 bytes, but packed is 11
            self.access_spec_id, self.antenna_id, self.protocol_id, self.current_state, self.rospec_id = struct.unpack(
                '!IHBHI', data[offset:offset+11])
            offset += 11
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            if sub_param_type == AccessSpecParameterType.ACCESS_COMMAND:
                self.access_command = AccessCommand()
                self.access_command.decode(data[offset:offset+sub_param_length])
            elif sub_param_type == AccessSpecParameterType.ACCESS_REPORT_SPEC:
                self.access_report_spec = AccessReportSpec()
                self.access_report_spec.decode(data[offset:offset+sub_param_length])
            # Add other sub-parameter types as needed
            
            offset += sub_param_length
        
        return param_length


@dataclass
class AccessCommand(LLRPParameter):
    """Access Command Parameter - Contains OpSpecs for tag operations"""
    
    def __init__(self):
        super().__init__(AccessSpecParameterType.ACCESS_COMMAND)
        self.air_protocol_tag_spec = None  # C1G2TagSpec for EPC Gen2
        self.access_command_op_specs = []  # List of OpSpec parameters
        self.custom_parameters = []
    
    def encode(self) -> bytes:
        """Encode AccessCommand"""
        data = b''
        
        # Add air protocol tag spec
        if self.air_protocol_tag_spec:
            data += self.air_protocol_tag_spec.encode()
        
        # Add operation specs
        for op_spec in self.access_command_op_specs:
            data += op_spec.encode()
        
        # Add custom parameters
        for custom in self.custom_parameters:
            data += custom.encode()
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode AccessCommand"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.ACCESS_COMMAND:
            return 0
        
        offset = header_len
        
        # Parse sub-parameters
        while offset < param_length and offset < len(data):
            sub_param_type, sub_param_length, sub_header_len, sub_is_tv = LLRPParameter.parse_header(data, offset)
            
            if sub_param_type is None:
                break
            
            # Parse different OpSpec types
            if sub_param_type == AccessSpecParameterType.C1G2_READ:
                op_spec = C1G2Read()
                op_spec.decode(data[offset:offset+sub_param_length])
                self.access_command_op_specs.append(op_spec)
            elif sub_param_type == AccessSpecParameterType.C1G2_WRITE:
                op_spec = C1G2Write()
                op_spec.decode(data[offset:offset+sub_param_length])
                self.access_command_op_specs.append(op_spec)
            elif sub_param_type == AccessSpecParameterType.C1G2_KILL:
                op_spec = C1G2Kill()
                op_spec.decode(data[offset:offset+sub_param_length])
                self.access_command_op_specs.append(op_spec)
            elif sub_param_type == AccessSpecParameterType.C1G2_LOCK:
                op_spec = C1G2Lock()
                op_spec.decode(data[offset:offset+sub_param_length])
                self.access_command_op_specs.append(op_spec)
            # Add other OpSpec types as needed
            
            offset += sub_param_length
        
        return param_length


@dataclass
class AccessReportSpec(LLRPParameter):
    """Access Report Spec Parameter - Controls AccessSpec reporting"""
    
    def __init__(self, access_report_trigger: int = 1):
        super().__init__(AccessSpecParameterType.ACCESS_REPORT_SPEC)
        self.access_report_trigger = access_report_trigger  # 1=End_Of_AccessSpec
    
    def encode(self) -> bytes:
        """Encode AccessReportSpec"""
        data = struct.pack('!B', self.access_report_trigger)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode AccessReportSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.ACCESS_REPORT_SPEC:
            return 0
        
        offset = header_len
        if len(data) >= offset + 1:
            self.access_report_trigger = struct.unpack('!B', data[offset:offset+1])[0]
        
        return param_length


# C1G2 (EPC Class1 Gen2) Operation Specifications

@dataclass
class C1G2Read(LLRPParameter):
    """C1G2 Read OpSpec - Read data from tag memory"""
    
    def __init__(self, op_spec_id: int = 1, access_password: int = 0,
                 memory_bank: int = 1, word_pointer: int = 2, word_count: int = 0):
        super().__init__(AccessSpecParameterType.C1G2_READ)
        self.op_spec_id = op_spec_id
        self.access_password = access_password  # 32-bit access password
        self.memory_bank = memory_bank  # 0=Reserved, 1=EPC, 2=TID, 3=User
        self.word_pointer = word_pointer  # Starting word address
        self.word_count = word_count  # Number of words to read (0=read to end)
    
    def encode(self) -> bytes:
        """Encode C1G2Read OpSpec"""
        data = struct.pack('!HIBHH',
                          self.op_spec_id,
                          self.access_password,
                          self.memory_bank,
                          self.word_pointer,
                          self.word_count)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2Read OpSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_READ:
            return 0
        
        offset = header_len
        if len(data) >= offset + 9:  # 2+4+1+2+2 = 11, but packed is 9
            self.op_spec_id, self.access_password, self.memory_bank, self.word_pointer, self.word_count = struct.unpack(
                '!HIBHH', data[offset:offset+9])
        
        return param_length


@dataclass
class C1G2Write(LLRPParameter):
    """C1G2 Write OpSpec - Write data to tag memory"""
    
    def __init__(self, op_spec_id: int = 1, access_password: int = 0,
                 memory_bank: int = 3, word_pointer: int = 0, write_data: bytes = b''):
        super().__init__(AccessSpecParameterType.C1G2_WRITE)
        self.op_spec_id = op_spec_id
        self.access_password = access_password
        self.memory_bank = memory_bank  # Usually 3=User memory
        self.word_pointer = word_pointer  # Starting word address
        self.write_data = write_data  # Data to write (must be word-aligned)
    
    def encode(self) -> bytes:
        """Encode C1G2Write OpSpec"""
        # Ensure write_data is word-aligned (even number of bytes)
        write_data = self.write_data
        if len(write_data) % 2 != 0:
            write_data += b'\x00'  # Pad with zero byte
        
        data = struct.pack('!HIBH',
                          self.op_spec_id,
                          self.access_password,
                          self.memory_bank,
                          self.word_pointer)
        
        # Add write data length and data
        data += struct.pack('!H', len(write_data))
        data += write_data
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2Write OpSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_WRITE:
            return 0
        
        offset = header_len
        if len(data) >= offset + 7:  # 2+4+1+2+2 = 11, but packed is 7 for fixed part
            self.op_spec_id, self.access_password, self.memory_bank, self.word_pointer = struct.unpack(
                '!HIBH', data[offset:offset+7])
            offset += 7
            
            # Read write data length and data
            if len(data) >= offset + 2:
                write_data_length = struct.unpack('!H', data[offset:offset+2])[0]
                offset += 2
                
                if len(data) >= offset + write_data_length:
                    self.write_data = data[offset:offset+write_data_length]
        
        return param_length


@dataclass
class C1G2Kill(LLRPParameter):
    """C1G2 Kill OpSpec - Permanently disable a tag"""
    
    def __init__(self, op_spec_id: int = 1, kill_password: int = 0):
        super().__init__(AccessSpecParameterType.C1G2_KILL)
        self.op_spec_id = op_spec_id
        self.kill_password = kill_password  # 32-bit kill password
    
    def encode(self) -> bytes:
        """Encode C1G2Kill OpSpec"""
        data = struct.pack('!HI', self.op_spec_id, self.kill_password)
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2Kill OpSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_KILL:
            return 0
        
        offset = header_len
        if len(data) >= offset + 6:
            self.op_spec_id, self.kill_password = struct.unpack('!HI', data[offset:offset+6])
        
        return param_length


@dataclass
class C1G2Lock(LLRPParameter):
    """C1G2 Lock OpSpec - Lock/unlock tag memory areas"""
    
    def __init__(self, op_spec_id: int = 1, access_password: int = 0,
                 lock_data_field: int = 0, lock_privilege: int = 0):
        super().__init__(AccessSpecParameterType.C1G2_LOCK)
        self.op_spec_id = op_spec_id
        self.access_password = access_password
        self.lock_data_field = lock_data_field  # Bitmap of memory areas to lock
        self.lock_privilege = lock_privilege  # Lock action for each area
    
    def encode(self) -> bytes:
        """Encode C1G2Lock OpSpec"""
        data = struct.pack('!HIBB', 
                          self.op_spec_id,
                          self.access_password,
                          self.lock_data_field,
                          self.lock_privilege)
        
        header = self.encode_header(4 + len(data))
        return header + data
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2Lock OpSpec"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_LOCK:
            return 0
        
        offset = header_len
        if len(data) >= offset + 8:
            self.op_spec_id, self.access_password, self.lock_data_field, self.lock_privilege = struct.unpack(
                '!HIBB', data[offset:offset+8])
        
        return param_length


# OpSpec Result Parameters (for AccessReports)

@dataclass  
class C1G2ReadOpSpecResult(LLRPParameter):
    """C1G2 Read OpSpec Result"""
    
    def __init__(self):
        super().__init__(AccessSpecParameterType.C1G2_READ_OP_SPEC_RESULT)
        self.result = 0  # 0=Success, others are error codes
        self.op_spec_id = 0
        self.read_data = b''
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 Read result"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_READ_OP_SPEC_RESULT:
            return 0
        
        offset = header_len
        if len(data) >= offset + 4:
            self.result, self.op_spec_id = struct.unpack('!BH', data[offset:offset+3])
            offset += 3
            
            # Read data length and data
            if len(data) >= offset + 2:
                read_data_length = struct.unpack('!H', data[offset:offset+2])[0]
                offset += 2
                
                if len(data) >= offset + read_data_length:
                    self.read_data = data[offset:offset+read_data_length]
        
        return param_length


@dataclass
class C1G2WriteOpSpecResult(LLRPParameter):
    """C1G2 Write OpSpec Result"""
    
    def __init__(self):
        super().__init__(AccessSpecParameterType.C1G2_WRITE_OP_SPEC_RESULT)
        self.result = 0  # 0=Success, others are error codes
        self.op_spec_id = 0
        self.num_words_written = 0
    
    def decode(self, data: bytes) -> int:
        """Decode C1G2 Write result"""
        from .protocol import LLRPParameter
        
        param_type, param_length, header_len, is_tv = LLRPParameter.parse_header(data)
        if param_type != AccessSpecParameterType.C1G2_WRITE_OP_SPEC_RESULT:
            return 0
        
        offset = header_len
        if len(data) >= offset + 5:
            self.result, self.op_spec_id, self.num_words_written = struct.unpack('!BHH', data[offset:offset+5])
        
        return param_length


# AccessSpec parameter registry
ACCESSSPEC_PARAMETER_CLASSES = {
    AccessSpecParameterType.ACCESS_SPEC: AccessSpec,
    AccessSpecParameterType.ACCESS_COMMAND: AccessCommand,
    AccessSpecParameterType.ACCESS_REPORT_SPEC: AccessReportSpec,
    AccessSpecParameterType.C1G2_READ: C1G2Read,
    AccessSpecParameterType.C1G2_WRITE: C1G2Write,
    AccessSpecParameterType.C1G2_KILL: C1G2Kill,
    AccessSpecParameterType.C1G2_LOCK: C1G2Lock,
    AccessSpecParameterType.C1G2_READ_OP_SPEC_RESULT: C1G2ReadOpSpecResult,
    AccessSpecParameterType.C1G2_WRITE_OP_SPEC_RESULT: C1G2WriteOpSpecResult,
}