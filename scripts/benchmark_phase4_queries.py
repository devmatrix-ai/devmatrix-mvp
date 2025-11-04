#!/usr/bin/env python
"""
Phase 4 Query Success Benchmarking

Benchmark the 34 ingested JavaScript/TypeScript examples by running
targeted queries and measuring retrieval success rates.

Target: 85%+ query success rate
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.vector_store import create_vector_store
from src.rag.embeddings import EmbeddingModel
from src.observability import get_logger

logger = get_logger(__name__)


# Test queries organized by framework and task type
TEST_QUERIES = {
    "express": [
        "How do I create a basic Express server?",
        "Express middleware for error handling",
        "API endpoint in Express with routing",
        "Express CORS configuration",
        "Express async error wrapper",
    ],
    "react": [
        "React hooks for state management",
        "React custom hooks useAsync",
        "React form handling with hooks",
        "React Context API for state",
        "React Suspense for lazy loading",
        "useReducer pattern in React",
    ],
    "typescript": [
        "TypeScript generics for API calls",
        "TypeScript decorators for validation",
        "TypeScript discriminated union types",
        "TypeScript type system best practices",
    ],
    "nodejs": [
        "Node.js event emitter pattern",
        "Node.js file operations with async/await",
    ],
    "general": [
        "Async/await error handling",
        "JavaScript promise patterns",
        "TypeScript vs JavaScript differences",
        "Component composition patterns",
        "Middleware patterns",
        "API error handling",
        "Type validation",
        "Form submission handling",
        "Code splitting and performance",
        "Real-time updates with WebSockets",
    ],
}


class Phase4Benchmark:
    """Benchmark Phase 4 RAG system."""

    def __init__(self):
        self.vector_store = None
        self.queries = self._flatten_queries()
        self.results = {
            "total_queries": len(self.queries),
            "successful_queries": 0,
            "failed_queries": 0,
            "query_results": [],
        }

    def _flatten_queries(self) -> List[Tuple[str, str]]:
        """Flatten query dict into list of (category, query) tuples."""
        queries = []
        for category, query_list in TEST_QUERIES.items():
            for query in query_list:
                queries.append((category, query))
        return queries

    def _initialize_vector_store(self) -> bool:
        """Initialize connection to ChromaDB."""
        try:
            logger.info("Initializing embedding model...")
            embedding_model = EmbeddingModel(model_name="all-mpnet-base-v2", enable_cache=True)
            logger.info(f"✅ Embedding model ready (dim: {embedding_model.dimension})")

            logger.info("Connecting to ChromaDB...")
            self.vector_store = create_vector_store(embedding_model=embedding_model)
            logger.info("✅ Connected to ChromaDB")

            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector store: {str(e)}")
            return False

    def run_query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Run a single query against the vector store."""
        try:
            results = self.vector_store.search(query=query, top_k=top_k)
            return results
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return []

    def is_relevant(self, query: str, results: List[Dict[str, Any]]) -> bool:
        """
        Determine if query results are relevant.

        A query is considered successful if:
        1. At least one result is returned
        2. The top result has similarity >= 0.6
        """
        if not results:
            return False

        # Check if top result has decent similarity
        top_result = results[0]
        similarity = top_result.get("similarity", 0)

        return similarity >= 0.6

    def benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        logger.info("=" * 80)
        logger.info("🚀 PHASE 4 QUERY SUCCESS BENCHMARKING")
        logger.info("=" * 80)

        # Initialize
        if not self._initialize_vector_store():
            return self.results

        logger.info(f"\n📊 Running {len(self.queries)} benchmark queries...")

        # Run each query
        for idx, (category, query) in enumerate(self.queries, 1):
            logger.info(f"\n[{idx}/{len(self.queries)}] [{category}] {query}")

            # Execute query
            results = self.run_query(query, top_k=5)

            # Check if relevant
            is_relevant = self.is_relevant(query, results)
            status = "✅ SUCCESS" if is_relevant else "❌ FAILED"

            logger.info(f"   {status}")

            if results:
                top_result = results[0]
                logger.info(f"   Top result similarity: {top_result.get('similarity', 'N/A'):.3f}")
                pattern = top_result.get("metadatas", {}).get("pattern", "unknown")
                logger.info(f"   Pattern: {pattern}")

            # Record result
            self.results["query_results"].append({
                "category": category,
                "query": query,
                "successful": is_relevant,
                "result_count": len(results),
                "top_similarity": results[0].get("similarity", 0) if results else 0,
            })

            if is_relevant:
                self.results["successful_queries"] += 1
            else:
                self.results["failed_queries"] += 1

        # Calculate final metrics
        self._calculate_metrics()

        return self.results

    def _calculate_metrics(self) -> None:
        """Calculate final benchmark metrics."""
        total = self.results["total_queries"]
        successful = self.results["successful_queries"]

        success_rate = (successful / total * 100) if total > 0 else 0

        # By category metrics
        category_results = {}
        for result in self.results["query_results"]:
            category = result["category"]
            if category not in category_results:
                category_results[category] = {"total": 0, "successful": 0}

            category_results[category]["total"] += 1
            if result["successful"]:
                category_results[category]["successful"] += 1

        category_metrics = {}
        for category, stats in category_results.items():
            cat_rate = (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
            category_metrics[category] = {
                "total": stats["total"],
                "successful": stats["successful"],
                "success_rate": round(cat_rate, 1),
            }

        self.results["metrics"] = {
            "total_queries": total,
            "successful_queries": successful,
            "failed_queries": self.results["failed_queries"],
            "success_rate": round(success_rate, 1),
            "by_category": category_metrics,
        }


def print_benchmark_results(results: Dict[str, Any]) -> None:
    """Print formatted benchmark results."""
    metrics = results.get("metrics", {})

    print("\n" + "=" * 80)
    print("📊 PHASE 4 QUERY SUCCESS BENCHMARKING - RESULTS")
    print("=" * 80)

    print(f"\n🎯 OVERALL RESULTS")
    print(f"   Total queries: {metrics.get('total_queries', 0)}")
    print(f"   Successful: {metrics.get('successful_queries', 0)}")
    print(f"   Failed: {metrics.get('failed_queries', 0)}")
    print(f"   Success rate: {metrics.get('success_rate', 0)}%")

    # Check if meets target
    success_rate = metrics.get("success_rate", 0)
    if success_rate >= 85:
        status = "🟢 TARGET MET - 85%+ success rate achieved!"
    elif success_rate >= 75:
        status = "🟡 GOOD - 75-85% success rate"
    else:
        status = "🔴 NEEDS IMPROVEMENT - Below 75% success"

    print(f"\n{status}")

    # By category
    print(f"\n📈 RESULTS BY CATEGORY")
    by_category = metrics.get("by_category", {})
    for category, stats in sorted(by_category.items(), key=lambda x: -x[1]["success_rate"]):
        print(f"   {category:12} - {stats['successful']}/{stats['total']} ({stats['success_rate']}%)")

    # Detailed results
    print(f"\n📋 DETAILED QUERY RESULTS")
    print(f"{'Category':<12} {'Query':<45} {'Result':<15} {'Similarity':<12}")
    print("-" * 84)

    for result in results.get("query_results", []):
        status_icon = "✅" if result["successful"] else "❌"
        similarity = f"{result.get('top_similarity', 0):.3f}"
        query_short = result["query"][:42] + "..." if len(result["query"]) > 42 else result["query"]

        print(f"{result['category']:<12} {query_short:<45} {status_icon:<15} {similarity:<12}")

    print("\n" + "=" * 80)

    # Summary
    if success_rate >= 85:
        print("✅ PHASE 4 BENCHMARK PASSED - Ready for production deployment")
    elif success_rate >= 75:
        print("⚠️  PHASE 4 BENCHMARK PASSED (with caution) - Consider optimization before production")
    else:
        print("❌ PHASE 4 BENCHMARK FAILED - Requires additional work")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    benchmark = Phase4Benchmark()
    results = benchmark.benchmark()
    print_benchmark_results(results)
