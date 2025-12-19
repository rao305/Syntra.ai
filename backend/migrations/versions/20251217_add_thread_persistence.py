"""Add persistent thread storage table.

Revision ID: 013
Revises: 012
Create Date: 2025-12-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create threads table for persistent conversation storage
    op.create_table(
        "threads",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("turns", sa.Text(), nullable=True),  # JSON array of turns
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),  # JSON metadata
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_threads_updated_at"), "threads", ["updated_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_threads_updated_at"), table_name="threads")

    # Drop table
    op.drop_table("threads")

