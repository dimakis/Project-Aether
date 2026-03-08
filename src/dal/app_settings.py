"""App settings data access layer.

Provides read/write for the single-row app_settings table and
a resolution helper that merges DB overrides with env defaults.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.storage.entities.app_settings import AppSettings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ─── Defaults per section ─────────────────────────────────────────────────────
# These mirror the env-var defaults from Settings() but are the canonical
# source for the Settings UI.  When a key is missing from the DB row,
# the resolution helper falls back to these.

CHAT_DEFAULTS: dict[str, Any] = {
    "stream_timeout_seconds": 900,
    "tool_timeout_seconds": 30,
    "analysis_tool_timeout_seconds": 180,
    "max_tool_iterations": 10,
}

DASHBOARD_DEFAULTS: dict[str, Any] = {
    "default_refresh_interval_seconds": 60,
    "max_widgets": 20,
}

DATA_SCIENCE_DEFAULTS: dict[str, Any] = {
    "sandbox_enabled": True,
    "sandbox_timeout_quick": 30,
    "sandbox_timeout_standard": 60,
    "sandbox_timeout_deep": 180,
    "sandbox_memory_quick": 512,
    "sandbox_memory_standard": 1024,
    "sandbox_memory_deep": 2048,
    "sandbox_artifacts_enabled": False,
}

NOTIFICATIONS_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "min_impact": "high",
    "quiet_hours_start": None,
    "quiet_hours_end": None,
}

SECTION_DEFAULTS: dict[str, dict[str, Any]] = {
    "chat": CHAT_DEFAULTS,
    "dashboard": DASHBOARD_DEFAULTS,
    "data_science": DATA_SCIENCE_DEFAULTS,
    "notifications": NOTIFICATIONS_DEFAULTS,
}

# ─── Validation bounds ────────────────────────────────────────────────────────
# (min, max) for numeric fields.  Missing = no bound check.

FIELD_BOUNDS: dict[str, tuple[int | None, int | None]] = {
    "stream_timeout_seconds": (60, 3600),
    "tool_timeout_seconds": (5, 300),
    "analysis_tool_timeout_seconds": (30, 600),
    "max_tool_iterations": (1, 50),
    "default_refresh_interval_seconds": (10, 3600),
    "max_widgets": (1, 100),
    "sandbox_timeout_quick": (5, 120),
    "sandbox_timeout_standard": (10, 300),
    "sandbox_timeout_deep": (30, 600),
    "sandbox_memory_quick": (128, 2048),
    "sandbox_memory_standard": (256, 4096),
    "sandbox_memory_deep": (512, 8192),
}


_VALID_IMPACTS = {"low", "medium", "high", "critical"}

# HH:MM time format for quiet hours validation
_TIME_PATTERN = r"^\d{1,2}:\d{2}$"


def validate_section(section: str, data: dict[str, Any]) -> dict[str, Any]:
    """Validate and clamp setting values within allowed bounds.

    Unknown keys are silently dropped.

    Args:
        section: Section name (chat, dashboard, data_science, notifications)
        data: Incoming key-value pairs to validate

    Returns:
        Validated dict (only known keys, clamped to bounds)

    Raises:
        ValueError: If a value has the wrong type
    """
    import re

    defaults = SECTION_DEFAULTS.get(section, {})
    validated: dict[str, Any] = {}

    for key, value in data.items():
        if key not in defaults:
            continue  # drop unknown keys

        expected = defaults[key]
        if isinstance(expected, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be a boolean")
            validated[key] = value
        elif isinstance(expected, int):
            if not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be a number")
            iv = int(value)
            lo, hi = FIELD_BOUNDS.get(key, (None, None))
            if lo is not None:
                iv = max(iv, lo)
            if hi is not None:
                iv = min(iv, hi)
            validated[key] = iv
        elif key == "min_impact":
            if value not in _VALID_IMPACTS:
                raise ValueError(f"{key} must be one of {sorted(_VALID_IMPACTS)}")
            validated[key] = value
        elif key in ("quiet_hours_start", "quiet_hours_end"):
            if value is None:
                validated[key] = None
            elif isinstance(value, str) and re.match(_TIME_PATTERN, value):
                validated[key] = value
            else:
                raise ValueError(f"{key} must be a time string in HH:MM format or null")
        else:
            validated[key] = value

    return validated


# ─── In-memory cache ──────────────────────────────────────────────────────────

_settings_cache: dict[str, dict[str, Any]] | None = None
_cache_ts: float = 0
_CACHE_TTL = 30  # seconds


def invalidate_settings_cache() -> None:
    """Clear the in-memory settings cache."""
    global _settings_cache, _cache_ts
    _settings_cache = None
    _cache_ts = 0


# ─── Repository ───────────────────────────────────────────────────────────────


class AppSettingsRepository:
    """Repository for the single-row app_settings table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> AppSettings | None:
        """Get the settings row, if it exists."""
        result = await self.session.execute(select(AppSettings).limit(1))
        return result.scalar_one_or_none()

    async def get_merged(self) -> dict[str, dict[str, Any]]:
        """Get all settings merged with defaults.

        Returns a dict with keys 'chat', 'dashboard', 'data_science',
        each containing the full set of keys (DB values override defaults).
        """
        row = await self.get()
        result: dict[str, dict[str, Any]] = {}
        for section, defaults in SECTION_DEFAULTS.items():
            db_values = getattr(row, section, {}) if row else {}
            result[section] = {**defaults, **(db_values or {})}
        return result

    async def update_section(self, section: str, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Update a single section, merging with existing values.

        Creates the row if it doesn't exist (upsert pattern).

        Args:
            section: Section name (chat, dashboard, data_science)
            data: Validated key-value pairs to merge

        Returns:
            Full merged settings (all sections)
        """
        if section not in SECTION_DEFAULTS:
            raise ValueError(f"Unknown section: {section}")

        validated = validate_section(section, data)
        row = await self.get()

        if row is None:
            kwargs: dict[str, Any] = {s: {} for s in SECTION_DEFAULTS}
            kwargs[section] = validated
            row = AppSettings(id=str(uuid4()), **kwargs)
            self.session.add(row)
        else:
            current = getattr(row, section) or {}
            setattr(row, section, {**current, **validated})

        await self.session.flush()
        invalidate_settings_cache()
        return await self.get_merged()

    async def reset_section(self, section: str) -> dict[str, dict[str, Any]]:
        """Reset a section to defaults (clear DB overrides).

        Args:
            section: Section name to reset

        Returns:
            Full merged settings (all sections)
        """
        if section not in SECTION_DEFAULTS:
            raise ValueError(f"Unknown section: {section}")

        row = await self.get()
        if row is not None:
            setattr(row, section, {})
            await self.session.flush()
            invalidate_settings_cache()

        return await self.get_merged()


# ─── Resolution helper ────────────────────────────────────────────────────────


async def get_app_settings_merged() -> dict[str, dict[str, Any]]:
    """Get all settings merged with defaults, using an in-memory cache.

    Creates its own DB session.  Safe to call from anywhere.
    """
    global _settings_cache, _cache_ts

    now = time.monotonic()
    if _settings_cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return _settings_cache

    from src.storage import get_session_factory

    factory = get_session_factory()
    session = factory()
    try:
        repo = AppSettingsRepository(session)
        merged = await repo.get_merged()
        _settings_cache = merged
        _cache_ts = now
        return merged
    except (OSError, SQLAlchemyError):
        logger.debug("Failed to load app settings from DB, using defaults", exc_info=True)
        return {s: {**d} for s, d in SECTION_DEFAULTS.items()}
    finally:
        await session.close()


async def get_chat_setting(key: str) -> Any:
    """Get a single chat setting, resolved from DB or defaults."""
    merged = await get_app_settings_merged()
    return merged.get("chat", {}).get(key, CHAT_DEFAULTS.get(key))
