#!/usr/bin/env python3
"""
Migration 009: Expand BehaviorModelIR Structure
================================================
Sprint: 3 Preparation
Date: 2025-11-29

Creates:
- HAS_BEHAVIOR_MODEL relationships (ApplicationIR → BehaviorModelIR)
- Flow nodes with properties
- HAS_FLOW relationships
- Step nodes with properties
- HAS_STEP relationships with sequence
- Temporal metadata on all new nodes

Schema version: 4 → 5
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from neo4j import GraphDatabase
from src.cognitive.config.settings import settings


class BehaviorModelStructureExpansion:
    """Expands BehaviorModelIR with Flow and Step nodes."""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.database = settings.neo4j_database
        self.migration_id = "009_expand_behavior_model_structure"
        self.schema_version_before = 4
        self.schema_version_after = 5
        self.stats = {
            "has_behavior_model_created": 0,
            "flows_created": 0,
            "has_flow_created": 0,
            "steps_created": 0,
            "has_step_created": 0,
            "temporal_metadata_added": 0,
        }

    def close(self):
        self.driver.close()

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute the migration."""
        print(f"\n{'='*60}")
        print(f"Migration: {self.migration_id}")
        print(f"{'='*60}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"Schema: {self.schema_version_before} → {self.schema_version_after}")

        with self.driver.session(database=self.database) as session:
            # Step 1: Create HAS_BEHAVIOR_MODEL relationships
            print("\n[1/5] Creating HAS_BEHAVIOR_MODEL relationships...")
            self._create_has_behavior_model(session, dry_run)

            # Step 2: Get existing BehaviorModelIR data
            print("\n[2/5] Analyzing existing BehaviorModelIR nodes...")
            behavior_models = self._get_behavior_models_with_data(session)
            print(f"      Found {len(behavior_models)} BehaviorModelIR nodes to process")

            # Step 3: Create Flow nodes
            print("\n[3/5] Creating Flow nodes...")
            self._create_flow_nodes(session, behavior_models, dry_run)

            # Step 4: Create Step nodes
            print("\n[4/5] Creating Step nodes...")
            self._create_step_nodes(session, dry_run)

            # Step 5: Add temporal metadata
            print("\n[5/5] Adding temporal metadata...")
            self._add_temporal_metadata(session, dry_run)

            # Update schema version
            if not dry_run:
                self._update_schema_version(session)
                self._record_migration(session)

        return self._generate_report(dry_run)

    def _create_has_behavior_model(self, session, dry_run: bool):
        """Create HAS_BEHAVIOR_MODEL relationships between ApplicationIR and BehaviorModelIR."""
        query = """
        MATCH (a:ApplicationIR)
        MATCH (b:BehaviorModelIR)
        WHERE b.app_id = a.app_id
          AND NOT (a)-[:HAS_BEHAVIOR_MODEL]->(b)
        RETURN a.app_id as app_id, id(a) as app_node_id, id(b) as behavior_node_id
        """
        result = session.run(query)
        pairs = list(result)

        if dry_run:
            print(f"      Would create {len(pairs)} HAS_BEHAVIOR_MODEL relationships")
            self.stats["has_behavior_model_created"] = len(pairs)
            return

        for pair in pairs:
            create_query = """
            MATCH (a:ApplicationIR) WHERE id(a) = $app_node_id
            MATCH (b:BehaviorModelIR) WHERE id(b) = $behavior_node_id
            CREATE (a)-[:HAS_BEHAVIOR_MODEL {created_at: datetime()}]->(b)
            """
            session.run(create_query, {
                "app_node_id": pair["app_node_id"],
                "behavior_node_id": pair["behavior_node_id"]
            })
            self.stats["has_behavior_model_created"] += 1

        print(f"      Created {self.stats['has_behavior_model_created']} HAS_BEHAVIOR_MODEL relationships")

    def _get_behavior_models_with_data(self, session) -> List[Dict]:
        """Get BehaviorModelIR nodes that have flow/invariant data."""
        query = """
        MATCH (b:BehaviorModelIR)
        WHERE b.flows IS NOT NULL OR b.invariants IS NOT NULL
        RETURN b.app_id as app_id,
               b.app_id as behavior_model_id,
               b.flows as flows_json,
               b.invariants as invariants_json
        """
        result = session.run(query)
        return list(result)

    def _create_flow_nodes(self, session, behavior_models: List[Dict], dry_run: bool):
        """Create Flow nodes from BehaviorModelIR.flows data."""
        import json

        total_flows = 0
        for bm in behavior_models:
            flows_json = bm.get("flows_json")
            if not flows_json:
                continue

            try:
                flows = json.loads(flows_json) if isinstance(flows_json, str) else flows_json
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(flows, list):
                continue

            app_id = bm["app_id"]
            behavior_model_id = bm["behavior_model_id"]

            for flow in flows:
                if not isinstance(flow, dict):
                    continue

                flow_name = flow.get("name", "unnamed")
                flow_id = f"{app_id}|flow|{flow_name}"

                if dry_run:
                    total_flows += 1
                    continue

                # Create Flow node
                create_query = """
                MATCH (b:BehaviorModelIR {app_id: $behavior_model_id})
                MERGE (f:Flow {flow_id: $flow_id})
                ON CREATE SET
                    f.name = $name,
                    f.type = $type,
                    f.trigger = $trigger,
                    f.description = $description,
                    f.behavior_model_id = $behavior_model_id,
                    f.steps_json = $steps_json,
                    f.created_at = datetime(),
                    f.updated_at = datetime(),
                    f.schema_version = $schema_version
                MERGE (b)-[:HAS_FLOW {created_at: datetime()}]->(f)
                RETURN f.flow_id as created_id
                """
                result = session.run(create_query, {
                    "behavior_model_id": behavior_model_id,
                    "flow_id": flow_id,
                    "name": flow_name,
                    "type": flow.get("type", "workflow"),
                    "trigger": flow.get("trigger", ""),
                    "description": flow.get("description"),
                    "steps_json": json.dumps(flow.get("steps", [])),
                    "schema_version": self.schema_version_after
                })

                if result.single():
                    self.stats["flows_created"] += 1
                    self.stats["has_flow_created"] += 1

        if dry_run:
            print(f"      Would create {total_flows} Flow nodes")
            self.stats["flows_created"] = total_flows
            self.stats["has_flow_created"] = total_flows
        else:
            print(f"      Created {self.stats['flows_created']} Flow nodes")
            print(f"      Created {self.stats['has_flow_created']} HAS_FLOW relationships")

    def _create_step_nodes(self, session, dry_run: bool):
        """Create Step nodes from Flow.steps_json data."""
        import json

        # Get all flows with steps
        query = """
        MATCH (f:Flow)
        WHERE f.steps_json IS NOT NULL
        RETURN f.flow_id as flow_id, f.steps_json as steps_json
        """
        result = session.run(query)
        flows = list(result)

        total_steps = 0
        for flow in flows:
            steps_json = flow.get("steps_json")
            if not steps_json:
                continue

            try:
                steps = json.loads(steps_json) if isinstance(steps_json, str) else steps_json
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(steps, list):
                continue

            flow_id = flow["flow_id"]

            for step in steps:
                if not isinstance(step, dict):
                    continue

                order = step.get("order", 0)
                step_id = f"{flow_id}|step|{order}"

                if dry_run:
                    total_steps += 1
                    continue

                # Create Step node
                create_query = """
                MATCH (f:Flow {flow_id: $flow_id})
                MERGE (s:Step {step_id: $step_id})
                ON CREATE SET
                    s.order = $order,
                    s.description = $description,
                    s.action = $action,
                    s.target_entity = $target_entity,
                    s.condition = $condition,
                    s.flow_id = $flow_id,
                    s.created_at = datetime(),
                    s.updated_at = datetime(),
                    s.schema_version = $schema_version
                MERGE (f)-[:HAS_STEP {sequence: $order, created_at: datetime()}]->(s)
                RETURN s.step_id as created_id
                """
                result = session.run(create_query, {
                    "flow_id": flow_id,
                    "step_id": step_id,
                    "order": order,
                    "description": step.get("description", ""),
                    "action": step.get("action", ""),
                    "target_entity": step.get("target_entity"),
                    "condition": step.get("condition"),
                    "schema_version": self.schema_version_after
                })

                if result.single():
                    self.stats["steps_created"] += 1
                    self.stats["has_step_created"] += 1

        if dry_run:
            print(f"      Would create {total_steps} Step nodes")
            self.stats["steps_created"] = total_steps
            self.stats["has_step_created"] = total_steps
        else:
            print(f"      Created {self.stats['steps_created']} Step nodes")
            print(f"      Created {self.stats['has_step_created']} HAS_STEP relationships")

    def _add_temporal_metadata(self, session, dry_run: bool):
        """Add temporal metadata to any nodes missing it."""
        query = """
        MATCH (n)
        WHERE (n:Flow OR n:Step)
          AND (n.created_at IS NULL OR n.updated_at IS NULL)
        SET n.created_at = coalesce(n.created_at, datetime()),
            n.updated_at = coalesce(n.updated_at, datetime()),
            n.schema_version = coalesce(n.schema_version, $schema_version)
        RETURN count(n) as updated_count
        """

        if dry_run:
            check_query = """
            MATCH (n)
            WHERE (n:Flow OR n:Step)
              AND (n.created_at IS NULL OR n.updated_at IS NULL)
            RETURN count(n) as count
            """
            result = session.run(check_query)
            count = result.single()["count"]
            print(f"      Would add temporal metadata to {count} nodes")
            self.stats["temporal_metadata_added"] = count
            return

        result = session.run(query, {"schema_version": self.schema_version_after})
        count = result.single()["updated_count"]
        self.stats["temporal_metadata_added"] = count
        print(f"      Added temporal metadata to {count} nodes")

    def _update_schema_version(self, session):
        """Update GraphSchemaVersion singleton."""
        query = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        SET v.current_version = $new_version,
            v.last_migration = $migration_id,
            v.updated_at = datetime()
        RETURN v.current_version as version
        """
        result = session.run(query, {
            "new_version": self.schema_version_after,
            "migration_id": self.migration_id
        })
        record = result.single()
        print(f"\n      Schema version updated to: {record['version']}")

    def _record_migration(self, session):
        """Record this migration run."""
        query = """
        CREATE (m:MigrationRun {
            migration_id: $migration_id,
            executed_at: datetime(),
            schema_version_before: $version_before,
            schema_version_after: $version_after,
            stats: $stats,
            status: 'SUCCESS'
        })
        WITH m
        MATCH (v:GraphSchemaVersion {singleton: true})
        CREATE (m)-[:RESULTED_IN_VERSION]->(v)
        RETURN m.migration_id as id
        """
        import json
        session.run(query, {
            "migration_id": self.migration_id,
            "version_before": self.schema_version_before,
            "version_after": self.schema_version_after,
            "stats": json.dumps(self.stats)
        })
        print(f"      Migration recorded: {self.migration_id}")

    def _generate_report(self, dry_run: bool) -> Dict[str, Any]:
        """Generate migration report."""
        report = {
            "migration_id": self.migration_id,
            "dry_run": dry_run,
            "schema_version_before": self.schema_version_before,
            "schema_version_after": self.schema_version_after,
            "stats": self.stats,
            "executed_at": datetime.now().isoformat()
        }

        print(f"\n{'='*60}")
        print("MIGRATION REPORT")
        print(f"{'='*60}")
        print(f"HAS_BEHAVIOR_MODEL created: {self.stats['has_behavior_model_created']}")
        print(f"Flow nodes created: {self.stats['flows_created']}")
        print(f"HAS_FLOW relationships: {self.stats['has_flow_created']}")
        print(f"Step nodes created: {self.stats['steps_created']}")
        print(f"HAS_STEP relationships: {self.stats['has_step_created']}")
        print(f"Temporal metadata added: {self.stats['temporal_metadata_added']}")
        print(f"{'='*60}")

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migration 009: Expand BehaviorModelIR Structure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    args = parser.parse_args()

    migration = BehaviorModelStructureExpansion()
    try:
        report = migration.run(dry_run=args.dry_run)
        return 0 if report else 1
    finally:
        migration.close()


if __name__ == "__main__":
    sys.exit(main())
