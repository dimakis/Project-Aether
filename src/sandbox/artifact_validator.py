"""Artifact egress validation for sandbox output.

Validates artifacts produced by sandboxed scripts before they leave
the sandbox boundary.  Enforces extension allowlists, magic-byte
verification, size limits, symlink rejection, and filename sanitization.

Constitution: Isolation + Security — defense-in-depth for artifact egress.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# MAGIC BYTE SIGNATURES
# =============================================================================

# Maps extensions to valid file header byte sequences.
# A file must start with at least one of these to pass validation.
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    # SVG and text formats are validated differently (see validate_magic_bytes)
}

# Text-based formats: validated by content pattern, not raw bytes.
_TEXT_FORMATS: frozenset[str] = frozenset({".svg", ".csv", ".json"})


# =============================================================================
# ARTIFACT METADATA
# =============================================================================


class ArtifactMeta(BaseModel):
    """Metadata for a validated artifact."""

    filename: str
    content_type: str  # e.g. image/png, text/csv
    size_bytes: int
    path: Path  # temp path (before persistence)


# =============================================================================
# EGRESS POLICY
# =============================================================================


class ArtifactEgressPolicy(BaseModel):
    """Security policy for artifacts leaving the sandbox.

    All fields have safe defaults.  Customise per-execution if needed.
    """

    # Extension allowlist — reject everything else
    allowed_extensions: frozenset[str] = Field(
        default=frozenset({".png", ".jpg", ".jpeg", ".svg", ".csv", ".json"}),
        description="File extensions permitted to leave the sandbox.",
    )

    # Size limits
    max_file_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        description="Maximum size per artifact file (bytes).",
    )
    max_total_size_bytes: int = Field(
        default=50 * 1024 * 1024,
        ge=1024,
        description="Maximum total size of all artifacts per execution (bytes).",
    )
    max_file_count: int = Field(
        default=20,
        ge=1,
        description="Maximum number of artifact files per execution.",
    )

    # Path safety
    max_filename_length: int = Field(
        default=255,
        ge=1,
        description="Maximum filename length.",
    )
    allowed_filename_pattern: str = Field(
        default=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$",
        description="Regex pattern filenames must match.",
    )


# =============================================================================
# CONTENT-TYPE MAPPING
# =============================================================================

_CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".csv": "text/csv",
    ".json": "application/json",
}


# =============================================================================
# INDIVIDUAL VALIDATORS
# =============================================================================


def validate_filename(filename: str, policy: ArtifactEgressPolicy) -> bool:
    """Validate a filename for safety.

    Rejects: path traversal, null bytes, dotfiles, slashes,
    names not matching the allowed pattern, and names exceeding max length.
    """
    # Null bytes
    if "\x00" in filename:
        logger.warning("Artifact rejected (null byte): %r", filename)
        return False

    # Path separators
    if "/" in filename or "\\" in filename:
        logger.warning("Artifact rejected (path separator): %r", filename)
        return False

    # Path traversal
    if ".." in filename:
        logger.warning("Artifact rejected (path traversal): %r", filename)
        return False

    # Dotfiles
    if filename.startswith("."):
        logger.warning("Artifact rejected (dotfile): %r", filename)
        return False

    # Length
    if len(filename) > policy.max_filename_length:
        logger.warning("Artifact rejected (too long: %d): %r", len(filename), filename)
        return False

    # Pattern match
    if not re.match(policy.allowed_filename_pattern, filename):
        logger.warning("Artifact rejected (pattern mismatch): %r", filename)
        return False

    return True


def validate_extension(filename: str, policy: ArtifactEgressPolicy) -> bool:
    """Check that the file extension is in the allowlist."""
    ext = Path(filename).suffix.lower()
    if not ext:
        logger.warning("Artifact rejected (no extension): %r", filename)
        return False
    if ext not in policy.allowed_extensions:
        logger.warning("Artifact rejected (extension %s): %r", ext, filename)
        return False
    return True


def validate_not_symlink(path: Path) -> bool:
    """Reject symlinks (prevent sandbox escape)."""
    if path.is_symlink():
        logger.warning("Artifact rejected (symlink): %s", path.name)
        return False
    return True


def validate_file_size(path: Path, policy: ArtifactEgressPolicy) -> bool:
    """Check that a file does not exceed the per-file size limit."""
    size = path.stat().st_size
    if size > policy.max_file_size_bytes:
        logger.warning(
            "Artifact rejected (size %d > %d): %s",
            size,
            policy.max_file_size_bytes,
            path.name,
        )
        return False
    return True


def validate_magic_bytes(
    path: Path,
    extension: str,
    policy: ArtifactEgressPolicy,
) -> bool:
    """Verify that file content matches the claimed extension.

    Binary formats (PNG, JPEG) must have correct magic bytes.
    Text formats (SVG, CSV, JSON) are checked for plausible content.
    Empty files are always rejected.
    """
    try:
        data = path.read_bytes()
    except OSError:
        logger.warning("Artifact rejected (unreadable): %s", path.name)
        return False

    if len(data) == 0:
        logger.warning("Artifact rejected (empty): %s", path.name)
        return False

    ext = extension.lower()

    # Binary formats: check magic bytes
    if ext in _MAGIC_SIGNATURES:
        for sig in _MAGIC_SIGNATURES[ext]:
            if data.startswith(sig):
                return True
        logger.warning("Artifact rejected (magic bytes mismatch for %s): %s", ext, path.name)
        return False

    # SVG: must contain <svg (case-insensitive)
    if ext == ".svg":
        text = data.decode("utf-8", errors="replace").lower()
        if "<svg" in text:
            return True
        logger.warning("Artifact rejected (not valid SVG): %s", path.name)
        return False

    # CSV: text-based, allow any non-empty content
    if ext == ".csv":
        return True

    # JSON: must start with { or [ (after whitespace)
    if ext == ".json":
        text = data.decode("utf-8", errors="replace").lstrip()
        if text and text[0] in ("{", "["):
            return True
        logger.warning("Artifact rejected (not valid JSON): %s", path.name)
        return False

    # Unknown text format — reject by default
    logger.warning("Artifact rejected (unknown text format %s): %s", ext, path.name)
    return False


# =============================================================================
# ORCHESTRATOR
# =============================================================================


def validate_artifacts(
    output_dir: Path,
    policy: ArtifactEgressPolicy | None = None,
) -> tuple[list[ArtifactMeta], int]:
    """Validate all artifacts in a sandbox output directory.

    Applies all security checks in sequence.  Returns accepted artifacts
    and a count of rejected files.

    Args:
        output_dir: Path to the sandbox output directory.
        policy: Egress policy (uses defaults if None).

    Returns:
        Tuple of (accepted_artifacts, rejected_count).
    """
    if policy is None:
        policy = ArtifactEgressPolicy()

    if not output_dir.exists() or not output_dir.is_dir():
        return [], 0

    accepted: list[ArtifactMeta] = []
    rejected = 0
    total_bytes = 0

    # Enumerate only top-level files (no recursion)
    for entry in sorted(output_dir.iterdir()):
        # Skip subdirectories
        if entry.is_dir():
            continue

        filename = entry.name

        # --- Validation pipeline ---

        # 1. Filename sanitization
        if not validate_filename(filename, policy):
            rejected += 1
            continue

        # 2. Extension allowlist
        if not validate_extension(filename, policy):
            rejected += 1
            continue

        # 3. Symlink check
        if not validate_not_symlink(entry):
            rejected += 1
            continue

        # 4. File count limit
        if len(accepted) >= policy.max_file_count:
            logger.warning(
                "Artifact rejected (count limit %d): %s", policy.max_file_count, filename
            )
            rejected += 1
            continue

        # 5. Per-file size check
        if not validate_file_size(entry, policy):
            rejected += 1
            continue

        # 6. Total size check
        file_size = entry.stat().st_size
        if total_bytes + file_size > policy.max_total_size_bytes:
            logger.warning(
                "Artifact rejected (total size would exceed %d): %s",
                policy.max_total_size_bytes,
                filename,
            )
            rejected += 1
            continue

        # 7. Magic-byte / content verification
        ext = Path(filename).suffix.lower()
        if not validate_magic_bytes(entry, ext, policy):
            rejected += 1
            continue

        # --- All checks passed ---
        content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
        total_bytes += file_size
        accepted.append(
            ArtifactMeta(
                filename=filename,
                content_type=content_type,
                size_bytes=file_size,
                path=entry,
            )
        )

    if rejected > 0:
        logger.info(
            "Artifact validation: %d accepted, %d rejected in %s",
            len(accepted),
            rejected,
            output_dir,
        )

    return accepted, rejected


__all__ = [
    "ArtifactEgressPolicy",
    "ArtifactMeta",
    "validate_artifacts",
    "validate_extension",
    "validate_file_size",
    "validate_filename",
    "validate_magic_bytes",
    "validate_not_symlink",
]
