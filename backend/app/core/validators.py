"""
Input validation utilities.
"""

import re
import uuid
from typing import Optional
from fastapi import HTTPException, status

# UUID validation regex
UUID_REGEX = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "id") -> str:
    """Validate that a string is a valid UUID."""
    if not value or not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a non-empty string"
        )

    if not UUID_REGEX.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid UUID"
        )

    return value.lower()


def validate_thread_id(thread_id: str) -> str:
    """Validate thread ID."""
    return validate_uuid(thread_id, "thread_id")


def validate_org_id(org_id: str) -> str:
    """Validate organization ID."""
    return validate_uuid(org_id, "org_id")


def validate_user_id(user_id: str) -> str:
    """Validate user ID."""
    return validate_uuid(user_id, "user_id")


def validate_message_content(content: str, max_length: int = 100000) -> str:
    """Validate message content."""
    if not content or not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )

    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be only whitespace"
        )

    if len(content) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message content exceeds maximum length of {max_length} characters"
        )

    return content


def validate_thread_title(title: Optional[str], max_length: int = 200) -> Optional[str]:
    """Validate thread title."""
    if title is None:
        return None

    if not isinstance(title, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread title must be a string"
        )

    title = title.strip()
    if not title:
        return None

    if len(title) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Thread title exceeds maximum length of {max_length} characters"
        )

    return title


def validate_provider_name(provider: Optional[str]) -> Optional[str]:
    """Validate AI provider name."""
    if provider is None:
        return None

    valid_providers = {"openai", "gemini", "perplexity", "kimi", "anthropic", "claude"}
    if provider.lower() not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be one of: {', '.join(valid_providers)}"
        )

    return provider.lower()


def validate_model_name(model: Optional[str]) -> Optional[str]:
    """Validate model name (basic validation)."""
    if model is None:
        return None

    if not isinstance(model, str) or not model.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name must be a non-empty string"
        )

    model = model.strip()
    if len(model) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name is too long"
        )

    # Basic sanity check - no control characters
    if any(ord(c) < 32 for c in model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name contains invalid characters"
        )

    return model


def validate_temperature(temp: Optional[float]) -> Optional[float]:
    """Validate temperature parameter."""
    if temp is None:
        return None

    if not isinstance(temp, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Temperature must be a number"
        )

    if temp < 0 or temp > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Temperature must be between 0 and 2"
        )

    return float(temp)


def validate_max_tokens(max_tokens: Optional[int]) -> Optional[int]:
    """Validate max tokens parameter."""
    if max_tokens is None:
        return None

    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max tokens must be a positive integer"
        )

    if max_tokens > 1000000:  # Reasonable upper limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max tokens cannot exceed 1,000,000"
        )

    return max_tokens


def validate_email(email: Optional[str]) -> Optional[str]:
    """Validate email address."""
    if email is None:
        return None

    if not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email must be a string"
        )

    email = email.strip().lower()

    # Basic email regex
    email_regex = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    if not email_regex.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    if len(email) > 254:  # RFC 5321 limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is too long"
        )

    return email
