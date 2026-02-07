"""Application settings using pydantic-settings.

Loads configuration from environment variables with .env file support.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # Allow both field name and alias
    )

    # Environment
    environment: Literal["development", "staging", "production", "testing"] = "development"
    debug: bool = False

    # Database (Constitution: State - PostgreSQL for checkpointing)
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://aether:aether@localhost:5432/aether",
        description="PostgreSQL connection URL with asyncpg driver",
    )
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5)

    # Home Assistant MCP
    ha_url: str = Field(
        default="http://localhost:8123",
        description="Home Assistant instance URL (primary/local)",
        validation_alias=AliasChoices("ha_url", "hass_url"),
    )
    ha_url_remote: str | None = Field(
        default=None,
        description="Home Assistant remote URL (fallback if local fails)",
        validation_alias=AliasChoices("ha_url_remote", "hass_remote_url"),
    )
    ha_token: SecretStr = Field(
        default=SecretStr(""),
        description="Home Assistant long-lived access token",
        validation_alias=AliasChoices("ha_token", "hass_token"),
    )

    # LLM Configuration (Research Decision #6)
    # Supports: openai, openrouter, google, ollama, together, groq, or custom
    llm_provider: Literal["openai", "openrouter", "google", "ollama", "together", "groq", "custom"] = Field(
        default="openai",
        description="LLM provider (openai, openrouter, google, ollama, together, groq, custom)",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="Model name (provider-specific format)",
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for generation",
    )
    llm_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for the LLM provider",
        validation_alias=AliasChoices("llm_api_key", "openai_api_key", "openrouter_api_key"),
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Custom base URL for OpenAI-compatible APIs",
    )

    # Provider-specific defaults (used if llm_base_url not set)
    # OpenRouter: https://openrouter.ai/api/v1
    # OpenAI: https://api.openai.com/v1
    # Together: https://api.together.xyz/v1
    # Groq: https://api.groq.com/openai/v1
    # Ollama: http://localhost:11434/v1

    # Per-agent model overrides (optional)
    # When set, the agent uses this model instead of the global default.
    # Resolution: user UI selection > per-agent setting > global default.
    data_scientist_model: str | None = Field(
        default=None,
        description="Override model for Data Scientist agent (e.g., gpt-4o-mini for cheaper script gen)",
    )
    data_scientist_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Override temperature for Data Scientist agent",
    )

    # LLM Failover (optional)
    llm_fallback_provider: str | None = Field(
        default=None,
        description="Fallback LLM provider (e.g., 'ollama') when primary is unavailable",
    )
    llm_fallback_model: str | None = Field(
        default=None,
        description="Fallback model name (e.g., 'llama3') when primary is unavailable",
    )

    # Google Gemini (separate SDK, not OpenAI-compatible)
    google_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google API key for Gemini (if using google provider)",
    )

    # MLflow (Constitution: Observability)
    mlflow_tracking_uri: str = Field(
        default="sqlite:///mlflow.db",
        description="MLflow tracking server URI (use sqlite:///mlflow.db or http://localhost:5000)",
    )
    mlflow_experiment_name: str = Field(
        default="aether",
        description="MLflow experiment name",
    )

    # API
    api_host: str = Field(default="0.0.0.0")  # noqa: S104
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_workers: int = Field(default=1, ge=1, le=16)
    api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for authentication (empty = auth disabled)",
    )

    # Authentication (JWT + Passkey)
    auth_username: str = Field(
        default="admin",
        description="Login username for session authentication",
    )
    auth_password: SecretStr = Field(
        default=SecretStr(""),
        description="Login password (empty = session auth disabled, API key or passkey only)",
    )
    jwt_secret: SecretStr = Field(
        default=SecretStr(""),
        description="JWT signing secret (auto-generated on startup if empty)",
    )
    jwt_expiry_hours: int = Field(
        default=72,
        ge=1,
        le=720,
        description="JWT token lifetime in hours",
    )

    # Google OAuth 2.0
    google_client_id: str = Field(
        default="",
        description="Google OAuth 2.0 Client ID (empty = Google sign-in disabled)",
    )
    google_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Google OAuth 2.0 Client Secret",
    )

    # CORS
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins (empty = auto based on environment)",
    )

    # WebAuthn / Passkey
    webauthn_rp_id: str = Field(
        default="localhost",
        description="WebAuthn Relying Party ID (your domain, e.g. home.example.com)",
    )
    webauthn_rp_name: str = Field(
        default="Aether",
        description="WebAuthn Relying Party display name",
    )
    webauthn_origin: str = Field(
        default="http://localhost:3000",
        description="Expected WebAuthn origin (must match the URL users access)",
    )

    # Role-based process separation (K8s multi-replica deployment)
    # - "all": Run both API server and scheduler (default, for single-process dev)
    # - "api": API server only (no scheduler) — use for API Deployment replicas
    # - "scheduler": Scheduler only — use for a single-replica scheduler Deployment
    aether_role: Literal["all", "api", "scheduler"] = Field(
        default="all",
        description="Process role: 'all' (default), 'api' (no scheduler), or 'scheduler' (scheduler only)",
    )

    # Scheduler (Feature 10: Scheduled & Event-Driven Insights)
    scheduler_enabled: bool = Field(
        default=True,
        description="Enable the APScheduler for periodic insight jobs",
    )
    scheduler_timezone: str = Field(
        default="UTC",
        description="Timezone for cron schedule evaluation",
    )
    webhook_secret: str | None = Field(
        default=None,
        description="Optional shared secret for webhook authentication (in addition to HA token)",
    )

    # Sandbox (Constitution: Isolation)
    sandbox_enabled: bool = Field(
        default=True,
        description="Enable gVisor sandbox for script execution",
    )
    sandbox_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum script execution time",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded once and reused.
    """
    return Settings()
