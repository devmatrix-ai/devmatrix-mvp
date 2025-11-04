#!/usr/bin/env python
"""
Phase 4 GitHub Extraction Ingestion - Combine curated + GitHub examples

Reads GitHub extracted examples from JSON and combines with 65 curated examples,
then ingests the full combined dataset into ChromaDB.

Usage:
    python scripts/ingest_phase4_github_extracted.py
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
    logger.info("🚀 PHASE 4 GITHUB EXTRACTION INGESTION")
    logger.info("=" * 80)

    # Load curated examples
    logger.info("\n📦 Loading example datasets...")
    logger.info("  1. Original 65 curated examples...")
    curated_examples = collect_all_phase4_examples()
    logger.info(f"     ✅ Loaded: {len(curated_examples)}") if len(curated_examples) > 0 else logger.error("     ❌ Failed to load curated")

    # Load GitHub extracted examples
    logger.info("  2. GitHub extracted examples...")
    github_path = Path("/tmp/phase4_github_extraction.json")
    github_examples_tuples = load_github_extracted_examples(str(github_path))
    logger.info(f"     ✅ Loaded: {len(github_examples_tuples)}")

    # Combine
    all_examples = list(curated_examples) + github_examples_tuples
    logger.info(f"\n✨ Total examples to ingest: {len(all_examples)}")
    logger.info(f"   • Curated: {len(curated_examples)}")
    logger.info(f"   • GitHub: {len(github_examples_tuples)}")

    if len(all_examples) == 0:
        logger.error("❌ No examples to ingest!")
        return False

    # Analyze
    frameworks = {}
    languages = {}
    sources = {}
    for item in all_examples:
        if isinstance(item, tuple):
            code, metadata = item
            fw = metadata.get("framework", "unknown")
            frameworks[fw] = frameworks.get(fw, 0) + 1

            lang = metadata.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1

            src = metadata.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

    logger.info("\n📊 Framework distribution:")
    for fw, count in sorted(frameworks.items(), key=lambda x: -x[1]):
        pct = (count / len(all_examples)) * 100
        logger.info(f"   • {fw}: {count} ({pct:.1f}%)")

    logger.info("\n📝 Language distribution:")
    for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
        pct = (count / len(all_examples)) * 100
        logger.info(f"   • {lang}: {count} ({pct:.1f}%)")

    logger.info("\n📍 Source distribution:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        pct = (count / len(all_examples)) * 100
        logger.info(f"   • {src}: {count} ({pct:.1f}%)")

    # Prepare documents
    logger.info("\n📄 Preparing documents...")
    documents = prepare_documents(all_examples)
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

        codes = [doc["code"] for doc in batch_docs]
        example_ids = [doc["id"] for doc in batch_docs]
        metadatas = [doc["metadatas"] for doc in batch_docs]

        if ingest_batch(vector_store, codes, example_ids, metadatas):
            logger.info(f"   ✅ Successfully ingested {len(batch_docs)} examples")
            total_ingested += len(batch_docs)
        else:
            logger.error(f"   ❌ Failed to ingest batch {batch_num}")
            failed += len(batch_docs)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 COMBINED INGESTION SUMMARY")
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
