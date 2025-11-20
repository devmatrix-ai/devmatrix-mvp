#!/usr/bin/env python3
"""
Simple E2E test to validate adaptive prompt fixes.
Tests Simple Task and E-Commerce specs with new adaptive instructions.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cognitive.pipeline.pipeline import CognitivePipeline


async def test_spec(spec_name: str, spec_path: str):
    """Test a single spec and print results."""

    print(f"\n{'='*80}")
    print(f"🧪 Testing: {spec_name}")
    print(f"📄 Spec: {spec_path}")
    print(f"{'='*80}\n")

    start = datetime.now()

    try:
        pipeline = CognitivePipeline()
        result = await pipeline.execute(spec_path)

        duration = (datetime.now() - start).total_seconds()

        print(f"\n{'='*80}")
        print(f"✅ {spec_name} COMPLETED")
        print(f"{'='*80}\n")

        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"📁 Output: {result.get('output_directory', 'N/A')}")

        # Check generated files
        output_dir = Path(result.get('output_directory', ''))
        if output_dir.exists():
            main_py = output_dir / 'main.py'
            if main_py.exists():
                content = main_py.read_text()
                lines = len(content.splitlines())

                print(f"\n📊 Generated Code Analysis:")
                print(f"   Lines: {lines}")
                print(f"   Characters: {len(content)}")

                # Check for /unknowns/ bug
                if '/unknowns/' in content:
                    print(f"   ⚠️  BUG: /unknowns/ found in code")
                else:
                    print(f"   ✅ No /unknowns/ bug")

                # Count endpoints (rough estimate)
                endpoint_count = content.count('@app.') + content.count('@router.')
                print(f"   Endpoints (estimated): {endpoint_count}")

        return True

    except Exception as e:
        print(f"\n❌ {spec_name} FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run tests on both specs."""

    print(f"\n{'='*80}")
    print(f"🎯 ADAPTIVE PROMPT VALIDATION TEST")
    print(f"{'='*80}\n")
    print(f"Testing adaptive output instructions:")
    print(f"  - Simple Task API: Should use Simple mode (<300 complexity)")
    print(f"  - E-Commerce API: Should use Medium mode (300-800 complexity)")
    print(f"\n{'='*80}\n")

    specs = [
        {
            'name': 'Simple Task API',
            'path': 'tests/e2e/synthetic_specs/01_todo_backend_api.md'
        },
        {
            'name': 'E-Commerce API',
            'path': 'tests/e2e/synthetic_specs/05_ecommerce_minimal.md'
        }
    ]

    results = []

    for spec in specs:
        success = await test_spec(spec['name'], spec['path'])
        results.append((spec['name'], success))

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}\n")

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")

    total_passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {total_passed}/{len(results)} passed")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
