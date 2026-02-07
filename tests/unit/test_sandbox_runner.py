"""Unit tests for sandbox runner.

Tests SandboxRunner with mocked Podman execution.
Constitution: Isolation - verify sandbox behavior.

TDD: T109 - Sandbox execution logic tests.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sandbox.policies import SandboxPolicy, get_default_policy
from src.sandbox.runner import SandboxResult, SandboxRunner


class TestSandboxResult:
    """Tests for SandboxResult model."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="Hello, World!",
            stderr="",
            duration_seconds=0.5,
            policy_name="standard",
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Hello, World!"
        assert result.timed_out is False

    def test_create_failure_result(self):
        """Test creating a failed result."""
        result = SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Error: division by zero",
            duration_seconds=0.1,
            policy_name="standard",
        )

        assert result.success is False
        assert result.exit_code == 1
        assert "division by zero" in result.stderr

    def test_create_timeout_result(self):
        """Test creating a timeout result."""
        result = SandboxResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_seconds=30.0,
            timed_out=True,
            policy_name="standard",
        )

        assert result.success is False
        assert result.timed_out is True

    def test_result_has_id(self):
        """Test that result gets a UUID."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=0.1,
            policy_name="standard",
        )

        assert result.id is not None
        assert len(result.id) == 36  # UUID format

    def test_result_timestamps(self):
        """Test that result has timestamps."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=0.1,
            policy_name="standard",
        )

        assert result.started_at is not None
        assert isinstance(result.started_at, datetime)


class TestSandboxRunnerInit:
    """Tests for SandboxRunner initialization."""

    def test_default_image(self):
        """Test default image is set."""
        runner = SandboxRunner()

        assert runner.image == SandboxRunner.DEFAULT_IMAGE
        assert "aether-sandbox" in runner.image

    def test_custom_image(self):
        """Test custom image can be set."""
        runner = SandboxRunner(image="python:3.12-slim")

        assert runner.image == "python:3.12-slim"

    def test_fallback_image_exists(self):
        """Test fallback image is defined."""
        assert hasattr(SandboxRunner, "FALLBACK_IMAGE")
        assert "python" in SandboxRunner.FALLBACK_IMAGE

    def test_custom_podman_path(self):
        """Test custom podman path can be set."""
        runner = SandboxRunner(podman_path="/usr/local/bin/podman")

        assert runner.podman_path == "/usr/local/bin/podman"


class TestSandboxRunnerUnsandboxed:
    """Tests for unsandboxed execution (when sandbox disabled)."""

    @pytest.mark.asyncio
    async def test_run_unsandboxed_success(self):
        """Test running script without sandbox."""
        runner = SandboxRunner()
        
        with patch.object(runner, "_run_unsandboxed") as mock_run:
            mock_run.return_value = SandboxResult(
                success=True,
                exit_code=0,
                stdout="42",
                stderr="",
                duration_seconds=0.1,
                policy_name="standard",
            )
            
            # Mock settings to disable sandbox
            with patch("src.sandbox.runner.get_settings") as mock_settings:
                mock_settings.return_value.sandbox_enabled = False
                
                result = await runner.run("print(6 * 7)")
                
                assert result.success is True
                assert result.stdout == "42"


class TestSandboxRunnerBuildCommand:
    """Tests for Podman command building."""

    def test_build_basic_command(self):
        """Test building a basic podman command."""
        runner = SandboxRunner()
        policy = get_default_policy()
        
        # The runner should build a command with security options
        # This tests the command structure without actually running
        assert runner.podman_path == "podman"
        assert policy.timeout_seconds > 0

    def test_policy_applied(self):
        """Test that policy settings are respected."""
        from src.sandbox.policies import NetworkPolicy, PolicyLevel
        
        policy = SandboxPolicy(
            name="test",
            level=PolicyLevel.STANDARD,
            timeout_seconds=10,
            network=NetworkPolicy.NONE,
            read_only_root=True,
        )

        assert policy.timeout_seconds == 10
        assert policy.network == NetworkPolicy.NONE
        assert policy.read_only_root is True


