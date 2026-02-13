"""Filesystem-based artifact storage for analysis reports.

Persists validated artifacts from sandbox execution to a structured
directory layout: ``{base_dir}/{report_id}/{filename}``.

All filenames are re-validated on persist and retrieve to prevent
path traversal attacks.  Content-type is stored alongside the file
via a sidecar metadata approach (the content_type from ArtifactMeta).

Constitution: Isolation + Security — artifacts are validated before
storage and filenames are sanitized on every access.
"""

from __future__ import annotations

import logging
import mimetypes
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.sandbox.artifact_validator import ArtifactMeta

logger = logging.getLogger(__name__)

# Content-type mapping (extension -> MIME type)
_CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".csv": "text/csv",
    ".json": "application/json",
}


def _is_safe_filename(filename: str) -> bool:
    """Check if a filename is safe for filesystem operations.

    Rejects path traversal, slashes, null bytes, and dotfiles.
    """
    if not filename:
        return False
    if "\x00" in filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if ".." in filename:
        return False
    return not filename.startswith(".")


class ArtifactStore:
    """Filesystem-based artifact storage.

    Stores artifacts in ``{base_dir}/{report_id}/{filename}``.

    Args:
        base_dir: Root directory for artifact storage.
            Defaults to ``data/artifacts`` relative to the working directory.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path("data/artifacts")

    def persist(self, report_id: str, artifact: ArtifactMeta) -> Path:
        """Persist a validated artifact to the store.

        Args:
            report_id: The report this artifact belongs to.
            artifact: Validated artifact metadata (from egress validator).

        Returns:
            Path to the stored artifact.

        Raises:
            ValueError: If the filename is unsafe.
            FileNotFoundError: If the source artifact file doesn't exist.
        """
        if not _is_safe_filename(report_id):
            msg = f"Unsafe report_id rejected: {report_id!r}"
            raise ValueError(msg)
        if not _is_safe_filename(artifact.filename):
            msg = f"Unsafe artifact filename rejected: {artifact.filename!r}"
            raise ValueError(msg)

        report_dir = self.base_dir / report_id
        report_dir.mkdir(parents=True, exist_ok=True)

        dest = report_dir / artifact.filename

        # Copy from source (the temp path from sandbox output)
        shutil.copy2(artifact.path, dest)

        logger.info(
            "Artifact stored: %s/%s (%s, %d bytes)",
            report_id,
            artifact.filename,
            artifact.content_type,
            artifact.size_bytes,
        )

        return dest

    def retrieve(
        self,
        report_id: str,
        filename: str,
    ) -> tuple[Path, str] | None:
        """Retrieve an artifact's path and content type.

        Args:
            report_id: The report ID.
            filename: The artifact filename.

        Returns:
            Tuple of (path, content_type) if found, None otherwise.
        """
        if not _is_safe_filename(report_id):
            logger.warning("Unsafe report_id in retrieve: %r", report_id)
            return None
        if not _is_safe_filename(filename):
            logger.warning("Unsafe filename in retrieve: %r", filename)
            return None

        path = (self.base_dir / report_id / filename).resolve()

        # Belt-and-suspenders: verify resolved path stays within base_dir
        # to guard against any path traversal that escapes the name checks.
        if not path.is_relative_to(self.base_dir.resolve()):
            logger.warning("Path traversal blocked in retrieve: %s", path)
            return None

        if not path.exists() or not path.is_file():
            return None

        # Determine content type from extension
        ext = path.suffix.lower()
        content_type = _CONTENT_TYPES.get(ext)
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"

        return path, content_type

    def content_type_for(self, filename: str) -> str:
        """Determine the content type for an artifact filename.

        Args:
            filename: The artifact filename.

        Returns:
            MIME type string (defaults to ``application/octet-stream``).
        """
        ext = Path(filename).suffix.lower()
        ct = _CONTENT_TYPES.get(ext)
        if not ct:
            ct, _ = mimetypes.guess_type(filename)
            ct = ct or "application/octet-stream"
        return ct

    def delete_report(self, report_id: str) -> None:
        """Delete all artifacts for a report.

        Args:
            report_id: The report ID whose artifacts to delete.
        """
        if not _is_safe_filename(report_id):
            logger.warning("Unsafe report_id in delete_report: %r", report_id)
            return
        report_dir = self.base_dir / report_id
        if report_dir.exists():
            shutil.rmtree(report_dir)
            logger.info("Artifacts deleted for report: %s", report_id)

    def list_artifacts(self, report_id: str) -> list[str]:
        """List all artifact filenames for a report.

        Args:
            report_id: The report ID.

        Returns:
            List of filenames (empty if report has no artifacts).
        """
        if not _is_safe_filename(report_id):
            logger.warning("Unsafe report_id in list_artifacts: %r", report_id)
            return []
        report_dir = self.base_dir / report_id
        if not report_dir.exists():
            return []

        return sorted(f.name for f in report_dir.iterdir() if f.is_file())


__all__ = [
    "ArtifactStore",
]
