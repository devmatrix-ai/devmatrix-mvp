"""
Unit tests for Phase 3.5: SpecToApplicationIR.

Tests spec parsing, ApplicationIR generation, caching, and validation rule extraction.
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.specs.spec_to_application_ir import SpecToApplicationIR
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DataType
from src.cognitive.ir.infrastructure_model import DatabaseType
from src.cognitive.ir.validation_model import ValidationType


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def converter(temp_cache_dir):
    """Create SpecToApplicationIR instance with temp cache."""
    return SpecToApplicationIR(cache_dir=temp_cache_dir)


class TestSpecToApplicationIRInitialization:
    """Tests for SpecToApplicationIR initialization."""

    def test_init_creates_cache_dir(self, temp_cache_dir):
        """Test that initialization creates cache directory."""
        converter = SpecToApplicationIR(cache_dir=temp_cache_dir)
        assert converter.CACHE_DIR.exists()
        assert converter.CACHE_DIR == temp_cache_dir

    def test_init_with_default_cache_dir(self):
        """Test initialization with default cache directory."""
        converter = SpecToApplicationIR()
        assert converter.CACHE_DIR == SpecToApplicationIR.CACHE_DIR


class TestDataTypeMapping:
    """Tests for data type string to enum conversion."""

    def test_parse_string_type(self, converter):
        """Test parsing string data type."""
        result = converter._parse_data_type("string")
        assert result == DataType.STRING

    def test_parse_integer_type(self, converter):
        """Test parsing integer data type."""
        result = converter._parse_data_type("integer")
        assert result == DataType.INTEGER

    def test_parse_float_type(self, converter):
        """Test parsing float data type."""
        result = converter._parse_data_type("float")
        assert result == DataType.FLOAT

    def test_parse_boolean_type(self, converter):
        """Test parsing boolean data type."""
        result = converter._parse_data_type("boolean")
        assert result == DataType.BOOLEAN

    def test_parse_uuid_type(self, converter):
        """Test parsing UUID data type."""
        result = converter._parse_data_type("uuid")
        assert result == DataType.UUID

    def test_parse_datetime_type(self, converter):
        """Test parsing datetime data type."""
        result = converter._parse_data_type("datetime")
        assert result == DataType.DATETIME

    def test_parse_unknown_defaults_to_string(self, converter):
        """Test that unknown types default to string."""
        result = converter._parse_data_type("unknown_type")
        assert result == DataType.STRING


class TestValidationTypeMapping:
    """Tests for validation type string to enum conversion."""

    def test_parse_format_type(self, converter):
        """Test parsing FORMAT validation type."""
        result = converter._parse_validation_type("FORMAT")
        assert result == ValidationType.FORMAT

    def test_parse_range_type(self, converter):
        """Test parsing RANGE validation type."""
        result = converter._parse_validation_type("RANGE")
        assert result == ValidationType.RANGE

    def test_parse_presence_type(self, converter):
        """Test parsing PRESENCE validation type."""
        result = converter._parse_validation_type("PRESENCE")
        assert result == ValidationType.PRESENCE

    def test_parse_custom_defaults(self, converter):
        """Test that unknown types default to CUSTOM."""
        result = converter._parse_validation_type("UNKNOWN")
        assert result == ValidationType.CUSTOM

    def test_parse_case_insensitive(self, converter):
        """Test that parsing is case-insensitive."""
        result = converter._parse_validation_type("format")
        assert result == ValidationType.FORMAT


class TestDatabaseTypeMapping:
    """Tests for database type string to enum conversion."""

    def test_parse_postgresql_type(self, converter):
        """Test parsing PostgreSQL database type."""
        result = converter._parse_database_type("postgresql")
        assert result == DatabaseType.POSTGRESQL

    def test_parse_mysql_type(self, converter):
        """Test parsing MySQL database type."""
        result = converter._parse_database_type("mysql")
        assert result == DatabaseType.MYSQL

    def test_parse_sqlite_type(self, converter):
        """Test parsing SQLite database type."""
        result = converter._parse_database_type("sqlite")
        assert result == DatabaseType.SQLITE


class TestJsonExtraction:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_json_from_code_block(self, converter):
        """Test extracting JSON from markdown code block."""
        response = '```json\n{"key": "value"}\n```'
        result = converter._extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_json_from_generic_code_block(self, converter):
        """Test extracting JSON from generic code block."""
        response = '```\n{"key": "value"}\n```'
        result = converter._extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_json_plain_text(self, converter):
        """Test extracting JSON from plain text."""
        response = '{"key": "value"}'
        result = converter._extract_json(response)
        assert result == '{"key": "value"}'


class TestImplicitRuleExtraction:
    """Tests for implicit validation rule extraction."""

    def test_extract_required_rule_from_not_nullable(self, converter):
        """Test extracting PRESENCE rule from is_nullable=False."""
        from src.cognitive.ir.domain_model import Entity, Attribute

        entity = Entity(
            name="Product",
            attributes=[
                Attribute(
                    name="name",
                    data_type=DataType.STRING,
                    is_nullable=False,
                )
            ],
        )

        rules = converter._extract_implicit_rules(entity.name, entity.attributes[0])

        assert len(rules) > 0
        assert any(r.type == ValidationType.PRESENCE for r in rules)

    def test_extract_uniqueness_rule(self, converter):
        """Test extracting UNIQUENESS rule from is_unique=True."""
        from src.cognitive.ir.domain_model import Entity, Attribute

        entity = Entity(
            name="Product",
            attributes=[
                Attribute(
                    name="email",
                    data_type=DataType.STRING,
                    is_unique=True,
                )
            ],
        )

        rules = converter._extract_implicit_rules(entity.name, entity.attributes[0])

        assert any(r.type == ValidationType.UNIQUENESS for r in rules)

    def test_extract_range_constraint(self, converter):
        """Test extracting RANGE constraint from min_value/max_value."""
        from src.cognitive.ir.domain_model import Entity, Attribute

        entity = Entity(
            name="Product",
            attributes=[
                Attribute(
                    name="price",
                    data_type=DataType.FLOAT,
                    constraints={"min_value": 0, "max_value": 10000},
                )
            ],
        )

        rules = converter._extract_implicit_rules(entity.name, entity.attributes[0])

        assert any(r.type == ValidationType.RANGE for r in rules)
        range_rule = next(r for r in rules if r.type == ValidationType.RANGE)
        assert ">= 0" in range_rule.condition
        assert "<= 10000" in range_rule.condition

    def test_extract_length_constraint(self, converter):
        """Test extracting FORMAT constraint from min_length/max_length."""
        from src.cognitive.ir.domain_model import Entity, Attribute

        entity = Entity(
            name="Product",
            attributes=[
                Attribute(
                    name="code",
                    data_type=DataType.STRING,
                    constraints={"min_length": 3, "max_length": 10},
                )
            ],
        )

        rules = converter._extract_implicit_rules(entity.name, entity.attributes[0])

        assert any(r.type == ValidationType.FORMAT for r in rules)

    def test_extract_enum_constraint(self, converter):
        """Test extracting STATUS_TRANSITION constraint from enum_values."""
        from src.cognitive.ir.domain_model import Entity, Attribute

        entity = Entity(
            name="Order",
            attributes=[
                Attribute(
                    name="status",
                    data_type=DataType.STRING,
                    constraints={"enum_values": ["pending", "completed", "cancelled"]},
                )
            ],
        )

        rules = converter._extract_implicit_rules(entity.name, entity.attributes[0])

        status_rules = [r for r in rules if r.type == ValidationType.STATUS_TRANSITION]
        assert len(status_rules) > 0
        assert "pending" in status_rules[0].condition


class TestHashGeneration:
    """Tests for spec content hashing."""

    def test_hash_consistency(self, converter):
        """Test that same content produces same hash."""
        content = "spec content"
        hash1 = converter._hash_spec(content)
        hash2 = converter._hash_spec(content)
        assert hash1 == hash2

    def test_hash_different_for_different_content(self, converter):
        """Test that different content produces different hashes."""
        hash1 = converter._hash_spec("content1")
        hash2 = converter._hash_spec("content2")
        assert hash1 != hash2

    def test_hash_length(self, converter):
        """Test that hash has expected length (SHA256 = 64 chars)."""
        hash_result = converter._hash_spec("test")
        assert len(hash_result) == 64


class TestCacheOperations:
    """Tests for cache save/load operations."""

    def test_save_to_cache_creates_file(self, converter, temp_cache_dir):
        """Test that saving creates cache file."""
        from src.cognitive.ir.application_ir import ApplicationIR
        from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute
        from src.cognitive.ir.api_model import APIModelIR
        from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, DatabaseType

        app_ir = ApplicationIR(
            name="test_app",
            domain_model=DomainModelIR(
                entities=[
                    Entity(
                        name="Product",
                        attributes=[
                            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
                            Attribute(name="name", data_type=DataType.STRING),
                        ],
                    )
                ]
            ),
            api_model=APIModelIR(endpoints=[]),
            infrastructure_model=InfrastructureModelIR(
                database=DatabaseConfig(
                    type=DatabaseType.POSTGRESQL,
                    port=5432,
                    name="app_db",
                    user="app_user",
                    password_env_var="DB_PASSWORD",
                )
            ),
        )

        spec_hash = converter._hash_spec("test spec")
        cache_path = temp_cache_dir / "test_app_12345678.json"

        converter._save_to_cache(app_ir, cache_path, spec_hash, "test_app.md")

        assert cache_path.exists()
        with open(cache_path) as f:
            data = json.load(f)
        assert data["spec_hash"] == spec_hash

    def test_clear_cache_by_pattern(self, converter, temp_cache_dir):
        """Test clearing cache by spec path pattern."""
        # Create dummy cache files
        cache_file1 = temp_cache_dir / "app_12345678.json"
        cache_file2 = temp_cache_dir / "app_87654321.json"
        cache_file3 = temp_cache_dir / "other_12345678.json"

        cache_file1.write_text("{}")
        cache_file2.write_text("{}")
        cache_file3.write_text("{}")

        converter.clear_cache("app.md")

        assert not cache_file1.exists()
        assert not cache_file2.exists()
        assert cache_file3.exists()

    def test_clear_all_cache(self, converter, temp_cache_dir):
        """Test clearing all cache files."""
        cache_file1 = temp_cache_dir / "app_12345678.json"
        cache_file2 = temp_cache_dir / "other_87654321.json"

        cache_file1.write_text("{}")
        cache_file2.write_text("{}")

        converter.clear_cache()

        assert not cache_file1.exists()
        assert not cache_file2.exists()


class TestCacheInfo:
    """Tests for cache information retrieval."""

    def test_get_cache_info_no_cache(self, converter):
        """Test getting info when cache doesn't exist."""
        info = converter.get_cache_info("nonexistent.md")
        assert info["cached"] is False

    def test_get_cache_info_with_cache(self, converter, temp_cache_dir):
        """Test getting info when cache exists."""
        cache_file = temp_cache_dir / "app_12345678.json"
        cache_data = {
            "spec_hash": "12345678",
            "spec_path": "app.md",
            "generated_at": "2024-01-01T00:00:00",
            "application_ir": {
                "name": "app",
                "domain_model": {
                    "entities": [
                        {
                            "name": "Product",
                            "attributes": [],
                            "relationships": [],
                        }
                    ]
                },
                "validation_model": {
                    "rules": [
                        {
                            "entity": "Product",
                            "attribute": "name",
                            "type": "presence",
                            "condition": "required",
                            "enforcement_type": "description",
                        }
                    ]
                },
            },
        }

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        info = converter.get_cache_info("app.md")

        assert info["cached"] is True
        assert info["spec_hash"] == "12345678"
