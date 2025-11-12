"""Ingest 30 Backend Templates into Neo4j

This script:
1. Loads template data structures
2. Creates Template nodes in Neo4j
3. Creates Category, Framework, and support nodes
4. Creates relationships between them
5. Validates the ingestion with queries
"""

import asyncio
import logging
from typing import Dict, List
from src.neo4j_client import Neo4jClient
from src.scripts.backend_templates_data import BACKEND_TEMPLATES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_categories(client: Neo4jClient) -> Dict[str, str]:
    """Create category nodes"""
    categories = [
        {"id": "authentication", "name": "Authentication", "icon": "🔐", "description": "Authentication & Authorization", "order": 1},
        {"id": "api", "name": "API", "icon": "🔌", "description": "REST & GraphQL APIs", "order": 2},
        {"id": "ddd", "name": "Domain-Driven Design", "icon": "🎯", "description": "DDD Patterns & Principles", "order": 3},
        {"id": "data", "name": "Data & Database", "icon": "💾", "description": "Data Access & Persistence", "order": 4},
        {"id": "service", "name": "Services", "icon": "⚙️", "description": "Business Logic & Services", "order": 5},
    ]

    created_ids = {}
    for cat in categories:
        try:
            cat_id = await client.create_category(cat)
            created_ids[cat["id"]] = cat_id
            logger.info(f"✅ Created category: {cat['name']}")
        except Exception as e:
            logger.error(f"❌ Failed to create category {cat['id']}: {e}")

    return created_ids


async def create_frameworks(client: Neo4jClient) -> Dict[str, str]:
    """Create framework nodes"""
    frameworks = [
        {"id": "fastapi", "name": "FastAPI", "type": "web", "language": "python", "version_range": ">=0.95.0", "ecosystem": "pip"},
        {"id": "django-rest-framework", "name": "Django REST Framework", "type": "web", "language": "python", "version_range": ">=3.12.0", "ecosystem": "pip"},
        {"id": "express", "name": "Express.js", "type": "web", "language": "javascript", "version_range": ">=4.18.0", "ecosystem": "npm"},
        {"id": "gin", "name": "Gin", "type": "web", "language": "go", "version_range": ">=1.8.0", "ecosystem": "go"},
        {"id": "actix-web", "name": "Actix-web", "type": "web", "language": "rust", "version_range": ">=4.0.0", "ecosystem": "cargo"},
        {"id": "django", "name": "Django", "type": "web", "language": "python", "version_range": ">=3.2.0", "ecosystem": "pip"},
        {"id": "sqlalchemy", "name": "SQLAlchemy", "type": "orm", "language": "python", "version_range": ">=1.4.0", "ecosystem": "pip"},
        {"id": "alembic", "name": "Alembic", "type": "migration", "language": "python", "version_range": ">=1.8.0", "ecosystem": "pip"},
        {"id": "redis", "name": "Redis", "type": "cache", "language": "generic", "version_range": ">=6.0.0", "ecosystem": "docker"},
        {"id": "domain-driven", "name": "Domain-Driven Design", "type": "pattern", "language": "generic", "version_range": ">=1.0.0", "ecosystem": "concept"},
    ]

    created_ids = {}
    for fw in frameworks:
        try:
            fw_id = await client.create_framework(fw)
            created_ids[fw["id"]] = fw_id
            logger.info(f"✅ Created framework: {fw['name']}")
        except Exception as e:
            logger.error(f"❌ Failed to create framework {fw['id']}: {e}")

    return created_ids


