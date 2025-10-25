"""
Tests for AcceptanceTestGenerator

Tests orchestration of test generation pipeline.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.testing.test_generator import AcceptanceTestGenerator
from src.models import MasterPlan, AcceptanceTest


@pytest.mark.asyncio
class TestAcceptanceTestGenerator:
    """Test AcceptanceTestGenerator functionality"""

    @pytest.fixture
    def masterplan_id(self):
        """Generate test masterplan ID"""
        return uuid4()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def valid_markdown(self):
        """Valid masterplan markdown"""
        return """
### MUST
- Must use JWT tokens
- Must validate email
- Must hash passwords

### SHOULD
- Should support OAuth
- Should cache sessions
"""

    @pytest.fixture
    async def generator(self, mock_db):
        """Create AcceptanceTestGenerator instance"""
        return AcceptanceTestGenerator(mock_db)

    async def test_generate_from_markdown(self, generator, masterplan_id, valid_markdown):
        """Test generation from markdown content"""
        tests = await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        assert len(tests) == 5
        assert all(isinstance(t, AcceptanceTest) for t in tests)

    async def test_generated_tests_have_correct_priority(self, generator, masterplan_id, valid_markdown):
        """Test generated tests have correct priority classification"""
        tests = await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        must_tests = [t for t in tests if t.requirement_priority == 'must']
        should_tests = [t for t in tests if t.requirement_priority == 'should']

        assert len(must_tests) == 3
        assert len(should_tests) == 2

    async def test_generated_tests_have_test_code(self, generator, masterplan_id, valid_markdown):
        """Test all generated tests have test code"""
        tests = await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        assert all(t.test_code for t in tests)
        assert all(len(t.test_code) > 0 for t in tests)

    async def test_validation_failure_raises_error(self, generator, masterplan_id):
        """Test validation failure raises ValueError"""
        invalid_markdown = """
### SHOULD
- Should do something
"""
        with pytest.raises(ValueError, match="Invalid requirements"):
            await generator.generate_from_masterplan(masterplan_id, invalid_markdown)

    async def test_test_language_determination_python(self, generator, masterplan_id, valid_markdown, mock_db):
        """Test language determination selects pytest for Python"""
        mock_masterplan = MagicMock()
        mock_masterplan.metadata = {'primary_language': 'python'}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_masterplan
        mock_db.execute.return_value = mock_result

        tests = await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        assert all(t.test_language == 'pytest' for t in tests)

    async def test_commits_to_database(self, generator, masterplan_id, valid_markdown, mock_db):
        """Test generator commits tests to database"""
        await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        mock_db.commit.assert_called_once()

    async def test_adds_all_tests_to_session(self, generator, masterplan_id, valid_markdown, mock_db):
        """Test all tests are added to database session"""
        tests = await generator.generate_from_masterplan(masterplan_id, valid_markdown)

        assert mock_db.add.call_count == len(tests)

    async def test_regenerate_failed_tests(self, generator, masterplan_id, mock_db):
        """Test regenerating failed tests"""
        failed_test_ids = [uuid4(), uuid4()]

        mock_tests = [
            AcceptanceTest(
                test_id=failed_test_ids[0],
                masterplan_id=masterplan_id,
                requirement_text="Must do something",
                requirement_priority='must',
                test_code="old code",
                test_language='pytest'
            ),
            AcceptanceTest(
                test_id=failed_test_ids[1],
                masterplan_id=masterplan_id,
                requirement_text="Must do another thing",
                requirement_priority='must',
                test_code="old code",
                test_language='pytest'
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_tests
        mock_db.execute.return_value = mock_result

        regenerated = await generator.regenerate_failed_tests(masterplan_id, failed_test_ids)

        assert len(regenerated) == 2
        assert all(t.test_code != "old code" for t in regenerated)

    async def test_get_test_statistics(self, generator, masterplan_id, mock_db):
        """Test getting test statistics"""
        mock_tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Must do A",
                requirement_priority='must',
                test_code="code",
                test_language='pytest',
                timeout_seconds=30
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Should do B",
                requirement_priority='should',
                test_code="code",
                test_language='jest',
                timeout_seconds=30
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_tests
        mock_db.execute.return_value = mock_result

        stats = await generator.get_test_statistics(masterplan_id)

        assert stats['total_tests'] == 2
        assert stats['must_tests'] == 1
        assert stats['should_tests'] == 1
        assert 'pytest' in stats['languages']
        assert 'jest' in stats['languages']
