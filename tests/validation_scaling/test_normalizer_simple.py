"""
Simple test to debug LLM normalizer
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.llm_spec_normalizer import LLMSpecNormalizer

# Simple test spec
SIMPLE_SPEC = """
# Simple API

## Entities

1. **User**
   - id (UUID, primary key)
   - email (string, required, unique)
   - name (string, required)

2. **Product**
   - id (UUID, primary key)
   - name (string, required)
   - price (decimal, required, > 0)

## Relationships

- User → Product (one-to-many, user_id foreign key)

## Endpoints

- POST /api/users - Create user
- GET /api/products - List products
"""

print("Testing LLM Normalizer with simple spec...\n")

normalizer = LLMSpecNormalizer()
try:
    result = normalizer.normalize(SIMPLE_SPEC)
    print("✅ Success!\n")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"❌ Failed: {e}\n")
    import traceback
    traceback.print_exc()
