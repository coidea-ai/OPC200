"""OPC200 - One Person Company AI Support Platform."""

from src.exceptions import (
    OPC200Error,
    JournalError,
    EntryNotFoundError,
    EntryValidationError,
    StorageError,
    VectorStoreError,
    SecurityError,
    EncryptionError,
    VaultError,
    AccessDeniedError,
    KeyManagementError,
    PatternError,
    InsufficientDataError,
    SchedulerError,
    CronParseError,
    TaskExecutionError,
    InsightError,
    ValidationError,
    ConfigurationError,
)

__version__ = "2.2.0"

__all__ = [
    # Exceptions
    "OPC200Error",
    "JournalError",
    "EntryNotFoundError",
    "EntryValidationError",
    "StorageError",
    "VectorStoreError",
    "SecurityError",
    "EncryptionError",
    "VaultError",
    "AccessDeniedError",
    "KeyManagementError",
    "PatternError",
    "InsufficientDataError",
    "SchedulerError",
    "CronParseError",
    "TaskExecutionError",
    "InsightError",
    "ValidationError",
    "ConfigurationError",
    # Version
    "__version__",
]
