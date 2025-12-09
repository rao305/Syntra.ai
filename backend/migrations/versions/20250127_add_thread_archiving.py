"""Add archiving support to threads.

Revision ID: 010
Revises: 009
Create Date: 2025-01-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add archived column
    op.add_column(
        "threads",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false")
    )
    
    # Add archived_at column
    op.add_column(
        "threads",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )
    
    # Create index for filtering archived threads (non-archived threads for sidebar)
    op.create_index(
        "idx_threads_org_archived_updated",
        "threads",
        ["org_id", "archived", "updated_at"],
        unique=False
    )
    
    # Create partial index for non-archived threads (more efficient for sidebar)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_org_archived_updated_partial
        ON threads (org_id, updated_at DESC)
        WHERE archived = false
    """)
    
    # Create full-text search index for title and last_message_preview
    # Using GIN index for efficient text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_fulltext_search 
        ON threads USING gin(
            to_tsvector('english', 
                coalesce(title, '') || ' ' || 
                coalesce(last_message_preview, '')
            )
        )
    """)


def downgrade() -> None:
    # Drop full-text search index
    op.execute("DROP INDEX IF EXISTS idx_threads_fulltext_search")
    
    # Drop partial index
    op.execute("DROP INDEX IF EXISTS idx_threads_org_archived_updated_partial")
    
    # Drop index
    op.drop_index("idx_threads_org_archived_updated", table_name="threads")
    
    # Drop columns
    op.drop_column("threads", "archived_at")
    op.drop_column("threads", "archived")

