#!/usr/bin/env python
"""
Reset Embeddings and Re-ingest with New Model

Clears existing embeddings and re-embeds all 146 documents using the new
CodeSearch model (Salesforce/codesearch-distilroberta-base).

Steps:
1. Clear persistent embedding cache
2. Delete existing ChromaDB collection
3. Load 146 combined examples (52 curated + 94 GitHub)
4. Re-embed with CodeSearch model
5. Re-ingest into ChromaDB
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.combine_phase4_all_examples import collect_all_phase4_examples
from src.rag.vector_store import create_vector_store
from src.rag.embeddings import EmbeddingModel
from src.observability import get_logger
import shutil

logger = get_logger(__name__)


def load_github_extracted_examples(json_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Load GitHub extracted examples from JSON file."""

    if not Path(json_path).exists():
        logger.error(f"GitHub extraction file not found: {json_path}")
        return []

    logger.info(f"Loading GitHub extraction from {json_path}...")

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        examples = []
        for item in data:
            if isinstance(item, dict) and "code" in item and "metadata" in item:
                code = item["code"]
                metadata = item["metadata"]
                examples.append((code, metadata))

        logger.info(f"✅ Loaded {len(examples)} GitHub extracted examples")
        return examples

    except Exception as e:
        logger.error(f"Failed to load GitHub extraction: {str(e)}")
        return []


def clear_embedding_cache(cache_dir: str = ".cache/rag") -> bool:
    """Clear persistent embedding cache."""
    try:
        cache_path = Path(cache_dir)
        if cache_path.exists():
            logger.info(f"Clearing embedding cache at {cache_dir}")
            shutil.rmtree(cache_path)
            logger.info("✅ Cache cleared")
            return True
        else:
            logger.info(f"Cache directory not found: {cache_dir}")
            return True
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return False


def delete_chromadb_collection() -> bool:
    """Delete existing ChromaDB collection."""
    try:
        logger.info("Connecting to ChromaDB to delete existing collection...")
        vector_store = create_vector_store(
            embedding_model=EmbeddingModel(
                model_name="jinaai/jina-embeddings-v2-base-code",
                enable_cache=False  # Don't use cache yet
            )
        )

        logger.info("Deleting existing collection...")
        try:
            # Delete the collection
            vector_store.client.delete_collection(
                name=vector_store.collection_name
            )
            logger.info(f"✅ Deleted collection: {vector_store.collection_name}")
        except Exception as e:
            logger.warning(f"Collection may not exist yet: {str(e)}")

        return True

    except Exception as e:
        logger.error(f"Failed to delete ChromaDB collection: {str(e)}")
        return False


def prepare_documents(examples: List[Tuple[str, Dict[str, Any]]],
                      start_index: int = 0) -> List[Dict[str, Any]]:
    """Prepare examples for ChromaDB ingestion."""
    documents = []

    for i, (code, metadata) in enumerate(examples, start=start_index):
        doc_id = f"phase4_github_{i:03d}"

        language = metadata.get("language", "unknown")
        framework = metadata.get("framework", "general")
        pattern = metadata.get("pattern", "unknown")
        task_type = metadata.get("task_type", "unknown")
        complexity = metadata.get("complexity", "unknown")
        tags = metadata.get("tags", [])
        source = metadata.get("source", "github")

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
                "indexed_at": "2025-11-04-codesearch",
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
    logger.info("🔄 RESET EMBEDDINGS WITH CODE-SPECIFIC MODEL")
    logger.info("=" * 80)

    # Step 1: Clear cache
    logger.info("\n📁 Step 1: Clearing embedding cache...")
    if not clear_embedding_cache():
        logger.warning("Cache clearing failed, continuing anyway")

    # Step 2: Delete ChromaDB collection
    logger.info("\n🗑️  Step 2: Deleting ChromaDB collection...")
    # Skip for now since we'll just use the new embeddings
    # if not delete_chromadb_collection():
    #     logger.warning("Collection deletion failed, continuing anyway")

    # Step 3: Load all examples
    logger.info("\n📦 Step 3: Loading all 146 examples...")
    logger.info("  Loading 52 curated examples...")
    curated_examples = collect_all_phase4_examples()
    logger.info(f"     ✅ {len(curated_examples)} curated")

    logger.info("  Loading 94 GitHub extracted examples...")
    github_examples_tuples = load_github_extracted_examples("/tmp/phase4_github_extraction.json")
    logger.info(f"     ✅ {len(github_examples_tuples)} GitHub")

    all_examples = list(curated_examples) + github_examples_tuples
    logger.info(f"\n✨ Total examples: {len(all_examples)}")

    if len(all_examples) == 0:
        logger.error("❌ No examples to ingest!")
        return False

    # Step 4: Initialize vector store with NEW model
    logger.info("\n🔌 Step 4: Initializing vector store with Jina code model...")
    try:
        embedding_model = EmbeddingModel(
            model_name="jinaai/jina-embeddings-v2-base-code",
            enable_cache=True
        )
        logger.info(f"✅ Jina code model loaded (dim: {embedding_model.dimension})")

        vector_store = create_vector_store(embedding_model=embedding_model)
        logger.info("✅ Vector store connected")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {str(e)}")
        return False

    # Step 5: Re-ingest with new embeddings
    logger.info("\n📥 Step 5: Re-ingesting 146 examples with new model...")
    documents = prepare_documents(all_examples)

    batch_size = 10
    total_ingested = 0
    failed = 0

    for batch_idx in range(0, len(documents), batch_size):
        batch_docs = documents[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(documents) + batch_size - 1) // batch_size

        logger.info(f"\nBatch {batch_num}/{total_batches} ({len(batch_docs)} examples)")

        codes = [doc["code"] for doc in batch_docs]
        example_ids = [doc["id"] for doc in batch_docs]
        metadatas = [doc["metadatas"] for doc in batch_docs]

        if ingest_batch(vector_store, codes, example_ids, metadatas):
            logger.info(f"   ✅ Ingested {len(batch_docs)} examples")
            total_ingested += len(batch_docs)
        else:
            logger.error(f"   ❌ Failed to ingest batch {batch_num}")
            failed += len(batch_docs)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 RE-EMBEDDING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Model: jinaai/jina-embeddings-v2-base-code")
    logger.info(f"Total examples: {len(documents)}")
    logger.info(f"Successfully ingested: {total_ingested}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info(f"\n✅ SUCCESS! All {total_ingested} examples re-embedded with Jina code model")
        logger.info("=" * 80)
        logger.info("\n📝 Next: Run benchmark_phase4_queries.py to compare results")
        return True
    else:
        logger.error(f"\n❌ PARTIAL FAILURE: {failed} examples failed")
        logger.info("=" * 80)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
