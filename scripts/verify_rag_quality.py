#!/usr/bin/env python
"""
RAG Quality Verification Script

Verifies that the RAG system has good coverage for planning and implementation tasks.
Tests retrieval quality with predefined queries across multiple categories.

Usage:
    python scripts/verify_rag_quality.py [--detailed] [--min-similarity 0.7]
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
    create_retriever,
    RetrievalStrategy,
)
from src.observability import get_logger

logger = get_logger("verify_rag_quality")


@dataclass
class TestQuery:
    """Test query with expected results."""
    query: str
    category: str
    min_results_expected: int = 2
    min_avg_similarity: float = 0.7


# Test queries organized by category
TEST_QUERIES: List[TestQuery] = [
    # ============================================================
    # Planning & Task Decomposition
    # ============================================================
    TestQuery(
        query="how to decompose a REST API project with authentication into tasks",
        category="planning",
        min_results_expected=2,
    ),
    TestQuery(
        query="microservices architecture task breakdown with event-driven communication",
        category="planning",
        min_results_expected=2,
    ),
    TestQuery(
        query="data pipeline ETL project task decomposition",
        category="planning",
        min_results_expected=1,
    ),
    TestQuery(
        query="CLI application implementation tasks",
        category="planning",
        min_results_expected=1,
    ),
    TestQuery(
        query="task dependencies and ordering for complex project",
        category="planning",
        min_results_expected=1,
    ),
    
    # ============================================================
    # Security Patterns
    # ============================================================
    TestQuery(
        query="JWT authentication with token refresh and revocation",
        category="security",
        min_results_expected=2,
    ),
    TestQuery(
        query="password hashing with bcrypt best practices",
        category="security",
        min_results_expected=2,
    ),
    TestQuery(
        query="role-based access control RBAC implementation",
        category="security",
        min_results_expected=2,
    ),
    TestQuery(
        query="input validation to prevent SQL injection",
        category="security",
        min_results_expected=2,
    ),
    TestQuery(
        query="XSS protection and HTML sanitization",
        category="security",
        min_results_expected=1,
    ),
    TestQuery(
        query="password strength validation policy",
        category="security",
        min_results_expected=1,
    ),
    
    # ============================================================
    # Performance Optimization
    # ============================================================
    TestQuery(
        query="prevent N+1 queries in SQLAlchemy with eager loading",
        category="performance",
        min_results_expected=2,
    ),
    TestQuery(
        query="database query optimization selectinload joinedload",
        category="performance",
        min_results_expected=2,
    ),
    TestQuery(
        query="Redis caching strategies and patterns",
        category="performance",
        min_results_expected=2,
    ),
    TestQuery(
        query="cache-aside pattern implementation",
        category="performance",
        min_results_expected=1,
    ),
    TestQuery(
        query="async concurrent requests with asyncio gather",
        category="performance",
        min_results_expected=1,
    ),
    TestQuery(
        query="batch processing to avoid large IN clauses",
        category="performance",
        min_results_expected=1,
    ),
    
    # ============================================================
    # Testing Patterns
    # ============================================================
    TestQuery(
        query="pytest fixtures for async database testing",
        category="testing",
        min_results_expected=2,
    ),
    TestQuery(
        query="API testing with authentication headers",
        category="testing",
        min_results_expected=2,
    ),
    TestQuery(
        query="mocking async functions with AsyncMock",
        category="testing",
        min_results_expected=2,
    ),
    TestQuery(
        query="parametrized tests with pytest.mark.parametrize",
        category="testing",
        min_results_expected=1,
    ),
    TestQuery(
        query="integration tests with test client and database rollback",
        category="testing",
        min_results_expected=2,
    ),
    TestQuery(
        query="mocking external services with patch decorator",
        category="testing",
        min_results_expected=1,
    ),
    
    # ============================================================
    # Observability
    # ============================================================
    TestQuery(
        query="structured logging with correlation IDs",
        category="observability",
        min_results_expected=2,
    ),
    TestQuery(
        query="request/response logging middleware for FastAPI",
        category="observability",
        min_results_expected=1,
    ),
    TestQuery(
        query="timing context manager for performance logging",
        category="observability",
        min_results_expected=1,
    ),
    TestQuery(
        query="error logging with stack traces and context",
        category="observability",
        min_results_expected=1,
    ),
    
    # ============================================================
    # Architecture & Patterns
    # ============================================================
    TestQuery(
        query="repository pattern with SQLAlchemy async",
        category="architecture",
        min_results_expected=1,
    ),
    TestQuery(
        query="service layer with business logic separation",
        category="architecture",
        min_results_expected=1,
    ),
    TestQuery(
        query="dependency injection in FastAPI",
        category="architecture",
        min_results_expected=1,
    ),
]


def verify_rag_quality(
    retriever,
    vector_store,
    test_queries: List[TestQuery],
    top_k: int = 3,
    min_similarity: float = 0.7,
    detailed: bool = False,
) -> Dict[str, Any]:
    """
    Verify RAG quality with test queries.
    
    Args:
        retriever: RAG retriever instance
        vector_store: Vector store instance
        test_queries: List of test queries
        top_k: Number of results to retrieve
        min_similarity: Minimum similarity threshold
        detailed: Show detailed results
    
    Returns:
        Verification results dictionary
    """
    results = []
    total_queries = len(test_queries)
    passed_queries = 0
    
    print("\n" + "=" * 80)
    print("RAG QUALITY VERIFICATION")
    print("=" * 80)
    
    # Get vector store stats
    stats = vector_store.get_stats()
    total_examples = stats.get("total_examples", 0)
    print(f"\n📊 Vector Store Stats:")
    print(f"  Total examples: {total_examples}")
    
    if total_examples == 0:
        print("\n❌ ERROR: Vector store is empty!")
        print("   Please run seeding scripts first:")
        print("   - python scripts/seed_enhanced_patterns.py")
        print("   - python scripts/migrate_existing_code.py")
        return {
            "total_queries": total_queries,
            "passed_queries": 0,
            "failed_queries": total_queries,
            "coverage": 0.0,
            "avg_similarity": 0.0,
            "results": []
        }
    
    print(f"\n📝 Running {total_queries} test queries (top_k={top_k}, min_similarity={min_similarity})...")
    print("-" * 80)
    
    # Group queries by category
    categories = {}
    for tq in test_queries:
        categories.setdefault(tq.category, []).append(tq)
    
    # Run queries
    for category, queries in sorted(categories.items()):
        print(f"\n🔍 Category: {category.upper()}")
        print("-" * 80)
        
        for tq in queries:
            try:
                # Retrieve examples
                examples = retriever.retrieve(
                    tq.query,
                    top_k=top_k,
                    min_similarity=min_similarity
                )
                
                # Calculate metrics
                found = len(examples)
                avg_sim = sum(e.similarity for e in examples) / len(examples) if examples else 0.0
                
                # Check if query passed
                passed = (
                    found >= tq.min_results_expected and
                    avg_sim >= tq.min_avg_similarity
                )
                
                if passed:
                    passed_queries += 1
                
                # Store result
                result = {
                    "query": tq.query,
                    "category": tq.category,
                    "found": found,
                    "expected": tq.min_results_expected,
                    "avg_similarity": avg_sim,
                    "passed": passed,
                    "examples": examples if detailed else []
                }
                results.append(result)
                
                # Print result
                status = "✅" if passed else "❌"
                query_short = tq.query[:60] + "..." if len(tq.query) > 60 else tq.query
                print(f"{status} {query_short:<63} Found: {found}/{tq.min_results_expected} (avg: {avg_sim:.3f})")
                
                # Show details if requested
                if detailed and examples:
                    for i, ex in enumerate(examples[:2], 1):  # Show top 2
                        pattern = ex.metadata.get("pattern", "unknown")
                        framework = ex.metadata.get("framework", "")
                        print(f"     {i}. {pattern:<20} [{framework}] sim={ex.similarity:.3f}")
            
            except Exception as e:
                logger.error(f"Query failed", query=tq.query, error=str(e))
                result = {
                    "query": tq.query,
                    "category": tq.category,
                    "found": 0,
                    "expected": tq.min_results_expected,
                    "avg_similarity": 0.0,
                    "passed": False,
                    "error": str(e)
                }
                results.append(result)
                print(f"❌ {tq.query[:63]:<63} ERROR: {str(e)[:20]}")
    
    # Calculate overall metrics
    coverage = (passed_queries / total_queries) * 100 if total_queries > 0 else 0
    total_found = sum(r["found"] for r in results)
    total_expected = sum(r["expected"] for r in results)
    avg_similarity = sum(r["avg_similarity"] for r in results) / len(results) if results else 0
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✓ Passed queries: {passed_queries}/{total_queries} ({coverage:.1f}%)")
    print(f"✗ Failed queries: {total_queries - passed_queries}/{total_queries}")
    print(f"📊 Total results: {total_found}/{total_expected} expected")
    print(f"📈 Average similarity: {avg_similarity:.3f}")
    
    # Category breakdown
    print(f"\n📋 Category Breakdown:")
    for category in sorted(categories.keys()):
        cat_results = [r for r in results if r["category"] == category]
        cat_passed = sum(1 for r in cat_results if r["passed"])
        cat_total = len(cat_results)
        cat_pct = (cat_passed / cat_total * 100) if cat_total > 0 else 0
        status = "✅" if cat_pct >= 80 else "⚠️" if cat_pct >= 60 else "❌"
        print(f"  {status} {category:<20} {cat_passed}/{cat_total} ({cat_pct:.0f}%)")
    
    # Overall assessment
    print(f"\n🎯 Overall Assessment:")
    if coverage >= 90 and avg_similarity >= 0.75:
        print("  ✅ EXCELLENT - RAG is production-ready!")
    elif coverage >= 80 and avg_similarity >= 0.70:
        print("  ⚠️  GOOD - RAG is functional but could be improved")
    elif coverage >= 60:
        print("  ⚠️  FAIR - RAG needs more examples in weak categories")
    else:
        print("  ❌ POOR - RAG needs significant improvement")
    
    # Recommendations
    failed_categories = {}
    for r in results:
        if not r["passed"]:
            failed_categories.setdefault(r["category"], []).append(r["query"])
    
    if failed_categories:
        print(f"\n💡 Recommendations:")
        for cat, queries in failed_categories.items():
            print(f"  • Add more {cat} examples ({len(queries)} weak queries)")
    
    return {
        "total_queries": total_queries,
        "passed_queries": passed_queries,
        "failed_queries": total_queries - passed_queries,
        "coverage": coverage,
        "avg_similarity": avg_similarity,
        "results": results,
        "failed_categories": failed_categories,
    }


def export_results(results: Dict[str, Any], output_file: str):
    """Export verification results to JSON file."""
    import json
    from datetime import datetime
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_queries": results["total_queries"],
            "passed_queries": results["passed_queries"],
            "failed_queries": results["failed_queries"],
            "coverage": results["coverage"],
            "avg_similarity": results["avg_similarity"],
        },
        "results": results["results"],
        "failed_categories": results["failed_categories"],
    }
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results exported to: {output_file}")


def main():
    """Main verification script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify RAG quality and coverage")
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed results for each query",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.7,
        help="Minimum similarity threshold (default: 0.7)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of results to retrieve (default: 3)",
    )
    parser.add_argument(
        "--category",
        choices=["all", "planning", "security", "performance", "testing", "observability", "architecture"],
        default="all",
        help="Test only specific category",
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to JSON file",
    )
    
    args = parser.parse_args()
    
    # Filter queries by category if specified
    if args.category != "all":
        queries_to_test = [q for q in TEST_QUERIES if q.category == args.category]
    else:
        queries_to_test = TEST_QUERIES
    
    # Initialize RAG components
    try:
        logger.info("Initializing RAG components...")
        embedding_model = create_embedding_model()
        vector_store = create_vector_store(embedding_model)
        retriever = create_retriever(
            vector_store,
            strategy=RetrievalStrategy.MMR,  # Use MMR for diversity
            top_k=args.top_k
        )
        
        logger.info("RAG components initialized")
    
    except Exception as e:
        logger.error("Failed to initialize RAG", error=str(e))
        print(f"\n❌ Initialization failed: {str(e)}")
        print("\nPlease ensure:")
        print("  1. ChromaDB is running: docker-compose up chromadb -d")
        print("  2. CHROMADB_HOST and CHROMADB_PORT are configured in .env")
        return 1
    
    # Run verification
    try:
        results = verify_rag_quality(
            retriever=retriever,
            vector_store=vector_store,
            test_queries=queries_to_test,
            top_k=args.top_k,
            min_similarity=args.min_similarity,
            detailed=args.detailed,
        )
        
        # Export if requested
        if args.export:
            export_results(results, args.export)
        
        # Exit code based on coverage
        if results["coverage"] >= 80:
            return 0
        else:
            return 1
    
    except Exception as e:
        logger.error("Verification failed", error=str(e))
        print(f"\n❌ Verification failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

