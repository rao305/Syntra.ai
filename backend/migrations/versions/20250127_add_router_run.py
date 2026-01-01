"""Add router_run table for dynamic routing analytics.

Revision ID: 008
Revises: 007
Create Date: 2025-01-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "router_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("thread_id", sa.String(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("requires_web", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_tools", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column("chosen_model_id", sa.String(), nullable=False),
        sa.Column("chosen_provider", sa.String(), nullable=False),
        sa.Column("chosen_provider_model", sa.String(), nullable=False),
        sa.Column("scores_json", postgresql.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("user_rating", sa.Integer(), nullable=True),
        sa.Column("user_liked", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_router_runs_user_id"), "router_runs", ["user_id"], unique=False)
    op.create_index(op.f("ix_router_runs_session_id"), "router_runs", ["session_id"], unique=False)
    op.create_index(op.f("ix_router_runs_thread_id"), "router_runs", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_router_runs_thread_id"), table_name="router_runs")
    op.drop_index(op.f("ix_router_runs_session_id"), table_name="router_runs")
    op.drop_index(op.f("ix_router_runs_user_id"), table_name="router_runs")
    op.drop_table("router_runs")











