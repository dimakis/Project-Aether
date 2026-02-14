"""Analysis state for Data Scientist agent."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .base import MessageState
from .conversation import AutomationSuggestion
from .enums import AnalysisDepth, AnalysisType, ExecutionStrategy


class SpecialistFinding(BaseModel):
    """A single finding from one DS team specialist.

    Accumulated in TeamAnalysis.findings during multi-specialist analysis.
    Each specialist reads prior findings and flags cross-references or conflicts.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique finding identifier",
    )
    specialist: str = Field(
        description="Which specialist produced this: energy_analyst, behavioral_analyst, diagnostic_analyst",
    )
    finding_type: str = Field(
        description="Category: insight, concern, recommendation, data_quality_flag",
    )
    title: str = Field(description="Short title for the finding")
    description: str = Field(description="Detailed explanation")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entity IDs relevant to this finding",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data (metrics, stats, raw values)",
    )
    automation_suggestion: AutomationSuggestion | None = Field(
        default=None,
        description="Optional automation proposal if finding warrants one",
    )
    cross_references: list[str] = Field(
        default_factory=list,
        description="IDs of related findings from other specialists",
    )


class CommunicationEntry(BaseModel):
    """A single inter-agent communication event.

    Captures delegation, findings, cross-references, questions, and synthesis
    messages exchanged between specialist agents during an analysis session.

    Feature 33: DS Deep Analysis — communication log.
    """

    from_agent: str = Field(description="Source agent role (e.g. 'energy_analyst')")
    to_agent: str = Field(description="Target agent role or 'team' for broadcast")
    message_type: str = Field(
        description="Type of communication: finding, question, cross_reference, synthesis, status",
    )
    content: str = Field(description="The message text")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context: confidence, entities, finding_id, etc.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When this communication occurred",
    )


class TeamAnalysis(BaseModel):
    """Shared analysis state for the DS team.

    Passed through each specialist node in the LangGraph workflow.
    Each specialist reads prior findings, adds their own, and flags
    cross-references or conflicts. A synthesis step then merges findings.
    """

    request_id: str = Field(description="Unique analysis request identifier")
    request_summary: str = Field(
        description="What the user/Architect asked for",
    )
    findings: list[SpecialistFinding] = Field(
        default_factory=list,
        description="Accumulated findings from all specialists",
    )
    consensus: str | None = Field(
        default=None,
        description="Synthesized view after all specialists contribute",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Disagreements between specialists",
    )
    holistic_recommendations: list[str] = Field(
        default_factory=list,
        description="Combined, ranked recommendations",
    )
    synthesis_strategy: str | None = Field(
        default=None,
        description="Which synthesizer produced the consensus: 'programmatic' or 'llm'",
    )
    communication_log: list[CommunicationEntry] = Field(
        default_factory=list,
        description="Chronological log of inter-agent communications. "
        "Feature 33: DS Deep Analysis.",
    )
    shared_data: dict[str, Any] = Field(
        default_factory=dict,
        description="In-memory working data shared between specialists within "
        "a single analysis session. Specialists can write intermediate "
        "results (e.g. computed statistics, DataFrame-as-JSON) that later "
        "specialists can read in teamwork mode. Not persisted to DB. "
        "Feature 33: DS Deep Analysis — B3.",
    )


class ScriptExecution(BaseModel):
    """Record of a sandboxed script execution (Constitution: Isolation)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    script_content: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    sandbox_policy: str = "default"  # gVisor policy used
    timed_out: bool = False


class AnalysisState(MessageState):
    """State for data analysis workflow.

    Used by the Data Scientist agent for insights and visualizations.
    """

    analysis_type: AnalysisType = AnalysisType.CUSTOM
    mlflow_run_id: str | None = None

    # Feature 33: DS Deep Analysis — configurable depth and strategy
    depth: AnalysisDepth = Field(
        default=AnalysisDepth.STANDARD,
        description="Analysis depth: quick (fast), standard (default), or deep (full EDA).",
    )
    strategy: ExecutionStrategy = Field(
        default=ExecutionStrategy.PARALLEL,
        description="Execution strategy: parallel (fast) or teamwork (sequential + cross-consultation).",
    )

    # Input data
    entity_ids: list[str] = Field(
        default_factory=list,
        description="Entities to analyze",
    )
    time_range_hours: int = Field(
        default=24,
        description="Hours of history to analyze",
    )
    custom_query: str | None = None
    diagnostic_context: str | None = Field(
        default=None,
        description="Pre-collected diagnostic data from Architect (logs, history, observations)",
    )

    # Script execution (Constitution: Isolation - gVisor sandbox)
    generated_script: str | None = None
    script_executions: list[ScriptExecution] = Field(default_factory=list)

    # Results
    insights: list[dict[str, Any]] = Field(default_factory=list)
    visualizations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Generated charts/graphs metadata",
    )
    recommendations: list[str] = Field(default_factory=list)

    # Reverse communication: automation suggestion from Data Scientist
    automation_suggestion: AutomationSuggestion | None = Field(
        default=None,
        description=(
            "Structured automation suggestion from the DS Team when a "
            "high-confidence, high-impact insight is detected. Contains pattern, "
            "entities, proposed trigger/action, and evidence."
        ),
    )

    # Dashboard output (User Story 4)
    dashboard_yaml: str | None = None

    # DS team shared analysis (multi-specialist collaboration)
    team_analysis: TeamAnalysis | None = Field(
        default=None,
        description="Shared analysis state for the DS team. Populated during multi-specialist workflows.",
    )
