"""Unit tests for artifact security gates and egress validation.

Tests T3301-T3310: sandbox_artifacts_enabled setting, per-policy
artifacts_enabled flag, gate logic, and the artifact egress validator.

All filesystem operations use tmp_path fixtures — no real sandbox involved.
"""

from pathlib import Path

from src.sandbox.policies import SandboxPolicy, get_default_policy

# =============================================================================
# T3301: sandbox_artifacts_enabled setting
# =============================================================================


class TestArtifactsEnabledSetting:
    """Test the global sandbox_artifacts_enabled setting."""

    def test_default_is_false(self):
        """sandbox_artifacts_enabled defaults to False (defense-in-depth)."""
        from src.settings import Settings

        settings = Settings(
            environment="testing",
            ha_token="test",  # type: ignore[arg-type]
        )
        assert settings.sandbox_artifacts_enabled is False

    def test_can_enable(self):
        """sandbox_artifacts_enabled can be set to True."""
        from src.settings import Settings

        settings = Settings(
            environment="testing",
            ha_token="test",  # type: ignore[arg-type]
            sandbox_artifacts_enabled=True,
        )
        assert settings.sandbox_artifacts_enabled is True


# =============================================================================
# T3302: artifacts_enabled on SandboxPolicy
# =============================================================================


class TestPolicyArtifactsEnabled:
    """Test per-policy artifacts_enabled flag."""

    def test_default_is_false(self):
        """SandboxPolicy.artifacts_enabled defaults to False."""
        policy = get_default_policy()
        assert policy.artifacts_enabled is False

    def test_can_enable(self):
        """artifacts_enabled can be set to True on a policy."""
        policy = SandboxPolicy(
            name="test",
            level="standard",
            artifacts_enabled=True,
        )
        assert policy.artifacts_enabled is True

    def test_predefined_policies_default_false(self):
        """All predefined policies have artifacts_enabled=False."""
        from src.sandbox.policies import get_policy

        for name in ("minimal", "analysis", "standard", "extended"):
            policy = get_policy(name)
            assert policy.artifacts_enabled is False, f"Policy '{name}' should default to False"


# =============================================================================
# T3303: Gate logic — effective = global AND per-policy
# =============================================================================


class TestArtifactGateLogic:
    """Test that artifact output requires BOTH global AND per-policy gates."""

    def test_both_false_means_disabled(self):
        """When both gates are False, artifacts are disabled."""
        from src.sandbox.runner import resolve_artifacts_enabled

        assert resolve_artifacts_enabled(global_enabled=False, policy_enabled=False) is False

    def test_global_true_policy_false_means_disabled(self):
        """When global is True but policy is False, artifacts are disabled."""
        from src.sandbox.runner import resolve_artifacts_enabled

        assert resolve_artifacts_enabled(global_enabled=True, policy_enabled=False) is False

    def test_global_false_policy_true_means_disabled(self):
        """When global is False but policy is True, artifacts are disabled (global wins)."""
        from src.sandbox.runner import resolve_artifacts_enabled

        assert resolve_artifacts_enabled(global_enabled=False, policy_enabled=True) is False

    def test_both_true_means_enabled(self):
        """When both gates are True, artifacts are enabled."""
        from src.sandbox.runner import resolve_artifacts_enabled

        assert resolve_artifacts_enabled(global_enabled=True, policy_enabled=True) is True


# =============================================================================
# T3304: ArtifactEgressPolicy model
# =============================================================================


