"""HA Registry models for User Story 1.

Revision ID: 002_ha_registry
Revises: 001_initial_agent
Create Date: 2026-02-03

Creates tables for:
- areas: Physical locations in the home
- devices: Hardware devices
- ha_entities: All HA entities (lights, sensors, etc.)
- discovery_sessions: Tracks discovery runs
- ha_automations: HA automation sync
- scripts: HA scripts
- scenes: HA scenes
- services: Available services
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_ha_registry"
down_revision: str | None = "001_initial_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Areas table
    op.create_table(
        "areas",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("ha_area_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("floor_id", sa.String(255), nullable=True),
        sa.Column("icon", sa.String(255), nullable=True),
        sa.Column("picture", sa.String(512), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_areas_name", "areas", ["name"])

    # Devices table
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("ha_device_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_by_user", sa.String(255), nullable=True),
        sa.Column("area_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("areas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("sw_version", sa.String(100), nullable=True),
        sa.Column("hw_version", sa.String(100), nullable=True),
        sa.Column("config_entry_id", sa.String(255), nullable=True),
        sa.Column("via_device_id", sa.String(255), nullable=True),
        sa.Column("identifiers", postgresql.JSONB, nullable=True),
        sa.Column("connections", postgresql.JSONB, nullable=True),
        sa.Column("disabled", sa.Boolean, default=False),
        sa.Column("disabled_by", sa.String(50), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_devices_name", "devices", ["name"])
    op.create_index("ix_devices_manufacturer", "devices", ["manufacturer"])

    # HA Entities table
    op.create_table(
        "ha_entities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("entity_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("domain", sa.String(50), nullable=False, index=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=True),
        sa.Column("state", sa.String(255), nullable=True),
        sa.Column("attributes", postgresql.JSONB, nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("area_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("areas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_class", sa.String(100), nullable=True),
        sa.Column("unit_of_measurement", sa.String(50), nullable=True),
        sa.Column("supported_features", sa.Integer, default=0),
        sa.Column("state_class", sa.String(50), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("entity_category", sa.String(50), nullable=True),
        sa.Column("disabled", sa.Boolean, default=False),
        sa.Column("disabled_by", sa.String(50), nullable=True),
        sa.Column("hidden", sa.Boolean, default=False),
        sa.Column("hidden_by", sa.String(50), nullable=True),
        sa.Column("labels", postgresql.JSONB, nullable=True),
        sa.Column("config_entry_id", sa.String(255), nullable=True),
        sa.Column("unique_id", sa.String(255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ha_entities_device_class", "ha_entities", ["device_class"])
    op.create_index("ix_ha_entities_state", "ha_entities", ["state"])
    op.create_index("ix_ha_entities_domain_state", "ha_entities", ["domain", "state"])

    # Discovery Sessions table
    op.create_table(
        "discovery_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), default="running", nullable=False),
        sa.Column("entities_found", sa.Integer, default=0),
        sa.Column("entities_added", sa.Integer, default=0),
        sa.Column("entities_removed", sa.Integer, default=0),
        sa.Column("entities_updated", sa.Integer, default=0),
        sa.Column("devices_found", sa.Integer, default=0),
        sa.Column("devices_added", sa.Integer, default=0),
        sa.Column("areas_found", sa.Integer, default=0),
        sa.Column("areas_added", sa.Integer, default=0),
        sa.Column("floors_found", sa.Integer, default=0),
        sa.Column("labels_found", sa.Integer, default=0),
        sa.Column("integrations_found", sa.Integer, default=0),
        sa.Column("services_found", sa.Integer, default=0),
        sa.Column("automations_found", sa.Integer, default=0),
        sa.Column("scripts_found", sa.Integer, default=0),
        sa.Column("scenes_found", sa.Integer, default=0),
        sa.Column("domain_counts", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("errors", postgresql.JSONB, nullable=True),
        sa.Column("mcp_gaps_encountered", postgresql.JSONB, nullable=True),
        sa.Column("mlflow_run_id", sa.String(255), nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # HA Automations table
    op.create_table(
        "ha_automations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("ha_automation_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("entity_id", sa.String(255), nullable=False, index=True),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("state", sa.String(50), default="on"),
        sa.Column("mode", sa.String(50), default="single"),
        sa.Column("trigger_types", postgresql.JSONB, nullable=True),
        sa.Column("trigger_count", sa.Integer, default=0),
        sa.Column("action_count", sa.Integer, default=0),
        sa.Column("condition_count", sa.Integer, default=0),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("last_triggered", sa.String(50), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ha_automations_alias", "ha_automations", ["alias"])
    op.create_index("ix_ha_automations_state", "ha_automations", ["state"])

    # Scripts table
    op.create_table(
        "scripts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("entity_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("state", sa.String(50), default="off"),
        sa.Column("mode", sa.String(50), default="single"),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("sequence", postgresql.JSONB, nullable=True),
        sa.Column("fields", postgresql.JSONB, nullable=True),
        sa.Column("last_triggered", sa.String(50), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scripts_alias", "scripts", ["alias"])

    # Scenes table
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("entity_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("entity_states", postgresql.JSONB, nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ha_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenes_name", "scenes", ["name"])

    # Services table
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("service", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("fields", postgresql.JSONB, nullable=True),
        sa.Column("target", postgresql.JSONB, nullable=True),
        sa.Column("response", postgresql.JSONB, nullable=True),
        sa.Column("is_seeded", sa.Boolean, default=False),
        sa.Column("discovered_at", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_services_domain_service", "services", ["domain", "service"], unique=True)


def downgrade() -> None:
    op.drop_table("services")
    op.drop_table("scenes")
    op.drop_table("scripts")
    op.drop_table("ha_automations")
    op.drop_table("discovery_sessions")
    op.drop_table("ha_entities")
    op.drop_table("devices")
    op.drop_table("areas")
