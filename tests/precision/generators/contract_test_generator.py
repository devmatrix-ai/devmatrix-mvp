"""
Contract Test Generator

Generates contract tests (preconditions, postconditions, invariants) from discovery documents.
These tests validate that generated code meets specified contracts.

Architecture:
    Discovery Doc → Parse Requirements → Extract Contracts → Generate Tests → pytest/jest files

Contract Types:
    - Preconditions: State required before operation (e.g., "user must exist")
    - Postconditions: Expected state after operation (e.g., "session created")
    - Invariants: Conditions that must always hold (e.g., "password hashed")
"""

import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import anthropic
import os


@dataclass
class Contract:
    """Represents a single contract (pre/post/invariant)."""

    contract_type: str  # "precondition" | "postcondition" | "invariant"
    description: str
    requirement_id: int
    requirement_text: str
    check_code: Optional[str] = None  # pytest assertion code


@dataclass
class ContractTest:
    """Represents a complete contract test."""

    test_name: str
    requirement_id: int
    requirement_text: str
    contracts: List[Contract]
    test_code: str  # Complete pytest test function


class ContractTestGenerator:
    """
    Generates contract tests from discovery documents.

    Uses Claude API to intelligently extract contracts and generate
    executable tests that validate code correctness.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize contract test generator.

        Args:
            api_key: Anthropic API key (default: from ANTHROPIC_API_KEY env)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    def parse_requirements(self, discovery_doc: str) -> List[Dict[str, Any]]:
        """
        Parse requirements from discovery document.

        Args:
            discovery_doc: Markdown discovery document

        Returns:
            List of requirements with metadata:
            [
                {
                    "id": 1,
                    "text": "Create Project model",
                    "module": "Project Module",
                    "technical_reqs": ["Use SQLAlchemy", "Foreign keys"]
                },
                ...
            ]
        """
        requirements = []
        current_module = None
        technical_reqs = []

        # Extract technical requirements section
        tech_match = re.search(
            r"\*\*Technical Requirements:\*\*(.*?)(?=\n\*\*|$)", discovery_doc, re.DOTALL
        )
        if tech_match:
            tech_section = tech_match.group(1)
            technical_reqs = [
                line.strip("- ").strip()
                for line in tech_section.split("\n")
                if line.strip().startswith("-")
            ]

        # Parse numbered requirements
        lines = discovery_doc.split("\n")
        for line in lines:
            # Detect module sections
            if line.strip().startswith("**") and "Module" in line:
                current_module = line.strip("*").strip(":").strip()
                continue

            # Parse numbered requirements (format: "1. Create...")
            match = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
            if match:
                req_id = int(match.group(1))
                req_text = match.group(2)

                requirements.append(
                    {
                        "id": req_id,
                        "text": req_text,
                        "module": current_module,
                        "technical_reqs": technical_reqs,
                    }
                )

        return requirements

    def extract_contracts(
        self, requirement: Dict[str, Any], discovery_doc: str
    ) -> List[Contract]:
        """
        Extract contracts from a requirement using Claude API.

        Args:
            requirement: Parsed requirement dict
            discovery_doc: Full discovery document for context

        Returns:
            List of Contract objects (preconditions, postconditions, invariants)
        """
        prompt = f"""Analyze this requirement and extract contracts (preconditions, postconditions, invariants).

**Requirement #{requirement['id']}:**
{requirement['text']}

**Module:** {requirement['module'] or 'N/A'}

**Technical Context:**
{chr(10).join('- ' + req for req in requirement['technical_reqs'])}

**Full Discovery Document (for context):**
{discovery_doc}

---

Extract contracts in JSON format:
{{
  "preconditions": [
    {{"description": "User must exist in database", "implied_from": "requirement context"}},
    ...
  ],
  "postconditions": [
    {{"description": "Session token created and stored", "implied_from": "requirement"}},
    ...
  ],
  "invariants": [
    {{"description": "Password must be hashed (never plaintext)", "implied_from": "security requirement"}},
    ...
  ]
}}

**Rules:**
- Preconditions: State that MUST exist before operation (e.g., "user exists", "database connected")
- Postconditions: State that MUST exist after operation (e.g., "record created", "email sent")
- Invariants: Conditions that ALWAYS hold (e.g., "price > 0", "password hashed", "unique constraints")
- Extract from both explicit requirements AND implicit technical requirements
- Be specific: "User with given email exists" vs "User exists"
- Include security/validation invariants from technical requirements

