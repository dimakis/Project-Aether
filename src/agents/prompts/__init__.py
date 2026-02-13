"""Prompt loader for agent system prompts.

Loads prompt templates from markdown files and supports dynamic formatting.
Feature 23 extends this to check DB-backed prompt versions first.
"""

from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent

# Agent name -> prompt file name mapping
_AGENT_PROMPT_MAP: dict[str, str] = {
    "architect": "architect_system",
    "data_scientist": "data_scientist_system",
}


@lru_cache(maxsize=32)
def _load_raw(name: str) -> str:
    """Load raw prompt template from disk (cached).

    Args:
        name: Prompt name (without .md extension)

    Returns:
        Raw template string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {name}.md")
    return path.read_text(encoding="utf-8")


def load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt template and optionally format with kwargs.

    Templates are cached on disk read; formatting is applied per call
    so dynamic values work correctly.

    Args:
        name: Prompt name (without .md extension)
        **kwargs: Formatting arguments for the template

    Returns:
        Loaded and formatted prompt string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    template = _load_raw(name)
    if kwargs:
        template = template.format(**kwargs)
    return template


def load_depth_fragment(depth: str) -> str:
    """Load the EDA depth prompt fragment for a given analysis depth.

    Feature 33: DS Deep Analysis — depth-aware prompt composition.

    Args:
        depth: One of ``"quick"``, ``"standard"``, ``"deep"``.

    Returns:
        Prompt fragment string (empty string if not found, to allow graceful fallback).
    """
    name = f"eda_depth_{depth}"
    try:
        return _load_raw(name)
    except FileNotFoundError:
        return ""


def load_strategy_fragment(strategy: str, **kwargs: str) -> str:
    """Load the execution strategy prompt fragment.

    Feature 33: DS Deep Analysis — strategy-aware prompt composition.

    Args:
        strategy: One of ``"parallel"``, ``"teamwork"``.
        **kwargs: Formatting arguments (e.g. ``prior_findings``).

    Returns:
        Prompt fragment string (empty string for parallel or if not found).
    """
    if strategy == "parallel":
        return ""  # No additional fragment needed for parallel
    name = f"strategy_{strategy}"
    try:
        template = _load_raw(name)
        if kwargs:
            template = template.format(**kwargs)
        return template
    except FileNotFoundError:
        return ""


def load_prompt_for_agent(agent_name: str, db_prompt: str | None = None, **kwargs: str) -> str:
    """Load a prompt for an agent, checking DB-backed version first.

    Feature 23: Resolution order:
        1. DB-backed active prompt version (passed in)
        2. File-based prompt template (existing behavior)

    Args:
        agent_name: Agent identifier (e.g. 'architect', 'data_scientist')
        db_prompt: Optional DB-backed prompt template text
        **kwargs: Formatting arguments for the template

    Returns:
        Loaded and formatted prompt string

    Raises:
        FileNotFoundError: If no prompt found in DB or on disk
    """
    # Priority 1: DB-backed prompt
    if db_prompt:
        template = db_prompt
        if kwargs:
            template = template.format(**kwargs)
        return template

    # Priority 2: File-based prompt
    prompt_name = _AGENT_PROMPT_MAP.get(agent_name)
    if prompt_name:
        return load_prompt(prompt_name, **kwargs)

    raise FileNotFoundError(f"No prompt template found for agent: {agent_name}")
