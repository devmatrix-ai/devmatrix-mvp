import unittest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock
from src.mge.v2.agents.code_repair_agent import CodeRepairAgent
from src.parsing.spec_parser import SpecRequirements, Entity, Field
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

class TestCodeRepairRegex(unittest.TestCase):
    def setUp(self):
        # Disable caching for test to avoid Redis dependency
        client = EnhancedAnthropicClient(enable_v2_caching=False, enable_v2_batching=False)
        self.agent = CodeRepairAgent(Path("/tmp/test_output"), llm_client=client)
        
        # Mock internal methods to avoid file I/O, but KEEP LLM logic real
        self.agent._add_field_constraint_to_schema = MagicMock(return_value=True)
        self.agent._find_entity_for_field = MagicMock(return_value="Product")
        
        self.spec = SpecRequirements(
            entities=[
                Entity(name="Product", fields=[
                    Field(name="price", type="decimal"),
                    Field(name="stock", type="int"),
                    Field(name="name", type="str"),
                    Field(name="id", type="uuid"),
                    Field(name="is_active", type="bool")
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
        
        print("\nTesting LLM Parsing on Real Failures:")
        
        async def run_tests():
            for failure in failures:
                print(f"Testing: {failure}...")
                success = await self.agent.repair_missing_validation(failure, self.spec)
                status = "✅ Parsed" if success else "❌ Failed"
                print(f"{status}: {failure}")
                
                if not success:
                    print(f"   -> LLM failed to parse this format")

        asyncio.run(run_tests())

if __name__ == "__main__":
    unittest.main()
