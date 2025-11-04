#!/usr/bin/env python3
"""
Metadata Enrichment Script

Auto-detects and enriches document metadata in ChromaDB.
Fills missing framework/language information and adds pattern detection.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_embedding_model, create_vector_store
from src.rag.metadata_extractor import MetadataExtractor
from src.observability import get_logger

logger = get_logger(__name__)


def enrich_documents(vector_store, extractor=None):
    """
    Enrich documents in vector store with auto-detected metadata.

    Args:
        vector_store: VectorStore instance
        extractor: MetadataExtractor instance (uses default if None)

    Returns:
        Statistics of enrichment
    """
    if extractor is None:
        extractor = MetadataExtractor()

    # Get all documents from collection
    try:
        all_docs = vector_store.collection.get()
        doc_ids = all_docs.get("ids", [])
        metadatas = all_docs.get("metadatas", [])
        documents = all_docs.get("documents", [])

        logger.info(
            f"📚 Enriching {len(doc_ids)} documents",
            doc_count=len(doc_ids)
        )

        stats = {
            "total": len(doc_ids),
            "framework_filled": 0,
            "language_filled": 0,
            "patterns_added": 0,
            "errors": 0,
        }

        # Process documents
        for i, (doc_id, doc_text, metadata) in enumerate(
            zip(doc_ids, documents, metadatas)
        ):
            try:
                # Enrich metadata
                enriched = extractor.enrich_metadata(metadata, doc_text)

                # Track what was added/updated
                if enriched.get("framework") != metadata.get("framework"):
                    if enriched.get("framework") != "unknown":
                        stats["framework_filled"] += 1
                        logger.debug(
                            f"Filled framework",
                            doc_id=doc_id[:8],
                            framework=enriched.get("framework")
                        )

                if enriched.get("language") != metadata.get("language"):
                    if enriched.get("language") != "unknown":
                        stats["language_filled"] += 1
                        logger.debug(
                            f"Filled language",
                            doc_id=doc_id[:8],
                            language=enriched.get("language")
                        )

                if enriched.get("patterns"):
                    stats["patterns_added"] += 1

                # Update document with enriched metadata (don't re-embed)
                # Only update metadata field to avoid embedding conflicts
                vector_store.collection.update(
                    ids=[doc_id],
                    metadatas=[enriched],
                )

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"Failed to enrich document",
                    doc_id=doc_id[:8],
                    error=str(e)
                )

            # Progress indicator
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(doc_ids)} documents")

        return stats

    except Exception as e:
        logger.error("Failed to enrich documents", error=str(e), exc_info=True)
        raise


def main():
    """Main enrichment workflow."""
    logger.info("=" * 70)
    logger.info("METADATA ENRICHMENT - Auto-detect framework/language/patterns")
    logger.info("=" * 70)

    try:
        # Initialize RAG components
        logger.info("\n📦 Initializing RAG components...")
        embeddings = create_embedding_model(use_openai=True, enable_cache=False)
        vector_store = create_vector_store(embeddings)

        logger.info(
            "✅ RAG components initialized",
            model=embeddings.model_name,
            dimension=embeddings.dimension
        )

        # Get initial stats
        initial_docs = vector_store.collection.get()
        doc_count = len(initial_docs.get("ids", []))
        logger.info(f"✅ Documents in ChromaDB: {doc_count}")

        # Analyze initial metadata quality
        logger.info("\n📊 Analyzing initial metadata quality...")
        frameworks = {}
        languages = {}

        for meta in initial_docs.get("metadatas", []):
            fw = meta.get("framework", "unknown")
            lang = meta.get("language", "unknown")
            frameworks[fw] = frameworks.get(fw, 0) + 1
            languages[lang] = languages.get(lang, 0) + 1

        logger.info("Framework distribution BEFORE:")
        for fw in sorted(frameworks.keys()):
            pct = frameworks[fw] / doc_count * 100
            logger.info(f"  {fw:15s}: {frameworks[fw]:3d} ({pct:5.1f}%)")

        logger.info("Language distribution BEFORE:")
        for lang in sorted(languages.keys()):
            pct = languages[lang] / doc_count * 100
            logger.info(f"  {lang:15s}: {languages[lang]:3d} ({pct:5.1f}%)")

        # Perform enrichment
        logger.info("\n🔧 Starting enrichment process...")
        stats = enrich_documents(vector_store)

        # Get updated stats
        logger.info("\n📊 Analyzing updated metadata quality...")
        updated_docs = vector_store.collection.get()
        frameworks_after = {}
        languages_after = {}

        for meta in updated_docs.get("metadatas", []):
            fw = meta.get("framework", "unknown")
            lang = meta.get("language", "unknown")
            frameworks_after[fw] = frameworks_after.get(fw, 0) + 1
            languages_after[lang] = languages_after.get(lang, 0) + 1

        logger.info("Framework distribution AFTER:")
        for fw in sorted(frameworks_after.keys()):
            pct = frameworks_after[fw] / doc_count * 100
            before = frameworks.get(fw, 0)
            change = frameworks_after[fw] - before
            logger.info(
                f"  {fw:15s}: {frameworks_after[fw]:3d} ({pct:5.1f}%) "
                f"[{'+'if change > 0 else ''}{change}]"
            )

        logger.info("Language distribution AFTER:")
        for lang in sorted(languages_after.keys()):
            pct = languages_after[lang] / doc_count * 100
            before = languages.get(lang, 0)
            change = languages_after[lang] - before
            logger.info(
                f"  {lang:15s}: {languages_after[lang]:3d} ({pct:5.1f}%) "
                f"[{'+'if change > 0 else ''}{change}]"
            )

        # Print enrichment statistics
        logger.info("\n" + "=" * 70)
        logger.info("ENRICHMENT STATISTICS:")
        logger.info(f"  Total documents processed: {stats['total']}")
        logger.info(f"  Frameworks filled: {stats['framework_filled']}")
        logger.info(f"  Languages filled: {stats['language_filled']}")
        logger.info(f"  Patterns detected: {stats['patterns_added']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info("=" * 70)

        # Calculate improvement
        unknown_before = frameworks.get("unknown", 0)
        unknown_after = frameworks_after.get("unknown", 0)
        improvement = unknown_before - unknown_after

        logger.info("\n✅ Enrichment complete!")
        logger.info(
            f"✅ Reduced 'unknown' frameworks: {unknown_before} → {unknown_after} "
            f"(improvement: {improvement})"
        )

        return 0

    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
