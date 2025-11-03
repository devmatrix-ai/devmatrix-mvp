#!/usr/bin/env python3
"""
Check that Python files have proper type hints.
Part of DevMatrix Constitution compliance.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

def check_function_has_type_hints(node: ast.FunctionDef) -> bool:
    """Check if a function has type hints on parameters and return."""
    # Skip private functions and test functions
    if node.name.startswith('_') or node.name.startswith('test_'):
        return True
    
    # Check if it's a method with only 'self' or 'cls'
    if len(node.args.args) <= 1 and node.args.args and \
       node.args.args[0].arg in ('self', 'cls'):
        return True
    
    # Check return type
    if node.returns is None and node.name != '__init__':
        return False
    
    # Check parameter types (skip self/cls)
    for arg in node.args.args:
        if arg.arg in ('self', 'cls'):
            continue
        if arg.annotation is None:
            return False
    
    return True

def check_file(filepath: Path) -> List[Tuple[int, str]]:
    """Check a Python file for type hint compliance."""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not check_function_has_type_hints(node):
                    issues.append((
                        node.lineno,
                        f"Function '{node.name}' missing type hints"
                    ))
    except SyntaxError as e:
        issues.append((0, f"Syntax error: {e}"))
    
    return issues

def main():
    src_dir = Path('src')
    if not src_dir.exists():
        print("ERROR: src/ directory not found", file=sys.stderr)
        sys.exit(1)
    
    all_issues = []
    checked_files = 0
    
    for py_file in src_dir.rglob('*.py'):
        # Skip __pycache__, tests, migrations
        if '__pycache__' in py_file.parts or \
           'test_' in py_file.name or \
           'alembic/versions' in str(py_file):
            continue
        
        issues = check_file(py_file)
        if issues:
            all_issues.append((py_file, issues))
        checked_files += 1
    
    if all_issues:
        print(f"Type hint issues found in {len(all_issues)} files:")
        print()
        for filepath, issues in all_issues:
            print(f"  {filepath}:")
            for line, message in issues:
                print(f"    Line {line}: {message}")
        print()
        print(f"Checked {checked_files} files, found issues in {len(all_issues)}")
        sys.exit(1)
    else:
        print(f"✓ All {checked_files} Python files have proper type hints")
        sys.exit(0)

if __name__ == '__main__':
    main()

