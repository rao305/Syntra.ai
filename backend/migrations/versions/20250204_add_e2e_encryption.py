"""Add E2E encryption fields to messages table.

Revision ID: 007
Revises: 006
Create Date: 2025-02-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add E2E encryption columns to messages table
    op.add_column(
        "messages",
        sa.Column("encrypted_content", sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        "messages",
        sa.Column("encryption_key_id", sa.String(), nullable=True)
    )
    # Create index for encryption key lookups
    op.create_index(
        "ix_messages_encryption_key_id",
        "messages",
        ["encryption_key_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_messages_encryption_key_id", table_name="messages")
    op.drop_column("messages", "encryption_key_id")
    op.drop_column("messages", "encrypted_content")
