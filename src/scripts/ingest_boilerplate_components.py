"""
Ingest Boilerplate Components into Neo4j

This script:
1. Initializes the boilerplate schema
2. Ingests shared components (used by all apps)
3. Ingests app-specific components
4. Creates relationships between components
5. Validates the ingestion
"""

import asyncio
import logging
from typing import Dict, List
from uuid import uuid4

from src.neo4j_client import Neo4jClient
from src.neo4j_schemas.boilerplate_schema import BoilerplateSchema

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =========================================================================
# SHARED COMPONENTS LIBRARY
# =========================================================================

SHARED_COMPONENTS = [
    # =====================================================================
    # AUTHENTICATION & AUTHORIZATION
    # =====================================================================
    {
        "id": "user_entity",
        "name": "User Entity",
        "description": "Core user model with authentication",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "user_management,auth,shared",
        "code": """
class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
""",
    },

    {
        "id": "auth_service",
        "name": "Authentication Service",
        "description": "JWT token management and auth logic",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "medium",
        "purpose": "auth,security,shared",
        "code": """
class AuthService:
    @staticmethod
    def create_access_token(user_id: str) -> str:
        payload = {"sub": user_id, "exp": datetime.utcnow() + timedelta(hours=24)}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> str:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
""",
    },

    {
        "id": "auth_middleware",
        "name": "Authentication Middleware",
        "description": "Request authentication and authorization",
        "category": "Middleware",
        "language": "python",
        "framework": "fastapi",
        "complexity": "simple",
        "purpose": "auth,security,shared",
        "code": """
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        user_id = AuthService.verify_token(token)
    except JWTError:
        raise HTTPException(status_code=401)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user
""",
    },

    # =====================================================================
    # CORE DATA PATTERNS
    # =====================================================================
    {
        "id": "timestamped_base",
        "name": "Timestamped Base Model",
        "description": "Base class with created_at/updated_at",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "simple",
        "purpose": "data_modeling,shared",
        "code": """
class TimestampedModel(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
""",
    },

    {
        "id": "activity_log_entity",
        "name": "Activity Log Entity",
        "description": "Audit trail for all actions",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "audit,logging,shared",
        "code": """
class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    entity_type = Column(String(255))
    entity_id = Column(UUID)
    action = Column(String(50))
    before = Column(JSON)
    after = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
""",
    },

    # =====================================================================
    # CRUD API PATTERN
    # =====================================================================
    {
        "id": "crud_base_service",
        "name": "CRUD Base Service",
        "description": "Generic CRUD operations for any entity",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "medium",
        "purpose": "api,crud,shared",
        "code": """
class CRUDService(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def create(self, obj_in: dict) -> T:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        return db_obj

    async def read(self, id: str) -> Optional[T]:
        return await db.get(self.model, id)

    async def update(self, id: str, obj_in: dict) -> Optional[T]:
        obj = await self.read(id)
        if obj:
            for k, v in obj_in.items():
                setattr(obj, k, v)
            await db.commit()
        return obj

    async def delete(self, id: str) -> bool:
        obj = await self.read(id)
        if obj:
            await db.delete(obj)
            await db.commit()
            return True
        return False
""",
    },

    {
        "id": "pagination_utility",
        "name": "Pagination Utility",
        "description": "Handle pagination for list responses",
        "category": "Utility",
        "language": "python",
        "framework": "fastapi",
        "complexity": "simple",
        "purpose": "api,pagination,shared",
        "code": """
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

async def paginate(query, page: int = 1, page_size: int = 10):
    total = await query.count()
    items = await query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
""",
    },

    # =====================================================================
    # VALIDATION & ERROR HANDLING
    # =====================================================================
    {
        "id": "error_handler_middleware",
        "name": "Error Handler Middleware",
        "description": "Centralized error handling",
        "category": "Middleware",
        "language": "python",
        "framework": "fastapi",
        "complexity": "medium",
        "purpose": "error_handling,shared",
        "code": """
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
""",
    },

    # =====================================================================
    # REAL-TIME UPDATES
    # =====================================================================
    {
        "id": "websocket_manager",
        "name": "WebSocket Manager",
        "description": "Manage WebSocket connections and broadcasting",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "complex",
        "purpose": "realtime,collaboration,shared",
        "code": """
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List] = {}

    async def connect(self, room: str, websocket):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    async def broadcast(self, room: str, message: dict):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                await connection.send_json(message)
""",
    },

    # =====================================================================
    # PERMISSIONS & ACCESS CONTROL
    # =====================================================================
    {
        "id": "permission_checker",
        "name": "Permission Checker",
        "description": "Check resource-level permissions",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "medium",
        "purpose": "security,authorization,shared",
        "code": """
class PermissionChecker:
    @staticmethod
    async def check_resource_access(user_id: str, resource_id: str, model) -> bool:
        resource = await db.get(model, resource_id)
        return resource and resource.user_id == user_id
""",
    },

    # =====================================================================
    # SEARCH & FILTERING
    # =====================================================================
    {
        "id": "search_service",
        "name": "Search Service",
        "description": "Full-text search and filtering",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "complex",
        "purpose": "search,shared",
        "code": """
class SearchService:
    @staticmethod
    async def search(model: Type, query: str, filters: Dict = None) -> List:
        stmt = select(model)
        if query:
            stmt = stmt.where(model.name.ilike(f"%{query}%"))
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(model, key) == value)
        return await db.execute(stmt).scalars().all()
""",
    },

    # =====================================================================
    # NOTIFICATIONS
    # =====================================================================
    {
        "id": "notification_service",
        "name": "Notification Service",
        "description": "Handle in-app and email notifications",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "complex",
        "purpose": "notifications,shared",
        "code": """
class NotificationService:
    @staticmethod
    async def notify(user_id: str, notification_type: str, content: str):
        notification = Notification(user_id=user_id, type=notification_type, content=content)
        db.add(notification)
        await db.commit()
""",
    },
]

