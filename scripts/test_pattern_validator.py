#!/usr/bin/env python3
"""
Test script for PatternBasedValidator.

Validates that the pattern-based validator extracts comprehensive validation rules
from a sample specification with +30-40% coverage improvement.

Author: DevMatrix Team
Date: 2025-11-23
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.pattern_validator import PatternBasedValidator
from src.cognitive.ir.domain_model import Entity, Attribute, DataType, Relationship, RelationshipType
from src.cognitive.ir.api_model import Endpoint, HttpMethod, APIParameter, ParameterLocation
from src.cognitive.ir.validation_model import ValidationType


def create_test_specification():
    """Create a test specification with e-commerce entities."""

    # Product entity
    product = Entity(
        name="Product",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
            Attribute(name="sku", data_type=DataType.STRING, is_unique=True, is_nullable=False),
            Attribute(name="name", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="description", data_type=DataType.STRING, is_nullable=True),
            Attribute(name="price", data_type=DataType.FLOAT, is_nullable=False),
            Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
            Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
            Attribute(name="updated_at", data_type=DataType.DATETIME, is_nullable=False),
            Attribute(name="is_active", data_type=DataType.BOOLEAN, is_nullable=False),
        ],
        is_aggregate_root=True
    )

    # User entity
    user = Entity(
        name="User",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
            Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False),
            Attribute(name="password", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="phone", data_type=DataType.STRING, is_nullable=True),
            Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
            Attribute(name="updated_at", data_type=DataType.DATETIME, is_nullable=False),
        ],
        is_aggregate_root=True
    )

    # Order entity
    order = Entity(
        name="Order",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
            Attribute(name="user_id", data_type=DataType.UUID, is_nullable=False),
            Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
            Attribute(name="total_amount", data_type=DataType.FLOAT, is_nullable=False),
            Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
            Attribute(name="updated_at", data_type=DataType.DATETIME, is_nullable=False),
        ],
        is_aggregate_root=True
    )

    # OrderItem entity
    order_item = Entity(
        name="OrderItem",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
            Attribute(name="order_id", data_type=DataType.UUID, is_nullable=False),
            Attribute(name="product_id", data_type=DataType.UUID, is_nullable=False),
            Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
            Attribute(name="unit_price", data_type=DataType.FLOAT, is_nullable=False),
        ]
    )

    entities = [product, user, order, order_item]

    # Create test endpoints
    endpoints = [
        Endpoint(
            path="/api/v1/products",
            method=HttpMethod.POST,
            operation_id="create_product",
            summary="Create a new product"
        ),
        Endpoint(
            path="/api/v1/products/{id}",
            method=HttpMethod.GET,
            operation_id="get_product",
            summary="Get product by ID",
            parameters=[
                APIParameter(name="id", location=ParameterLocation.PATH, data_type="UUID")
            ]
        ),
        Endpoint(
            path="/api/v1/products/{id}",
            method=HttpMethod.PUT,
            operation_id="update_product",
            summary="Update product",
            parameters=[
                APIParameter(name="id", location=ParameterLocation.PATH, data_type="UUID")
            ]
        ),
        Endpoint(
            path="/api/v1/products/{id}",
            method=HttpMethod.DELETE,
            operation_id="delete_product",
            summary="Delete product",
            parameters=[
                APIParameter(name="id", location=ParameterLocation.PATH, data_type="UUID")
            ]
        ),
        Endpoint(
            path="/api/v1/orders",
            method=HttpMethod.POST,
            operation_id="create_order",
            summary="Create a new order"
        ),
    ]

    return entities, endpoints


def print_validation_summary(rules):
    """Print a summary of extracted validation rules."""
    print(f"\n{'='*80}")
    print(f"VALIDATION RULES SUMMARY")
    print(f"{'='*80}")
    print(f"Total rules extracted: {len(rules)}\n")

    # Group by entity
    by_entity = {}
    for rule in rules:
        if rule.entity not in by_entity:
            by_entity[rule.entity] = []
        by_entity[rule.entity].append(rule)

    for entity, entity_rules in sorted(by_entity.items()):
        print(f"\n{entity}:")
        print(f"  Rules: {len(entity_rules)}")

        # Group by type
        by_type = {}
        for rule in entity_rules:
            type_name = rule.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(rule)

        for vtype, vrules in sorted(by_type.items()):
            print(f"    {vtype.upper()}: {len(vrules)}")
            for rule in vrules[:3]:  # Show first 3
                print(f"      - {rule.attribute}: {rule.error_message}")
            if len(vrules) > 3:
                print(f"      ... and {len(vrules) - 3} more")

    print(f"\n{'='*80}")
    print("VALIDATION BY TYPE")
    print(f"{'='*80}")

    type_counts = {}
    for rule in rules:
        type_name = rule.type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    for vtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {vtype.upper()}: {count}")


def main():
    """Run pattern validator test."""
    print("PatternBasedValidator Test")
    print("="*80)

    # Create test specification
    print("\nCreating test specification...")
    entities, endpoints = create_test_specification()
    print(f"  Entities: {len(entities)} ({', '.join(e.name for e in entities)})")
    print(f"  Endpoints: {len(endpoints)}")

    # Count total fields
    total_fields = sum(len(e.attributes) for e in entities)
    print(f"  Total fields: {total_fields}")

    # Initialize validator
    print("\nInitializing PatternBasedValidator...")
    validator = PatternBasedValidator()

    # Extract patterns
    print("\nExtracting validation patterns...")
    rules = validator.extract_patterns(entities, endpoints)

    # Print summary
    print_validation_summary(rules)

    # Calculate coverage improvement
    baseline = 22  # Baseline from requirements
    improvement = len(rules) - baseline
    improvement_pct = (improvement / baseline) * 100 if baseline > 0 else 0

    print(f"\n{'='*80}")
    print("COVERAGE ANALYSIS")
    print(f"{'='*80}")
    print(f"  Baseline validations: {baseline}")
    print(f"  Pattern-extracted validations: {len(rules)}")
    print(f"  Improvement: +{improvement} validations ({improvement_pct:.1f}%)")

    target_min = 45
    target_max = 50
    if len(rules) >= target_min:
        print(f"  ✓ Target achieved: {len(rules)} >= {target_min}")
    else:
        print(f"  ✗ Target not met: {len(rules)} < {target_min} (need {target_min - len(rules)} more)")

    # Detailed breakdown
    print(f"\n{'='*80}")
    print("PATTERN SOURCE BREAKDOWN")
    print(f"{'='*80}")

    # Create validator with detailed logging to see pattern sources
    validator_detailed = PatternBasedValidator()

    # Extract with individual pattern methods to see breakdown
    type_matches = validator_detailed._extract_type_patterns(entities)
    semantic_matches = validator_detailed._extract_semantic_patterns(entities)
    constraint_matches = validator_detailed._extract_constraint_patterns(entities)
    endpoint_matches = validator_detailed._extract_endpoint_patterns(endpoints)
    domain_matches = validator_detailed._extract_domain_patterns(entities)
    implicit_matches = validator_detailed._extract_implicit_patterns(entities)

    print(f"  Type patterns: {len(type_matches)} matches")
    print(f"  Semantic patterns: {len(semantic_matches)} matches")
    print(f"  Constraint patterns: {len(constraint_matches)} matches")
    print(f"  Endpoint patterns: {len(endpoint_matches)} matches")
    print(f"  Domain patterns: {len(domain_matches)} matches")
    print(f"  Implicit patterns: {len(implicit_matches)} matches")
    print(f"  Total before dedup: {len(type_matches) + len(semantic_matches) + len(constraint_matches) + len(endpoint_matches) + len(domain_matches) + len(implicit_matches)}")
    print(f"  After deduplication: {len(rules)}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    return 0 if len(rules) >= target_min else 1


if __name__ == "__main__":
    sys.exit(main())
