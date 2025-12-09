"""Initialize database by creating all tables and adding encryption columns."""
import asyncio
from sqlalchemy import text
from app.database import get_db, Base, engine
from app.models import message, thread, org  # Import models to register them

async def init_database():
    async for db in get_db():
        try:
            # Create all tables
            print("Creating tables...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables created")
            
            # Add encryption columns to messages if table exists
            result = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'messages'
                )
            """))
            
            if result.scalar():
                # Check if columns exist
                result = await db.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'messages' 
                    AND column_name IN ('encrypted_content', 'encryption_key_id')
                """))
                existing = [r[0] for r in result]
                
                if 'encrypted_content' not in existing:
                    await db.execute(text("ALTER TABLE messages ADD COLUMN encrypted_content BYTEA"))
                    print("✅ Added encrypted_content")
                
                if 'encryption_key_id' not in existing:
                    await db.execute(text("ALTER TABLE messages ADD COLUMN encryption_key_id VARCHAR"))
                    print("✅ Added encryption_key_id")
                
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_messages_encryption_key_id 
                    ON messages(encryption_key_id)
                """))
                await db.commit()
                print("✅ Encryption columns added")
            
            print("✅ Database initialization complete!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            break

if __name__ == "__main__":
    asyncio.run(init_database())

