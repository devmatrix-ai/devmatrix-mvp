"""
Tests for RequirementParser

Tests requirement extraction, classification, and validation from masterplan markdown.
"""
import pytest
from uuid import uuid4

from src.testing.requirement_parser import RequirementParser, Requirement


class TestRequirementParser:
    """Test RequirementParser functionality"""

    @pytest.fixture
    def parser(self):
        """Create RequirementParser instance"""
        return RequirementParser()

    @pytest.fixture
    def masterplan_id(self):
        """Generate test masterplan ID"""
        return uuid4()

    @pytest.fixture
    def valid_markdown(self):
        """Valid masterplan markdown with MUST and SHOULD requirements"""
        return """
# Masterplan: User Authentication

## Requirements

### MUST
- Must use JWT tokens for authentication
- Must validate email format before registration
- Must hash passwords using bcrypt
- Must implement rate limiting (5 attempts/minute)
- Must return 401 for invalid credentials

### SHOULD
- Should support OAuth 2.0 integration
- Should cache user sessions for 30 minutes
- Should log all authentication attempts
"""

    def test_parse_must_requirements(self, parser, masterplan_id, valid_markdown):
        """Test parsing MUST requirements"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']

        assert len(must_reqs) == 5
        assert "use JWT tokens" in must_reqs[0].text
        assert "validate email format" in must_reqs[1].text
        assert "hash passwords" in must_reqs[2].text

    def test_parse_should_requirements(self, parser, masterplan_id, valid_markdown):
        """Test parsing SHOULD requirements"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)

        should_reqs = [r for r in requirements if r.priority == 'should']

        assert len(should_reqs) == 3
        assert "OAuth 2.0" in should_reqs[0].text
        assert "cache user sessions" in should_reqs[1].text
        assert "log all authentication" in should_reqs[2].text

    def test_requirement_id_generation(self, parser, masterplan_id, valid_markdown):
        """Test requirement ID generation follows pattern"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']

        assert must_reqs[0].requirement_id == f"{masterplan_id}_must_0"
        assert must_reqs[1].requirement_id == f"{masterplan_id}_must_1"
        assert must_reqs[4].requirement_id == f"{masterplan_id}_must_4"

    def test_parse_empty_markdown(self, parser, masterplan_id):
        """Test parsing empty markdown returns empty list"""
        requirements = parser.parse_masterplan(masterplan_id, "")

        assert len(requirements) == 0

    def test_parse_markdown_without_requirements(self, parser, masterplan_id):
        """Test markdown without requirement sections"""
        markdown = """
# Some Title

This is just text without requirements.

## Other Section

More text.
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)

        assert len(requirements) == 0

    def test_parse_only_must_requirements(self, parser, masterplan_id):
        """Test markdown with only MUST requirements"""
        markdown = """
### MUST
- Must do this
- Must do that
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)

        assert len(requirements) == 2
        assert all(r.priority == 'must' for r in requirements)

    def test_parse_only_should_requirements(self, parser, masterplan_id):
        """Test markdown with only SHOULD requirements"""
        markdown = """
### SHOULD
- Should do this
- Should do that
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)

        assert len(requirements) == 2
        assert all(r.priority == 'should' for r in requirements)

    def test_validate_valid_requirements(self, parser, masterplan_id, valid_markdown):
        """Test validation of valid requirements"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)
        validation = parser.validate_requirements(requirements)

        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0
        assert validation['must_count'] == 5
        assert validation['should_count'] == 3

    def test_validate_empty_requirements(self, parser):
        """Test validation of empty requirements list"""
        validation = parser.validate_requirements([])

        assert validation['is_valid'] is False
        assert "No requirements found in masterplan" in validation['errors']

    def test_validate_no_must_requirements(self, parser, masterplan_id):
        """Test validation warns without MUST requirements"""
        markdown = """
### SHOULD
- Should do something
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)
        validation = parser.validate_requirements(requirements)

        # Changed: Now returns valid=True with warning instead of error
        assert validation['is_valid'] is True
        assert any("No MUST requirements found" in w for w in validation['warnings'])

    def test_validate_duplicate_requirements(self, parser, masterplan_id):
        """Test validation detects duplicates"""
        markdown = """
### MUST
- Must use JWT tokens
- Must use JWT tokens
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)
        validation = parser.validate_requirements(requirements)

        assert validation['is_valid'] is False
        assert any("duplicate" in err.lower() for err in validation['errors'])

    def test_validate_empty_requirement_text(self, parser):
        """Test validation detects empty requirement text"""
        requirements = [
            Requirement(
                text="",
                priority='must',
                requirement_id='test_1',
                section='MUST',
                metadata={}
            )
        ]
        validation = parser.validate_requirements(requirements)

        assert validation['is_valid'] is False
        assert "Empty requirement found in MUST section" in validation['errors']

    def test_warning_too_many_must_requirements(self, parser, masterplan_id):
        """Test warning for >15 MUST requirements"""
        must_items = [f"- Must do task {i}" for i in range(20)]
        markdown = f"### MUST\n" + "\n".join(must_items)

        requirements = parser.parse_masterplan(masterplan_id, markdown)
        validation = parser.validate_requirements(requirements)

        assert validation['is_valid'] is True
        assert any("too many must" in w.lower() for w in validation['warnings'])

    def test_warning_too_many_should_requirements(self, parser, masterplan_id):
        """Test warning for >10 SHOULD requirements"""
        must_items = ["- Must do something"]
        should_items = [f"- Should do task {i}" for i in range(15)]
        markdown = f"### MUST\n" + "\n".join(must_items) + "\n### SHOULD\n" + "\n".join(should_items)

        requirements = parser.parse_masterplan(masterplan_id, markdown)
        validation = parser.validate_requirements(requirements)

        assert validation['is_valid'] is True
        assert any("too many should" in w.lower() for w in validation['warnings'])

    def test_metadata_includes_line_number(self, parser, masterplan_id, valid_markdown):
        """Test requirement metadata includes line number"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)

        assert 'line_number' in requirements[0].metadata
        assert isinstance(requirements[0].metadata['line_number'], int)

    def test_section_classification(self, parser, masterplan_id, valid_markdown):
        """Test requirements are classified into correct sections"""
        requirements = parser.parse_masterplan(masterplan_id, valid_markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']
        should_reqs = [r for r in requirements if r.priority == 'should']

        assert all(r.section == 'MUST' for r in must_reqs)
        assert all(r.section == 'SHOULD' for r in should_reqs)

    def test_parse_multiple_must_sections(self, parser, masterplan_id):
        """Test parsing multiple MUST sections"""
        markdown = """
### MUST
- Must do A
- Must do B

Some text here

### MUST
- Must do C
- Must do D
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)
        must_reqs = [r for r in requirements if r.priority == 'must']

        assert len(must_reqs) == 4

    def test_requirement_text_cleaned(self, parser, masterplan_id):
        """Test requirement text is cleaned of extra whitespace"""
        markdown = """
### MUST
-   Must   do   something   with   spaces
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)

        assert requirements[0].text == "Must do something with spaces"

    def test_case_insensitive_section_headers(self, parser, masterplan_id):
        """Test section headers are case-insensitive"""
        markdown = """
### must
- Must do this

### SHOULD
- Should do that
"""
        requirements = parser.parse_masterplan(masterplan_id, markdown)

        assert len(requirements) == 2
        assert requirements[0].priority == 'must'
        assert requirements[1].priority == 'should'
