"""Input validation utilities for API endpoints."""

import re
import uuid
from typing import Optional, Any
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)

# UUID regex pattern for validation
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class InputValidator:
    """Centralized input validation utility."""

    @staticmethod
    def validate_uuid(value: str, field_name: str = "id") -> str:
        """Validate UUID format."""
        if not value:
            raise ValueError(f"{field_name} cannot be empty")

        try:
            uuid.UUID(value)
            return value
        except ValueError:
            raise ValueError(f"{field_name} must be a valid UUID, got: {value}")

    @staticmethod
    def validate_org_id(value: str) -> str:
        """Validate organization ID."""
        return InputValidator.validate_uuid(value, "org_id")

    @staticmethod
    def validate_user_id(value: str) -> str:
        """Validate user ID."""
        return InputValidator.validate_uuid(value, "user_id")

    @staticmethod
    def validate_thread_id(value: str) -> str:
        """Validate thread ID."""
        return InputValidator.validate_uuid(value, "thread_id")

    @staticmethod
    def validate_string_length(value: str, min_len: int = 1, max_len: int = 10000, field_name: str = "value") -> str:
        """Validate string length."""
        if not value:
            if min_len > 0:
                raise ValueError(f"{field_name} cannot be empty")
            return value

        if len(value) < min_len:
            raise ValueError(f"{field_name} must be at least {min_len} characters")

        if len(value) > max_len:
            raise ValueError(f"{field_name} must be at most {max_len} characters")

        return value

    @staticmethod
    def validate_email(value: str) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")

        return value

    @staticmethod
    def validate_api_key_format(value: str) -> str:
        """Validate API key format (basic check)."""
        if not value or len(value) < 10:
            raise ValueError("API key format is invalid")

        # Check for common API key patterns
        if not any(char in value for char in ['-', '_']):
            raise ValueError("API key must contain at least one dash or underscore")

        return value

    @staticmethod
    def validate_integer_range(value: int, min_val: int = 0, max_val: int = 10000, field_name: str = "value") -> int:
        """Validate integer is within range."""
        if value < min_val or value > max_val:
            raise ValueError(f"{field_name} must be between {min_val} and {max_val}, got: {value}")

        return value

    @staticmethod
    def sanitize_string(value: str, allow_special: bool = False) -> str:
        """Sanitize string input by removing potentially dangerous characters."""
        if not value:
            return value

        # Always remove null bytes
        value = value.replace('\x00', '')

        if not allow_special:
            # Remove potentially dangerous SQL/scripting characters
            dangerous_patterns = [';', '--', '/*', '*/', 'xp_', 'sp_', '<script', '</script>']
            for pattern in dangerous_patterns:
                value = value.replace(pattern, '')

        return value.strip()


# Pydantic base model with validation
class ValidatedRequestModel(BaseModel):
    """Base model for all validated API requests."""

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        str_strip_whitespace = True

    @validator('*', pre=True)
    def validate_input(cls, v):
        """Validate all string inputs."""
        if isinstance(v, str):
            # Basic sanitization
            v = v.strip()
            if not v:
                return v
            # Remove null bytes
            v = v.replace('\x00', '')
        return v


# Common validated request models
class ValidatedOrgRequest(ValidatedRequestModel):
    """Base request model with org_id validation."""
    org_id: str

    @validator('org_id')
    def validate_org_id_field(cls, v):
        return InputValidator.validate_org_id(v)


class ValidatedThreadRequest(ValidatedOrgRequest):
    """Base request model with thread_id validation."""
    thread_id: str

    @validator('thread_id')
    def validate_thread_id_field(cls, v):
        return InputValidator.validate_thread_id(v)


class ValidatedMessageRequest(ValidatedThreadRequest):
    """Request model for message operations."""
    content: str = Field(..., min_length=1, max_length=50000)

    @validator('content')
    def validate_content(cls, v):
        return InputValidator.validate_string_length(v, min_len=1, max_len=50000, field_name="content")
