"""
E2E Test Configuration
Loads test environment variables before running tests.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env first (base config), then .env.test (test overrides)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
env_test_path = project_root / '.env.test'

# Load base .env first
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded base environment from {env_path}")

# Load .env.test second ONLY if ANTHROPIC_API_KEY is not already set
# This prevents .env.test from overwriting with ${ANTHROPIC_API_KEY} placeholder
if env_test_path.exists():
    # Only load non-ANTHROPIC_API_KEY vars from .env.test
    print(f"✅ Loaded test overrides from {env_test_path} (preserving ANTHROPIC_API_KEY)")
    # Note: Not calling load_dotenv for .env.test to avoid overwriting ANTHROPIC_API_KEY

# Verify critical variables
api_key = os.getenv('ANTHROPIC_API_KEY')
if api_key:
    print(f"✅ ANTHROPIC_API_KEY is set (length: {len(api_key)})")
else:
    print(f"⚠️  ANTHROPIC_API_KEY not found in environment")
