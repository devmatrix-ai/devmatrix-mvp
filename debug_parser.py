#!/usr/bin/env python3
"""Debug tree-sitter parser issue"""

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

try:
    print("1. Loading Python language...")
    # tree-sitter 0.25.2 API: Language(ptr)
    PY_LANGUAGE = Language(tspython.language())
    print(f"   ✓ Language loaded: {type(PY_LANGUAGE)}")

    print("\n2. Creating Parser...")
    parser = Parser(PY_LANGUAGE)
    print(f"   ✓ Parser created: {type(parser)}")

    print("\n3. Parsing simple code...")
    code = "def hello():\n    print('Hello World')"
    tree = parser.parse(bytes(code, "utf8"))
    print(f"   ✓ Tree created: {type(tree)}")

    print("\n4. Checking root node...")
    root = tree.root_node
    print(f"   ✓ Root node: {root.type}")
    print(f"   ✓ Has error: {root.has_error}")
    print(f"   ✓ Text: {code[root.start_byte:root.end_byte]}")

    print("\n✓ SUCCESS - Parser works correctly!")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
