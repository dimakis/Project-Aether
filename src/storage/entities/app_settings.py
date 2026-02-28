"""App settings entity model.

Stores runtime-configurable application settings as JSONB columns
grouped by section (chat, dashboard, data_science). This enables
in-app configuration via the Settings UI without requiring env
variable changes or server restarts.

Single-row table — only one settings row exists at any time.
Missing keys fall back to environment defaults from Settings().
"""

from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class AppSettings(Base, UUIDMixin, TimestampMixin):
    """Runtime-configurable application settings.

    Each column is a JSONB dict holding settings for one section.
    Keys within each section mirror the field names in Settings()
    so the resolution logic can fall through to env defaults.
    """

    __tablename__ = "app_settings"

    chat: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Chat & streaming settings (stream_timeout_seconds, tool timeouts, etc.)",
    )
    dashboard: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Dashboard settings (refresh interval, max widgets, etc.)",
    )
    data_science: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Data Science settings (sandbox timeouts, memory limits, etc.)",
    )
    notifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc=(
            "Insight notification preferences (Feature 37). "
            "Keys: enabled (bool), min_impact (str: low|medium|high|critical), "
            "quiet_hours_start (str: HH:MM), quiet_hours_end (str: HH:MM)."
        ),
    )

    def __repr__(self) -> str:
        return f"<AppSettings(id={self.id})>"
