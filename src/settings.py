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
    database_url: PostgresDsn = Field(  # type: ignore[assignment]
        default="postgresql+asyncpg://aether:aether@localhost:5432/aether",
        description="PostgreSQL connection URL with asyncpg driver",
    )
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5)
    database_pool_recycle: int = Field(
        default=1800,
        ge=-1,
        description="Seconds before a connection is recycled (-1 to disable)",
    )

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
    llm_provider: Literal[
        "openai", "openrouter", "google", "ollama", "together", "groq", "custom"
    ] = Field(
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
        description="Override model for Data Science team (e.g., gpt-4o-mini for cheaper script gen)",
    )
    data_scientist_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Override temperature for Data Science team",
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
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    public_url: str | None = Field(
        default=None,
        description="Externally reachable base URL for this Aether instance "
        "(used to generate webhook URLs that HA can reach). "
        "Example: https://aether.example.com",
    )
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

    # Deployment mode (Feature 30: Domain-Agnostic Orchestration / A2A)
    deployment_mode: Literal["monolith", "distributed"] = Field(
        default="monolith",
        description="'monolith' (all agents in-process) or 'distributed' (agents as remote A2A services)",
    )
    architect_service_url: str = Field(
        default="http://architect:8000",
        description="URL of the Architect A2A service (distributed mode)",
    )
    ds_orchestrator_url: str = Field(
        default="http://ds-orchestrator:8000",
        description="URL of the DS Orchestrator A2A service (distributed mode)",
    )
    ds_analysts_url: str = Field(
        default="http://ds-analysts:8000",
        description="URL of the DS Analysts A2A service (distributed mode)",
    )
    developer_service_url: str = Field(
        default="http://developer:8000",
        description="URL of the Developer A2A service (distributed mode)",
    )
    librarian_service_url: str = Field(
        default="http://librarian:8000",
        description="URL of the Librarian A2A service (distributed mode)",
    )
    dashboard_designer_service_url: str = Field(
        default="http://dashboard-designer:8000",
        description="URL of the Dashboard Designer A2A service (distributed mode)",
    )
    orchestrator_service_url: str = Field(
        default="http://orchestrator-agent:8000",
        description="URL of the Orchestrator A2A service (distributed mode)",
    )
    ds_service_url: str = Field(
        default="http://ds-orchestrator:8000",
        description="Legacy alias for ds_orchestrator_url",
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

    # Trace evaluation (MLflow 3.x GenAI scorers)
    trace_eval_enabled: bool = Field(
        default=True,
        description="Enable nightly trace evaluation via MLflow 3.x scorers",
    )
    trace_eval_cron: str = Field(
        default="0 2 * * *",
        description="Cron expression for trace evaluation (default: 2am daily)",
    )
    trace_eval_max_traces: int = Field(
        default=200,
        ge=10,
        le=1000,
        description="Max traces to evaluate per run",
    )

    # Data retention (nightly cleanup of unbounded tables)
    data_retention_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Days to keep analysis reports, messages, and actioned insights",
    )
    llm_usage_retention_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="Days to keep LLM usage records (high-volume table)",
    )

    # Discovery sync (periodic + webhook-triggered)
    discovery_sync_enabled: bool = Field(
        default=True,
        description="Enable periodic delta sync of HA entities to the discovery DB",
    )
    discovery_sync_interval_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Interval in minutes between periodic delta syncs (5 min - 24 h)",
    )

    # Tool execution timeouts
    tool_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout for simple tool calls (HA queries, etc.)",
    )
    analysis_tool_timeout_seconds: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Timeout for long-running analysis tools (DS team, diagnostics)",
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
    sandbox_artifacts_enabled: bool = Field(
        default=False,
        description="Allow sandbox scripts to write artifacts (charts, CSVs) to /workspace/output/. "
        "When False, no writable mount is created regardless of per-request settings. "
        "Constitution: default-deny for artifact egress.",
    )

    # Per-depth analysis timeouts (Feature 33: DS Deep Analysis)
    sandbox_timeout_quick: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Sandbox timeout for quick analysis (seconds)",
    )
    sandbox_timeout_standard: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Sandbox timeout for standard analysis (seconds)",
    )
    sandbox_timeout_deep: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Sandbox timeout for deep analysis (seconds)",
    )

    # Per-depth analysis memory limits (Feature 33: DS Deep Analysis)
    sandbox_memory_quick: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Memory limit for quick analysis (MB)",
    )
    sandbox_memory_standard: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Memory limit for standard analysis (MB)",
    )
    sandbox_memory_deep: int = Field(
        default=2048,
        ge=512,
        le=4096,
        description="Memory limit for deep analysis (MB)",
    )


# Tools that get the longer analysis_tool_timeout_seconds timeout.
# All others use tool_timeout_seconds.
ANALYSIS_TOOLS: frozenset[str] = frozenset(
    {
        "consult_data_science_team",
        "consult_energy_analyst",
        "consult_behavioral_analyst",
        "consult_diagnostic_analyst",
        "request_synthesis_review",
        "analyze_energy",
        "diagnose_issue",
        "run_custom_analysis",
        "discover_entities",
    }
)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded once and reused.
    """
    return Settings()
