#!/usr/bin/env python3
"""
Sprint 0 Task 0.5: Classify Untagged Patterns

Uses Qdrant embedding similarity to find the most similar tagged pattern
and copies its tags to the untagged pattern.

This script:
1. Finds all patterns in Neo4j without HAS_TAG relationships
2. For each untagged pattern, retrieves its embedding from Qdrant
3. Searches for the most similar tagged pattern (similarity >= 0.85)
4. Copies tags from the similar pattern to the untagged one

The script is idempotent - it uses MERGE to avoid duplicate relationships
and can be run multiple times safely.
"""
import asyncio
import os
import sys
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from neo4j import AsyncGraphDatabase

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "devmatrix_patterns"

# Similarity threshold: only copy tags if similarity exceeds this value
SIMILARITY_THRESHOLD = 0.85

# Batch size for processing
BATCH_SIZE = 100


async def get_untagged_patterns(driver) -> List[str]:
    """
    Retrieve pattern IDs for patterns without any tags.

    Returns:
        List of pattern_id strings
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (p:Pattern)
            WHERE NOT EXISTS { MATCH (p)-[:HAS_TAG]->() }
              AND p.pattern_id IS NOT NULL
              AND p.pattern_id <> ''
            RETURN p.pattern_id as pattern_id
            ORDER BY p.pattern_id
            LIMIT 2000
        """)
        patterns = [record["pattern_id"] async for record in result]
        return patterns


async def check_pattern_has_tags(driver, pattern_id: str) -> bool:
    """
    Check if a pattern has any tags in Neo4j.

    Args:
        driver: Neo4j driver instance
        pattern_id: Pattern ID to check

    Returns:
        True if pattern has tags, False otherwise
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (p:Pattern {pattern_id: $pattern_id})
            RETURN EXISTS { MATCH (p)-[:HAS_TAG]->() } as has_tags
        """, pattern_id=pattern_id)
        record = await result.single()
        return record["has_tags"] if record else False


async def copy_tags_from_similar(driver, pattern_id: str, ref_pattern_id: str) -> int:
    """
    Copy all tags from reference pattern to target pattern.

    Args:
        driver: Neo4j driver instance
        pattern_id: Target pattern ID
        ref_pattern_id: Reference pattern ID to copy tags from

    Returns:
        Number of tags copied
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (p:Pattern {pattern_id: $pattern_id})
            MATCH (ref:Pattern {pattern_id: $ref_id})-[:HAS_TAG]->(t:Tag)
            MERGE (p)-[:HAS_TAG]->(t)
            RETURN count(t) as tags_copied
        """, pattern_id=pattern_id, ref_id=ref_pattern_id)
        record = await result.single()
        return record["tags_copied"] if record else 0


def find_similar_tagged_pattern(
    qdrant: QdrantClient,
    pattern_vector: List[float],
    current_pattern_id: str,
    driver
) -> Optional[tuple[str, float]]:
    """
    Find the most similar pattern that has tags.

    Args:
        qdrant: Qdrant client instance
        pattern_vector: Embedding vector of the current pattern
        current_pattern_id: ID of current pattern (to exclude from results)
        driver: Neo4j driver to check if candidates have tags

    Returns:
        Tuple of (pattern_id, similarity_score) or None if no suitable match found
    """
    # Search for similar patterns (top 20 to increase chances of finding tagged ones)
    similar = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=pattern_vector,
        limit=20
    )

    # Filter results to find first tagged pattern above threshold
    for result in similar:
        # Skip if it's the same pattern
        if result.payload.get("pattern_id") == current_pattern_id:
            continue

        # Skip if similarity is below threshold
        if result.score < SIMILARITY_THRESHOLD:
            continue

        ref_id = result.payload.get("pattern_id")
        if not ref_id:
            continue

        # Check if this pattern has tags (synchronous call needed)
        # This is acceptable since we're checking one at a time
        if asyncio.run(check_pattern_has_tags(driver, ref_id)):
            return ref_id, result.score

    return None


