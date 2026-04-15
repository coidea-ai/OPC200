"""
OPC200 Custom Exceptions Module

Defines the exception hierarchy for the OPC200 project.
All custom exceptions should inherit from OPC200Error.
"""


class OPC200Error(Exception):
    """Base exception for all OPC200 errors.
    
    This is the root of the exception hierarchy and should be caught
    when you want to handle any OPC200-specific error.
    
    Attributes:
        message: Error message
        error_code: Optional error code for programmatic handling
        details: Optional dictionary with additional error details
    """
    
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


# Security Exceptions
class SecurityError(OPC200Error):
    """Base exception for security-related errors."""
    pass


class EncryptionError(SecurityError):
    """Raised when encryption/decryption operations fail."""
    pass


class VaultError(SecurityError):
    """Raised when vault operations fail."""
    pass


class AccessDeniedError(SecurityError):
    """Raised when access is denied due to permissions."""
    pass


class KeyManagementError(SecurityError):
    """Raised when key operations fail."""
    pass


# Pattern Analysis Exceptions
class PatternError(OPC200Error):
    """Base exception for pattern analysis errors."""
    pass


class InsufficientDataError(PatternError):
    """Raised when there's not enough data for analysis."""
    pass


# Insight Generation Exceptions
class InsightError(OPC200Error):
    """Base exception for insight generation errors."""
    pass


# Validation Exceptions
class ValidationError(OPC200Error):
    """Raised when input validation fails."""
    pass


# Configuration Exceptions
class ConfigurationError(OPC200Error):
    """Raised when configuration is invalid or missing."""
    pass
