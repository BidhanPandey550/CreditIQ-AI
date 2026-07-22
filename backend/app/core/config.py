"""Application configuration (12-factor, environment-driven)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Symmetric HS256 is used deliberately: a single backend both signs and verifies its own
# tokens, so a shared secret is sufficient and simplest. RS256 (asymmetric) is the documented
# production upgrade once other services must verify tokens without the signing key.
INSECURE_DEFAULT_SECRET = "dev-only-secret-change-me-in-production"
INSECURE_DEFAULT_MFA_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


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
    auth_mfa_rate_limit: int = 10
    ai_analysis_rate_limit: int = 20
    rate_limit_window_seconds: int = 60

    # Security — HS256 symmetric signing (see module note). Secret MUST be overridden in prod.
    jwt_secret_key: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "creditiq-backend"
    jwt_audience: str = "creditiq-platform"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "creditiq_refresh"
    expose_refresh_token_in_body: bool = True
    mfa_encryption_key: str = INSECURE_DEFAULT_MFA_KEY
    mfa_issuer: str = "CreditIQ AI"
    mfa_challenge_expire_minutes: int = 5

    # ML engine
    ml_engine_url: str = "http://localhost:8001"
    ml_engine_timeout_seconds: float = 5.0

    # Fraud decision policy. Only a dismissed alert clears approval blocking.
    fraud_approval_blocking_severities: str = "high,critical"

    # Loan servicing defaults. Product-level rates override the default rate.
    servicing_default_annual_interest_rate: float = 0.0
    servicing_first_due_days: int = 30
    servicing_grace_days: int = 0
    servicing_par_threshold_days: str = "1,30,60,90"

    # Private financial-document storage and malware scanning.
    document_storage_root: str = "./var/documents"
    document_max_bytes: int = 10_485_760
    document_allowed_content_types: str = "application/pdf,image/jpeg,image/png"
    document_scan_required: bool = False
    clamav_host: str | None = None
    clamav_port: int = 3310
    clamav_timeout_seconds: float = 10.0
    document_upload_rate_limit: int = 10

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

    @property
    def par_threshold_days(self) -> list[int]:
        return sorted(
            {int(value.strip()) for value in self.servicing_par_threshold_days.split(",")}
        )

    @property
    def allowed_document_content_types(self) -> set[str]:
        return {
            value.strip()
            for value in self.document_allowed_content_types.split(",")
            if value.strip()
        }

    @property
    def approval_blocking_fraud_severities(self) -> set[str]:
        return {
            value.strip().lower()
            for value in self.fraud_approval_blocking_severities.split(",")
            if value.strip()
        }

    @model_validator(mode="after")
    def _forbid_insecure_secret_in_production(self) -> "Settings":
        """Fail fast rather than boot production with the shipped development secret."""
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be an approved HMAC algorithm")
        if self.servicing_default_annual_interest_rate < 0:
            raise ValueError("SERVICING_DEFAULT_ANNUAL_INTEREST_RATE cannot be negative")
        if self.servicing_first_due_days <= 0 or self.servicing_grace_days < 0:
            raise ValueError("Servicing due-day settings are invalid")
        if not self.par_threshold_days or any(value <= 0 for value in self.par_threshold_days):
            raise ValueError("SERVICING_PAR_THRESHOLD_DAYS must contain positive integers")
        if self.document_max_bytes <= 0 or not self.allowed_document_content_types:
            raise ValueError("Document upload limits and content types must be configured")
        if not self.approval_blocking_fraud_severities.issubset(
            {"low", "medium", "high", "critical"}
        ):
            raise ValueError("FRAUD_APPROVAL_BLOCKING_SEVERITIES contains an invalid severity")
        if self.is_production:
            if self.jwt_secret_key == INSECURE_DEFAULT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
            if self.seed_on_startup:
                raise ValueError("SEED_ON_STARTUP must be false in production")
            if self.auto_migrate_on_startup:
                raise ValueError("AUTO_MIGRATE_ON_STARTUP must be false in production")
            if self.expose_refresh_token_in_body:
                raise ValueError("EXPOSE_REFRESH_TOKEN_IN_BODY must be false in production")
            if self.mfa_encryption_key == INSECURE_DEFAULT_MFA_KEY:
                raise ValueError("MFA_ENCRYPTION_KEY must be independently generated in production")
            if any(origin == "*" or "localhost" in origin for origin in self.cors_origins):
                raise ValueError("Production CORS origins must be explicit non-localhost origins")
            if not self.document_scan_required or not self.clamav_host:
                raise ValueError("Production document uploads require a configured malware scanner")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
