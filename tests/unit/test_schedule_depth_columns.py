"""Unit tests for A5: depth/strategy/timeout columns on InsightSchedule.

Verifies that the InsightSchedule entity has the new columns and they
can be set and read.
"""

from __future__ import annotations

from sqlalchemy import inspect as sa_inspect


class TestInsightScheduleDepthColumns:
    """InsightSchedule has depth, strategy, and timeout_seconds columns."""

    def test_depth_column_exists_in_mapper(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        mapper = sa_inspect(InsightSchedule)
        assert "depth" in mapper.columns

    def test_strategy_column_exists_in_mapper(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        mapper = sa_inspect(InsightSchedule)
        assert "strategy" in mapper.columns

    def test_timeout_seconds_column_exists_in_mapper(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        mapper = sa_inspect(InsightSchedule)
        assert "timeout_seconds" in mapper.columns

    def test_custom_depth_and_strategy(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        schedule = InsightSchedule(
            id="test-1",
            name="Deep weekly analysis",
            analysis_type="energy",
            trigger_type="cron",
            cron_expression="0 0 * * 0",
            depth="deep",
            strategy="teamwork",
            timeout_seconds=300,
        )
        assert schedule.depth == "deep"
        assert schedule.strategy == "teamwork"
        assert schedule.timeout_seconds == 300

    def test_depth_column_has_server_default(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        mapper = sa_inspect(InsightSchedule)
        col = mapper.columns["depth"]
        assert col.server_default is not None
        assert col.server_default.arg == "standard"

    def test_strategy_column_has_server_default(self):
        from src.storage.entities.insight_schedule import InsightSchedule

        mapper = sa_inspect(InsightSchedule)
        col = mapper.columns["strategy"]
        assert col.server_default is not None
        assert col.server_default.arg == "parallel"


class TestMigrationFileExists:
    """The Alembic migration file for the new columns exists."""

    def test_migration_file_exists(self):
        from pathlib import Path

        migration = Path("alembic/versions/024_schedule_depth_strategy.py")
        assert migration.exists(), f"Migration file not found: {migration}"
