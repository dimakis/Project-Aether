"""AutomationProposal entity model.

Proposed automation rules requiring HITL approval - User Story 2.
"""

import enum
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.conversation import Conversation


class ProposalType(enum.Enum):
    """Type of proposal action.

    Determines how the proposal is deployed:
    - automation: HA automation YAML (existing behavior)
    - entity_command: Single service call (turn on/off/toggle entity)
    - script: HA script creation
    - scene: HA scene creation
    """

    AUTOMATION = "automation"
    ENTITY_COMMAND = "entity_command"
    SCRIPT = "script"
    SCENE = "scene"


class ProposalStatus(enum.Enum):
    """Status of an automation proposal.

    State machine:
        draft -> proposed -> approved -> deployed -> rolled_back
                    |                        |
                    v                        v
                rejected                  archived

    HITL: Cannot transition from proposed -> deployed without going through approved.
    """

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


# Valid state transitions
VALID_TRANSITIONS: dict[ProposalStatus, set[ProposalStatus]] = {
    ProposalStatus.DRAFT: {ProposalStatus.PROPOSED},
    ProposalStatus.PROPOSED: {ProposalStatus.APPROVED, ProposalStatus.REJECTED},
    ProposalStatus.APPROVED: {ProposalStatus.DEPLOYED, ProposalStatus.REJECTED},
    ProposalStatus.REJECTED: {ProposalStatus.PROPOSED, ProposalStatus.ARCHIVED},
    ProposalStatus.DEPLOYED: {ProposalStatus.ROLLED_BACK},
    ProposalStatus.ROLLED_BACK: {ProposalStatus.PROPOSED, ProposalStatus.ARCHIVED},
    ProposalStatus.ARCHIVED: set(),  # Terminal state
}


