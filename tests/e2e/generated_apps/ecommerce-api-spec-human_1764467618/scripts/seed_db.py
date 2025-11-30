#!/usr/bin/env python3
"""
Database Initialization and Seed Script

Bug #85 Fix: Creates tables and seeds test data for smoke testing.
Run this before starting the app to ensure test resources exist.

Usage:
    python scripts/seed_db.py
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

logger = structlog.get_logger(__name__)


async def init_database():
    """
    Initialize database tables.

    Bug #99 Fix: When called from Docker, Alembic runs first via docker-compose.
    This function is kept for standalone usage but handles "already exists" gracefully.
    """
    from src.core.database import init_db
    logger.info("🔄 Creating database tables (if not exists)...")
    try:
        await init_db()
        logger.info("✅ Database tables created")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("ℹ️ Tables already exist (alembic ran first)")
        else:
            raise


async def seed_test_data():
    """Seed minimal test data for smoke testing.

    Bug #143 Fix: Use direct session creation instead of get_db() generator.
    The generator pattern causes issues when exiting with 'break' - the
    generator cleanup code tries another commit which can trigger rollback.
    """
    from src.core.database import _get_session_maker

    logger.info("🌱 Seeding test data...")

    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
            # Seed Product with predictable UUID for smoke testing
            from src.models.entities import ProductEntity
            from uuid import UUID
            test_product = ProductEntity(
                id=UUID("00000000-0000-4000-8000-000000000001"),
                name="Test Product",
                description="Test description for Product",
                price=99.99,
                stock=100,
                is_active=True
            )
            session.add(test_product)
            logger.info("✅ Created test Product with ID 00000000-0000-4000-8000-000000000001")
            # Seed Customer with predictable UUID for smoke testing
            from src.models.entities import CustomerEntity
            from uuid import UUID
            test_customer = CustomerEntity(
                id=UUID("00000000-0000-4000-8000-000000000002"),
                email="test@example.com",
                full_name="Test Customer"
            )
            session.add(test_customer)
            logger.info("✅ Created test Customer with ID 00000000-0000-4000-8000-000000000002")
            # Seed Cart with predictable UUID for smoke testing
            from src.models.entities import CartEntity
            from uuid import UUID
            test_cart = CartEntity(
                id=UUID("00000000-0000-4000-8000-000000000003"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                status="OPEN"
            )
            session.add(test_cart)
            logger.info("✅ Created test Cart with ID 00000000-0000-4000-8000-000000000003")
            # Seed Order with predictable UUID for smoke testing
            from src.models.entities import OrderEntity
            from uuid import UUID
            test_order = OrderEntity(
                id=UUID("00000000-0000-4000-8000-000000000005"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                order_status="PENDING_PAYMENT",
                payment_status="PENDING",
                total_amount=99.99
            )
            session.add(test_order)
            logger.info("✅ Created test Order with ID 00000000-0000-4000-8000-000000000005")
            await session.commit()
            logger.info("✅ Test data seeded successfully")
        except Exception as e:
            await session.rollback()
            # Ignore duplicate key errors (data already exists)
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.info("ℹ️ Test data already exists, skipping seed")
            else:
                logger.error(f"❌ Failed to seed data: {e}")
                raise


async def main():
    """Initialize database and seed test data."""
    logger.info("🚀 Starting database initialization...")

    try:
        await init_database()
        await seed_test_data()
        logger.info("✅ Database initialization complete!")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())