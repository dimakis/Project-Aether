"""Unit tests for PostgresCheckpointer (src/storage/checkpoints.py).

All DB operations are mocked via a MagicMock AsyncSession.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.storage.checkpoints import (
    CheckpointConfig,
    CheckpointRecord,
    PendingWrite,
    PostgresCheckpointer,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def checkpointer(mock_session):
    return PostgresCheckpointer(mock_session)


@pytest.fixture
def sample_config():
    return {
        "configurable": {
            "thread_id": "thread-1",
            "checkpoint_ns": "",
            "checkpoint_id": "cp-1",
        }
    }


class TestCheckpointConfig:
    def test_default_config(self):
        cfg = CheckpointConfig()
        assert cfg.max_checkpoints_per_thread == 100
        assert cfg.cleanup_on_complete is False

    def test_custom_config(self):
        cfg = CheckpointConfig(max_checkpoints_per_thread=50, cleanup_on_complete=True)
        assert cfg.max_checkpoints_per_thread == 50
        assert cfg.cleanup_on_complete is True


class TestCheckpointRecordModel:
    def test_tablename(self):
        assert CheckpointRecord.__tablename__ == "checkpoints"

    def test_pending_write_tablename(self):
        assert PendingWrite.__tablename__ == "checkpoint_writes"


class TestPostgresCheckpointerInit:
    def test_init_default_config(self, mock_session):
        cp = PostgresCheckpointer(mock_session)
        assert cp.session is mock_session
        assert cp.config.max_checkpoints_per_thread == 100

    def test_init_custom_config(self, mock_session):
        cfg = CheckpointConfig(max_checkpoints_per_thread=10)
        cp = PostgresCheckpointer(mock_session, config=cfg)
        assert cp.config.max_checkpoints_per_thread == 10


class TestAgetTuple:
    async def test_returns_none_when_not_found(self, checkpointer, mock_session, sample_config):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await checkpointer.aget_tuple(sample_config)
        assert result is None

    async def test_returns_checkpoint_tuple(self, checkpointer, mock_session, sample_config):
        record = MagicMock()
        record.thread_id = "thread-1"
        record.checkpoint_ns = ""
        record.checkpoint_id = "cp-1"
        record.parent_checkpoint_id = None
        record.checkpoint_data = {"key": "value"}
        record.metadata_data = {"source": "update", "versions_seen": {}, "pending_sends": []}
        record.channel_versions = {"ch1": 1}
        record.channel_values = {"ch1": "val"}
        record.step = 3
        record.checkpoint_at = datetime.now(UTC)

        # First execute: the checkpoint query
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = record

        # Second execute: pending writes query
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value = []

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        result = await checkpointer.aget_tuple(sample_config)
        assert result is not None
        assert result.config["configurable"]["checkpoint_id"] == "cp-1"

    async def test_with_specific_checkpoint_id(self, checkpointer, mock_session):
        config = {
            "configurable": {
                "thread_id": "thread-1",
                "checkpoint_ns": "",
                "checkpoint_id": "cp-specific",
            }
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await checkpointer.aget_tuple(config)
        assert result is None
        mock_session.execute.assert_called_once()

    async def test_with_pending_writes(self, checkpointer, mock_session, sample_config):
        record = MagicMock()
        record.thread_id = "thread-1"
        record.checkpoint_ns = ""
        record.checkpoint_id = "cp-1"
        record.parent_checkpoint_id = "cp-0"
        record.checkpoint_data = {}
        record.metadata_data = {"source": "update", "versions_seen": {}, "pending_sends": []}
        record.channel_versions = {}
        record.channel_values = {}
        record.step = 1
        record.checkpoint_at = datetime.now(UTC)

        write = MagicMock()
        write.task_id = "task-1"
        write.channel = "messages"
        write.value_type = "json"
        write.value_data = '["hello"]'

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = record
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value = [write]

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        result = await checkpointer.aget_tuple(sample_config)
        assert result is not None
        assert len(result.pending_writes) == 1
        assert result.parent_config is not None


class TestAlist:
    async def test_returns_empty_for_none_config(self, checkpointer):
        result = await checkpointer.alist(None)
        assert result == []

    async def test_returns_checkpoints(self, checkpointer, mock_session):
        config = {"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}}
        record = MagicMock()
        record.checkpoint_id = "cp-1"
        record.checkpoint_at = datetime.now(UTC)
        record.channel_values = {}
        record.channel_versions = {}
        record.metadata_data = {"source": "update", "versions_seen": {}, "pending_sends": []}
        record.step = 1
        record.parent_checkpoint_id = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [record]
        mock_session.execute.return_value = mock_result

        result = await checkpointer.alist(config)
        assert len(result) == 1

    async def test_with_limit(self, checkpointer, mock_session):
        config = {"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}}
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await checkpointer.alist(config, limit=5)
        assert result == []

    async def test_with_before(self, checkpointer, mock_session):
        config = {"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}}
        before = {"configurable": {"step": 10}}
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await checkpointer.alist(config, before=before)
        assert result == []


class TestAput:
    async def test_put_checkpoint(self, checkpointer, mock_session, sample_config):
        # Checkpoint and CheckpointMetadata are TypedDicts but source code
        # accesses them via attribute syntax, so use MagicMock
        checkpoint = MagicMock()
        checkpoint.id = "cp-new"
        checkpoint.ts = datetime.now(UTC).isoformat()
        checkpoint.channel_values = {"ch1": "val"}
        checkpoint.channel_versions = {"ch1": 1}
        checkpoint.versions_seen = {}
        checkpoint.pending_sends = []

        metadata = MagicMock()
        metadata.source = "update"
        metadata.step = 5
        metadata.writes = None
        metadata.parents = {}

        # Mock cleanup
        cleanup_result = MagicMock()
        cleanup_result.fetchall.return_value = [("cp-new",)]
        mock_session.execute.return_value = cleanup_result

        result = await checkpointer.aput(sample_config, checkpoint, metadata, {})
        assert result["configurable"]["checkpoint_id"] == "cp-new"
        assert mock_session.execute.call_count >= 1  # upsert + cleanup


class TestAputWrites:
    async def test_put_writes(self, checkpointer, mock_session, sample_config):
        writes = [("messages", ["hello"]), ("status", "active")]
        await checkpointer.aput_writes(sample_config, writes, "task-1")
        assert mock_session.execute.call_count == 2  # one per write


class TestSerializeDeserialize:
    def test_serialize_dict(self, checkpointer):
        vtype, vdata = checkpointer._serialize_value({"key": "value"})
        assert vtype == "json"
        assert json.loads(vdata) == {"key": "value"}

    def test_serialize_list(self, checkpointer):
        vtype, vdata = checkpointer._serialize_value([1, 2, 3])
        assert vtype == "json"
        assert json.loads(vdata) == [1, 2, 3]

    def test_serialize_string(self, checkpointer):
        vtype, vdata = checkpointer._serialize_value("hello")
        assert vtype == "json"
        assert json.loads(vdata) == "hello"

    def test_deserialize_json(self, checkpointer):
        result = checkpointer._deserialize_value("json", '{"a": 1}')
        assert result == {"a": 1}

    def test_deserialize_pydantic(self, checkpointer):
        result = checkpointer._deserialize_value("pydantic", '{"name": "test"}')
        assert result == {"name": "test"}

    def test_deserialize_unknown_type(self, checkpointer):
        result = checkpointer._deserialize_value("unknown", '"hello"')
        assert result == "hello"


class TestSyncMethodsNotImplemented:
    def test_get_tuple_raises(self, checkpointer, sample_config):
        with pytest.raises(NotImplementedError):
            checkpointer.get_tuple(sample_config)

    def test_list_raises(self, checkpointer, sample_config):
        with pytest.raises(NotImplementedError):
            checkpointer.list(sample_config)

    def test_put_raises(self, checkpointer, sample_config):
        with pytest.raises(NotImplementedError):
            checkpointer.put(sample_config, MagicMock(), MagicMock(), {})

    def test_put_writes_raises(self, checkpointer, sample_config):
        with pytest.raises(NotImplementedError):
            checkpointer.put_writes(sample_config, [], "task-1")


class TestCleanupOldCheckpoints:
    async def test_cleanup_removes_old(self, checkpointer, mock_session):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("cp-1",), ("cp-2",)]
        mock_session.execute.return_value = mock_result

        await checkpointer._cleanup_old_checkpoints("thread-1", "")
        assert mock_session.execute.call_count == 3  # select + delete + delete writes

    async def test_cleanup_empty_keeps(self, checkpointer, mock_session):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        await checkpointer._cleanup_old_checkpoints("thread-1", "")
        assert mock_session.execute.call_count == 1  # only select
