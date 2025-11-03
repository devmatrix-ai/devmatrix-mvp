#!/usr/bin/env python3
"""
Basic accessibility checks for React components.
Part of DevMatrix Constitution compliance.
"""

import re
import sys
from pathlib import Path

def check_file(filepath: Path) -> list:
    """Check a TSX file for basic accessibility issues."""
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Check for buttons without aria-label
    for i, line in enumerate(lines, 1):
        if '<button' in line or '<Button' in line:
            # Check if it has aria-label or aria-labelledby
            if 'aria-label' not in line and 'aria-labelledby' not in line:
                # Check if it has text content
                if not re.search(r'>\s*\w+', line):
                    issues.append((i, "Button without aria-label or text content"))
        
        # Check for images without alt text
        if '<img' in line and 'alt=' not in line:
            issues.append((i, "Image without alt text"))
        
        # Check for interactive divs without role
        if 'onClick' in line and '<div' in line and 'role=' not in line:
            issues.append((i, "Interactive div without role attribute"))
    
    return issues

def main():
    ui_dir = Path('src/ui/src')
    all_issues = []
    
    for tsx_file in ui_dir.rglob('*.tsx'):
        if '__tests__' in tsx_file.parts:
            continue
        
        issues = check_file(tsx_file)
        if issues:
            all_issues.append((tsx_file, issues))
    
    if all_issues:
        print("Accessibility issues found:")
        for filepath, issues in all_issues:
            print(f"\n  {filepath}:")
            for line, message in issues:
                print(f"    Line {line}: {message}")
        sys.exit(1)
    else:
        print("✓ No basic accessibility issues found")
        sys.exit(0)

if __name__ == '__main__':
    main()

