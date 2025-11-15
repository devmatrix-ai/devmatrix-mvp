"""
Unit Tests for Semantic Task Signatures (STS)

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Hash consistency and uniqueness
- Similarity scoring with known values
- I/O type extraction from Python functions
- Domain classification
- Constraint parsing
- Extraction from AtomicUnit database objects
- Edge cases and validation
"""

import pytest
from typing import Dict, Any, List

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.signatures.semantic_signature import (
    SemanticTaskSignature,
    compute_semantic_hash,
    similarity_score,
    from_atomic_unit,
)


class TestSemanticTaskSignatureDataclass:
    """Test SemanticTaskSignature dataclass validation and structure."""

    def test_signature_instantiation_with_all_fields(self):
        """Test creating a complete SemanticTaskSignature."""
        signature = SemanticTaskSignature(
            purpose="Validate user email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool", "error_message": "Optional[str]"},
            domain="authentication",
            constraints=["RFC 5322 compliant", "Max length 254 chars"],
            security_level="medium",
            performance_tier="fast",
            idempotency=True,
        )

        assert signature.purpose == "Validate user email format"
        assert signature.intent == "validate"
        assert signature.domain == "authentication"
        assert signature.security_level == "medium"
        assert signature.performance_tier == "fast"
        assert signature.idempotency is True
        assert len(signature.constraints) == 2

    def test_signature_instantiation_with_minimal_fields(self):
        """Test creating SemanticTaskSignature with only required fields."""
        signature = SemanticTaskSignature(
            purpose="Transform data structure",
            intent="transform",
            inputs={"data": "dict"},
            outputs={"result": "dict"},
            domain="data_processing",
        )

        assert signature.purpose == "Transform data structure"
        assert signature.intent == "transform"
        assert signature.domain == "data_processing"
        # Check defaults for optional fields
        assert signature.constraints == []
        assert signature.security_level == "low"
        assert signature.performance_tier == "standard"
        assert signature.idempotency is False

    def test_signature_validation_rejects_empty_purpose(self):
        """Test that empty purpose string raises validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            SemanticTaskSignature(
                purpose="",  # Invalid
                intent="validate",
                inputs={"x": "int"},
                outputs={"y": "int"},
                domain="general",
            )

    def test_signature_validation_accepts_valid_domains(self):
        """Test that valid domain categories are accepted."""
        valid_domains = [
            "authentication",
            "authorization",
            "data_processing",
            "api",
            "database",
            "ui",
            "testing",
            "infrastructure",
        ]

        for domain in valid_domains:
            signature = SemanticTaskSignature(
                purpose="Test purpose",
                intent="create",
                inputs={},
                outputs={},
                domain=domain,
            )
            assert signature.domain == domain


class TestHashComputation:
    """Test hash computation for semantic consistency."""

    def test_hash_consistency_same_signature_same_hash(self):
        """Test that identical signatures produce identical hashes."""
        sig1 = SemanticTaskSignature(
            purpose="Calculate tax amount",
            intent="calculate",
            inputs={"price": "float", "tax_rate": "float"},
            outputs={"tax": "float"},
            domain="financial",
            security_level="high",
            performance_tier="fast",
        )

        sig2 = SemanticTaskSignature(
            purpose="Calculate tax amount",
            intent="calculate",
            inputs={"price": "float", "tax_rate": "float"},
            outputs={"tax": "float"},
            domain="financial",
            security_level="high",
            performance_tier="fast",
        )

        hash1 = compute_semantic_hash(sig1)
        hash2 = compute_semantic_hash(sig2)

        assert hash1 == hash2, "Identical signatures must produce identical hashes"
        assert len(hash1) == 64, "Hash should be 64-character SHA256 hex string"

    def test_hash_uniqueness_different_signatures_different_hashes(self):
        """Test that different signatures produce different hashes."""
        sig1 = SemanticTaskSignature(
            purpose="Validate email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        sig2 = SemanticTaskSignature(
            purpose="Validate phone number",  # Different purpose
            intent="validate",
            inputs={"phone": "str"},  # Different inputs
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        hash1 = compute_semantic_hash(sig1)
        hash2 = compute_semantic_hash(sig2)

        assert hash1 != hash2, "Different signatures must produce different hashes"

    def test_hash_deterministic_across_runs(self):
        """Test that hash computation is deterministic."""
        signature = SemanticTaskSignature(
            purpose="Test determinism",
            intent="test",
            inputs={"x": "int"},
            outputs={"y": "int"},
            domain="testing",
        )

        # Compute hash multiple times
        hashes = [compute_semantic_hash(signature) for _ in range(10)]

        # All hashes should be identical
        assert len(set(hashes)) == 1, "Hash must be deterministic"


class TestSimilarityScoring:
    """Test similarity scoring algorithm with known values."""

    def test_similarity_identical_signatures_returns_1_0(self):
        """Test that identical signatures have similarity = 1.0."""
        sig = SemanticTaskSignature(
            purpose="Create user account",
            intent="create",
            inputs={"email": "str", "password": "str"},
            outputs={"user_id": "UUID"},
            domain="authentication",
            constraints=["Password min 8 chars", "Email must be unique"],
        )

        similarity = similarity_score(sig, sig)
        assert similarity == pytest.approx(1.0, abs=0.01)

    def test_similarity_completely_different_signatures_returns_low_score(self):
        """Test that completely different signatures have low similarity."""
        sig1 = SemanticTaskSignature(
            purpose="Validate user email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        sig2 = SemanticTaskSignature(
            purpose="Calculate shipping cost",
            intent="calculate",
            inputs={"weight": "float", "distance": "float"},
            outputs={"cost": "Decimal"},
            domain="logistics",
        )

        similarity = similarity_score(sig1, sig2)
        assert similarity < 0.3, "Completely different signatures should have low similarity"

    def test_similarity_same_domain_different_purpose_moderate_score(self):
        """Test signatures with same domain but different purpose."""
        sig1 = SemanticTaskSignature(
            purpose="Create user account",
            intent="create",
            inputs={"email": "str", "password": "str"},
            outputs={"user_id": "UUID"},
            domain="authentication",
        )

        sig2 = SemanticTaskSignature(
            purpose="Validate user credentials",
            intent="validate",
            inputs={"email": "str", "password": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",  # Same domain
        )

        similarity = similarity_score(sig1, sig2)
        # Same domain contributes 20%, different purpose/intent reduces overall
        assert 0.3 < similarity < 0.7, "Same domain, different purpose should be moderate"

    def test_similarity_scoring_weights_applied_correctly(self):
        """Test that similarity weights are applied correctly."""
        # Two signatures with partial overlap
        sig1 = SemanticTaskSignature(
            purpose="Process user payment",  # Similar words
            intent="process",
            inputs={"amount": "Decimal", "user_id": "UUID"},
            outputs={"transaction_id": "UUID"},
            domain="financial",
            constraints=["Amount > 0", "User verified"],
        )

        sig2 = SemanticTaskSignature(
            purpose="Process payment transaction",  # Similar words
            intent="process",
            inputs={"amount": "Decimal", "customer_id": "UUID"},  # Partial overlap
            outputs={"transaction_id": "UUID"},
            domain="financial",  # Same domain
            constraints=["Amount > 0"],  # Partial overlap
        )

        similarity = similarity_score(sig1, sig2)

        # Expected contributions:
        # - Purpose similarity (40%): High (~0.6) → ~0.24
        # - I/O similarity (30%): Moderate (~0.4) → ~0.12
        # - Domain similarity (20%): Exact (1.0) → 0.20
        # - Constraints similarity (10%): Partial (~0.33) → ~0.03
        # Total expected: ~0.60
        assert 0.55 < similarity < 0.70, f"Expected ~0.60, got {similarity}"


class TestDomainClassification:
    """Test automatic domain classification."""

    def test_domain_classification_from_keywords_auth(self):
        """Test domain classification for authentication tasks."""
        signature = SemanticTaskSignature(
            purpose="Verify user login credentials",
            intent="validate",
            inputs={"username": "str", "password": "str"},
            outputs={"is_authenticated": "bool"},
            domain="auto",  # Should auto-classify
        )

        # After auto-classification
        assert signature.domain in ["authentication", "authorization"]

    def test_domain_classification_from_keywords_database(self):
        """Test domain classification for database tasks."""
        signature = SemanticTaskSignature(
            purpose="Query user records from database",
            intent="retrieve",
            inputs={"user_id": "UUID"},
            outputs={"user_data": "dict"},
            domain="auto",
        )

        assert signature.domain == "database"

    def test_domain_classification_from_keywords_api(self):
        """Test domain classification for API tasks."""
        signature = SemanticTaskSignature(
            purpose="Send HTTP request to external API endpoint",
            intent="execute",
            inputs={"url": "str", "payload": "dict"},
            outputs={"response": "dict"},
            domain="auto",
        )

        assert signature.domain == "api"


class TestIOTypeExtraction:
    """Test I/O type extraction from Python code."""

    def test_extract_io_types_from_function_signature(self):
        """Test extracting input/output types from Python function."""

        def sample_function(email: str, age: int) -> bool:
            """Check if user is valid."""
            return len(email) > 0 and age >= 18

        # Extract I/O types from function
        inputs, outputs = extract_io_types_from_function(sample_function)

        assert inputs == {"email": "str", "age": "int"}
        assert outputs == {"return": "bool"}

    def test_extract_io_types_from_async_function(self):
        """Test extracting types from async function."""

        async def async_function(user_id: str) -> dict:
            """Fetch user data asynchronously."""
            return {"id": user_id}

        inputs, outputs = extract_io_types_from_function(async_function)

        assert inputs == {"user_id": "str"}
        assert outputs == {"return": "dict"}


class TestAtomicUnitExtraction:
    """Test extraction from AtomicUnit database objects."""

    def test_extract_from_atomic_unit_basic(self):
        """Test basic extraction from AtomicUnit object."""
        # Mock AtomicUnit object (from masterplan_subtasks table)
        atomic_unit = type('AtomicUnit', (), {
            'description': 'Validate user email format',
            'code_snippet': 'def validate_email(email: str) -> bool:\n    return "@" in email',
            'dependencies': [],
            'complexity_score': 0.2,
        })()

        signature = from_atomic_unit(atomic_unit)

        assert signature.purpose == "Validate user email format"
        assert signature.intent == "validate"  # Inferred from "Validate"
        assert "email" in signature.inputs
        assert signature.inputs["email"] == "str"
        assert "return" in signature.outputs
        assert signature.outputs["return"] == "bool"

    def test_extract_domain_from_atomic_unit_description(self):
        """Test domain extraction from description keywords."""
        atomic_unit = type('AtomicUnit', (), {
            'description': 'Create database migration for user authentication',
            'code_snippet': '',
            'dependencies': [],
        })()

        signature = from_atomic_unit(atomic_unit)

        # Should detect both "database" and "authentication" keywords
        assert signature.domain in ["database", "authentication"]

    def test_extract_intent_from_action_verbs(self):
        """Test intent extraction from action verbs in description."""
        test_cases = [
            ("Create new user account", "create"),
            ("Validate input parameters", "validate"),
            ("Transform data structure", "transform"),
            ("Delete old records", "delete"),
            ("Update user profile", "update"),
            ("Retrieve user data", "retrieve"),
        ]

        for description, expected_intent in test_cases:
            atomic_unit = type('AtomicUnit', (), {
                'description': description,
                'code_snippet': '',
                'dependencies': [],
            })()

            signature = from_atomic_unit(atomic_unit)
            assert signature.intent == expected_intent


# Helper function stub (will be implemented in semantic_signature.py)
def extract_io_types_from_function(func):
    """Extract input/output types from Python function signature."""
    # This will be imported from semantic_signature module
    from src.cognitive.signatures.semantic_signature import extract_io_types_from_function as _extract
    return _extract(func)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
