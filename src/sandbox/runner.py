"""Podman + gVisor script execution runner.

Executes Python scripts in isolated containers using Podman
with the gVisor (runsc) runtime for secure sandboxing.

Constitution: Isolation - All analysis scripts run in sandbox.
"""

import asyncio
import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.sandbox.policies import SandboxPolicy, get_default_policy
from src.settings import get_settings
from src.tracing.mlflow_spans import get_active_span, trace_with_uri

logger = logging.getLogger(__name__)

# Truncation limits for span attributes (FR-007)
_STDOUT_ATTR_MAX = 4096  # 4KB
_STDERR_ATTR_MAX = 2048  # 2KB


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
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # Resource usage (if available)
    memory_peak_mb: float | None = None
    cpu_time_seconds: float | None = None

    # Artifact output (Constitution: Isolation + Security)
    artifacts: list[Any] = Field(
        default_factory=list,
        description="Validated artifact metadata from sandbox output",
    )
    artifacts_rejected: int = Field(
        default=0,
        description="Number of artifact files rejected by egress policy",
    )


def _set_sandbox_span_attributes(result: SandboxResult) -> None:
    """Set MLflow span attributes for sandbox execution (exit_code, policy, duration, etc.)."""
    span = get_active_span()
    if span is None or not hasattr(span, "set_attribute"):
        return
    try:
        span.set_attribute("exit_code", result.exit_code)
        span.set_attribute("sandbox.policy", result.policy_name)
        span.set_attribute("sandbox.duration_s", result.duration_seconds)
        span.set_attribute("sandbox.timed_out", result.timed_out)
        span.set_attribute("sandbox.artifact_count", len(result.artifacts))
        span.set_attribute("sandbox.artifacts_rejected", result.artifacts_rejected)
        if len(result.stdout) > _STDOUT_ATTR_MAX:
            span.set_attribute("stdout_preview", result.stdout[:_STDOUT_ATTR_MAX] + "...")
        else:
            span.set_attribute("stdout_preview", result.stdout)
        if len(result.stderr) > _STDERR_ATTR_MAX:
            span.set_attribute("stderr_preview", result.stderr[:_STDERR_ATTR_MAX] + "...")
        else:
            span.set_attribute("stderr_preview", result.stderr)
    except Exception as e:
        logger.debug("Failed to set sandbox span attributes: %s", e)


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
        self._build_attempted: bool = False  # Only attempt auto-build once per process

    @trace_with_uri(name="sandbox.execute", span_type="TOOL")
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

        started_at = datetime.now(UTC)
        start_time = asyncio.get_event_loop().time()

        # Determine if artifact output is active (defense-in-depth gate)
        artifacts_active = resolve_artifacts_enabled(
            global_enabled=settings.sandbox_artifacts_enabled,
            policy_enabled=policy.artifacts_enabled,
        )

        # Always create an output dir so LLM-generated scripts that write to
        # /workspace/output don't crash on the read-only root filesystem.
        # Artifacts are only collected when both gates are True.
        output_dir = Path(tempfile.mkdtemp(prefix="aether-artifacts-"))

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
                output_dir=output_dir,
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
                except TimeoutError:
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
                r = SandboxResult(
                    success=False,
                    exit_code=-1,
                    stderr=f"Podman not found at '{self.podman_path}'. "
                    "Install Podman or disable sandbox.",
                    duration_seconds=0,
                    policy_name=policy.name,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
                _set_sandbox_span_attributes(r)
                return r

            except Exception as e:
                r = SandboxResult(
                    success=False,
                    exit_code=-1,
                    stderr=f"Sandbox error: {e!s}",
                    duration_seconds=asyncio.get_event_loop().time() - start_time,
                    policy_name=policy.name,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
                _set_sandbox_span_attributes(r)
                return r

            duration = asyncio.get_event_loop().time() - start_time
            completed_at = datetime.now(UTC)

            # Collect and validate artifacts from the output directory
            artifacts_list: list[Any] = []
            artifacts_rejected = 0
            if artifacts_active and output_dir.exists():
                from src.sandbox.artifact_validator import validate_artifacts

                artifacts_list, artifacts_rejected = validate_artifacts(output_dir)

            result = SandboxResult(
                success=exit_code == 0 and not timed_out,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                timed_out=timed_out,
                policy_name=policy.name,
                started_at=started_at,
                completed_at=completed_at,
                artifacts=artifacts_list,
                artifacts_rejected=artifacts_rejected,
            )
            _set_sandbox_span_attributes(result)
            return result

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

        except Exception as e:
            logger.warning("Failed to check gVisor availability: %s", e)
            self._gvisor_available = False

        return self._gvisor_available

    async def _build_command(
        self,
        script_path: Path,
        policy: SandboxPolicy,
        data_path: Path | None,
        environment: dict[str, str] | None,
        output_dir: Path | None = None,
    ) -> list[str]:
        """Build the Podman command.

        Args:
            script_path: Path to the script file
            policy: Security policy
            data_path: Optional data mount path
            environment: Optional environment variables
            output_dir: Optional writable output directory for artifacts

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
            policy = policy.model_copy(
                update={
                    "use_gvisor": False,
                    "seccomp_profile": None,  # Disable seccomp on non-gVisor systems
                }
            )

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
        # DS Team system prompt which tells the LLM to read from there.
        if data_path and data_path.exists():
            cmd.extend(
                [
                    "--volume",
                    f"{data_path}:/workspace/data.json:ro",
                ]
            )

        # Mount writable output directory for artifacts (charts, CSVs).
        # Only mounted when both global and per-policy gates are True.
        # Constitution: Isolation — this is the only writable mount.
        if output_dir is not None:
            cmd.extend(
                [
                    "--volume",
                    f"{output_dir}:/workspace/output:rw",
                ]
            )
            cmd.extend(["--env", "OUTDIR=/workspace/output"])

        # Suppress Python deprecation warnings so they don't pollute stdout.
        # The DS Team agent parses JSON from stdout; stray warnings
        # (e.g. pandas pyarrow DeprecationWarning) break extraction.
        cmd.extend(["--env", "PYTHONWARNINGS=ignore::DeprecationWarning"])
        cmd.extend(["--env", "MPLCONFIGDIR=/tmp"])

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

    # Timeout for podman subprocess checks (image exists, build, etc.)
    _PODMAN_CHECK_TIMEOUT = 10  # seconds
    _PODMAN_BUILD_TIMEOUT = 300  # 5 minutes for image build

    async def _image_exists(self, image: str) -> bool:
        """Check if a container image exists, with timeout."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.podman_path,
                "image",
                "exists",
                image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=self._PODMAN_CHECK_TIMEOUT)
            return process.returncode == 0
        except TimeoutError:
            logger.warning(
                "Timed out checking image '%s' (podman machine may not be running)",
                image,
            )
            return False
        except Exception:
            return False

    async def _auto_build_image(self) -> bool:
        """Attempt to auto-build the sandbox image from the Containerfile.

        Returns True on success, False on failure.
        """
        # Resolve project root from this file's location
        project_root = Path(__file__).resolve().parent.parent.parent
        containerfile = project_root / "infrastructure" / "podman" / "Containerfile.sandbox"

        if not containerfile.exists():
            logger.warning("Containerfile not found at %s, cannot auto-build", containerfile)
            return False

        try:
            process = await asyncio.create_subprocess_exec(
                self.podman_path,
                "build",
                "-t",
                self.image,
                "-f",
                str(containerfile),
                str(project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=self._PODMAN_BUILD_TIMEOUT)
            return process.returncode == 0
        except TimeoutError:
            logger.warning("Sandbox image build timed out after %ds", self._PODMAN_BUILD_TIMEOUT)
            return False
        except Exception as exc:
            logger.warning("Sandbox image auto-build failed: %s", exc)
            return False

    async def _get_available_image(self) -> str:
        """Get an available container image, auto-building if needed.

        Returns:
            Available container image name
        """
        # Check if preferred image already exists
        if await self._image_exists(self.image):
            return self.image

        # Attempt auto-build (once per process lifetime)
        if not self._build_attempted:
            self._build_attempted = True
            logger.info(
                "Sandbox image '%s' not found. Building automatically "
                "(first run only, this may take 2-3 minutes)...",
                self.image,
            )
            if await self._auto_build_image():
                logger.info("Sandbox image '%s' built successfully.", self.image)
                return self.image
            logger.warning("Auto-build of sandbox image failed.")

        # Fall back to basic Python image
        logger.warning(
            "Container image '%s' not found — falling back to '%s'. "
            "The fallback image lacks data-science packages (numpy, pandas, scipy, etc.) "
            "and analysis scripts WILL fail. Build manually with:\n"
            "  make build-sandbox",
            self.image,
            self.FALLBACK_IMAGE,
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

        started_at = datetime.now(UTC)
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
            except TimeoutError:
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = b"Execution timed out"
                timed_out = True

            duration = asyncio.get_event_loop().time() - start_time

            result = SandboxResult(
                success=process.returncode == 0 and not timed_out,
                exit_code=process.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                duration_seconds=duration,
                timed_out=timed_out,
                policy_name=f"{policy.name}:unsandboxed",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            _set_sandbox_span_attributes(result)
            return result

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


def resolve_artifacts_enabled(
    *,
    global_enabled: bool,
    policy_enabled: bool,
) -> bool:
    """Determine if artifact output is effective for this execution.

    Both the global setting (``sandbox_artifacts_enabled``) and the
    per-policy flag (``policy.artifacts_enabled``) must be ``True``
    for artifact output to be active.  This is a defense-in-depth
    gate: the global switch is the master kill switch.

    Args:
        global_enabled: Value of ``settings.sandbox_artifacts_enabled``.
        policy_enabled: Value of ``policy.artifacts_enabled``.

    Returns:
        ``True`` only when both gates are ``True``.
    """
    return global_enabled and policy_enabled


__all__ = [
    "SandboxResult",
    "SandboxRunner",
    "resolve_artifacts_enabled",
    "run_script",
]
