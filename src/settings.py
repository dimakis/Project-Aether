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
    environment: Literal["development", "staging", "production"] = "development"
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
    # Supports: openai, openrouter, google, or any OpenAI-compatible API
    llm_provider: Literal["openai", "openrouter", "google"] = Field(
        default="openrouter",
        description="LLM provider (openai, openrouter, google)",
    )
    llm_model: str = Field(
        default="anthropic/claude-sonnet-4",
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
        validation_alias=AliasChoices("llm_api_key", "openrouter_api_key", "openai_api_key"),
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

    # Google Gemini (separate SDK, not OpenAI-compatible)
    google_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google API key for Gemini (if using google provider)",
    )

    # MLflow (Constitution: Observability)
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI",
    )
    mlflow_experiment_name: str = Field(
        default="aether",
        description="MLflow experiment name",
    )

    # API
    api_host: str = Field(default="0.0.0.0")  # noqa: S104
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_workers: int = Field(default=1, ge=1, le=16)

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
