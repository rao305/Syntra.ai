"""Add quality metrics to collaborate_runs table.

Revision ID: 013
Revises: 012
Create Date: 2025-12-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add quality metrics columns to collaborate_runs table
    op.add_column("collaborate_runs", sa.Column("query_complexity", sa.Integer(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("substance_score", sa.Float(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("completeness_score", sa.Float(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("depth_score", sa.Float(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("accuracy_score", sa.Float(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("overall_quality_score", sa.Float(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("quality_gate_passed", sa.Boolean(), nullable=True))
    op.add_column("collaborate_runs", sa.Column("quality_validation_timestamp", sa.DateTime(timezone=True), nullable=True))

    # Create indexes for quality metrics queries
    op.create_index("ix_collaborate_runs_quality_gate_passed", "collaborate_runs", ["quality_gate_passed"], unique=False)
    op.create_index("ix_collaborate_runs_overall_quality_score", "collaborate_runs", ["overall_quality_score"], unique=False)
    op.create_index("ix_collaborate_runs_query_complexity", "collaborate_runs", ["query_complexity"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_collaborate_runs_query_complexity", table_name="collaborate_runs")
    op.drop_index("ix_collaborate_runs_overall_quality_score", table_name="collaborate_runs")
    op.drop_index("ix_collaborate_runs_quality_gate_passed", table_name="collaborate_runs")

    # Remove quality metrics columns
    op.drop_column("collaborate_runs", "quality_validation_timestamp")
    op.drop_column("collaborate_runs", "quality_gate_passed")
    op.drop_column("collaborate_runs", "overall_quality_score")
    op.drop_column("collaborate_runs", "accuracy_score")
    op.drop_column("collaborate_runs", "depth_score")
    op.drop_column("collaborate_runs", "completeness_score")
    op.drop_column("collaborate_runs", "substance_score")
    op.drop_column("collaborate_runs", "query_complexity")
