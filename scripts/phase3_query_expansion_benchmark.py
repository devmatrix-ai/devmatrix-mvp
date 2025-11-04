#!/usr/bin/env python3
"""
Phase 3: Query Expansion Benchmark

Tests query expansion effectiveness by comparing:
- Phase 1 baseline (OpenAI, no expansion): 62.5% (5/8)
- Phase 3 with query expansion: Target 70-75%
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


def run_benchmark_with_expansion():
    """Run benchmark with query expansion enabled."""
    logger.info("=" * 70)
    logger.info("PHASE 3: QUERY EXPANSION BENCHMARK")
    logger.info("=" * 70)

    try:
        # Initialize RAG
        logger.info("\n📦 Initializing RAG with Query Expansion...")
        embeddings = create_embedding_model(use_openai=True, enable_cache=False)
        vector_store = create_vector_store(embeddings)

        # Create retriever WITH query expansion
        retriever = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            min_similarity=0.4,  # Same as Phase 1
            use_multi_collection=False,
            enable_v2_caching=False,
            enable_query_expansion=True,  # ENABLE EXPANSION
        )

        logger.info("✅ RAG initialized with query expansion enabled")

        # Get baseline retriever WITHOUT expansion for comparison
        retriever_baseline = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5,
            min_similarity=0.4,
            use_multi_collection=False,
            enable_v2_caching=False,
            enable_query_expansion=False,  # DISABLE EXPANSION
        )

        logger.info("✅ Baseline retriever initialized without expansion")

        # Run tests
        logger.info("\n🧪 Running tests...")
        results_with_expansion = []
        results_without_expansion = []

        for query, expected_fw in TEST_QUERIES:
            logger.info(f"\n📝 Query: {query}")
            logger.info(f"   Expected: {expected_fw}")

            # Run WITH expansion
            expanded_results = retriever.retrieve_with_expansion(
                query=query,
                top_k=5,
            )

            expanded_fw = extract_framework_from_results(expanded_results)
            expanded_match = expanded_fw == expected_fw

            if expanded_results:
                expanded_sim = expanded_results[0].similarity
            else:
                expanded_sim = 0.0

            logger.info(f"   WITH expansion: {expanded_fw} (sim: {expanded_sim:.3f}) {'✅' if expanded_match else '❌'}")

            results_with_expansion.append({
                "query": query,
                "expected": expected_fw,
                "retrieved": expanded_fw,
                "match": expanded_match,
                "similarity": expanded_sim,
                "results_count": len(expanded_results),
            })

            # Run WITHOUT expansion (for comparison)
            baseline_results = retriever_baseline.retrieve(
                query=query,
                top_k=5,
            )

            baseline_fw = extract_framework_from_results(baseline_results)
            baseline_match = baseline_fw == expected_fw

            if baseline_results:
                baseline_sim = baseline_results[0].similarity
            else:
                baseline_sim = 0.0

            logger.info(f"   WITHOUT expansion: {baseline_fw} (sim: {baseline_sim:.3f}) {'✅' if baseline_match else '❌'}")

            results_without_expansion.append({
                "query": query,
                "expected": expected_fw,
                "retrieved": baseline_fw,
                "match": baseline_match,
                "similarity": baseline_sim,
                "results_count": len(baseline_results),
            })

        # Calculate statistics
        expanded_correct = sum(1 for r in results_with_expansion if r["match"])
        baseline_correct = sum(1 for r in results_without_expansion if r["match"])

        expanded_rate = (expanded_correct / len(TEST_QUERIES)) * 100
        baseline_rate = (baseline_correct / len(TEST_QUERIES)) * 100
        improvement = expanded_rate - baseline_rate

        # Print results
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 70)

        logger.info(f"\n📊 WITH Query Expansion:")
        logger.info(f"   Success rate: {expanded_rate:.1f}% ({expanded_correct}/{len(TEST_QUERIES)})")

        logger.info(f"\n📊 WITHOUT Query Expansion (Phase 1 baseline):")
        logger.info(f"   Success rate: {baseline_rate:.1f}% ({baseline_correct}/{len(TEST_QUERIES)})")

        logger.info(f"\n📈 Improvement: {improvement:+.1f} percentage points")

        # Detailed query results
        logger.info("\n" + "=" * 70)
        logger.info("DETAILED QUERY RESULTS")
        logger.info("=" * 70)

        for i, (query, expected_fw) in enumerate(TEST_QUERIES, 1):
            exp = results_with_expansion[i - 1]
            base = results_without_expansion[i - 1]

            logger.info(f"\n{i}. {query}")
            logger.info(f"   Expected: {expected_fw}")
            logger.info(f"   With expansion:    {exp['retrieved']:15s} (sim: {exp['similarity']:.3f}) {'✅' if exp['match'] else '❌'}")
            logger.info(f"   Without expansion: {base['retrieved']:15s} (sim: {base['similarity']:.3f}) {'✅' if base['match'] else '❌'}")

        # Save results to JSON
        benchmark_data = {
            "phase": "PHASE 3: Query Expansion",
            "timestamp": datetime.now().isoformat(),
            "embedding_model": "OpenAI text-embedding-3-large",
            "expansion_enabled": True,
            "metrics": {
                "with_expansion_rate_percent": expanded_rate,
                "with_expansion_successes": expanded_correct,
                "baseline_rate_percent": baseline_rate,
                "baseline_successes": baseline_correct,
                "improvement_points": improvement,
                "total_queries": len(TEST_QUERIES),
            },
            "queries": [
                {
                    "query": q,
                    "expected": e,
                    "with_expansion": results_with_expansion[i],
                    "without_expansion": results_without_expansion[i],
                }
                for i, (q, e) in enumerate(TEST_QUERIES)
            ],
        }

        output_file = Path(__file__).parent.parent / "DOCS" / "rag" / "phase3_expansion_benchmark.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(benchmark_data, f, indent=2)

        logger.info(f"\n💾 Results saved to {output_file}")

        logger.info("\n" + "=" * 70)

        if expanded_rate >= 70:
            logger.info("✅ PHASE 3 SUCCESS: Query expansion achieved target (70%+)")
        else:
            logger.info(f"⚠️  Phase 3 result: {expanded_rate:.1f}% (target: 70%+)")

        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(run_benchmark_with_expansion())
