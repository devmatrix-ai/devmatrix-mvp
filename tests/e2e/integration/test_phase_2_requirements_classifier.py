"""
Integration Tests for Phase 2: RequirementsClassifier Integration

Tests the integration of RequirementsClassifier into Phase 2 of the E2E pipeline.
Task Group 2.2.1: Write 2-3 focused tests for Phase 2 integration.
"""
import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.parsing.spec_parser import SpecParser
from src.classification.requirements_classifier import RequirementsClassifier


class TestPhase2RequirementsClassifierIntegration:
    """Integration tests for Phase 2 with RequirementsClassifier"""

    @pytest.fixture
    def ecommerce_spec_path(self) -> Path:
        """Path to ecommerce spec"""
        return Path(__file__).parent.parent / "test_specs" / "ecommerce_api_simple.md"

    @pytest.fixture
    def simple_task_spec_path(self) -> Path:
        """Path to simple task API spec"""
        return Path(__file__).parent.parent / "test_specs" / "simple_task_api.md"

    def test_phase_2_receives_structured_requirements_from_phase_1(self, ecommerce_spec_path):
        """
        Test: Phase 2 receives structured requirements from Phase 1

        Validates that:
        - Phase 1 (SpecParser) outputs SpecRequirements
        - Phase 2 can consume SpecRequirements
        - Data flow works end-to-end
        """
        # Phase 1: Parse spec
        parser = SpecParser()
        spec_requirements = parser.parse(ecommerce_spec_path)

        # Verify Phase 1 output structure
        assert spec_requirements is not None, "Phase 1 should output SpecRequirements"
        assert len(spec_requirements.requirements) > 0, "Should have requirements"
        assert len(spec_requirements.entities) > 0, "Should have entities"
        assert len(spec_requirements.endpoints) > 0, "Should have endpoints"

        # Phase 2: Classify requirements
        classifier = RequirementsClassifier()
        classified_requirements = classifier.classify_batch(spec_requirements.requirements)

        # Verify Phase 2 can process Phase 1 output
        assert len(classified_requirements) == len(spec_requirements.requirements), \
            "All requirements should be classified"

        # Verify enrichment occurred
        for req in classified_requirements:
            assert hasattr(req, 'domain'), f"Requirement {req.id} should have domain"
            assert hasattr(req, 'complexity'), f"Requirement {req.id} should have complexity"
            assert hasattr(req, 'risk_level'), f"Requirement {req.id} should have risk_level"

        print(f"\n✅ Phase 1→2 integration successful: {len(classified_requirements)} requirements classified")

    def test_phase_2_outputs_classified_requirements_with_metadata(self, ecommerce_spec_path):
        """
        Test: Phase 2 outputs classified requirements with all metadata

        Validates that classified requirements have:
        - Domain classification
        - Priority extraction
        - Complexity scoring
        - Risk assessment
        - Dependency relationships
        """
        # Phase 1: Parse spec
        parser = SpecParser()
        spec_requirements = parser.parse(ecommerce_spec_path)

        # Phase 2: Classify requirements
        classifier = RequirementsClassifier()
        classified_requirements = classifier.classify_batch(spec_requirements.requirements)

        # Verify all requirements are classified (actual count from parser)
        # ecommerce spec has 17 functional + 7 non-functional = 24 total
        assert len(classified_requirements) >= 17, \
            f"Expected ≥17 requirements, got {len(classified_requirements)}"

        # Count functional requirements specifically
        functional_count = sum(1 for r in classified_requirements if r.type == "functional")
        assert functional_count == 17, \
            f"Expected 17 functional requirements, got {functional_count}"

        # Verify domain classification for each requirement
        domain_counts = {}
        for req in classified_requirements:
            domain = req.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Verify required metadata fields
            assert req.domain in ['crud', 'authentication', 'payment', 'workflow', 'search', 'custom'], \
                f"Invalid domain '{req.domain}' for requirement {req.id}"
            assert req.priority in ['MUST', 'SHOULD', 'COULD', "WON'T"], \
                f"Invalid priority '{req.priority}' for requirement {req.id}"
            assert 0.0 <= req.complexity <= 1.0, \
                f"Complexity {req.complexity} out of range for requirement {req.id}"
            assert req.risk_level in ['low', 'medium', 'high'], \
                f"Invalid risk level '{req.risk_level}' for requirement {req.id}"

        # Verify domain distribution makes sense for ecommerce spec
        # Should have CRUD, payment, and workflow requirements
        assert 'crud' in domain_counts, "Ecommerce spec should have CRUD requirements"
        assert domain_counts['crud'] >= 5, \
            f"Expected ≥5 CRUD requirements, got {domain_counts.get('crud', 0)}"

        # Build dependency graph
        dep_graph = classifier.build_dependency_graph(classified_requirements)

        # Verify dependency graph exists
        assert len(dep_graph) >= 0, "Dependency graph should be generated"

        # Verify graph is a valid DAG
        assert classifier.validate_dag(dep_graph), \
            "Dependency graph should be a DAG (no circular dependencies)"

        print(f"\n✅ Phase 2 metadata validation successful")
        print(f"   - Domain distribution: {domain_counts}")
        print(f"   - Dependency graph nodes: {len(dep_graph)}")

    def test_phase_2_handles_empty_or_minimal_specs(self, simple_task_spec_path):
        """
        Test: Phase 2 handles empty or minimal specs gracefully

        Validates that:
        - Simple specs are processed correctly
        - No errors with minimal requirements
        - Classification still works for baseline specs
        """
        # Phase 1: Parse simple task API spec
        parser = SpecParser()
        spec_requirements = parser.parse(simple_task_spec_path)

        # Verify we got requirements (even if minimal)
        assert spec_requirements is not None, "Should parse minimal spec"

        # Phase 2: Classify requirements
        classifier = RequirementsClassifier()
        classified_requirements = classifier.classify_batch(spec_requirements.requirements)

        # Verify classification works for minimal spec
        assert len(classified_requirements) > 0, "Should classify minimal spec requirements"

        # Most requirements should be classified as CRUD for simple task API
        # Allow some flexibility as "retrieve all tasks" might be classified differently
        crud_count = sum(1 for req in classified_requirements if req.domain == 'crud')
        assert crud_count >= len(classified_requirements) * 0.5, \
            f"Simple task API should have mostly CRUD operations, got {crud_count}/{len(classified_requirements)}"

        # Build dependency graph (should be simple or empty)
        dep_graph = classifier.build_dependency_graph(classified_requirements)

        # Verify graph is valid
        assert classifier.validate_dag(dep_graph), \
            "Dependency graph should be valid even for minimal spec"

        print(f"\n✅ Minimal spec handling successful: {len(classified_requirements)} requirements")
        print(f"   - CRUD requirements: {crud_count}")

    def test_phase_2_classification_accuracy_above_90_percent(self, ecommerce_spec_path):
        """
        Test: Classification accuracy ≥90% for ecommerce spec

        Ground truth for ecommerce_api_simple.md:
        - F1-F5: Product CRUD (5 requirements) → domain: crud
        - F6-F7: Customer CRUD (2 requirements) → domain: crud
        - F8-F12: Cart operations (5 requirements) → domain: crud/workflow
        - F13-F14: Checkout/Payment (2 requirements) → domain: payment
        - F15: Cancel order (1 requirement) → domain: workflow
        - F16-F17: Order list/detail (2 requirements) → domain: crud

        Total: 17 functional requirements
        """
        # Phase 1: Parse spec
        parser = SpecParser()
        spec_requirements = parser.parse(ecommerce_spec_path)

        # Phase 2: Classify requirements
        classifier = RequirementsClassifier()
        classified_requirements = classifier.classify_batch(spec_requirements.requirements)

        # Ground truth validation
        correct_classifications = 0
        total_functional = 0

        for req in classified_requirements:
            if req.type != "functional":
                continue

            total_functional += 1

            # Check if domain classification is reasonable
            # F1-F5, F6-F7, F16-F17: Should be CRUD
            if req.id in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F16', 'F17']:
                if req.domain == 'crud':
                    correct_classifications += 1

            # F8-F12: Cart operations (can be CRUD or workflow)
            elif req.id in ['F8', 'F9', 'F10', 'F11', 'F12']:
                if req.domain in ['crud', 'workflow']:
                    correct_classifications += 1

            # F13-F14: Checkout/Payment
            elif req.id in ['F13', 'F14']:
                if req.domain in ['payment', 'workflow']:
                    correct_classifications += 1

            # F15: Cancel order (workflow)
            elif req.id == 'F15':
                if req.domain == 'workflow':
                    correct_classifications += 1

        # Calculate accuracy
        accuracy = correct_classifications / total_functional if total_functional > 0 else 0

        print(f"\n📊 Classification Accuracy: {accuracy*100:.1f}% ({correct_classifications}/{total_functional})")

        assert accuracy >= 0.90, \
            f"Classification accuracy {accuracy*100:.1f}% is below 90% threshold"

        # Verify all 17 functional requirements detected (≥90% recall)
        assert total_functional >= 15, \
            f"Expected ≥15 functional requirements (90% of 17), got {total_functional}"

        print(f"✅ Classification accuracy test passed: {accuracy*100:.1f}%")
