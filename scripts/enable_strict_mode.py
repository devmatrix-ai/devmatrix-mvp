#!/usr/bin/env python3
"""
Enable Pydantic Strict Mode Across All Models

Automatically converts legacy `class Config` to `ConfigDict(strict=True)`
for all Pydantic models in the codebase.

Task Group 5: Security Hardening - Task 5.1

Usage:
    python scripts/enable_strict_mode.py --dry-run  # Preview changes
    python scripts/enable_strict_mode.py            # Apply changes
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import argparse


def find_pydantic_files() -> List[Path]:
    """Find all Python files that use Pydantic BaseModel."""
    root = Path("src")
    files = []

    for py_file in root.rglob("*.py"):
        content = py_file.read_text()
        if "from pydantic import" in content and "BaseModel" in content:
            files.append(py_file)

    return files


def has_config_dict_import(content: str) -> bool:
    """Check if file already imports ConfigDict."""
    return "ConfigDict" in content


def add_config_dict_import(content: str) -> str:
    """Add ConfigDict to pydantic imports."""
    # Find pydantic import line
    import_pattern = r"from pydantic import ([^\n]+)"
    match = re.search(import_pattern, content)

    if not match:
        return content

    current_imports = match.group(1)

    # Check if ConfigDict already imported
    if "ConfigDict" in current_imports:
        return content

    # Add ConfigDict to imports
    new_imports = current_imports.rstrip() + ", ConfigDict"
    content = content.replace(
        f"from pydantic import {current_imports}",
        f"from pydantic import {new_imports}"
    )

    return content


def convert_class_config_to_model_config(content: str) -> Tuple[str, int]:
    """
    Convert legacy `class Config` to `model_config = ConfigDict(strict=True)`.

    Returns:
        Tuple of (updated_content, number_of_conversions)
    """
    conversions = 0

    # Pattern to match:
    # class SomeModel(BaseModel):
    #     ...
    #     class Config:
    #         schema_extra = {...}

    # Find all class definitions
    class_pattern = r"class\s+(\w+)\(BaseModel\):(.*?)(?=\nclass\s|\Z)"
    matches = list(re.finditer(class_pattern, content, re.DOTALL))

    for match in reversed(matches):  # Reverse to maintain positions
        class_name = match.group(1)
        class_body = match.group(2)

        # Check if has class Config
        if "class Config:" not in class_body:
            continue

        # Extract Config content
        config_pattern = r"class Config:(.*?)(?=\n    [a-zA-Z_]|\Z)"
        config_match = re.search(config_pattern, class_body, re.DOTALL)

        if not config_match:
            continue

        config_content = config_match.group(1).strip()

        # Build ConfigDict content
        config_dict_lines = []

        # Check for strict mode (if not present, add it)
        if "strict" not in config_content:
            config_dict_lines.append("strict=True")

        # Extract schema_extra
        schema_extra_pattern = r"schema_extra\s*=\s*(\{[^}]+\})"
        schema_extra_match = re.search(schema_extra_pattern, config_content, re.DOTALL)

        if schema_extra_match:
            schema_extra = schema_extra_match.group(1)
            config_dict_lines.append(f"json_schema_extra={schema_extra}")

        # Extract from_attributes (for ORM models)
        if "from_attributes" in config_content or "orm_mode" in config_content:
            config_dict_lines.append("from_attributes=True")

        # Extract arbitrary_types_allowed
        if "arbitrary_types_allowed" in config_content:
            config_dict_lines.append("arbitrary_types_allowed=True")

        # Build new model_config
        if config_dict_lines:
            config_dict_content = ",\n        ".join(config_dict_lines)
            new_config = f"""    # Task Group 5.1: Enable strict mode to prevent type coercion
    model_config = ConfigDict(
        {config_dict_content}
    )"""
        else:
            new_config = """    # Task Group 5.1: Enable strict mode to prevent type coercion
    model_config = ConfigDict(strict=True)"""

        # Replace class Config with model_config
        old_config = f"class Config:{config_content}"
        class_body = class_body.replace(old_config, new_config)

        # Update full content
        old_class = match.group(0)
        new_class = f"class {class_name}(BaseModel):{class_body}"
        content = content.replace(old_class, new_class)

        conversions += 1

        print(f"  ✓ Converted {class_name}")

    return content, conversions


def process_file(file_path: Path, dry_run: bool = False) -> int:
    """
    Process a single file to enable strict mode.

    Returns:
        Number of conversions made
    """
    print(f"\nProcessing: {file_path}")

    content = file_path.read_text()

    # Add ConfigDict import if needed
    if not has_config_dict_import(content):
        content = add_config_dict_import(content)
        print("  + Added ConfigDict import")

    # Convert class Config to model_config
    updated_content, conversions = convert_class_config_to_model_config(content)

    if conversions > 0:
        print(f"  → {conversions} model(s) converted")

        if not dry_run:
            file_path.write_text(updated_content)
            print("  ✓ File updated")
        else:
            print("  ℹ Dry run - no changes written")

    return conversions


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Enable Pydantic strict mode across all models"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Pydantic Strict Mode Enabler")
    print("Task Group 5: Security Hardening - Task 5.1")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")

    # Find all Pydantic files
    files = find_pydantic_files()
    print(f"\nFound {len(files)} files with Pydantic models")

    # Process each file
    total_conversions = 0
    modified_files = 0

    for file_path in files:
        conversions = process_file(file_path, dry_run=args.dry_run)
        if conversions > 0:
            total_conversions += conversions
            modified_files += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(files)}")
    print(f"Files modified: {modified_files}")
    print(f"Total conversions: {total_conversions}")

    if args.dry_run:
        print("\n✓ Dry run complete - re-run without --dry-run to apply changes")
    else:
        print("\n✓ Strict mode enabled successfully!")

    print("\nNext steps:")
    print("1. Run tests: pytest tests/unit/test_models.py")
    print("2. Verify no breaking changes: pytest")
    print("3. Commit changes: git commit -m 'security: Enable Pydantic strict mode'")


if __name__ == "__main__":
    main()
