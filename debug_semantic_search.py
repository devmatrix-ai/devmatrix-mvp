"""
Debug semantic search to understand why patterns are not retrieved correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cognitive.patterns.pattern_bank import PatternBank, SemanticTaskSignature


def debug_search():
    """Debug semantic search for specific purposes."""

    bank = PatternBank()
    bank.connect()

    print("=" * 80)
    print("DEBUGGING SEMANTIC SEARCH")
    print("=" * 80)
    print()

    # Test case 1: Search for exact purpose string
    print("🔍 Test 1: Searching for EXACT purpose string")
    print("-" * 80)

    exact_purpose = "Structured logging configuration with structlog and JSON output"
    print(f"Query: {exact_purpose}")
    print()

    query_sig = SemanticTaskSignature(
        purpose=exact_purpose,
        intent="implement",
        inputs={},
        outputs={},
        domain="infrastructure",
    )

    results = bank.hybrid_search(
        signature=query_sig,
        domain="infrastructure",
        production_ready=True,
        top_k=3,
    )

    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Purpose: {r.signature.purpose}")
        print(f"     Similarity: {r.similarity_score:.4f}")
        print(f"     Domain: {r.signature.domain}")
        print()

    # Test case 2: Search for observability patterns
    print("🔍 Test 2: Generic 'production ready observability implementation'")
    print("-" * 80)

    generic_purpose = "production ready observability implementation"
    print(f"Query: {generic_purpose}")
    print()

    query_sig = SemanticTaskSignature(
        purpose=generic_purpose,
        intent="implement",
        inputs={},
        outputs={},
        domain="infrastructure",
    )

    results = bank.hybrid_search(
        signature=query_sig,
        domain="infrastructure",
        production_ready=True,
        top_k=5,
    )

    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Purpose: {r.signature.purpose}")
        print(f"     Similarity: {r.similarity_score:.4f}")
        print(f"     Domain: {r.signature.domain}")
        print()

    # Test case 3: Search ALL patterns in infrastructure domain
    print("🔍 Test 3: All infrastructure domain patterns")
    print("-" * 80)

    results = bank.hybrid_search(
        signature=query_sig,
        domain="infrastructure",
        production_ready=True,
        top_k=20,
    )

    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Purpose: {r.signature.purpose[:70]}")
        print(f"     Domain: {r.signature.domain}")
        print()


if __name__ == "__main__":
    debug_search()