class TestArtifactEgressPolicy:
    """Test the ArtifactEgressPolicy configuration model."""

    def test_default_allowed_extensions(self):
        """Default extensions include common chart/data formats."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy

        policy = ArtifactEgressPolicy()
        assert ".png" in policy.allowed_extensions
        assert ".svg" in policy.allowed_extensions
        assert ".csv" in policy.allowed_extensions
        assert ".json" in policy.allowed_extensions
        assert ".jpg" in policy.allowed_extensions
        assert ".jpeg" in policy.allowed_extensions

    def test_rejects_dangerous_extensions(self):
        """Default extensions do NOT include executable types."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy

        policy = ArtifactEgressPolicy()
        assert ".py" not in policy.allowed_extensions
        assert ".sh" not in policy.allowed_extensions
        assert ".exe" not in policy.allowed_extensions
        assert ".so" not in policy.allowed_extensions

    def test_default_size_limits(self):
        """Default size limits are reasonable."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy

        policy = ArtifactEgressPolicy()
        assert policy.max_file_size_bytes == 10 * 1024 * 1024  # 10MB
        assert policy.max_total_size_bytes == 50 * 1024 * 1024  # 50MB
        assert policy.max_file_count == 20


# =============================================================================
# T3305: Extension allowlist validation
# =============================================================================


class TestExtensionValidation:
    """Test artifact extension checking."""

    def test_allowed_extension_passes(self, tmp_path: Path):
        """Files with allowed extensions pass validation."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_extension

        policy = ArtifactEgressPolicy()
        assert validate_extension("chart.png", policy) is True
        assert validate_extension("data.csv", policy) is True
        assert validate_extension("results.json", policy) is True

    def test_disallowed_extension_rejected(self):
        """Files with disallowed extensions are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_extension

        policy = ArtifactEgressPolicy()
        assert validate_extension("script.py", policy) is False
        assert validate_extension("malware.exe", policy) is False
        assert validate_extension("payload.sh", policy) is False

    def test_no_extension_rejected(self):
        """Files with no extension are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_extension

        policy = ArtifactEgressPolicy()
        assert validate_extension("Makefile", policy) is False

    def test_double_extension_uses_last(self):
        """Double extensions use the final extension."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_extension

        policy = ArtifactEgressPolicy()
        assert validate_extension("chart.backup.png", policy) is True
        assert validate_extension("chart.png.sh", policy) is False


# =============================================================================
# T3306: Magic-byte verification
# =============================================================================


class TestMagicByteValidation:
    """Test that file content matches claimed extension."""

    def test_valid_png(self, tmp_path: Path):
        """A real PNG header passes validation."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "chart.png"
        # PNG magic bytes: \x89PNG\r\n\x1a\n
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert validate_magic_bytes(f, ".png", policy) is True

    def test_fake_png_rejected(self, tmp_path: Path):
        """A file claiming to be PNG but with wrong header is rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "fake.png"
        f.write_bytes(b"#!/bin/bash\nrm -rf /\n")
        assert validate_magic_bytes(f, ".png", policy) is False

    def test_valid_jpg(self, tmp_path: Path):
        """A real JPEG header passes validation."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
        assert validate_magic_bytes(f, ".jpg", policy) is True

    def test_valid_svg(self, tmp_path: Path):
        """SVG content (XML with <svg) passes validation."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "chart.svg"
        f.write_bytes(b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>')
        assert validate_magic_bytes(f, ".svg", policy) is True

    def test_valid_csv(self, tmp_path: Path):
        """CSV files pass (text-based, no specific magic bytes enforced)."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "data.csv"
        f.write_bytes(b"col1,col2,col3\n1,2,3\n")
        assert validate_magic_bytes(f, ".csv", policy) is True

    def test_valid_json(self, tmp_path: Path):
        """JSON files pass (text-based, checked for valid start chars)."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "results.json"
        f.write_bytes(b'{"key": "value"}')
        assert validate_magic_bytes(f, ".json", policy) is True

    def test_empty_file_rejected(self, tmp_path: Path):
        """Empty files are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_magic_bytes

        policy = ArtifactEgressPolicy()
        f = tmp_path / "empty.png"
        f.write_bytes(b"")
        assert validate_magic_bytes(f, ".png", policy) is False


# =============================================================================
# T3307: Size limits
# =============================================================================


class TestSizeLimits:
    """Test per-file and total size limit enforcement."""

    def test_file_within_limit(self, tmp_path: Path):
        """A file within size limit passes."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_file_size

        policy = ArtifactEgressPolicy(max_file_size_bytes=1024)
        f = tmp_path / "small.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert validate_file_size(f, policy) is True

    def test_file_exceeds_limit(self, tmp_path: Path):
        """A file exceeding size limit is rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_file_size

        policy = ArtifactEgressPolicy(max_file_size_bytes=1024)
        f = tmp_path / "large.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000)
        assert validate_file_size(f, policy) is False


# =============================================================================
# T3308: Symlink rejection
# =============================================================================


class TestSymlinkRejection:
    """Test that symlinks are rejected."""

    def test_regular_file_passes(self, tmp_path: Path):
        """A regular file is not a symlink."""
        from src.sandbox.artifact_validator import validate_not_symlink

        f = tmp_path / "chart.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert validate_not_symlink(f) is True

    def test_symlink_rejected(self, tmp_path: Path):
        """A symlink is rejected."""
        from src.sandbox.artifact_validator import validate_not_symlink

        target = tmp_path / "target.txt"
        target.write_text("secret")
        link = tmp_path / "link.png"
        link.symlink_to(target)
        assert validate_not_symlink(link) is False


# =============================================================================
# T3309: Filename sanitization
# =============================================================================


