"""
Structured Logging Module - Centralized logging with structured output.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class Logger:
    """Structured logger wrapper."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.handlers = []
        
        # Prevent propagation to root logger
        self._logger.propagate = False
    
    def add_console_handler(self, level: int = logging.INFO) -> "Logger":
        """Add console handler with structured formatting."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(StructuredFormatter())
        self._logger.addHandler(handler)
        return self
    
    def add_file_handler(self, log_path: Path, level: int = logging.INFO) -> "Logger":
        """Add file handler with structured formatting."""
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_path)
        handler.setLevel(level)
        handler.setFormatter(StructuredFormatter())
        self._logger.addHandler(handler)
        return self
    
    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal log method with extra fields support."""
        extra = kwargs.pop("extra", {})
        extra.update(kwargs)
        
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "",
            0,
            message,
            (),
            None,
        )
        record.extra = extra
        
        self._logger.handle(record)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(message, extra=kwargs)


class ContextualLogger(Logger):
    """Logger with context fields that are added to every log entry."""
    
    def __init__(self, name: str, context: dict[str, Any], level: int = logging.INFO):
        super().__init__(name, level)
        self._context = context
    
    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log with merged context."""
        extra = self._context.copy()
        extra.update(kwargs.pop("extra", {}))
        extra.update(kwargs)
        super()._log(level, message, extra=extra)


# Module-level convenience functions
_default_logger: Optional[Logger] = None


def get_logger(name: str = "opc200", level: int = logging.INFO) -> Logger:
    """Get or create default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = Logger(name, level).add_console_handler()
    return _default_logger


def configure_logging(
    log_path: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> Logger:
    """Configure structured logging with console and optional file output."""
    logger = Logger("opc200", min(console_level, file_level))
    logger.add_console_handler(console_level)
    
    if log_path:
        logger.add_file_handler(log_path, file_level)
    
    global _default_logger
    _default_logger = logger
    return logger


# Audit logging for security events
class AuditLogger:
    """Specialized logger for security audit events."""
    
    def __init__(self, log_path: Path):
        self._logger = Logger("opc200.audit", logging.INFO)
        self._logger.add_file_handler(log_path, logging.INFO)
    
    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        success: bool,
        details: Optional[dict] = None,
    ) -> None:
        """Log access attempt."""
        self._logger.info(
            f"Access attempt: {action} on {resource}",
            user_id=user_id,
            resource=resource,
            action=action,
            success=success,
            details=details or {},
        )
    
    def log_auth(
        self,
        user_id: str,
        method: str,
        success: bool,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log authentication attempt."""
        self._logger.info(
            f"Authentication: {method}",
            user_id=user_id,
            method=method,
            success=success,
            ip_address=ip_address,
        )
    
    def log_data_access(
        self,
        user_id: str,
        data_type: str,
        operation: str,
        record_id: Optional[str] = None,
    ) -> None:
        """Log sensitive data access."""
        self._logger.info(
            f"Data access: {operation} on {data_type}",
            user_id=user_id,
            data_type=data_type,
            operation=operation,
            record_id=record_id,
        )
