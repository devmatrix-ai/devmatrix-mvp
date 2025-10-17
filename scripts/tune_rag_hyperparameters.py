#!/usr/bin/env python
"""
RAG Hyperparameter Tuning Script

Automated tuning of RAG system hyperparameters using grid search.
Optimizes similarity_threshold, top_k, and mmr_lambda for best retrieval quality.

Usage:
    python scripts/tune_rag_hyperparameters.py [--test-queries queries.json] [--quick]
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    RetrievalStrategy,
)
from src.observability import get_logger

logger = get_logger("tune_rag_hyperparameters")


@dataclass
class HyperparameterConfig:
    """Hyperparameter configuration."""

    top_k: int
    similarity_threshold: float
    mmr_lambda: float
    strategy: RetrievalStrategy


@dataclass
class TuningResult:
    """Result of hyperparameter tuning."""

    config: HyperparameterConfig
    avg_retrieval_time: float
    avg_similarity: float
    avg_results_count: float
    relevance_score: float
    diversity_score: float
    overall_score: float


# Test queries for tuning
DEFAULT_TEST_QUERIES = [
    {
        "query": "authenticate user with JWT token",
        "expected_patterns": ["authentication", "jwt"],
    },
    {
        "query": "create database record with validation",
        "expected_patterns": ["crud", "validation"],
    },
    {
        "query": "handle API errors with logging",
        "expected_patterns": ["error_handling", "logging"],
    },
    {
        "query": "async concurrent HTTP requests",
        "expected_patterns": ["async", "concurrent"],
    },
    {
        "query": "cache frequently accessed data",
        "expected_patterns": ["caching", "optimization"],
    },
    {
        "query": "paginated list of items with filters",
        "expected_patterns": ["pagination", "filtering"],
    },
    {
        "query": "test API endpoint with fixtures",
        "expected_patterns": ["testing", "fixtures"],
    },
    {
        "query": "validate user input with Pydantic",
        "expected_patterns": ["validation", "pydantic"],
    },
]


class HyperparameterTuner:
    """Automated hyperparameter tuning for RAG system."""

    def __init__(self, vector_store, test_queries: List[Dict[str, Any]] = None):
        self.vector_store = vector_store
        self.test_queries = test_queries or DEFAULT_TEST_QUERIES
        self.embedding_model = None

    def tune(
        self,
        parameter_grid: Dict[str, List[Any]] = None,
        quick_mode: bool = False,
    ) -> List[TuningResult]:
        """
        Run hyperparameter tuning.

        Args:
            parameter_grid: Grid of parameters to search
            quick_mode: Use smaller grid for faster tuning

        Returns:
            List of tuning results sorted by overall score
        """
        if parameter_grid is None:
            if quick_mode:
                parameter_grid = {
                    "top_k": [3, 5],
                    "similarity_threshold": [0.65, 0.75],
                    "mmr_lambda": [0.6, 0.8],
                    "strategy": [RetrievalStrategy.MMR],
                }
            else:
                parameter_grid = {
                    "top_k": [3, 5, 7, 10],
                    "similarity_threshold": [0.6, 0.65, 0.7, 0.75, 0.8],
                    "mmr_lambda": [0.5, 0.6, 0.7, 0.8],
                    "strategy": [
                        RetrievalStrategy.SIMILARITY,
                        RetrievalStrategy.MMR,
                    ],
                }

        logger.info("Starting hyperparameter tuning")
        logger.info(f"Test queries: {len(self.test_queries)}")

        # Generate all parameter combinations
        configs = self._generate_configs(parameter_grid)

        logger.info(f"Testing {len(configs)} configurations")

        # Test each configuration
        results = []

        for i, config in enumerate(configs, 1):
            logger.info(
                f"Testing config {i}/{len(configs)}",
                top_k=config.top_k,
                threshold=config.similarity_threshold,
                mmr_lambda=config.mmr_lambda,
                strategy=config.strategy.value,
            )

            result = self._evaluate_config(config)
            results.append(result)

            logger.info(
                f"Config {i} score: {result.overall_score:.3f}",
                retrieval_time=f"{result.avg_retrieval_time:.0f}ms",
                similarity=f"{result.avg_similarity:.3f}",
                relevance=f"{result.relevance_score:.3f}",
            )

        # Sort by overall score
        results.sort(key=lambda r: r.overall_score, reverse=True)

        logger.info("Tuning complete")

        return results

    def _generate_configs(
        self, parameter_grid: Dict[str, List[Any]]
    ) -> List[HyperparameterConfig]:
        """Generate all parameter combinations."""
        configs = []

        for top_k in parameter_grid["top_k"]:
            for threshold in parameter_grid["similarity_threshold"]:
                for mmr_lambda in parameter_grid["mmr_lambda"]:
                    for strategy in parameter_grid["strategy"]:
                        # Skip mmr_lambda for non-MMR strategies
                        if strategy != RetrievalStrategy.MMR and mmr_lambda != 0.7:
                            continue

                        configs.append(
                            HyperparameterConfig(
                                top_k=top_k,
                                similarity_threshold=threshold,
                                mmr_lambda=mmr_lambda,
                                strategy=strategy,
                            )
                        )

        return configs

    def _evaluate_config(self, config: HyperparameterConfig) -> TuningResult:
        """Evaluate a configuration against test queries."""
        # Create retriever with config
        retriever = create_retriever(
            self.vector_store,
            strategy=config.strategy,
            top_k=config.top_k,
            mmr_lambda=config.mmr_lambda,
            cache_enabled=False,  # Disable cache for fair comparison
        )

        # Run test queries
        retrieval_times = []
        similarities = []
        results_counts = []
        relevance_scores = []

        for test in self.test_queries:
            start = time.time()

            results = retriever.retrieve(
                query=test["query"],
                min_similarity=config.similarity_threshold,
            )

            duration = (time.time() - start) * 1000  # Convert to ms

            retrieval_times.append(duration)
            results_counts.append(len(results))

            if results:
                # Average similarity
                avg_sim = sum(r.similarity for r in results) / len(results)
                similarities.append(avg_sim)

                # Relevance score (how many expected patterns found)
                relevance = self._calculate_relevance(results, test["expected_patterns"])
                relevance_scores.append(relevance)
            else:
                similarities.append(0.0)
                relevance_scores.append(0.0)

        # Calculate diversity score (for MMR)
        diversity_score = 0.0
        if config.strategy == RetrievalStrategy.MMR:
            diversity_score = config.mmr_lambda  # Use lambda as proxy

        # Calculate overall metrics
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times)
        avg_similarity = sum(similarities) / len(similarities)
        avg_results_count = sum(results_counts) / len(results_counts)
        avg_relevance = sum(relevance_scores) / len(relevance_scores)

        # Calculate overall score (weighted)
        # Prioritize relevance, then similarity, then speed
        overall_score = (
            avg_relevance * 0.5  # 50% relevance
            + avg_similarity * 0.3  # 30% similarity
            + min(1.0, 100 / avg_retrieval_time) * 0.1  # 10% speed (cap at 100ms)
            + min(1.0, avg_results_count / config.top_k) * 0.1  # 10% results count
        )

        return TuningResult(
            config=config,
            avg_retrieval_time=avg_retrieval_time,
            avg_similarity=avg_similarity,
            avg_results_count=avg_results_count,
            relevance_score=avg_relevance,
            diversity_score=diversity_score,
            overall_score=overall_score,
        )

    def _calculate_relevance(
        self, results: List[Any], expected_patterns: List[str]
    ) -> float:
        """Calculate relevance score based on expected patterns."""
        if not results or not expected_patterns:
            return 0.0

        # Check how many expected patterns are found in results
        found_patterns = set()

        for result in results:
            metadata = result.metadata
            pattern = metadata.get("pattern", "")

            for expected in expected_patterns:
                if expected in pattern:
                    found_patterns.add(expected)

        # Relevance is percentage of expected patterns found
        relevance = len(found_patterns) / len(expected_patterns)

        return relevance


def print_results(results: List[TuningResult], top_n: int = 10):
    """Print tuning results in a readable format."""
    print("\n" + "=" * 80)
    print(f"Top {min(top_n, len(results))} Configurations")
    print("=" * 80)

    for i, result in enumerate(results[:top_n], 1):
        config = result.config

        print(f"\n{i}. Overall Score: {result.overall_score:.3f}")
        print("   " + "-" * 76)
        print(f"   Strategy: {config.strategy.value}")
        print(f"   Top-K: {config.top_k}")
        print(f"   Similarity Threshold: {config.similarity_threshold}")
        print(f"   MMR Lambda: {config.mmr_lambda}")
        print()
        print(f"   Metrics:")
        print(f"     Relevance Score:    {result.relevance_score:.3f} ⭐")
        print(f"     Avg Similarity:     {result.avg_similarity:.3f}")
        print(f"     Avg Retrieval Time: {result.avg_retrieval_time:.1f}ms")
        print(f"     Avg Results Count:  {result.avg_results_count:.1f}")

        if i == 1:
            print("\n   ✅ RECOMMENDED CONFIGURATION")


def save_results(results: List[TuningResult], output_path: Path):
    """Save tuning results to JSON file."""
    results_data = []

    for result in results:
        result_dict = {
            "config": {
                "top_k": result.config.top_k,
                "similarity_threshold": result.config.similarity_threshold,
                "mmr_lambda": result.config.mmr_lambda,
                "strategy": result.config.strategy.value,
            },
            "metrics": {
                "overall_score": result.overall_score,
                "relevance_score": result.relevance_score,
                "avg_similarity": result.avg_similarity,
                "avg_retrieval_time": result.avg_retrieval_time,
                "avg_results_count": result.avg_results_count,
                "diversity_score": result.diversity_score,
            },
        }

        results_data.append(result_dict)

    output_path.write_text(json.dumps(results_data, indent=2))
    logger.info(f"Results saved to {output_path}")


def generate_env_config(result: TuningResult) -> str:
    """Generate .env configuration from best result."""
    config = result.config

    env_config = f"""
