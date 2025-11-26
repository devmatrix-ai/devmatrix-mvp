#!/usr/bin/env python3
"""
Qdrant Migration: Enrich legacy patterns with full metadata
Adds category, classification_confidence, and other missing fields to 30K+ legacy patterns
"""
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient
from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient
from src.cognitive.patterns.pattern_classifier import PatternClassifier


def migrate_qdrant_enrich_metadata():
    """Enrich legacy Qdrant patterns with full metadata from Neo4j + re-classification"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path("/home/kwar/code/agentic-ai/backups") / f"qdrant_migration_{timestamp}.log"

    qdrant_client = QdrantClient(host='localhost', port=6333)
    neo4j_client = Neo4jPatternClient()
    neo4j_client.connect()
    classifier = PatternClassifier()

    print(f"🔄 Starting Qdrant migration: Enriching legacy patterns")
    print(f"📝 Log file: {log_file}")

    collection_name = 'semantic_patterns'

    # Check how many patterns need enrichment
    sample = qdrant_client.scroll(
        collection_name=collection_name,
        limit=1,
        with_payload=True,
        with_vectors=False
    )[0]

    if sample:
        payload = sample[0].payload
        fields = set(payload.keys())
        print(f"📋 Current fields in collection: {fields}")

        if 'category' in fields and 'classification_confidence' in fields:
            print("✅ Patterns already have rich metadata!")
            neo4j_client.close()
            return 0, 0

    # Process patterns in batches
    updated = 0
    errors = 0
    log_entries = []
    offset = None
    batch_size = 100
    max_to_process = 30126  # Process ALL patterns

    print(f"📊 Processing first {max_to_process} patterns (test batch)...")

    while updated < max_to_process:
        # Scroll through Qdrant patterns
        patterns, next_offset = qdrant_client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        if not patterns:
            break

        for pattern in patterns:
            if updated >= max_to_process:
                break

            point_id = pattern.id
            payload = pattern.payload
            pattern_id = payload.get('pattern_id')

            try:
                # Get full data from Neo4j
                neo4j_query = """
                MATCH (p:Pattern {pattern_id: $pattern_id})
                RETURN p.code as code,
                       p.description as description,
                       p.category as category,
                       p.classification_confidence as classification_confidence,
                       p.purpose as purpose,
                       p.intent as intent,
                       p.domain as domain,
                       p.success_rate as success_rate,
                       p.usage_count as usage_count,
                       p.semantic_hash as semantic_hash
                """

                neo4j_data = neo4j_client._execute_query(neo4j_query, {'pattern_id': pattern_id})

                if not neo4j_data:
                    errors += 1
                    log_entries.append(f"⚠️  {pattern_id}: Not found in Neo4j")
                    continue

                neo4j_pattern = neo4j_data[0]

                # If category is missing, re-classify
                if not neo4j_pattern.get('category'):
                    code = neo4j_pattern['code']
                    description = neo4j_pattern['description'] or ""
                    parts = pattern_id.split('_')
                    name = parts[-2] if len(parts) > 2 else "unknown"

                    result = classifier.classify(code=code, name=name, description=description)
                    category = result.category
                    confidence = result.confidence
                else:
                    category = neo4j_pattern['category']
                    confidence = neo4j_pattern.get('classification_confidence', 0.5)

                # Build enriched payload (with safe type conversions)
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_int(value, default=0):
                    try:
                        return int(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default

                enriched_payload = {
                    'pattern_id': pattern_id,
                    'description': neo4j_pattern.get('description') or payload.get('description', ''),
                    'file_path': payload.get('file_path', ''),
                    'purpose': neo4j_pattern.get('purpose') or '',
                    'intent': neo4j_pattern.get('intent') or '',
                    'domain': neo4j_pattern.get('domain') or '',
                    'category': category or 'unknown',
                    'classification_confidence': safe_float(confidence, 0.5),
                    'code': neo4j_pattern.get('code') or '',
                    'success_rate': safe_float(neo4j_pattern.get('success_rate'), 0.0),
                    'usage_count': safe_int(neo4j_pattern.get('usage_count'), 0),
                    'created_at': datetime.utcnow().isoformat(),
                    'semantic_hash': neo4j_pattern.get('semantic_hash') or ''
                }

                # Update Qdrant payload
                qdrant_client.set_payload(
                    collection_name=collection_name,
                    payload=enriched_payload,
                    points=[point_id]
                )

                updated += 1
                log_entries.append(f"✅ {pattern_id}: Added {len(enriched_payload)} fields (category={category})")

            except Exception as e:
                errors += 1
                log_entries.append(f"❌ {pattern_id}: ERROR - {str(e)}")
                print(f"  ⚠️  Error processing {pattern_id}: {e}")

        if updated % 100 == 0:
            print(f"  ⏳ Processed {updated} patterns ({errors} errors)")

        offset = next_offset
        if offset is None:
            break

    # Write log file
    with open(log_file, 'w') as f:
        f.write(f"Qdrant Migration Log - {timestamp}\n")
        f.write(f"Collection: {collection_name}\n")
        f.write(f"Updated: {updated}\n")
        f.write(f"Errors: {errors}\n")
        f.write("\nDetails:\n")
        f.write("\n".join(log_entries))

    print(f"\n✅ Qdrant migration completed!")
    print(f"📊 Updated: {updated} patterns")
    print(f"⚠️  Errors: {errors}")
    print(f"📝 Log: {log_file}")

    neo4j_client.close()
    return updated, errors


if __name__ == "__main__":
    updated, errors = migrate_qdrant_enrich_metadata()
    print(f"\n🎉 Migration complete: {updated} patterns enriched")