class AutomationProposal(Base, UUIDMixin, TimestampMixin):
    """A proposed automation rule from agents, requiring HITL approval.

    Represents an automation designed through conversation with the Architect
    agent. Must go through the approval workflow before deployment to HA.

    Constitution: Safety First - HITL approval required before any deployment.
    """

    __tablename__ = "automation_proposal"
    __table_args__ = (
        Index("ix_proposals_status_created", "status", "created_at"),
    )

    proposal_type: Mapped[str] = mapped_column(
        String(20),
        insert_default=ProposalType.AUTOMATION.value,
        default=ProposalType.AUTOMATION.value,
        nullable=False,
        server_default="automation",
        doc="Type of proposal: automation, entity_command, script, scene",
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversation.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="FK to source conversation",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Automation name (human-readable)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="What the automation does (user-facing)",
    )
    trigger: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="HA trigger configuration (time, state, event, etc.)",
    )
    conditions: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="HA conditions (optional)",
    )
    actions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="HA actions (required)",
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="single",
        doc="Execution mode: single, restart, queued, parallel",
    )
    service_call: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Service call details for entity_command type (domain, service, data)",
    )
    status: Mapped[ProposalStatus] = mapped_column(
        default=ProposalStatus.DRAFT,
        nullable=False,
        index=True,
        doc="Proposal state (see state machine)",
    )

    # Deployment tracking
    ha_automation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        doc="HA automation ID (set after deployment)",
    )

    # Timestamps for workflow tracking
    proposed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When proposal was submitted for approval",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When proposal was approved",
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Who approved the proposal",
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When deployed to HA",
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When rolled back from HA",
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Why the proposal was rejected",
    )

    # Observability
    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MLflow run ID for tracking",
    )

    # Relationships
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        back_populates="proposals",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AutomationProposal(id={self.id!r}, name={self.name!r}, status={self.status.value!r})>"

    def can_transition_to(self, new_status: ProposalStatus) -> bool:
        """Check if transition to new status is valid.

        Args:
            new_status: Target status

        Returns:
            True if transition is allowed
        """
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def propose(self) -> None:
        """Submit proposal for approval."""
        if not self.can_transition_to(ProposalStatus.PROPOSED):
            raise ValueError(f"Cannot propose from status {self.status.value}")
        self.status = ProposalStatus.PROPOSED
        self.proposed_at = datetime.now(timezone.utc)

    def approve(self, approved_by: str) -> None:
        """Approve the proposal.

        Args:
            approved_by: Who is approving
        """
        if not self.can_transition_to(ProposalStatus.APPROVED):
            raise ValueError(f"Cannot approve from status {self.status.value}")
        self.status = ProposalStatus.APPROVED
        self.approved_at = datetime.now(timezone.utc)
        self.approved_by = approved_by

    def reject(self, reason: str) -> None:
        """Reject the proposal.

        Args:
            reason: Why it was rejected
        """
        if not self.can_transition_to(ProposalStatus.REJECTED):
            raise ValueError(f"Cannot reject from status {self.status.value}")
        self.status = ProposalStatus.REJECTED
        self.rejection_reason = reason

    def deploy(self, ha_automation_id: str) -> None:
        """Mark as deployed to HA.

        Args:
            ha_automation_id: The HA automation ID assigned
        """
        if not self.can_transition_to(ProposalStatus.DEPLOYED):
            raise ValueError(f"Cannot deploy from status {self.status.value}")
        self.status = ProposalStatus.DEPLOYED
        self.deployed_at = datetime.now(timezone.utc)
        self.ha_automation_id = ha_automation_id

    def rollback(self) -> None:
        """Mark as rolled back from HA."""
        if not self.can_transition_to(ProposalStatus.ROLLED_BACK):
            raise ValueError(f"Cannot rollback from status {self.status.value}")
        self.status = ProposalStatus.ROLLED_BACK
        self.rolled_back_at = datetime.now(timezone.utc)

    def archive(self) -> None:
        """Archive the proposal (terminal state)."""
        if not self.can_transition_to(ProposalStatus.ARCHIVED):
            raise ValueError(f"Cannot archive from status {self.status.value}")
        self.status = ProposalStatus.ARCHIVED

    @property
    def proposal_type_enum(self) -> ProposalType:
        """Get proposal_type as a ProposalType enum."""
        try:
            if isinstance(self.proposal_type, ProposalType):
                return self.proposal_type
            return ProposalType(self.proposal_type)
        except (ValueError, TypeError):
            return ProposalType.AUTOMATION

    def to_ha_yaml_dict(self) -> dict:
        """Convert to Home Assistant YAML format appropriate for the proposal type.

        Returns:
            Dictionary suitable for YAML serialization to HA config.
        """
        ptype = self.proposal_type_enum
        if ptype == ProposalType.ENTITY_COMMAND:
            return self._to_entity_command_dict()
        elif ptype == ProposalType.SCRIPT:
            return self._to_script_dict()
        elif ptype == ProposalType.SCENE:
            return self._to_scene_dict()
        else:
            return self._to_automation_dict()

    def _to_automation_dict(self) -> dict:
        """Convert to HA automation YAML format."""
        automation = {
            "alias": self.name,
            "trigger": self.trigger if isinstance(self.trigger, list) else [self.trigger],
            "action": self.actions if isinstance(self.actions, list) else [self.actions],
            "mode": self.mode,
        }

        if self.description:
            automation["description"] = self.description

        if self.conditions:
            automation["condition"] = (
                self.conditions if isinstance(self.conditions, list) else [self.conditions]
            )

        return automation

    def _to_entity_command_dict(self) -> dict:
        """Convert to service call YAML format."""
        sc = self.service_call or {}
        result: dict[str, Any] = {
            "service": f"{sc.get('domain', 'homeassistant')}.{sc.get('service', 'turn_on')}",
        }
        if sc.get("entity_id"):
            result["target"] = {"entity_id": sc["entity_id"]}
        if sc.get("data"):
            result["data"] = sc["data"]
        if self.description:
            result["description"] = self.description
        return result

    def _to_script_dict(self) -> dict:
        """Convert to HA script YAML format."""
        script = {
            "alias": self.name,
            "sequence": self.actions if isinstance(self.actions, list) else [self.actions],
            "mode": self.mode,
        }
        if self.description:
            script["description"] = self.description
        return script

    def _to_scene_dict(self) -> dict:
        """Convert to HA scene YAML format."""
        scene: dict[str, Any] = {
            "name": self.name,
        }
        if self.actions:
            scene["entities"] = self.actions
        if self.description:
            scene["description"] = self.description  # not standard HA but useful
        return scene
