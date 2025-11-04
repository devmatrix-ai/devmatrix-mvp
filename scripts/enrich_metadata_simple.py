#!/usr/bin/env python3
"""
Simple Metadata Enrichment - No Embeddings

Only enriches metadata without touching embeddings.
Avoids all caching issues.
"""

import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.metadata_extractor import MetadataExtractor
from src.rag import create_vector_store, create_embedding_model
from src.observability import get_logger

logger = get_logger(__name__)


def main():
    """Enrich metadata without re-embedding."""
    logger.info("=" * 70)
    logger.info("METADATA ENRICHMENT - No Embeddings (Metadata Only)")
    logger.info("=" * 70)

    try:
        # Create minimal embedding model just to access ChromaDB collection
        # Use dummy model to avoid cache issues
        logger.info("\n📦 Connecting to ChromaDB...")
        embeddings = create_embedding_model(use_openai=True, enable_cache=False)
        vector_store = create_vector_store(embeddings)

        # Get all documents
        logger.info("📚 Loading documents from ChromaDB...")
        all_docs = vector_store.collection.get()
        doc_ids = all_docs.get("ids", [])
        metadatas = all_docs.get("metadatas", [])
        documents = all_docs.get("documents", [])

        logger.info(f"✅ Loaded {len(doc_ids)} documents")

        # Analyze before
        logger.info("\n📊 BEFORE enrichment:")
        unknown_fw = sum(1 for m in metadatas if m.get("framework") == "unknown")
        unknown_lang = sum(1 for m in metadatas if m.get("language") == "unknown")
        logger.info(f"  Unknown frameworks: {unknown_fw}/{len(doc_ids)}")
        logger.info(f"  Unknown languages: {unknown_lang}/{len(doc_ids)}")

        # Enrich metadata
        logger.info(f"\n🔧 Enriching metadata for {len(doc_ids)} documents...")
        extractor = MetadataExtractor()
        enriched_metadatas = []
        stats = {"filled_fw": 0, "filled_lang": 0, "patterns": 0}

        for i, (doc_id, doc_text, metadata) in enumerate(
            zip(doc_ids, documents, metadatas)
        ):
            try:
                enriched = extractor.enrich_metadata(metadata, doc_text)

                # Track improvements
                if (
                    enriched.get("framework") != metadata.get("framework")
                    and enriched.get("framework") != "unknown"
                ):
                    stats["filled_fw"] += 1

                if (
                    enriched.get("language") != metadata.get("language")
                    and enriched.get("language") != "unknown"
                ):
                    stats["filled_lang"] += 1

                if enriched.get("patterns"):
                    stats["patterns"] += 1

                enriched_metadatas.append(enriched)

            except Exception as e:
                logger.warning(f"Skipped doc {doc_id[:8]}: {e}")
                enriched_metadatas.append(metadata)

            if (i + 1) % 20 == 0:
                logger.info(f"  Processed {i + 1}/{len(doc_ids)}")

        # Update ALL at once (batch update)
        logger.info(f"\n📝 Writing enriched metadata to ChromaDB...")
        vector_store.collection.upsert(
            ids=doc_ids,
            documents=documents,
            metadatas=enriched_metadatas,
        )

        # Analyze after
        logger.info("\n📊 AFTER enrichment:")
        unknown_fw_after = sum(1 for m in enriched_metadatas if m.get("framework") == "unknown")
        unknown_lang_after = sum(1 for m in enriched_metadatas if m.get("language") == "unknown")
        logger.info(f"  Unknown frameworks: {unknown_fw_after}/{len(doc_ids)} (improved: {unknown_fw - unknown_fw_after})")
        logger.info(f"  Unknown languages: {unknown_lang_after}/{len(doc_ids)} (improved: {unknown_lang - unknown_lang_after})")

        logger.info("\n" + "=" * 70)
        logger.info("ENRICHMENT COMPLETE!")
        logger.info(f"  Frameworks filled: {stats['filled_fw']}")
        logger.info(f"  Languages filled: {stats['filled_lang']}")
        logger.info(f"  Patterns detected: {stats['patterns']}")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
