#!/usr/bin/env python
"""
Phase 4 Combined Example Ingestion into ChromaDB

Ingests 52 combined examples (34 seed + 18 gap-filling) into ChromaDB
for RAG system training and query testing.

Usage:
    python scripts/ingest_phase4_combined.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.combine_phase4_all_examples import collect_all_phase4_examples
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
        doc_id = f"phase4_combined_{i:03d}"

        # Extract metadata
        language = metadata.get("language", "unknown")
        framework = metadata.get("framework", "general")
        pattern = metadata.get("pattern", "unknown")
        task_type = metadata.get("task_type", "unknown")
        complexity = metadata.get("complexity", "unknown")
        tags = metadata.get("tags", [])
        source = metadata.get("source", "unknown")

        # Create document
        doc = {
            "id": doc_id,
            "code": code,
            "metadatas": {
                "language": language,
                "framework": framework,
                "pattern": pattern,
                "task_type": task_type,
                "complexity": complexity,
                "tags": ",".join(tags) if isinstance(tags, list) else str(tags),
                "source": source,
                "indexed_at": "2025-11-04",
            }
        }

        documents.append(doc)

    return documents


def ingest_batch(vector_store, codes: List[str], example_ids: List[str],
                metadatas: List[Dict[str, Any]]) -> bool:
    """Ingest a batch of examples."""
    try:
        vector_store.add_batch(
            codes=codes,
            example_ids=example_ids,
            metadatas=metadatas
        )
        return True
    except Exception as e:
        logger.error(f"Batch ingestion failed: {str(e)}")
        return False


def main():
    logger.info("=" * 80)
    logger.info("🚀 PHASE 4 COMBINED EXAMPLE INGESTION")
    logger.info("=" * 80)

    # Collect all examples
    logger.info("\n📦 Collecting examples...")
    examples = collect_all_phase4_examples()
    logger.info(f"✅ Total examples: {len(examples)}")

    # Prepare documents
    logger.info("\n📄 Preparing documents...")
    documents = prepare_documents(examples)
    logger.info(f"✅ Documents prepared: {len(documents)}")

    # Initialize vector store
    logger.info("\n🔌 Initializing vector store...")
    try:
        embedding_model = EmbeddingModel(model_name="all-mpnet-base-v2", enable_cache=True)
        logger.info(f"✅ Embedding model loaded (dim: {embedding_model.dimension})")

        vector_store = create_vector_store(embedding_model=embedding_model)
        logger.info("✅ Vector store connected")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {str(e)}")
        return False

    # Ingest in batches
    logger.info("\n📥 Ingesting examples...")
    batch_size = 10
    total_ingested = 0
    failed = 0

    for batch_idx in range(0, len(documents), batch_size):
        batch_docs = documents[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(documents) + batch_size - 1) // batch_size

        logger.info(f"\nBatch {batch_num}/{total_batches} ({len(batch_docs)} examples)")

        # Extract batch data
        codes = [doc["code"] for doc in batch_docs]
        example_ids = [doc["id"] for doc in batch_docs]
        metadatas = [doc["metadatas"] for doc in batch_docs]

        # Ingest
        if ingest_batch(vector_store, codes, example_ids, metadatas):
            logger.info(f"   ✅ Successfully ingested {len(batch_docs)} examples")
            total_ingested += len(batch_docs)
        else:
            logger.error(f"   ❌ Failed to ingest batch {batch_num}")
            failed += len(batch_docs)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total examples: {len(documents)}")
    logger.info(f"Successfully ingested: {total_ingested}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info(f"\n✅ SUCCESS! All {total_ingested} examples ingested")
        logger.info("=" * 80)
        return True
    else:
        logger.error(f"\n❌ PARTIAL FAILURE: {failed} examples failed")
        logger.info("=" * 80)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
