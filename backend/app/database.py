"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database connection."""
    # Import all models here to ensure they're registered
    from app.models import org, user, thread, message, memory, audit, provider_key, access_graph  # noqa

    # In production, use Alembic migrations instead
    if not settings.is_production:
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.create_all)
            pass  # Use Alembic even in dev


async def close_db():
    """Close database connection."""
    await engine.dispose()


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
