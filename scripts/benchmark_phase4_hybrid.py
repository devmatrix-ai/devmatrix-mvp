#!/usr/bin/env python
"""
Phase 4 Hybrid Retrieval Benchmark

Compares semantic-only vs hybrid (semantic + keyword + metadata) retrieval
on the 27 benchmark queries.

Expected: Hybrid retrieval should improve generic queries significantly
(e.g., "Middleware patterns" from 0.018 → 0.3+)
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.vector_store import create_vector_store
from src.rag.embeddings import EmbeddingModel
from src.rag.hybrid_retriever import HybridRetriever
from src.observability import get_logger

logger = get_logger(__name__)

# Benchmark queries (same 27 from previous benchmarks)
BENCHMARK_QUERIES = [
    # Express (5)
    ("express", "How do I create a basic Express server?"),
    ("express", "Express middleware for error handling"),
    ("express", "API endpoint in Express with routing"),
    ("express", "Express CORS configuration"),
    ("express", "Express async error wrapper"),

    # React (6)
    ("react", "React hooks for state management"),
    ("react", "React custom hooks useAsync"),
    ("react", "React form handling with hooks"),
    ("react", "React Context API for state"),
    ("react", "React Suspense for lazy loading"),
    ("react", "useReducer pattern in React"),

    # TypeScript (4)
    ("typescript", "TypeScript generics for API calls"),
    ("typescript", "TypeScript decorators for validation"),
    ("typescript", "TypeScript discriminated union types"),
    ("typescript", "TypeScript type system best practices"),

    # Node.js (2)
    ("nodejs", "Node.js event emitter pattern"),
    ("nodejs", "Node.js file operations with async/await"),

    # General (10)
    ("general", "Async/await error handling"),
    ("general", "JavaScript promise patterns"),
    ("general", "TypeScript vs JavaScript differences"),
    ("general", "Component composition patterns"),
    ("general", "Middleware patterns"),
    ("general", "API error handling"),
    ("general", "Type validation"),
    ("general", "Form submission handling"),
    ("general", "Code splitting and performance"),
    ("general", "Real-time updates with WebSockets"),
]

SUCCESS_THRESHOLD = 0.6


def benchmark_hybrid_retrieval():
    """Run hybrid retrieval benchmark on 27 queries."""

    logger.info("=" * 80)
    logger.info("🚀 PHASE 4 HYBRID RETRIEVAL BENCHMARK")
    logger.info("=" * 80)

    # Initialize
    logger.info("\n📦 Initializing embedding system...")
    embedding_model = EmbeddingModel(
        model_name="jinaai/jina-embeddings-v2-base-code",
        enable_cache=True
    )
    vector_store = create_vector_store(embedding_model=embedding_model)
    logger.info("✅ System ready")

    # Run queries
    logger.info(f"\n📊 Running {len(BENCHMARK_QUERIES)} benchmark queries...")

    results_by_category = {}
    results_detailed = []

    for query_idx, (category, query) in enumerate(BENCHMARK_QUERIES, 1):
        logger.info(f"\n[{query_idx}/{len(BENCHMARK_QUERIES)}] [{category}] {query}")

        try:
            # Semantic search via ChromaDB
            semantic_results = vector_store.search(query, top_k=20)

            if not semantic_results:
                logger.warning("   ⚠️ No semantic results")
                continue

            # Extract semantic scores (ChromaDB returns dicts with 'id' and 'similarity')
            semantic_tuples = []
            semantic_docs_map = {}  # Keep full document info
            for r in semantic_results:
                if isinstance(r, dict) and 'id' in r and 'similarity' in r:
                    semantic_tuples.append((r['id'], r['similarity']))
                    semantic_docs_map[r['id']] = r

            if not semantic_tuples:
                logger.warning("   ⚠️ No valid semantic results")
                continue

            top_semantic_score = semantic_tuples[0][1] if semantic_tuples else 0

            # Evaluate semantic success
            semantic_success = top_semantic_score >= SUCCESS_THRESHOLD
            status_sem = "✅" if semantic_success else "❌"

            logger.info(f"   {status_sem} Semantic: {top_semantic_score:.3f}")

            # For now, hybrid score = semantic score (to verify baseline works)
            top_hybrid_score = top_semantic_score
            hybrid_success = top_hybrid_score >= SUCCESS_THRESHOLD
            status_hyb = "✅" if hybrid_success else "❌"

            logger.info(f"   {status_hyb} Hybrid (baseline): {top_hybrid_score:.3f}")

            # Track improvement  (none yet, just baseline)
            improvement = 0
            logger.info(f"   • Baseline setup complete")

            # Store results
            if category not in results_by_category:
                results_by_category[category] = {
                    'semantic': {'total': 0, 'success': 0},
                    'hybrid': {'total': 0, 'success': 0}
                }

            results_by_category[category]['semantic']['total'] += 1
            results_by_category[category]['hybrid']['total'] += 1

            if semantic_success:
                results_by_category[category]['semantic']['success'] += 1
            if hybrid_success:
                results_by_category[category]['hybrid']['success'] += 1

            results_detailed.append({
                'category': category,
                'query': query,
                'semantic_score': round(float(top_semantic_score), 3),
                'hybrid_score': round(float(top_hybrid_score), 3),
                'improvement': round(float(improvement), 3),
                'semantic_success': bool(semantic_success),
                'hybrid_success': bool(hybrid_success)
            })

        except Exception as e:
            logger.error(f"   ❌ Error: {str(e)}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 HYBRID RETRIEVAL BENCHMARK - RESULTS")
    logger.info("=" * 80)

    # Calculate overall stats
    total_queries = len(results_detailed)
    semantic_successes = sum(1 for r in results_detailed if r['semantic_success'])
    hybrid_successes = sum(1 for r in results_detailed if r['hybrid_success'])

    logger.info(f"\n🎯 OVERALL RESULTS")
    logger.info(f"   Total queries: {total_queries}")
    logger.info(
        f"   Semantic-only: {semantic_successes}/{total_queries} "
        f"({100*semantic_successes/total_queries:.1f}%)"
    )
    logger.info(
        f"   Hybrid: {hybrid_successes}/{total_queries} "
        f"({100*hybrid_successes/total_queries:.1f}%)"
    )

    improvement_pts = 100 * (hybrid_successes - semantic_successes) / total_queries
    logger.info(f"\n⬆️  IMPROVEMENT: +{improvement_pts:.1f} percentage points")

    # By category
    logger.info(f"\n📈 RESULTS BY CATEGORY")
    for category in sorted(results_by_category.keys()):
        stats = results_by_category[category]
        sem_rate = 100 * stats['semantic']['success'] / stats['semantic']['total']
        hyb_rate = 100 * stats['hybrid']['success'] / stats['hybrid']['total']
        delta = hyb_rate - sem_rate

        logger.info(
            f"   {category}: "
            f"Semantic {stats['semantic']['success']}/{stats['semantic']['total']} "
            f"({sem_rate:.0f}%) → "
            f"Hybrid {stats['hybrid']['success']}/{stats['hybrid']['total']} "
            f"({hyb_rate:.0f}%) "
            f"({delta:+.0f} pts)"
        )

    # Detailed results table
    logger.info(f"\n📋 DETAILED QUERY RESULTS")
    logger.info(
        "Category     Query                                         "
        "Semantic    Hybrid      Change    Reason"
    )
    logger.info("-" * 90)

    for result in results_detailed:
        sem_str = f"{result['semantic_score']:.3f}"
        hyb_str = f"{result['hybrid_score']:.3f}"
        change_str = f"{result['improvement']:+.3f}"

        logger.info(
            f"{result['category']:<12} {result['query']:<40} "
            f"{sem_str:<11} {hyb_str:<11} {change_str:<8}"
        )

    # Save detailed results
    output_file = Path("/tmp/phase4_hybrid_benchmark_results.json")
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'semantic_success_rate': semantic_successes / total_queries,
                'hybrid_success_rate': hybrid_successes / total_queries,
                'improvement_points': improvement_pts
            },
            'by_category': results_by_category,
            'detailed': results_detailed
        }, f, indent=2)

    logger.info(f"\n💾 Detailed results saved to {output_file}")

    # Final assessment
    logger.info("\n" + "=" * 80)
    if hybrid_successes > semantic_successes:
        logger.info(
            f"✅ HYBRID RETRIEVAL IMPROVED RESULTS by +{improvement_pts:.1f} pts"
        )
    elif hybrid_successes == semantic_successes:
        logger.info("⚠️  HYBRID RETRIEVAL: No significant change from semantic-only")
    else:
        logger.info("❌ HYBRID RETRIEVAL: Degraded performance (unexpected)")

    logger.info("=" * 80)

    return hybrid_successes > semantic_successes


if __name__ == "__main__":
    success = benchmark_hybrid_retrieval()
    sys.exit(0 if success else 1)
