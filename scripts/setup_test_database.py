#!/usr/bin/env python3
"""
Setup test database with proper schema and extensions.

Creates devmatrix_test database with pgvector extension and required tables.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load test environment
load_dotenv('.env.test')


def setup_test_db():
    """Setup test database with schema and extensions."""

    # Connect to postgres (default database)
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            user=os.getenv('POSTGRES_USER', 'devmatrix'),
            password=os.getenv('POSTGRES_PASSWORD', 'devmatrix'),
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Drop and recreate test database
        db_name = os.getenv('POSTGRES_DB', 'devmatrix_test')

        print(f"🗄️  Dropping database {db_name} if exists...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")

        print(f"🗄️  Creating database {db_name}...")
        cursor.execute(f"CREATE DATABASE {db_name}")

        cursor.close()
        conn.close()
        print(f"✅ Database {db_name} created")

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

    # Connect to test database and install extensions
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            user=os.getenv('POSTGRES_USER', 'devmatrix'),
            password=os.getenv('POSTGRES_PASSWORD', 'devmatrix'),
            database=db_name
        )
        cursor = conn.cursor()

        print("📦 Installing pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ pgvector extension installed")

        print("📋 Creating schema...")

        # Code generation logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_generation_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                workspace_id VARCHAR(255),
                user_request TEXT,
                generated_code TEXT,
                approval_status VARCHAR(50),
                quality_score FLOAT,
                git_committed BOOLEAN DEFAULT FALSE,
                git_commit_hash VARCHAR(40),
                metadata JSONB
            )
        """)
        print("✅ code_generation_logs table created")

        # Agent execution logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_execution_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                agent_name VARCHAR(100),
                task_id VARCHAR(100),
                task_type VARCHAR(50),
                status VARCHAR(50),
                duration_ms INTEGER,
                error TEXT,
                metadata JSONB
            )
        """)
        print("✅ agent_execution_logs table created")

        # Workflow logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                workflow_id VARCHAR(100),
                workspace_id VARCHAR(255),
                user_request TEXT,
                status VARCHAR(50),
                total_tasks INTEGER,
                completed_tasks INTEGER,
                failed_tasks INTEGER,
                duration_ms INTEGER,
                metadata JSONB
            )
        """)
        print("✅ workflow_logs table created")

        # RAG feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_feedback (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                query TEXT,
                retrieved_code TEXT,
                feedback_type VARCHAR(50),
                rating INTEGER,
                metadata JSONB
            )
        """)
        print("✅ rag_feedback table created")

        # Create indexes for performance
        print("📊 Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_gen_workspace
            ON code_generation_logs(workspace_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_gen_timestamp
            ON code_generation_logs(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_exec_timestamp
            ON agent_execution_logs(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_timestamp
            ON workflow_logs(timestamp DESC)
        """)
        print("✅ Indexes created")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✨ Test database {db_name} is ready!")
        print(f"   📊 Tables: code_generation_logs, agent_execution_logs, workflow_logs, rag_feedback")
        print(f"   🔌 Extensions: pgvector")
        print(f"   🔗 Connection: postgresql://{os.getenv('POSTGRES_USER')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{db_name}")

        return True

    except Exception as e:
        print(f"❌ Error setting up schema: {e}")
        return False


if __name__ == "__main__":
    success = setup_test_db()
    sys.exit(0 if success else 1)
