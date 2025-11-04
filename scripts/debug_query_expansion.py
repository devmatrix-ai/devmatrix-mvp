#!/usr/bin/env python3
"""Debug script to see what query variants are being generated."""

import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.query_expander import QueryExpander
from src.observability import get_logger

logger = get_logger(__name__)

# Test queries
TEST_QUERIES = [
    "Express.js server setup with routing",
    "React hooks and functional components",
    "TypeScript type definitions and interfaces",
    "JavaScript async/await patterns",
    "REST API error handling",
    "React state management with hooks",
    "Node.js middleware implementation",
    "Async Express middleware patterns",
]

expander = QueryExpander()

print("=" * 70)
print("QUERY EXPANSION DEBUG")
print("=" * 70)

for query in TEST_QUERIES:
    variants = expander.expand_query(query, max_variants=5)
    print(f"\nOriginal: {query}")
    for i, variant in enumerate(variants, 1):
        if i == 1:
            print(f"  [1] {variant} (original)")
        else:
            print(f"  [{i}] {variant}")

print("\n" + "=" * 70)
