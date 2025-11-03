#!/usr/bin/env python
"""
Phase 4 Example Ingestion into ChromaDB

Ingests the 34 curated JavaScript/TypeScript examples into ChromaDB
for RAG system training and query testing.

Usage:
    python scripts/ingest_phase4_examples.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_and_benchmark_phase4 import collect_all_examples
from src.rag.vector_store import create_vector_store
from src.rag.embeddings import EmbeddingModel
from src.observability import get_logger

logger = get_logger(__name__)


def prepare_documents(examples: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Prepare examples for ChromaDB ingestion.

    Converts (code, metadata) tuples into documents with proper structure.

    Args:
        examples: List of (code, metadata) tuples

    Returns:
        List of documents ready for ChromaDB ingestion
    """
    documents = []

    for i, (code, metadata) in enumerate(examples):
        # Create document ID
        doc_id = f"phase4_example_{i:03d}"

        # Extract metadata
        language = metadata.get("language", "unknown")
        framework = metadata.get("framework", "general")
        pattern = metadata.get("pattern", "unknown")
        task_type = metadata.get("task_type", "unknown")

        # Create ChromaDB document
        document = {
            "id": doc_id,
            "document": code,  # The actual code content
            "metadatas": {
                "language": language,
                "framework": framework,
                "pattern": pattern,
                "task_type": task_type,
                "source": metadata.get("source", "phase4_curated"),
                "complexity": metadata.get("complexity", "medium"),
                "docs_section": metadata.get("docs_section", "general"),
                "approved": metadata.get("approved", True),
                "tags": metadata.get("tags", ""),
            },
        }

        documents.append(document)

    return documents


def ingest_examples() -> Tuple[int, int]:
    """
    Ingest Phase 4 examples into ChromaDB.

    Returns:
        Tuple of (total_examples, successfully_ingested)
    """
    logger.info("=" * 70)
    logger.info("🚀 PHASE 4 INGESTION INTO CHROMADB")
    logger.info("=" * 70)

    # Step 1: Load all examples
    logger.info("\n📚 Loading Phase 4 examples...")
    examples = collect_all_examples()
    logger.info(f"✅ Loaded {len(examples)} examples")

    # Step 2: Prepare documents
    logger.info("\n📝 Preparing documents for ChromaDB...")
    documents = prepare_documents(examples)
    logger.info(f"✅ Prepared {len(documents)} documents")

    # Step 3: Initialize embedding model
    logger.info("\n🤖 Initializing embedding model...")
    try:
        # Use all-mpnet-base-v2 (768 dims) to match existing ChromaDB collection
        embedding_model = EmbeddingModel(model_name="all-mpnet-base-v2", enable_cache=True)
        logger.info(f"✅ Embedding model ready (dimension: {embedding_model.dimension})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize embedding model: {str(e)}")
        return len(examples), 0

    # Step 4: Create/connect to vector store
    logger.info("\n🔗 Connecting to ChromaDB...")
    try:
        vector_store = create_vector_store(embedding_model=embedding_model)
        logger.info("✅ Connected to ChromaDB")
    except Exception as e:
        logger.error(f"❌ Failed to connect to ChromaDB: {str(e)}")
        return len(examples), 0

    # Step 5: Ingest examples in batches
    logger.info("\n📤 Ingesting examples into ChromaDB...")

    ingested_count = 0
    batch_size = 10

    try:
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(f"  Ingesting batch {batch_num}/{(len(documents) - 1) // batch_size + 1}...")

            try:
                # Extract IDs and documents for ingestion
                example_ids = [doc["id"] for doc in batch]
                codes = [doc["document"] for doc in batch]
                metadatas = [doc["metadatas"] for doc in batch]

                # Add to vector store
                vector_store.add_batch(codes=codes, example_ids=example_ids, metadatas=metadatas)

                ingested_count += len(batch)
                logger.info(f"    ✅ Ingested {len(batch)} examples")

            except Exception as e:
                logger.error(f"    ❌ Failed to ingest batch: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {str(e)}")
        return len(examples), ingested_count

    # Step 5: Verify ingestion
    logger.info("\n✅ Ingestion Complete!")
    logger.info(f"   Total examples: {len(examples)}")
    logger.info(f"   Successfully ingested: {ingested_count}")
    logger.info(f"   Success rate: {(ingested_count / len(examples) * 100):.1f}%")

    # Get stats
    try:
        stats = vector_store.get_stats()
        logger.info(f"\n📊 Vector Store Statistics:")
        logger.info(f"   Collection name: {stats.get('collection_name', 'unknown')}")
        logger.info(f"   Total documents: {stats.get('total_documents', 0)}")
        logger.info(f"   Embedding model: {stats.get('embedding_model', 'unknown')}")
        logger.info(f"   Distance metric: {stats.get('distance_metric', 'unknown')}")
    except Exception as e:
        logger.warning(f"Could not retrieve vector store stats: {str(e)}")

    return len(examples), ingested_count


def print_ingestion_summary(total: int, ingested: int) -> None:
    """Print summary of ingestion results."""
    print("\n" + "=" * 70)
    print("🎯 INGESTION SUMMARY")
    print("=" * 70)

    print(f"\n📊 Results:")
    print(f"   Total examples: {total}")
    print(f"   Successfully ingested: {ingested}")
    print(f"   Success rate: {(ingested / total * 100):.1f}%")

    if ingested == total:
        print(f"\n✅ ALL EXAMPLES INGESTED SUCCESSFULLY!")
    else:
        print(f"\n⚠️  {total - ingested} examples failed to ingest")

    print(f"\n📝 Phase 4 Coverage:")
    print(f"   • 34 JavaScript/TypeScript examples")
    print(f"   • 4 frameworks (Express, React, TypeScript, Node.js)")
    print(f"   • 2 languages (JavaScript, TypeScript)")
    print(f"   • 16 task types")
    print(f"   • Ready for query benchmarking")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    total, ingested = ingest_examples()
    print_ingestion_summary(total, ingested)
