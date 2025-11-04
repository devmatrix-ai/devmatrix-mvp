#!/usr/bin/env python3
"""
PHASE 1 ORCHESTRATOR: Reset ChromaDB, Seed Examples, Run Baseline Benchmark

Executes:
1. Seed TypeScript/JavaScript docs (from seed_typescript_docs.py)
2. Seed Official Docs (from seed_official_docs.py)
3. Run baseline benchmark

Usage:
    python scripts/phase1_execute.py
"""

import sys
import subprocess
import time
import json
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability import get_logger
from src.rag import create_retriever, create_vector_store, create_embedding_model, RetrievalStrategy

logger = get_logger(__name__)


def run_command(cmd: List[str], description: str) -> bool:
    """Execute a command and report results"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 {description}")
    logger.info(f"{'='*60}")
    logger.info(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=False,
            timeout=600,
        )
        if result.returncode == 0:
            logger.info(f"✅ {description} completed")
            return True
        else:
            logger.error(f"❌ {description} failed with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} timed out (600s)")
        return False
    except Exception as e:
        logger.error(f"❌ {description} error: {e}")
        return False


def run_benchmark() -> Dict:
    """Run baseline benchmark"""
    logger.info(f"\n{'='*60}")
    logger.info("🧪 BASELINE BENCHMARK (SIMILARITY)")
    logger.info(f"{'='*60}")

    try:
        embeddings = create_embedding_model()
        vector_store = create_vector_store(embeddings)
        retriever = create_retriever(
            vector_store=vector_store,
            strategy=RetrievalStrategy.SIMILARITY,
            top_k=5
        )

        # Get vector store stats
        stats = vector_store.get_stats()
        logger.info(f"\n📊 Vector Store Stats:")
        logger.info(f"   Total documents: {stats.get('total_documents', 'unknown')}")
        logger.info(f"   Collections: {stats.get('collections', 'unknown')}")

        # Run quick test queries
        test_queries = [
            ("Express server setup", "express"),
            ("React component", "react"),
            ("TypeScript types", "typescript"),
            ("async function", "javascript"),
            ("error handling", "general"),
        ]

        logger.info(f"\n🔍 Testing {len(test_queries)} queries:")
        successes = 0

        for query, expected_framework in test_queries:
            try:
                results = retriever.retrieve(query, top_k=1)
                if results:
                    top = results[0]
                    framework = top.metadata.get("framework", "unknown")
                    match = framework == expected_framework
                    status = "✅" if match else "⚠️ "
                    logger.info(
                        f"{status} [{query:25s}] → {framework:15s} "
                        f"(similarity: {top.similarity:.3f})"
                    )
                    if match:
                        successes += 1
                else:
                    logger.warning(f"⚠️  No results for: {query}")
            except Exception as e:
                logger.error(f"❌ Error querying '{query}': {e}")

        success_rate = (successes / len(test_queries)) * 100
        logger.info(f"\n📈 Success Rate: {successes}/{len(test_queries)} ({success_rate:.1f}%)")

        return {
            "success_rate": success_rate,
            "successes": successes,
            "total": len(test_queries),
            "vector_store_docs": stats.get('total_documents', 0),
        }

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Execute PHASE 1"""
    start_time = time.time()

    logger.info("🎯 PHASE 1: RESET & BASELINE")
    logger.info(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    steps = [
        # ("Clear vector store", ["python", "scripts/clear_vector_store.py"]),
        ("Seed TypeScript/JS docs", ["python", "scripts/seed_typescript_docs.py"]),
        ("Seed Official docs", ["python", "scripts/seed_official_docs.py"]),
    ]

    for description, cmd in steps:
        success = run_command(cmd, description)
        if not success:
            logger.warning(f"⚠️  {description} failed, continuing anyway...")

    # Run benchmark
    benchmark_results = run_benchmark()

    # Save results
    output_file = Path(__file__).parent.parent / "DOCS" / "rag" / "phase1_baseline_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "phase": "PHASE 1: Reset & Baseline",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": time.time() - start_time,
            "benchmark": benchmark_results,
        }, f, indent=2)

    elapsed = time.time() - start_time

    logger.info("\n" + "="*60)
    logger.info("✅ PHASE 1 COMPLETE")
    logger.info(f"   Success Rate: {benchmark_results.get('success_rate', 0):.1f}%")
    logger.info(f"   Vector Store Docs: {benchmark_results.get('vector_store_docs', 0)}")
    logger.info(f"   Time Elapsed: {elapsed:.1f}s")
    logger.info(f"   Results saved: {output_file}")
    logger.info("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
