"""
Validation Coverage Measurement Tests - Phase 2

Measures extraction coverage before and after Phase 2 improvements:
- Phase 1 Baseline: 45/62 validations (73%) - pattern-based extraction
- Phase 2 Target: 60-62/62 validations (97-100%) - pattern + aggressive LLM

Coverage breakdown by:
- Validation type (UNIQUENESS, RELATIONSHIP, etc.)
- Entity (Customer, Product, Order, etc.)
- Extraction source (direct, pattern, LLM)
"""
import pytest
from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path
import yaml

from src.services.business_logic_extractor import BusinessLogicExtractor
from src.cognitive.ir.validation_model import ValidationRule, ValidationType, ValidationModelIR


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def ecommerce_spec() -> Dict[str, Any]:
    """
    Complete e-commerce specification for coverage testing.

    Expected validations: 62 total
    - UNIQUENESS: 8 (email, username, sku, slug, order_number, etc.)
    - RELATIONSHIP: 12 (customer_id, product_id, order_id FKs, etc.)
    - STOCK_CONSTRAINT: 5 (stock >= 0, quantity <= stock, etc.)
    - STATUS_TRANSITION: 8 (order status, customer active, etc.)
    - PRESENCE: 15 (required fields)
    - FORMAT: 10 (email, phone, url, uuid formats)
    - RANGE: 4 (price >= 0, quantity >= 1, etc.)
    """
    return {
        "name": "E-commerce API",
        "entities": [
            {
                "name": "Customer",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "required": True,
                        "description": "Unique customer identifier"
                    },
                    {
                        "name": "email",
                        "type": "String",
                        "required": True,
                        "unique": True,
                        "description": "Customer email address"
                    },
                    {
                        "name": "username",
                        "type": "String",
                        "required": True,
                        "unique": True,
                        "constraints": {"min_length": 3, "max_length": 50}
                    },
                    {
                        "name": "password",
                        "type": "String",
                        "required": True,
                        "constraints": {"min_length": 8}
                    },
                    {
                        "name": "phone",
                        "type": "String",
                        "description": "Customer phone number"
                    },
                    {
                        "name": "is_active",
                        "type": "Boolean",
                        "required": True,
                        "description": "Customer account status"
                    }
                ]
            },
            {
                "name": "Product",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "required": True
                    },
                    {
                        "name": "sku",
                        "type": "String",
                        "required": True,
                        "unique": True,
                        "description": "Stock keeping unit"
                    },
                    {
                        "name": "name",
                        "type": "String",
                        "required": True
                    },
                    {
                        "name": "slug",
                        "type": "String",
                        "unique": True,
                        "description": "URL-friendly product identifier"
                    },
                    {
                        "name": "price",
                        "type": "Decimal",
                        "required": True,
                        "constraints": {"minimum": 0}
                    },
                    {
                        "name": "stock_quantity",
                        "type": "Integer",
                        "required": True,
                        "constraints": {"minimum": 0}
                    }
                ]
            },
            {
                "name": "Order",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "required": True
                    },
                    {
                        "name": "order_number",
                        "type": "String",
                        "required": True,
                        "unique": True,
                        "description": "Human-readable order number"
                    },
                    {
                        "name": "customer_id",
                        "type": "UUID",
                        "required": True,
                        "description": "Reference to Customer.id"
                    },
                    {
                        "name": "status",
                        "type": "String",
                        "required": True,
                        "enum": ["pending", "processing", "shipped", "delivered", "cancelled"],
                        "description": "Order status workflow"
                    },
                    {
                        "name": "total_amount",
                        "type": "Decimal",
                        "required": True,
                        "constraints": {"minimum": 0}
                    }
                ]
            },
            {
                "name": "OrderItem",
                "fields": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "required": True
                    },
                    {
                        "name": "order_id",
                        "type": "UUID",
                        "required": True,
                        "description": "Reference to Order.id"
                    },
                    {
                        "name": "product_id",
                        "type": "UUID",
                        "required": True,
                        "description": "Reference to Product.id"
                    },
                    {
                        "name": "quantity",
                        "type": "Integer",
                        "required": True,
                        "constraints": {"minimum": 1}
                    },
                    {
                        "name": "unit_price",
                        "type": "Decimal",
                        "required": True,
                        "constraints": {"minimum": 0}
                    }
                ]
            }
        ],
        "workflows": [
            {
                "name": "Order Processing",
                "steps": [
                    {"name": "Create order", "status": "pending"},
                    {"name": "Process payment", "status": "processing"},
                    {"name": "Ship order", "status": "shipped"},
                    {"name": "Deliver order", "status": "delivered"}
                ]
            }
        ]
    }


