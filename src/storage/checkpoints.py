"""PostgreSQL checkpointer for LangGraph state persistence.

Implements the Constitution's State requirement:
"Use LangGraph for state management and Postgres for long-term checkpointing."

This module provides a PostgreSQL-backed checkpointer that stores
graph state snapshots, enabling:
- State persistence across restarts
- State recovery after failures
- Historical state inspection for debugging
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class CheckpointRecord(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for storing LangGraph checkpoints.

    Stores serialized graph state with metadata for recovery
    and inspection. Supports both single-thread and multi-thread
    workflows via the (thread_id, checkpoint_ns, checkpoint_id) key.
    """

    __tablename__ = "checkpoints"

    # LangGraph checkpoint identity
    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Workflow thread identifier",
    )
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        doc="Checkpoint namespace (for sub-graphs)",
    )
    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Unique checkpoint identifier",
    )
    parent_checkpoint_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Parent checkpoint for branching",
    )

    # Checkpoint data
    checkpoint_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Serialized checkpoint state",
    )
    metadata_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Checkpoint metadata (step, source, etc.)",
    )

    # Channel versions for conflict detection
    channel_versions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Channel version map",
    )
    channel_values: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Pending channel writes",
    )

    # Ordering and cleanup
    step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Step number in the workflow",
    )
    checkpoint_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When checkpoint was created",
    )

    # Composite unique constraint
    __table_args__ = (
        Index(
            "ix_checkpoints_thread_ns_id",
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            unique=True,
        ),
        Index(
            "ix_checkpoints_thread_ns_step",
            "thread_id",
            "checkpoint_ns",
            "step",
        ),
    )


class PendingWrite(Base, UUIDMixin):
    """Pending channel writes for a checkpoint."""

    __tablename__ = "checkpoint_writes"

    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    checkpoint_ns: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    checkpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(255), nullable=False)
    value_data: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index(
            "ix_writes_thread_checkpoint_task",
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            "task_id",
            "idx",
            unique=True,
        ),
    )


class CheckpointConfig(BaseModel):
    """Configuration for the PostgreSQL checkpointer."""

    max_checkpoints_per_thread: int = 100
    cleanup_on_complete: bool = False


