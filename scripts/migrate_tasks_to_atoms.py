#!/usr/bin/env python3
"""
Data Migration Script: MVP Tasks → MGE V2 Atomic Units

Migrates existing MasterPlanTask data to AtomicUnit format.

Strategy:
- Phase 1 (Simple): 1:1 conversion (1 task → 1 atom)
- Phase 2 (Full): Actual decomposition (1 task → N atoms)

Usage:
    python scripts/migrate_tasks_to_atoms.py --dry-run
    python scripts/migrate_tasks_to_atoms.py --production

Author: DevMatrix Team
Date: 2025-10-23
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Add src to path
sys.path.insert(0, "/home/kwar/code/agentic-ai")

from src.config.database import get_db
from src.models import (
    MasterPlan,
    MasterPlanTask,
    AtomicUnit,
    AtomStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskToAtomMigrator:
    """Migrates MVP tasks to MGE V2 atomic units"""

    def __init__(self, db: Session, dry_run: bool = True):
        self.db = db
        self.dry_run = dry_run
        self.stats = {
            "masterplans_found": 0,
            "tasks_found": 0,
            "atoms_created": 0,
            "errors": 0,
        }

    def migrate_all(self) -> Dict:
        """
        Main migration entrypoint

        Returns:
            Dict with migration statistics
        """
        logger.info("=" * 80)
        logger.info("MGE V2 Data Migration: Tasks → Atomic Units")
        logger.info("=" * 80)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info("")

        try:
            # Step 1: Load all masterplans
            masterplans = self.load_masterplans()
            self.stats["masterplans_found"] = len(masterplans)
            logger.info(f"Found {len(masterplans)} masterplans")

            # Step 2: Migrate each masterplan
            for masterplan in masterplans:
                self.migrate_masterplan(masterplan)

            # Step 3: Validate integrity
            if not self.dry_run:
                self.validate_migration()

            # Summary
            self.print_summary()

            return self.stats

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.stats["errors"] += 1
            raise

    def load_masterplans(self) -> List[MasterPlan]:
        """Load all masterplans from database"""
        return self.db.query(MasterPlan).all()

    def migrate_masterplan(self, masterplan: MasterPlan) -> None:
        """
        Migrate all tasks in a masterplan to atoms

        Phase 1 strategy: 1:1 conversion (simple placeholder)
        - 1 task → 1 atom
        - Preserve all task metadata
        - Set v2_mode = True on masterplan
        """
        logger.info(f"\nMigrating MasterPlan: {masterplan.project_name}")
        logger.info(f"  ID: {masterplan.masterplan_id}")

        # Load tasks for this masterplan
        tasks = self.load_masterplan_tasks(masterplan.masterplan_id)
        self.stats["tasks_found"] += len(tasks)
        logger.info(f"  Found {len(tasks)} tasks")

        # Convert each task to atom
        atom_number = 1
        for task in tasks:
            atom = self.task_to_atom(masterplan, task, atom_number)

            if not self.dry_run:
                self.db.add(atom)
                self.db.flush()  # Get atom_id

            self.stats["atoms_created"] += 1
            atom_number += 1

            logger.info(f"    ✓ Task #{task.task_number} → Atom #{atom.atom_number}")

        # Update masterplan V2 metadata
        if not self.dry_run:
            masterplan.v2_mode = True
            masterplan.total_atoms = len(tasks)
            masterplan.atomization_config = {
                "strategy": "simple_1_to_1",
                "migrated_at": datetime.utcnow().isoformat(),
                "original_tasks": len(tasks),
            }
            self.db.commit()

        logger.info(f"  ✓ Migrated {len(tasks)} tasks → {len(tasks)} atoms")

    def load_masterplan_tasks(self, masterplan_id) -> List[MasterPlanTask]:
        """Load all tasks for a masterplan"""
        # Join through phases and milestones to get all tasks
        from src.models import MasterPlanPhase, MasterPlanMilestone

        tasks = (
            self.db.query(MasterPlanTask)
            .join(MasterPlanMilestone)
            .join(MasterPlanPhase)
            .filter(MasterPlanPhase.masterplan_id == masterplan_id)
            .order_by(MasterPlanTask.task_number)
            .all()
        )

        return tasks

    def task_to_atom(
        self,
        masterplan: MasterPlan,
        task: MasterPlanTask,
        atom_number: int
    ) -> AtomicUnit:
        """
        Convert a single task to an atomic unit

        Phase 1: Simple 1:1 conversion
        - Copy task data to atom fields
        - Estimate LOC and complexity
        - Set placeholder context
        """
        # Estimate LOC (rough estimate from task description)
        estimated_loc = self._estimate_loc(task)

        # Estimate complexity (rough estimate from task complexity)
        estimated_complexity = self._estimate_complexity(task)

        # Extract language from target files (default to Python)
        language = self._detect_language(task)

        # Create atomic unit
        atom = AtomicUnit(
            masterplan_id=masterplan.masterplan_id,
            task_id=task.task_id,  # Link to original task for traceability
            atom_number=atom_number,
            name=task.name,
            description=task.description,

            # Code fields
            code_to_generate=f"# Placeholder code from task #{task.task_number}\n# {task.description}",
            file_path=task.target_files[0] if task.target_files else None,
            language=language,
            loc=estimated_loc,
            complexity=estimated_complexity,

            # Context (placeholder)
            imports={"placeholder": True},
            type_schema={"placeholder": True},
            preconditions={},
            postconditions={},
            test_cases=[],
            context_completeness=0.5,  # Placeholder context, needs real atomization

            # Atomicity (assume valid for now)
            atomicity_score=0.7,
            is_atomic=True,

            # Execution state (copy from task)
            status=self._map_task_status(task.status),
            attempts=task.retry_count,
            max_attempts=3,  # V2 default

            # Confidence (medium confidence for migrated data)
            confidence_score=0.6,
            needs_review=False,

            # Timestamps
            created_at=task.created_at,
            updated_at=datetime.utcnow(),
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

        return atom

    def _estimate_loc(self, task: MasterPlanTask) -> int:
        """
        Estimate lines of code from task

        Simple heuristic:
        - LOW complexity: ~10 LOC
        - MEDIUM complexity: ~25 LOC
        - HIGH complexity: ~50 LOC
        - CRITICAL complexity: ~100 LOC
        """
        from src.models import TaskComplexity

        loc_map = {
            TaskComplexity.LOW: 10,
            TaskComplexity.MEDIUM: 25,
            TaskComplexity.HIGH: 50,
            TaskComplexity.CRITICAL: 100,
        }

        return loc_map.get(task.complexity, 25)

    def _estimate_complexity(self, task: MasterPlanTask) -> float:
        """
        Estimate cyclomatic complexity

        Simple mapping:
        - LOW: 1.5
        - MEDIUM: 2.5
        - HIGH: 4.0
        - CRITICAL: 6.0
        """
        from src.models import TaskComplexity

        complexity_map = {
            TaskComplexity.LOW: 1.5,
            TaskComplexity.MEDIUM: 2.5,
            TaskComplexity.HIGH: 4.0,
            TaskComplexity.CRITICAL: 6.0,
        }

        return complexity_map.get(task.complexity, 2.5)

    def _detect_language(self, task: MasterPlanTask) -> str:
        """Detect language from target files"""
        if not task.target_files:
            return "python"

        file_path = task.target_files[0]

        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        else:
            return "python"  # Default

    def _map_task_status(self, task_status) -> AtomStatus:
        """Map MVP TaskStatus to V2 AtomStatus"""
        from src.models import TaskStatus

        status_map = {
            TaskStatus.PENDING: AtomStatus.PENDING,
            TaskStatus.READY: AtomStatus.READY,
            TaskStatus.IN_PROGRESS: AtomStatus.RUNNING,
            TaskStatus.VALIDATING: AtomStatus.RUNNING,
            TaskStatus.COMPLETED: AtomStatus.COMPLETED,
            TaskStatus.FAILED: AtomStatus.FAILED,
            TaskStatus.SKIPPED: AtomStatus.SKIPPED,
            TaskStatus.BLOCKED: AtomStatus.BLOCKED,
        }

        return status_map.get(task_status, AtomStatus.PENDING)

    def validate_migration(self) -> None:
        """Validate migration data integrity"""
        logger.info("\n" + "=" * 80)
        logger.info("Validating Migration")
        logger.info("=" * 80)

        # Check 1: All tasks have corresponding atoms
        total_tasks = self.db.query(MasterPlanTask).count()
        total_atoms = self.db.query(AtomicUnit).count()

        logger.info(f"Tasks: {total_tasks}")
        logger.info(f"Atoms: {total_atoms}")

        if total_tasks > 0 and total_atoms >= total_tasks:
            logger.info("✓ All tasks have atoms")
        else:
            logger.warning(f"⚠ Mismatch: {total_tasks} tasks but {total_atoms} atoms")

        # Check 2: All V2 masterplans have atoms
        v2_masterplans = self.db.query(MasterPlan).filter(MasterPlan.v2_mode == True).all()
        for mp in v2_masterplans:
            atom_count = self.db.query(AtomicUnit).filter(AtomicUnit.masterplan_id == mp.masterplan_id).count()
            if atom_count > 0:
                logger.info(f"✓ MasterPlan {mp.project_name}: {atom_count} atoms")
            else:
                logger.warning(f"⚠ MasterPlan {mp.project_name}: No atoms!")

        logger.info("✓ Validation complete")

    def print_summary(self) -> None:
        """Print migration summary"""
        logger.info("\n" + "=" * 80)
        logger.info("Migration Summary")
        logger.info("=" * 80)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"MasterPlans: {self.stats['masterplans_found']}")
        logger.info(f"Tasks: {self.stats['tasks_found']}")
        logger.info(f"Atoms created: {self.stats['atoms_created']}")
        logger.info(f"Errors: {self.stats['errors']}")

        if self.dry_run:
            logger.info("\n⚠️  DRY RUN - No data was written to database")
            logger.info("Run with --production to execute migration")
        else:
            logger.info("\n✓ Migration complete!")

        logger.info("=" * 80)


def main():
    """Main CLI entrypoint"""
    parser = argparse.ArgumentParser(
        description="Migrate MVP tasks to MGE V2 atomic units"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without writing to database"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Execute production migration (writes to database)"
    )

    args = parser.parse_args()

    # Validate args
    if not args.dry_run and not args.production:
        logger.error("Must specify either --dry-run or --production")
        sys.exit(1)

    if args.dry_run and args.production:
        logger.error("Cannot specify both --dry-run and --production")
        sys.exit(1)

    # Get database session
    db = next(get_db())

    try:
        # Run migration
        migrator = TaskToAtomMigrator(db, dry_run=args.dry_run)
        stats = migrator.migrate_all()

        # Exit with success
        sys.exit(0 if stats["errors"] == 0 else 1)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
