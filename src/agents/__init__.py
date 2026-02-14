"""Agent base classes and concrete agent implementations.

All agent classes are re-exported here for backward compatibility.
Canonical definitions live in their own modules:
- base.py: BaseAgent, AgentContext
- librarian.py: LibrarianAgent
- architect/: ArchitectAgent, ArchitectWorkflow, StreamEvent
- data_scientist/: DataScientistAgent, DataScientistWorkflow
- developer.py: DeveloperAgent, DeveloperWorkflow
- dashboard_designer.py: DashboardDesignerAgent
- behavioral_analyst.py: BehavioralAnalyst
- diagnostic_analyst.py: DiagnosticAnalyst
- energy_analyst.py: EnergyAnalyst
"""

# Base classes (canonical: src.agents.base)
from src.agents.base import AgentContext, BaseAgent
from src.agents.execution_context import emit_progress  # noqa: F401
from src.graph.state import AgentRole, BaseState  # noqa: F401
from src.tracing import add_span_event, get_active_span, log_dict, log_param  # noqa: F401

# Librarian agent (canonical: src.agents.librarian)
from src.agents.librarian import LibrarianAgent

# Other agents
from src.agents.architect import ArchitectAgent, ArchitectWorkflow, StreamEvent
from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.dashboard_designer import DashboardDesignerAgent
from src.agents.data_scientist import DataScientistAgent, DataScientistWorkflow
from src.agents.developer import DeveloperAgent, DeveloperWorkflow
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst

# Exports
__all__ = [
    "AgentContext",
    "ArchitectAgent",
    "ArchitectWorkflow",
    "BaseAgent",
    "BehavioralAnalyst",
    "DashboardDesignerAgent",
    "DataScientistAgent",
    "DataScientistWorkflow",
    "DeveloperAgent",
    "DeveloperWorkflow",
    "DiagnosticAnalyst",
    "EnergyAnalyst",
    "LibrarianAgent",
    "StreamEvent",
]