# =========================================================================
# TASK MANAGER SPECIFIC COMPONENTS
# =========================================================================

TASK_MANAGER_COMPONENTS = [
    {
        "id": "task_entity",
        "name": "Task Entity",
        "description": "Task model with status and priority",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "task_manager",
        "code": """
class Task(TimestampedModel):
    __tablename__ = "tasks"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    project_id = Column(UUID, ForeignKey("projects.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="todo")
    priority = Column(String(50), default="medium")
    due_date = Column(DateTime)
""",
    },
    {
        "id": "task_service",
        "name": "Task Service",
        "description": "Task business logic",
        "category": "Service",
        "language": "python",
        "framework": "fastapi",
        "complexity": "medium",
        "purpose": "task_manager",
        "code": """
class TaskService(CRUDService[Task]):
    async def get_user_tasks(self, user_id: str):
        return await db.query(Task).filter(Task.user_id == user_id).all()

    async def update_status(self, task_id: str, status: str):
        task = await self.read(task_id)
        task.status = status
        await db.commit()
        return task
""",
    },
]

# =========================================================================
# CRM SPECIFIC COMPONENTS
# =========================================================================

CRM_COMPONENTS = [
    {
        "id": "contact_entity",
        "name": "Contact Entity",
        "description": "Customer contact model",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "crm",
        "code": """
class Contact(TimestampedModel):
    __tablename__ = "contacts"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    company = Column(String(255))
    lead_source = Column(String(100))
""",
    },
    {
        "id": "deal_entity",
        "name": "Deal Entity",
        "description": "Sales opportunity model",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "crm",
        "code": """
class Deal(TimestampedModel):
    __tablename__ = "deals"
    id = Column(UUID, primary_key=True, default=uuid4)
    contact_id = Column(UUID, ForeignKey("contacts.id"))
    name = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2))
    stage = Column(String(50))
    probability = Column(Float)
    close_date = Column(DateTime)
""",
    },
]

# =========================================================================
# E-COMMERCE SPECIFIC COMPONENTS
# =========================================================================

ECOMMERCE_COMPONENTS = [
    {
        "id": "product_entity",
        "name": "Product Entity",
        "description": "Product catalog model",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "ecommerce",
        "code": """
class Product(TimestampedModel):
    __tablename__ = "products"
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100))
    inventory = Column(Integer, default=0)
    sku = Column(String(100), unique=True)
""",
    },
    {
        "id": "order_entity",
        "name": "Order Entity",
        "description": "Customer purchase order",
        "category": "Entity",
        "language": "python",
        "framework": "sqlalchemy",
        "complexity": "medium",
        "purpose": "ecommerce",
        "code": """
class Order(TimestampedModel):
    __tablename__ = "orders"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    total_amount = Column(Numeric(10, 2))
    status = Column(String(50))
    shipping_address = Column(JSON)
""",
    },
]

# =========================================================================
# COMPONENT DEPENDENCY RELATIONSHIPS
# =========================================================================

