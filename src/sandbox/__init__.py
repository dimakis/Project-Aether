"""Sandbox infrastructure for isolated script execution.

Implements the Constitution's Isolation requirement:
"All generated analysis scripts must run in a gVisor (runsc) sandbox."

This module provides secure script execution using Podman containers
with gVisor (runsc) runtime for defense-in-depth isolation.
"""

from src.sandbox.policies import SandboxPolicy, get_default_policy, get_policy
from src.sandbox.runner import SandboxResult, SandboxRunner, run_script

__all__ = [
    # Policies
    "SandboxPolicy",
    "get_policy",
    "get_default_policy",
    # Runner
    "SandboxRunner",
    "SandboxResult",
    "run_script",
]
