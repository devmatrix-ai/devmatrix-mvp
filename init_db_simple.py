#!/usr/bin/env python3
"""Initialize database schema from SQLAlchemy models."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.config.database import engine, Base
# Import models to register them
from src.models.masterplan import *
from src.models.auth import *
from src.models.conversation import *

# Create all tables
print("🔨 Creating database schema from SQLAlchemy models...")
Base.metadata.create_all(engine)
print("✅ Database schema created successfully!")

# Verify tables were created
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"\n📊 Created {len(tables)} tables:")
for table in sorted(tables):
    print(f"  - {table}")
