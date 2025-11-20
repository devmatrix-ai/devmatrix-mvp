#!/usr/bin/env python3
"""
Fix Timezone-Aware Datetimes

Automatically replaces naive datetime.utcnow() with timezone-aware datetime.now(timezone.utc)
across the codebase.

Task Group 5: Security Hardening - Task 5.6

OWASP: A04:2021 Insecure Design

Usage:
    python scripts/fix_timezone_aware_datetimes.py --dry-run  # Preview changes
    python scripts/fix_timezone_aware_datetimes.py            # Apply changes
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Set
import argparse


def find_python_files_with_datetime() -> List[Path]:
    """Find all Python files that use datetime."""
    root = Path("src")
    files = []

    for py_file in root.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "datetime" in content:
                files.append(py_file)
        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}")

    return files


def has_timezone_import(content: str) -> bool:
    """Check if file already imports timezone."""
    return "from datetime import" in content and "timezone" in content


def add_timezone_import(content: str) -> Tuple[str, bool]:
    """
    Add timezone to datetime imports.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    # Pattern 1: from datetime import datetime
    pattern1 = r"from datetime import datetime\b"
    match1 = re.search(pattern1, content)

    if match1 and "timezone" not in content:
        # Add timezone to existing import
        new_import = "from datetime import datetime, timezone"
        content = re.sub(pattern1, new_import, content, count=1)
        return content, True

    # Pattern 2: from datetime import datetime, timedelta
    pattern2 = r"from datetime import ([^\n]+)"
    match2 = re.search(pattern2, content)

    if match2 and "timezone" not in match2.group(1):
        existing_imports = match2.group(1)
        new_imports = existing_imports + ", timezone"
        content = content.replace(
            f"from datetime import {existing_imports}",
            f"from datetime import {new_imports}",
            1
        )
        return content, True

    return content, False


def fix_utcnow_calls(content: str) -> Tuple[str, int]:
    """
    Replace datetime.utcnow() with datetime.now(timezone.utc).

    Returns:
        Tuple of (updated_content, number_of_replacements)
    """
    replacements = 0

    # Pattern 1: datetime.utcnow()
    pattern1 = r"datetime\.utcnow\(\)"
    matches1 = list(re.finditer(pattern1, content))
    for _ in matches1:
        content = re.sub(pattern1, "datetime.now(timezone.utc)", content, count=1)
        replacements += 1

    # Pattern 2: default_factory=datetime.utcnow
    pattern2 = r"default_factory=datetime\.utcnow"
    matches2 = list(re.finditer(pattern2, content))
    for _ in matches2:
        content = re.sub(
            pattern2,
            "default_factory=lambda: datetime.now(timezone.utc)",
            content,
            count=1
        )
        replacements += 1

    # Pattern 3: field(default_factory=datetime.utcnow)
    pattern3 = r"field\(default_factory=datetime\.utcnow\)"
    matches3 = list(re.finditer(pattern3, content))
    for _ in matches3:
        content = re.sub(
            pattern3,
            "field(default_factory=lambda: datetime.now(timezone.utc))",
            content,
            count=1
        )
        replacements += 1

    return content, replacements


def fix_datetime_columns(content: str) -> Tuple[str, int]:
    """
    Fix SQLAlchemy DateTime columns to be timezone-aware.

    Returns:
        Tuple of (updated_content, number_of_replacements)
    """
    replacements = 0

    # Pattern: DateTime() without timezone=True
    pattern = r"DateTime\(\)"
    matches = list(re.finditer(pattern, content))

    for _ in matches:
        content = re.sub(pattern, "DateTime(timezone=True)", content, count=1)
        replacements += 1

    return content, replacements