async def classify_patterns():
    """
    Main classification logic.

    Process:
    1. Connect to Neo4j and Qdrant
    2. Get all untagged patterns
    3. For each pattern:
       - Retrieve embedding from Qdrant
       - Find most similar tagged pattern
       - Copy tags if similarity >= threshold
    4. Report statistics
    """
    print("🚀 Starting pattern classification...")
    print(f"📊 Configuration:")
    print(f"   Neo4j: {NEO4J_URI}")
    print(f"   Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   Similarity threshold: {SIMILARITY_THRESHOLD}")
    print()

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    try:
        # Verify Qdrant collection exists
        collections = qdrant.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            print(f"❌ Error: Collection '{COLLECTION_NAME}' not found in Qdrant")
            return

        # Get untagged patterns
        print("🔍 Fetching untagged patterns from Neo4j...")
        untagged = await get_untagged_patterns(driver)
        print(f"📝 Found {len(untagged)} untagged patterns")

        if not untagged:
            print("✅ No untagged patterns to process!")
            return

        print()

        # Statistics
        classified = 0
        skipped_no_vector = 0
        skipped_no_similar = 0
        errors = 0

        # Process each pattern
        for i, pattern_id in enumerate(untagged, 1):
            try:
                # Get pattern vector from Qdrant
                results = qdrant.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="pattern_id",
                                match=MatchValue(value=pattern_id)
                            )
                        ]
                    ),
                    limit=1,
                    with_vectors=True
                )

                points, _ = results
                if not points:
                    skipped_no_vector += 1
                    if i % BATCH_SIZE == 0 or i == len(untagged):
                        print(f"⏩ Skipped (no vector): {pattern_id}")
                    continue

                pattern_vector = points[0].vector

                # Find most similar tagged pattern
                similar_match = find_similar_tagged_pattern(
                    qdrant,
                    pattern_vector,
                    pattern_id,
                    driver
                )

                if similar_match:
                    ref_id, similarity = similar_match

                    # Copy tags from similar pattern
                    tags_copied = await copy_tags_from_similar(
                        driver,
                        pattern_id,
                        ref_id
                    )

                    classified += 1
                    if i % BATCH_SIZE == 0 or i == len(untagged):
                        print(f"✅ [{i}/{len(untagged)}] {pattern_id} → {ref_id} "
                              f"(similarity: {similarity:.3f}, tags: {tags_copied})")
                else:
                    skipped_no_similar += 1
                    if i % BATCH_SIZE == 0 or i == len(untagged):
                        print(f"⚠️  No similar tagged pattern found: {pattern_id}")

                # Progress report every BATCH_SIZE patterns
                if i % BATCH_SIZE == 0:
                    print(f"\n📊 Progress: {i}/{len(untagged)}")
                    print(f"   ✅ Classified: {classified}")
                    print(f"   ⏩ Skipped (no vector): {skipped_no_vector}")
                    print(f"   ⚠️  Skipped (no similar): {skipped_no_similar}")
                    print(f"   ❌ Errors: {errors}")
                    print()

            except Exception as e:
                errors += 1
                print(f"❌ Error processing {pattern_id}: {e}")
                continue

        # Final report
        print("\n" + "=" * 60)
        print("📊 CLASSIFICATION COMPLETE")
        print("=" * 60)
        print(f"Total patterns processed: {len(untagged)}")
        print(f"✅ Successfully classified: {classified} ({classified/len(untagged)*100:.1f}%)")
        print(f"⏩ Skipped (no vector in Qdrant): {skipped_no_vector}")
        print(f"⚠️  Skipped (no similar tagged pattern): {skipped_no_similar}")
        print(f"❌ Errors: {errors}")
        print("=" * 60)

        if classified > 0:
            print("\n💡 Next steps:")
            print("   1. Verify tags were copied correctly in Neo4j")
            print("   2. Review patterns that couldn't be classified")
            print("   3. Consider lowering threshold or manual tagging for remaining patterns")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await driver.close()
        print("\n🔌 Connections closed")


if __name__ == "__main__":
    asyncio.run(classify_patterns())
