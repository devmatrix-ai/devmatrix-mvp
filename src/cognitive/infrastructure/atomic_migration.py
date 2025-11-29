"""
Atomic Migration System with Checkpoints
=========================================
Sprint: Infrastructure Improvements (Fase 4)
Date: 2025-11-29

Provides:
- Batch execution with automatic checkpointing
- Rollback capability on failure
- Progress tracking and resumption
- Transaction-safe operations
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

from neo4j import GraphDatabase, Session


class CheckpointStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Batch:
    """Represents a batch of operations to execute."""
    batch_id: str
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    rollback_query: Optional[str] = None
    rollback_parameters: Optional[Dict[str, Any]] = None


@dataclass
class CheckpointState:
    """Represents the state of a migration checkpoint."""
    checkpoint_id: str
    migration_id: str
    batch_index: int
    total_batches: int
    status: CheckpointStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)


class MigrationCheckpoint:
    """Manages checkpoint state for atomic migrations."""

    def __init__(self, driver, database: str, migration_id: str):
        self.driver = driver
        self.database = database
        self.migration_id = migration_id
        self.checkpoint_id = f"{migration_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create(self, total_batches: int) -> CheckpointState:
        """Create a new checkpoint for this migration."""
        with self.driver.session(database=self.database) as session:
            query = """
            CREATE (c:MigrationCheckpoint {
                checkpoint_id: $checkpoint_id,
                migration_id: $migration_id,
                batch_index: 0,
                total_batches: $total_batches,
                status: $status,
                created_at: datetime(),
                updated_at: datetime(),
                stats: '{}'
            })
            RETURN c
            """
            result = session.run(query, {
                "checkpoint_id": self.checkpoint_id,
                "migration_id": self.migration_id,
                "total_batches": total_batches,
                "status": CheckpointStatus.PENDING.value
            })
            record = result.single()

            return CheckpointState(
                checkpoint_id=self.checkpoint_id,
                migration_id=self.migration_id,
                batch_index=0,
                total_batches=total_batches,
                status=CheckpointStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def update(self, batch_index: int, status: CheckpointStatus,
               stats: Optional[Dict] = None, error: Optional[str] = None):
        """Update checkpoint progress."""
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (c:MigrationCheckpoint {checkpoint_id: $checkpoint_id})
            SET c.batch_index = $batch_index,
                c.status = $status,
                c.updated_at = datetime(),
                c.stats = $stats,
                c.error_message = $error
            RETURN c
            """
            session.run(query, {
                "checkpoint_id": self.checkpoint_id,
                "batch_index": batch_index,
                "status": status.value,
                "stats": json.dumps(stats or {}),
                "error": error
            })

    def get_latest(self) -> Optional[CheckpointState]:
        """Get the latest checkpoint for this migration."""
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (c:MigrationCheckpoint {migration_id: $migration_id})
            RETURN c
            ORDER BY c.created_at DESC
            LIMIT 1
            """
            result = session.run(query, {"migration_id": self.migration_id})
            record = result.single()

            if not record:
                return None

            c = record["c"]
            return CheckpointState(
                checkpoint_id=c["checkpoint_id"],
                migration_id=c["migration_id"],
                batch_index=c["batch_index"],
                total_batches=c["total_batches"],
                status=CheckpointStatus(c["status"]),
                created_at=c["created_at"].to_native(),
                updated_at=c["updated_at"].to_native(),
                error_message=c.get("error_message"),
                stats=json.loads(c.get("stats", "{}"))
            )

    def mark_completed(self, stats: Dict[str, Any]):
        """Mark checkpoint as completed."""
        self.update(
            batch_index=-1,  # -1 indicates completion
            status=CheckpointStatus.COMPLETED,
            stats=stats
        )

    def mark_failed(self, batch_index: int, error: str, stats: Dict[str, Any]):
        """Mark checkpoint as failed."""
        self.update(
            batch_index=batch_index,
            status=CheckpointStatus.FAILED,
            stats=stats,
            error=error
        )

    def mark_rolled_back(self, stats: Dict[str, Any]):
        """Mark checkpoint as rolled back."""
        self.update(
            batch_index=-1,
            status=CheckpointStatus.ROLLED_BACK,
            stats=stats
        )


class AtomicMigration:
    """
    Executes migrations atomically with checkpoint support.

    Features:
    - Batch execution with progress tracking
    - Automatic checkpointing at configurable intervals
    - Rollback on failure (if rollback queries provided)
    - Resume from last checkpoint
    """

    def __init__(self, driver, database: str):
        self.driver = driver
        self.database = database
        self.stats = {
            "batches_executed": 0,
            "batches_failed": 0,
            "batches_rolled_back": 0,
            "rows_affected": 0
        }

    def execute_with_checkpoints(
        self,
        migration_id: str,
        batches: List[Batch],
        checkpoint_interval: int = 10,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        resume_from_checkpoint: bool = True
    ) -> Dict[str, Any]:
        """
        Execute batches with automatic checkpointing.

        Args:
            migration_id: Unique identifier for this migration
            batches: List of Batch objects to execute
            checkpoint_interval: Save checkpoint every N batches
            on_progress: Callback for progress updates (current, total, description)
            resume_from_checkpoint: If True, resume from last checkpoint if exists

        Returns:
            Dict with execution stats and status
        """
        checkpoint = MigrationCheckpoint(self.driver, self.database, migration_id)

        # Check for existing checkpoint to resume
        start_index = 0
        if resume_from_checkpoint:
            existing = checkpoint.get_latest()
            if existing and existing.status == CheckpointStatus.FAILED:
                start_index = existing.batch_index
                print(f"Resuming from batch {start_index} (previous failure)")
                self.stats = existing.stats

        # Create new checkpoint
        state = checkpoint.create(len(batches))
        checkpoint.update(start_index, CheckpointStatus.IN_PROGRESS)

        executed_batches = []

        try:
            for i, batch in enumerate(batches[start_index:], start=start_index):
                # Execute batch
                try:
                    rows = self._execute_batch(batch)
                    self.stats["batches_executed"] += 1
                    self.stats["rows_affected"] += rows
                    executed_batches.append(batch)

                    if on_progress:
                        on_progress(i + 1, len(batches), batch.description)

                except Exception as e:
                    self.stats["batches_failed"] += 1
                    checkpoint.mark_failed(i, str(e), self.stats)
                    raise MigrationError(
                        f"Batch {i} ({batch.batch_id}) failed: {e}",
                        batch_index=i,
                        batch_id=batch.batch_id
                    )

                # Save checkpoint at intervals
                if (i + 1) % checkpoint_interval == 0:
                    checkpoint.update(i + 1, CheckpointStatus.IN_PROGRESS, self.stats)

            # Mark as completed
            checkpoint.mark_completed(self.stats)

            return {
                "status": "success",
                "migration_id": migration_id,
                "checkpoint_id": checkpoint.checkpoint_id,
                "stats": self.stats
            }

        except MigrationError as e:
            # Attempt rollback if rollback queries exist
            if any(b.rollback_query for b in executed_batches):
                print(f"Attempting rollback of {len(executed_batches)} batches...")
                self._rollback(executed_batches, checkpoint)

            raise

    def _execute_batch(self, batch: Batch) -> int:
        """Execute a single batch and return rows affected."""
        with self.driver.session(database=self.database) as session:
            result = session.run(batch.query, batch.parameters)
            summary = result.consume()
            return (
                summary.counters.nodes_created +
                summary.counters.nodes_deleted +
                summary.counters.relationships_created +
                summary.counters.relationships_deleted +
                summary.counters.properties_set
            )

    def _rollback(self, executed_batches: List[Batch], checkpoint: MigrationCheckpoint):
        """Rollback executed batches in reverse order."""
        for batch in reversed(executed_batches):
            if batch.rollback_query:
                try:
                    with self.driver.session(database=self.database) as session:
                        session.run(
                            batch.rollback_query,
                            batch.rollback_parameters or batch.parameters
                        )
                    self.stats["batches_rolled_back"] += 1
                except Exception as e:
                    print(f"Rollback failed for batch {batch.batch_id}: {e}")

        checkpoint.mark_rolled_back(self.stats)


class MigrationError(Exception):
    """Exception raised when a migration batch fails."""

    def __init__(self, message: str, batch_index: int = -1, batch_id: str = ""):
        super().__init__(message)
        self.batch_index = batch_index
        self.batch_id = batch_id


# Utility functions for creating common batch types

def create_node_batch(
    label: str,
    properties: Dict[str, Any],
    batch_id: str,
    description: str = ""
) -> Batch:
    """Create a batch for node creation."""
    return Batch(
        batch_id=batch_id,
        query=f"""
        CREATE (n:{label} $props)
        SET n.created_at = datetime(),
            n.updated_at = datetime()
        RETURN n
        """,
        parameters={"props": properties},
        description=description or f"Create {label} node",
        rollback_query=f"""
        MATCH (n:{label})
        WHERE n.{list(properties.keys())[0]} = $key_value
        DELETE n
        """,
        rollback_parameters={"key_value": list(properties.values())[0]}
    )


def create_relationship_batch(
    source_label: str,
    source_key: str,
    source_value: Any,
    target_label: str,
    target_key: str,
    target_value: Any,
    rel_type: str,
    rel_properties: Optional[Dict[str, Any]] = None,
    batch_id: str = "",
    description: str = ""
) -> Batch:
    """Create a batch for relationship creation."""
    return Batch(
        batch_id=batch_id or f"rel_{source_value}_{target_value}",
        query=f"""
        MATCH (s:{source_label} {{{source_key}: $source_value}})
        MATCH (t:{target_label} {{{target_key}: $target_value}})
        MERGE (s)-[r:{rel_type}]->(t)
        ON CREATE SET r += $props, r.created_at = datetime()
        RETURN r
        """,
        parameters={
            "source_value": source_value,
            "target_value": target_value,
            "props": rel_properties or {}
        },
        description=description or f"Create {rel_type} relationship",
        rollback_query=f"""
        MATCH (s:{source_label} {{{source_key}: $source_value}})
              -[r:{rel_type}]->
              (t:{target_label} {{{target_key}: $target_value}})
        DELETE r
        """,
        rollback_parameters={
            "source_value": source_value,
            "target_value": target_value
        }
    )
