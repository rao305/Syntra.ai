"""
Safe query builder that prevents SQL injection.
All dynamic values MUST be passed as parameters.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)


class SafeQueryBuilder:
    """
    Safe query builder that prevents SQL injection.
    All dynamic values MUST be passed as parameters.
    """

    # Allowlist of valid table names
    VALID_TABLES = frozenset({
        "users", "organizations", "threads", "messages",
        "api_keys", "audit_logs", "collaboration_runs",
        "collaboration_stages", "subscriptions", "usage_records",
        "conversation_memory"
    })

    # Allowlist of valid column names
    VALID_COLUMNS = frozenset({
        "id", "org_id", "user_id", "thread_id", "created_at",
        "updated_at", "content", "role", "provider", "model",
        "status", "email", "name", "type", "messages", "metadata",
        "title", "is_active", "api_key_encrypted", "key_type"
    })

    @classmethod
    def validate_identifier(cls, name: str, valid_set: frozenset) -> str:
        """Validate and return a safe identifier."""
        # Remove any non-alphanumeric characters except underscore
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        if clean_name not in valid_set:
            raise ValueError(f"Invalid identifier: {name}")
        return clean_name

    @classmethod
    def validate_table(cls, table_name: str) -> str:
        return cls.validate_identifier(table_name, cls.VALID_TABLES)

    @classmethod
    def validate_column(cls, column_name: str) -> str:
        return cls.validate_identifier(column_name, cls.VALID_COLUMNS)

    @classmethod
    async def execute_safe(
        cls,
        db: AsyncSession,
        query: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute a parameterized query safely."""
        # Ensure query uses : param syntax, not f-strings
        if re.search(r'\{.*?\}', query):
            raise ValueError("Query contains f-string formatting. Use : param syntax.")

        logger.debug(f"Executing safe query: {query[:100]}...")
        return await db.execute(text(query), params)