COMPONENT_DEPENDENCIES = [
    # Task Manager dependencies
    {"source_id": "task_service", "target_id": "task_entity", "type": "USES"},
    {"source_id": "task_service", "target_id": "crud_base_service", "type": "EXTENDS"},
    {"source_id": "task_entity", "target_id": "timestamped_base", "type": "EXTENDS"},

    # CRM dependencies
    {"source_id": "deal_entity", "target_id": "timestamped_base", "type": "EXTENDS"},
    {"source_id": "contact_entity", "target_id": "timestamped_base", "type": "EXTENDS"},

    # E-commerce dependencies
    {"source_id": "product_entity", "target_id": "timestamped_base", "type": "EXTENDS"},
    {"source_id": "order_entity", "target_id": "timestamped_base", "type": "EXTENDS"},

    # Shared dependencies
    {"source_id": "auth_service", "target_id": "user_entity", "type": "USES"},
    {"source_id": "auth_middleware", "target_id": "auth_service", "type": "USES"},
    {"source_id": "crud_base_service", "target_id": "pagination_utility", "type": "USES"},
    {"source_id": "crud_base_service", "target_id": "activity_log_entity", "type": "USES"},
    {"source_id": "search_service", "target_id": "crud_base_service", "type": "EXTENDS"},
]


# =========================================================================
# INGESTION FUNCTIONS
# =========================================================================

async def init_schema(client: Neo4jClient) -> bool:
    """Initialize Neo4j schema (constraints and indexes)"""
    logger.info("🔧 Initializing Neo4j schema...")

    try:
        async with client.driver.session() as session:
            for query in BoilerplateSchema.SETUP_QUERIES:
                await session.run(query)

        logger.info("✅ Schema initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {e}")
        return False


async def ingest_components(client: Neo4jClient, components: List[Dict], app_type: str = "shared") -> int:
    """Ingest components into Neo4j"""
    if not components:
        return 0

    logger.info(f"📦 Ingesting {len(components)} {app_type} components...")

    try:
        async with client.driver.session() as session:
            result = await session.run(
                BoilerplateSchema.batch_create_components(),
                components=components
            )
            record = await result.single()
            created = record["created"] if record else 0

        logger.info(f"✅ Created {created} {app_type} components")
        return created
    except Exception as e:
        logger.error(f"❌ Component ingestion failed: {e}")
        return 0


async def create_dependencies(client: Neo4jClient) -> int:
    """Create relationships between components"""
    logger.info("🔗 Creating component dependencies...")

    try:
        async with client.driver.session() as session:
            created_count = 0
            for dep in COMPONENT_DEPENDENCIES:
                result = await session.run(
                    f"""
                    MATCH (source:Component {{id: $source_id}})
                    MATCH (target:Component {{id: $target_id}})
                    CREATE (source)-[r:{dep['type']}]->(target)
                    RETURN r
                    """,
                    source_id=dep["source_id"],
                    target_id=dep["target_id"]
                )
                if await result.single():
                    created_count += 1

        logger.info(f"✅ Created {created_count} dependencies")
        return created_count
    except Exception as e:
        logger.error(f"❌ Dependency creation failed: {e}")
        return 0


async def validate_ingestion(client: Neo4jClient) -> Dict:
    """Validate the ingestion"""
    stats = await client.get_database_stats()

    validation = {
        "component_count": stats.get("component_count", 0),
        "relationship_count": stats.get("relationship_count", 0),
    }

    logger.info("\n" + "="*60)
    logger.info("📊 BOILERPLATE INGESTION REPORT")
    logger.info("="*60)
    logger.info(f"Components created: {validation['component_count']}")
    logger.info(f"Dependencies created: {validation['relationship_count']}")
    logger.info("="*60)

    return validation


async def main():
    """Main ingestion orchestration"""
    logger.info("🚀 Starting boilerplate component ingestion...\n")

    client = Neo4jClient()

    try:
        if not await client.connect():
            logger.error("Failed to connect to Neo4j")
            return

        logger.info("✅ Connected to Neo4j\n")

        # Initialize schema
        if not await init_schema(client):
            return

        # Ingest components
        shared_count = await ingest_components(client, SHARED_COMPONENTS, "shared")
        task_manager_count = await ingest_components(client, TASK_MANAGER_COMPONENTS, "task_manager")
        crm_count = await ingest_components(client, CRM_COMPONENTS, "crm")
        ecommerce_count = await ingest_components(client, ECOMMERCE_COMPONENTS, "ecommerce")

        # Create dependencies
        dep_count = await create_dependencies(client)

        # Validate
        logger.info("\n✅ Validating ingestion...")
        validation = await validate_ingestion(client)

        # Summary
        total_components = shared_count + task_manager_count + crm_count + ecommerce_count
        logger.info("\n" + "="*60)
        logger.info("✅ BOILERPLATE INGESTION COMPLETE")
        logger.info("="*60)
        logger.info(f"✅ {shared_count} shared components")
        logger.info(f"✅ {task_manager_count} task manager components")
        logger.info(f"✅ {crm_count} CRM components")
        logger.info(f"✅ {ecommerce_count} e-commerce components")
        logger.info(f"✅ {dep_count} dependencies")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
