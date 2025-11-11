"""
Unit tests for RequirementParser

Tests requirement parsing from masterplan markdown:
- MUST/SHOULD section extraction
- Text cleaning and normalization
- Validation logic (duplicates, empty, counts)
- Metadata extraction (return values, exceptions, thresholds)
"""
import pytest
from uuid import uuid4
from src.testing.requirement_parser import RequirementParser, Requirement


class TestRequirementParser:
    """Test RequirementParser core functionality"""

    def setup_method(self):
        """Setup parser instance for each test"""
        self.parser = RequirementParser()
        self.masterplan_id = uuid4()

    # ========================================
    # Basic Parsing Tests
    # ========================================

    def test_parse_valid_must_requirements(self):
        """Test parsing valid MUST requirements"""
        markdown = """
# MasterPlan

## Requirements

### MUST
- User authentication must use JWT tokens
- Database transactions must be ACID compliant
- API responses must return JSON format

### SHOULD
- UI should be responsive
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']
        assert len(must_reqs) == 3
        assert must_reqs[0].text == 'User authentication must use JWT tokens'
        assert must_reqs[1].text == 'Database transactions must be ACID compliant'
        assert must_reqs[2].text == 'API responses must return JSON format'
        assert all(r.section == 'MUST' for r in must_reqs)

    def test_parse_valid_should_requirements(self):
        """Test parsing valid SHOULD requirements"""
        markdown = """
## Requirements

### SHOULD
- UI should be responsive on mobile devices
- API response time should be <200ms p95
- Logs should be structured JSON
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        should_reqs = [r for r in requirements if r.priority == 'should']
        assert len(should_reqs) == 3
        assert should_reqs[0].text == 'UI should be responsive on mobile devices'
        assert should_reqs[1].text == 'API response time should be <200ms p95'
        assert should_reqs[2].text == 'Logs should be structured JSON'
        assert all(r.section == 'SHOULD' for r in should_reqs)

    def test_parse_mixed_requirements(self):
        """Test parsing both MUST and SHOULD requirements"""
        markdown = """
### MUST
- Critical feature A
- Critical feature B

### SHOULD
- Nice to have X
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        assert len(requirements) == 3
        assert sum(1 for r in requirements if r.priority == 'must') == 2
        assert sum(1 for r in requirements if r.priority == 'should') == 1

    def test_parse_case_insensitive_headers(self):
        """Test parsing works with different case headers"""
        markdown_variations = [
            "### MUST\n- Req A\n### SHOULD\n- Req B",
            "### must\n- Req A\n### should\n- Req B",
            "### Must\n- Req A\n### Should\n- Req B",
            "### MuSt\n- Req A\n### ShOuLd\n- Req B"
        ]

        for markdown in markdown_variations:
            requirements = self.parser.parse_masterplan(uuid4(), markdown)
            assert len(requirements) == 2
            assert any(r.priority == 'must' for r in requirements)
            assert any(r.priority == 'should' for r in requirements)

    def test_parse_empty_markdown(self):
        """Test parsing empty markdown returns empty list"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, "")
        assert requirements == []

    def test_parse_no_requirements_section(self):
        """Test markdown without Requirements section"""
        markdown = """
# MasterPlan

## Tech Stack
- Python
- FastAPI
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)
        assert requirements == []

    def test_parse_whitespace_cleaning(self):
        """Test requirement text is cleaned of extra whitespace"""
        markdown = """
### MUST
- User   authentication    must    use   JWT
- Database  transactions   must be ACID
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        assert requirements[0].text == 'User authentication must use JWT'
        assert requirements[1].text == 'Database transactions must be ACID'

    # ========================================
    # Requirement ID Generation Tests
    # ========================================

    def test_requirement_id_format(self):
        """Test requirement_id follows correct format"""
        markdown = """
### MUST
- Req A
- Req B

### SHOULD
- Req C
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']
        should_reqs = [r for r in requirements if r.priority == 'should']

        assert must_reqs[0].requirement_id == f"{self.masterplan_id}_must_0"
        assert must_reqs[1].requirement_id == f"{self.masterplan_id}_must_1"
        assert should_reqs[0].requirement_id == f"{self.masterplan_id}_should_0"

    def test_requirement_ids_unique(self):
        """Test all requirement IDs are unique"""
        markdown = """
### MUST
- Req A
- Req B
- Req C

### SHOULD
- Req D
- Req E
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        req_ids = [r.requirement_id for r in requirements]
        assert len(req_ids) == len(set(req_ids))  # All unique

    # ========================================
    # Metadata Tests
    # ========================================

    def test_requirement_metadata_line_numbers(self):
        """Test metadata contains correct line numbers"""
        markdown = """Line 0
Line 1
### MUST
- Req A
Line 5
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        assert requirements[0].metadata['line_number'] == 2  # Line where ### MUST appears

    def test_requirement_metadata_block_index(self):
        """Test metadata contains correct block index"""
        markdown = """