# RAG Hyperparameters (Tuned on {time.strftime('%Y-%m-%d %H:%M:%S')})
# Overall Score: {result.overall_score:.3f}
RAG_TOP_K={config.top_k}
RAG_SIMILARITY_THRESHOLD={config.similarity_threshold}
RAG_MMR_LAMBDA={config.mmr_lambda}
RAG_STRATEGY={config.strategy.value}

# Performance Metrics
# - Relevance Score: {result.relevance_score:.3f}
# - Avg Similarity: {result.avg_similarity:.3f}
# - Avg Retrieval Time: {result.avg_retrieval_time:.1f}ms
# - Avg Results Count: {result.avg_results_count:.1f}
"""

    return env_config.strip()


def main():
    """Main tuning script."""
    import argparse

    parser = argparse.ArgumentParser(description="Tune RAG hyperparameters")
    parser.add_argument(
        "--test-queries",
        type=str,
        help="Path to JSON file with test queries",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode with smaller parameter grid",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tuning_results.json",
        help="Output file for results (default: tuning_results.json)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top results to display (default: 10)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("RAG Hyperparameter Tuning")
    print("=" * 80)

    if args.quick:
        print("\n⚡ Quick mode enabled (smaller parameter grid)")

    # Load test queries
    test_queries = None

    if args.test_queries:
        queries_path = Path(args.test_queries)

        if not queries_path.exists():
            print(f"\n❌ Test queries file not found: {queries_path}")
            return 1

        try:
            test_queries = json.loads(queries_path.read_text())
            print(f"\n📋 Loaded {len(test_queries)} test queries from {queries_path}")
        except Exception as e:
            print(f"\n❌ Failed to load test queries: {str(e)}")
            return 1
    else:
        print(f"\n📋 Using {len(DEFAULT_TEST_QUERIES)} default test queries")

    # Initialize RAG components
    try:
        logger.info("Initializing RAG components...")
        embedding_model = create_embedding_model()
        vector_store = create_vector_store(embedding_model)

        # Check if vector store has data
        stats = vector_store.get_stats()
        total_examples = stats.get("total_examples", 0)

        if total_examples == 0:
            print("\n⚠️  Warning: Vector store is empty!")
            print("   Please run seed or migration scripts first:")
            print("   - python scripts/seed_rag_examples.py")
            print("   - python scripts/migrate_existing_code.py")
            return 1

        print(f"\n📊 Vector store has {total_examples} examples")

        logger.info("RAG components initialized")

    except Exception as e:
        logger.error("Failed to initialize RAG", error=str(e))
        print(f"\n❌ Initialization failed: {str(e)}")
        print("\nPlease ensure:")
        print("  1. ChromaDB is running: docker-compose up chromadb -d")
        print("  2. CHROMADB_HOST and CHROMADB_PORT are configured in .env")
        return 1

    # Create tuner
    tuner = HyperparameterTuner(vector_store, test_queries)

    # Run tuning
    try:
        print("\n🔄 Starting hyperparameter tuning...\n")

        results = tuner.tune(quick_mode=args.quick)

        # Print results
        print_results(results, top_n=args.top_n)

        # Save results
        output_path = Path(args.output)
        save_results(results, output_path)

        print(f"\n💾 Full results saved to: {output_path}")

        # Generate .env config
        best_config = generate_env_config(results[0])

        print("\n" + "=" * 80)
        print("Recommended .env Configuration")
        print("=" * 80)
        print(best_config)

        # Save .env config
        env_path = Path("tuning_best_config.env")
        env_path.write_text(best_config)

        print(f"\n💾 Configuration saved to: {env_path}")
        print("\nTo apply, copy these values to your .env file")

        print("\n✅ Tuning complete!")

        return 0

    except Exception as e:
        logger.error("Tuning failed", error=str(e))
        print(f"\n❌ Tuning failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
