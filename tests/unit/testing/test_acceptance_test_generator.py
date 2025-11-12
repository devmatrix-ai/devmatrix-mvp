"""
Unit tests for AcceptanceTestGenerator

Tests complete test generation orchestration:
- Masterplan parsing and requirement extraction
- Test generation and storage
- Language detection logic
- Failed test regeneration
- Statistics and deletion
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.testing.test_generator import AcceptanceTestGenerator
from src.models import AcceptanceTest, MasterPlan


@pytest.fixture
def mock_async_db():
    """Mock async database session"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.delete = AsyncMock()
    return mock_db


@pytest.fixture
def sample_markdown():
    """Sample masterplan markdown with requirements"""
    return """
# MasterPlan - Authentication System

## Tech Stack
- Backend: Python FastAPI
- Database: PostgreSQL

## Requirements

### MUST
- User authentication must use JWT tokens
- Database transactions must be ACID compliant
- API responses must return JSON format

### SHOULD
- UI should be responsive on mobile devices
- API response time should be <200ms p95
"""


@pytest.fixture
def sample_masterplan(sample_markdown):
    """Sample MasterPlan object"""
    masterplan = MasterPlan(
        masterplan_id=uuid4(),
        project_name="Authentication System",
        description="Complete auth system",
        markdown_content=sample_markdown,
        metadata={'primary_language': 'python'}
    )
    return masterplan


