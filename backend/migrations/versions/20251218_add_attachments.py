"""Add attachments table for file uploads.

Revision ID: add_attachments_001
Revises: 20251217_add_thread_persistence
Create Date: 2025-12-18 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_attachments_001'
down_revision = '20251217_add_thread_persistence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.Column('attachment_type', sa.String(), nullable=False, server_default='file'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attachments_thread_id'), 'attachments', ['thread_id'], unique=False)
    op.create_index(op.f('ix_attachments_message_id'), 'attachments', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_attachments_message_id'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_thread_id'), table_name='attachments')
    op.drop_table('attachments')
