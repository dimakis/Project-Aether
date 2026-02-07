"""Podman + gVisor script execution runner.

Executes Python scripts in isolated containers using Podman
with the gVisor (runsc) runtime for secure sandboxing.

Constitution: Isolation - All analysis scripts run in sandbox.
"""

import asyncio
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.sandbox.policies import SandboxPolicy, get_default_policy
from src.settings import get_settings


class SandboxResult(BaseModel):
    """Result of a sandboxed script execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    success: bool = Field(..., description="Whether execution completed successfully")
    exit_code: int = Field(..., description="Process exit code")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    duration_seconds: float = Field(..., description="Execution time")
    timed_out: bool = Field(default=False, description="Whether execution timed out")
    policy_name: str = Field(..., description="Policy used for execution")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Resource usage (if available)
    memory_peak_mb: float | None = None
    cpu_time_seconds: float | None = None


class SandboxRunner:
    """Runs scripts in isolated Podman containers with gVisor.

    Usage:
        runner = SandboxRunner()
        result = await runner.run("print('hello')")

        # With custom policy
        policy = get_policy("minimal")
        result = await runner.run("1 + 1", policy=policy)

        # With data mount
        result = await runner.run(
            script,
            policy=policy,
            data_path=Path("/path/to/data"),
        )
    """

    # Default container image for Python scripts
    # Use custom data science image with pandas, numpy, matplotlib, etc.
    # Build with: podman build -t aether-sandbox -f infrastructure/podman/Containerfile.sandbox .
    DEFAULT_IMAGE = "aether-sandbox:latest"
    
    # Fallback image if custom image not available
    FALLBACK_IMAGE = "python:3.11-slim"

    def __init__(
        self,
        image: str | None = None,
        podman_path: str = "podman",
    ) -> None:
        """Initialize the sandbox runner.

        Args:
            image: Container image to use (default: python:3.11-slim)
            podman_path: Path to podman executable
        """
        self.image = image or self.DEFAULT_IMAGE
        self.podman_path = podman_path
        self._gvisor_available: bool | None = None  # Cached check result

    async def run(
        self,
        script: str,
        policy: SandboxPolicy | None = None,
        data_path: Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a Python script in a sandboxed container.

        Args:
            script: Python script content to execute
            policy: Security policy (defaults to standard policy)
            data_path: Optional path to mount as read-only data
            environment: Optional environment variables

        Returns:
            SandboxResult with execution details
        """
        policy = policy or get_default_policy()
        settings = get_settings()

        # Check if sandbox is enabled
        if not settings.sandbox_enabled:
            # SECURITY: Never allow unsandboxed execution in production.
            # Constitution Principle II (Isolation) requires all generated
            # scripts to run in a gVisor sandbox.
            if settings.environment == "production":
                from src.exceptions import ConfigurationError

                raise ConfigurationError(
                    "Sandbox MUST be enabled in production (SANDBOX_ENABLED=true). "
                    "Unsandboxed script execution is only permitted in development."
                )
            return await self._run_unsandboxed(script, policy)

        started_at = datetime.now(timezone.utc)
        start_time = asyncio.get_event_loop().time()

        # Create temp file for the script
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as f:
            f.write(script)
            script_path = Path(f.name)

        try:
            # Build command
            cmd = await self._build_command(
                script_path=script_path,
                policy=policy,
                data_path=data_path,
                environment=environment,
            )

            # Execute with timeout
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=policy.timeout_seconds,
                    )
                    timed_out = False
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    stdout_bytes = b""
                    stderr_bytes = b"Execution timed out"
                    timed_out = True

                exit_code = process.returncode or 0
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

            except FileNotFoundError:
                # Podman not installed
                return SandboxResult(
                    success=False,
                    exit_code=-1,
                    stderr=f"Podman not found at '{self.podman_path}'. "
                    "Install Podman or disable sandbox.",
                    duration_seconds=0,
                    policy_name=policy.name,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )

            except Exception as e:
                return SandboxResult(
                    success=False,
                    exit_code=-1,
                    stderr=f"Sandbox error: {e!s}",
                    duration_seconds=asyncio.get_event_loop().time() - start_time,
                    policy_name=policy.name,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )

            duration = asyncio.get_event_loop().time() - start_time
            completed_at = datetime.now(timezone.utc)

            return SandboxResult(
                success=exit_code == 0 and not timed_out,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                timed_out=timed_out,
                policy_name=policy.name,
                started_at=started_at,
                completed_at=completed_at,
            )

        finally:
            # Cleanup temp file
            script_path.unlink(missing_ok=True)

    async def _is_gvisor_available(self) -> bool:
        """Check if gVisor (runsc) runtime is available.

        Returns:
            True if gVisor is available
        """
        if self._gvisor_available is not None:
            return self._gvisor_available

        try:
            process = await asyncio.create_subprocess_exec(
                self.podman_path,
                "info",
                "--format",
                "{{.Host.OCIRuntime.Name}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            # Check if runsc is configured
            if b"runsc" in stdout:
                self._gvisor_available = True
            else:
                # Also check runtimes list
                proc2 = await asyncio.create_subprocess_exec(
                    self.podman_path,
                    "info",
                    "--format",
                    "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout2, _ = await proc2.communicate()
                self._gvisor_available = b"runsc" in stdout2

        except Exception:
            self._gvisor_available = False

        return self._gvisor_available

    async def _build_command(
        self,
        script_path: Path,
        policy: SandboxPolicy,
        data_path: Path | None,
        environment: dict[str, str] | None,
    ) -> list[str]:
        """Build the Podman command.

        Args:
            script_path: Path to the script file
            policy: Security policy
            data_path: Optional data mount path
            environment: Optional environment variables

        Returns:
            Complete command as list of strings
        """
        cmd = [self.podman_path, "run", "--rm"]

        # Check if gVisor is available when policy requires it
        if policy.use_gvisor and not await self._is_gvisor_available():
            # Create a copy of the policy with gVisor disabled
            # Also disable seccomp as it may not be available on all platforms (e.g., macOS)
            import logging

            logging.getLogger(__name__).warning(
                "gVisor (runsc) not available - running with standard container isolation"
            )
            policy = policy.model_copy(update={
                "use_gvisor": False,
                "seccomp_profile": None,  # Disable seccomp on non-gVisor systems
            })

        # Add policy args
        cmd.extend(policy.to_podman_args())

        # Mount script
        cmd.extend(
            [
                "--volume",
                f"{script_path}:/workspace/script.py:ro",
            ]
        )

        # Mount data if provided — at /workspace/data.json to match the
        # Data Scientist system prompt which tells the LLM to read from there.
        if data_path and data_path.exists():
            cmd.extend(
                [
                    "--volume",
                    f"{data_path}:/workspace/data.json:ro",
                ]
            )

        # Environment variables
        if environment:
            for key, value in environment.items():
                # Sanitize: only allow alphanumeric + underscore keys
                if key.replace("_", "").isalnum():
                    cmd.extend(["--env", f"{key}={value}"])

        # Container image (check availability)
        image = await self._get_available_image()
        cmd.extend([image, "python", "/workspace/script.py"])

        return cmd

    async def _get_available_image(self) -> str:
        """Get an available container image, falling back if necessary.

        Returns:
            Available container image name
        """
        # Check if preferred image exists
        try:
            process = await asyncio.create_subprocess_exec(
                self.podman_path,
                "image",
                "exists",
                self.image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if process.returncode == 0:
                return self.image

        except Exception:
            pass

        # Fall back to basic Python image
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Container image '{self.image}' not found — falling back to '{self.FALLBACK_IMAGE}'. "
            f"The fallback image lacks data-science packages (numpy, pandas, scipy, etc.) "
            f"and analysis scripts WILL fail. Build the sandbox image with:\n"
            f"  make build-sandbox"
        )
        return self.FALLBACK_IMAGE

    async def _run_unsandboxed(
        self,
        script: str,
        policy: SandboxPolicy,
    ) -> SandboxResult:
        """Run script without sandboxing (for development/testing).

        WARNING: Only use when sandbox_enabled=False in settings.
        This runs the script directly without isolation.

        Args:
            script: Python script to run
            policy: Policy (used for timeout only)

        Returns:
            SandboxResult
        """
        import sys

        started_at = datetime.now(timezone.utc)
        start_time = asyncio.get_event_loop().time()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as f:
            f.write(script)
            script_path = Path(f.name)

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=policy.timeout_seconds,
                )
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = b"Execution timed out"
                timed_out = True

            duration = asyncio.get_event_loop().time() - start_time

            return SandboxResult(
                success=process.returncode == 0 and not timed_out,
                exit_code=process.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                duration_seconds=duration,
                timed_out=timed_out,
                policy_name=f"{policy.name}:unsandboxed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        finally:
            script_path.unlink(missing_ok=True)

    async def check_runtime(self) -> dict[str, Any]:
        """Check if the sandbox runtime is available.

        Returns:
            Dictionary with runtime status information
        """
        result: dict[str, Any] = {
            "podman_available": False,
            "gvisor_available": False,
            "image_available": False,
            "errors": [],
        }

        # Check Podman
        try:
            process = await asyncio.create_subprocess_exec(
                self.podman_path,
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result["podman_available"] = True
                result["podman_version"] = stdout.decode().strip()
        except FileNotFoundError:
            result["errors"].append("Podman not found")

        # Check gVisor runtime
        if result["podman_available"]:
            try:
                process = await asyncio.create_subprocess_exec(
                    self.podman_path,
                    "info",
                    "--format",
                    "{{.Host.OCIRuntime.Path}}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()

                # Check if runsc is available as a runtime
                runtimes_proc = await asyncio.create_subprocess_exec(
                    self.podman_path,
                    "info",
                    "--format",
                    "{{json .Host.Runtimes}}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                runtimes_out, _ = await runtimes_proc.communicate()

                if b"runsc" in runtimes_out:
                    result["gvisor_available"] = True
                else:
                    result["errors"].append("gVisor (runsc) runtime not configured")

            except Exception as e:
                result["errors"].append(f"Error checking runtimes: {e}")

        # Check image availability
        if result["podman_available"]:
            try:
                process = await asyncio.create_subprocess_exec(
                    self.podman_path,
                    "image",
                    "exists",
                    self.image,
                )
                await process.communicate()

                result["image_available"] = process.returncode == 0
                if not result["image_available"]:
                    result["errors"].append(f"Image '{self.image}' not found locally")

            except Exception as e:
                result["errors"].append(f"Error checking image: {e}")

        return result


# Convenience function
async def run_script(
    script: str,
    policy: SandboxPolicy | None = None,
    data_path: Path | None = None,
) -> SandboxResult:
    """Run a script in the sandbox.

    Convenience wrapper around SandboxRunner.run().

    Args:
        script: Python script to execute
        policy: Security policy (default: standard)
        data_path: Optional path to mount as read-only data

    Returns:
        SandboxResult with execution details
    """
    runner = SandboxRunner()
    return await runner.run(script, policy=policy, data_path=data_path)


__all__ = [
    "SandboxResult",
    "SandboxRunner",
    "run_script",
]
