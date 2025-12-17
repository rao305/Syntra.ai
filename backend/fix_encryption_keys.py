"""Fix encryption key mismatch by re-encrypting provider keys with current encryption key."""
import asyncio
import sys
sys.path.insert(0, '/Users/rao305/Documents/Syntra/backend')

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.provider_key import ProviderKey, ProviderType
from app.security import encryption_service
from config import get_settings

settings = get_settings()

async def fix_provider_keys():
    """Delete old encrypted keys and re-insert with fresh encryption from .env."""
    async with AsyncSessionLocal() as db:
        try:
            print("🔍 Checking current provider keys...")

            # Get all provider keys for org_demo
            stmt = select(ProviderKey).where(ProviderKey.org_id == "org_demo")
            result = await db.execute(stmt)
            records = result.scalars().all()

            print(f"Found {len(records)} provider keys in database")
            for record in records:
                print(f"  - {record.provider.value}")

            # Delete all old keys that can't be decrypted
            print("\n🗑️  Deleting old encrypted keys...")
            delete_stmt = delete(ProviderKey).where(ProviderKey.org_id == "org_demo")
            await db.execute(delete_stmt)
            await db.commit()
            print("✅ Old keys deleted")

            # Re-insert keys from environment variables with fresh encryption
            print("\n🔐 Re-encrypting keys from .env...")

            keys_to_add = []

            if settings.openai_api_key:
                keys_to_add.append(("openai", settings.openai_api_key, ProviderType.OPENAI))
            if settings.google_api_key:
                keys_to_add.append(("gemini", settings.google_api_key, ProviderType.GEMINI))
            if settings.perplexity_api_key:
                keys_to_add.append(("perplexity", settings.perplexity_api_key, ProviderType.PERPLEXITY))
            if settings.kimi_api_key:
                keys_to_add.append(("kimi", settings.kimi_api_key, ProviderType.KIMI))
            if settings.openrouter_api_key:
                keys_to_add.append(("openrouter", settings.openrouter_api_key, ProviderType.OPENROUTER))

            if not keys_to_add:
                print("❌ No API keys found in .env file!")
                print("Please add at least one of: OPENAI_API_KEY, GOOGLE_API_KEY, PERPLEXITY_API_KEY, KIMI_API_KEY, OPENROUTER_API_KEY")
                return

            for name, api_key, provider_type in keys_to_add:
                print(f"  Encrypting {name} API key...")
                encrypted = encryption_service.encrypt(api_key)

                new_key = ProviderKey(
                    org_id="org_demo",
                    provider=provider_type,
                    encrypted_key=encrypted,
                    key_name=f"{name} (from .env)",
                    is_active="true"
                )
                db.add(new_key)
                print(f"  ✅ {name} added")

            await db.commit()
            print(f"\n✅ Successfully re-encrypted {len(keys_to_add)} API keys!")

            # Verify decryption works
            print("\n🧪 Testing decryption...")
            stmt = select(ProviderKey).where(ProviderKey.org_id == "org_demo").limit(1)
            result = await db.execute(stmt)
            test_record = result.scalar_one_or_none()

            if test_record:
                try:
                    decrypted = encryption_service.decrypt(test_record.encrypted_key)
                    print(f"✅ Decryption test passed! Key starts with: {decrypted[:20]}...")
                except Exception as e:
                    print(f"❌ Decryption test failed: {e}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(fix_provider_keys())
