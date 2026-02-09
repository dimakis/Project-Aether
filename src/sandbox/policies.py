"""gVisor security policies for sandbox isolation.

Defines security policies that control what sandboxed scripts can access.
Each policy specifies network access, filesystem mounts, resource limits,
and syscall restrictions.

Constitution: Isolation - All scripts run with restricted capabilities.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PolicyLevel(StrEnum):
    """Security policy levels from most to least restrictive."""

    MINIMAL = "minimal"  # Most restrictive - only computation
    ANALYSIS = "analysis"  # Read-only data access
    STANDARD = "standard"  # Default for data science scripts
    EXTENDED = "extended"  # More resources, still isolated


class NetworkPolicy(StrEnum):
    """Network access policies."""

    NONE = "none"  # No network access (default)
    LOCAL_ONLY = "local_only"  # Only localhost (for inter-container comms)
    LIMITED = "limited"  # Specific allowed hosts


class MountMode(StrEnum):
    """Filesystem mount modes."""

    READ_ONLY = "ro"
    READ_WRITE = "rw"


class Mount(BaseModel):
    """Filesystem mount configuration."""

    source: Path = Field(..., description="Host path to mount")
    target: Path = Field(..., description="Container path")
    mode: MountMode = Field(default=MountMode.READ_ONLY, description="Mount mode")


class ResourceLimits(BaseModel):
    """Container resource limits."""

    memory_mb: int = Field(default=512, ge=64, le=4096, description="Memory limit in MB")
    cpu_shares: int = Field(default=256, ge=64, le=1024, description="CPU shares")
    cpu_period: int = Field(default=100000, description="CPU period in microseconds")
    cpu_quota: int = Field(default=50000, description="CPU quota in microseconds")
    pids_limit: int = Field(default=64, ge=8, le=256, description="Maximum number of processes")
    nofile_soft: int = Field(default=256, description="Soft limit on open files")
    nofile_hard: int = Field(default=512, description="Hard limit on open files")


class SandboxPolicy(BaseModel):
    """Complete sandbox security policy.

    Defines all security constraints for a sandboxed script execution.
    Policies are immutable after creation.
    """

    name: str = Field(..., description="Policy identifier")
    level: PolicyLevel = Field(..., description="Security level")

    # Timeouts
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum execution time",
    )

    # Network
    network: NetworkPolicy = Field(
        default=NetworkPolicy.NONE,
        description="Network access policy",
    )
    allowed_hosts: list[str] = Field(
        default_factory=list,
        description="Allowed hosts (if network=LIMITED)",
    )

    # Filesystem
    mounts: list[Mount] = Field(
        default_factory=list,
        description="Filesystem mounts",
    )
    temp_dir_mb: int = Field(
        default=100,
        ge=10,
        le=1024,
        description="Temp directory size in MB",
    )

    # Resources
    resources: ResourceLimits = Field(
        default_factory=ResourceLimits,
        description="Resource limits",
    )

    # Execution
    working_dir: Path = Field(
        default=Path("/workspace"),
        description="Working directory in container",
    )
    user: str = Field(
        default="nobody",
        description="User to run as",
    )
    read_only_root: bool = Field(
        default=True,
        description="Make root filesystem read-only",
    )

    # gVisor specific
    use_gvisor: bool = Field(
        default=True,
        description="Use gVisor (runsc) runtime",
    )
    gvisor_platform: str = Field(
        default="systrap",
        description="gVisor platform (systrap, kvm, ptrace)",
    )

    # Security capabilities
    drop_all_caps: bool = Field(
        default=True,
        description="Drop all Linux capabilities",
    )
    no_new_privileges: bool = Field(
        default=True,
        description="Prevent privilege escalation",
    )
    seccomp_profile: str | None = Field(
        default="default",
        description="Seccomp profile (null for none)",
    )

    def to_podman_args(self) -> list[str]:
        """Convert policy to Podman command-line arguments.

        Returns:
            List of Podman CLI arguments
        """
        args: list[str] = []

        # Runtime
        if self.use_gvisor:
            args.extend(["--runtime", "runsc"])

        # Resource limits
        args.extend(
            [
                "--memory",
                f"{self.resources.memory_mb}m",
                "--cpu-shares",
                str(self.resources.cpu_shares),
                "--cpu-period",
                str(self.resources.cpu_period),
                "--cpu-quota",
                str(self.resources.cpu_quota),
                "--pids-limit",
                str(self.resources.pids_limit),
                "--ulimit",
                f"nofile={self.resources.nofile_soft}:{self.resources.nofile_hard}",
            ]
        )

        # Network
        if self.network == NetworkPolicy.NONE:
            args.append("--network=none")
        elif self.network == NetworkPolicy.LOCAL_ONLY:
            args.append("--network=host")  # Will be restricted by gVisor

        # Filesystem
        if self.read_only_root:
            args.append("--read-only")

        # Temp filesystem
        args.extend(["--tmpfs", f"/tmp:size={self.temp_dir_mb}m,mode=1777"])  # nosec B108

        # Mounts
        for mount in self.mounts:
            args.extend(
                [
                    "--volume",
                    f"{mount.source}:{mount.target}:{mount.mode.value}",
                ]
            )

        # Working directory
        args.extend(["--workdir", str(self.working_dir)])

        # User
        args.extend(["--user", self.user])

        # Security
        if self.drop_all_caps:
            args.append("--cap-drop=ALL")

        if self.no_new_privileges:
            args.append("--security-opt=no-new-privileges:true")

        if self.seccomp_profile:
            args.append(f"--security-opt=seccomp={self.seccomp_profile}")

        return args

    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dictionary for logging/storage."""
        return self.model_dump()


