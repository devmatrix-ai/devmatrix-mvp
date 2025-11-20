"""
Reset and Populate Production Patterns

Clears the existing semantic_patterns collection in Qdrant
and re-populates it with the latest production-ready patterns.

This ensures semantic search retrieves correct patterns.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cognitive.patterns.pattern_bank import PatternBank
from tools.populate_production_patterns import populate_patterns


def reset_and_populate():
    """
    Reset semantic_patterns collection and re-populate with fresh patterns.
    """
    print("=" * 80)
    print("RESET AND POPULATE PRODUCTION PATTERNS")
    print("=" * 80)
    print()

    # Step 1: Initialize PatternBank
    print("📂 Initializing PatternBank...")
    bank = PatternBank()
    bank.connect()

    # Step 2: Delete existing collection
    print("🗑️  Deleting existing semantic_patterns collection...")
    try:
        bank.delete_collection()
        print("✅ Collection deleted successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not delete collection: {e}")
        print("   (This is OK if collection doesn't exist)")

    # Step 3: Recreate collection
    print("\n📦 Creating fresh collection...")
    bank.create_collection()
    print("✅ Collection created")

    # Step 4: Populate with production patterns
    print("\n📥 Populating with production-ready patterns...")
    print("=" * 80)
    populate_patterns()

    print("\n" + "=" * 80)
    print("✅ RESET AND POPULATE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    reset_and_populate()
