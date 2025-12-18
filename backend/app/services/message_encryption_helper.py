"""Helper functions for integrating E2E encryption into message operations."""
from typing import Optional, Dict, Any
from app.models.message import Message, MessageRole
from app.services.chat_encryption import chat_encryption_service

import logging
logger = logging.getLogger(__name__)


async def create_encrypted_message(
    thread_id: str,
    user_id: str,
    role: MessageRole,
    content: str,
    **kwargs
) -> Message:
    """
    Create a message with encryption.

    Args:
        thread_id: Thread ID
        user_id: User ID (owner of message)
        role: Message role (user, assistant, system)
        content: Message content to encrypt
        **kwargs: Additional message fields (provider, model, tokens, etc.)

    Returns:
        Message object with encrypted content
    """
    # Encrypt content
    encrypted_content = chat_encryption_service.encrypt_message(
        content=content,
        user_id=user_id
    )

    # Create message
    message = Message(
        thread_id=thread_id,
        user_id=user_id,
        role=role,
        content=content,  # Keep plaintext for search/indexing
        encrypted_content=encrypted_content,
        encryption_key_id="v1",  # Version identifier
        **kwargs
    )

    return message


async def decrypt_message_content(message: Message) -> str:
    """
    Decrypt message content if encrypted, otherwise return plaintext.

    Args:
        message: Message object

    Returns:
        Decrypted or plaintext content
    """
    if message.encrypted_content and message.user_id:
        try:
            return chat_encryption_service.decrypt_message(
                encrypted_content=message.encrypted_content,
                user_id=message.user_id
            )
        except Exception as e:
            # Fallback to plaintext if decryption fails
            logger.info("Decryption failed for message {message.id}: {e}")
            return message.content or "[Decryption Error]"

    return message.content or ""


def serialize_message_for_api(
    message: Message,
    include_encrypted: bool = False
) -> Dict[str, Any]:
    """
    Serialize message for API response.

    Args:
        message: Message object
        include_encrypted: Whether to include encrypted_content field

    Returns:
        Serialized message dictionary
    """
    data = {
        "id": message.id,
        "thread_id": message.thread_id,
        "user_id": message.user_id,
        "role": message.role.value,
        "content": message.content,  # Always include plaintext for display
        "provider": message.provider,
        "model": message.model,
        "prompt_tokens": message.prompt_tokens,
        "completion_tokens": message.completion_tokens,
        "total_tokens": message.total_tokens,
        "citations": message.citations,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "sequence": message.sequence,
    }

    # Optional: Include encryption metadata
    if include_encrypted:
        data["is_encrypted"] = message.encrypted_content is not None
        data["encryption_key_id"] = message.encryption_key_id

    return data


async def batch_decrypt_messages(
    messages: list[Message]
) -> list[Dict[str, Any]]:
    """
    Decrypt multiple messages efficiently.

    Args:
        messages: List of message objects

    Returns:
        List of serialized messages with decrypted content
    """
    result = []

    for message in messages:
        content = await decrypt_message_content(message)
        serialized = serialize_message_for_api(message)
        serialized["content"] = content  # Override with decrypted content
        result.append(serialized)

    return result
