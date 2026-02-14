"""Workflow presets for task flow customization."""

from pydantic import BaseModel, Field


class WorkflowPreset(BaseModel):
    """A preset workflow configuration for task flow customization.

    Defines which agents participate and which workflow graph to use
    for a given task type.
    """

    id: str
    name: str
    description: str
    agents: list[str] = Field(default_factory=list)
    workflow_key: str
    icon: str | None = None


DEFAULT_WORKFLOW_PRESETS: list[WorkflowPreset] = [
    WorkflowPreset(
        id="full-analysis",
        name="Full Analysis",
        description="Run all DS team specialists with programmatic synthesis for comprehensive insights.",
        agents=["energy_analyst", "behavioral_analyst", "diagnostic_analyst"],
        workflow_key="team_analysis",
        icon="bar-chart-3",
    ),
    WorkflowPreset(
        id="energy-only",
        name="Energy Only",
        description="Focus on energy consumption analysis and cost optimization.",
        agents=["energy_analyst"],
        workflow_key="team_analysis",
        icon="zap",
    ),
    WorkflowPreset(
        id="quick-diagnostic",
        name="Quick Diagnostic",
        description="Run diagnostic checks on system health, errors, and integrations.",
        agents=["diagnostic_analyst"],
        workflow_key="team_analysis",
        icon="stethoscope",
    ),
    WorkflowPreset(
        id="dashboard-design",
        name="Dashboard Design",
        description="Design Lovelace dashboards with DS team consultation for data-driven layouts.",
        agents=["dashboard_designer", "energy_analyst", "behavioral_analyst"],
        workflow_key="dashboard",
        icon="layout-dashboard",
    ),
    WorkflowPreset(
        id="conversation",
        name="General Chat",
        description="Open-ended conversation with the Architect agent.",
        agents=["architect"],
        workflow_key="conversation",
        icon="message-square",
    ),
]
