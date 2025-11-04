#!/usr/bin/env python
"""
Combine all Phase 4 examples:
- 34 seed examples (pragmatic curation)
- 18 gap-filling examples (targeted at failures)
- Plus placeholder for GitHub extracted examples (when available)

Total: 52 examples (+ GitHub when extraction completes)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_and_benchmark_phase4 import collect_all_examples as get_seed_examples
from scripts.create_phase4_gap_examples import get_gap_examples
from src.observability import get_logger

logger = get_logger(__name__)


def collect_all_phase4_examples():
    """Collect all Phase 4 examples (seed + gap-filling)."""

    logger.info("=" * 80)
    logger.info("📦 PHASE 4 COMBINED EXAMPLES COLLECTION")
    logger.info("=" * 80)

    # Get seed examples
    logger.info("\n1️⃣  Loading seed examples...")
    seed_examples = get_seed_examples()
    logger.info(f"   ✅ Seed examples: {len(seed_examples)}")

    # Get gap-filling examples
    logger.info("\n2️⃣  Loading gap-filling examples...")
    gap_examples = get_gap_examples()
    logger.info(f"   ✅ Gap-filling examples: {len(gap_examples)}")

    # Combine - convert gap examples to tuple format
    all_examples = list(seed_examples)  # Already in (code, metadata) format

    # Convert gap examples to same format
    for gap_ex in gap_examples:
        code = gap_ex.get("code", "")
        metadata = {k: v for k, v in gap_ex.items() if k != "code"}
        all_examples.append((code, metadata))

    logger.info(f"\n✨ Total examples collected: {len(all_examples)}")
    logger.info(f"   • Seed: {len(seed_examples)}")
    logger.info(f"   • Gap-filling: {len(gap_examples)}")

    # Analyze combined set
    frameworks = {}
    languages = {}
    task_types = {}
    patterns = {}

    for item in all_examples:
        if isinstance(item, tuple):
            code, metadata = item
        else:
            continue
        fw = metadata.get("framework", "unknown")
        frameworks[fw] = frameworks.get(fw, 0) + 1

        lang = metadata.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1

        task = metadata.get("task_type", "unknown")
        task_types[task] = task_types.get(task, 0) + 1

        pattern = metadata.get("pattern", "unknown")
        patterns[pattern] = patterns.get(pattern, 0) + 1

    logger.info("\n📊 Framework distribution:")
    for fw, count in sorted(frameworks.items(), key=lambda x: -x[1]):
        pct = (count / len(all_examples)) * 100
        logger.info(f"   • {fw}: {count} ({pct:.1f}%)")

    logger.info("\n📝 Language distribution:")
    for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
        pct = (count / len(all_examples)) * 100
        logger.info(f"   • {lang}: {count} ({pct:.1f}%)")

    logger.info("\n🎯 Task types:")
    for task, count in sorted(task_types.items(), key=lambda x: -x[1]):
        logger.info(f"   • {task}: {count}")

    logger.info(f"\n🎪 Pattern diversity: {len(patterns)} unique patterns")

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Combined collection ready: {len(all_examples)} examples")
    logger.info("   Ready for ingestion into ChromaDB")
    logger.info("=" * 80)

    return all_examples


if __name__ == "__main__":
    examples = collect_all_phase4_examples()
