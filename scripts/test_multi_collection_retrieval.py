#!/usr/bin/env python
"""
Integration Test: Multi-Collection Retrieval

Tests the multi-collection retrieval system with fallback strategy.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_embedding_model
from src.rag.multi_collection_manager import MultiCollectionManager
from src.observability import get_logger

logger = get_logger("test_multi_collection")

# Test queries covering different domains
TEST_QUERIES = {
    "curated_heavy": [
        "FastAPI dependency injection pattern",
        "SQLAlchemy async orm relationships",
        "REST API versioning strategy",
        "JWT token refresh implementation",
        "Password hashing with bcrypt",
    ],
    "standards_heavy": [
        "project code structure conventions",
        "contribution guidelines best practices",
        "type hints requirements",
        "testing coverage expectations",
    ],
    "project_code_heavy": [
        "existing project database models",
        "project api endpoints",
        "project service implementations",
        "project middleware layers",
    ],
    "mixed": [
        "caching strategy implementation",
        "error handling patterns",
        "logging configuration",
        "middleware architecture",
        "decorator patterns",
    ]
}

def test_multi_collection_retrieval():
    """Test multi-collection retrieval with fallback."""
    print("\n" + "="*80)
    print("MULTI-COLLECTION RETRIEVAL INTEGRATION TEST")
    print("="*80)
    
    try:
        # Initialize
        embedding_model = create_embedding_model()
        manager = MultiCollectionManager(embedding_model)
        
        # Get collection stats
        stats = manager.get_collection_stats()
        print("\n📊 Collection Statistics:")
        print(f"  Curated: {stats['curated']['count']} examples (threshold: {stats['curated']['threshold']})")
        print(f"  Project Code: {stats['project_code']['count']} examples (threshold: {stats['project_code']['threshold']})")
        print(f"  Standards: {stats['standards']['count']} examples (threshold: {stats['standards']['threshold']})")
        print(f"  Total: {stats['total']} examples")
        
        # Test queries
        print("\n🧪 Testing Multi-Collection Retrieval:\n")
        
        overall_stats = {
            "total_queries": 0,
            "successful": 0,
            "by_category": {}
        }
        
        for category, queries in TEST_QUERIES.items():
            print(f"\n📁 Category: {category}")
            print(f"   Queries: {len(queries)}")
            
            category_results = {"total": len(queries), "found": 0, "avg_sim": 0, "sources": {}}
            
            for query in queries:
                results = manager.search_with_fallback(query, top_k=3)
                
                if results:
                    category_results["found"] += 1
                    category_results["avg_sim"] += results[0].similarity
                    
                    # Track which collection returned the result
                    source = results[0].collection
                    if source not in category_results["sources"]:
                        category_results["sources"][source] = 0
                    category_results["sources"][source] += 1
                    
                    status = "✅" if results[0].similarity > 0.7 else "⚠️ "
                    print(f"   {status} {query[:40]:40} | Sim: {results[0].similarity:.3f} | Source: {source}")
                else:
                    print(f"   ❌ {query[:40]:40} | No results found")
            
            if category_results["found"] > 0:
                category_results["avg_sim"] /= category_results["found"]
            
            success_rate = (category_results["found"] / len(queries) * 100) if queries else 0
            print(f"   Success: {category_results['found']}/{len(queries)} ({success_rate:.1f}%)")
            print(f"   Avg Similarity: {category_results['avg_sim']:.3f}")
            print(f"   Sources: {category_results['sources']}")
            
            overall_stats["by_category"][category] = category_results
            overall_stats["total_queries"] += len(queries)
            overall_stats["successful"] += category_results["found"]
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        overall_success = (overall_stats["successful"] / overall_stats["total_queries"] * 100) if overall_stats["total_queries"] else 0
        print(f"\nOverall Success Rate: {overall_stats['successful']}/{overall_stats['total_queries']} ({overall_success:.1f}%)")
        print(f"Target: >85%")
        
        if overall_success >= 85:
            print("\n✅ EXCELLENT: Multi-collection system performing above target!")
        elif overall_success >= 70:
            print("\n⚠️  GOOD: System performing well, room for improvement")
        else:
            print("\n❌ NEEDS WORK: Below target, recommend reviewing thresholds")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"\n✗ Test Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_multi_collection_retrieval()
    sys.exit(0 if success else 1)
