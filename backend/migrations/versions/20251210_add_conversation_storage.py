"""Add conversation storage tables for collaboration persistence.

Revision ID: 012
Revises: 011
Create Date: 2025-12-10
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversation_turns table
    op.create_table(
        "conversation_turns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("turn_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=True),
        sa.Column("collaboration_mode", sa.String(50), nullable=True),
        sa.Column("final_report", sa.Text(), nullable=True),
        sa.Column("total_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for conversation_turns
    op.create_index(op.f("ix_conversation_turns_turn_id"), "conversation_turns", ["turn_id"], unique=True)
    op.create_index(op.f("ix_conversation_turns_thread_id"), "conversation_turns", ["thread_id"], unique=False)

    # Create agent_outputs table
    op.create_table(
        "agent_outputs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("turn_id", sa.String(255), nullable=True),
        sa.Column("agent_role", sa.String(50), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("execution_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["turn_id"], ["conversation_turns.turn_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for agent_outputs
    op.create_index(op.f("ix_agent_outputs_turn_id"), "agent_outputs", ["turn_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_agent_outputs_turn_id"), table_name="agent_outputs")
    op.drop_index(op.f("ix_conversation_turns_thread_id"), table_name="conversation_turns")
    op.drop_index(op.f("ix_conversation_turns_turn_id"), table_name="conversation_turns")

    # Drop tables
    op.drop_table("agent_outputs")
    op.drop_table("conversation_turns")