# =============================================================================
# PREDEFINED POLICIES
# =============================================================================


def _minimal_policy() -> SandboxPolicy:
    """Most restrictive policy - pure computation only."""
    return SandboxPolicy(
        name="minimal",
        level=PolicyLevel.MINIMAL,
        timeout_seconds=10,
        network=NetworkPolicy.NONE,
        resources=ResourceLimits(
            memory_mb=128,
            cpu_shares=128,
            pids_limit=16,
        ),
        temp_dir_mb=10,
    )


def _analysis_policy() -> SandboxPolicy:
    """Read-only data analysis policy."""
    return SandboxPolicy(
        name="analysis",
        level=PolicyLevel.ANALYSIS,
        timeout_seconds=30,
        network=NetworkPolicy.NONE,
        resources=ResourceLimits(
            memory_mb=512,
            cpu_shares=256,
            pids_limit=32,
        ),
        temp_dir_mb=50,
    )


def _standard_policy() -> SandboxPolicy:
    """Standard data science policy."""
    return SandboxPolicy(
        name="standard",
        level=PolicyLevel.STANDARD,
        timeout_seconds=60,
        network=NetworkPolicy.NONE,
        resources=ResourceLimits(
            memory_mb=1024,
            cpu_shares=512,
            pids_limit=64,
        ),
        temp_dir_mb=100,
    )


def _extended_policy() -> SandboxPolicy:
    """Extended policy for resource-intensive analysis."""
    return SandboxPolicy(
        name="extended",
        level=PolicyLevel.EXTENDED,
        timeout_seconds=180,
        network=NetworkPolicy.NONE,
        resources=ResourceLimits(
            memory_mb=2048,
            cpu_shares=768,
            pids_limit=128,
        ),
        temp_dir_mb=256,
    )


# Policy registry
_POLICIES: dict[str, SandboxPolicy] = {
    "minimal": _minimal_policy(),
    "analysis": _analysis_policy(),
    "standard": _standard_policy(),
    "extended": _extended_policy(),
}


def get_policy(name: str) -> SandboxPolicy:
    """Get a predefined policy by name.

    Args:
        name: Policy name (minimal, analysis, standard, extended)

    Returns:
        SandboxPolicy instance

    Raises:
        ValueError: If policy name is unknown
    """
    if name not in _POLICIES:
        available = ", ".join(_POLICIES.keys())
        msg = f"Unknown policy '{name}'. Available: {available}"
        raise ValueError(msg)

    return _POLICIES[name]


def get_default_policy() -> SandboxPolicy:
    """Get the default sandbox policy.

    Returns:
        Standard policy for data science scripts
    """
    return get_policy("standard")


__all__ = [
    "Mount",
    "MountMode",
    "NetworkPolicy",
    "PolicyLevel",
    "ResourceLimits",
    "SandboxPolicy",
    "get_default_policy",
    "get_policy",
]
