from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./dev.db"
    # Legacy HS256 shared-secret verification — used only when supabase_url is
    # unset (local dev/tests, no network). Real projects created since
    # Supabase's move to per-project asymmetric signing keys don't have this;
    # see supabase_url below.
    supabase_jwt_secret: str = "test-secret-do-not-use-in-production"
    # e.g. "https://<project-ref>.supabase.co". When set, JWTs are verified
    # against this project's JWKS (https://.../auth/v1/.well-known/jwks.json)
    # instead of the legacy shared secret — required for any project using
    # asymmetric (ES256/RS256) signing keys, which is the default today.
    supabase_url: str = ""
    cors_origins: str = "http://localhost:3000"

    # Platform-level Razorpay credentials (SeatServe is the merchant of record;
    # there is no per-business Razorpay Connect/Route account yet). Left blank
    # by default — the payments service checks for this and returns a clear
    # "provider not configured" error rather than faking success. Get these
    # from the Razorpay Dashboard -> Settings -> API Keys / Webhooks.
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # File upload settings
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 5
    allowed_image_types: str = "image/jpeg,image/png,image/webp,image/gif"

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
