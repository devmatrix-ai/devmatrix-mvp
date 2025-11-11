"""
E2E Test Configuration
Loads test environment variables before running tests.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test from project root
project_root = Path(__file__).parent.parent.parent
env_test_path = project_root / '.env.test'

if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"✅ Loaded test environment from {env_test_path}")
else:
    print(f"⚠️  .env.test not found at {env_test_path}")
