#!/usr/bin/env python3
"""
Validate Deterministic LLM Configuration

This script validates that all LLM temperature settings across the codebase
have been properly set to 0.0 for deterministic mode.

Part of Fase 1 Quick Wins - Deterministic Architecture Implementation
Expected impact: 38% → 65% precision improvement

Usage:
    python scripts/validate_deterministic_setup.py

Returns:
    Exit code 0: All validations passed
    Exit code 1: Validation failures detected
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def validate_no_non_zero_temperatures():
    """Validate that no temperature values > 0 exist in the codebase."""
    print("🔍 Checking for non-zero temperature values...")

    errors = []

    # Search for temperature assignments in Python files
    returncode, stdout, stderr = run_command([
        "grep", "-rn",
        "--include=*.py",
        r"temperature\s*=\s*0\.[1-9]",
        "src/"
    ])

    # grep returns 1 when no matches found (which is what we want)
    if returncode == 0:
        lines = stdout.strip().split('\n')
        for line in lines:
            if line and "# Deterministic mode" not in line:
                errors.append(f"Found non-zero temperature: {line}")

    # Also check for temperature = 1.0 or temperature = 0.X where X > 0
    returncode, stdout, stderr = run_command([
        "grep", "-rn",
        "--include=*.py",
        r"temperature\s*=\s*[1-9]",
        "src/"
    ])

    if returncode == 0:
        lines = stdout.strip().split('\n')
        for line in lines:
            if line and "# Deterministic mode" not in line:
                errors.append(f"Found non-zero temperature: {line}")

    if errors:
        print("❌ Non-zero temperature values found:")
        for error in errors:
            print(f"  {error}")
        return False

    print("✅ No non-zero temperature values found")
    return True


def validate_llm_config_exists():
    """Validate that LLMConfig module exists and is properly configured."""
    print("\n🔍 Validating LLMConfig module...")

    config_path = Path("src/config/llm_config.py")
    if not config_path.exists():
        print("❌ src/config/llm_config.py not found")
        return False

    try:
        # Import the module
        sys.path.insert(0, str(Path.cwd()))
        from src.config.llm_config import LLMConfig

        # Validate constants
        errors = []

        if LLMConfig.DEFAULT_TEMPERATURE != 0.0:
            errors.append(f"DEFAULT_TEMPERATURE is {LLMConfig.DEFAULT_TEMPERATURE}, expected 0.0")

        if LLMConfig.DEFAULT_SEED != 42:
            errors.append(f"DEFAULT_SEED is {LLMConfig.DEFAULT_SEED}, expected 42")

        if not LLMConfig.DETERMINISTIC_MODE:
            errors.append("DETERMINISTIC_MODE is False, expected True")

        # Validate methods exist
        if not hasattr(LLMConfig, 'get_deterministic_params'):
            errors.append("Missing method: get_deterministic_params()")

        if not hasattr(LLMConfig, 'validate_determinism'):
            errors.append("Missing method: validate_determinism()")

        # Test get_deterministic_params
        params = LLMConfig.get_deterministic_params()
        if params['temperature'] != 0.0:
            errors.append(f"get_deterministic_params() returns temperature={params['temperature']}, expected 0.0")

        if params['seed'] != 42:
            errors.append(f"get_deterministic_params() returns seed={params['seed']}, expected 42")

        if errors:
            print("❌ LLMConfig validation failed:")
            for error in errors:
                print(f"  {error}")
            return False

        print("✅ LLMConfig module validated successfully")
        return True

    except ImportError as e:
        print(f"❌ Failed to import LLMConfig: {e}")
        return False
    except Exception as e:
        print(f"❌ LLMConfig validation error: {e}")
        return False


def validate_constants_default_temp():
    """Validate that DEFAULT_TEMPERATURE in constants.py is 0.0."""
    print("\n🔍 Validating DEFAULT_TEMPERATURE in constants.py...")

    try:
        from src.config.constants import DEFAULT_TEMPERATURE

        if DEFAULT_TEMPERATURE != 0.0:
            print(f"❌ constants.DEFAULT_TEMPERATURE is {DEFAULT_TEMPERATURE}, expected 0.0")
            return False

        print("✅ constants.DEFAULT_TEMPERATURE is 0.0")
        return True

    except ImportError as e:
        print(f"❌ Failed to import constants: {e}")
        return False


def validate_tolerance_removed():
    """Validate that 15% tolerance has been removed from masterplan_generator."""
    print("\n🔍 Validating task count tolerance removal...")

    # Check specifically for the tolerance validation logic
    returncode, stdout, stderr = run_command([
        "grep", "-n",
        "deviation > 0.15",
        "src/services/masterplan_generator.py"
    ])

    # grep returns 1 when no matches (which is what we want)
    if returncode == 0:
        print("❌ Found 15% tolerance validation (deviation > 0.15) still in masterplan_generator.py:")
        print(stdout)
        return False

    # Verify exact match logic exists
    returncode, stdout, stderr = run_command([
        "grep", "-n",
        "total_tasks != calculated_task_count",
        "src/services/masterplan_generator.py"
    ])

    if returncode != 0:
        print("❌ Exact match validation (!=) not found in masterplan_generator.py")
        return False

    print("✅ Task count tolerance removed, exact match validation present")
    return True


def validate_retry_orchestrators():
    """Validate that both retry orchestrators use temperature 0.0."""
    print("\n🔍 Validating retry orchestrators...")

    errors = []

    # Check src/execution/retry_orchestrator.py
    returncode, stdout, stderr = run_command([
        "grep", "-A", "5",
        "TEMPERATURE_SCHEDULE",
        "src/execution/retry_orchestrator.py"
    ])

    if returncode == 0:
        if "0.7" in stdout or "0.5" in stdout or "0.3" in stdout:
            errors.append("src/execution/retry_orchestrator.py still has non-zero temperatures")

    # Check src/mge/v2/execution/retry_orchestrator.py
    returncode, stdout, stderr = run_command([
        "grep", "-A", "2",
        "TEMPERATURE_SCHEDULE",
        "src/mge/v2/execution/retry_orchestrator.py"
    ])

    if returncode == 0:
        if "0.7" in stdout or "0.5" in stdout or "0.3" in stdout:
            errors.append("src/mge/v2/execution/retry_orchestrator.py still has non-zero temperatures")

    if errors:
        print("❌ Retry orchestrator validation failed:")
        for error in errors:
            print(f"  {error}")
        return False

    print("✅ Both retry orchestrators use temperature 0.0")
    return True


def main():
    """Run all validations."""
    print("=" * 70)
    print("🔬 DETERMINISTIC LLM CONFIGURATION VALIDATION")
    print("=" * 70)

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    all_passed = True

    # Run validations
    validations = [
        validate_no_non_zero_temperatures,
        validate_llm_config_exists,
        validate_constants_default_temp,
        validate_tolerance_removed,
        validate_retry_orchestrators,
    ]

    for validation in validations:
        if not validation():
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 70)
        print("\n🎯 Deterministic architecture successfully implemented!")
        print("📊 Expected precision improvement: 38% → 65%")
        print("\nNext steps:")
        print("  1. Run integration tests to verify behavior")
        print("  2. Measure new baseline precision with measure_precision_baseline.py")
        print("  3. Commit changes with: git commit -m 'feat: Implement deterministic LLM configuration (Fase 1 Quick Wins)'")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("=" * 70)
        print("\n⚠️  Some validations failed. Please fix the issues above and re-run.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
