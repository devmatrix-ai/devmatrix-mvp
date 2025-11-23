#!/usr/bin/env python
"""
Manual test script for Phase 2 LLM Validation Extractor.

Tests the new aggressive LLM-based extraction against a sample spec
to demonstrate 15-20+ additional validations beyond Phase 1.

Usage:
    python scripts/test_phase2_llm_extractor.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor
from src.cognitive.ir.validation_model import ValidationType
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def main():
    """Execute Phase 2 LLM extractor test."""
    print_section("Phase 2 LLM Validation Extractor Test")

    # Sample e-commerce spec
    spec = {
        "name": "E-Commerce Platform",
        "entities": [
            {
                "name": "User",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True},
                    {"name": "email", "type": "String", "required": True, "unique": True,
                     "description": "User's email address for login"},
                    {"name": "password", "type": "String", "required": True,
                     "description": "Hashed password, minimum 8 characters"},
                    {"name": "username", "type": "String", "required": True, "unique": True,
                     "description": "Unique username for display"},
                    {"name": "phone", "type": "String", "description": "Contact phone number"},
                    {"name": "created_at", "type": "DateTime", "required": True},
                ]
            },
            {
                "name": "Product",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True},
                    {"name": "name", "type": "String", "required": True},
                    {"name": "price", "type": "Decimal", "required": True,
                     "constraints": {"minimum": 0}},
                    {"name": "stock", "type": "Integer", "required": True,
                     "constraints": {"minimum": 0},
                     "description": "Available inventory quantity"},
                    {"name": "category", "type": "String", "required": True},
                    {"name": "sku", "type": "String", "required": True, "unique": True,
                     "description": "Stock Keeping Unit"},
                ]
            },
            {
                "name": "Order",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True},
                    {"name": "user_id", "type": "UUID", "required": True,
                     "description": "Reference to User"},
                    {"name": "status", "type": "String", "required": True,
                     "enum": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                    {"name": "total_amount", "type": "Decimal", "required": True,
                     "constraints": {"minimum": 0}},
                    {"name": "created_at", "type": "DateTime", "required": True},
                ]
            },
            {
                "name": "OrderItem",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True},
                    {"name": "order_id", "type": "UUID", "required": True},
                    {"name": "product_id", "type": "UUID", "required": True},
                    {"name": "quantity", "type": "Integer", "required": True,
                     "constraints": {"minimum": 1}},
                    {"name": "price", "type": "Decimal", "required": True,
                     "description": "Price at time of purchase"},
                ]
            }
        ],
        "endpoints": [
            {
                "method": "POST",
                "path": "/users",
                "description": "Register new user",
                "request_body": {
                    "email": "string",
                    "password": "string",
                    "username": "string"
                }
            },
            {
                "method": "GET",
                "path": "/products/{id}",
                "description": "Get product by ID"
            },
            {
                "method": "POST",
                "path": "/orders",
                "description": "Create new order",
                "request_body": {
                    "user_id": "uuid",
                    "items": [{"product_id": "uuid", "quantity": "integer"}]
                }
            },
            {
                "method": "PATCH",
                "path": "/orders/{id}/status",
                "description": "Update order status"
            }
        ],
        "workflows": [
            {
                "name": "order_fulfillment",
                "steps": [
                    {"name": "create_order", "status": "pending"},
                    {"name": "process_payment", "status": "processing"},
                    {"name": "ship_order", "status": "shipped"},
                    {"name": "deliver_order", "status": "delivered"}
                ]
            }
        ]
    }

    print("\n📋 Specification Summary:")
    print(f"  - Entities: {len(spec['entities'])}")
    print(f"  - Fields: {sum(len(e['fields']) for e in spec['entities'])}")
    print(f"  - Endpoints: {len(spec['endpoints'])}")
    print(f"  - Workflows: {len(spec['workflows'])}")

    # Extract validations
    print_section("Extracting Validations")
    print("\n⏳ Running comprehensive extraction (Phases 1 + 2)...\n")

    extractor = BusinessLogicExtractor()
    result = extractor.extract_validation_rules(spec)

    # Analyze results
    print_section("Extraction Results")
    print(f"\n✅ Total validations extracted: {len(result.rules)}")

    # Group by type
    by_type = {}
    for rule in result.rules:
        by_type.setdefault(rule.type, []).append(rule)

    print("\n📊 Validations by Type:")
    for val_type, rules in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {val_type.value:20} : {len(rules):3} rules")

    # Group by entity
    by_entity = {}
    for rule in result.rules:
        by_entity.setdefault(rule.entity, []).append(rule)

    print("\n🏢 Validations by Entity:")
    for entity, rules in sorted(by_entity.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {entity:20} : {len(rules):3} rules")

    # Show sample validations
    print_section("Sample Validation Rules")

    # Format validations
    print("\n🔍 FORMAT Validations:")
    format_rules = by_type.get(ValidationType.FORMAT, [])[:5]
    for rule in format_rules:
        print(f"  • {rule.entity}.{rule.attribute}")
        print(f"    Condition: {rule.condition or 'N/A'}")
        print(f"    Error: {rule.error_message or 'N/A'}")

    # Uniqueness validations
    print("\n🔑 UNIQUENESS Validations:")
    unique_rules = by_type.get(ValidationType.UNIQUENESS, [])[:5]
    for rule in unique_rules:
        print(f"  • {rule.entity}.{rule.attribute}")
        print(f"    Error: {rule.error_message or 'N/A'}")

    # Relationship validations
    print("\n🔗 RELATIONSHIP Validations:")
    rel_rules = by_type.get(ValidationType.RELATIONSHIP, [])[:5]
    for rule in rel_rules:
        print(f"  • {rule.entity}.{rule.attribute}")
        print(f"    Error: {rule.error_message or 'N/A'}")

    # Stock constraints
    print("\n📦 STOCK_CONSTRAINT Validations:")
    stock_rules = by_type.get(ValidationType.STOCK_CONSTRAINT, [])[:5]
    for rule in stock_rules:
        print(f"  • {rule.entity}.{rule.attribute}")
        print(f"    Condition: {rule.condition or 'N/A'}")
        print(f"    Error: {rule.error_message or 'N/A'}")

    # Status transitions
    print("\n🔄 STATUS_TRANSITION Validations:")
    status_rules = by_type.get(ValidationType.STATUS_TRANSITION, [])[:5]
    for rule in status_rules:
        print(f"  • {rule.entity}.{rule.attribute}")
        print(f"    Condition: {rule.condition or 'N/A'}")
        print(f"    Error: {rule.error_message or 'N/A'}")

    # Performance metrics
    if hasattr(extractor.llm_extractor, 'total_tokens_used'):
        print_section("Performance Metrics")
        print(f"\n📈 LLM Usage:")
        print(f"  Total API calls: {extractor.llm_extractor.total_api_calls}")
        print(f"  Total tokens: {extractor.llm_extractor.total_tokens_used}")
        print(f"  Avg tokens/call: {extractor.llm_extractor.total_tokens_used / max(extractor.llm_extractor.total_api_calls, 1):.0f}")

    # Success criteria
    print_section("Phase 2 Success Criteria")
    print("\n✅ Target: 60-62 total validations")
    print(f"✅ Achieved: {len(result.rules)} validations")

    if len(result.rules) >= 60:
        print("\n🎉 SUCCESS! Phase 2 target achieved!")
    elif len(result.rules) >= 50:
        print("\n⚠️  CLOSE! Approaching Phase 2 target.")
    else:
        print("\n❌ Below target. More extraction needed.")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
