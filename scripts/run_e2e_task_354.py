#!/usr/bin/env python3
"""
Task 3.5.4: Test E2E validation pipeline with synthetic apps

Generates 5 synthetic apps using DevMatrix MGE V2 and validates them
through the 4-layer E2E Production Validator to measure real E2E precision.

Target: ≥88% precision (at least 4 of 5 apps passing all 4 layers)
"""

import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import existing precision measurement
from tests.precision.e2e.precision_pipeline_mge_v2 import E2EPrecisionPipelineMGE_V2


SYNTHETIC_SPECS = [
    ("01_todo_backend_api", "tests/e2e/synthetic_specs/01_todo_backend_api.md"),
    ("02_landing_page", "tests/e2e/synthetic_specs/02_landing_page.md"),
    ("03_todo_fullstack", "tests/e2e/synthetic_specs/03_todo_fullstack.md"),
    ("04_blog_platform", "tests/e2e/synthetic_specs/04_blog_platform.md"),
    ("05_ecommerce_minimal", "tests/e2e/synthetic_specs/05_ecommerce_minimal.md"),
]


async def main():
    """Execute Task 3.5.4"""
    logger.info("=" * 80)
    logger.info("🎯 Task 3.5.4: E2E Validation Pipeline Test")
    logger.info("=" * 80)
    
    output_dir = Path("/tmp/e2e_task_354")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pipeline = E2EPrecisionPipelineMGE_V2(auto_correct=False)
    
    results = []
    
    for spec_id, spec_file in SYNTHETIC_SPECS:
        logger.info(f"\n📋 Processing {spec_id}...")
        spec_path = Path(spec_file)
        
        if not spec_path.exists():
            logger.error(f"  ❌ Spec not found: {spec_file}")
            results.append({"spec_id": spec_id, "passed": False, "error": "Spec not found"})
            continue
            
        spec_content = spec_path.read_text()
        
        try:
            result = await pipeline.execute_from_discovery(
                discovery_doc=spec_content,
                user_id="task_354",
                output_dir=output_dir / spec_id,
            )
            
            passed = result.precision_gate_passed
            results.append({
                "spec_id": spec_id,
                "passed": passed,
                "precision": result.final_precision,
                "tests_passed": result.passed_tests,
                "tests_total": result.total_tests,
            })
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            logger.info(f"  {status} - Precision: {result.final_precision:.1%}")
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            results.append({"spec_id": spec_id, "passed": False, "error": str(e)})
    
    # Calculate E2E precision
    total = len(SYNTHETIC_SPECS)
    passed_count = sum(1 for r in results if r.get("passed", False))
    e2e_precision = (passed_count / total * 100) if total > 0 else 0
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 TASK 3.5.4 RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total apps: {total}")
    logger.info(f"Apps passed all 4 layers: {passed_count}")
    logger.info(f"E2E Precision: {e2e_precision:.1f}%")
    logger.info(f"Target: ≥88.0%")
    logger.info(f"Status: {'✅ TARGET MET' if e2e_precision >= 88.0 else '❌ TARGET NOT MET'}")
    logger.info("=" * 80)
    
    return e2e_precision >= 88.0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
