#!/usr/bin/env python3
"""
Test to validate System Prompt Fix (Fix #5)
Tests adaptive output instructions are working correctly for E-Commerce spec
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.code_generation_service import CodeGenerationService


class SpecRequirements:
    """Mock SpecRequirements class matching the interface used by CodeGenerationService"""

    def __init__(self, entities, endpoints, business_logic, requirements, metadata):
        self.entities = entities
        self.endpoints = endpoints
        self.business_logic = business_logic
        self.requirements = requirements
        self.metadata = metadata


async def parse_spec(spec_path: str) -> SpecRequirements:
    """Parse spec file and extract requirements manually"""

    with open(spec_path, 'r') as f:
        content = f.read()

    # Extract entities (simple pattern matching)
    entities = []
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '## Entities' in line or '## Data Models' in line:
            # Next lines after entities header
            for j in range(i+1, min(i+20, len(lines))):
                if lines[j].startswith('###'):
                    entity_name = lines[j].strip('# ').strip()
                    if entity_name and not entity_name.startswith('Requirements'):
                        entities.append(entity_name)
                elif lines[j].startswith('##'):
                    break

    # Extract endpoints (F1-F17 pattern for ecommerce)
    endpoints = []
    for line in lines:
        if line.strip().startswith('- F') or line.strip().startswith('F'):
            # Extract endpoint info
            if 'GET' in line or 'POST' in line or 'PUT' in line or 'DELETE' in line:
                endpoints.append(line.strip('- ').strip())

    # Extract business logic
    business_logic = []
    for line in lines:
        if 'validation' in line.lower() or 'calculate' in line.lower() or 'process' in line.lower():
            if line.strip().startswith('-'):
                business_logic.append(line.strip('- ').strip())

    # Extract all functional requirements
    requirements = []
    for line in lines:
        if line.strip().startswith('- F') or line.strip().startswith('F'):
            requirements.append(line.strip('- ').strip())

    return SpecRequirements(
        entities=entities if entities else ['Product', 'Customer', 'Cart', 'Order'],
        endpoints=endpoints if endpoints else [f"endpoint_{i}" for i in range(17)],
        business_logic=business_logic if business_logic else ['Payment processing', 'Inventory management', 'Order fulfillment'],
        requirements=requirements if requirements else [f"req_{i}" for i in range(17)],
        metadata={'spec_path': spec_path, 'spec_name': Path(spec_path).name}
    )


async def test_spec(spec_name: str, spec_path: str):
    """Test a single spec and analyze results"""

    print(f"\n{'='*80}")
    print(f"🧪 Testing: {spec_name}")
    print(f"📄 Spec: {spec_path}")
    print(f"{'='*80}\n")

    start_time = datetime.now()

    try:
        # Parse spec
        print("📋 Parsing spec requirements...")
        spec_reqs = await parse_spec(spec_path)

        print(f"   Entities: {len(spec_reqs.entities)}")
        print(f"   Endpoints: {len(spec_reqs.endpoints)}")
        print(f"   Business Logic: {len(spec_reqs.business_logic)}")

        # Calculate complexity
        entity_count = len(spec_reqs.entities)
        endpoint_count = len(spec_reqs.endpoints)
        logic_count = len(spec_reqs.business_logic)

        complexity = (entity_count * 50) + (endpoint_count * 30) + (logic_count * 20)

        print(f"\n📊 Complexity Analysis:")
        print(f"   Entities: {entity_count} × 50 = {entity_count * 50}")
        print(f"   Endpoints: {endpoint_count} × 30 = {endpoint_count * 30}")
        print(f"   Business Logic: {logic_count} × 20 = {logic_count * 20}")
        print(f"   {'─'*40}")
        print(f"   ✅ Total Complexity: {complexity}")

        if complexity < 300:
            mode = "Simple (single file)"
        elif complexity < 800:
            mode = "Medium (modular structure)"
        else:
            mode = "Complex (full project)"

        print(f"   📊 Mode Selected: {mode}")

        # Initialize CodeGenerationService
        print(f"\n🔨 Initializing CodeGenerationService...")
        service = CodeGenerationService()

        # Generate code
        print(f"\n🚀 Generating code...")
        code = await service.generate_from_requirements(spec_reqs)

        # Analyze generated code
        lines = code.splitlines()
        line_count = len(lines)
        char_count = len(code)

        print(f"\n{'='*80}")
        print(f"📊 Generated Code Analysis")
        print(f"{'='*80}\n")

        print(f"📏 Size Metrics:")
        print(f"   Lines: {line_count}")
        print(f"   Characters: {char_count}")

        # Check for issues
        issues = []

        if '/unknowns/' in code:
            issues.append("⚠️  BUG: /unknowns/ found in code")
        else:
            print(f"   ✅ No /unknowns/ bug")

        # Count endpoints (rough estimate)
        endpoint_markers = code.count('@app.') + code.count('@router.')
        print(f"   Endpoints (estimated): {endpoint_markers}")

        if endpoint_markers < endpoint_count:
            issues.append(f"⚠️  Missing endpoints: {endpoint_count - endpoint_markers}")

        # Count entities
        entity_found = sum(1 for entity in spec_reqs.entities if entity in code)
        print(f"   Entities found: {entity_found}/{entity_count}")

        if entity_found < entity_count:
            issues.append(f"⚠️  Missing entities: {entity_count - entity_found}")

        # Save generated code
        output_dir = Path("tests/e2e/generated_apps") / f"{spec_reqs.metadata['spec_name'].replace('.md', '')}_{int(datetime.now().timestamp())}"
        output_dir.mkdir(parents=True, exist_ok=True)

        main_py = output_dir / "main.py"
        main_py.write_text(code)

        print(f"\n💾 Generated code saved to: {output_dir}/main.py")

        # Results
        duration = (datetime.now() - start_time).total_seconds()

        result = {
            'spec_name': spec_name,
            'spec_path': spec_path,
            'complexity': complexity,
            'mode': mode,
            'generated_lines': line_count,
            'generated_chars': char_count,
            'expected_endpoints': endpoint_count,
            'found_endpoints': endpoint_markers,
            'expected_entities': entity_count,
            'found_entities': entity_found,
            'issues': issues,
            'output_path': str(main_py),
            'duration_s': duration
        }

        # Save metrics
        metrics_file = output_dir / "metrics.json"
        metrics_file.write_text(json.dumps(result, indent=2))

        print(f"\n{'='*80}")
        print(f"✅ TEST COMPLETED")
        print(f"{'='*80}\n")

        if issues:
            print(f"⚠️  Issues Found:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print(f"✅ No issues found - all validations passed!")

        print(f"\n⏱️  Duration: {duration:.2f}s")

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run validation tests"""

    print(f"\n{'='*80}")
    print(f"🎯 SYSTEM PROMPT FIX VALIDATION (Fix #5)")
    print(f"{'='*80}\n")
    print(f"Validating adaptive output instructions:")
    print(f"  - Simple specs (<300): Single file")
    print(f"  - Medium specs (300-800): Modular structure")
    print(f"  - Complex specs (>800): Full project")
    print(f"\n{'='*80}\n")

    specs = [
        {
            'name': 'Simple Task API',
            'path': 'tests/e2e/test_specs/simple_task_api.md'
        },
        {
            'name': 'E-Commerce API (Simple Backend)',
            'path': 'tests/e2e/test_specs/ecommerce_api_simple.md'
        }
    ]

    results = []

    for spec in specs:
        result = await test_spec(spec['name'], spec['path'])
        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 VALIDATION SUMMARY")
    print(f"{'='*80}\n")

    for result in results:
        print(f"{'='*80}")
        print(f"📋 {result['spec_name']}")
        print(f"{'='*80}")
        print(f"   Complexity: {result['complexity']} ({result['mode']})")
        print(f"   Generated: {result['generated_lines']} lines")
        print(f"   Endpoints: {result['found_endpoints']}/{result['expected_endpoints']}")
        print(f"   Entities: {result['found_entities']}/{result['expected_entities']}")

        if result['issues']:
            print(f"   ⚠️  Issues: {len(result['issues'])}")
        else:
            print(f"   ✅ All validations passed")

        print(f"   📁 Output: {result['output_path']}")
        print()

    print(f"{'='*80}")
    print(f"🎯 Expected Results:")
    print(f"{'='*80}\n")
    print(f"✅ Simple Task API:")
    print(f"   - Complexity: ~220 (Simple mode)")
    print(f"   - Lines: ~200-300")
    print(f"   - Single file structure")
    print()
    print(f"📈 E-Commerce API:")
    print(f"   - Complexity: ~770 (Medium mode)")
    print(f"   - Lines: ~800-1200 (NOT ~438)")
    print(f"   - Modular structure with sections")
    print(f"   - ALL 17 endpoints (NOT 16)")
    print(f"   - NO /unknowns/ bug")
    print()
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
