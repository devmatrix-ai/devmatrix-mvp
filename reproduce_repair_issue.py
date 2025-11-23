
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from src.mge.v2.agents.code_repair_agent import CodeRepairAgent
from src.parsing.spec_parser import SpecRequirements, Entity, Field

class TestCodeRepairRegex(unittest.TestCase):
    def setUp(self):
        self.agent = CodeRepairAgent(Path("/tmp/test_output"))
        # Mock internal methods to avoid file I/O
        self.agent._add_field_constraint_to_schema = MagicMock(return_value=True)
        self.agent._find_entity_for_field = MagicMock(return_value="Product")
        
        self.spec = SpecRequirements(
            entities=[
                Entity(name="Product", fields=[
                    Field(name="price", type="decimal"),
                    Field(name="stock", type="int"),
                    Field(name="name", type="str")
                ])
            ]
        )

    def test_regex_failures(self):
        # These are the actual failures from the E2E log
        failures = [
            "Product.name: non-empty",
            "Product.price: greater_than_zero",
            "Product.stock: non-negative",
            "Product.id: auto-generated",
            "Product.is_active: default_true"
        ]
        
        print("\nTesting Regex Parsing on Real Failures:")
        for failure in failures:
            success = self.agent.repair_missing_validation(failure, self.spec)
            status = "✅ Parsed" if success else "❌ Failed"
            print(f"{status}: {failure}")
            
            # We expect these to fail with current regex
            if not success:
                print(f"   -> Current regex cannot handle this format")

if __name__ == "__main__":
    unittest.main()
