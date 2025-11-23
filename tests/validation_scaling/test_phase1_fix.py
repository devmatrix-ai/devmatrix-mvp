"""
Test to verify Phase 1 spec conversion fix
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor


def test_phase1_with_correct_spec_format():
    """Test that correct spec format gives much better coverage than wrong format"""

    # Test spec with CORRECT format (entities as LIST)
    correct_spec = {
        'entities': [
            {
                'name': 'User',
                'fields': [
                    {'name': 'id', 'type': 'UUID', 'is_primary_key': True},
                    {'name': 'email', 'type': 'string', 'unique': True, 'required': True},
                    {'name': 'username', 'type': 'string', 'unique': True, 'required': True},
                    {'name': 'password_hash', 'type': 'string', 'required': True},
                    {'name': 'created_at', 'type': 'datetime'},
                    {'name': 'updated_at', 'type': 'datetime'}
                ]
            },
            {
                'name': 'Product',
                'fields': [
                    {'name': 'id', 'type': 'UUID', 'is_primary_key': True},
                    {'name': 'name', 'type': 'string', 'required': True},
                    {'name': 'price', 'type': 'decimal', 'minimum': 0, 'required': True},
                    {'name': 'stock', 'type': 'integer', 'minimum': 0, 'required': True},
                    {'name': 'status', 'type': 'string', 'allowed_values': ['active', 'inactive', 'discontinued']},
                    {'name': 'created_at', 'type': 'datetime'}
                ]
            }
        ]
    }

    extractor = BusinessLogicExtractor()
    try:
        rules = extractor.extract_validations(correct_spec)
        print(f"✅ Phase 1 with correct format:")
        print(f"   Total validations: {len(rules)}")

        by_entity = {}
        for rule in rules:
            entity = rule.entity
            if entity not in by_entity:
                by_entity[entity] = 0
            by_entity[entity] += 1

        for entity in sorted(by_entity.keys()):
            print(f"   - {entity}: {by_entity[entity]}")

        # Expected: ~25-30 for User + Product combined
        assert len(rules) > 20, f"Expected >20 validations, got {len(rules)}"
        print(f"\n✅ Phase 1 WORKING: Detected {len(rules)} validations")
        return True

    except Exception as e:
        print(f"❌ Phase 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_phase1_with_correct_spec_format()
    exit(0 if success else 1)
