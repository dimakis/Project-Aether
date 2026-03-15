"""Normalize insight enum values to match ORM entity definitions.

The insightstatus PG enum contains UPPERCASE labels (PENDING, REVIEWED,
ACTIONED, DISMISSED) and some lowercase duplicates (pending, actioned),
but the ORM expects the .value side of the Python enum: generated,
reviewed, acted_upon, dismissed.

Similarly, insighttype has UPPERCASE labels (ENERGY_OPTIMIZATION, etc.)
but the ORM expects lowercase .value strings (energy_optimization, etc.).

This migration:
  1. Adds missing canonical enum labels
  2. Converts all existing row data to canonical lowercase values
  3. Leaves orphan enum labels in place (PG can't drop enum values)

Revision ID: 040_normalize_insightstatus_data
Revises: 039_app_settings_id_to_uuid
Create Date: 2026-03-15
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "040_normalize_insightstatus_data"
down_revision: str | None = "039_app_settings_id_to_uuid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── insightstatus ──────────────────────────────────────────────────────
# ORM values: generated, reviewed, acted_upon, dismissed
_STATUS_LABELS_TO_ADD = ["generated", "reviewed", "acted_upon", "dismissed"]
_STATUS_DATA_MAP = {
    "PENDING": "generated",
    "pending": "generated",
    "REVIEWED": "reviewed",
    "ACTIONED": "acted_upon",
    "actioned": "acted_upon",
    "DISMISSED": "dismissed",
}

# ── insighttype ────────────────────────────────────────────────────────
# ORM values (from InsightType.value): energy_optimization, anomaly,
# pattern, recommendation, maintenance_prediction, automation_gap, etc.
_TYPE_LABELS_TO_ADD = [
    "energy_optimization",
    "anomaly",
    "pattern",
    "recommendation",
    "maintenance_prediction",
]
_TYPE_DATA_MAP = {
    "ENERGY_OPTIMIZATION": "energy_optimization",
    "ANOMALY_DETECTION": "anomaly",
    "USAGE_PATTERN": "pattern",
    "COST_SAVING": "recommendation",
    "MAINTENANCE_PREDICTION": "maintenance_prediction",
}


def upgrade() -> None:
    # 1. Add missing canonical labels to the PG enums
    for label in _STATUS_LABELS_TO_ADD:
        op.execute(f"ALTER TYPE insightstatus ADD VALUE IF NOT EXISTS '{label}'")

    for label in _TYPE_LABELS_TO_ADD:
        op.execute(f"ALTER TYPE insighttype ADD VALUE IF NOT EXISTS '{label}'")

    # ADD VALUE must commit before the values can be used in DML,
    # so we need a separate transaction for the UPDATEs.
    # Alembic runs each migration in its own transaction by default.
    # We force a commit here, then run the UPDATEs.
    op.execute("COMMIT")

    # 2. Convert stale data rows to canonical values
    for old, new in _STATUS_DATA_MAP.items():
        op.execute(f"UPDATE insights SET status = '{new}' WHERE status = '{old}'")

    for old, new in _TYPE_DATA_MAP.items():
        op.execute(f"UPDATE insights SET type = '{new}' WHERE type = '{old}'")

    # Re-open a transaction for Alembic's version-table update
    op.execute("BEGIN")


def downgrade() -> None:
    # Best-effort reverse: map canonical values back to UPPERCASE
    _STATUS_REVERSE = {
        "generated": "PENDING",
        "reviewed": "REVIEWED",
        "acted_upon": "ACTIONED",
        "dismissed": "DISMISSED",
    }
    _TYPE_REVERSE = {
        "energy_optimization": "ENERGY_OPTIMIZATION",
        "anomaly": "ANOMALY_DETECTION",
        "pattern": "USAGE_PATTERN",
        "recommendation": "COST_SAVING",
        "maintenance_prediction": "MAINTENANCE_PREDICTION",
    }
    for old, new in _STATUS_REVERSE.items():
        op.execute(f"UPDATE insights SET status = '{new}' WHERE status = '{old}'")
    for old, new in _TYPE_REVERSE.items():
        op.execute(f"UPDATE insights SET type = '{new}' WHERE type = '{old}'")
