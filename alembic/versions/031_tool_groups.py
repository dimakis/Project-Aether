"""Create tool_group table for dynamic tool registry.

Feature 34: Dynamic Tool Registry.
Stores named groups of tools for dynamic agent tool assignment,
with seed data for the 12 default groups.

Revision ID: 031_tool_groups
Revises: 030_workflow_definitions
Create Date: 2026-02-28
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "031_tool_groups"
down_revision: str | None = "030_workflow_definitions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_GROUPS = [
    {
        "name": "ha_entity_query",
        "display_name": "HA Entity Queries",
        "tool_names": '["get_entity_state", "list_entities_by_domain", "search_entities", "get_domain_summary"]',
        "is_read_only": True,
    },
    {
        "name": "ha_automation_query",
        "display_name": "HA Automation Queries",
        "tool_names": '["list_automations", "get_automation_config", "get_script_config"]',
        "is_read_only": True,
    },
    {
        "name": "ha_live_query",
        "display_name": "HA Live Queries",
        "tool_names": '["render_template", "get_ha_logs", "check_ha_config"]',
        "is_read_only": True,
    },
    {
        "name": "ha_mutation",
        "display_name": "HA Mutations",
        "tool_names": '["control_entity", "deploy_automation", "delete_automation", "create_script", "create_scene", "fire_event", "send_ha_notification", "create_input_boolean", "create_input_number", "create_input_text", "create_input_select", "create_input_datetime", "create_input_button", "create_counter", "create_timer"]',
        "is_read_only": False,
    },
    {
        "name": "diagnostics",
        "display_name": "Diagnostic Tools",
        "tool_names": '["analyze_error_log", "find_unavailable_entities", "diagnose_entity", "check_integration_health", "validate_config"]',
        "is_read_only": True,
    },
    {
        "name": "specialists",
        "display_name": "Specialist Delegation",
        "tool_names": '["consult_energy_analyst", "consult_behavioral_analyst", "consult_diagnostic_analyst", "consult_dashboard_designer", "consult_data_science_team", "request_synthesis_review"]',
        "is_read_only": True,
    },
    {
        "name": "approval",
        "display_name": "HITL Approval",
        "tool_names": '["seek_approval"]',
        "is_read_only": True,
    },
    {
        "name": "discovery",
        "display_name": "Entity Discovery",
        "tool_names": '["discover_entities"]',
        "is_read_only": True,
    },
    {
        "name": "analysis",
        "display_name": "Custom Analysis",
        "tool_names": '["run_custom_analysis"]',
        "is_read_only": False,
    },
    {
        "name": "scheduling",
        "display_name": "Insight Scheduling",
        "tool_names": '["create_insight_schedule"]',
        "is_read_only": True,
    },
    {
        "name": "web",
        "display_name": "Web Search",
        "tool_names": '["web_search"]',
        "is_read_only": True,
    },
    {
        "name": "review",
        "display_name": "Config Review",
        "tool_names": '["review_config"]',
        "is_read_only": True,
    },
]


def upgrade() -> None:
    op.create_table(
        "tool_group",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tool_names", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_read_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    for group in SEED_GROUPS:
        op.execute(
            sa.text(
                "INSERT INTO tool_group "
                "(id, name, display_name, tool_names, is_read_only, created_at, updated_at) "
                "VALUES (:id, :name, :display_name, :tool_names, :is_read_only, now(), now())"
            ).bindparams(
                id=str(uuid4()),
                name=group["name"],
                display_name=group["display_name"],
                tool_names=group["tool_names"],
                is_read_only=group["is_read_only"],
            )
        )


def downgrade() -> None:
    op.drop_table("tool_group")
