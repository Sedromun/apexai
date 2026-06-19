from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env.

    No secret has a production-safe default: dev defaults are intentionally marked
    insecure so a misconfigured production deploy is obvious.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # App
    app_name: str = "ApexAI"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://apexai:apexai@localhost:5432/apexai"

    # JWT
    jwt_secret: str = Field(
        default="dev-insecure-secret-change-me-please-0123456789", min_length=16
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # Object storage (S3-compatible)
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "apexai"
    s3_secret_key: str = "apexai-secret"
    s3_bucket: str = "apexai-traces"
    s3_use_path_style: bool = True

    # CORS — comma-separated string in env, exposed as a parsed list.
    cors_origins: str = "http://localhost:3000"

    # Limits
    max_trace_upload_bytes: int = 5 * 1024 * 1024
    free_monthly_lap_limit: int = 30
    free_ai_trial: int = 1

    # AI coach (layer 2). Provider-agnostic; "stub" works fully offline (default).
    coach_provider: str = "stub"  # "stub" | "openai" | "anthropic"
    coach_timeout_s: int = 30
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    # Billing (stub provider by default; ЮKassa/CloudPayments adapter chosen later).
    public_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    billing_provider: str = "stub"
    billing_webhook_secret: str = "dev-billing-secret-change-me"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
