"""Debug script to test API key decryption."""
import asyncio
import sys
sys.path.insert(0, '/Users/rao305/Documents/Syntra/backend')

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.provider_key import ProviderKey, ProviderType
from app.security import encryption_service
from config import get_settings

settings = get_settings()

async def test_decrypt():
    """Test decryption of stored API keys."""
    async with AsyncSessionLocal() as db:
        try:
            # Get a provider key from database
            stmt = select(ProviderKey).where(
                ProviderKey.org_id == "org_demo",
                ProviderKey.provider == ProviderType.OPENAI
            ).limit(1)
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                print("No provider key found for org_demo / openai")
                return

            print(f"Found record: {record}")
            print(f"Encrypted key type: {type(record.encrypted_key)}")
            print(f"Encrypted key length: {len(record.encrypted_key)}")
            print(f"Encrypted key (first 50 bytes): {record.encrypted_key[:50]}")
            print(f"\nEncryption key from settings: {settings.encryption_key[:20]}...")

            # Try to decrypt
            try:
                decrypted = encryption_service.decrypt(record.encrypted_key)
                print(f"\n✅ Decryption successful!")
                print(f"Decrypted key starts with: {decrypted[:20]}...")
            except Exception as e:
                print(f"\n❌ Decryption failed!")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print(f"Error repr: {repr(e)}")

                # Try to get more details
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_decrypt())