class TestAcceptanceTestGenerator:
    """Test AcceptanceTestGenerator orchestration"""

    # ========================================
    # Test Generation Pipeline Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_generate_from_masterplan_success(self, mock_async_db, sample_masterplan, sample_markdown):
        """Test successful test generation from masterplan"""
        masterplan_id = sample_masterplan.masterplan_id

        # Mock database query to return masterplan
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)

        # Generate tests
        tests = await generator.generate_from_masterplan(masterplan_id)

        # Verify correct number of tests generated
        assert len(tests) == 5  # 3 MUST + 2 SHOULD

        # Verify MUST tests
        must_tests = [t for t in tests if t.requirement_priority == 'must']
        assert len(must_tests) == 3
        assert any('JWT' in t.requirement_text for t in must_tests)
        assert any('ACID' in t.requirement_text for t in must_tests)

        # Verify SHOULD tests
        should_tests = [t for t in tests if t.requirement_priority == 'should']
        assert len(should_tests) == 2
        assert any('responsive' in t.requirement_text for t in should_tests)

        # Verify all tests use pytest (due to Python in metadata)
        assert all(t.test_language == 'pytest' for t in tests)

        # Verify commit was called
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_explicit_markdown(self, mock_async_db, sample_markdown):
        """Test generation when markdown is explicitly provided"""
        masterplan_id = uuid4()

        # Mock masterplan query for language detection (called by _determine_test_language)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # Will default to pytest
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)

        # Generate with explicit markdown (execute called only for language detection)
        tests = await generator.generate_from_masterplan(
            masterplan_id,
            markdown_content=sample_markdown
        )

        # Verify tests were generated
        assert len(tests) == 5

        # Verify DB was queried only once for language detection
        assert mock_async_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_masterplan_not_found(self, mock_async_db):
        """Test error when masterplan not found"""
        masterplan_id = uuid4()

        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)

        with pytest.raises(ValueError, match="not found"):
            await generator.generate_from_masterplan(masterplan_id)

    @pytest.mark.asyncio
    async def test_generate_no_markdown_content(self, mock_async_db):
        """Test error when masterplan has no markdown content"""
        masterplan = MasterPlan(
            masterplan_id=uuid4(),
            project_name="Test",
            description="Test",
            markdown_content=None  # No content
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)

        with pytest.raises(ValueError, match="no markdown content"):
            await generator.generate_from_masterplan(masterplan.masterplan_id)

    @pytest.mark.asyncio
    async def test_generate_invalid_requirements(self, mock_async_db):
        """Test error when requirements validation fails"""
        masterplan_id = uuid4()

        # Markdown with duplicate requirements
        markdown = """
### MUST
- Same requirement
- Same requirement
"""

        generator = AcceptanceTestGenerator(mock_async_db)

        with pytest.raises(ValueError, match="Invalid requirements"):
            await generator.generate_from_masterplan(
                masterplan_id,
                markdown_content=markdown
            )

    # ========================================
    # Test Language Detection Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_determine_test_language_python(self, mock_async_db):
        """Test language detection for Python projects"""
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="Python Project",
            description="",
            metadata={'primary_language': 'python'}
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        language = await generator._determine_test_language(masterplan_id)

        assert language == 'pytest'

    @pytest.mark.asyncio
    async def test_determine_test_language_typescript_vitest(self, mock_async_db):
        """Test language detection for TypeScript with Vite"""
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="TypeScript Project",
            description="",
            metadata={
                'primary_language': 'typescript',
                'dependencies': ['vite', 'react']
            }
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        language = await generator._determine_test_language(masterplan_id)

        assert language == 'vitest'

    @pytest.mark.asyncio
    async def test_determine_test_language_javascript_jest(self, mock_async_db):
        """Test language detection for JavaScript without Vite"""
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="JavaScript Project",
            description="",
            metadata={'primary_language': 'javascript'}
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        language = await generator._determine_test_language(masterplan_id)

        assert language == 'jest'

    @pytest.mark.asyncio
    async def test_determine_test_language_from_title(self, mock_async_db):
        """Test language detection from title when metadata missing"""
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="React TypeScript App",
            description="",
            metadata={}
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        language = await generator._determine_test_language(masterplan_id)

        assert language == 'vitest'

    @pytest.mark.asyncio
    async def test_determine_test_language_default(self, mock_async_db):
        """Test language detection defaults to pytest"""
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="Unknown Project",
            description="",
            metadata={}
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = masterplan
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        language = await generator._determine_test_language(masterplan_id)

        assert language == 'pytest'

    # ========================================
    # Test Regeneration Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_regenerate_failed_tests(self, mock_async_db):
        """Test regeneration of failed tests"""
        masterplan_id = uuid4()
        test_id_1 = uuid4()
        test_id_2 = uuid4()

        # Create mock failed tests
        failed_test_1 = AcceptanceTest(
            test_id=test_id_1,
            masterplan_id=masterplan_id,
            requirement_text="Must validate email",
            requirement_priority="must",
            test_code="# Old test code",
            test_language="pytest"
        )
        failed_test_2 = AcceptanceTest(
            test_id=test_id_2,
            masterplan_id=masterplan_id,
            requirement_text="Should be responsive",
            requirement_priority="should",
            test_code="# Old test code",
            test_language="pytest"
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [failed_test_1, failed_test_2]
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        regenerated = await generator.regenerate_failed_tests(
            masterplan_id,
            [test_id_1, test_id_2]
        )

        assert len(regenerated) == 2

        # Verify test code was updated
        assert regenerated[0].test_code != "# Old test code"
        assert regenerated[1].test_code != "# Old test code"

        # Verify commit was called
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_no_failed_tests(self, mock_async_db):
        """Test regeneration when no tests found"""
        masterplan_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        regenerated = await generator.regenerate_failed_tests(
            masterplan_id,
            [uuid4()]
        )

        assert regenerated == []

    # ========================================
    # Statistics Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_get_test_statistics(self, mock_async_db):
        """Test statistics calculation"""
        masterplan_id = uuid4()

        # Create mock tests
        tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Test 1",
                requirement_priority="must",
                test_code="",
                test_language="pytest",
                timeout_seconds=30
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Test 2",
                requirement_priority="must",
                test_code="",
                test_language="pytest",
                timeout_seconds=40
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Test 3",
                requirement_priority="should",
                test_code="",
                test_language="vitest",
                timeout_seconds=20
            ),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = tests
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        stats = await generator.get_test_statistics(masterplan_id)

        assert stats['total_tests'] == 3
        assert stats['must_tests'] == 2
        assert stats['should_tests'] == 1
        assert stats['languages'] == {'pytest': 2, 'vitest': 1}
        assert stats['avg_timeout'] == 30  # (30 + 40 + 20) / 3

    @pytest.mark.asyncio
    async def test_get_test_statistics_empty(self, mock_async_db):
        """Test statistics for masterplan with no tests"""
        masterplan_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        stats = await generator.get_test_statistics(masterplan_id)

        assert stats['total_tests'] == 0
        assert stats['must_tests'] == 0
        assert stats['should_tests'] == 0
        assert stats['languages'] == {}
        assert stats['avg_timeout'] == 0

    # ========================================
    # Deletion Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_delete_tests_for_masterplan(self, mock_async_db):
        """Test deletion of all tests for a masterplan"""
        masterplan_id = uuid4()

        # Create mock tests
        tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Test 1",
                requirement_priority="must",
                test_code="",
                test_language="pytest"
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Test 2",
                requirement_priority="should",
                test_code="",
                test_language="pytest"
            ),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = tests
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        count = await generator.delete_tests_for_masterplan(masterplan_id)

        assert count == 2

        # Verify delete was called for each test
        assert mock_async_db.delete.call_count == 2

        # Verify commit was called
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tests_none_found(self, mock_async_db):
        """Test deletion when no tests exist"""
        masterplan_id = uuid4()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        generator = AcceptanceTestGenerator(mock_async_db)
        count = await generator.delete_tests_for_masterplan(masterplan_id)

        assert count == 0
        mock_async_db.delete.assert_not_called()
