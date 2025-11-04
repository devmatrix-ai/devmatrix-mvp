#!/usr/bin/env python3
"""
PHASE 1 OPENAI BENCHMARK - Test OpenAI embeddings performance

Quick benchmark without re-seeding
"""

import sys
import time
import json
import os
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_retriever, create_vector_store, create_embedding_model, RetrievalStrategy
from src.observability import get_logger

logger = get_logger(__name__)


def main():
    """Run OpenAI baseline benchmark"""
    logger.info("=" * 60)
    logger.info("PHASE 1: OPENAI BASELINE BENCHMARK")
    logger.info("=" * 60)

    start = time.time()

    try:
        # Initialize with OpenAI (cache disabled for now due to compatibility)
        logger.info("\n📦 Initializing RAG with OpenAI embeddings...")
        embeddings = create_embedding_model(use_openai=True, enable_cache=False)
        logger.info(f"✅ Model: {embeddings.model_name}")
        logger.info(f"✅ Dimensions: {embeddings.dimension}")

        vector_store = create_vector_store(embeddings)

        # Check stats
        doc_count = len(vector_store.collection.get().get('ids', []))
        logger.info(f"✅ Documents indexed: {doc_count}")

        # Create retriever (disable V2 caching, lower similarity threshold for OpenAI embeddings)
        # OpenAI embeddings (3072-dim) give lower similarity scores than Jina (768-dim)
        # Adjusted threshold from 0.7 to 0.4 based on empirical testing
        retriever = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            min_similarity=0.4,  # Lowered from default 0.7 for OpenAI embeddings
            use_multi_collection=False,
            enable_v2_caching=False
        )
        logger.info(f"✅ Retriever created (SIMILARITY, min_similarity=0.4, V2 caching disabled)")

        # Test queries - more diverse
        test_queries = [
            ("Express.js server setup", "express"),
            ("React hooks and functional components", "react"),
            ("TypeScript type definitions and interfaces", "typescript"),
            ("JavaScript async await functions", "javascript"),
            ("REST API error handling patterns", "express"),
            ("React state management with useState", "react"),
            ("Node.js middleware functions", "node"),
            ("Async middleware in Express", "express"),
        ]

        logger.info(f"\n🔍 Running {len(test_queries)} test queries:\n")

        results = []
        successes = 0

        for query, expected_framework in test_queries:
            try:
                ret_results = retriever.retrieve(query, top_k=1)

                if ret_results:
                    top = ret_results[0]
                    framework = top.metadata.get("framework", "unknown")
                    match = (framework == expected_framework)

                    results.append({
                        "query": query,
                        "expected": expected_framework,
                        "retrieved": framework,
                        "match": match,
                        "similarity": float(top.similarity),
                        "code_preview": top.code[:60] + "..." if top.code else ""
                    })

                    status = "✅" if match else "❌"
                    logger.info(
                        f"{status} [{query:45s}] → {framework:15s} "
                        f"(similarity: {top.similarity:.3f})"
                    )

                    if match:
                        successes += 1
                else:
                    logger.warning(f"⚠️  No results for: {query}")
                    results.append({
                        "query": query,
                        "expected": expected_framework,
                        "retrieved": "NO_RESULTS",
                        "match": False,
                        "similarity": 0.0,
                    })

            except Exception as e:
                logger.error(f"❌ Error querying '{query}': {e}")
                results.append({
                    "query": query,
                    "expected": expected_framework,
                    "error": str(e),
                    "match": False
                })

        # Summary
        success_rate = (successes / len(test_queries) * 100) if test_queries else 0
        elapsed = time.time() - start

        logger.info("\n" + "=" * 60)
        logger.info(f"RESULTS:")
        logger.info(f"  Success Rate: {successes}/{len(test_queries)} ({success_rate:.1f}%)")
        logger.info(f"  Improvement vs Jina: {success_rate - 20:.1f}% (from 20% baseline)")
        logger.info(f"  Time Elapsed: {elapsed:.1f}s")
        logger.info("=" * 60)

        # Save results
        output_file = Path(__file__).parent.parent / "DOCS" / "rag" / "phase1_openai_benchmark.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump({
                "phase": "PHASE 1: OpenAI Baseline",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "embedding_model": "OpenAI text-embedding-3-large",
                "metrics": {
                    "success_rate_percent": success_rate,
                    "successes": successes,
                    "total_queries": len(test_queries),
                    "elapsed_seconds": elapsed,
                    "documents_indexed": doc_count,
                },
                "results": results,
            }, f, indent=2)

        logger.info(f"\n📊 Results saved to: {output_file}")
        return 0

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
