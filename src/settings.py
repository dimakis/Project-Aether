"""Application settings using pydantic-settings.

Loads configuration from environment variables with .env file support.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
        description="Home Assistant instance URL",
    )
    ha_token: SecretStr = Field(
        default=SecretStr(""),
        description="Home Assistant long-lived access token",
    )

    # OpenAI (Research Decision #6)
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="OpenAI API key for LLM operations",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for agents",
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
