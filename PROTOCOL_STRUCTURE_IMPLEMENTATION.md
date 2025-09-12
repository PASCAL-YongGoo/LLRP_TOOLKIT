# LLRP Protocol Structure Implementation

## Overview

All LLRP commands have been implemented according to the exact protocol specification with correct bit field sizes and message structures.

## Message Format

All LLRP messages follow this header format:
```
Rsvd(3) + Ver(3) + Message Type(10) + Message Length(32) + Message ID(32)
```

## Implemented Messages with Exact Protocol Structure

### Version Management Messages

#### GET_SUPPORTED_VERSION (Message Type 46)
```
Header: Rsvd(3) + Ver(3) + 46(10) + Message Length(32) + Message ID(32)
Body: No parameters
```

#### GET_SUPPORTED_VERSION_RESPONSE (Message Type 56)
```
Header: Rsvd(3) + Ver(3) + 56(10) + Message Length(32) + Message ID(32)
Body: CurrentVersion(8) + SupportedVersion(8) + LLRPStatus Parameter
```
- CurrentVersion: 4-bit major + 4-bit minor
- SupportedVersion: 4-bit major + 4-bit minor

#### SET_PROTOCOL_VERSION (Message Type 47)  
```
Header: Rsvd(3) + Ver(3) + 47(10) + Message Length(32) + Message ID(32)
Body: ProtocolVersion(8)
```
- ProtocolVersion: 4-bit major + 4-bit minor

#### SET_PROTOCOL_VERSION_RESPONSE (Message Type 57)
```
Header: Rsvd(3) + Ver(3) + 57(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter
```

### Reader Management Messages

#### GET_READER_CAPABILITIES (Message Type 1)
```
Header: Rsvd(3) + Ver(3) + 1(10) + Message Length(32) + Message ID(32)  
Body: RequestedData(8) + Custom Parameter(0-n)
```

#### GET_READER_CAPABILITIES_RESPONSE (Message Type 11)
```
Header: Rsvd(3) + Ver(3) + 11(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter(48) + GeneralDeviceCapabilities Parameter(0-1) + 
      LLRPCapabilities Parameter(0-1) + RegulatoryCapabilities Parameter(0-1) + 
      AirProtocolLLRPCapabilities Parameter(0-1) + Custom Parameter(0-n)
```

### ROSpec Messages

#### ADD_ROSPEC (Message Type 20)
```
Header: Rsvd(3) + Ver(3) + 20(10) + Message Length(32) + Message ID(32)
Body: ROSpec Parameter(0-n)
```

#### ADD_ROSPEC_RESPONSE (Message Type 30)
```
Header: Rsvd(3) + Ver(3) + 30(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter
```

#### DELETE_ROSPEC (Message Type 21)
```
Header: Rsvd(3) + Ver(3) + 21(10) + Message Length(32) + Message ID(32)
Body: ROSpecID(32)
```

#### DELETE_ROSPEC_RESPONSE (Message Type 31)
```
Header: Rsvd(3) + Ver(3) + 31(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter
```

#### START_ROSPEC (Message Type 22)
```
Header: Rsvd(3) + Ver(3) + 22(10) + Message Length(32) + Message ID(32)
Body: ROSpecID(32)
```

#### START_ROSPEC_RESPONSE (Message Type 32)
```
Header: Rsvd(3) + Ver(3) + 32(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter
```

## Implementation Details

### Binary Encoding
- All multi-byte fields use network byte order (big-endian)
- Bit fields are packed according to LLRP specification
- Version fields use 4-bit major + 4-bit minor encoding

### Parameter Structure
- Parameters use TLV (Type-Length-Value) or TV (Type-Value) encoding
- Parameter types are defined in ParameterType enum
- LLRPStatus parameter is consistently used in response messages

### Message Classes
Each message type has a corresponding Python class with:
- Proper encoding/decoding methods
- Field validation
- Helper methods for version handling (where applicable)

## Key Features

### Version Handling
- GET_SUPPORTED_VERSION_RESPONSE provides both current and supported versions
- SET_PROTOCOL_VERSION uses single byte encoding (4+4 bits)
- Helper methods for major/minor version extraction

### Protocol Compliance
- Exact bit field sizes as specified
- Proper parameter ordering
- Complete message structure implementation

### Error Handling
- LLRPStatus parameters in all response messages
- Proper error code propagation
- Timeout and connection error handling

## Usage Examples

### Version Management
```python
# Get supported versions
msg = GetSupportedVersion(msg_id=1)
response = client.send_message_sync(msg)

current_major = response.get_current_version_major()
current_minor = response.get_current_version_minor()

# Set protocol version  
version_msg = SetProtocolVersion(msg_id=2, protocol_version=0x11)  # Version 1.1
response = client.send_message_sync(version_msg)
```

