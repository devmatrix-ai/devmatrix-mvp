#!/usr/bin/env python3
"""
Script para inicializar Neo4j con el schema y seed templates
"""
import asyncio
from neo4j import GraphDatabase
from datetime import datetime

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "devmatrix123"

class Neo4jInitializer:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def run_query(self, query: str, params: dict = None):
        """Ejecuta una query en Neo4j"""
        with self.driver.session() as session:
            try:
                result = session.run(query, params or {})
                return result.consume()
            except Exception as e:
                print(f"❌ Error en query: {str(e)}")
                print(f"Query: {query[:100]}...")
                raise

    def init_constraints(self):
        """Crea constraints para garantizar unicidad"""
        print("\n📋 Creando constraints...")

        constraints = [
            "CREATE CONSTRAINT template_id IF NOT EXISTS FOR (t:Template) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT design_token_key IF NOT EXISTS FOR (d:DesignToken) REQUIRE d.key IS UNIQUE",
            "CREATE CONSTRAINT ui_component_id IF NOT EXISTS FOR (u:UIComponent) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT figma_import_id IF NOT EXISTS FOR (f:FigmaImport) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT domain_model_id IF NOT EXISTS FOR (dm:DomainModel) REQUIRE dm.id IS UNIQUE",
            "CREATE CONSTRAINT use_case_id IF NOT EXISTS FOR (uc:UseCase) REQUIRE uc.id IS UNIQUE",
            "CREATE CONSTRAINT project_spec_id IF NOT EXISTS FOR (ps:ProjectSpec) REQUIRE ps.id IS UNIQUE",
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE",
            "CREATE CONSTRAINT stage_id IF NOT EXISTS FOR (s:Stage) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT template_override_id IF NOT EXISTS FOR (t:TemplateOverride) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT generated_file_id IF NOT EXISTS FOR (gf:GeneratedFile) REQUIRE gf.id IS UNIQUE",
            "CREATE CONSTRAINT generation_plan_id IF NOT EXISTS FOR (gp:GenerationPlan) REQUIRE gp.id IS UNIQUE",
            "CREATE CONSTRAINT metric_id IF NOT EXISTS FOR (m:Metric) REQUIRE m.id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                self.run_query(constraint)
                print(f"  ✅ {constraint.split('FOR')[1][:40]}...")
            except Exception as e:
                print(f"  ⚠️  {str(e)[:50]}")

    def init_indexes(self):
        """Crea índices para performance"""
        print("\n🔍 Creando índices...")

        indexes = [
            "CREATE INDEX template_category IF NOT EXISTS FOR (t:Template) ON (t.category)",
            "CREATE INDEX template_stack IF NOT EXISTS FOR (t:Template) ON (t.stack)",
            "CREATE INDEX template_language IF NOT EXISTS FOR (t:Template) ON (t.language)",
            "CREATE INDEX template_precision IF NOT EXISTS FOR (t:Template) ON (t.precision)",
            "CREATE INDEX design_token_category IF NOT EXISTS FOR (d:DesignToken) ON (d.category)",
            "CREATE INDEX ui_component_responsive IF NOT EXISTS FOR (u:UIComponent) ON (u.responsive_variants)",
            "CREATE INDEX domain_model_domain IF NOT EXISTS FOR (dm:DomainModel) ON (dm.domain)",
            "CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status)",
            "CREATE INDEX workflow_tenant IF NOT EXISTS FOR (w:Workflow) ON (w.tenant_id)",
            "CREATE INDEX generated_file_project IF NOT EXISTS FOR (gf:GeneratedFile) ON (gf.project_id)",
            "CREATE INDEX metric_template IF NOT EXISTS FOR (m:Metric) ON (m.template_id)",
            "CREATE INDEX metric_measured IF NOT EXISTS FOR (m:Metric) ON (m.measured_at)",
        ]

        for index in indexes:
            try:
                self.run_query(index)
                print(f"  ✅ {index.split('ON')[0][-30:].strip()}")
            except Exception as e:
                print(f"  ⚠️  {str(e)[:50]}")

    def seed_categories(self):
        """Crea las categorías base"""
        print("\n📂 Creando categorías...")

        categories = [
            {"id": "infrastructure", "name": "Infrastructure", "desc": "Docker, CI/CD", "icon": "⚙️", "order": 0},
            {"id": "backend", "name": "Backend", "desc": "API, Services", "icon": "🔌", "order": 1},
            {"id": "frontend", "name": "Frontend", "desc": "React, Components", "icon": "🎨", "order": 2},
            {"id": "database", "name": "Database", "desc": "Schema, Migrations", "icon": "💾", "order": 3},
            {"id": "auth", "name": "Authentication", "desc": "JWT, Security", "icon": "🔐", "order": 4},
            {"id": "domain", "name": "Domain Models", "desc": "Entities, DDD", "icon": "🎯", "order": 5},
        ]

        for cat in categories:
            query = """
            CREATE (c:Category {
                id: $id,
                name: $name,
                description: $desc,
                icon: $icon,
                order: $order,
                created_at: datetime()
            })
            """
            self.run_query(query, cat)
            print(f"  ✅ {cat['name']}")

    def seed_templates(self):
        """Crea los templates core"""
        print("\n📦 Creando templates base...")

        templates = [
            {
                "id": "urn:template:backend:fastapi:main-app:1.0",
                "name": "FastAPI Main App",
                "version": "1.0.0",
                "category": "infrastructure",
                "stack": "backend",
                "language": "python",
                "framework": "fastapi",
                "complexity": "simple",
                "description": "FastAPI application entry point",
                "precision": 0.98,
            },
            {
                "id": "urn:template:backend:fastapi:settings:1.0",
                "name": "FastAPI Settings",
                "version": "1.0.0",
                "category": "infrastructure",
                "stack": "backend",
                "language": "python",
                "framework": "fastapi",
                "complexity": "simple",
                "description": "Pydantic settings for configuration",
                "precision": 0.97,
            },
            {
                "id": "urn:template:backend:database:sqlalchemy-setup:1.0",
                "name": "SQLAlchemy Setup",
                "version": "1.0.0",
                "category": "database",
                "stack": "backend",
                "language": "python",
                "framework": "sqlalchemy",
                "complexity": "medium",
                "description": "SQLAlchemy engine and session setup",
                "precision": 0.96,
            },
            {
                "id": "urn:template:backend:auth:jwt-service:1.0",
                "name": "JWT Auth Service",
                "version": "1.0.0",
                "category": "auth",
                "stack": "backend",
                "language": "python",
                "framework": "fastapi",
                "complexity": "medium",
                "description": "JWT token creation and verification",
                "precision": 0.96,
            },
            {
                "id": "urn:template:backend:auth:password-hasher:1.0",
                "name": "Password Hasher",
                "version": "1.0.0",
                "category": "auth",
                "stack": "backend",
                "language": "python",
                "framework": "fastapi",
                "complexity": "simple",
                "description": "Password hashing with bcrypt",
                "precision": 0.98,
            },
            {
                "id": "urn:template:backend:ddd:entity-base:1.0",
                "name": "DDD Entity Base",
                "version": "1.0.0",
                "category": "domain",
                "stack": "backend",
                "language": "python",
                "framework": "sqlalchemy",
                "complexity": "medium",
                "description": "Base SQLAlchemy model with DDD patterns",
                "precision": 0.95,
            },
            {
                "id": "urn:template:backend:ddd:repository:1.0",
                "name": "DDD Repository",
                "version": "1.0.0",
                "category": "domain",
                "stack": "backend",
                "language": "python",
                "framework": "sqlalchemy",
                "complexity": "medium",
                "description": "Generic repository pattern",
                "precision": 0.94,
            },
            {
                "id": "urn:template:backend:api:crud-endpoints:1.0",
                "name": "CRUD API Endpoints",
                "version": "1.0.0",
                "category": "backend",
                "stack": "backend",
                "language": "python",
                "framework": "fastapi",
                "complexity": "medium",
                "description": "Generic CRUD endpoints",
                "precision": 0.94,
            },
            {
                "id": "urn:template:domain:user-entity:1.0",
                "name": "User Entity",
                "version": "1.0.0",
                "category": "domain",
                "stack": "backend",
                "language": "python",
                "framework": "sqlalchemy",
                "complexity": "medium",
                "description": "User entity with authentication",
                "precision": 0.95,
            },
            {
                "id": "urn:template:domain:task-entity:1.0",
                "name": "Task Entity",
                "version": "1.0.0",
                "category": "domain",
                "stack": "backend",
                "language": "python",
                "framework": "sqlalchemy",
                "complexity": "medium",
                "description": "Task entity with status and priority",
                "precision": 0.94,
            },
        ]

        for t in templates:
            query = """
            CREATE (t:Template {
                id: $id,
                name: $name,
                version: $version,
                category: $category,
                stack: $stack,
                language: $language,
                framework: $framework,
                complexity: $complexity,
                description: $description,
                precision: $precision,
                usage_count: 0,
                success_rate: 0.0,
                created_at: datetime()
            })
            """
            self.run_query(query, t)
            print(f"  ✅ {t['name']}")

    def create_relations(self):
        """Crea relaciones entre templates"""
        print("\n🔗 Creando relaciones...")

        relations = [
            {
                "source": "urn:template:backend:auth:jwt-service:1.0",
                "target": "urn:template:backend:fastapi:settings:1.0",
                "type": "REQUIRES",
                "reason": "Settings para secret key",
            },
            {
                "source": "urn:template:backend:database:sqlalchemy-setup:1.0",
                "target": "urn:template:backend:fastapi:settings:1.0",
                "type": "REQUIRES",
                "reason": "Settings para database URL",
            },
            {
                "source": "urn:template:backend:ddd:entity-base:1.0",
                "target": "urn:template:backend:database:sqlalchemy-setup:1.0",
                "type": "REQUIRES",
                "reason": "Base class dependency",
            },
            {
                "source": "urn:template:domain:user-entity:1.0",
                "target": "urn:template:backend:ddd:entity-base:1.0",
                "type": "EXTENDS",
                "reason": "Hereda de TimestampedModel",
            },
            {
                "source": "urn:template:domain:task-entity:1.0",
                "target": "urn:template:backend:ddd:entity-base:1.0",
                "type": "EXTENDS",
                "reason": "Hereda de TimestampedModel",
            },
            {
                "source": "urn:template:backend:api:crud-endpoints:1.0",
                "target": "urn:template:backend:auth:jwt-service:1.0",
                "type": "USES",
                "reason": "Para autenticación de endpoints",
            },
        ]

        for rel in relations:
            query = f"""
            MATCH (source:Template {{id: $source}}),
                  (target:Template {{id: $target}})
            CREATE (source)-[r:{rel['type']} {{reason: $reason, min_version: "1.0.0"}}]->(target)
            """
            self.run_query(query, rel)
            print(f"  ✅ {rel['source'].split(':')[3][:20]} -> {rel['target'].split(':')[3][:20]}")

    def init(self):
        """Ejecuta la inicialización completa"""
        print("\n" + "="*60)
        print("🚀 INICIALIZANDO NEO4J PARA DEVMATRIX MVP")
        print("="*60)

        try:
            self.init_constraints()
            self.init_indexes()
            self.seed_categories()
            self.seed_templates()
            self.create_relations()

            print("\n" + "="*60)
            print("✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
            print("="*60)
            print("\n📊 Estadísticas:")

            # Count nodes
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
                for record in result:
                    print(f"  • {record['label']}: {record['count']} nodos")

                result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
                print("\n  Relaciones:")
                for record in result:
                    print(f"  • {record['type']}: {record['count']} relaciones")

        except Exception as e:
            print(f"\n❌ Error en inicialización: {str(e)}")
            raise
        finally:
            self.close()

if __name__ == "__main__":
    initializer = Neo4jInitializer()
    initializer.init()
