"""Application configuration."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str

    # Qdrant
    qdrant_url: str
    qdrant_api_key: Optional[str] = None

    # Upstash Redis
    upstash_redis_url: str
    upstash_redis_token: Optional[str] = None

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    encryption_key: str  # Fernet key for provider API keys

    # Email
    email_from: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    resend_api_key: Optional[str] = None

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id: Optional[str] = None

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Environment
    environment: str = "development"

    # Rate Limits (conservative limits to stay under $5 USD)
    # At ~$0.50 per 1M tokens average, 5M tokens ≈ $2.50
    # Adding buffer for output tokens and request overhead
    default_requests_per_day: int = 100
    default_tokens_per_day: int = 5_000_000  # 5M tokens ≈ $2-3 depending on provider

    # LLM Fallback Keys (optional - orgs bring their own)
    perplexity_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None

    # SuperMemory (long-term episodic memory)
    supermemory_api_key: Optional[str] = None
    supermemory_api_base_url: str = "https://api.supermemory.ai"

    # Feature Flags
    feature_corewrite: bool = False  # Query rewriter feature

    # Firebase Auth
    firebase_credentials_file: Optional[str] = None
    firebase_credentials_json: Optional[str] = None
    firebase_project_id: Optional[str] = None
    default_org_id: str = "org_demo"

    # Clerk Auth
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None

    # Supabase (NEW)
    supabase_db_url: Optional[str] = None  # Direct connection for migrations
    supabase_pooler_url: Optional[str] = None  # Transaction pooler for FastAPI
    supabase_url: Optional[str] = None  # API URL
    supabase_anon_key: Optional[str] = None  # Public key
    supabase_service_key: Optional[str] = None  # Admin key

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
