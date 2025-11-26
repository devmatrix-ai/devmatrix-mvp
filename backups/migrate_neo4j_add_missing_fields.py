#!/usr/bin/env python3
"""
Neo4j Migration: Add security_level and performance_tier to existing patterns
Safe additive operation - re-classifies patterns and adds missing fields
"""
from datetime import datetime
from pathlib import Path

from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient
from src.cognitive.patterns.pattern_classifier import PatternClassifier


def migrate_neo4j_add_fields():
    """Add security_level and performance_tier to existing patterns"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path("/home/kwar/code/agentic-ai/backups") / f"neo4j_migration_{timestamp}.log"

    client = Neo4jPatternClient()
    client.connect()
    classifier = PatternClassifier()

    print(f"🔄 Starting Neo4j migration: Adding missing fields")
    print(f"📝 Log file: {log_file}")

    # Get all patterns that need migration
    query = """
    MATCH (p:Pattern)
    WHERE p.security_level IS NULL OR p.performance_tier IS NULL
    RETURN p.pattern_id as pattern_id,
           p.code as code,
           p.description as description,
           id(p) as node_id
    LIMIT 5000
    """

    patterns_to_migrate = client._execute_query(query)
    total = len(patterns_to_migrate)

    print(f"📊 Found {total} patterns needing migration")

    if total == 0:
        print("✅ All patterns already have required fields!")
        client.close()
        return

    # Process in batches
    updated = 0
    errors = 0
    log_entries = []

    for i, record in enumerate(patterns_to_migrate, 1):
        pattern_id = record['pattern_id']
        code = record['code']
        description = record['description'] or ""

        try:
            # Extract name from pattern_id (format: repo_filename_functionname_hash)
            parts = pattern_id.split('_')
            name = parts[-2] if len(parts) > 2 else "unknown"

            # Re-classify pattern
            result = classifier.classify(
                code=code,
                name=name,
                description=description
            )

            # Update Neo4j with new fields
            update_query = """
            MATCH (p:Pattern {pattern_id: $pattern_id})
            SET p.security_level = $security_level,
                p.performance_tier = $performance_tier,
                p.classification_updated_at = $updated_at
            RETURN p.pattern_id as updated_id
            """

            client._execute_query(update_query, {
                'pattern_id': pattern_id,
                'security_level': result.security_level,
                'performance_tier': result.performance_tier,
                'updated_at': datetime.utcnow().isoformat()
            })

            updated += 1
            log_entries.append(f"✅ {pattern_id}: security={result.security_level}, perf={result.performance_tier}")

            if i % 100 == 0:
                print(f"  ⏳ Processed {i}/{total} patterns ({updated} updated, {errors} errors)")

        except Exception as e:
            errors += 1
            log_entries.append(f"❌ {pattern_id}: ERROR - {str(e)}")
            print(f"  ⚠️  Error processing {pattern_id}: {e}")

    # Write log file
    with open(log_file, 'w') as f:
        f.write(f"Neo4j Migration Log - {timestamp}\n")
        f.write(f"Total patterns: {total}\n")
        f.write(f"Updated: {updated}\n")
        f.write(f"Errors: {errors}\n")
        f.write("\nDetails:\n")
        f.write("\n".join(log_entries))

    print(f"\n✅ Neo4j migration completed!")
    print(f"📊 Updated: {updated}/{total}")
    print(f"⚠️  Errors: {errors}/{total}")
    print(f"📝 Log: {log_file}")

    client.close()
    return updated, errors


if __name__ == "__main__":
    updated, errors = migrate_neo4j_add_fields()
    print(f"\n🎉 Migration complete: {updated} patterns updated")
