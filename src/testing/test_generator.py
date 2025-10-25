"""
Complete test generation orchestration

Orchestrates: parse requirements → generate tests → store in database
"""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from .requirement_parser import RequirementParser, Requirement
from .test_template_engine import TestTemplateEngine
from src.models import AcceptanceTest, MasterPlan

logger = logging.getLogger(__name__)


class AcceptanceTestGenerator:
    """
    Orchestrate complete test generation pipeline

    Pipeline: parse masterplan → generate tests → validate → store
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.parser = RequirementParser()
        self.template_engine = TestTemplateEngine()

    async def generate_from_masterplan(
        self,
        masterplan_id: UUID,
        markdown_content: Optional[str] = None
    ) -> List[AcceptanceTest]:
        """
        Complete pipeline: parse → generate → store

        Args:
            masterplan_id: Masterplan UUID
            markdown_content: Full masterplan markdown (optional, will fetch if not provided)

        Returns:
            List of generated AcceptanceTest objects

        Raises:
            ValueError: If requirements validation fails
        """
        # Fetch masterplan if markdown not provided
        if markdown_content is None:
            result = await self.db.execute(
                select(MasterPlan).where(MasterPlan.masterplan_id == masterplan_id)
            )
            masterplan = result.scalar_one_or_none()

            if not masterplan:
                raise ValueError(f"Masterplan {masterplan_id} not found")

            markdown_content = masterplan.markdown_content

            if not markdown_content:
                raise ValueError(f"Masterplan {masterplan_id} has no markdown content")

        # Parse requirements
        logger.info(f"Parsing requirements from masterplan {masterplan_id}")
        requirements = self.parser.parse_masterplan(masterplan_id, markdown_content)

        # Validate requirements
        validation = self.parser.validate_requirements(requirements)
        if not validation['is_valid']:
            error_msg = f"Invalid requirements: {', '.join(validation['errors'])}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"Requirement validation warning: {warning}")

        # Determine test language based on project
        test_language = await self._determine_test_language(masterplan_id)

        # Generate tests
        logger.info(
            f"Generating {len(requirements)} tests "
            f"({validation['must_count']} MUST, {validation['should_count']} SHOULD) "
            f"using {test_language}"
        )

        generated_tests = []
        for req in requirements:
            # Generate test code
            if test_language == 'pytest':
                test_code = self.template_engine.generate_pytest_test(req)
            elif test_language in ['jest', 'vitest']:
                test_code = self.template_engine.generate_jest_test(req)
            else:
                logger.warning(f"Unknown test language {test_language}, defaulting to pytest")
                test_code = self.template_engine.generate_pytest_test(req)

            # Create DB object
            test = AcceptanceTest(
                masterplan_id=masterplan_id,
                requirement_text=req.text,
                requirement_priority=req.priority,
                test_code=test_code,
                test_language=test_language,
                timeout_seconds=30  # Default timeout
            )

            self.db.add(test)
            generated_tests.append(test)

        # Commit all tests
        await self.db.commit()

        logger.info(
            f"Successfully generated and stored {len(generated_tests)} acceptance tests "
            f"for masterplan {masterplan_id}"
        )

        return generated_tests

    async def regenerate_failed_tests(
        self,
        masterplan_id: UUID,
        failed_test_ids: List[UUID]
    ) -> List[AcceptanceTest]:
        """
        Regenerate specific failed tests with improved prompts

        Args:
            masterplan_id: Masterplan UUID
            failed_test_ids: List of test IDs to regenerate

        Returns:
            List of regenerated AcceptanceTest objects
        """
        # Fetch failed tests
        result = await self.db.execute(
            select(AcceptanceTest).where(
                AcceptanceTest.masterplan_id == masterplan_id,
                AcceptanceTest.test_id.in_(failed_test_ids)
            )
        )
        failed_tests = result.scalars().all()

        if not failed_tests:
            logger.warning(f"No failed tests found for masterplan {masterplan_id}")
            return []

        logger.info(f"Regenerating {len(failed_tests)} failed tests")

        regenerated = []
        for test in failed_tests:
            # Create Requirement from test
            req = Requirement(
                text=test.requirement_text,
                priority=test.requirement_priority,
                requirement_id=f"{masterplan_id}_{test.requirement_priority}_{len(regenerated)}",
                section=test.requirement_priority.upper(),
                metadata={}
            )

            # Regenerate with potentially improved template
            if test.test_language == 'pytest':
                new_test_code = self.template_engine.generate_pytest_test(req)
            else:
                new_test_code = self.template_engine.generate_jest_test(req)

            # Update test code
            test.test_code = new_test_code
            regenerated.append(test)

        await self.db.commit()

        logger.info(f"Successfully regenerated {len(regenerated)} tests")
        return regenerated

    async def _determine_test_language(self, masterplan_id: UUID) -> str:
        """
        Determine test framework based on project language

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            'pytest', 'jest', or 'vitest'
        """
        # Query masterplan to get primary language
        result = await self.db.execute(
            select(MasterPlan).where(MasterPlan.masterplan_id == masterplan_id)
        )
        masterplan = result.scalar_one_or_none()

        if not masterplan:
            logger.warning(f"Masterplan {masterplan_id} not found, defaulting to pytest")
            return 'pytest'

        # Check project metadata for language hints
        # This is a simplified version - in production would analyze codebase
        if hasattr(masterplan, 'metadata') and masterplan.metadata:
            metadata = masterplan.metadata
            if isinstance(metadata, dict):
                primary_language = metadata.get('primary_language', '').lower()

                if 'python' in primary_language:
                    return 'pytest'
                elif 'typescript' in primary_language or 'javascript' in primary_language:
                    # Check for vite in dependencies (prefer vitest)
                    if 'vite' in str(metadata.get('dependencies', [])):
                        return 'vitest'
                    return 'jest'

        # Check title/description for language hints
        title = masterplan.title.lower() if hasattr(masterplan, 'title') else ''
        description = masterplan.description.lower() if hasattr(masterplan, 'description') else ''

        if 'python' in title or 'python' in description:
            return 'pytest'
        elif 'typescript' in title or 'javascript' in title or 'react' in title or 'vue' in title:
            return 'vitest'

        # Default to pytest
        logger.info(f"Could not determine test language for masterplan {masterplan_id}, defaulting to pytest")
        return 'pytest'

    async def get_test_statistics(self, masterplan_id: UUID) -> dict:
        """
        Get statistics about generated tests for a masterplan

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            Dict with test statistics
        """
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        must_tests = [t for t in tests if t.requirement_priority == 'must']
        should_tests = [t for t in tests if t.requirement_priority == 'should']

        # Group by language
        language_counts = {}
        for test in tests:
            language_counts[test.test_language] = language_counts.get(test.test_language, 0) + 1

        return {
            'total_tests': len(tests),
            'must_tests': len(must_tests),
            'should_tests': len(should_tests),
            'languages': language_counts,
            'avg_timeout': sum(t.timeout_seconds for t in tests) / len(tests) if tests else 0
        }

    async def delete_tests_for_masterplan(self, masterplan_id: UUID) -> int:
        """
        Delete all acceptance tests for a masterplan

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            Number of tests deleted
        """
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        count = len(tests)

        for test in tests:
            await self.db.delete(test)

        await self.db.commit()

        logger.info(f"Deleted {count} acceptance tests for masterplan {masterplan_id}")
        return count
