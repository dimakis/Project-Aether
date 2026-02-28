"""Specialist delegation tools for the Architect.

These tools allow the Architect to delegate analysis tasks to the
DS team specialists (Energy, Behavioral, Diagnostic) and request
LLM synthesis reviews for complex/conflicting findings.

The Architect calls these tools during conversation to gather
specialist insights, which are accumulated in a TeamAnalysis object
for cross-consultation and synthesis.

The primary entry point is ``consult_data_science_team`` which acts
as a programmatic "Head DS" — it selects the right specialists based
on query keywords (or an explicit override), runs them with shared
TeamAnalysis, and auto-synthesises a unified response.
"""

from __future__ import annotations

from src.tools.ds_team_runners import (  # noqa: F401
    _run_behavioral,
    _run_diagnostic,
    _run_energy,
)
from src.tools.ds_team_strategies import (  # noqa: F401
    _run_discussion_round,
    _run_parallel,
    _run_teamwork,
)
from src.tools.ds_team_tool import consult_data_science_team
from src.tools.specialist_consult_tools import (
    consult_behavioral_analyst,
    consult_dashboard_designer,
    consult_diagnostic_analyst,
    consult_energy_analyst,
    request_synthesis_review,
)
from src.tools.specialist_routing import (  # noqa: F401
    SPECIALIST_TRIGGERS,
    _format_findings,
    _get_or_create_team_analysis,
    _select_specialists,
    _set_team_analysis,
    reset_team_analysis,
)


def get_specialist_tools() -> list:
    return [
        consult_energy_analyst,
        consult_behavioral_analyst,
        consult_diagnostic_analyst,
        request_synthesis_review,
        consult_data_science_team,
        consult_dashboard_designer,
    ]
