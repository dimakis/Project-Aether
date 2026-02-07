"""Prompt loader for agent system prompts.

Loads prompt templates from markdown files and supports dynamic formatting.
"""

from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent


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
