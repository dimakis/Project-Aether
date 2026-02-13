"""Unit tests for artifact serving API (T3318-T3319).

Tests the GET /reports/{report_id}/artifacts/{filename} endpoint.
Uses FastAPI TestClient with a real ArtifactStore backed by tmp_path.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.artifacts import router
from src.storage.artifact_store import ArtifactStore


@pytest.fixture
def app() -> FastAPI:
    """Create a minimal test app with the artifacts router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _setup_artifact(tmp_path: Path, report_id: str, filename: str, content: bytes) -> ArtifactStore:
    """Create a real artifact file under a tmp-based ArtifactStore."""
    store = ArtifactStore(base_dir=tmp_path)
    report_dir = tmp_path / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / filename).write_bytes(content)
    return store


# =============================================================================
# T3318: Artifact serving endpoint
# =============================================================================


class TestArtifactServingEndpoint:
    """Test GET /reports/{report_id}/artifacts/{filename}."""

    def test_serve_existing_artifact(self, client: TestClient, tmp_path: Path):
        """Serving a valid artifact returns the file with correct content type."""
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        store = _setup_artifact(tmp_path, "rpt-001", "chart.png", content)

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/chart.png")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == content

    def test_serve_csv_artifact(self, client: TestClient, tmp_path: Path):
        """CSV artifacts are served with text/csv content type."""
        content = b"col1,col2\n1,2\n"
        store = _setup_artifact(tmp_path, "rpt-001", "data.csv", content)

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/data.csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_nonexistent_artifact_404(self, client: TestClient, tmp_path: Path):
        """Requesting a nonexistent artifact returns 404."""
        store = ArtifactStore(base_dir=tmp_path)

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/nope.png")

        assert response.status_code == 404

    def test_path_traversal_rejected(self, client: TestClient, tmp_path: Path):
        """Path traversal in filename is rejected with 400."""
        store = ArtifactStore(base_dir=tmp_path)

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/..%2F..%2Fetc%2Fpasswd")

        assert response.status_code == 400

    def test_invalid_report_id_rejected(self, client: TestClient, tmp_path: Path):
        """Report IDs with unsafe characters are rejected (422 from FastAPI pattern)."""
        store = ArtifactStore(base_dir=tmp_path)

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt..evil/artifacts/chart.png")

        # FastAPI Path(pattern=...) returns 422 for pattern violations
        assert response.status_code == 422


# =============================================================================
# T3319: Security headers
# =============================================================================


class TestArtifactSecurityHeaders:
    """Test that artifact responses include proper security headers."""

    def test_nosniff_header(self, client: TestClient, tmp_path: Path):
        """Response includes X-Content-Type-Options: nosniff."""
        store = _setup_artifact(
            tmp_path, "rpt-001", "chart.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        )

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/chart.png")

        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_csp_sandbox_header(self, client: TestClient, tmp_path: Path):
        """Response includes Content-Security-Policy: sandbox."""
        store = _setup_artifact(
            tmp_path, "rpt-001", "chart.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        )

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/chart.png")

        assert "sandbox" in response.headers.get("content-security-policy", "")

    def test_content_disposition_inline(self, client: TestClient, tmp_path: Path):
        """Response includes Content-Disposition: inline."""
        store = _setup_artifact(
            tmp_path, "rpt-001", "chart.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        )

        with patch("src.api.routes.artifacts.get_artifact_store", return_value=store):
            response = client.get("/reports/rpt-001/artifacts/chart.png")

        disp = response.headers.get("content-disposition", "")
        assert "inline" in disp