### MUST
- Req A
- Req B
- Req C
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        assert requirements[0].metadata['block_index'] == 0
        assert requirements[1].metadata['block_index'] == 1
        assert requirements[2].metadata['block_index'] == 2

    # ========================================
    # Validation Tests
    # ========================================

    def test_validate_valid_requirements(self):
        """Test validation passes for valid requirements"""
        requirements = [
            Requirement("Auth must use JWT", "must", "id1", "MUST", {}),
            Requirement("UI should be responsive", "should", "id2", "SHOULD", {}),
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is True
        assert result['must_count'] == 1
        assert result['should_count'] == 1
        assert result['total_count'] == 2
        assert len(result['errors']) == 0

    def test_validate_empty_requirements(self):
        """Test validation fails for empty requirements list"""
        result = self.parser.validate_requirements([])

        assert result['is_valid'] is False
        assert "No requirements found" in result['errors'][0]
        assert result['must_count'] == 0
        assert result['should_count'] == 0

    def test_validate_duplicate_requirements(self):
        """Test validation detects duplicate requirements"""
        requirements = [
            Requirement("Auth must use JWT", "must", "id1", "MUST", {}),
            Requirement("Auth must use JWT", "must", "id2", "MUST", {}),
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is False
        assert any("Duplicate requirement" in err for err in result['errors'])

    def test_validate_empty_requirement_text(self):
        """Test validation detects empty requirement text"""
        requirements = [
            Requirement("", "must", "id1", "MUST", {}),
            Requirement("   ", "should", "id2", "SHOULD", {}),
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is False
        assert any("Empty requirement" in err for err in result['errors'])

    def test_validate_no_must_requirements_warning(self):
        """Test validation warns when no MUST requirements"""
        requirements = [
            Requirement("UI should be nice", "should", "id1", "SHOULD", {}),
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is True  # Warning, not error
        assert any("No MUST requirements" in warn for warn in result['warnings'])

    def test_validate_no_should_requirements_warning(self):
        """Test validation warns when no SHOULD requirements"""
        requirements = [
            Requirement("Auth must work", "must", "id1", "MUST", {}),
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is True  # Warning, not error
        assert any("No SHOULD requirements" in warn for warn in result['warnings'])

    def test_validate_too_many_must_requirements_warning(self):
        """Test validation warns when >15 MUST requirements"""
        requirements = [
            Requirement(f"Req {i}", "must", f"id{i}", "MUST", {})
            for i in range(16)
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is True  # Warning, not error
        assert any("Too many MUST requirements" in warn for warn in result['warnings'])

    def test_validate_too_many_should_requirements_warning(self):
        """Test validation warns when >10 SHOULD requirements"""
        requirements = [
            Requirement("Critical", "must", "id0", "MUST", {}),
        ] + [
            Requirement(f"Req {i}", "should", f"id{i}", "SHOULD", {})
            for i in range(11)
        ]

        result = self.parser.validate_requirements(requirements)

        assert result['is_valid'] is True  # Warning, not error
        assert any("Too many SHOULD requirements" in warn for warn in result['warnings'])

    # ========================================
    # Metadata Extraction Tests
    # ========================================

    def test_extract_metadata_return_value(self):
        """Test extraction of expected return values"""
        req = Requirement("API must return 200", "must", "id1", "MUST", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata['expected_value'] == '200'

    def test_extract_metadata_exception(self):
        """Test extraction of expected exceptions"""
        req = Requirement("Function must raise ValueError", "must", "id1", "MUST", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata['expected_exception'] == 'ValueError'

    def test_extract_metadata_threshold_less_than(self):
        """Test extraction of less-than thresholds"""
        req = Requirement("Response time must be <200ms", "must", "id1", "MUST", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata['comparison_operator'] == '<'
        assert metadata['threshold_value'] == 200
        assert metadata['threshold_unit'] == 'ms'

    def test_extract_metadata_threshold_greater_than(self):
        """Test extraction of greater-than thresholds"""
        req = Requirement("Success rate should be >95%", "should", "id1", "SHOULD", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata['comparison_operator'] == '>'
        assert metadata['threshold_value'] == 95

    def test_extract_metadata_validation_target(self):
        """Test extraction of validation targets"""
        req = Requirement("System must validate email", "must", "id1", "MUST", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata['validation_target'] == 'email'

    def test_extract_metadata_no_patterns(self):
        """Test extraction returns empty dict when no patterns match"""
        req = Requirement("System works correctly", "must", "id1", "MUST", {})
        metadata = self.parser.extract_requirement_metadata(req)

        assert metadata == {}

    # ========================================
    # Edge Cases
    # ========================================

    def test_parse_multiple_must_sections(self):
        """Test parsing handles multiple MUST sections"""
        markdown = """
### MUST
- Req A

### SHOULD
- Req B

### MUST
- Req C
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        must_reqs = [r for r in requirements if r.priority == 'must']
        assert len(must_reqs) == 2
        assert must_reqs[0].text == 'Req A'
        assert must_reqs[1].text == 'Req C'

    def test_parse_multiline_requirement(self):
        """Test parsing treats each line as separate requirement"""
        markdown = """
### MUST
- First line
continues here
- Second requirement
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        # Only lines starting with "- " are parsed
        assert len(requirements) == 2
        assert requirements[0].text == 'First line'
        assert requirements[1].text == 'Second requirement'

    def test_parse_special_characters(self):
        """Test parsing handles special characters in requirements"""
        markdown = """
### MUST
- Support UTF-8 encoding: é, ñ, 中文
- Handle regex: /^[a-z]+$/
- Parse JSON: {"key": "value"}
"""
        requirements = self.parser.parse_masterplan(self.masterplan_id, markdown)

        assert len(requirements) == 3
        assert 'é, ñ, 中文' in requirements[0].text
        assert '/^[a-z]+$/' in requirements[1].text
        assert '{"key": "value"}' in requirements[2].text