class TestFilenameSanitization:
    """Test filename safety checks."""

    def test_valid_filename_passes(self):
        """Normal filenames pass."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy()
        assert validate_filename("chart.png", policy) is True
        assert validate_filename("energy_analysis_2024.csv", policy) is True
        assert validate_filename("results-v2.json", policy) is True

    def test_path_traversal_rejected(self):
        """Filenames with path traversal are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy()
        assert validate_filename("../../../etc/passwd", policy) is False
        assert validate_filename("..\\windows\\system32", policy) is False

    def test_dotfile_rejected(self):
        """Hidden/dotfiles are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy()
        assert validate_filename(".hidden.png", policy) is False
        assert validate_filename(".env", policy) is False

    def test_null_byte_rejected(self):
        """Filenames with null bytes are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy()
        assert validate_filename("chart\x00.png", policy) is False

    def test_too_long_rejected(self):
        """Filenames exceeding max length are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy(max_filename_length=20)
        assert validate_filename("a" * 21 + ".png", policy) is False

    def test_slash_in_name_rejected(self):
        """Filenames containing slashes are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_filename

        policy = ArtifactEgressPolicy()
        assert validate_filename("sub/chart.png", policy) is False


# =============================================================================
# T3310: validate_artifacts orchestrator
# =============================================================================


class TestValidateArtifacts:
    """Test the top-level validate_artifacts() function."""

    def test_empty_directory(self, tmp_path: Path):
        """An empty output directory returns no artifacts."""
        from src.sandbox.artifact_validator import validate_artifacts

        accepted, rejected = validate_artifacts(tmp_path)
        assert accepted == []
        assert rejected == 0

    def test_valid_artifacts_accepted(self, tmp_path: Path):
        """Valid artifacts pass all checks."""
        from src.sandbox.artifact_validator import validate_artifacts

        # Create a valid PNG
        png = tmp_path / "chart.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Create a valid CSV
        csv = tmp_path / "data.csv"
        csv.write_text("col1,col2\n1,2\n")

        accepted, rejected = validate_artifacts(tmp_path)
        assert len(accepted) == 2
        assert rejected == 0
        filenames = {a.filename for a in accepted}
        assert filenames == {"chart.png", "data.csv"}

    def test_mixed_valid_and_invalid(self, tmp_path: Path):
        """Valid artifacts are accepted, invalid ones rejected."""
        from src.sandbox.artifact_validator import validate_artifacts

        # Valid PNG
        png = tmp_path / "chart.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Invalid: Python script
        py = tmp_path / "script.py"
        py.write_text("import os; os.system('rm -rf /')")

        # Invalid: fake PNG
        fake = tmp_path / "fake.png"
        fake.write_bytes(b"#!/bin/bash\nrm -rf /\n")

        accepted, rejected = validate_artifacts(tmp_path)
        assert len(accepted) == 1
        assert accepted[0].filename == "chart.png"
        assert rejected == 2

    def test_symlink_rejected(self, tmp_path: Path):
        """Symlinks in output directory are rejected."""
        from src.sandbox.artifact_validator import validate_artifacts

        # Put the target outside the output dir so it doesn't get scanned
        target = tmp_path.parent / "secret_target.txt"
        target.write_text("secret data")
        link = tmp_path / "link.png"
        link.symlink_to(target)

        accepted, rejected = validate_artifacts(tmp_path)
        assert len(accepted) == 0
        assert rejected == 1

    def test_exceeds_total_size_limit(self, tmp_path: Path):
        """Once total size limit is hit, remaining files are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_artifacts

        # Each file ~1100 bytes, total limit 1500 -> first fits, second exceeds
        policy = ArtifactEgressPolicy(max_total_size_bytes=1500)

        for name in ("a.png", "b.png"):
            f = tmp_path / name
            f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1100)

        accepted, rejected = validate_artifacts(tmp_path, policy)
        assert len(accepted) == 1  # First fits, second exceeds total
        assert rejected == 1

    def test_exceeds_file_count_limit(self, tmp_path: Path):
        """Once file count limit is hit, remaining files are rejected."""
        from src.sandbox.artifact_validator import ArtifactEgressPolicy, validate_artifacts

        policy = ArtifactEgressPolicy(max_file_count=2)

        for i in range(3):
            f = tmp_path / f"chart{i}.csv"
            f.write_text(f"col1\n{i}\n")

        accepted, rejected = validate_artifacts(tmp_path, policy)
        assert len(accepted) == 2
        assert rejected == 1

    def test_subdirectories_ignored(self, tmp_path: Path):
        """Subdirectories in output dir are not traversed."""
        from src.sandbox.artifact_validator import validate_artifacts

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sneaky.py").write_text("import os")

        # Valid file at top level
        f = tmp_path / "chart.csv"
        f.write_text("col1\n1\n")

        accepted, _rejected = validate_artifacts(tmp_path)
        assert len(accepted) == 1
        assert accepted[0].filename == "chart.csv"

    def test_nonexistent_directory(self, tmp_path: Path):
        """A nonexistent directory returns empty results."""
        from src.sandbox.artifact_validator import validate_artifacts

        accepted, rejected = validate_artifacts(tmp_path / "nope")
        assert accepted == []
        assert rejected == 0