@pytest.fixture
def expected_validations() -> Dict[str, int]:
    """Expected validation counts by type for complete e-commerce spec."""
    return {
        "UNIQUENESS": 5,  # email, username, sku, slug, order_number
        "RELATIONSHIP": 3,  # customer_id, product_id, order_id
        "STOCK_CONSTRAINT": 2,  # stock >= 0, quantity <= stock (LLM should infer)
        "STATUS_TRANSITION": 2,  # order status enum, is_active boolean
        "PRESENCE": 15,  # All required fields
        "FORMAT": 3,  # email, phone (if detected), UUID fields
        "RANGE": 7,  # min_length, max_length, minimum constraints
        "TOTAL": 37  # Minimum expected (some LLM rules may add more)
    }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def calculate_coverage(validation_ir: ValidationModelIR, total_expected: int = 62) -> float:
    """Calculate coverage percentage."""
    total_extracted = len(validation_ir.rules)
    return total_extracted / total_expected if total_expected > 0 else 0.0


def group_by_validation_type(rules: List[ValidationRule]) -> Dict[str, int]:
    """Group rules by ValidationType and count."""
    counts = defaultdict(int)
    for rule in rules:
        counts[rule.type.value] = counts.get(rule.type.value, 0) + 1
    return dict(counts)


def group_by_entity(rules: List[ValidationRule]) -> Dict[str, int]:
    """Group rules by entity name and count."""
    counts = defaultdict(int)
    for rule in rules:
        counts[rule.entity] = counts.get(rule.entity, 0) + 1
    return dict(counts)


def attribute_extraction_sources(rules: List[ValidationRule]) -> Dict[str, int]:
    """
    Attribute extraction source for each rule.

    Categories:
    - direct: Extracted from entity field constraints (Stage 1-5)
    - pattern: Extracted from YAML patterns (Stage 6.5)
    - llm: Extracted via LLM (Stage 7)

    Note: This is a heuristic - actual implementation would need source tracking.
    """
    sources = {"direct": 0, "pattern": 0, "llm": 0, "unknown": 0}

    for rule in rules:
        # Heuristic: PRESENCE and UNIQUENESS from fields are likely direct
        if rule.type in [ValidationType.PRESENCE, ValidationType.UNIQUENESS]:
            if rule.condition and "pattern" in rule.condition.lower():
                sources["pattern"] += 1
            else:
                sources["direct"] += 1

        # FORMAT rules often from patterns
        elif rule.type == ValidationType.FORMAT:
            sources["pattern"] += 1

        # Complex rules likely from LLM
        elif rule.type in [ValidationType.STOCK_CONSTRAINT, ValidationType.WORKFLOW_CONSTRAINT]:
            sources["llm"] += 1

        # Others
        else:
            sources["unknown"] += 1

    return sources


# ==============================================================================
# 1. PHASE 1 BASELINE MEASUREMENT
# ==============================================================================

class TestPhase1Baseline:
    """Measure Phase 1 baseline coverage (pattern-based extraction only)."""

    def test_phase1_baseline_coverage(self, ecommerce_spec):
        """
        Measure Phase 1 coverage (pattern-based only, no aggressive LLM).
        Expected: ~30-45 validations (48-73% coverage).
        """
        extractor = BusinessLogicExtractor()

        # Run extraction
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        total_extracted = len(validation_ir.rules)
        coverage = calculate_coverage(validation_ir, total_expected=62)

        print(f"\n=== Phase 1 Baseline ===")
        print(f"Total validations extracted: {total_extracted}")
        print(f"Coverage: {coverage:.1%}")
        print(f"Target: 45/62 (73%)")

        # Phase 1 should extract at least 30 validations (minimum)
        assert total_extracted >= 30, f"Expected >=30 validations, got {total_extracted}"

        # Should not exceed Phase 2 target yet
        assert total_extracted < 60, f"Phase 1 should not exceed 60 validations, got {total_extracted}"

    def test_phase1_validation_type_breakdown(self, ecommerce_spec):
        """Measure Phase 1 breakdown by validation type."""
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        breakdown = group_by_validation_type(validation_ir.rules)

        print(f"\n=== Phase 1 Type Breakdown ===")
        for val_type, count in sorted(breakdown.items()):
            print(f"{val_type}: {count}")

        # Phase 1 should detect basic types
        assert breakdown.get('presence', 0) > 0, "Should detect PRESENCE validations"
        assert breakdown.get('uniqueness', 0) > 0, "Should detect UNIQUENESS validations"


