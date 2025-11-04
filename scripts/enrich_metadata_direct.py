#!/usr/bin/env python3
"""
Direct Metadata Enrichment via ChromaDB Client

Directly updates ChromaDB metadata without touching embeddings.
"""

import sys
from pathlib import Path
import chromadb

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.metadata_extractor import MetadataExtractor
from src.observability import get_logger

logger = get_logger(__name__)


def main():
    """Enrich metadata directly via ChromaDB client."""
    logger.info("=" * 70)
    logger.info("METADATA ENRICHMENT - Direct ChromaDB Client")
    logger.info("=" * 70)

    try:
        # Connect directly to ChromaDB
        logger.info("\n📦 Connecting to ChromaDB...")
        client = chromadb.HttpClient(host="localhost", port=8001)
        collection = client.get_collection("devmatrix_code_examples")

        # Get all documents
        logger.info("📚 Loading documents...")
        all_data = collection.get()
        doc_ids = all_data["ids"]
        documents = all_data["documents"]
        metadatas = all_data["metadatas"]

        logger.info(f"✅ Loaded {len(doc_ids)} documents")

        # Analyze before
        logger.info("\n📊 BEFORE enrichment:")
        unknown_fw = sum(1 for m in metadatas if m.get("framework") == "unknown")
        unknown_lang = sum(1 for m in metadatas if m.get("language") == "unknown")
        logger.info(f"  Unknown frameworks: {unknown_fw}/{len(doc_ids)}")
        logger.info(f"  Unknown languages: {unknown_lang}/{len(doc_ids)}")

        # Enrich
        logger.info(f"\n🔧 Enriching metadata...")
        extractor = MetadataExtractor()
        enriched_metadatas = []
        stats = {"fw": 0, "lang": 0, "patterns": 0}

        for i, (doc_id, doc_text, metadata) in enumerate(
            zip(doc_ids, documents, metadatas)
        ):
            try:
                enriched = extractor.enrich_metadata(metadata, doc_text)

                if (
                    enriched.get("framework") != metadata.get("framework")
                    and enriched.get("framework") != "unknown"
                ):
                    stats["fw"] += 1

                if (
                    enriched.get("language") != metadata.get("language")
                    and enriched.get("language") != "unknown"
                ):
                    stats["lang"] += 1

                if enriched.get("patterns"):
                    stats["patterns"] += 1

                enriched_metadatas.append(enriched)

            except Exception as e:
                logger.warning(f"Skipped {doc_id[:8]}: {e}")
                enriched_metadatas.append(metadata)

            if (i + 1) % 20 == 0:
                logger.info(f"  Processed {i + 1}/{len(doc_ids)}")

        # Update in batches (ONLY metadatas, no documents or embeddings)
        logger.info(f"\n📝 Writing enriched metadata (batch of 10)...")
        batch_size = 10
        for i in range(0, len(doc_ids), batch_size):
            batch_ids = doc_ids[i:i+batch_size]
            batch_metadatas = enriched_metadatas[i:i+batch_size]

            # Update ONLY metadata, not documents (to avoid embedding re-validation)
            collection.update(
                ids=batch_ids,
                metadatas=batch_metadatas,
            )
            logger.info(f"  Updated batch {i//batch_size + 1}")

        # Verify
        logger.info("\n✅ Verifying updates...")
        updated = collection.get()
        updated_metadatas = updated["metadatas"]
        unknown_fw_after = sum(1 for m in updated_metadatas if m.get("framework") == "unknown")
        unknown_lang_after = sum(1 for m in updated_metadatas if m.get("language") == "unknown")

        logger.info("\n📊 AFTER enrichment:")
        logger.info(f"  Unknown frameworks: {unknown_fw_after}/{len(doc_ids)} (improved: {unknown_fw - unknown_fw_after})")
        logger.info(f"  Unknown languages: {unknown_lang_after}/{len(doc_ids)} (improved: {unknown_lang - unknown_lang_after})")

        logger.info("\n" + "=" * 70)
        logger.info("ENRICHMENT STATISTICS:")
        logger.info(f"  Frameworks filled: {stats['fw']}")
        logger.info(f"  Languages filled: {stats['lang']}")
        logger.info(f"  Patterns detected: {stats['patterns']}")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