def verify_no_naive_datetimes(content: str) -> List[str]:
    """
    Verify that no naive datetimes remain.

    Returns:
        List of issues found
    """
    issues = []

    # Check for datetime.utcnow()
    if re.search(r"datetime\.utcnow\(\)", content):
        issues.append("Found datetime.utcnow() - should use datetime.now(timezone.utc)")

    # Check for default_factory=datetime.utcnow (without lambda)
    if re.search(r"default_factory=datetime\.utcnow\b", content):
        issues.append("Found default_factory=datetime.utcnow - should use lambda")

    # Check for DateTime() without timezone parameter
    if re.search(r"DateTime\(\)", content):
        issues.append("Found DateTime() - should use DateTime(timezone=True)")

    return issues


def process_file(file_path: Path, dry_run: bool = False) -> Tuple[int, int, int]:
    """
    Process a single file to fix timezone-aware datetimes.

    Returns:
        Tuple of (utcnow_replacements, column_replacements, import_added)
    """
    print(f"\nProcessing: {file_path}")

    content = file_path.read_text()
    original_content = content

    utcnow_replacements = 0
    column_replacements = 0
    import_added = 0

    # Fix datetime.utcnow() calls
    content, utcnow_count = fix_utcnow_calls(content)
    utcnow_replacements = utcnow_count

    # Fix SQLAlchemy DateTime columns
    content, column_count = fix_datetime_columns(content)
    column_replacements = column_count

    # Add timezone import if needed
    if utcnow_replacements > 0 or column_replacements > 0:
        if not has_timezone_import(content):
            content, added = add_timezone_import(content)
            if added:
                import_added = 1
                print("  + Added timezone import")

    # Verify no issues remain
    issues = verify_no_naive_datetimes(content)
    if issues:
        print("  ⚠️  Remaining issues:")
        for issue in issues:
            print(f"    - {issue}")

    # Report changes
    if utcnow_replacements > 0:
        print(f"  ✓ Fixed {utcnow_replacements} datetime.utcnow() call(s)")

    if column_replacements > 0:
        print(f"  ✓ Fixed {column_replacements} DateTime column(s)")

    # Write changes
    if content != original_content:
        if not dry_run:
            file_path.write_text(content)
            print("  ✓ File updated")
        else:
            print("  ℹ Dry run - no changes written")

    return utcnow_replacements, column_replacements, import_added


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Fix timezone-aware datetimes across codebase"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Timezone-Aware Datetime Fixer")
    print("Task Group 5: Security Hardening - Task 5.6")
    print("OWASP: A04:2021 Insecure Design")
    print("=" * 70)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")

    # Find all Python files with datetime
    files = find_python_files_with_datetime()
    print(f"\nFound {len(files)} files with datetime usage")

    # Process each file
    total_utcnow = 0
    total_columns = 0
    total_imports = 0
    modified_files = 0

    for file_path in files:
        try:
            utcnow, columns, imports = process_file(file_path, dry_run=args.dry_run)

            if utcnow > 0 or columns > 0 or imports > 0:
                modified_files += 1
                total_utcnow += utcnow
                total_columns += columns
                total_imports += imports

        except Exception as e:
            print(f"  ❌ Error processing file: {e}")
            continue

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files scanned:          {len(files)}")
    print(f"Files modified:         {modified_files}")
    print(f"datetime.utcnow() fixed: {total_utcnow}")
    print(f"DateTime columns fixed:  {total_columns}")
    print(f"Timezone imports added:  {total_imports}")

    if args.dry_run:
        print("\n✓ Dry run complete - re-run without --dry-run to apply changes")
    else:
        print("\n✓ Timezone-aware datetimes fixed successfully!")

    print("\nWhat was fixed:")
    print("  • datetime.utcnow() → datetime.now(timezone.utc)")
    print("  • default_factory=datetime.utcnow → lambda: datetime.now(timezone.utc)")
    print("  • DateTime() → DateTime(timezone=True)")

    print("\nNext steps:")
    print("1. Run tests: pytest tests/")
    print("2. Verify database migrations work correctly")
    print("3. Check for any timezone-related test failures")
    print("4. Commit: git commit -m 'security: Fix timezone-aware datetimes (OWASP A04:2021)'")


if __name__ == "__main__":
    main()