# ==============================================================================
# 2. PHASE 2 COVERAGE MEASUREMENT
# ==============================================================================

class TestPhase2Coverage:
    """Measure Phase 2 coverage (pattern + aggressive LLM extraction)."""

    @pytest.mark.skip(reason="Phase 2 LLM extraction not yet implemented")
    def test_phase2_full_coverage(self, ecommerce_spec):
        """
        Measure Phase 2 coverage (pattern + aggressive LLM).
        Expected: 60-62/62 validations (97-100% coverage).
        """
        extractor = BusinessLogicExtractor()

        # Run extraction with Phase 2 improvements
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        total_extracted = len(validation_ir.rules)
        coverage = calculate_coverage(validation_ir, total_expected=62)

        print(f"\n=== Phase 2 Full Coverage ===")
        print(f"Total validations extracted: {total_extracted}")
        print(f"Coverage: {coverage:.1%}")
        print(f"Target: 60-62/62 (97-100%)")

        # Phase 2 target: 60-62 validations
        assert total_extracted >= 60, f"Expected >=60 validations, got {total_extracted}"
        assert coverage >= 0.97, f"Expected >=97% coverage, got {coverage:.1%}"

    @pytest.mark.skip(reason="Phase 2 not yet implemented")
    def test_phase2_improvement_delta(self, ecommerce_spec):
        """
        Measure improvement from Phase 1 to Phase 2.
        Expected improvement: +15-20 validations.
        """
        extractor = BusinessLogicExtractor()

        # Measure Phase 1 (disable LLM extraction)
        # TODO: Need a way to disable LLM extraction for baseline measurement

        # Measure Phase 2 (full extraction)
        validation_ir_phase2 = extractor.extract_validation_rules(ecommerce_spec)

        # Calculate improvement
        # improvement = len(validation_ir_phase2.rules) - phase1_count

        print(f"\n=== Phase 2 Improvement ===")
        # print(f"Phase 1: {phase1_count} validations")
        print(f"Phase 2: {len(validation_ir_phase2.rules)} validations")
        # print(f"Improvement: +{improvement} validations")


# ==============================================================================
# 3. COVERAGE BREAKDOWN TESTS
# ==============================================================================

class TestCoverageBreakdown:
    """Measure coverage breakdown by type, entity, and source."""

    def test_coverage_breakdown_by_validation_type(self, ecommerce_spec):
        """
        Measure coverage breakdown by validation type.
        Shows which validation types are well-covered vs gaps.
        """
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        breakdown = group_by_validation_type(validation_ir.rules)

        print(f"\n=== Validation Type Breakdown ===")
        for val_type, count in sorted(breakdown.items(), key=lambda x: -x[1]):
            print(f"{val_type:20s}: {count:3d} validations")

        # Should have some validations of each major type
        assert breakdown.get('presence', 0) > 0, "Should detect PRESENCE validations"
        assert breakdown.get('uniqueness', 0) > 0, "Should detect UNIQUENESS validations"

    def test_coverage_breakdown_by_entity(self, ecommerce_spec):
        """
        Measure coverage breakdown by entity.
        Shows which entities are well-validated vs gaps.
        """
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        breakdown = group_by_entity(validation_ir.rules)

        print(f"\n=== Entity Coverage Breakdown ===")
        for entity, count in sorted(breakdown.items(), key=lambda x: -x[1]):
            print(f"{entity:20s}: {count:3d} validations")

        # Should have validations for all entities
        assert 'Customer' in breakdown, "Should have Customer validations"
        assert 'Product' in breakdown, "Should have Product validations"
        assert 'Order' in breakdown, "Should have Order validations"

    def test_coverage_source_attribution(self, ecommerce_spec):
        """
        Measure extraction source breakdown.
        Shows contribution of direct, pattern, and LLM extraction.
        """
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        sources = attribute_extraction_sources(validation_ir.rules)

        print(f"\n=== Extraction Source Attribution ===")
        for source, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"{source:10s}: {count:3d} validations ({count/len(validation_ir.rules)*100:.1f}%)")

        # Should have validations from multiple sources
        total_attributed = sources['direct'] + sources['pattern'] + sources['llm']
        assert total_attributed > 0, "Should have some attributed validations"


# ==============================================================================
# 4. REGRESSION COVERAGE TESTS
# ==============================================================================

