"""Unit tests for artifact storage service (T3316-T3317).

Tests filesystem-based artifact persistence, retrieval, and deletion.
All operations use tmp_path — no real data directory involved.
"""

from pathlib import Path

import pytest

from src.sandbox.artifact_validator import ArtifactMeta

# =============================================================================
# T3316: ArtifactStore persist, retrieve, delete
# =============================================================================


class TestArtifactStore:
    """Test the ArtifactStore filesystem operations."""

    def test_persist_artifact(self, tmp_path: Path):
        """Persisting an artifact copies it to the store directory."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)

        # Create a source artifact
        source = tmp_path / "source" / "chart.png"
        source.parent.mkdir()
        source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        artifact = ArtifactMeta(
            filename="chart.png",
            content_type="image/png",
            size_bytes=source.stat().st_size,
            path=source,
        )

        stored_path = store.persist(report_id="rpt-001", artifact=artifact)

        assert stored_path.exists()
        assert stored_path.name == "chart.png"
        assert stored_path.parent.name == "rpt-001"
        assert stored_path.read_bytes() == source.read_bytes()

    def test_persist_multiple_artifacts(self, tmp_path: Path):
        """Multiple artifacts for the same report go in the same directory."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        artifacts = []
        for name, content in [("a.png", b"\x89PNG\r\n\x1a\n"), ("b.csv", b"col1\n1\n")]:
            f = source_dir / name
            f.write_bytes(content)
            artifacts.append(
                ArtifactMeta(
                    filename=name,
                    content_type="image/png" if name.endswith(".png") else "text/csv",
                    size_bytes=f.stat().st_size,
                    path=f,
                )
            )

        for a in artifacts:
            store.persist(report_id="rpt-002", artifact=a)

        report_dir = tmp_path / "rpt-002"
        assert report_dir.exists()
        assert len(list(report_dir.iterdir())) == 2

    def test_retrieve_artifact(self, tmp_path: Path):
        """Retrieve returns the path and content type of a stored artifact."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)

        # Persist first
        source = tmp_path / "source" / "data.csv"
        source.parent.mkdir()
        source.write_text("col1,col2\n1,2\n")

        artifact = ArtifactMeta(
            filename="data.csv",
            content_type="text/csv",
            size_bytes=source.stat().st_size,
            path=source,
        )
        store.persist(report_id="rpt-003", artifact=artifact)

        # Retrieve
        result = store.retrieve(report_id="rpt-003", filename="data.csv")
        assert result is not None
        path, content_type = result
        assert path.exists()
        assert content_type == "text/csv"
        assert path.read_text() == "col1,col2\n1,2\n"

    def test_retrieve_nonexistent_returns_none(self, tmp_path: Path):
        """Retrieve returns None for a nonexistent artifact."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        assert store.retrieve(report_id="nope", filename="nope.png") is None

    def test_delete_report_artifacts(self, tmp_path: Path):
        """Deleting a report's artifacts removes the entire directory."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)

        # Persist
        source = tmp_path / "source" / "chart.png"
        source.parent.mkdir()
        source.write_bytes(b"\x89PNG\r\n\x1a\n")

        artifact = ArtifactMeta(
            filename="chart.png",
            content_type="image/png",
            size_bytes=source.stat().st_size,
            path=source,
        )
        store.persist(report_id="rpt-del", artifact=artifact)
        assert (tmp_path / "rpt-del").exists()

        # Delete
        store.delete_report(report_id="rpt-del")
        assert not (tmp_path / "rpt-del").exists()

    def test_delete_nonexistent_is_noop(self, tmp_path: Path):
        """Deleting a nonexistent report does not raise."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        store.delete_report(report_id="nope")  # Should not raise

    def test_list_artifacts(self, tmp_path: Path):
        """List returns all artifact filenames for a report."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        for name in ("a.png", "b.csv"):
            f = source_dir / name
            f.write_bytes(b"\x89PNG\r\n\x1a\n" if name.endswith(".png") else b"col1\n1\n")
            store.persist(
                report_id="rpt-list",
                artifact=ArtifactMeta(
                    filename=name,
                    content_type="image/png",
                    size_bytes=f.stat().st_size,
                    path=f,
                ),
            )

        names = store.list_artifacts(report_id="rpt-list")
        assert sorted(names) == ["a.png", "b.csv"]

    def test_list_empty_report(self, tmp_path: Path):
        """List returns empty for a nonexistent report."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        assert store.list_artifacts(report_id="nope") == []


# =============================================================================
# T3317: Filename sanitization in store
# =============================================================================


class TestArtifactStoreSecurity:
    """Test that the store rejects unsafe filenames."""

    def test_rejects_path_traversal(self, tmp_path: Path):
        """Store rejects artifacts with path traversal in filename."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)

        source = tmp_path / "source" / "chart.png"
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(b"\x89PNG\r\n\x1a\n")

        artifact = ArtifactMeta(
            filename="../../../etc/passwd",
            content_type="image/png",
            size_bytes=source.stat().st_size,
            path=source,
        )

        with pytest.raises(ValueError, match=r"(?i)unsafe"):
            store.persist(report_id="rpt-evil", artifact=artifact)

    def test_rejects_slash_in_filename(self, tmp_path: Path):
        """Store rejects filenames containing slashes."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)

        source = tmp_path / "source" / "chart.png"
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(b"\x89PNG\r\n\x1a\n")

        artifact = ArtifactMeta(
            filename="sub/chart.png",
            content_type="image/png",
            size_bytes=source.stat().st_size,
            path=source,
        )

        with pytest.raises(ValueError, match=r"(?i)unsafe"):
            store.persist(report_id="rpt-evil", artifact=artifact)

    def test_retrieve_rejects_unsafe_filename(self, tmp_path: Path):
        """Retrieve rejects filenames with path traversal."""
        from src.storage.artifact_store import ArtifactStore

        store = ArtifactStore(base_dir=tmp_path)
        assert store.retrieve(report_id="rpt-1", filename="../../../etc/passwd") is None
