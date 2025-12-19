"""Supabase Storage service for file uploads."""
import logging
from typing import Optional
from supabase import create_client, Client
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    """Manage file uploads/downloads to Supabase Storage with org-based isolation."""

    BUCKET_NAME = "attachments"

    def __init__(self):
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        """Get or create Supabase client."""
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_key  # Use service key for admin access
            )
        return self._client

    async def upload_file(
        self,
        org_id: str,
        thread_id: str,
        attachment_id: str,
        filename: str,
        file_data: bytes,
        mime_type: Optional[str] = None
    ) -> str:
        """
        Upload file to Supabase Storage.

        Args:
            org_id: Organization ID
            thread_id: Thread ID
            attachment_id: Unique attachment ID
            filename: Original filename
            file_data: File contents as bytes
            mime_type: MIME type of the file (optional)

        Returns:
            storage_path: Path to file in bucket (org_id/thread_id/attachment_id_filename)

        Raises:
            Exception: If upload fails
        """
        try:
            client = self._get_client()

            # Construct storage path using org-based isolation
            storage_path = f"{org_id}/{thread_id}/{attachment_id}_{filename}"

            logger.info(f"Uploading file to storage: {storage_path}")

            # Upload to bucket
            client.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=file_data,
                file_options={
                    "content-type": mime_type or "application/octet-stream",
                    "cache-control": "3600",  # Cache for 1 hour
                    "upsert": False  # Don't overwrite existing files
                }
            )

            logger.info(f"✅ File uploaded to storage: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"❌ Failed to upload file: {e}")
            raise

    async def download_file(
        self,
        storage_path: str,
        bucket: str = BUCKET_NAME
    ) -> bytes:
        """
        Download file from Supabase Storage.

        Args:
            storage_path: Path to file in bucket
            bucket: Bucket name (default: attachments)

        Returns:
            File contents as bytes

        Raises:
            Exception: If download fails
        """
        try:
            client = self._get_client()

            logger.info(f"Downloading file from storage: {storage_path}")

            result = client.storage.from_(bucket).download(storage_path)

            logger.info(f"✅ File downloaded: {storage_path}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to download file {storage_path}: {e}")
            raise

    async def delete_file(
        self,
        storage_path: str,
        bucket: str = BUCKET_NAME
    ) -> None:
        """
        Delete file from Supabase Storage.

        Args:
            storage_path: Path to file in bucket
            bucket: Bucket name (default: attachments)

        Raises:
            Exception: If deletion fails
        """
        try:
            client = self._get_client()

            logger.info(f"Deleting file from storage: {storage_path}")

            client.storage.from_(bucket).remove([storage_path])

            logger.info(f"✅ File deleted: {storage_path}")

        except Exception as e:
            logger.error(f"❌ Failed to delete file {storage_path}: {e}")
            raise

    def get_signed_url(
        self,
        storage_path: str,
        bucket: str = BUCKET_NAME,
        expires_in: int = 3600
    ) -> str:
        """
        Get signed URL for temporary access to private file.

        Useful for sharing files without making them public.

        Args:
            storage_path: Path to file in bucket
            bucket: Bucket name (default: attachments)
            expires_in: URL expiration time in seconds (default: 1 hour)

        Returns:
            Signed URL for temporary access

        Raises:
            Exception: If URL generation fails
        """
        try:
            client = self._get_client()

            logger.info(f"Generating signed URL for: {storage_path}")

            result = client.storage.from_(bucket).create_signed_url(
                storage_path,
                expires_in
            )

            return result.get("signedURL") or result

        except Exception as e:
            logger.error(f"❌ Failed to generate signed URL: {e}")
            raise

    async def get_file_url(
        self,
        storage_path: str,
        bucket: str = BUCKET_NAME
    ) -> str:
        """
        Get public URL for a file (if bucket is public).

        For private buckets, use get_signed_url instead.

        Args:
            storage_path: Path to file in bucket
            bucket: Bucket name (default: attachments)

        Returns:
            Public URL
        """
        try:
            client = self._get_client()

            # Get public URL (works for public buckets, returns URL even for private)
            result = client.storage.from_(bucket).get_public_url(storage_path)

            return result

        except Exception as e:
            logger.error(f"❌ Failed to get public URL: {e}")
            raise

    async def list_files(
        self,
        org_id: str,
        thread_id: Optional[str] = None,
        bucket: str = BUCKET_NAME
    ) -> list:
        """
        List files in storage for an organization (or specific thread).

        Args:
            org_id: Organization ID
            thread_id: Thread ID (optional - list specific thread)
            bucket: Bucket name (default: attachments)

        Returns:
            List of file metadata

        Raises:
            Exception: If listing fails
        """
        try:
            client = self._get_client()

            # Build path prefix
            if thread_id:
                path_prefix = f"{org_id}/{thread_id}"
            else:
                path_prefix = org_id

            logger.info(f"Listing files in: {path_prefix}")

            result = client.storage.from_(bucket).list(path_prefix)

            return result

        except Exception as e:
            logger.error(f"❌ Failed to list files: {e}")
            raise


# Singleton instance
storage_service = StorageService()
