#!/usr/bin/env python3
"""
Migration 010: Create BehaviorModel Cross-IR Relationships
===========================================================
Sprint: 3 Preparation
Date: 2025-11-29

Creates:
- TARGETS_ENTITY (Step → Entity) - inferred from step.target_entity
- CALLS_ENDPOINT (Step → Endpoint) - inferred from action + entity
- Invariant nodes from BehaviorModelIR.invariants
- HAS_INVARIANT (BehaviorModelIR → Invariant)
- APPLIES_TO (Invariant → Entity)
- CHECKS_ATTRIBUTE (Invariant → Attribute) - inferred from expression

Schema version: 5 → 6
"""

import sys
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from neo4j import GraphDatabase
from src.cognitive.config.settings import settings


class BehaviorCrossIRRelationships:
    """Creates cross-IR relationships for BehaviorModelIR expansion."""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.database = settings.neo4j_database
        self.migration_id = "010_create_behavior_cross_ir_relationships"
        self.schema_version_before = 5
        self.schema_version_after = 6
        self.stats = {
            "targets_entity_created": 0,
            "calls_endpoint_created": 0,
            "invariants_created": 0,
            "has_invariant_created": 0,
            "applies_to_created": 0,
            "checks_attribute_created": 0,
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
            # Step 1: Create TARGETS_ENTITY relationships
            print("\n[1/5] Creating TARGETS_ENTITY (Step → Entity)...")
            self._create_step_targets_entity(session, dry_run)

            # Step 2: Create CALLS_ENDPOINT relationships
            print("\n[2/5] Creating CALLS_ENDPOINT (Step → Endpoint)...")
            self._create_step_calls_endpoint(session, dry_run)

            # Step 3: Create Invariant nodes
            print("\n[3/5] Creating Invariant nodes...")
            self._create_invariant_nodes(session, dry_run)

            # Step 4: Create APPLIES_TO relationships
            print("\n[4/5] Creating APPLIES_TO (Invariant → Entity)...")
            self._create_applies_to(session, dry_run)

            # Step 5: Create CHECKS_ATTRIBUTE relationships
            print("\n[5/5] Creating CHECKS_ATTRIBUTE (Invariant → Attribute)...")
            self._create_checks_attribute(session, dry_run)

            # Update schema version
            if not dry_run:
                self._update_schema_version(session)
                self._record_migration(session)

        return self._generate_report(dry_run)

    def _create_step_targets_entity(self, session, dry_run: bool):
        """Create TARGETS_ENTITY relationships from Step.target_entity to Entity."""
        # Get steps with target_entity that don't have TARGETS_ENTITY relationship yet
        query = """
        MATCH (s:Step)
        WHERE s.target_entity IS NOT NULL
          AND s.target_entity <> ''
          AND NOT (s)-[:TARGETS_ENTITY]->(:Entity)
        RETURN s.step_id as step_id,
               s.target_entity as target_entity,
               s.action as action,
               s.flow_id as flow_id
        """
        result = session.run(query)
        steps = list(result)

        if dry_run:
            print(f"      Would process {len(steps)} steps with target_entity")
            # Count how many would match
            matched = 0
            for step in steps:
                check_query = """
                MATCH (e:Entity)
                WHERE toLower(e.name) = toLower($target_entity)
                RETURN count(e) as count
                """
                check_result = session.run(check_query, {"target_entity": step["target_entity"]})
                if check_result.single()["count"] > 0:
                    matched += 1
            print(f"      Would create ~{matched} TARGETS_ENTITY relationships")
            self.stats["targets_entity_created"] = matched
            return

        created = 0
        for step in steps:
            # Find matching Entity (case-insensitive match within same app)
            app_id = step["flow_id"].split("|")[0] if "|" in step["flow_id"] else None

            create_query = """
            MATCH (s:Step {step_id: $step_id})
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($target_entity)
            MERGE (s)-[r:TARGETS_ENTITY]->(e)
            ON CREATE SET
                r.operation = $operation,
                r.role = 'primary',
                r.confidence = 1.0,
                r.inference_method = 'explicit',
                r.created_at = datetime()
            RETURN count(r) as created
            """

            # Infer operation from action
            action = step["action"].lower() if step["action"] else ""
            operation = "read"
            if any(w in action for w in ["create", "add", "insert", "new"]):
                operation = "create"
            elif any(w in action for w in ["update", "modify", "edit", "change"]):
                operation = "update"
            elif any(w in action for w in ["delete", "remove", "destroy"]):
                operation = "delete"

            result = session.run(create_query, {
                "step_id": step["step_id"],
                "target_entity": step["target_entity"],
                "operation": operation
            })

            record = result.single()
            if record and record["created"] > 0:
                created += 1

        self.stats["targets_entity_created"] = created
        print(f"      Created {created} TARGETS_ENTITY relationships")

    def _create_step_calls_endpoint(self, session, dry_run: bool):
        """Create CALLS_ENDPOINT relationships by inferring from action + entity."""
        # Get steps that have target_entity and might map to endpoints
        query = """
        MATCH (s:Step)
        WHERE s.target_entity IS NOT NULL
          AND s.target_entity <> ''
          AND s.action IS NOT NULL
          AND NOT (s)-[:CALLS_ENDPOINT]->(:Endpoint)
        RETURN s.step_id as step_id,
               s.target_entity as target_entity,
               s.action as action,
               s.flow_id as flow_id
        """
        result = session.run(query)
        steps = list(result)

        if dry_run:
            print(f"      Would analyze {len(steps)} steps for endpoint matching")
            self.stats["calls_endpoint_created"] = len(steps) // 3  # Rough estimate
            return

        created = 0
        for step in steps:
            # Map action to HTTP method
            action = step["action"].lower() if step["action"] else ""
            methods = []
            if any(w in action for w in ["create", "add", "insert", "new"]):
                methods = ["POST"]
            elif any(w in action for w in ["update", "modify", "edit"]):
                methods = ["PUT", "PATCH"]
            elif any(w in action for w in ["delete", "remove"]):
                methods = ["DELETE"]
            elif any(w in action for w in ["get", "fetch", "read", "list", "show"]):
                methods = ["GET"]
            else:
                methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]  # Try all

            # Find matching endpoint by entity name in path
            entity = step["target_entity"].lower()
            entity_plural = entity + "s" if not entity.endswith("s") else entity

            create_query = """
            MATCH (s:Step {step_id: $step_id})
            MATCH (e:Endpoint)
            WHERE (toLower(e.path) CONTAINS $entity OR toLower(e.path) CONTAINS $entity_plural)
              AND e.method IN $methods
            WITH s, e
            LIMIT 1
            MERGE (s)-[r:CALLS_ENDPOINT]->(e)
            ON CREATE SET
                r.sequence = 1,
                r.conditional = false,
                r.confidence = 0.7,
                r.inference_method = 'action_matching',
                r.created_at = datetime()
            RETURN count(r) as created
            """

            result = session.run(create_query, {
                "step_id": step["step_id"],
                "entity": entity,
                "entity_plural": entity_plural,
                "methods": methods
            })

            record = result.single()
            if record and record["created"] > 0:
                created += 1

        self.stats["calls_endpoint_created"] = created
        print(f"      Created {created} CALLS_ENDPOINT relationships")

    def _create_invariant_nodes(self, session, dry_run: bool):
        """Create Invariant nodes from BehaviorModelIR.invariants data."""
        # Get BehaviorModelIR nodes with invariants
        query = """
        MATCH (b:BehaviorModelIR)
        WHERE b.invariants IS NOT NULL AND b.invariants <> '[]'
        RETURN b.app_id as app_id, b.invariants as invariants_json
        """
        result = session.run(query)
        behavior_models = list(result)

        total_invariants = 0
        for bm in behavior_models:
            invariants_json = bm.get("invariants_json")
            if not invariants_json:
                continue

            try:
                invariants = json.loads(invariants_json) if isinstance(invariants_json, str) else invariants_json
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(invariants, list):
                continue

            app_id = bm["app_id"]

            for invariant in invariants:
                if not isinstance(invariant, dict):
                    continue

                entity = invariant.get("entity", "unknown")
                description = invariant.get("description", "")

                # Create hash for uniqueness
                inv_hash = hash(f"{entity}:{description}")
                invariant_id = f"{app_id}|invariant|{entity}|{abs(inv_hash) % 10000}"

                if dry_run:
                    total_invariants += 1
                    continue

                # Create Invariant node
                create_query = """
                MATCH (b:BehaviorModelIR {app_id: $app_id})
                MERGE (i:Invariant {invariant_id: $invariant_id})
                ON CREATE SET
                    i.entity = $entity,
                    i.description = $description,
                    i.expression = $expression,
                    i.enforcement_level = $enforcement_level,
                    i.behavior_model_id = $app_id,
                    i.created_at = datetime(),
                    i.updated_at = datetime(),
                    i.schema_version = $schema_version
                MERGE (b)-[:HAS_INVARIANT {created_at: datetime()}]->(i)
                RETURN i.invariant_id as created_id
                """
                result = session.run(create_query, {
                    "app_id": app_id,
                    "invariant_id": invariant_id,
                    "entity": entity,
                    "description": description,
                    "expression": invariant.get("expression"),
                    "enforcement_level": invariant.get("enforcement_level", "strict"),
                    "schema_version": self.schema_version_after
                })

                if result.single():
                    total_invariants += 1

        if dry_run:
            print(f"      Would create {total_invariants} Invariant nodes")
        else:
            print(f"      Created {total_invariants} Invariant nodes")

        self.stats["invariants_created"] = total_invariants
        self.stats["has_invariant_created"] = total_invariants

    def _create_applies_to(self, session, dry_run: bool):
        """Create APPLIES_TO relationships from Invariant.entity to Entity."""
        query = """
        MATCH (i:Invariant)
        WHERE i.entity IS NOT NULL
          AND NOT (i)-[:APPLIES_TO]->(:Entity)
        RETURN i.invariant_id as invariant_id, i.entity as entity
        """
        result = session.run(query)
        invariants = list(result)

        if dry_run:
            print(f"      Would process {len(invariants)} invariants")
            self.stats["applies_to_created"] = len(invariants)
            return

        created = 0
        for inv in invariants:
            create_query = """
            MATCH (i:Invariant {invariant_id: $invariant_id})
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($entity)
            MERGE (i)-[r:APPLIES_TO]->(e)
            ON CREATE SET
                r.scope = 'global',
                r.created_at = datetime()
            RETURN count(r) as created
            """
            result = session.run(create_query, {
                "invariant_id": inv["invariant_id"],
                "entity": inv["entity"]
            })

            record = result.single()
            if record and record["created"] > 0:
                created += 1

        self.stats["applies_to_created"] = created
        print(f"      Created {created} APPLIES_TO relationships")

    def _create_checks_attribute(self, session, dry_run: bool):
        """Create CHECKS_ATTRIBUTE relationships by parsing invariant expressions."""
        query = """
        MATCH (i:Invariant)-[:APPLIES_TO]->(e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
        WHERE i.expression IS NOT NULL
          AND toLower(i.expression) CONTAINS toLower(a.name)
          AND NOT (i)-[:CHECKS_ATTRIBUTE]->(a)
        RETURN i.invariant_id as invariant_id,
               a.attribute_id as attribute_id,
               a.name as attr_name,
               i.expression as expression
        """
        result = session.run(query)
        matches = list(result)

        if dry_run:
            print(f"      Would create {len(matches)} CHECKS_ATTRIBUTE relationships")
            self.stats["checks_attribute_created"] = len(matches)
            return

        created = 0
        for match in matches:
            # Extract operator from expression
            expression = match["expression"]
            attr_name = match["attr_name"]
            operator = self._extract_operator(expression, attr_name)

            create_query = """
            MATCH (i:Invariant {invariant_id: $invariant_id})
            MATCH (a:Attribute {attribute_id: $attribute_id})
            MERGE (i)-[r:CHECKS_ATTRIBUTE]->(a)
            ON CREATE SET
                r.expression = $expression,
                r.operator = $operator,
                r.created_at = datetime()
            RETURN count(r) as created
            """
            result = session.run(create_query, {
                "invariant_id": match["invariant_id"],
                "attribute_id": match["attribute_id"],
                "expression": expression,
                "operator": operator
            })

            record = result.single()
            if record and record["created"] > 0:
                created += 1

        self.stats["checks_attribute_created"] = created
        print(f"      Created {created} CHECKS_ATTRIBUTE relationships")

    def _extract_operator(self, expression: str, attr_name: str) -> str:
        """Extract operator from expression for a given attribute."""
        # Common patterns: "balance >= 0", "status IN ['active']", "price > 0"
        operators = [">=", "<=", "!=", "==", ">", "<", "IN", "NOT IN", "IS NOT NULL", "IS NULL"]

        # Find attribute in expression and look for operator nearby
        expr_lower = expression.lower()
        attr_lower = attr_name.lower()

        idx = expr_lower.find(attr_lower)
        if idx == -1:
            return "unknown"

        # Look at text after attribute name
        after_attr = expression[idx + len(attr_name):].strip()

        for op in operators:
            if after_attr.upper().startswith(op):
                return op

        return "expression"

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
        print(f"TARGETS_ENTITY created: {self.stats['targets_entity_created']}")
        print(f"CALLS_ENDPOINT created: {self.stats['calls_endpoint_created']}")
        print(f"Invariant nodes created: {self.stats['invariants_created']}")
        print(f"HAS_INVARIANT relationships: {self.stats['has_invariant_created']}")
        print(f"APPLIES_TO created: {self.stats['applies_to_created']}")
        print(f"CHECKS_ATTRIBUTE created: {self.stats['checks_attribute_created']}")
        print(f"{'='*60}")

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migration 010: Create BehaviorModel Cross-IR Relationships")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    args = parser.parse_args()

    migration = BehaviorCrossIRRelationships()
    try:
        report = migration.run(dry_run=args.dry_run)
        return 0 if report else 1
    finally:
        migration.close()


if __name__ == "__main__":
    sys.exit(main())
