#!/usr/bin/env python3
"""
PHASE 1 SIMPLE BENCHMARK - Direct Retriever (no Multi-Collection)

Bypasses multi-collection manager to isolate retriever performance
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_retriever, create_vector_store, create_embedding_model, RetrievalStrategy
from src.observability import get_logger

logger = get_logger(__name__)


def main():
    """Run simple benchmark"""
    logger.info("="*60)
    logger.info("PHASE 1: SIMPLE BASELINE BENCHMARK")
    logger.info("="*60)

    start = time.time()

    try:
        # Initialize RAG
        logger.info("\n📦 Initializing RAG...")
        embeddings = create_embedding_model()
        vector_store = create_vector_store(embeddings)

        # Check vector store contents
        stats = vector_store.get_stats()
        logger.info(f"✅ Vector store initialized")
        logger.info(f"   Collection: devmatrix_code_examples")
        logger.info(f"   Total documents: {len(vector_store.collection.get().get('ids', []))}")

        # Create retriever (direct, no multi-collection for PHASE 1)
        # Note: Disabling V2 cache for this benchmark
        import os
        os.environ['RAG_V2_CACHING_ENABLED'] = 'false'  # Disable RAG query caching for clean benchmark

        retriever = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            use_multi_collection=False  # Use main vector store only
        )
        logger.info(f"✅ Retriever created (SIMILARITY strategy)")

        # Test queries
        test_queries = [
            ("Express server setup", "express"),
            ("React component patterns", "react"),
            ("TypeScript types and interfaces", "typescript"),
            ("JavaScript async functions", "javascript"),
            ("error handling in REST API", "express"),
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
                        "similarity": top.similarity,
                        "code_preview": top.code[:80] + "..." if top.code else ""
                    })

                    status = "✅" if match else "❌"
                    logger.info(
                        f"{status} [{query:35s}] → {framework:15s} "
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
                        "error": "No documents returned"
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

        logger.info("\n" + "="*60)
        logger.info(f"RESULTS:")
        logger.info(f"  Success Rate: {successes}/{len(test_queries)} ({success_rate:.1f}%)")
        logger.info(f"  Time Elapsed: {elapsed:.1f}s")
        logger.info("="*60)

        # Save results
        output_file = Path(__file__).parent.parent / "DOCS" / "rag" / "phase1_simple_benchmark.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump({
                "phase": "PHASE 1: Simple Baseline",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "metrics": {
                    "success_rate_percent": success_rate,
                    "successes": successes,
                    "total_queries": len(test_queries),
                    "elapsed_seconds": elapsed,
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
