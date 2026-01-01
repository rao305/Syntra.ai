"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import get_settings

settings = get_settings()

# Create async engine
# CRITICAL: Use Supabase transaction pooler (port 6543) for RLS context (SET LOCAL)
# Session pooler (port 5432) won't work - context gets lost between requests
db_url = settings.database_url  # Use local database for development

engine = create_async_engine(
    db_url,
    echo=False,  # Disabled for performance - use SQLAlchemy logging if needed
    pool_pre_ping=True,
    pool_size=50,  # Increased for Supabase pooler
    max_overflow=20,  # Added overflow for traffic spikes
    pool_recycle=1800,  # Recycle connections every 30 minutes
    connect_args={
        "server_settings": {"application_name": "syntra_backend"}
    }
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
    from app.models import org, user, thread, message, memory, audit, provider_key, access_graph, attachment, user_api_key  # noqa

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