Return ONLY valid JSON, no markdown or explanation.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.0,  # Deterministic contract extraction
            messages=[{"role": "user", "content": prompt}],
        )

        contracts_json = response.content[0].text.strip()

        # Parse JSON response
        try:
            contracts_data = json.loads(contracts_json)
        except json.JSONDecodeError:
            # Fallback: extract JSON from markdown code block
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", contracts_json, re.DOTALL)
            if json_match:
                contracts_data = json.loads(json_match.group(1))
            else:
                print(f"⚠️  Failed to parse contracts for req #{requirement['id']}")
                return []

        # Convert to Contract objects
        contracts = []

        for precon in contracts_data.get("preconditions", []):
            contracts.append(
                Contract(
                    contract_type="precondition",
                    description=precon["description"],
                    requirement_id=requirement["id"],
                    requirement_text=requirement["text"],
                )
            )

        for postcon in contracts_data.get("postconditions", []):
            contracts.append(
                Contract(
                    contract_type="postcondition",
                    description=postcon["description"],
                    requirement_id=requirement["id"],
                    requirement_text=requirement["text"],
                )
            )

        for inv in contracts_data.get("invariants", []):
            contracts.append(
                Contract(
                    contract_type="invariant",
                    description=inv["description"],
                    requirement_id=requirement["id"],
                    requirement_text=requirement["text"],
                )
            )

        return contracts

    def generate_test_code(
        self, requirement: Dict[str, Any], contracts: List[Contract]
    ) -> str:
        """
        Generate pytest test code for contracts using Claude API.

        Args:
            requirement: Requirement dict
            contracts: List of extracted contracts

        Returns:
            Complete pytest test function as string
        """
        contracts_summary = "\n".join(
            [
                f"- {c.contract_type.upper()}: {c.description}"
                for c in contracts
            ]
        )

        prompt = f"""Generate a pytest test function to validate these contracts.

**Requirement #{requirement['id']}:**
{requirement['text']}

**Contracts to validate:**
{contracts_summary}

**Technical Requirements:**
{chr(10).join('- ' + req for req in requirement['technical_reqs'])}

---

Generate a COMPLETE pytest test function that:
1. Sets up necessary preconditions
2. Executes the requirement operation
3. Validates all postconditions
4. Checks all invariants

**Guidelines:**
- Function name: test_requirement_{requirement['id']:03d}_contract_validation
- Use proper pytest fixtures if needed (e.g., @pytest.fixture)
- **IMPORTANT**: Import ONLY standard library modules (typing, datetime, uuid, etc.)
- **DO NOT import**: docker, psycopg2, redis, fastapi, sqlalchemy, or any external dependencies
- Tests will be executed in isolated pytest environment without external dependencies
- Add clear docstring explaining what's being tested
- Use descriptive variable names
- Add comments for each contract validation
- Use assert statements with clear error messages
- Handle edge cases (None values, empty lists, etc.)
- Make test executable with ONLY standard library imports

**Example Structure:**
```python
def test_requirement_001_contract_validation():
    \"\"\"
    Test: Create Project model
    Validates: preconditions, postconditions, invariants
    \"\"\"
    # Precondition: Database connection available
    assert db.is_connected(), "Database must be connected"

    # Execute: Create project
    project = create_project(name="Test", description="Test project", owner_id=1)

    # Postcondition: Project created with all fields
    assert project is not None, "Project must be created"
    assert project.id is not None, "Project must have ID"
    assert project.created_at is not None, "Project must have created_at timestamp"

    # Invariant: owner_id must be positive
    assert project.owner_id > 0, "owner_id must be positive integer"
```

Return ONLY the test function code (Python), no markdown or explanation.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,  # Increased to prevent f-string truncation
            temperature=0.2,  # Slight creativity for test variations
            messages=[{"role": "user", "content": prompt}],
        )

        test_code = response.content[0].text.strip()

        # Clean markdown code blocks if present
        code_match = re.search(r"```python\s*(.*?)\s*```", test_code, re.DOTALL)
        if code_match:
            test_code = code_match.group(1)

        return test_code

    def generate_tests(self, discovery_doc: str) -> List[ContractTest]:
        """
        Generate all contract tests from discovery document.

        Args:
            discovery_doc: Markdown discovery document

        Returns:
            List of ContractTest objects with executable test code
        """
        # 1. Parse requirements
        requirements = self.parse_requirements(discovery_doc)
        print(f"📋 Parsed {len(requirements)} requirements")

        # 2. Extract contracts and generate tests
        contract_tests = []

        for req in requirements:
            print(f"  → Req #{req['id']}: {req['text'][:60]}...")

            # Extract contracts
            contracts = self.extract_contracts(req, discovery_doc)
            print(f"    ✓ Extracted {len(contracts)} contracts")

            if not contracts:
                print(f"    ⚠️  No contracts found, skipping")
                continue

            # Generate test code
            test_code = self.generate_test_code(req, contracts)
            test_name = f"test_requirement_{req['id']:03d}_contract_validation"

            contract_tests.append(
                ContractTest(
                    test_name=test_name,
                    requirement_id=req["id"],
                    requirement_text=req["text"],
                    contracts=contracts,
                    test_code=test_code,
                )
            )

        print(f"✅ Generated {len(contract_tests)} contract tests")
        return contract_tests

    def write_test_file(
        self, contract_tests: List[ContractTest], output_path: Path, module_name: str
    ) -> None:
        """
        Write contract tests to pytest file.

        Args:
            contract_tests: List of generated contract tests
            output_path: Directory to write test file
            module_name: Name of module being tested (e.g., "task_management")
        """
        output_path.mkdir(parents=True, exist_ok=True)
        test_file = output_path / f"test_{module_name}_contracts.py"

        # Generate file header
        header = f'''"""