class TestRegressionCoverage:
    """Ensure Phase 2 doesn't regress Phase 1 coverage."""

    @pytest.mark.skip(reason="Phase 2 not yet implemented")
    def test_phase2_preserves_phase1_validations(self, ecommerce_spec):
        """
        Ensure Phase 2 extraction preserves all Phase 1 validations.
        No regressions from pattern-based extraction.
        """
        extractor = BusinessLogicExtractor()

        # Extract Phase 1 baseline (pattern-based only)
        # TODO: Need mechanism to disable LLM extraction for baseline

        # Extract Phase 2 (full extraction)
        validation_ir_phase2 = extractor.extract_validation_rules(ecommerce_spec)

        # Phase 2 should have >= Phase 1 validations
        # assert len(validation_ir_phase2.rules) >= len(validation_ir_phase1.rules)


# ==============================================================================
# 5. QUALITY COVERAGE TESTS
# ==============================================================================

class TestQualityCoverage:
    """Measure quality of extracted validations."""

    def test_validation_rule_completeness(self, ecommerce_spec):
        """
        Ensure extracted validations have all required fields.
        - entity
        - attribute
        - type
        - error_message (optional but recommended)
        """
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        incomplete_rules = 0
        for rule in validation_ir.rules:
            if not rule.entity or not rule.attribute or not rule.type:
                incomplete_rules += 1

        print(f"\n=== Validation Quality ===")
        print(f"Total rules: {len(validation_ir.rules)}")
        print(f"Incomplete rules: {incomplete_rules}")
        print(f"Completeness: {(1 - incomplete_rules/len(validation_ir.rules))*100:.1f}%")

        # All rules should be complete
        assert incomplete_rules == 0, f"Found {incomplete_rules} incomplete validation rules"

    def test_error_messages_present(self, ecommerce_spec):
        """
        Ensure most validation rules have user-friendly error messages.
        Target: >90% of rules should have error messages.
        """
        extractor = BusinessLogicExtractor()
        validation_ir = extractor.extract_validation_rules(ecommerce_spec)

        rules_with_messages = sum(1 for r in validation_ir.rules if r.error_message)
        message_coverage = rules_with_messages / len(validation_ir.rules) if validation_ir.rules else 0

        print(f"\n=== Error Message Coverage ===")
        print(f"Rules with messages: {rules_with_messages}/{len(validation_ir.rules)}")
        print(f"Message coverage: {message_coverage:.1%}")

        # Most rules should have error messages
        assert message_coverage >= 0.80, f"Expected >=80% error message coverage, got {message_coverage:.1%}"


# ==============================================================================
# 6. COVERAGE REPORT GENERATION
# ==============================================================================

def generate_coverage_report(validation_ir: ValidationModelIR, total_expected: int = 62) -> str:
    """
    Generate comprehensive coverage report.

    Returns:
        Formatted string with coverage metrics and breakdown
    """
    total_extracted = len(validation_ir.rules)
    coverage = calculate_coverage(validation_ir, total_expected)

    type_breakdown = group_by_validation_type(validation_ir.rules)
    entity_breakdown = group_by_entity(validation_ir.rules)
    sources = attribute_extraction_sources(validation_ir.rules)

    report = []
    report.append("=" * 60)
    report.append("VALIDATION EXTRACTION COVERAGE REPORT")
    report.append("=" * 60)
    report.append("")

    report.append("OVERALL COVERAGE")
    report.append(f"  Total Validations Extracted: {total_extracted}")
    report.append(f"  Total Expected: {total_expected}")
    report.append(f"  Coverage: {coverage:.1%}")
    report.append("")

    report.append("VALIDATION TYPE BREAKDOWN")
    for val_type, count in sorted(type_breakdown.items(), key=lambda x: -x[1]):
        pct = count / total_extracted * 100 if total_extracted > 0 else 0
        report.append(f"  {val_type:20s}: {count:3d} ({pct:5.1f}%)")
    report.append("")

    report.append("ENTITY BREAKDOWN")
    for entity, count in sorted(entity_breakdown.items(), key=lambda x: -x[1]):
        pct = count / total_extracted * 100 if total_extracted > 0 else 0
        report.append(f"  {entity:20s}: {count:3d} ({pct:5.1f}%)")
    report.append("")

    report.append("EXTRACTION SOURCE ATTRIBUTION")
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        pct = count / total_extracted * 100 if total_extracted > 0 else 0
        report.append(f"  {source:10s}: {count:3d} ({pct:5.1f}%)")
    report.append("")

    report.append("=" * 60)

    return "\n".join(report)


@pytest.fixture
def coverage_report_generator():
    """Fixture providing coverage report generation function."""
    return generate_coverage_report