### Reader Capabilities
```python
# Request all capabilities
caps_msg = GetReaderCapabilities(msg_id=1, requested_data=0xFF)
response = client.send_message_sync(caps_msg)
```

### ROSpec Operations
```python
# Delete specific ROSpec
delete_msg = DeleteROSpec(msg_id=1, rospec_id=100)
response = client.send_message_sync(delete_msg)

# Start ROSpec
start_msg = StartROSpec(msg_id=2, rospec_id=100)  
response = client.send_message_sync(start_msg)
```

## Testing

All message structures have been validated with:
- Unit tests for encoding/decoding
- Bit field manipulation tests  
- Protocol compliance verification
- Integration testing with real readers

## Recent Protocol Structure Updates

### Additional Message Types Implemented

#### RO_ACCESS_REPORT (Message Type 61)
```
Header: Rsvd(3) + Ver(3) + 61(10) + Message Length(32) + Message ID(32)
Body: TagReportData Parameter (0-n) + RFSurveyReportData Parameter (0-n) + Custom Parameter (0-n)
```
- Enhanced with RFSurveyReportData parameter support (type 242)
- Added custom parameter handling for vendor extensions
- Maintains backward compatibility with existing TagReportData parsing

#### KEEPALIVE (Message Type 62)
```
Header: Rsvd(3) + Ver(3) + 62(10) + Message Length(32) + Message ID(32)
Body: No parameters
```

#### KEEPALIVE_ACK (Message Type 72)
```
Header: Rsvd(3) + Ver(3) + 72(10) + Message Length(32) + Message ID(32)
Body: No parameters
```

#### READER_EVENT_NOTIFICATION (Message Type 63)
```
Header: Rsvd(3) + Ver(3) + 63(10) + Message Length(32) + Message ID(32)
Body: ReaderEventNotificationData Parameter
```

#### ENABLE_EVENTS_AND_REPORTS (Message Type 64)
```
Header: Rsvd(3) + Ver(3) + 64(10) + Message Length(32) + Message ID(32)
Body: No parameters
```

#### ERROR_MESSAGE (Message Type 100)
```
Header: Rsvd(3) + Ver(3) + 100(10) + Message Length(32) + Message ID(32)
Body: LLRPStatus Parameter
```

#### GET_READER_CONFIG (Message Type 2) - Updated Structure
```
Header: Rsvd(3) + Ver(3) + 2(10) + Message Length(32) + Message ID(32)
Body: Antenna ID (16) + RequestedData (8) + GPIPortNum (16) + GPOPortNum (16) + Custom Parameter (0-n)
```
- Updated from previous implementation to match exact protocol specification
- Added GPI/GPO port number fields
- Enhanced custom parameter support

### New Parameter Types

#### RF Survey Report Data Parameter (Type 242)
```
Type: 242 (0x00F2)
Structure: TLV parameter containing RF survey measurement data
Sub-parameters: ROSpecID, SpecIndex, AntennaID, PeakRSSI, Frequency, Timestamp
```

### Protocol Compliance Enhancements

- **Exact Bit Field Implementation**: All message structures now match precise bit field specifications
- **Network Byte Order**: Consistent big-endian encoding across all multi-byte fields
- **Custom Parameter Support**: Enhanced handling of vendor-specific extensions
- **Robust Parameter Parsing**: Improved error handling and parameter validation
- **Complete Message Coverage**: All standard LLRP v1.0.1 message types implemented

### Usage Examples - Updated

#### RF Survey Report Handling
```python
# Access RF survey data from RO_ACCESS_REPORT
report = ROAccessReport(msg_id=1)
# ... decode from received data ...

rf_survey_count = report.get_rf_survey_count()
antenna_1_surveys = report.get_rf_surveys_by_antenna(1)
```

#### Enhanced Reader Configuration
```python
# Request reader config with GPI/GPO ports
config_msg = GetReaderConfig(
    msg_id=1,
    antenna_id=0,  # All antennas
    requested_data=0xFF,  # All configuration data
    gpi_port_num=1,  # GPI port 1
    gpo_port_num=1   # GPO port 1
)
response = client.send_message_sync(config_msg)
```

#### Event Handling
```python
# Enable events and reports
enable_msg = EnableEventsAndReports(msg_id=1)
client.send_message_sync(enable_msg)

# Handle reader event notifications
def handle_event(notification: ReaderEventNotification):
    event_data = notification.reader_event_notification_data
    # Process event data...
```

This implementation provides complete LLRP v1.0.1 protocol compliance with exact bit-level accuracy and enhanced functionality for RF surveys, events, and configuration management.