"""
LLRP Error Codes and Exception Handling

Based on LLRP v1.0.1 specification Section 16.2.8.1.1 (LLRPStatus)
"""

from enum import IntEnum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LLRPStatusCode(IntEnum):
    """LLRP Status Codes from LLRP v1.0.1 specification"""
    
    # Success
    M_Success = 0
    
    # Parameter Errors (1-99)
    M_ParameterError = 100
    M_FieldError = 101
    M_UnexpectedParameter = 102
    M_MissingParameter = 103
    M_DuplicateParameter = 104
    M_OverflowParameter = 105
    M_OverflowField = 106
    M_UnknownParameter = 107
    M_UnknownField = 108
    M_UnsupportedMessage = 109
    M_UnsupportedVersion = 110
    M_UnsupportedParameter = 111
    
    # ROSpec Errors (200-299)
    M_NoSuchROSpec = 200
    M_NoSuchAccessSpec = 201
    M_ROSpecCurrentlyDisabled = 202
    M_ROSpecCurrentlyEnabled = 203
    M_NoMoreROSpecs = 204
    M_NoMoreAccessSpecs = 205
    M_AccessSpecCurrentlyDisabled = 206
    M_AccessSpecCurrentlyEnabled = 207
    M_ROSpecNotConfigured = 208
    M_AccessSpecNotConfigured = 209
    
    # Device Errors (300-399)
    M_DeviceError = 300
    M_OutOfRange = 301
    M_NoAntennaConnected = 302
    M_ReaderTemperatureTooHigh = 303
    M_ReaderOverheated = 304
    M_ReaderInitializationFailure = 305
    
    # Air Protocol Errors (400-499) 
    M_InvalidFrequency = 400
    M_InvalidAntennaID = 401
    M_InvalidPowerLevel = 402
    M_CycleCountExceeded = 403
    M_InvalidParameter = 404
    
    # Other Errors (500+)
    M_Other = 500
    A_Invalid = 501
    A_OutOfRange = 502


class LLRPError(Exception):
    """Base LLRP Exception"""
    
    def __init__(self, status_code: int, description: str = "", details: Optional[dict] = None):
        self.status_code = status_code
        self.description = description
        self.details = details or {}
        
        # Get human-readable status name
        try:
            self.status_name = LLRPStatusCode(status_code).name
        except ValueError:
            self.status_name = f"UnknownStatus_{status_code}"
        
        super().__init__(f"LLRP Error {status_code} ({self.status_name}): {description}")


class LLRPParameterError(LLRPError):
    """LLRP Parameter-related errors"""
    pass


class LLRPROSpecError(LLRPError):
    """LLRP ROSpec-related errors"""
    pass


class LLRPDeviceError(LLRPError):
    """LLRP Device-related errors"""
    pass


class LLRPConnectionError(LLRPError):
    """LLRP Connection-related errors"""
    pass


class LLRPTimeoutError(LLRPError):
    """LLRP Timeout errors"""
    
    def __init__(self, description: str = "Operation timed out", timeout_seconds: float = 0):
        super().__init__(LLRPStatusCode.M_Other, description, {'timeout': timeout_seconds})
        self.timeout_seconds = timeout_seconds


