#!/usr/bin/env python3
"""
Check that functions/methods are ≤100 lines.
Part of DevMatrix Constitution compliance.
"""

import ast
import sys
from pathlib import Path
import argparse

def check_file(filepath: Path, max_lines: int) -> list:
    """Check function lengths in a Python file."""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(filepath))
        
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate function length
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                func_length = end_line - start_line + 1
                
                if func_length > max_lines:
                    issues.append({
                        'file': filepath,
                        'function': node.name,
                        'line': start_line,
                        'length': func_length,
                        'max': max_lines
                    })
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
    
    return issues

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-lines', type=int, default=100)
    args = parser.parse_args()
    
    src_dir = Path('src')
    all_issues = []
    
    for py_file in src_dir.rglob('*.py'):
        if '__pycache__' in py_file.parts or 'test_' in py_file.name:
            continue
        
        issues = check_file(py_file, args.max_lines)
        all_issues.extend(issues)
    
    if all_issues:
        print(f"Found {len(all_issues)} functions exceeding {args.max_lines} lines:")
        print()
        for issue in all_issues:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Function '{issue['function']}' is {issue['length']} lines (max: {issue['max']})")
        sys.exit(1)
    else:
        print(f"✓ All functions are ≤{args.max_lines} lines")
        sys.exit(0)

if __name__ == '__main__':
    main()