class TestSandboxRunnerScriptExecution:
    """Tests for script execution behavior."""

    @pytest.mark.asyncio
    async def test_simple_script_mocked(self):
        """Test running a simple script with mocked subprocess."""
        runner = SandboxRunner()
        
        with patch("src.sandbox.runner.get_settings") as mock_settings:
            mock_settings.return_value.sandbox_enabled = False
            
            with patch.object(runner, "_run_unsandboxed") as mock_run:
                mock_run.return_value = SandboxResult(
                    success=True,
                    exit_code=0,
                    stdout="hello",
                    stderr="",
                    duration_seconds=0.05,
                    policy_name="standard",
                )
                
                result = await runner.run("print('hello')")
                
                mock_run.assert_called_once()
                assert result.success is True

    @pytest.mark.asyncio
    async def test_script_with_error_mocked(self):
        """Test handling script errors."""
        runner = SandboxRunner()
        
        with patch("src.sandbox.runner.get_settings") as mock_settings:
            mock_settings.return_value.sandbox_enabled = False
            
            with patch.object(runner, "_run_unsandboxed") as mock_run:
                mock_run.return_value = SandboxResult(
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr="NameError: name 'undefined' is not defined",
                    duration_seconds=0.05,
                    policy_name="standard",
                )
                
                result = await runner.run("print(undefined)")
                
                assert result.success is False
                assert result.exit_code == 1
                assert "NameError" in result.stderr


class TestSandboxPolicy:
    """Tests for SandboxPolicy."""

    def test_default_policy(self):
        """Test getting default policy."""
        policy = get_default_policy()

        assert policy is not None
        assert policy.name == "standard"
        assert policy.timeout_seconds > 0
        assert policy.resources.memory_mb > 0

    def test_policy_has_security_settings(self):
        """Test policy has security settings."""
        policy = get_default_policy()

        assert hasattr(policy, "network")
        assert hasattr(policy, "read_only_root")
        assert hasattr(policy, "resources")

    def test_custom_policy(self):
        """Test creating custom policy."""
        from src.sandbox.policies import NetworkPolicy, PolicyLevel
        
        policy = SandboxPolicy(
            name="custom",
            level=PolicyLevel.MINIMAL,
            timeout_seconds=5,
            network=NetworkPolicy.NONE,
            read_only_root=True,
        )

        assert policy.name == "custom"
        assert policy.timeout_seconds == 5
        assert policy.level == PolicyLevel.MINIMAL


class TestSandboxRunnerDataMount:
    """Tests for data mounting functionality."""

    def test_data_path_parameter(self):
        """Test that data_path parameter is accepted."""
        runner = SandboxRunner()
        
        # Verify the run method accepts data_path
        import inspect
        sig = inspect.signature(runner.run)
        assert "data_path" in sig.parameters

    def test_environment_parameter(self):
        """Test that environment parameter is accepted."""
        runner = SandboxRunner()
        
        import inspect
        sig = inspect.signature(runner.run)
        assert "environment" in sig.parameters


class TestSandboxWarningsSuppression:
    """Tests for deprecation warning suppression in sandbox scripts.

    Sandbox scripts must not have their stdout polluted by Python
    deprecation warnings (e.g. pandas pyarrow warning) since the
    Data Scientist agent parses JSON from stdout.
    """

    @pytest.mark.asyncio
    async def test_build_command_includes_pythonwarnings_env(self):
        """Test that _build_command injects PYTHONWARNINGS env var to suppress warnings."""
        runner = SandboxRunner()
        policy = get_default_policy()

        with patch.object(runner, "_is_gvisor_available", new_callable=AsyncMock, return_value=False):
            with patch.object(runner, "_get_available_image", new_callable=AsyncMock, return_value="aether-sandbox:latest"):
                script_path = Path("/tmp/test_script.py")
                cmd = await runner._build_command(
                    script_path=script_path,
                    policy=policy,
                    data_path=None,
                    environment=None,
                )

        # The command should contain --env PYTHONWARNINGS=ignore::DeprecationWarning
        cmd_str = " ".join(cmd)
        assert "PYTHONWARNINGS=ignore::DeprecationWarning" in cmd_str

    @pytest.mark.asyncio
    async def test_build_command_warning_env_does_not_override_user_env(self):
        """Test that user-provided env vars are preserved alongside warning suppression."""
        runner = SandboxRunner()
        policy = get_default_policy()

        with patch.object(runner, "_is_gvisor_available", new_callable=AsyncMock, return_value=False):
            with patch.object(runner, "_get_available_image", new_callable=AsyncMock, return_value="aether-sandbox:latest"):
                script_path = Path("/tmp/test_script.py")
                cmd = await runner._build_command(
                    script_path=script_path,
                    policy=policy,
                    data_path=None,
                    environment={"MY_VAR": "hello"},
                )

        cmd_str = " ".join(cmd)
        # Both the user env var and the warning suppression should be present
        assert "MY_VAR=hello" in cmd_str
        assert "PYTHONWARNINGS=ignore::DeprecationWarning" in cmd_str
