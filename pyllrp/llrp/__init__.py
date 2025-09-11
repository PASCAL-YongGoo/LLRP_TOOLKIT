"""
Pure Python LLRP (Low Level Reader Protocol) Implementation

A cross-platform Python library for communicating with RFID readers
using the EPCglobal LLRP v1.0.1 protocol.

No external dependencies - works on Windows, Linux, and macOS.
"""

__version__ = "0.1.0"
__author__ = "PyLLRP Contributors"

from .client import LLRPClient
from .protocol import (
    LLRPConnection,
    MessageType,
    ParameterType,
    AirProtocol
)
from .messages import (
    ROSpec,
    ROBoundarySpec,
    ROSpecStartTrigger,
    ROSpecStopTrigger,
    AISpec,
    AISpecStopTrigger,
    InventoryParameterSpec,
    ROReportSpec,
    TagReportContentSelector,
    TagReportData,
    ROAccessReport
)
from .parameters import (
    EPCData,
    EPC96,
    ROSpecID,
    AntennaID,
    PeakRSSI,
    TagSeenCount
)
from .config_parameters import (
    AntennaConfiguration,
    RFTransmitter,
    RFReceiver,
    AntennaProperties,
    EventsAndReports,
    KeepaliveSpec
)
from .capabilities_parameters import (
    GeneralDeviceCapabilities,
    LLRPCapabilities,
    RegulatoryCapabilities,
    UHFBandCapabilities,
    AirProtocolLLRPCapabilities
)
from .errors import (
    LLRPError,
    LLRPParameterError,
    LLRPROSpecError,
    LLRPDeviceError,
    LLRPConnectionError,
    LLRPTimeoutError,
    LLRPStatusCode,
    check_llrp_response
)

__all__ = [
    # Core classes
    'LLRPClient',
    'LLRPConnection',
    
    # Enums and types
    'MessageType',
    'ParameterType',
    'AirProtocol',
    'LLRPStatusCode',
    
    # ROSpec classes
    'ROSpec',
    'ROBoundarySpec',
    'ROSpecStartTrigger',
    'ROSpecStopTrigger',
    'AISpec',
    'AISpecStopTrigger',
    'InventoryParameterSpec',
    'ROReportSpec',
    'TagReportContentSelector',
    
    # Report classes
    'TagReportData',
    'ROAccessReport',
    
    # Parameter classes
    'EPCData',
    'EPC96',
    'ROSpecID',
    'AntennaID',
    'PeakRSSI',
    'TagSeenCount',
    
    # Configuration parameter classes
    'AntennaConfiguration',
    'RFTransmitter',
    'RFReceiver', 
    'AntennaProperties',
    'EventsAndReports',
    'KeepaliveSpec',
    
    # Capabilities parameter classes
    'GeneralDeviceCapabilities',
    'LLRPCapabilities',
    'RegulatoryCapabilities',
    'UHFBandCapabilities',
    'AirProtocolLLRPCapabilities',
    
    # Error classes
    'LLRPError',
    'LLRPParameterError',
    'LLRPROSpecError',
    'LLRPDeviceError',
    'LLRPConnectionError',
    'LLRPTimeoutError',
    
    # Utility functions
    'check_llrp_response'
]