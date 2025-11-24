"""
Audit: What does the spec parser extract from ecommerce_api_simple.md?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cognitive.ir.spec_parser import SpecParser

def audit_parsed_spec():
    """Parse the ecommerce spec and show what was extracted"""

    print("="*80)
    print("SPEC PARSER AUDIT")
    print("="*80 + "\n")

    parser = SpecParser()
    spec_path = "tests/e2e/test_specs/ecommerce_api_simple.md"

    print(f"Parsing: {spec_path}\n")

    spec = parser.parse_from_file(spec_path)

    # Show entities
    print(f"ENTITIES: {len(spec.entities)}")
    print("-" * 80)

    for entity in spec.entities:
        print(f"\n{entity.name}:")
        print(f"  Attributes: {len(entity.attributes)}")
        for attr in entity.attributes:
            print(f"    - {attr.name}: {attr.type}")
            print(f"      required={getattr(attr, 'required', False)}")
            print(f"      unique={getattr(attr, 'unique', False)}")
            print(f"      is_primary_key={getattr(attr, 'is_primary_key', False)}")
            print(f"      minimum={getattr(attr, 'minimum', None)}")
            print(f"      maximum={getattr(attr, 'maximum', None)}")
            print(f"      min_length={getattr(attr, 'min_length', None)}")
            print(f"      max_length={getattr(attr, 'max_length', None)}")
            print(f"      allowed_values={getattr(attr, 'allowed_values', None)}")

    # Show relationships
    print(f"\n\nRELATIONSHIPS: {len(spec.relationships)}")
    print("-" * 80)

    for rel in spec.relationships:
        print(f"\n{rel.from_entity} → {rel.to_entity}")
        print(f"  Type: {rel.relationship_type}")
        print(f"  FK: {rel.foreign_key}")
        print(f"  Required: {rel.required}")
        print(f"  Cascade: {rel.cascade_delete}")

    # Show endpoints
    print(f"\n\nENDPOINTS: {len(spec.endpoints)}")
    print("-" * 80)

    for ep in spec.endpoints:
        print(f"\n{ep.method} {ep.path}")

    # Show business logic
    print(f"\n\nBUSINESS LOGIC: {len(spec.business_logic)}")
    print("-" * 80)

    for bl in spec.business_logic:
        print(f"\n{bl.name}")
        print(f"  {bl.description}")

    # Summary
    total_attrs = sum(len(e.attributes) for e in spec.entities)
    print(f"\n\nSUMMARY")
    print("=" * 80)
    print(f"Entities: {len(spec.entities)}")
    print(f"Total Attributes: {total_attrs}")
    print(f"Relationships: {len(spec.relationships)}")
    print(f"Endpoints: {len(spec.endpoints)}")
    print(f"Business Logic Rules: {len(spec.business_logic)}")

    return spec

if __name__ == "__main__":
    spec = audit_parsed_spec()
