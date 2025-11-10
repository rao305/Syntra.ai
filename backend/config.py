"""Application configuration."""
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
    qdrant_api_key: str

    # Upstash Redis
    upstash_redis_url: str
    upstash_redis_token: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    encryption_key: str  # Fernet key for provider API keys

    # Email
    email_from: str
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    resend_api_key: str | None = None

    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str
    stripe_price_id: str

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Environment
    environment: str = "development"

    # Rate Limits
    default_requests_per_day: int = 1000
    default_tokens_per_day: int = 100000

    # LLM Fallback Keys (optional - orgs bring their own)
    perplexity_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    openrouter_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
