import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add src to path
sys.path.append(os.getcwd())

from src.parsing.spec_parser import SpecParser
from src.validation.compliance_validator import ComplianceValidator

def debug():
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_simple.md")
    app_path = Path("tests/e2e/generated_apps/ecommerce_api_simple_1763806274")

    print(f"Parsing spec: {spec_path}")
    parser = SpecParser()
    spec = parser.parse(spec_path)

    print(f"Validating app: {app_path}")
    validator = ComplianceValidator()
    report = validator.validate_from_app(spec, app_path)

    print("\n" + "="*50)
    print(f"Overall Compliance: {report.overall_compliance:.1%}")
    print(f"Validations: {report.compliance_details['validations']:.1%} ({len(report.validations_implemented)}/{len(report.validations_expected)})")
    print("="*50)

    print("\nMissing Validations:")
    implemented_set = set(report.validations_implemented)
    for v in sorted(report.validations_expected):
        if v not in implemented_set:
            print(f"  [MISSING] {v}")

    print("\nExtra Validations (Found but not Explicitly Expected):")
    expected_set = set(report.validations_expected)
    for v in sorted(report.validations_implemented):
        if v not in expected_set:
            print(f"  [EXTRA] {v}")

    print("\n--- Normalization Test ---")
    test_cases = ["> 0", ">= 0", "email format", "enum=OPEN,CHECKED_OUT"]
    for t in test_cases:
        norm = validator._normalize_constraint(t)
        print(f"'{t}' -> '{norm}'")

if __name__ == "__main__":
    debug()