Contract Tests - {module_name}

Auto-generated from Discovery Document.
Validates preconditions, postconditions, and invariants.

DO NOT EDIT - Changes will be overwritten.
Generated: {module_name}
Total Tests: {len(contract_tests)}
"""

import pytest
from typing import Any, List, Dict, Optional
from datetime import datetime

'''

        # Append all test functions
        test_functions = "\n\n".join([ct.test_code for ct in contract_tests])

        # Write file
        test_file.write_text(header + test_functions)
        print(f"📝 Written {len(contract_tests)} tests to {test_file}")

    def generate_from_discovery(
        self, discovery_doc: str, output_dir: Path, module_name: str
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Discovery → Contract Tests → File.

        Args:
            discovery_doc: Markdown discovery document
            output_dir: Where to write test files
            module_name: Module name (e.g., "ecommerce", "auth")

        Returns:
            Statistics:
            {
                "tests_generated": 10,
                "contracts_extracted": 25,
                "test_file": "test_ecommerce_contracts.py",
                "preconditions": 8,
                "postconditions": 12,
                "invariants": 5
            }
        """
        print(f"\n🔬 Generating contract tests for: {module_name}")
        print("=" * 60)

        # Generate tests
        contract_tests = self.generate_tests(discovery_doc)

        # Count contract types
        all_contracts = [c for ct in contract_tests for c in ct.contracts]
        stats = {
            "tests_generated": len(contract_tests),
            "contracts_extracted": len(all_contracts),
            "test_file": f"test_{module_name}_contracts.py",
            "preconditions": sum(
                1 for c in all_contracts if c.contract_type == "precondition"
            ),
            "postconditions": sum(
                1 for c in all_contracts if c.contract_type == "postcondition"
            ),
            "invariants": sum(
                1 for c in all_contracts if c.contract_type == "invariant"
            ),
        }

        # Write test file
        self.write_test_file(contract_tests, output_dir, module_name)

        print("\n📊 Generation Complete:")
        print(f"  ✓ Tests: {stats['tests_generated']}")
        print(f"  ✓ Contracts: {stats['contracts_extracted']}")
        print(f"    - Preconditions: {stats['preconditions']}")
        print(f"    - Postconditions: {stats['postconditions']}")
        print(f"    - Invariants: {stats['invariants']}")
        print("=" * 60)

        return stats


# Example usage
if __name__ == "__main__":
    # Test with sample prompt
    from tests.precision.fixtures.sample_prompts import SAMPLE_PROMPT_4

    generator = ContractTestGenerator()
    stats = generator.generate_from_discovery(
        discovery_doc=SAMPLE_PROMPT_4,
        output_dir=Path("/tmp/contract_tests"),
        module_name="task_management",
    )

    print(f"\n✅ Success! Generated {stats['tests_generated']} contract tests")
