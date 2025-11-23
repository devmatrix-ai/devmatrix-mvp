"""
Test script to verify ApplicationIR integration in CodeGenerationService.
"""
import asyncio
import logging
from src.services.code_generation_service import CodeGenerationService
from src.parsing.spec_parser import SpecRequirements, Entity, Endpoint, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ir_integration():
    # Mock requirements
    requirements = """
    Create a Todo app with users and tasks.
    Users have email and password.
    Tasks have title, description, and is_completed.
    """
    
    # Mock SpecRequirements (using actual classes from spec_parser)
    spec = SpecRequirements(
        entities=[
            Entity(name="User", fields=[
                Field(name="id", type="UUID", primary_key=True, description="PK"),
                Field(name="email", type="str", description="User email")
            ], description="User entity"),
            Entity(name="Task", fields=[
                Field(name="id", type="UUID", primary_key=True, description="PK"),
                Field(name="title", type="str", description="Task title")
            ], description="Task entity")
        ],
        endpoints=[
            Endpoint(path="/users", method="GET", description="List users", entity="User", operation="list"),
            Endpoint(path="/tasks", method="POST", description="Create task", entity="Task", operation="create")
        ],
        metadata={"spec_name": "TestTodoApp", "description": "A simple todo app"}
    )
    
    # Initialize service with mock DB
    class MockDB:
        pass
    service = CodeGenerationService(db=MockDB(), enable_pattern_promotion=False)
    
    # Inject mock analyzer to bypass LLM call for spec analysis
    class MockAnalyzer:
        async def analyze(self, req):
            return spec
    service.spec_analyzer = MockAnalyzer()
    
    # Run generation (will fail at LLM step but should build IR first)
    try:
        logger.info("Starting generation...")
        # We expect this to fail at LLM generation because we don't have a real LLM client configured for this test
        # But we want to see the IR construction logs before it fails
        await service.generate_from_requirements(spec)
    except Exception as e:
        logger.info(f"Generation stopped as expected: {e}")
        
    logger.info("Test finished. Check logs for 'ApplicationIR constructed'.")

if __name__ == "__main__":
    asyncio.run(test_ir_integration())
