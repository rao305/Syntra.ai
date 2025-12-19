"""Migrate existing BLOB attachments to Supabase Storage (run post-launch during low traffic)."""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.attachment import Attachment
from app.models.thread import Thread
from app.services.storage_service import storage_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_blobs():
    """
    Migrate existing BLOB attachments to Supabase Storage.

    This is a post-launch background migration that should run during low traffic.
    It safely migrates files while keeping the old BLOB data as fallback.

    Steps:
    1. Find all attachments with BLOB data but no storage_path
    2. Upload each to Supabase Storage
    3. Update record with storage_path
    4. Clear BLOB data (optional - keep for safety)
    """
    try:
        logger.info("🚀 Starting BLOB to Storage migration...")
        logger.info("=" * 60)

        async with AsyncSessionLocal() as db:
            # Find attachments with BLOBs but no storage_path
            stmt = select(Attachment).where(
                Attachment.file_data.isnot(None),
                Attachment.storage_path.is_(None)
            )
            result = await db.execute(stmt)
            attachments = result.scalars().all()

            total_attachments = len(attachments)
            logger.info(f"📊 Found {total_attachments} BLOB attachments to migrate")

            if total_attachments == 0:
                logger.info("✅ All attachments already migrated!")
                return True

            migrated = 0
            failed = 0
            batch_size = 10

            # Process in batches
            for i in range(0, total_attachments, batch_size):
                batch = attachments[i:i + batch_size]
                batch_migrated = 0

                for attachment in batch:
                    try:
                        # Get thread to find org_id
                        thread_stmt = select(Thread).where(Thread.id == attachment.thread_id)
                        thread_result = await db.execute(thread_stmt)
                        thread = thread_result.scalar_one()

                        logger.info(
                            f"Migrating attachment {attachment.id} "
                            f"({i + batch.index(attachment) + 1}/{total_attachments}) "
                            f"- {attachment.filename} ({attachment.file_size} bytes)"
                        )

                        # Upload to Supabase Storage
                        storage_path = await storage_service.upload_file(
                            org_id=thread.org_id,
                            thread_id=attachment.thread_id,
                            attachment_id=attachment.id,
                            filename=attachment.filename,
                            file_data=attachment.file_data,
                            mime_type=attachment.mime_type
                        )

                        # Update record with storage info
                        attachment.storage_path = storage_path
                        attachment.storage_bucket = "attachments"
                        # Keep BLOB data for safety (can delete after verification)
                        # attachment.file_data = None

                        db.add(attachment)
                        migrated += 1
                        batch_migrated += 1

                        logger.info(f"✅ Migrated: {attachment.filename}")

                    except Exception as e:
                        logger.error(f"❌ Failed to migrate attachment {attachment.id}: {e}")
                        failed += 1

                # Commit batch
                try:
                    await db.commit()
                    batch_num = (i // batch_size) + 1
                    logger.info(
                        f"✅ Batch {batch_num}: Migrated {batch_migrated} files "
                        f"({migrated}/{total_attachments} total)"
                    )
                except Exception as e:
                    await db.rollback()
                    logger.error(f"❌ Failed to commit batch: {e}")

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("Migration Complete!")
            logger.info(f"  ✅ Migrated:  {migrated}/{total_attachments}")
            logger.info(f"  ❌ Failed:    {failed}/{total_attachments}")
            if total_attachments > 0:
                logger.info(f"  📊 Success Rate: {(migrated / total_attachments * 100):.1f}%")
            logger.info("=" * 60)

            # Verify migration
            await verify_migration(db, total_attachments)

            return migrated == total_attachments

    except Exception as e:
        logger.error(f"Fatal error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_migration(db, expected_count: int):
    """Verify that all BLOBs were migrated correctly."""
    logger.info("\n🔍 Verifying migration...")

    # Count attachments with storage_path
    result = await db.execute(
        select(Attachment).where(Attachment.storage_path.isnot(None))
    )
    attachments_in_storage = len(result.scalars().all())

    # Count attachments still with BLOB but no storage_path
    result = await db.execute(
        select(Attachment).where(
            Attachment.file_data.isnot(None),
            Attachment.storage_path.is_(None)
        )
    )
    attachments_with_blob_only = len(result.scalars().all())

    logger.info(f"📊 Attachments in Supabase Storage: {attachments_in_storage}")
    logger.info(f"📊 Attachments still BLOB-only: {attachments_with_blob_only}")

    if attachments_with_blob_only == 0:
        logger.info("✅ Migration verified: All attachments successfully migrated!")
        return True
    else:
        logger.warning(f"⚠️  {attachments_with_blob_only} attachments still need migration")
        return False


async def cleanup_blobs(db):
    """
    Optional: Clean up BLOB data after successful migration (run separately).

    Only run this after confirming all files are in Storage and working correctly.
    """
    logger.info("\n🧹 Cleaning up BLOB data...")

    # Find attachments with both storage_path and file_data
    result = await db.execute(
        select(Attachment).where(
            Attachment.storage_path.isnot(None),
            Attachment.file_data.isnot(None)
        )
    )
    attachments = result.scalars().all()

    logger.info(f"Found {len(attachments)} attachments with both Storage path and BLOB data")

    for attachment in attachments:
        attachment.file_data = None
        db.add(attachment)

    await db.commit()

    logger.info(f"✅ Cleared BLOB data for {len(attachments)} attachments")


async def main():
    """Run the migration."""
    logger.info("BLOB to Storage Migration Tool")
    logger.info("=" * 60)
    logger.info("⚠️  WARNING: This script migrates production data")
    logger.info("           Run during low-traffic periods")
    logger.info("=" * 60)

    # Run migration
    success = await migrate_blobs()

    if success:
        logger.info("\n✅ All BLOBs migrated successfully!")
    else:
        logger.warning("\n⚠️  Some BLOBs failed to migrate - check logs above")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
