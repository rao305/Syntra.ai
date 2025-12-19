"""Add pgvector support to memory_fragments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20251219_add_pgvector'
down_revision = '20251218_add_attachments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add pgvector extension and embedding column."""
    # Enable vector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column (1536 dimensions for OpenAI embeddings)
    op.execute("""
        ALTER TABLE memory_fragments
        ADD COLUMN IF NOT EXISTS embedding vector(1536)
    """)

    # Create HNSW index for fast similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_fragments_embedding_hnsw
        ON memory_fragments
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Create index for filtered queries (org + tier)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_org_tier_embedding
        ON memory_fragments (org_id, tier)
        WHERE embedding IS NOT NULL
    """)


def downgrade() -> None:
    """Remove pgvector extension and embedding column."""
    op.execute("DROP INDEX IF EXISTS idx_memory_org_tier_embedding")
    op.execute("DROP INDEX IF EXISTS idx_memory_fragments_embedding_hnsw")
    op.execute("ALTER TABLE memory_fragments DROP COLUMN IF NOT EXISTS embedding")
    # Note: We don't drop the vector extension as other tables might use it
