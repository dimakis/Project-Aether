"""Enums for graph state."""

from enum import StrEnum


class AgentRole(StrEnum):
    """Agent roles in the system."""

    LIBRARIAN = "librarian"
    CATEGORIZER = "categorizer"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    DATA_SCIENTIST = "data_scientist"
    ORCHESTRATOR = "orchestrator"
    # DS team specialists
    ENERGY_ANALYST = "energy_analyst"
    BEHAVIORAL_ANALYST = "behavioral_analyst"
    DIAGNOSTIC_ANALYST = "diagnostic_analyst"
    # Dashboard designer
    DASHBOARD_DESIGNER = "dashboard_designer"


class ConversationStatus(StrEnum):
    """Status of a conversation session."""

    ACTIVE = "active"
    WAITING_APPROVAL = "waiting_approval"  # HITL (Constitution: Safety First)
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryStatus(StrEnum):
    """Status of an entity discovery session."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalDecision(StrEnum):
    """User decision for HITL approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnalysisDepth(StrEnum):
    """Depth of analysis to perform.

    Controls sandbox resource limits, prompt detail, and chart generation.
    Feature 33: DS Deep Analysis.
    """

    QUICK = "quick"  # Summary stats only, fast
    STANDARD = "standard"  # Current default behavior
    DEEP = "deep"  # Full EDA, correlations, charts, statistical tests


class ExecutionStrategy(StrEnum):
    """How DS team specialists execute.

    Controls whether specialists run in parallel or sequentially with
    cross-consultation.  Feature 33: DS Deep Analysis.
    """

    PARALLEL = "parallel"  # Fast: all specialists run simultaneously (default)
    TEAMWORK = "teamwork"  # Sequential with cross-consultation and discussion rounds


class AnalysisType(StrEnum):
    """Types of analysis the Data Scientist can perform."""

    ENERGY_OPTIMIZATION = "energy_optimization"
    USAGE_PATTERNS = "usage_patterns"
    ANOMALY_DETECTION = "anomaly_detection"
    DASHBOARD_GENERATION = "dashboard_generation"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"
    # Feature 03: Intelligent Optimization
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    AUTOMATION_ANALYSIS = "automation_analysis"
    AUTOMATION_GAP_DETECTION = "automation_gap_detection"
    CORRELATION_DISCOVERY = "correlation_discovery"
    DEVICE_HEALTH = "device_health"
    COST_OPTIMIZATION = "cost_optimization"
