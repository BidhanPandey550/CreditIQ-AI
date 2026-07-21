"""Application configuration (12-factor, environment-driven)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Symmetric HS256 is used deliberately: a single backend both signs and verifies its own
# tokens, so a shared secret is sufficient and simplest. RS256 (asymmetric) is the documented
# production upgrade once other services must verify tokens without the signing key.
INSECURE_DEFAULT_SECRET = "dev-only-secret-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"

    # Database — the app connects as a non-superuser role so RLS is enforced.
    database_url: str = (
        "postgresql+psycopg://creditiq_app:creditiq_app_password@localhost:5432/creditiq"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    auth_login_rate_limit: int = 10
    auth_refresh_rate_limit: int = 30
    ai_analysis_rate_limit: int = 20
    rate_limit_window_seconds: int = 60

    # Security — HS256 symmetric signing (see module note). Secret MUST be overridden in prod.
    jwt_secret_key: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "creditiq-backend"
    jwt_audience: str = "creditiq-platform"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ML engine
    ml_engine_url: str = "http://localhost:8001"
    ml_engine_timeout_seconds: float = 5.0

    # App behaviour
    seed_on_startup: bool = True
    auto_migrate_on_startup: bool = True
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    api_v1_prefix: str = "/api/v1"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def _forbid_insecure_secret_in_production(self) -> "Settings":
        """Fail fast rather than boot production with the shipped development secret."""
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be an approved HMAC algorithm")
        if self.is_production:
            if self.jwt_secret_key == INSECURE_DEFAULT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
            if self.seed_on_startup:
                raise ValueError("SEED_ON_STARTUP must be false in production")
            if self.auto_migrate_on_startup:
                raise ValueError("AUTO_MIGRATE_ON_STARTUP must be false in production")
            if any(origin == "*" or "localhost" in origin for origin in self.cors_origins):
                raise ValueError("Production CORS origins must be explicit non-localhost origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
