#!/usr/bin/env python3
"""
Example: Integration of PatternBasedValidator in Code Generation Pipeline.

Shows how to integrate pattern-based validation extraction in the
complete code generation workflow.

Author: DevMatrix Team
Date: 2025-11-23
"""
import sys
from typing import List
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, DataType
from src.cognitive.ir.api_model import APIModelIR, Endpoint, HttpMethod
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule

from src.services.pattern_validator import PatternBasedValidator


def create_sample_application_ir() -> ApplicationIR:
    """
    Create a sample ApplicationIR for demonstration.

    In real usage, this would come from IRBuilder parsing a PRD.
    """
    # Domain Model
    domain_model = DomainModelIR(
        entities=[
            Entity(
                name="Product",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="sku", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                    Attribute(name="name", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="price", data_type=DataType.FLOAT, is_nullable=False),
                    Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
                    Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                    Attribute(name="is_active", data_type=DataType.BOOLEAN, is_nullable=False),
                ],
                is_aggregate_root=True
            ),
            Entity(
                name="User",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                    Attribute(name="password", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                ],
                is_aggregate_root=True
            )
        ]
    )

    # API Model
    api_model = APIModelIR(
        endpoints=[
            Endpoint(path="/api/v1/products", method=HttpMethod.POST, operation_id="create_product"),
            Endpoint(path="/api/v1/products/{id}", method=HttpMethod.GET, operation_id="get_product"),
            Endpoint(path="/api/v1/users", method=HttpMethod.POST, operation_id="create_user"),
        ]
    )

    # Infrastructure Model (minimal)
    from src.cognitive.ir.infrastructure_model import DatabaseConfig, DatabaseType
    infrastructure_model = InfrastructureModelIR(
        database=DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            name="sample_db",
            user="postgres",
            password_env_var="DB_PASSWORD"
        )
    )

    # Create ApplicationIR
    app_ir = ApplicationIR(
        name="SampleECommerceApp",
        description="Sample e-commerce application for pattern validation demo",
        domain_model=domain_model,
        api_model=api_model,
        infrastructure_model=infrastructure_model,
        validation_model=ValidationModelIR()  # Empty initially
    )

    return app_ir


def extract_and_enrich_validations(app_ir: ApplicationIR) -> ApplicationIR:
    """
    Extract pattern-based validations and enrich ApplicationIR.

    This is the key integration step that enhances the IR with
    automatically discovered validation rules.
    """
    print("=" * 80)
    print("PATTERN-BASED VALIDATION EXTRACTION")
    print("=" * 80)

    # Initialize pattern validator
    validator = PatternBasedValidator()
    print(f"\nValidator initialized with patterns from: {validator.patterns_file}")

    # Extract validation rules
    print("\nExtracting patterns from specification...")
    pattern_rules = validator.extract_patterns(
        entities=app_ir.domain_model.entities,
        endpoints=app_ir.api_model.endpoints
    )

    print(f"✓ Extracted {len(pattern_rules)} validation rules")

    # Enrich the ApplicationIR
    app_ir.validation_model.rules.extend(pattern_rules)

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION MODEL ENRICHED")
    print("=" * 80)
    print(f"Total validation rules: {len(app_ir.validation_model.rules)}")

    # Breakdown by type
    by_type = {}
    for rule in app_ir.validation_model.rules:
        vtype = rule.type.value
        by_type[vtype] = by_type.get(vtype, 0) + 1

    print("\nBreakdown by type:")
    for vtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  {vtype.upper()}: {count}")

    # Breakdown by entity
    by_entity = {}
    for rule in app_ir.validation_model.rules:
        entity = rule.entity
        by_entity[entity] = by_entity.get(entity, 0) + 1

    print("\nBreakdown by entity:")
    for entity, count in sorted(by_entity.items()):
        print(f"  {entity}: {count} rules")

    return app_ir


def generate_validation_summary(rules: List[ValidationRule]) -> str:
    """
    Generate a human-readable validation summary.

    This could be used in generated documentation or README files.
    """
    summary = []
    summary.append("# Validation Rules Summary\n")

    # Group by entity
    by_entity = {}
    for rule in rules:
        if rule.entity not in by_entity:
            by_entity[rule.entity] = []
        by_entity[rule.entity].append(rule)

    for entity, entity_rules in sorted(by_entity.items()):
        summary.append(f"\n## {entity}\n")
        for rule in entity_rules:
            summary.append(
                f"- **{rule.attribute}** ({rule.type.value}): {rule.error_message}\n"
            )

    return "".join(summary)


def main():
    """Run the integration example."""
    print("\nPatternBasedValidator Integration Example")
    print("=" * 80)

    # Step 1: Create or load ApplicationIR
    print("\nStep 1: Creating ApplicationIR...")
    app_ir = create_sample_application_ir()
    print(f"✓ Created ApplicationIR: {app_ir.name}")
    print(f"  Entities: {len(app_ir.domain_model.entities)}")
    print(f"  Endpoints: {len(app_ir.api_model.endpoints)}")

    # Step 2: Extract and enrich validations
    print("\nStep 2: Extracting validation patterns...")
    app_ir = extract_and_enrich_validations(app_ir)

    # Step 3: Generate documentation
    print("\nStep 3: Generating validation summary...")
    summary = generate_validation_summary(app_ir.validation_model.rules)

    # Save summary to file
    output_path = Path("validation_summary.md")
    with open(output_path, "w") as f:
        f.write(summary)
    print(f"✓ Saved validation summary to: {output_path}")

    # Step 4: Show sample rules
    print("\n" + "=" * 80)
    print("SAMPLE VALIDATION RULES (first 10)")
    print("=" * 80)

    for i, rule in enumerate(app_ir.validation_model.rules[:10], 1):
        print(f"\n{i}. {rule.entity}.{rule.attribute}")
        print(f"   Type: {rule.type.value}")
        print(f"   Message: {rule.error_message}")
        if rule.condition:
            print(f"   Condition: {rule.condition}")

    print("\n" + "=" * 80)
    print("INTEGRATION COMPLETE")
    print("=" * 80)
    print("\nThe ApplicationIR is now enriched with comprehensive validation rules")
    print("and ready for code generation with full validation coverage.\n")

    # Next steps
    print("Next steps:")
    print("  1. Pass app_ir to code generation service")
    print("  2. Generate FastAPI routes with validation decorators")
    print("  3. Generate Pydantic schemas with Field validators")
    print("  4. Generate test cases covering all validation rules")
    print("  5. Generate OpenAPI spec with validation documentation")


if __name__ == "__main__":
    main()
