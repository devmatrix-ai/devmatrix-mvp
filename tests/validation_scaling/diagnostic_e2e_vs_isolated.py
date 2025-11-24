"""
Diagnostic Script: Compare E2E vs Isolated Test Validation Extraction

This script compares why isolated test gets 94/62 but E2E gets 44/62.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor

try:
    from tests.cognitive.ir.spec_parser import SpecParser
except ImportError:
    SpecParser = None


# Isolated test spec (from test_all_phases.py)
ISOLATED_SPEC = {
    "entities": [
        {
            "name": "User",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "email", "type": "string", "unique": True, "required": True},
                {"name": "username", "type": "string", "unique": True, "required": True},
                {"name": "password_hash", "type": "string", "required": True},
                {"name": "created_at", "type": "datetime"},
                {"name": "updated_at", "type": "datetime"}
            ]
        },
        {
            "name": "Product",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "price", "type": "decimal", "minimum": 0, "required": True},
                {"name": "stock", "type": "integer", "minimum": 0, "required": True},
                {"name": "status", "type": "string", "allowed_values": ["active", "inactive", "discontinued"]},
                {"name": "created_at", "type": "datetime"}
            ]
        },
        {
            "name": "Order",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "user_id", "type": "UUID", "required": True},
                {"name": "status", "type": "string", "allowed_values": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                {"name": "total_amount", "type": "decimal", "minimum": 0},
                {"name": "created_at", "type": "datetime"},
                {"name": "updated_at", "type": "datetime"}
            ]
        },
        {
            "name": "OrderItem",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "order_id", "type": "UUID", "required": True},
                {"name": "product_id", "type": "UUID", "required": True},
                {"name": "quantity", "type": "integer", "minimum": 1, "required": True},
                {"name": "unit_price", "type": "decimal", "minimum": 0, "required": True}
            ]
        }
    ],
    "relationships": [
        {
            "from": "User",
            "to": "Order",
            "type": "one-to-many",
            "foreign_key": "user_id",
            "required": True,
            "cascade_delete": True
        },
        {
            "from": "Order",
            "to": "OrderItem",
            "type": "one-to-many",
            "foreign_key": "order_id",
            "required": True,
            "cascade_delete": True
        },
        {
            "from": "Product",
            "to": "OrderItem",
            "type": "one-to-many",
            "foreign_key": "product_id",
            "required": True
        }
    ],
    "endpoints": [
        {"method": "POST", "path": "/api/users", "name": "Create User", "parameters": ["email", "username", "password"]},
        {"method": "GET", "path": "/api/users/{id}", "name": "Get User"},
        {"method": "POST", "path": "/api/orders", "name": "Create Order", "parameters": ["user_id", "items"]},
        {"method": "GET", "path": "/api/orders/{id}", "name": "Get Order"},
        {"method": "PUT", "path": "/api/orders/{id}", "name": "Update Order Status", "parameters": ["status"]}
    ]
}


def analyze_spec(spec, spec_name):
    """Analyze and extract validations from a spec"""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {spec_name}")
    print(f"{'='*80}\n")

    # Count spec structure
    entity_count = len(spec.get("entities", []))
    total_fields = sum(len(e.get("fields", [])) for e in spec.get("entities", []))
    relationship_count = len(spec.get("relationships", []))
    endpoint_count = len(spec.get("endpoints", []))

    print(f"Spec Structure:")
    print(f"  Entities: {entity_count}")
    print(f"  Total Fields: {total_fields}")
    print(f"  Relationships: {relationship_count}")
    print(f"  Endpoints: {endpoint_count}\n")

    # Extract validations
    extractor = BusinessLogicExtractor()
    try:
        validations = extractor.extract_validations(spec)
        print(f"Validations Extracted: {len(validations)}\n")

        # Group by type
        by_type = {}
        for v in validations:
            v_type = str(v.type)
            by_type[v_type] = by_type.get(v_type, 0) + 1

        print(f"Breakdown by Type:")
        for v_type, count in sorted(by_type.items()):
            pct = (count / len(validations) * 100) if validations else 0
            print(f"  {v_type:25} {count:3} ({pct:5.1f}%)")

        # Group by entity
        by_entity = {}
        for v in validations:
            entity = v.entity
            by_entity[entity] = by_entity.get(entity, 0) + 1

        print(f"\nBreakdown by Entity:")
        for entity, count in sorted(by_entity.items()):
            pct = (count / len(validations) * 100) if validations else 0
            print(f"  {entity:25} {count:3} ({pct:5.1f}%)")

        # List all validations
        print(f"\nDetailed Validations:")
        for v in sorted(validations, key=lambda x: (x.entity, x.attribute or "")):
            attr = v.attribute or "(no attr)"
            print(f"  {v.entity:15} {attr:20} {v.type:20}")

        return validations

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def compare_results(isolated, e2e_spec_path):
    """Compare isolated test vs E2E"""
    print("\n" + "="*80)
    print("COMPARISON: Isolated Test vs E2E Real")
    print("="*80 + "\n")

    # Extract isolated
    isolated_vals = analyze_spec(ISOLATED_SPEC, "ISOLATED TEST (Perfect Format)")

    # Try to extract from E2E spec if provided
    if e2e_spec_path and Path(e2e_spec_path).exists() and SpecParser:
        print(f"\nLoading E2E spec from: {e2e_spec_path}")
        spec_parser = SpecParser()
        spec_req = spec_parser.parse_from_file(e2e_spec_path)

        # Convert to dict format
        e2e_spec_dict = {
            "entities": [
                {
                    "name": e.name,
                    "fields": [
                        {
                            "name": attr.name,
                            "type": attr.type,
                            "required": getattr(attr, 'required', False),
                            "unique": getattr(attr, 'unique', False),
                            "is_primary_key": getattr(attr, 'is_primary_key', False),
                            "minimum": getattr(attr, 'minimum', None),
                            "maximum": getattr(attr, 'maximum', None),
                            "min_length": getattr(attr, 'min_length', None),
                            "max_length": getattr(attr, 'max_length', None),
                            "allowed_values": getattr(attr, 'allowed_values', None)
                        }
                        for attr in (e.attributes if hasattr(e, 'attributes') else [])
                    ]
                }
                for e in spec_req.entities
            ],
            "relationships": [
                {
                    "from": getattr(r, 'from_entity', ''),
                    "to": getattr(r, 'to_entity', ''),
                    "type": getattr(r, 'relationship_type', 'one-to-many'),
                    "foreign_key": getattr(r, 'foreign_key', None),
                    "required": getattr(r, 'required', False),
                    "cascade_delete": getattr(r, 'cascade_delete', False)
                }
                for r in (spec_req.relationships if hasattr(spec_req, 'relationships') else [])
            ],
            "endpoints": [
                {"method": ep.method, "path": ep.path}
                for ep in spec_req.endpoints
            ]
        }

        e2e_vals = analyze_spec(e2e_spec_dict, "E2E REAL (From ecommerce_api_simple.md)")
    else:
        print(f"\nE2E spec not found at {e2e_spec_path}")
        e2e_vals = []

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80 + "\n")
    print(f"Isolated Test:  {len(isolated_vals)}/62 ({len(isolated_vals)/62*100:.1f}%)")
    print(f"E2E Real:       {len(e2e_vals)}/62 ({len(e2e_vals)/62*100:.1f}%)")
    print(f"Difference:     {abs(len(isolated_vals) - len(e2e_vals))} validations")

    if len(isolated_vals) > len(e2e_vals):
        print(f"\n⚠️  E2E is missing {len(isolated_vals) - len(e2e_vals)} validations from isolated test")
        print("Likely causes:")
        print("  1. E2E spec has fewer fields/attributes")
        print("  2. E2E spec missing constraint metadata")
        print("  3. E2E spec has different entity structure")


if __name__ == "__main__":
    e2e_spec_path = "tests/e2e/test_specs/ecommerce_api_simple.md"
    compare_results(ISOLATED_SPEC, e2e_spec_path)
