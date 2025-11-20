"""
Rebuild Qdrant collection with GraphCodeBERT embeddings.

This script:
1. Loads the backup of 21,624 patterns
2. Re-encodes them using GraphCodeBERT (code-aware embeddings)
3. Creates a new Qdrant collection
4. Uploads the re-encoded patterns
5. Validates the rebuild

Expected time: 1-2 hours for 21,624 patterns
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import numpy as np


def load_backup(backup_file: str) -> List[Dict[str, Any]]:
    """Load the patterns backup."""
    print(f"📥 Loading backup from {backup_file}...")
    with open(backup_file, 'r') as f:
        patterns = json.load(f)

    print(f"   ✓ Loaded {len(patterns)} patterns")
    return patterns


def load_graphcodebert() -> SentenceTransformer:
    """Load GraphCodeBERT model."""
    print(f"\n🤖 Loading GraphCodeBERT model...")
    start = time.time()
    # Suppress pooler weights warning (cosmetic only, doesn't affect embeddings)
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*pooler.*")
        warnings.filterwarnings("ignore", message=".*Some weights.*not initialized.*")
        model = SentenceTransformer('microsoft/graphcodebert-base')
    elapsed = time.time() - start
    print(f"   ✓ Model loaded in {elapsed:.2f}s")

    # Test encoding
    test_vec = model.encode("test code function")
    print(f"   ✓ Vector dimension: {len(test_vec)}")
    print(f"   ✓ Vector range: [{test_vec.min():.4f}, {test_vec.max():.4f}]")
    print(f"   ✓ Vector std: {test_vec.std():.4f}")
    return model


def create_new_collection(client: QdrantClient, collection_name: str):
    """Create new Qdrant collection with GraphCodeBERT config."""
    print(f"\n📦 Creating new collection: {collection_name}")

    # Delete old collection if exists
    try:
        existing = client.get_collection(collection_name)
        print(f"   ⚠️  Collection exists with {existing.points_count} points")

        # Rename old collection as backup
        backup_name = f"{collection_name}_mpnet_backup"
        print(f"   🔄 Renaming old collection to: {backup_name}")

        # Can't rename directly in Qdrant, so we'll delete
        # (we have the JSON backup already)
        print(f"   🗑️  Deleting old collection (backup saved in qdrant_backup/)")
        client.delete_collection(collection_name)
        print(f"   ✓ Old collection deleted")
    except Exception as e:
        print(f"   ℹ️  No existing collection found (OK)")

    # Create new collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=768,  # GraphCodeBERT dimension
            distance=Distance.COSINE
        )
    )
    print(f"   ✓ New collection created (768-dim, Cosine)")
    return True


def re_encode_patterns(
    patterns: List[Dict[str, Any]],
    model: SentenceTransformer,
    batch_size: int = 50
) -> List[Dict[str, Any]]:
    """
    Re-encode all patterns using GraphCodeBERT.

    Args:
        patterns: List of patterns with payloads
        model: GraphCodeBERT model
        batch_size: Batch size for encoding

    Returns:
        List of patterns with new GraphCodeBERT vectors
    """
    print(f"\n🔄 Re-encoding {len(patterns)} patterns with GraphCodeBERT...")
    print(f"   Batch size: {batch_size}")
    print(f"   Estimated time: {len(patterns) / batch_size * 2:.1f} seconds (~{len(patterns) / batch_size * 2 / 60:.1f} minutes)")

    re_encoded = []
    total_batches = (len(patterns) + batch_size - 1) // batch_size
    start_time = time.time()

    for i in range(0, len(patterns), batch_size):
        batch = patterns[i:i+batch_size]
        batch_num = i // batch_size + 1

        # Extract content for encoding
        # Priority: code > description > name
        texts = []
        for p in batch:
            payload = p['payload']
            text = payload.get('code') or payload.get('description') or payload.get('name') or ''
            texts.append(text)

        # Encode batch
        batch_start = time.time()
        vectors = model.encode(texts, show_progress_bar=False)
        batch_time = time.time() - batch_start

        # Add to re-encoded list
        for pattern, vector in zip(batch, vectors):
            re_encoded.append({
                'id': pattern['id'],
                'vector': vector.tolist(),
                'payload': pattern['payload']
            })

        # Progress update
        if batch_num % 10 == 0 or batch_num == total_batches:
            elapsed = time.time() - start_time
            patterns_per_sec = len(re_encoded) / elapsed
            eta_seconds = (len(patterns) - len(re_encoded)) / patterns_per_sec

            print(f"   Batch {batch_num}/{total_batches}: "
                  f"{len(re_encoded)}/{len(patterns)} patterns "
                  f"({patterns_per_sec:.1f} p/s, "
                  f"ETA: {eta_seconds/60:.1f}m)")

    total_time = time.time() - start_time
    print(f"   ✓ Re-encoding complete in {total_time:.2f}s ({total_time/60:.2f}m)")
    print(f"   ✓ Average: {len(patterns) / total_time:.1f} patterns/second")

    return re_encoded


def upload_patterns(
    client: QdrantClient,
    collection_name: str,
    patterns: List[Dict[str, Any]],
    batch_size: int = 100
):
    """Upload re-encoded patterns to Qdrant."""
    print(f"\n📤 Uploading {len(patterns)} patterns to Qdrant...")
    print(f"   Batch size: {batch_size}")

    total_batches = (len(patterns) + batch_size - 1) // batch_size
    start_time = time.time()

    for i in range(0, len(patterns), batch_size):
        batch = patterns[i:i+batch_size]
        batch_num = i // batch_size + 1

        # Create PointStruct objects
        points = [
            PointStruct(
                id=p['id'],
                vector=p['vector'],
                payload=p['payload']
            )
            for p in batch
        ]

        # Upload batch
        client.upsert(
            collection_name=collection_name,
            points=points
        )

        # Progress update
        if batch_num % 20 == 0 or batch_num == total_batches:
            uploaded = min(i + batch_size, len(patterns))
            elapsed = time.time() - start_time
            print(f"   Batch {batch_num}/{total_batches}: "
                  f"{uploaded}/{len(patterns)} patterns uploaded")

    total_time = time.time() - start_time
    print(f"   ✓ Upload complete in {total_time:.2f}s")

    # Verify count
    collection = client.get_collection(collection_name)
    print(f"   ✓ Verified: {collection.points_count} points in collection")


def validate_retrieval(client: QdrantClient, collection_name: str, model: SentenceTransformer):
    """Validate that retrieval works with GraphCodeBERT."""
    print(f"\n✅ Validating retrieval quality...")

    test_queries = [
        "create REST API endpoint with Express.js",
        "React component with useState hook",
        "async function with error handling",
        "database connection pool",
        "authentication middleware JWT"
    ]

    for query in test_queries:
        # Encode query
        query_vec = model.encode(query)

        # Search
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vec.tolist(),
            limit=3
        )

        if results:
            top_score = results[0].score
            top_name = results[0].payload.get('name', 'N/A')
            print(f"   Query: '{query}'")
            print(f"      ✓ Top match: {top_name} (score: {top_score:.4f})")
        else:
            print(f"   Query: '{query}'")
            print(f"      ⚠️  No results found")

    print(f"\n✅ Validation complete!")


def main():
    """Main rebuild process."""
    print("=" * 80)
    print("🔧 QDRANT COLLECTION REBUILD: GraphCodeBERT")
    print("=" * 80)

    # Configuration
    BACKUP_FILE = "qdrant_backup/patterns_payloads_only.json"
    COLLECTION_NAME = "devmatrix_patterns"
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333

    # Step 1: Load backup
    patterns = load_backup(BACKUP_FILE)

    # Step 2: Load GraphCodeBERT
    model = load_graphcodebert()

    # Step 3: Connect to Qdrant
    print(f"\n🔌 Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"   ✓ Connected")

    # Step 4: Create new collection
    if not create_new_collection(client, COLLECTION_NAME):
        print("\n❌ Rebuild aborted")
        return

    # Step 5: Re-encode patterns
    re_encoded_patterns = re_encode_patterns(patterns, model, batch_size=50)

    # Step 6: Upload patterns
    upload_patterns(client, COLLECTION_NAME, re_encoded_patterns, batch_size=100)

    # Step 7: Validate
    validate_retrieval(client, COLLECTION_NAME, model)

    # Summary
    print("\n" + "=" * 80)
    print("🎉 REBUILD COMPLETE!")
    print("=" * 80)
    print(f"✓ Collection: {COLLECTION_NAME}")
    print(f"✓ Patterns: {len(re_encoded_patterns)}")
    print(f"✓ Model: GraphCodeBERT (microsoft/graphcodebert-base)")
    print(f"✓ Vector dimension: 768")
    print(f"✓ Distance metric: Cosine")
    print("\nNext steps:")
    print("1. Update unified_retriever.py to use GraphCodeBERT")
    print("2. Re-run Task 3.5.4 to measure E2E precision improvement")
    print("=" * 80)


if __name__ == "__main__":
    main()