def get_error_description(status_code: int) -> str:
    """Get human-readable description for LLRP status code"""
    
    descriptions = {
        # Success
        LLRPStatusCode.M_Success: "Operation completed successfully",
        
        # Parameter Errors
        LLRPStatusCode.M_ParameterError: "General parameter error",
        LLRPStatusCode.M_FieldError: "Field contains invalid value",
        LLRPStatusCode.M_UnexpectedParameter: "Unexpected parameter encountered",
        LLRPStatusCode.M_MissingParameter: "Required parameter missing",
        LLRPStatusCode.M_DuplicateParameter: "Duplicate parameter not allowed",
        LLRPStatusCode.M_OverflowParameter: "Too many parameters",
        LLRPStatusCode.M_OverflowField: "Field value out of range",
        LLRPStatusCode.M_UnknownParameter: "Parameter type not recognized",
        LLRPStatusCode.M_UnknownField: "Field not recognized",
        LLRPStatusCode.M_UnsupportedMessage: "Message type not supported",
        LLRPStatusCode.M_UnsupportedVersion: "LLRP version not supported",
        LLRPStatusCode.M_UnsupportedParameter: "Parameter not supported",
        
        # ROSpec Errors
        LLRPStatusCode.M_NoSuchROSpec: "ROSpec with specified ID does not exist",
        LLRPStatusCode.M_NoSuchAccessSpec: "AccessSpec with specified ID does not exist",
        LLRPStatusCode.M_ROSpecCurrentlyDisabled: "ROSpec is currently disabled",
        LLRPStatusCode.M_ROSpecCurrentlyEnabled: "ROSpec is currently enabled",
        LLRPStatusCode.M_NoMoreROSpecs: "Maximum number of ROSpecs reached",
        LLRPStatusCode.M_NoMoreAccessSpecs: "Maximum number of AccessSpecs reached",
        LLRPStatusCode.M_AccessSpecCurrentlyDisabled: "AccessSpec is currently disabled",
        LLRPStatusCode.M_AccessSpecCurrentlyEnabled: "AccessSpec is currently enabled",
        LLRPStatusCode.M_ROSpecNotConfigured: "ROSpec configuration incomplete",
        LLRPStatusCode.M_AccessSpecNotConfigured: "AccessSpec configuration incomplete",
        
        # Device Errors
        LLRPStatusCode.M_DeviceError: "General device error",
        LLRPStatusCode.M_OutOfRange: "Requested value out of supported range",
        LLRPStatusCode.M_NoAntennaConnected: "No antenna connected to specified port",
        LLRPStatusCode.M_ReaderTemperatureTooHigh: "Reader temperature exceeds safe operating limit",
        LLRPStatusCode.M_ReaderOverheated: "Reader has overheated and shut down",
        LLRPStatusCode.M_ReaderInitializationFailure: "Reader failed to initialize properly",
        
        # Air Protocol Errors
        LLRPStatusCode.M_InvalidFrequency: "Specified frequency not supported",
        LLRPStatusCode.M_InvalidAntennaID: "Invalid antenna ID specified",
        LLRPStatusCode.M_InvalidPowerLevel: "Power level out of supported range",
        LLRPStatusCode.M_CycleCountExceeded: "Maximum cycle count exceeded",
        LLRPStatusCode.M_InvalidParameter: "Parameter value invalid for current configuration",
        
        # Other Errors
        LLRPStatusCode.M_Other: "Other error not specified above",
        LLRPStatusCode.A_Invalid: "Invalid parameter value",
        LLRPStatusCode.A_OutOfRange: "Parameter value out of range",
    }
    
    return descriptions.get(status_code, f"Unknown error code: {status_code}")


def create_llrp_exception(status_code: int, description: str = "") -> LLRPError:
    """Factory function to create appropriate LLRP exception based on status code"""
    
    if not description:
        description = get_error_description(status_code)
    
    # Categorize errors and create appropriate exception type
    if 100 <= status_code <= 199:
        return LLRPParameterError(status_code, description)
    elif 200 <= status_code <= 299:
        return LLRPROSpecError(status_code, description)
    elif 300 <= status_code <= 399:
        return LLRPDeviceError(status_code, description)
    elif 400 <= status_code <= 499:
        return LLRPParameterError(status_code, description)  # Air protocol is parameter-related
    else:
        return LLRPError(status_code, description)


def is_success(status_code: int) -> bool:
    """Check if status code indicates success"""
    return status_code == LLRPStatusCode.M_Success


def is_error(status_code: int) -> bool:
    """Check if status code indicates an error"""
    return status_code != LLRPStatusCode.M_Success


def log_llrp_status(status_code: int, description: str = "", level: int = logging.INFO):
    """Log LLRP status with appropriate level"""
    
    if is_success(status_code):
        logger.info(f"LLRP Success: {description or 'Operation completed'}")
    else:
        status_name = getattr(LLRPStatusCode(status_code), 'name', f'Code{status_code}')
        error_desc = description or get_error_description(status_code)
        
        if 300 <= status_code <= 399:  # Device errors are more serious
            logger.error(f"LLRP Device Error {status_code} ({status_name}): {error_desc}")
        elif 200 <= status_code <= 299:  # ROSpec errors
            logger.warning(f"LLRP ROSpec Error {status_code} ({status_name}): {error_desc}")
        else:  # Parameter and other errors
            logger.warning(f"LLRP Error {status_code} ({status_name}): {error_desc}")


# Quick reference for common operations
def check_llrp_response(status_code: int, description: str = "", raise_on_error: bool = True):
    """
    Check LLRP response status and optionally raise exception
    
    Args:
        status_code: LLRP status code
        description: Additional description
        raise_on_error: Whether to raise exception on error status
        
    Returns:
        True if success, False if error (when raise_on_error=False)
        
    Raises:
        LLRPError: If status indicates error and raise_on_error=True
    """
    log_llrp_status(status_code, description)
    
    if is_error(status_code) and raise_on_error:
        raise create_llrp_exception(status_code, description)
    
    return is_success(status_code)