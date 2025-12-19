"""Migrate vectors from Qdrant to pgvector in Supabase."""
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.memory import MemoryFragment
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def migrate_vectors():
    """
    Migrate vectors from Qdrant to pgvector.

    Steps:
    1. Find all fragments with vector_id (from Qdrant) but no embedding (pgvector)
    2. For each fragment, fetch the vector from Qdrant
    3. Store the vector in the embedding column in PostgreSQL
    4. Batch commits every 100 fragments for efficiency
    """
    try:
        from qdrant_client import AsyncQdrantClient

        # Initialize Qdrant client
        qdrant = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=10.0
        )

        logger.info("🔄 Starting vector migration from Qdrant to pgvector...")

        # Connect to database
        async with AsyncSessionLocal() as db:
            # Find fragments with Qdrant IDs but no pgvector embeddings
            stmt = select(MemoryFragment).where(
                MemoryFragment.vector_id.isnot(None),
                MemoryFragment.embedding.is_(None)
            )
            result = await db.execute(stmt)
            fragments = result.scalars().all()

            total_fragments = len(fragments)
            logger.info(f"📊 Found {total_fragments} fragments to migrate")

            if total_fragments == 0:
                logger.info("✅ All fragments already migrated!")
                return True

            migrated = 0
            failed = 0

            # Process in batches
            batch_size = 100
            for i in range(0, total_fragments, batch_size):
                batch = fragments[i:i + batch_size]
                batch_migrated = 0

                for fragment in batch:
                    try:
                        # Retrieve vector from Qdrant
                        # vector_id format: "mem_{content_hash}"
                        vector_id = int(fragment.vector_id.split('_')[0]) if fragment.vector_id.isdigit() else fragment.vector_id

                        logger.debug(f"Fetching vector for fragment {fragment.id} (Qdrant ID: {vector_id})")

                        try:
                            # Get point from Qdrant
                            points = await qdrant.retrieve(
                                collection_name="dac_memory",
                                ids=[vector_id],
                                with_vectors=True,
                                with_payload=False
                            )

                            if points and len(points) > 0:
                                # Extract vector from point
                                vector = points[0].vector

                                # Update fragment with embedding
                                fragment.embedding = vector
                                db.add(fragment)
                                migrated += 1
                                batch_migrated += 1

                                logger.debug(f"✅ Migrated {fragment.id}")
                            else:
                                # Vector not found in Qdrant - this is OK, we'll skip
                                logger.warning(f"⚠️  Vector not found in Qdrant for fragment {fragment.id}")
                                failed += 1

                        except ValueError:
                            # vector_id might not be numeric, try using it directly
                            try:
                                points = await qdrant.retrieve(
                                    collection_name="dac_memory",
                                    ids=[fragment.vector_id],
                                    with_vectors=True,
                                    with_payload=False
                                )

                                if points and len(points) > 0:
                                    vector = points[0].vector
                                    fragment.embedding = vector
                                    db.add(fragment)
                                    migrated += 1
                                    batch_migrated += 1
                                    logger.debug(f"✅ Migrated {fragment.id}")
                                else:
                                    logger.warning(f"⚠️  Vector not found in Qdrant for fragment {fragment.id}")
                                    failed += 1
                            except Exception as e:
                                logger.error(f"❌ Failed to retrieve vector for {fragment.id}: {e}")
                                failed += 1

                    except Exception as e:
                        logger.error(f"❌ Failed to migrate fragment {fragment.id}: {e}")
                        failed += 1

                # Commit batch
                try:
                    await db.commit()
                    logger.info(f"✅ Batch {i // batch_size + 1}: Migrated {batch_migrated} fragments ({migrated}/{total_fragments} total)")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"❌ Failed to commit batch: {e}")

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info(f"Migration Complete!")
            logger.info(f"  ✅ Migrated:  {migrated}/{total_fragments}")
            logger.info(f"  ❌ Failed:    {failed}/{total_fragments}")
            logger.info(f"  📊 Success Rate: {(migrated / total_fragments * 100):.1f}%")
            logger.info("=" * 60)

            # Verify migration
            await verify_migration(db, total_fragments)

            return migrated == total_fragments

    except Exception as e:
        logger.error(f"Fatal error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_migration(db, expected_count: int):
    """Verify that all vectors were migrated correctly."""
    logger.info("\n🔍 Verifying migration...")

    # Count fragments with embeddings
    result = await db.execute(
        select(MemoryFragment).where(MemoryFragment.embedding.isnot(None))
    )
    fragments_with_embedding = len(result.scalars().all())

    # Count fragments without embeddings (and have vector_id from Qdrant)
    result = await db.execute(
        select(MemoryFragment).where(
            MemoryFragment.vector_id.isnot(None),
            MemoryFragment.embedding.is_(None)
        )
    )
    fragments_without_embedding = len(result.scalars().all())

    logger.info(f"📊 Fragments with pgvector embeddings: {fragments_with_embedding}")
    logger.info(f"📊 Fragments still missing embeddings: {fragments_without_embedding}")

    if fragments_without_embedding == 0:
        logger.info("✅ Migration verified: All vectors successfully migrated!")
        return True
    else:
        logger.warning(f"⚠️  {fragments_without_embedding} fragments still need vectors")
        return False


async def main():
    """Run the migration."""
    logger.info("Vector Migration Tool")
    logger.info("=" * 60)
    logger.info(f"Source: Qdrant ({settings.qdrant_url})")
    logger.info(f"Destination: Supabase pgvector (via asyncpg)")
    logger.info("=" * 60)

    # Run migration
    success = await migrate_vectors()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
