"""Artifact serving API route.

Serves validated artifacts (charts, CSVs) produced by sandbox analysis
scripts.  All responses include security headers to prevent content
sniffing and script execution.

Constitution: Security — nosniff, CSP sandbox, inline disposition.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse

from src.storage.artifact_store import ArtifactStore

router = APIRouter(tags=["Artifacts"])

# Module-level store singleton (overridable in tests via patching)
_store: ArtifactStore | None = None

# Strict allowlist patterns — only alphanumeric, hyphens, underscores.
# These guarantee no path separators, dots-only sequences, or null bytes
# can reach the filesystem layer.
_SAFE_ID_RE = re.compile(r"\A[a-zA-Z0-9_-]+\Z")
_SAFE_FILENAME_RE = re.compile(r"\A[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+\Z")


def _sanitize_path_component(value: str, pattern: re.Pattern[str], label: str) -> str:
    """Validate and return a path component, or raise HTTPException 400.

    This function breaks the CodeQL taint chain: the *returned* string
    is the same object only when the regex matched, so static analysis
    can see no uncontrolled data reaches the filesystem.
    """
    m = pattern.match(value)
    if m is None:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")
    return m.group(0)  # return the matched (safe) text — untainted by CodeQL


def get_artifact_store() -> ArtifactStore:
    """Get or create the artifact store singleton."""
    global _store
    if _store is None:
        _store = ArtifactStore()
    return _store


@router.get(
    "/reports/{report_id}/artifacts/{filename:path}",
    summary="Serve an analysis artifact",
    responses={
        200: {"description": "Artifact file"},
        404: {"description": "Artifact not found"},
    },
)
async def serve_artifact(
    report_id: str = Path(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    ),
    filename: str = Path(
        ...,
        min_length=1,
        max_length=255,
    ),
) -> FileResponse:
    """Serve a validated artifact from a completed analysis report.

    Security headers are set on all responses:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - Content-Security-Policy: sandbox (prevent script execution)
    - Content-Disposition: inline; filename=... (safe inline rendering)

    Args:
        report_id: The analysis report ID (alphanumeric, hyphens, underscores).
        filename: The artifact filename (e.g. ``chart.png``).

    Returns:
        FileResponse with the artifact content and security headers.

    Raises:
        HTTPException 404: If the artifact does not exist.
        HTTPException 400: If the parameters contain unsafe characters.
    """
    # Sanitize inputs — _sanitize_path_component returns the regex match
    # group, which CodeQL treats as a new (untainted) value.
    safe_id = _sanitize_path_component(report_id, _SAFE_ID_RE, "report_id")
    safe_name = _sanitize_path_component(filename, _SAFE_FILENAME_RE, "filename")

    store = get_artifact_store()

    # Build the expected path from validated components and the store's
    # known base directory.  This keeps the taint chain broken: the path
    # is assembled from the store's base_dir (a config constant) plus
    # the regex-matched components — not from raw user input.
    expected = (store.base_dir / safe_id / safe_name).resolve()

    # Verify the resolved path stays within the store's base directory
    # (belt-and-suspenders against any symlink tricks).
    base_resolved = store.base_dir.resolve()
    if not expected.is_relative_to(base_resolved):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not expected.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Determine content type from extension (use the store's logic).
    content_type = store.content_type_for(safe_name)

    # Construct the response path as a string from our fully-validated
    # pathlib.Path — no user-tainted data flows here.
    verified_path: str = str(expected)

    return FileResponse(
        path=verified_path,
        media_type=content_type,
        filename=safe_name,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Content-Disposition": f'inline; filename="{safe_name}"',
        },
    )
