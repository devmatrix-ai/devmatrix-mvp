#!/usr/bin/env python3
"""
Neo4j Backup Script
====================
Creates a full backup of Neo4j database via Cypher export.

Usage:
    python scripts/migrations/neo4j/backup_neo4j.py

Output:
    backups/neo4j_backup_YYYYMMDD_HHMMSS.cypher

Date: 2025-11-29
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from neo4j import GraphDatabase


class Neo4jBackup:
    """Creates Cypher-based backup of Neo4j database."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )

        # Backup directory
        self.backup_dir = Path(__file__).parent.parent.parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def close(self):
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run_query(self, query: str):
        """Execute a read-only query."""
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def get_all_labels(self):
        """Get all node labels."""
        query = "CALL db.labels() YIELD label RETURN label"
        return [r["label"] for r in self._run_query(query)]

    def get_all_relationship_types(self):
        """Get all relationship types."""
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        return [r["relationshipType"] for r in self._run_query(query)]

    def export_nodes(self, label: str) -> list:
        """Export all nodes of a given label."""
        query = f"""
        MATCH (n:{label})
        RETURN n, id(n) as nodeId
        """
        return self._run_query(query)

    def export_relationships(self) -> list:
        """Export all relationships."""
        query = """
        MATCH (a)-[r]->(b)
        RETURN id(a) as sourceId, id(b) as targetId, type(r) as relType, properties(r) as props
        """
        return self._run_query(query)

    def _escape_value(self, value):
        """Escape value for Cypher."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            return f"'{escaped}'"
        elif isinstance(value, list):
            items = [self._escape_value(v) for v in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            return self._escape_value(str(value))
        else:
            return f"'{str(value)}'"

    def _node_to_cypher(self, node, label: str, node_id: int) -> str:
        """Convert a node to CREATE statement."""
        props = dict(node)
        # Add internal ID for relationship mapping
        props["_backup_id"] = node_id

        prop_parts = []
        for key, value in props.items():
            if value is not None:
                prop_parts.append(f"{key}: {self._escape_value(value)}")

        props_str = ", ".join(prop_parts)
        return f"CREATE (n{node_id}:{label} {{{props_str}}});"

    def _relationship_to_cypher(self, source_id: int, target_id: int, rel_type: str, props: dict) -> str:
        """Convert a relationship to CREATE statement."""
        if props:
            prop_parts = []
            for key, value in props.items():
                if value is not None:
                    prop_parts.append(f"{key}: {self._escape_value(value)}")
            props_str = " {" + ", ".join(prop_parts) + "}" if prop_parts else ""
        else:
            props_str = ""

        return f"MATCH (a {{_backup_id: {source_id}}}), (b {{_backup_id: {target_id}}}) CREATE (a)-[:{rel_type}{props_str}]->(b);"

    def create_backup(self) -> Path:
        """Create full backup file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"neo4j_backup_{timestamp}.cypher"

        print(f"\n{'='*60}")
        print(f"Neo4j Backup")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Output: {backup_file}")
        print(f"{'='*60}\n")

        lines = []
        lines.append(f"// Neo4j Backup - {timestamp}")
        lines.append(f"// Database: {self.database}")
        lines.append(f"// Generated: {datetime.now().isoformat()}")
        lines.append("")
        lines.append("// Clear existing data (optional - uncomment if needed)")
        lines.append("// MATCH (n) DETACH DELETE n;")
        lines.append("")

        # Export nodes
        labels = self.get_all_labels()
        total_nodes = 0

        for label in labels:
            nodes = self.export_nodes(label)
            if nodes:
                lines.append(f"// {label} nodes ({len(nodes)})")
                for record in nodes:
                    node = record["n"]
                    node_id = record["nodeId"]
                    lines.append(self._node_to_cypher(node, label, node_id))
                lines.append("")
                total_nodes += len(nodes)
                print(f"  ✅ {label}: {len(nodes)} nodes")

        # Export relationships
        lines.append("// Relationships")
        rels = self.export_relationships()
        for rel in rels:
            lines.append(self._relationship_to_cypher(
                rel["sourceId"],
                rel["targetId"],
                rel["relType"],
                rel["props"]
            ))

        print(f"  ✅ Relationships: {len(rels)}")

        # Cleanup backup IDs
        lines.append("")
        lines.append("// Cleanup backup IDs")
        lines.append("MATCH (n) WHERE exists(n._backup_id) REMOVE n._backup_id;")

        # Write file
        with open(backup_file, 'w') as f:
            f.write("\n".join(lines))

        print(f"\n{'='*60}")
        print(f"✅ BACKUP COMPLETE")
        print(f"   Nodes: {total_nodes}")
        print(f"   Relationships: {len(rels)}")
        print(f"   File: {backup_file}")
        print(f"   Size: {backup_file.stat().st_size / 1024:.1f} KB")
        print(f"{'='*60}\n")

        return backup_file


def main():
    """Main entry point."""
    with Neo4jBackup() as backup:
        backup_file = backup.create_backup()
        print(f"Backup saved to: {backup_file}")


if __name__ == "__main__":
    main()
