"""Unit tests for src/sandbox/runner.py.

Tests SandboxResult model and SandboxRunner configuration.
All process execution is mocked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sandbox.runner import SandboxResult, SandboxRunner


class TestSandboxResult:
    def test_defaults(self):
        r = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=1.5,
            policy_name="standard",
        )
        assert r.success is True
        assert r.exit_code == 0
        assert r.stdout == ""
        assert r.stderr == ""
        assert r.timed_out is False
        assert r.memory_peak_mb is None

    def test_with_output(self):
        r = SandboxResult(
            success=False,
            exit_code=1,
            stdout="output",
            stderr="error",
            duration_seconds=0.5,
            timed_out=True,
            policy_name="minimal",
        )
        assert r.stdout == "output"
        assert r.stderr == "error"
        assert r.timed_out is True

    def test_id_is_uuid(self):
        r = SandboxResult(success=True, exit_code=0, duration_seconds=0.1, policy_name="test")
        uuid.UUID(r.id)  # Should not raise


class TestSandboxRunnerInit:
    def test_default_image(self):
        runner = SandboxRunner()
        assert runner.image == SandboxRunner.DEFAULT_IMAGE
        assert runner.podman_path == "podman"

    def test_custom_image(self):
        runner = SandboxRunner(image="custom:latest", podman_path="/usr/bin/podman")
        assert runner.image == "custom:latest"
        assert runner.podman_path == "/usr/bin/podman"


class TestSandboxRunnerRun:
    async def test_sandbox_disabled_dev(self):
        runner = SandboxRunner()
        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = False
        mock_settings.environment = "development"

        with patch("src.sandbox.runner.get_settings", return_value=mock_settings):
            with patch.object(
                runner, "_run_unsandboxed", new_callable=AsyncMock
            ) as mock_unsandboxed:
                mock_unsandboxed.return_value = SandboxResult(
                    success=True,
                    exit_code=0,
                    duration_seconds=0.1,
                    policy_name="default",
                )
                result = await runner.run("print('hello')")
                assert result.success is True

    async def test_sandbox_disabled_production_raises(self):
        runner = SandboxRunner()
        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = False
        mock_settings.environment = "production"

        with patch("src.sandbox.runner.get_settings", return_value=mock_settings):
            from src.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError, match="MUST be enabled"):
                await runner.run("print('hello')")

    async def test_podman_not_found(self):
        runner = SandboxRunner()
        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = True

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner, "_build_command", new_callable=AsyncMock, return_value=["podman", "run"]
            ),
            patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()),
        ):
            result = await runner.run("print('hello')")
            assert result.success is False
            assert "Podman not found" in result.stderr


class TestIsGvisorAvailable:
    async def test_cached_result(self):
        runner = SandboxRunner()
        runner._gvisor_available = True
        assert await runner._is_gvisor_available() is True

    async def test_detects_runsc(self):
        runner = SandboxRunner()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"runsc", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await runner._is_gvisor_available()
            assert result is True

    async def test_no_gvisor(self):
        runner = SandboxRunner()

        mock_proc1 = AsyncMock()
        mock_proc1.communicate = AsyncMock(return_value=(b"crun", b""))

        mock_proc2 = AsyncMock()
        mock_proc2.communicate = AsyncMock(return_value=(b"no-gvisor", b""))

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_proc1, mock_proc2],
        ):
            result = await runner._is_gvisor_available()
            assert result is False

    async def test_exception_handling(self):
        runner = SandboxRunner()

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=Exception("not found"),
        ):
            result = await runner._is_gvisor_available()
            assert result is False
