#!/usr/bin/env python3
"""
Phase 4: Cross-Encoder Re-ranking Benchmark

Tests cross-encoder re-ranking effectiveness:
- Phase 1 baseline (OpenAI, no expansion, heuristic reranking): 62.5% (5/8)
- Phase 3 (OpenAI + expansion): 62.5% (no improvement)
- Phase 4 (OpenAI + expansion + cross-encoder): Target 70-75%
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_vector_store, create_embedding_model, create_retriever
from src.rag.retriever import RetrievalStrategy
from src.observability import get_logger

logger = get_logger(__name__)


# Test queries with expected frameworks
TEST_QUERIES = [
    ("Express.js server setup with routing", "express"),
    ("React hooks and functional components", "react"),
    ("TypeScript type definitions and interfaces", "typescript"),
    ("JavaScript async/await patterns", "javascript"),
    ("REST API error handling", "express"),
    ("React state management with hooks", "react"),
    ("Node.js middleware implementation", "node"),
    ("Async Express middleware patterns", "express"),
]


def extract_framework_from_results(results: list) -> str:
    """Extract framework from retrieved results."""
    if not results:
        return "none"

    # Check metadata framework field
    for result in results:
        if hasattr(result, 'metadata'):
            fw = result.metadata.get("framework", "unknown")
        else:
            fw = result.get("metadata", {}).get("framework", "unknown")

        if fw and fw != "unknown":
            return fw

    return "unknown"


def run_benchmark():
    """Run Phase 4 benchmark with cross-encoder reranking."""
    logger.info("=" * 70)
    logger.info("PHASE 4: CROSS-ENCODER RE-RANKING BENCHMARK")
    logger.info("=" * 70)

    try:
        # Initialize RAG with cross-encoder
        logger.info("\n📦 Initializing RAG with Cross-Encoder Re-ranking...")
        embeddings = create_embedding_model(use_openai=True, enable_cache=False)
        vector_store = create_vector_store(embeddings)

        # Create retriever WITH cross-encoder
        retriever_ce = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            min_similarity=0.4,
            use_multi_collection=False,
            enable_v2_caching=False,
            enable_query_expansion=False,
            enable_cross_encoder_reranking=True,  # ENABLE CROSS-ENCODER
        )

        logger.info("✅ Cross-encoder retriever initialized")

        # Create baseline retriever WITHOUT cross-encoder for comparison
        retriever_baseline = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            min_similarity=0.4,
            use_multi_collection=False,
            enable_v2_caching=False,
            enable_query_expansion=False,
            enable_cross_encoder_reranking=False,  # DISABLE CROSS-ENCODER
        )

        logger.info("✅ Baseline retriever initialized without cross-encoder")

        # Run tests
        logger.info("\n🧪 Running tests...")
        results_with_ce = []
        results_without_ce = []

        for query, expected_fw in TEST_QUERIES:
            logger.info(f"\n📝 Query: {query}")
            logger.info(f"   Expected: {expected_fw}")

            # Run WITH cross-encoder
            ce_results = retriever_ce.retrieve(query=query, top_k=5)

            ce_fw = extract_framework_from_results(ce_results)
            ce_match = ce_fw == expected_fw

            if ce_results:
                ce_sim = ce_results[0].similarity
                ce_score = ce_results[0].relevance_score
            else:
                ce_sim = 0.0
                ce_score = 0.0

            logger.info(
                f"   WITH cross-encoder: {ce_fw:15s} (sim: {ce_sim:.3f}, score: {ce_score:.3f}) {'✅' if ce_match else '❌'}"
            )

            results_with_ce.append({
                "query": query,
                "expected": expected_fw,
                "retrieved": ce_fw,
                "match": ce_match,
                "similarity": ce_sim,
                "cross_encoder_score": ce_score,
                "results_count": len(ce_results),
            })

            # Run WITHOUT cross-encoder (baseline)
            baseline_results = retriever_baseline.retrieve(query=query, top_k=5)

            baseline_fw = extract_framework_from_results(baseline_results)
            baseline_match = baseline_fw == expected_fw

            if baseline_results:
                baseline_sim = baseline_results[0].similarity
            else:
                baseline_sim = 0.0

            logger.info(f"   WITHOUT cross-encoder: {baseline_fw:15s} (sim: {baseline_sim:.3f}) {'✅' if baseline_match else '❌'}")

            results_without_ce.append({
                "query": query,
                "expected": expected_fw,
                "retrieved": baseline_fw,
                "match": baseline_match,
                "similarity": baseline_sim,
                "results_count": len(baseline_results),
            })

        # Calculate statistics
        ce_correct = sum(1 for r in results_with_ce if r["match"])
        baseline_correct = sum(1 for r in results_without_ce if r["match"])

        ce_rate = (ce_correct / len(TEST_QUERIES)) * 100
        baseline_rate = (baseline_correct / len(TEST_QUERIES)) * 100
        improvement = ce_rate - baseline_rate

        # Print results
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 70)

        logger.info(f"\n📊 WITH Cross-Encoder Re-ranking:")
        logger.info(f"   Success rate: {ce_rate:.1f}% ({ce_correct}/{len(TEST_QUERIES)})")

        logger.info(f"\n📊 WITHOUT Cross-Encoder (Baseline):")
        logger.info(f"   Success rate: {baseline_rate:.1f}% ({baseline_correct}/{len(TEST_QUERIES)})")

        logger.info(f"\n📈 Improvement: {improvement:+.1f} percentage points")

        # Detailed query results
        logger.info("\n" + "=" * 70)
        logger.info("DETAILED QUERY RESULTS")
        logger.info("=" * 70)

        for i, (query, expected_fw) in enumerate(TEST_QUERIES, 1):
            ce = results_with_ce[i - 1]
            base = results_without_ce[i - 1]

            logger.info(f"\n{i}. {query}")
            logger.info(f"   Expected: {expected_fw}")
            logger.info(
                f"   WITH cross-encoder:    {ce['retrieved']:15s} (sim: {ce['similarity']:.3f}, score: {ce['cross_encoder_score']:.3f}) {'✅' if ce['match'] else '❌'}"
            )
            logger.info(f"   WITHOUT cross-encoder: {base['retrieved']:15s} (sim: {base['similarity']:.3f}) {'✅' if base['match'] else '❌'}")

        # Save results to JSON
        benchmark_data = {
            "phase": "PHASE 4: Cross-Encoder Re-ranking",
            "timestamp": datetime.now().isoformat(),
            "embedding_model": "OpenAI text-embedding-3-large",
            "cross_encoder_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "cross_encoder_enabled": True,
            "metrics": {
                "with_cross_encoder_rate_percent": ce_rate,
                "with_cross_encoder_successes": ce_correct,
                "baseline_rate_percent": baseline_rate,
                "baseline_successes": baseline_correct,
                "improvement_points": improvement,
                "total_queries": len(TEST_QUERIES),
            },
            "queries": [
                {
                    "query": q,
                    "expected": e,
                    "with_cross_encoder": results_with_ce[i],
                    "without_cross_encoder": results_without_ce[i],
                }
                for i, (q, e) in enumerate(TEST_QUERIES)
            ],
        }

        output_file = Path(__file__).parent.parent / "DOCS" / "rag" / "phase4_cross_encoder_benchmark.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(benchmark_data, f, indent=2)

        logger.info(f"\n💾 Results saved to {output_file}")

        logger.info("\n" + "=" * 70)

        if ce_rate >= 75:
            logger.info("✅ PHASE 4 SUCCESS: Cross-encoder achieved target (75%+)")
        elif ce_rate >= 70:
            logger.info("✅ PHASE 4 SUCCESS: Cross-encoder achieved target (70%+)")
        else:
            logger.info(f"⚠️  Phase 4 result: {ce_rate:.1f}% (target: 70%+)")

        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(run_benchmark())
