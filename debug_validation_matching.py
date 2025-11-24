#!/usr/bin/env python3
"""
Debug script to understand why validation matching is at 83.3% instead of 100%
"""
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, '/home/kwar/code/agentic-ai')

from src.validation.compliance_validator import ComplianceValidator
from src.spec.spec_parser import SpecParser

def main():
    # Paths
    spec_path = Path('tests/e2e/test_specs/ecommerce-api-spec-human.md')
    app_path = Path('tests/e2e/generated_apps/ecommerce-api-spec-human_1763977479')
    
    # Parse spec to get expected validations
    print("=== PARSING SPEC ===")
    parser = SpecParser()
    spec_req = parser.parse_spec(spec_path)
    
    # Get validator
    validator = ComplianceValidator()
    
    # Validate
    print("\n=== RUNNING VALIDATION ===")
    report = validator.validate_from_directory(app_path, spec_req)
    
    print(f"\n=== RESULTS ===")
    print(f"Overall Compliance: {report.overall_compliance:.1%}")
    print(f"Validations: {report.compliance_details.get('validations', 0):.1%}")
    print(f"  Expected: {len(report.validations_expected)}")
    print(f"  Found: {len(report.validations_found)}")
    print(f"  Implemented (matched): {len(report.validations_implemented)}")
    
    # Show first 10 expected validations
    print(f"\n=== EXPECTED VALIDATIONS (first 10) ===")
    for i, val in enumerate(report.validations_expected[:10], 1):
        print(f"{i}. {val}")
    
    # Show first 10 found validations
    print(f"\n=== FOUND VALIDATIONS (first 10) ===")
    for i, val in enumerate(report.validations_found[:10], 1):
        print(f"{i}. {val}")
    
    # Show first 10 implemented (matched) validations
    print(f"\n=== IMPLEMENTED/MATCHED VALIDATIONS (first 10) ===")
    for i, val in enumerate(report.validations_implemented[:10], 1):
        print(f"{i}. {val}")
    
    # Find missing validations (expected but not implemented)
    missing = set(report.validations_expected) - set(report.validations_implemented)
    print(f"\n=== MISSING VALIDATIONS ({len(missing)}) ===")
    for i, val in enumerate(sorted(missing)[:15], 1):
        print(f"{i}. {val}")

if __name__ == '__main__':
    main()