async def ingest_templates(client: Neo4jClient) -> int:
    """Ingest all 30 backend templates"""
    # Prepare template data
    templates_for_batch = []
    for template in BACKEND_TEMPLATES:
        templates_for_batch.append({
            "id": template["id"],
            "name": template["name"],
            "category": template["category"],
            "subcategory": template.get("subcategory", ""),
            "framework": template["framework"],
            "language": template["language"],
            "precision": template["precision"],
            "complexity": template.get("complexity", "medium"),
            "version": template.get("version", "1.0"),
            "status": template.get("status", "active"),
            "source": template.get("source", "backend"),
            "description": template["description"],
            "code": template["code"],
        })

    try:
        result = await client.batch_create_templates(templates_for_batch)
        logger.info(f"✅ Ingested {result['created']}/{result['total']} templates")
        return result["created"]
    except Exception as e:
        logger.error(f"❌ Failed to ingest templates: {e}")
        return 0


async def create_relationships(client: Neo4jClient, categories: Dict, frameworks: Dict) -> int:
    """Create relationships between templates and supporting nodes"""
    relationships_created = 0

    for template in BACKEND_TEMPLATES:
        # BELONGS_TO Category relationship
        category_id = categories.get(template["category"])
        if category_id:
            try:
                success = await client.create_relationship(
                    source_label="Template",
                    source_id=template["id"],
                    target_label="Category",
                    target_id=category_id,
                    relationship_type="BELONGS_TO",
                    properties={"order": 1}
                )
                if success:
                    relationships_created += 1
            except Exception as e:
                logger.warning(f"Failed to create BELONGS_TO for {template['id']}: {e}")

        # USES Framework relationship
        framework_id = frameworks.get(template["framework"])
        if framework_id:
            try:
                success = await client.create_relationship(
                    source_label="Template",
                    source_id=template["id"],
                    target_label="Framework",
                    target_id=framework_id,
                    relationship_type="USES",
                    properties={"language": template["language"]}
                )
                if success:
                    relationships_created += 1
            except Exception as e:
                logger.warning(f"Failed to create USES for {template['id']}: {e}")

    logger.info(f"✅ Created {relationships_created} relationships")
    return relationships_created


async def validate_ingestion(client: Neo4jClient) -> Dict:
    """Validate the ingestion with queries"""
    stats = await client.get_database_stats()

    validation = {
        "templates": stats.get("template_count", 0),
        "categories": stats.get("category_count", 0),
        "frameworks": stats.get("framework_count", 0),
        "relationships": stats.get("relationship_count", 0),
        "avg_precision": stats.get("avg_template_precision", 0.0),
    }

    logger.info("\n" + "="*50)
    logger.info("📊 INGESTION VALIDATION REPORT")
    logger.info("="*50)
    logger.info(f"Templates created: {validation['templates']}")
    logger.info(f"Categories created: {validation['categories']}")
    logger.info(f"Frameworks created: {validation['frameworks']}")
    logger.info(f"Total relationships: {validation['relationships']}")
    logger.info(f"Average template precision: {validation['avg_precision']:.3f}")
    logger.info("="*50)

    return validation


async def main():
    """Main ingestion orchestration"""
    logger.info("🚀 Starting template ingestion...")

    # Initialize Neo4j client
    client = Neo4jClient()

    try:
        # Connect
        if not await client.connect():
            logger.error("Failed to connect to Neo4j")
            return

        logger.info("✅ Connected to Neo4j")

        # Create support nodes
        logger.info("\n📝 Creating categories...")
        categories = await create_categories(client)

        logger.info("\n📝 Creating frameworks...")
        frameworks = await create_frameworks(client)

        # Ingest templates
        logger.info("\n📝 Ingesting templates...")
        templates_created = await ingest_templates(client)

        # Create relationships
        logger.info("\n🔗 Creating relationships...")
        relationships_created = await create_relationships(client, categories, frameworks)

        # Validate
        logger.info("\n✅ Validating ingestion...")
        validation = await validate_ingestion(client)

        # Summary
        logger.info("\n" + "="*50)
        logger.info("✅ INGESTION COMPLETE")
        logger.info("="*50)
        logger.info(f"✅ {templates_created} templates created")
        logger.info(f"✅ {len(categories)} categories created")
        logger.info(f"✅ {len(frameworks)} frameworks created")
        logger.info(f"✅ {relationships_created} relationships created")
        logger.info("="*50)

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
