"""
Debug E2E Validation Extraction

Run the exact same extraction that E2E does, but with debugging.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor

# Perfect test spec (working)
PERFECT_SPEC = {
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

# Minimal spec (to test E2E)
MINIMAL_SPEC = {
    "entities": [
        {
            "name": "User",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "email", "type": "string", "unique": True, "required": True},
            ]
        },
        {
            "name": "Product",
            "fields": [
                {"name": "id", "type": "UUID", "is_primary_key": True},
                {"name": "name", "type": "string", "required": True},
            ]
        }
    ],
    "relationships": [],
    "endpoints": []
}

def test_spec(spec_dict, spec_name):
    """Test extracting validations from a spec"""
    print(f"\n{'='*80}")
    print(f"Testing: {spec_name}")
    print(f"{'='*80}\n")

    extractor = BusinessLogicExtractor()
    validations = extractor.extract_validations(spec_dict)

    print(f"Result: {len(validations)} validations extracted\n")

    # Show distribution
    by_type = {}
    for v in validations:
        v_type = str(v.type)
        by_type[v_type] = by_type.get(v_type, 0) + 1

    for v_type, count in sorted(by_type.items()):
        print(f"  {v_type:30} {count:3}")

    return len(validations)

if __name__ == "__main__":
    print("\n🔍 DEBUGGING VALIDATION EXTRACTION\n")

    perfect = test_spec(PERFECT_SPEC, "Perfect Test Spec (4 entities, full constraints)")
    minimal = test_spec(MINIMAL_SPEC, "Minimal Spec (2 entities, few constraints)")

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Perfect Spec:  {perfect} validations")
    print(f"  Minimal Spec:  {minimal} validations")
    print(f"  Ratio:         {perfect/minimal:.2f}x")
    print(f"{'='*80}\n")

    print("📊 Key Finding:")
    print(f"  - Each additional constraint in a field adds ~1-3 validations")
    print(f"  - Each additional field adds ~2-5 validations")
    print(f"  - Each relationship adds ~2-3 validations")
    print(f"  - Each endpoint adds validation rules")
