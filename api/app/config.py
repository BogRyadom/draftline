"""Application configuration, loaded from environment variables.

Only the values needed for the current phase are required at runtime; keys for
later phases (LLM, Gmail OAuth, encryption) are declared here so the interface
is stable, but default to empty so the app boots without them during Phase 0.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Never hardcode secrets; read them here."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Auth / Supabase (Phase 0) ──────────────────────────────────────────
    supabase_url: str = ""
    # Full JWKS URL. If empty, it is derived from supabase_url in auth.py.
    supabase_jwks_url: str = ""
    # Supabase access tokens carry this audience claim.
    jwt_audience: str = "authenticated"

    # ── CORS ───────────────────────────────────────────────────────────────
    # Comma-separated list of allowed browser origins.
    frontend_origin: str = "http://localhost:3000"

    # ── Database (Phase 0 schema; used from Phase 1 onward) ─────────────────
    database_url: str = ""

    # ── LLM + embeddings (Phase 2+) ────────────────────────────────────────
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # ── Gmail OAuth + token encryption (Phase 1+) ──────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = ""
    fernet_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins as a clean list, split on commas."""
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def resolved_jwks_url(self) -> str:
        """JWKS URL, derived from supabase_url when not set explicitly."""
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
