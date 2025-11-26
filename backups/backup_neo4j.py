#!/usr/bin/env python3
"""
Neo4j Hot Backup Script
Exports all patterns and relationships to JSON without stopping the database
"""
import json
from datetime import datetime
from pathlib import Path

from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient


def backup_neo4j():
    """Create a full backup of Neo4j patterns and relationships"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("/home/kwar/code/agentic-ai/backups")
    backup_file = backup_dir / f"neo4j_full_backup_{timestamp}.json"

    client = Neo4jPatternClient()
    client.connect()

    print(f"🔄 Starting Neo4j backup to {backup_file}")

    # Export all patterns
    print("📦 Exporting Pattern nodes...")
    patterns_query = """
    MATCH (p:Pattern)
    RETURN p, id(p) as node_id
    """
    patterns_result = client._execute_query(patterns_query)

    patterns = []
    for record in patterns_result:
        pattern_dict = dict(record['p'])
        pattern_dict['_node_id'] = record['node_id']
        patterns.append(pattern_dict)

    print(f"✅ Exported {len(patterns)} patterns")

    # Export all other nodes (Tag, Category, etc.)
    print("🏷️  Exporting other nodes (Tags, Categories, etc.)...")
    other_nodes_query = """
    MATCH (n)
    WHERE NOT n:Pattern
    RETURN labels(n) as labels, n, id(n) as node_id
    """
    other_nodes_result = client._execute_query(other_nodes_query)

    other_nodes = []
    for record in other_nodes_result:
        node_dict = dict(record['n'])
        node_dict['_node_id'] = record['node_id']
        node_dict['_labels'] = record['labels']
        other_nodes.append(node_dict)

    print(f"✅ Exported {len(other_nodes)} other nodes")

    # Export all relationships (with batching to handle large counts)
    print("🔗 Exporting ALL relationships...")

    # First get total count
    count_query = "MATCH ()-[r]->() RETURN count(r) as total"
    total_rels = client._execute_query(count_query)[0]['total']
    print(f"  📊 Total relationships to export: {total_rels:,}")

    relationships = []
    batch_size = 10000
    skip = 0

    while skip < total_rels:
        relationships_query = f"""
        MATCH (n1)-[r]->(n2)
        RETURN type(r) as rel_type,
               labels(n1) as from_labels,
               labels(n2) as to_labels,
               id(startNode(r)) as from_id,
               id(endNode(r)) as to_id,
               properties(r) as props
        SKIP {skip} LIMIT {batch_size}
        """
        batch_result = client._execute_query(relationships_query)

        for record in batch_result:
            rel_dict = {
                'type': record['rel_type'],
                'from_node_id': record['from_id'],
                'from_labels': record['from_labels'],
                'to_node_id': record['to_id'],
                'to_labels': record['to_labels'],
                'properties': dict(record['props']) if record['props'] else {}
            }
            relationships.append(rel_dict)

        skip += batch_size
        if skip % 50000 == 0:
            print(f"  ⏳ Exported {len(relationships):,} relationships...")

    print(f"✅ Exported {len(relationships):,} relationships (verified: {len(relationships) == total_rels})")

    # Export constraints and indexes
    print("🔍 Exporting constraints and indexes...")
    constraints_query = "SHOW CONSTRAINTS"
    indexes_query = "SHOW INDEXES"

    try:
        constraints = [dict(record) for record in client._execute_query(constraints_query)]
        indexes = [dict(record) for record in client._execute_query(indexes_query)]
    except Exception as e:
        print(f"⚠️  Could not export constraints/indexes: {e}")
        constraints = []
        indexes = []

    # Create backup structure
    backup_data = {
        'metadata': {
            'timestamp': timestamp,
            'backup_date': datetime.now().isoformat(),
            'neo4j_version': 'unknown',
            'total_patterns': len(patterns),
            'total_other_nodes': len(other_nodes),
            'total_relationships': len(relationships),
            'total_constraints': len(constraints),
            'total_indexes': len(indexes)
        },
        'patterns': patterns,
        'other_nodes': other_nodes,
        'relationships': relationships,
        'constraints': constraints,
        'indexes': indexes
    }

    # Write to file
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)

    file_size = backup_file.stat().st_size / (1024 * 1024)  # MB

    print(f"\n✅ Neo4j backup completed successfully!")
    print(f"📁 File: {backup_file}")
    print(f"💾 Size: {file_size:.2f} MB")
    print(f"📊 Patterns: {len(patterns):,}")
    print(f"🏷️  Other nodes: {len(other_nodes):,}")
    print(f"🔗 Relationships: {len(relationships):,}")

    client.close()
    return backup_file


if __name__ == "__main__":
    backup_file = backup_neo4j()
    print(f"\n🎉 Backup guardado en: {backup_file}")
