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
    Bug #169 Fix: Add explicit flush + verification to ensure data persists.
    """
    from src.core.database import _get_session_maker
    from sqlalchemy import text

    logger.info("🌱 Seeding test data...")

    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
            # Seed Product for smoke testing with predictable UUID
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
            await session.merge(test_product)
            logger.info("✅ Created/updated test Product with ID 00000000-0000-4000-8000-000000000001")
            # Seed Product for DELETE tests with predictable UUID
            from src.models.entities import ProductEntity
            from uuid import UUID
            test_product_for_delete = ProductEntity(
                id=UUID("00000000-0000-4000-8000-000000000011"),
                name="Test Product (Delete)",
                description="Test description for Product",
                price=99.99,
                stock=100,
                is_active=True
            )
            await session.merge(test_product_for_delete)
            logger.info("✅ Created/updated test Product with ID 00000000-0000-4000-8000-000000000011")
            # Seed Customer for smoke testing with predictable UUID
            from src.models.entities import CustomerEntity
            from uuid import UUID
            test_customer = CustomerEntity(
                id=UUID("00000000-0000-4000-8000-000000000002"),
                email="test@example.com",
                full_name="Test Customer"
            )
            await session.merge(test_customer)
            logger.info("✅ Created/updated test Customer with ID 00000000-0000-4000-8000-000000000002")
            # Seed Customer for DELETE tests with predictable UUID
            from src.models.entities import CustomerEntity
            from uuid import UUID
            test_customer_for_delete = CustomerEntity(
                id=UUID("00000000-0000-4000-8000-000000000012"),
                email="test_delete@example.com",
                full_name="Test Customer (Delete)"
            )
            await session.merge(test_customer_for_delete)
            logger.info("✅ Created/updated test Customer with ID 00000000-0000-4000-8000-000000000012")
            # Seed Cart for smoke testing with predictable UUID
            from src.models.entities import CartEntity
            from uuid import UUID
            test_cart = CartEntity(
                id=UUID("00000000-0000-4000-8000-000000000003"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                status="OPEN"
            )
            await session.merge(test_cart)
            logger.info("✅ Created/updated test Cart with ID 00000000-0000-4000-8000-000000000003")
            # Seed Cart for DELETE tests with predictable UUID
            from src.models.entities import CartEntity
            from uuid import UUID
            test_cart_for_delete = CartEntity(
                id=UUID("00000000-0000-4000-8000-000000000013"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                status="OPEN"
            )
            await session.merge(test_cart_for_delete)
            logger.info("✅ Created/updated test Cart with ID 00000000-0000-4000-8000-000000000013")
            # Seed Order for smoke testing with predictable UUID
            from src.models.entities import OrderEntity
            from uuid import UUID
            test_order = OrderEntity(
                id=UUID("00000000-0000-4000-8000-000000000005"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                order_status="PENDING_PAYMENT",
                payment_status="PENDING",
                total_amount=99.99
            )
            await session.merge(test_order)
            logger.info("✅ Created/updated test Order with ID 00000000-0000-4000-8000-000000000005")
            # Seed Order for DELETE tests with predictable UUID
            from src.models.entities import OrderEntity
            from uuid import UUID
            test_order_for_delete = OrderEntity(
                id=UUID("00000000-0000-4000-8000-000000000015"),
                customer_id=UUID("00000000-0000-4000-8000-000000000002"),
                order_status="PENDING_PAYMENT",
                payment_status="PENDING",
                total_amount=99.99
            )
            await session.merge(test_order_for_delete)
            logger.info("✅ Created/updated test Order with ID 00000000-0000-4000-8000-000000000015")
            # Seed CartItem for smoke testing
            from src.models.entities import CartItemEntity
            from uuid import UUID
            from decimal import Decimal
            test_cartitem = CartItemEntity(
                id=UUID("00000000-0000-4000-8000-000000000020"),
                cart_id=UUID("00000000-0000-4000-8000-000000000003"),
                product_id=UUID("00000000-0000-4000-8000-000000000001"),
                quantity=2,
                unit_price=Decimal("19.99")
            )
            await session.merge(test_cartitem)
            logger.info("✅ Created/updated test CartItem with ID 00000000-0000-4000-8000-000000000020")
            # Seed CartItem for DELETE tests
            from src.models.entities import CartItemEntity
            from uuid import UUID
            from decimal import Decimal
            test_cartitem_for_delete = CartItemEntity(
                id=UUID("00000000-0000-4000-8000-000000000021"),
                cart_id=UUID("00000000-0000-4000-8000-000000000013"),
                product_id=UUID("00000000-0000-4000-8000-000000000001"),
                quantity=2,
                unit_price=Decimal("19.99")
            )
            await session.merge(test_cartitem_for_delete)
            logger.info("✅ Created/updated test CartItem with ID 00000000-0000-4000-8000-000000000021")
            # Seed OrderItem for smoke testing
            from src.models.entities import OrderItemEntity
            from uuid import UUID
            from decimal import Decimal
            test_orderitem = OrderItemEntity(
                id=UUID("00000000-0000-4000-8000-000000000022"),
                order_id=UUID("00000000-0000-4000-8000-000000000005"),
                product_id=UUID("00000000-0000-4000-8000-000000000001"),
                quantity=2,
                unit_price=Decimal("19.99")
            )
            await session.merge(test_orderitem)
            logger.info("✅ Created/updated test OrderItem with ID 00000000-0000-4000-8000-000000000022")
            # Seed OrderItem for DELETE tests
            from src.models.entities import OrderItemEntity
            from uuid import UUID
            from decimal import Decimal
            test_orderitem_for_delete = OrderItemEntity(
                id=UUID("00000000-0000-4000-8000-000000000023"),
                order_id=UUID("00000000-0000-4000-8000-000000000015"),
                product_id=UUID("00000000-0000-4000-8000-000000000001"),
                quantity=2,
                unit_price=Decimal("19.99")
            )
            await session.merge(test_orderitem_for_delete)
            logger.info("✅ Created/updated test OrderItem with ID 00000000-0000-4000-8000-000000000023")
            # Bug #169 Fix: Explicit flush before commit to ensure writes
            await session.flush()
            await session.commit()
            logger.info("✅ Test data seeded successfully")

            # Bug #169 Fix: Verify data was actually persisted
            # Use a new session to confirm data is in DB
            async with session_maker() as verify_session:
                result = await verify_session.execute(
                    text("SELECT COUNT(*) FROM products WHERE id = '00000000-0000-4000-8000-000000000001'")
                )
                count = result.scalar()
                if count == 0:
                    logger.error("❌ CRITICAL: Seed data verification failed - data not in DB!")
                    raise RuntimeError("Seed data verification failed")
                logger.info(f"✅ Verified: {count} seed record(s) in database")
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