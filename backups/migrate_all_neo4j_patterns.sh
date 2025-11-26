#!/bin/bash
# Complete Neo4j migration script - processes ALL patterns in batches

echo "🔄 Starting COMPLETE Neo4j migration..."
echo "📊 This will process all ~30K patterns in batches"

cd /home/kwar/code/agentic-ai

total_migrated=0
iteration=1

while true; do
    echo ""
    echo "🔁 Iteration $iteration - Processing next batch..."

    # Check remaining patterns
    remaining=$(docker exec devmatrix-neo4j cypher-shell -u neo4j -p password \
        "MATCH (p:Pattern) WHERE p.security_level IS NULL RETURN count(p)" 2>/dev/null | grep -E "^[0-9]+$")

    echo "📊 Remaining patterns: $remaining"

    if [ "$remaining" -eq 0 ]; then
        echo "✅ All patterns migrated!"
        break
    fi

    # Run migration script
    PYTHONPATH=/home/kwar/code/agentic-ai:$PYTHONPATH python backups/migrate_neo4j_add_missing_fields.py 2>&1 | \
        grep -E "(Found|Updated|Errors|complete)"

    ((iteration++))

    # Safety: max 10 iterations
    if [ $iteration -gt 10 ]; then
        echo "⚠️  Reached max iterations (10), stopping for safety"
        break
    fi
done

# Final verification
echo ""
echo "🎉 Migration Complete! Final counts:"
with_security=$(docker exec devmatrix-neo4j cypher-shell -u neo4j -p password \
    "MATCH (p:Pattern) WHERE p.security_level IS NOT NULL RETURN count(p)" 2>/dev/null | grep -E "^[0-9]+$")
without_security=$(docker exec devmatrix-neo4j cypher-shell -u neo4j -p password \
    "MATCH (p:Pattern) WHERE p.security_level IS NULL RETURN count(p)" 2>/dev/null | grep -E "^[0-9]+$")

echo "✅ Patterns with security_level: $with_security"
echo "⚠️  Patterns without security_level: $without_security"
