"""Make file_data nullable and add storage_bucket column for Supabase Storage migration."""

from alembic import op
import sqlalchemy as sa

revision = '20251219_add_storage_columns'
down_revision = '20251219_add_pgvector'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make file_data nullable and add storage_bucket column."""
    # Make file_data nullable to support Supabase Storage
    op.alter_column(
        'attachments',
        'file_data',
        existing_type=sa.LargeBinary(),
        nullable=True
    )

    # Add storage_bucket column with default value
    op.add_column(
        'attachments',
        sa.Column('storage_bucket', sa.String(), nullable=True)
    )

    # Set default value for existing rows
    op.execute("UPDATE attachments SET storage_bucket = 'attachments' WHERE storage_bucket IS NULL")


def downgrade() -> None:
    """Revert storage changes."""
    op.drop_column('attachments', 'storage_bucket')
    op.alter_column(
        'attachments',
        'file_data',
        existing_type=sa.LargeBinary(),
        nullable=False
    )
