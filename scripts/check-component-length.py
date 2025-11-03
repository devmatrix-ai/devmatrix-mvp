#!/usr/bin/env python3
"""
Check that React components are ≤300 lines.
Part of DevMatrix Constitution compliance.
"""

import sys
from pathlib import Path
import argparse

def check_component(filepath: Path, max_lines: int) -> dict:
    """Check component length."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Count non-empty, non-comment lines
    code_lines = [
        line for line in lines 
        if line.strip() and not line.strip().startswith('//')
    ]
    
    length = len(code_lines)
    
    if length > max_lines:
        return {
            'file': filepath,
            'length': length,
            'max': max_lines
        }
    
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-lines', type=int, default=300)
    args = parser.parse_args()
    
    ui_dir = Path('src/ui/src')
    if not ui_dir.exists():
        print("UI directory not found", file=sys.stderr)
        sys.exit(0)
    
    issues = []
    
    for tsx_file in ui_dir.rglob('*.tsx'):
        if '__tests__' in tsx_file.parts:
            continue
        
        issue = check_component(tsx_file, args.max_lines)
        if issue:
            issues.append(issue)
    
    if issues:
        print(f"Found {len(issues)} components exceeding {args.max_lines} lines:")
        print()
        for issue in issues:
            print(f"  {issue['file']}")
            print(f"    {issue['length']} lines (max: {issue['max']})")
        sys.exit(1)
    else:
        print(f"✓ All components are ≤{args.max_lines} lines")
        sys.exit(0)

if __name__ == '__main__':
    main()

