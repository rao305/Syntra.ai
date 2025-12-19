"""
Centralized logging configuration for Syntra.
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import json
from pathlib import Path
import re


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "org_id"):
            log_entry["org_id"] = record.org_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        return json.dumps(log_entry)


class DevelopmentFormatter(logging.Formatter):
    """Colorized formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data (API keys, tokens, passwords) in logs."""

    # Patterns for sensitive data that should be masked
    SENSITIVE_PATTERNS = [
        # API Keys and tokens
        (r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', r'\1***MASKED***'),
        (r'(secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', r'\1***MASKED***'),
        (r'(token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', r'\1***MASKED***'),
        (r'(password)["\']?\s*[:=]\s*["\']?([^\s"\']+)["\']?', r'\1***MASKED***'),
        (r'(authorization|bearer)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?', r'\1***MASKED***'),

        # AWS credentials
        (r'AKIA[0-9A-Z]{16}', '***AWS_KEY_MASKED***'),

        # OpenAI API keys
        (r'sk-[a-zA-Z0-9]{20,}', '***OPENAI_KEY_MASKED***'),

        # Generic patterns for key=value with secrets
        (r'(openai_api_key|anthropic_key|google_api_key|stripe_key)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', r'\1***MASKED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data from log records."""
        # Mask in message
        if record.msg:
            msg_str = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                msg_str = re.sub(pattern, replacement, msg_str, flags=re.IGNORECASE)
            record.msg = msg_str

        # Mask in args if present
        if record.args:
            if isinstance(record.args, dict):
                for key, value in record.args.items():
                    if value and isinstance(value, str):
                        for pattern, replacement in self.SENSITIVE_PATTERNS:
                            record.args[key] = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    re.sub(pattern, replacement, str(arg), flags=re.IGNORECASE)
                    if isinstance(arg, str) else arg
                    for arg in record.args
                    for pattern, replacement in self.SENSITIVE_PATTERNS
                )

        # Mask in extra fields
        if hasattr(record, 'org_id') and record.org_id:
            # Mask org IDs partially: show first 8 chars
            org_id = str(record.org_id)
            if len(org_id) > 8:
                record.org_id = org_id[:8] + '...***'

        # Mask in exception info
        if record.exc_text:
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.exc_text = re.sub(pattern, replacement, record.exc_text, flags=re.IGNORECASE)

        return True


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Use JSON format (for production)
        log_file: Optional file path for file logging
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_logs:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(DevelopmentFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))

    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)

    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        # Add sensitive data filter to file handler too
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info("Logging configured", extra={"level": level, "json_logs": json_logs})


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


# Context-aware logger adapter
class ContextLogger(logging.LoggerAdapter):
    """Logger that includes request context in all log messages."""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(
    name: str,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ContextLogger:
    """Get a context-aware logger."""
    logger = logging.getLogger(name)
    context = {}
    if org_id:
        context["org_id"] = org_id
    if user_id:
        context["user_id"] = user_id
    if request_id:
        context["request_id"] = request_id
    return ContextLogger(logger, context)

