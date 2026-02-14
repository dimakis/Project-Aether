"""Unit tests for sandbox artifact mount and collection (T3311-T3315).

Tests SandboxResult artifact fields, output directory mounting,
and post-execution artifact collection.  All process execution is mocked.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sandbox.artifact_validator import ArtifactMeta
from src.sandbox.runner import SandboxResult, SandboxRunner


@pytest.fixture(autouse=True)
def _skip_sandbox_auto_build():
    """Prevent sandbox tests from triggering real podman auto-build."""
    with patch.object(
        SandboxRunner,
        "_get_available_image",
        new_callable=AsyncMock,
        return_value=SandboxRunner.FALLBACK_IMAGE,
    ):
        yield


# =============================================================================
# T3311: ArtifactMeta on SandboxResult
# =============================================================================


class TestSandboxResultArtifactFields:
    """Test that SandboxResult includes artifact metadata fields."""

    def test_artifacts_default_empty(self):
        """SandboxResult.artifacts defaults to an empty list."""
        r = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=1.0,
            policy_name="standard",
        )
        assert r.artifacts == []

    def test_artifacts_rejected_default_zero(self):
        """SandboxResult.artifacts_rejected defaults to 0."""
        r = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=1.0,
            policy_name="standard",
        )
        assert r.artifacts_rejected == 0

    def test_can_set_artifacts(self):
        """SandboxResult accepts ArtifactMeta items."""
        artifact = ArtifactMeta(
            filename="chart.png",
            content_type="image/png",
            size_bytes=1024,
            path=Path("/tmp/output/chart.png"),
        )
        r = SandboxResult(
            success=True,
            exit_code=0,
            duration_seconds=1.0,
            policy_name="standard",
            artifacts=[artifact],
            artifacts_rejected=2,
        )
        assert len(r.artifacts) == 1
        assert r.artifacts[0].filename == "chart.png"
        assert r.artifacts_rejected == 2


# =============================================================================
# T3313: Output dir mounted when artifacts enabled
# =============================================================================


class TestBuildCommandArtifacts:
    """Test that _build_command mounts /workspace/output when artifacts enabled."""

    async def test_no_output_mount_when_artifacts_disabled(self):
        """When artifacts are disabled, no /workspace/output mount appears."""
        runner = SandboxRunner()

        mock_settings = MagicMock()
        mock_settings.sandbox_artifacts_enabled = False

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=False)

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner, "_is_gvisor_available", new_callable=AsyncMock, return_value=False
            ),
        ):
            cmd = await runner._build_command(
                script_path=Path("/tmp/script.py"),
                policy=policy,
                data_path=None,
                environment=None,
            )

        # No /workspace/output mount should appear
        cmd_str = " ".join(cmd)
        assert "/workspace/output" not in cmd_str

    async def test_output_mount_when_both_gates_true(self, tmp_path: Path):
        """When both gates are True, /workspace/output is mounted rw."""
        runner = SandboxRunner()

        mock_settings = MagicMock()
        mock_settings.sandbox_artifacts_enabled = True

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner, "_is_gvisor_available", new_callable=AsyncMock, return_value=False
            ),
        ):
            cmd = await runner._build_command(
                script_path=Path("/tmp/script.py"),
                policy=policy,
                data_path=None,
                environment=None,
                output_dir=output_dir,
            )

        # Should have a --volume with /workspace/output:rw
        cmd_str = " ".join(cmd)
        assert "/workspace/output" in cmd_str

        # Find the volume arg
        for _i, arg in enumerate(cmd):
            if "/workspace/output" in arg:
                assert ":rw" in arg or arg.endswith(":rw"), f"Mount should be rw: {arg}"
                break

    async def test_global_false_policy_true_no_mount(self):
        """Global gate overrides: no mount even if policy says True."""
        runner = SandboxRunner()

        mock_settings = MagicMock()
        mock_settings.sandbox_artifacts_enabled = False

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=True)

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner, "_is_gvisor_available", new_callable=AsyncMock, return_value=False
            ),
        ):
            cmd = await runner._build_command(
                script_path=Path("/tmp/script.py"),
                policy=policy,
                data_path=None,
                environment=None,
            )

        cmd_str = " ".join(cmd)
        assert "/workspace/output" not in cmd_str


# =============================================================================
# T3314: Artifact collection after execution
# =============================================================================


class TestRunArtifactCollection:
    """Test that run() collects artifacts from the output directory."""

    async def test_artifacts_collected_on_success(self, tmp_path: Path):
        """When artifacts enabled + script succeeds, artifacts are validated and collected."""
        runner = SandboxRunner()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a valid PNG in the output dir
        (output_dir / "chart.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = True
        mock_settings.sandbox_artifacts_enabled = True

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=True)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b'{"insights": []}', b""))
        mock_proc.returncode = 0

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner,
                "_build_command",
                new_callable=AsyncMock,
                return_value=["podman", "run", "test"],
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("tempfile.mkdtemp", return_value=str(output_dir)),
        ):
            result = await runner.run("print('hello')", policy=policy)

        assert result.success is True
        assert len(result.artifacts) == 1
        assert result.artifacts[0].filename == "chart.png"
        assert result.artifacts_rejected == 0

    async def test_no_artifacts_when_disabled(self):
        """When artifacts disabled, result has empty artifacts."""
        runner = SandboxRunner()

        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = True
        mock_settings.sandbox_artifacts_enabled = False

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=False)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner,
                "_build_command",
                new_callable=AsyncMock,
                return_value=["podman", "run", "test"],
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await runner.run("print('hello')", policy=policy)

        assert result.artifacts == []
        assert result.artifacts_rejected == 0

    async def test_invalid_artifacts_rejected(self, tmp_path: Path):
        """Invalid artifacts are counted in artifacts_rejected."""
        runner = SandboxRunner()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create an invalid file (Python script pretending to be PNG)
        (output_dir / "evil.py").write_text("import os")

        mock_settings = MagicMock()
        mock_settings.sandbox_enabled = True
        mock_settings.sandbox_artifacts_enabled = True

        from src.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy(name="test", level="standard", artifacts_enabled=True)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        with (
            patch("src.sandbox.runner.get_settings", return_value=mock_settings),
            patch.object(
                runner,
                "_build_command",
                new_callable=AsyncMock,
                return_value=["podman", "run", "test"],
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("tempfile.mkdtemp", return_value=str(output_dir)),
        ):
            result = await runner.run("print('hello')", policy=policy)

        assert result.artifacts == []
        assert result.artifacts_rejected == 1