class PostgresCheckpointer(BaseCheckpointSaver):
    """LangGraph checkpointer backed by PostgreSQL.

    Provides durable state persistence for LangGraph workflows,
    enabling recovery after process restarts or failures.

    Usage:
        async with get_session() as session:
            checkpointer = PostgresCheckpointer(session)
            graph = workflow.compile(checkpointer=checkpointer)
    """

    def __init__(
        self,
        session: AsyncSession,
        config: CheckpointConfig | None = None,
    ) -> None:
        """Initialize the checkpointer.

        Args:
            session: SQLAlchemy async session
            config: Optional configuration overrides
        """
        super().__init__()
        self.session = session
        self.config = config or CheckpointConfig()

    async def aget_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
        """Get checkpoint tuple for a thread.

        Args:
            config: Configuration dict with thread_id and optional checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        query = select(CheckpointRecord).where(
            CheckpointRecord.thread_id == thread_id,
            CheckpointRecord.checkpoint_ns == checkpoint_ns,
        )

        if checkpoint_id:
            query = query.where(CheckpointRecord.checkpoint_id == checkpoint_id)
        else:
            # Get latest checkpoint
            query = query.order_by(CheckpointRecord.step.desc()).limit(1)

        result = await self.session.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            return None

        # Get pending writes
        writes_query = select(PendingWrite).where(
            PendingWrite.thread_id == thread_id,
            PendingWrite.checkpoint_ns == checkpoint_ns,
            PendingWrite.checkpoint_id == record.checkpoint_id,
        ).order_by(PendingWrite.task_id, PendingWrite.idx)

        writes_result = await self.session.execute(writes_query)
        pending_writes = [
            (w.task_id, w.channel, self._deserialize_value(w.value_type, w.value_data))
            for w in writes_result.scalars()
        ]

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": record.checkpoint_id,
                }
            },
            checkpoint=Checkpoint(
                v=1,
                id=record.checkpoint_id,
                ts=record.checkpoint_at.isoformat(),
                channel_values=record.channel_values,
                channel_versions=record.channel_versions,
                versions_seen=record.metadata_data.get("versions_seen", {}),
                pending_sends=record.metadata_data.get("pending_sends", []),
            ),
            metadata=CheckpointMetadata(
                source=record.metadata_data.get("source", "update"),
                step=record.step,
                writes=record.metadata_data.get("writes"),
                parents=record.metadata_data.get("parents", {}),
            ),
            parent_config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": record.parent_checkpoint_id,
                }
            }
            if record.parent_checkpoint_id
            else None,
            pending_writes=pending_writes,
        )

    async def alist(
        self,
        config: dict[str, Any] | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        before: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[CheckpointTuple]:
        """List checkpoints for a thread.

        Args:
            config: Configuration with thread_id
            filter: Optional metadata filters
            before: Return checkpoints before this config
            limit: Maximum number to return

        Returns:
            List of CheckpointTuples
        """
        if config is None:
            return []

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        query = select(CheckpointRecord).where(
            CheckpointRecord.thread_id == thread_id,
            CheckpointRecord.checkpoint_ns == checkpoint_ns,
        )

        if before:
            before_step = before.get("configurable", {}).get("step")
            if before_step is not None:
                query = query.where(CheckpointRecord.step < before_step)

        query = query.order_by(CheckpointRecord.step.desc())

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        records = result.scalars().all()

        tuples = []
        for record in records:
            tuples.append(
                CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": record.checkpoint_id,
                        }
                    },
                    checkpoint=Checkpoint(
                        v=1,
                        id=record.checkpoint_id,
                        ts=record.checkpoint_at.isoformat(),
                        channel_values=record.channel_values,
                        channel_versions=record.channel_versions,
                        versions_seen=record.metadata_data.get("versions_seen", {}),
                        pending_sends=record.metadata_data.get("pending_sends", []),
                    ),
                    metadata=CheckpointMetadata(
                        source=record.metadata_data.get("source", "update"),
                        step=record.step,
                        writes=record.metadata_data.get("writes"),
                        parents=record.metadata_data.get("parents", {}),
                    ),
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": record.parent_checkpoint_id,
                        }
                    }
                    if record.parent_checkpoint_id
                    else None,
                )
            )

        return tuples

    async def aput(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict[str, Any]:
        """Save a checkpoint.

        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Updated channel versions

        Returns:
            Updated configuration with checkpoint_id
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        # Prepare metadata dict
        meta_dict = {
            "source": metadata.source,
            "writes": metadata.writes,
            "parents": metadata.parents,
            "versions_seen": checkpoint.versions_seen,
            "pending_sends": checkpoint.pending_sends,
        }

        # Upsert checkpoint
        stmt = insert(CheckpointRecord).values(
            thread_id=thread_id,
            checkpoint_ns=checkpoint_ns,
            checkpoint_id=checkpoint.id,
            parent_checkpoint_id=parent_checkpoint_id,
            checkpoint_data=checkpoint.channel_values,
            metadata_data=meta_dict,
            channel_versions=dict(checkpoint.channel_versions),
            channel_values=checkpoint.channel_values,
            step=metadata.step,
            checkpoint_at=datetime.fromisoformat(checkpoint.ts),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["thread_id", "checkpoint_ns", "checkpoint_id"],
            set_={
                "checkpoint_data": stmt.excluded.checkpoint_data,
                "metadata_data": stmt.excluded.metadata_data,
                "channel_versions": stmt.excluded.channel_versions,
                "channel_values": stmt.excluded.channel_values,
                "step": stmt.excluded.step,
                "checkpoint_at": stmt.excluded.checkpoint_at,
            },
        )

        await self.session.execute(stmt)

        # Cleanup old checkpoints if needed
        await self._cleanup_old_checkpoints(thread_id, checkpoint_ns)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint.id,
            }
        }

    async def aput_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Save pending writes for a checkpoint.

        Args:
            config: Configuration with thread_id and checkpoint_id
            writes: List of (channel, value) tuples
            task_id: Task identifier
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        for idx, (channel, value) in enumerate(writes):
            value_type, value_data = self._serialize_value(value)

            stmt = insert(PendingWrite).values(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                checkpoint_id=checkpoint_id,
                task_id=task_id,
                idx=idx,
                channel=channel,
                value_type=value_type,
                value_data=value_data,
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "thread_id",
                    "checkpoint_ns",
                    "checkpoint_id",
                    "task_id",
                    "idx",
                ],
                set_={
                    "channel": stmt.excluded.channel,
                    "value_type": stmt.excluded.value_type,
                    "value_data": stmt.excluded.value_data,
                },
            )

            await self.session.execute(stmt)

    async def _cleanup_old_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str,
    ) -> None:
        """Remove old checkpoints exceeding the limit.

        Args:
            thread_id: Thread to clean up
            checkpoint_ns: Namespace to clean up
        """
        # Get checkpoint IDs to keep
        keep_query = (
            select(CheckpointRecord.checkpoint_id)
            .where(
                CheckpointRecord.thread_id == thread_id,
                CheckpointRecord.checkpoint_ns == checkpoint_ns,
            )
            .order_by(CheckpointRecord.step.desc())
            .limit(self.config.max_checkpoints_per_thread)
        )

        keep_result = await self.session.execute(keep_query)
        keep_ids = {row[0] for row in keep_result.fetchall()}

        if not keep_ids:
            return

        # Delete old checkpoints
        delete_query = delete(CheckpointRecord).where(
            CheckpointRecord.thread_id == thread_id,
            CheckpointRecord.checkpoint_ns == checkpoint_ns,
            CheckpointRecord.checkpoint_id.notin_(keep_ids),
        )
        await self.session.execute(delete_query)

        # Delete orphaned writes
        delete_writes = delete(PendingWrite).where(
            PendingWrite.thread_id == thread_id,
            PendingWrite.checkpoint_ns == checkpoint_ns,
            PendingWrite.checkpoint_id.notin_(keep_ids),
        )
        await self.session.execute(delete_writes)

    def _serialize_value(self, value: Any) -> tuple[str, str]:
        """Serialize a channel value for storage.

        Args:
            value: Value to serialize

        Returns:
            Tuple of (type_name, serialized_data)
        """
        import json

        if isinstance(value, BaseModel):
            return ("pydantic", value.model_dump_json())
        elif isinstance(value, dict | list):
            return ("json", json.dumps(value))
        else:
            return ("json", json.dumps(value))

    def _deserialize_value(self, value_type: str, value_data: str) -> Any:
        """Deserialize a stored channel value.

        Args:
            value_type: Type of the stored value
            value_data: Serialized data

        Returns:
            Deserialized value
        """
        import json

        if value_type == "json":
            return json.loads(value_data)
        elif value_type == "pydantic":
            # Note: For Pydantic, we return the dict form
            # The graph node should reconstruct if needed
            return json.loads(value_data)
        else:
            return json.loads(value_data)

    # Sync methods (required by base class but we use async)
    def get_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
        """Sync version - not implemented, use aget_tuple."""
        raise NotImplementedError("Use aget_tuple for async operations")

    def list(
        self,
        config: dict[str, Any] | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        before: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[CheckpointTuple]:
        """Sync version - not implemented, use alist."""
        raise NotImplementedError("Use alist for async operations")

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict[str, Any]:
        """Sync version - not implemented, use aput."""
        raise NotImplementedError("Use aput for async operations")

    def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Sync version - not implemented, use aput_writes."""
        raise NotImplementedError("Use aput_writes for async operations")


# Exports
__all__ = [
    "CheckpointRecord",
    "PendingWrite",
    "CheckpointConfig",
    "PostgresCheckpointer",
]
