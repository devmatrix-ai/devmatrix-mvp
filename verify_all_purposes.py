"""
Verify ALL purpose strings stored in Qdrant PatternBank.

Compares what's stored vs what we're searching for in SPECIFIC_PURPOSES.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cognitive.patterns.pattern_bank import PatternBank, SemanticTaskSignature


def verify_all_purposes():
    """List ALL patterns in Qdrant grouped by domain."""

    bank = PatternBank()
    bank.connect()

    print("=" * 80)
    print("ALL PATTERNS IN QDRANT BY DOMAIN")
    print("=" * 80)
    print()

    domains = [
        "configuration",
        "data_access",
        "observability",
        "data_modeling",
        "business_logic",
        "api",
        "security",
        "testing",
        "infrastructure",
        "application",
        "documentation"
    ]

    for domain in domains:
        sig = SemanticTaskSignature(
            purpose=f"{domain}",
            intent="implement",
            inputs={},
            outputs={},
            domain=domain,
        )

        results = bank.hybrid_search(
            signature=sig,
            domain=domain,
            production_ready=True,
            top_k=20,
        )

        if results:
            print(f"📦 {domain.upper()} ({len(results)} patterns):")
            for i, r in enumerate(results, 1):
                print(f"  {i}. \"{r.signature.purpose}\"")
            print()


if __name__ == "__main__":
    verify_all_purposes()
