"""HA Automation, Script, Scene, and Service API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# AUTOMATION SCHEMAS
# =============================================================================


class AutomationBase(BaseModel):
    """Base automation schema."""

    entity_id: str = Field(..., description="Entity ID (automation.xxx)")
    alias: str = Field(..., description="Automation display name")
    state: str = Field("on", description="Current state (on/off)")


class AutomationResponse(AutomationBase):
    """Automation response with all fields."""

    id: str = Field(..., description="Internal UUID")
    ha_automation_id: str = Field(..., description="HA automation ID")
    description: str | None = None
    mode: str = Field("single", description="Execution mode")
    trigger_types: list[str] | None = None
    trigger_count: int = 0
    action_count: int = 0
    condition_count: int = 0
    last_triggered: str | None = None
    last_synced_at: datetime | None = None

    class Config:
        from_attributes = True


class AutomationListResponse(BaseModel):
    """Response for automation list."""

    automations: list[AutomationResponse]
    total: int
    enabled_count: int = Field(0, description="Number of enabled automations")
    disabled_count: int = Field(0, description="Number of disabled automations")


# =============================================================================
# SCRIPT SCHEMAS
# =============================================================================


class ScriptBase(BaseModel):
    """Base script schema."""

    entity_id: str = Field(..., description="Entity ID (script.xxx)")
    alias: str = Field(..., description="Script display name")
    state: str = Field("off", description="Current state (on=running, off=idle)")


class ScriptResponse(ScriptBase):
    """Script response with all fields."""

    id: str = Field(..., description="Internal UUID")
    description: str | None = None
    mode: str = Field("single", description="Execution mode")
    icon: str | None = None
    last_triggered: str | None = None
    last_synced_at: datetime | None = None
    # MCP Gap: sequence and fields are null until get_script_config available
    sequence: list[Any] | None = Field(
        None,
        description="Script sequence (null - HA gap)",
    )
    fields: dict[str, Any] | None = Field(
        None,
        description="Script input fields (null - HA gap)",
    )

    class Config:
        from_attributes = True


class ScriptListResponse(BaseModel):
    """Response for script list."""

    scripts: list[ScriptResponse]
    total: int
    running_count: int = Field(0, description="Number of running scripts")


# =============================================================================
# SCENE SCHEMAS
# =============================================================================


class SceneBase(BaseModel):
    """Base scene schema."""

    entity_id: str = Field(..., description="Entity ID (scene.xxx)")
    name: str = Field(..., description="Scene display name")


class SceneResponse(SceneBase):
    """Scene response with all fields."""

    id: str = Field(..., description="Internal UUID")
    icon: str | None = None
    last_synced_at: datetime | None = None
    # MCP Gap: entity_states is null until get_scene_config available
    entity_states: dict[str, Any] | None = Field(
        None,
        description="Entity states in scene (null - HA gap)",
    )

    class Config:
        from_attributes = True


class SceneListResponse(BaseModel):
    """Response for scene list."""

    scenes: list[SceneResponse]
    total: int


# =============================================================================
# SERVICE SCHEMAS
# =============================================================================


class ServiceFieldSchema(BaseModel):
    """Schema for a service input field."""

    description: str | None = None
    required: bool = False
    example: Any = None
    selector: dict[str, Any] | None = None


class ServiceBase(BaseModel):
    """Base service schema."""

    domain: str = Field(..., description="Service domain (e.g., light)")
    service: str = Field(..., description="Service name (e.g., turn_on)")


class ServiceResponse(ServiceBase):
    """Service response with all fields."""

    id: str = Field(..., description="Internal UUID")
    name: str | None = Field(None, description="Human-readable name")
    description: str | None = None
    fields: dict[str, Any] | None = Field(
        None,
        description="Service input fields schema",
    )
    target: dict[str, Any] | None = Field(
        None,
        description="Target specification",
    )
    is_seeded: bool = Field(False, description="Whether this is a seeded common service")

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        """Get the full service name (domain.service)."""
        return f"{self.domain}.{self.service}"


class ServiceListResponse(BaseModel):
    """Response for service list."""

    services: list[ServiceResponse]
    total: int
    domains: list[str] = Field(
        default_factory=list,
        description="Unique domains in the list",
    )
    seeded_count: int = Field(0, description="Number of seeded services")
    discovered_count: int = Field(0, description="Number of discovered services")


class ServiceCallRequest(BaseModel):
    """Request to call a service."""

    domain: str = Field(..., max_length=100, description="Service domain")
    service: str = Field(..., max_length=100, description="Service name")
    data: dict[str, Any] | None = Field(
        None,
        description="Service call data (including target entity_id)",
    )


class ServiceCallResponse(BaseModel):
    """Response from a service call."""

    success: bool
    domain: str
    service: str
    message: str | None = None


# =============================================================================
# HA REGISTRY SUMMARY SCHEMA
# =============================================================================


class HARegistrySummary(BaseModel):
    """Summary of HA registry (automations, scripts, scenes, services, helpers)."""

    automations_count: int = 0
    automations_enabled: int = 0
    scripts_count: int = 0
    scenes_count: int = 0
    services_count: int = 0
    services_seeded: int = 0
    helpers_count: int = 0
    last_synced_at: datetime | None = None
    mcp_gaps: list[str] = Field(
        default_factory=list,
        description="Known MCP capability gaps affecting this data",
    )
