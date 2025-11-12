"""
Neo4j Schema for Boilerplate Graph

Defines:
1. Node types (Component, Application, Stack, etc)
2. Relationships (USES, REQUIRES, PART_OF, etc)
3. Constraints and indexes
4. Initialization scripts
"""

from typing import List, Dict, Any


class BoilerplateSchema:
    """Schema definition for boilerplate component graph"""

    # =========================================================================
    # NODE DEFINITIONS
    # =========================================================================

    COMPONENT_CATEGORY_TYPES = [
        "Entity",
        "Service",
        "API",
        "UI",
        "Middleware",
        "Integration",
        "Utility",
        "Pattern",
    ]

    APPLICATION_TYPES = [
        "task_manager",
        "crm",
        "ecommerce",
    ]

    LANGUAGES = [
        "python",
        "typescript",
        "javascript",
        "go",
        "rust",
        "sql",
    ]

    COMPLEXITY_LEVELS = [
        "simple",
        "medium",
        "complex",
    ]

    # =========================================================================
    # CYPHER QUERIES FOR SCHEMA INITIALIZATION
    # =========================================================================

    SETUP_QUERIES = [
        # =====================================================================
        # CONSTRAINTS
        # =====================================================================
        # Component unique constraint
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE
        """,

        # Application unique constraint
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (a:Application) REQUIRE a.id IS UNIQUE
        """,

        # Stack unique constraint
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (s:Stack) REQUIRE s.id IS UNIQUE
        """,

        # =====================================================================
        # INDEXES
        # =====================================================================
        # Component indexes for common queries
        """
        CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.name)
        """,

        """
        CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.category)
        """,

        """
        CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.language)
        """,

        """
        CREATE INDEX IF NOT EXISTS FOR (c:Component) ON (c.framework)
        """,

        # Application indexes
        """
        CREATE INDEX IF NOT EXISTS FOR (a:Application) ON (a.type)
        """,

        """
        CREATE INDEX IF NOT EXISTS FOR (a:Application) ON (a.status)
        """,

        # Stack indexes
        """
        CREATE INDEX IF NOT EXISTS FOR (s:Stack) ON (s.frontend_framework)
        """,

        """
        CREATE INDEX IF NOT EXISTS FOR (s:Stack) ON (s.backend_framework)
        """,
    ]

    # =========================================================================
    # CYPHER TEMPLATES FOR COMMON OPERATIONS
    # =========================================================================

    @staticmethod
    def create_component() -> str:
        """Template for creating a Component node"""
        return """
        CREATE (c:Component {
            id: $id,
            name: $name,
            description: $description,
            category: $category,
            language: $language,
            framework: $framework,
            complexity: $complexity,
            purpose: $purpose,
            code: $code,
            created_at: datetime(),
            updated_at: datetime(),
            version: '1.0'
        })
        RETURN c
        """

    @staticmethod
    def create_application() -> str:
        """Template for creating an Application node"""
        return """
        CREATE (a:Application {
            id: $id,
            name: $name,
            description: $description,
            type: $type,
            status: $status,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN a
        """

    @staticmethod
    def create_stack() -> str:
        """Template for creating a Stack node"""
        return """
        CREATE (s:Stack {
            id: $id,
            name: $name,
            frontend_framework: $frontend_framework,
            backend_framework: $backend_framework,
            database: $database,
            cache: $cache,
            additional_services: $additional_services,
            created_at: datetime()
        })
        RETURN s
        """

    @staticmethod
    def create_component_relationship(rel_type: str) -> str:
        """Template for creating relationships between components"""
        return f"""
        MATCH (source:Component {{id: $source_id}})
        MATCH (target:Component {{id: $target_id}})
        CREATE (source)-[r:{rel_type}]->(target)
        RETURN r
        """

    @staticmethod
    def query_component_dependencies() -> str:
        """Get all dependencies of a component"""
        return """
        MATCH (c:Component {id: $component_id})
        OPTIONAL MATCH (c)-[r:USES|REQUIRES]->(dep:Component)
        RETURN c, collect({component: dep, relationship: type(r)}) as dependencies
        """

    @staticmethod
    def query_application_components() -> str:
        """Get all components required for an application"""
        return """
        MATCH (app:Application {id: $app_id})
        OPTIONAL MATCH (app)-[r:REQUIRES|USES]->(comp:Component)
        RETURN app, collect({component: comp, relationship: type(r)}) as components
        """

    @staticmethod
    def query_stack_compatibility() -> str:
        """Check if components are compatible with a stack"""
        return """
        MATCH (s:Stack {id: $stack_id})
        MATCH (c:Component)
        WHERE c.framework IN [$framework] OR c.language IN [$language]
        RETURN c
        """

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    @staticmethod
    def batch_create_components() -> str:
        """Batch create multiple components"""
        return """
        UNWIND $components as comp
        CREATE (c:Component {
            id: comp.id,
            name: comp.name,
            description: comp.description,
            category: comp.category,
            language: comp.language,
            framework: comp.framework,
            complexity: comp.complexity,
            purpose: comp.purpose,
            code: comp.code,
            created_at: datetime(),
            updated_at: datetime(),
            version: '1.0'
        })
        RETURN COUNT(c) as created
        """

    @staticmethod
    def batch_create_relationships() -> str:
        """Batch create multiple relationships"""
        return """
        UNWIND $relationships as rel
        MATCH (source:Component {id: rel.source_id})
        MATCH (target:Component {id: rel.target_id})
        CREATE (source)-[r:USES {created_at: datetime()}]->(target)
        RETURN COUNT(r) as created
        """

    # =========================================================================
    # QUERY PATTERNS
    # =========================================================================

    @staticmethod
    def find_reusable_components(app_type: str) -> str:
        """Find components that should be in a specific app type"""
        return f"""
        MATCH (c:Component)
        WHERE c.purpose CONTAINS '{app_type}' OR c.category IN ['Entity', 'Service', 'Utility']
        RETURN c
        ORDER BY c.complexity, c.name
        """

    @staticmethod
    def get_component_graph() -> str:
        """Get the full dependency graph for components"""
        return """
        MATCH (c:Component)
        OPTIONAL MATCH (c)-[r:USES|REQUIRES]->(dep:Component)
        RETURN c, r, dep
        """

    @staticmethod
    def find_compatible_stacks(language: str, framework: str) -> str:
        """Find stacks compatible with specific tech"""
        return f"""
        MATCH (s:Stack)
        WHERE s.backend_framework = '{framework}' OR s.frontend_framework = '{framework}'
        RETURN s
        """

    @staticmethod
    def validate_component_integrity() -> str:
        """Validate component graph integrity"""
        return """
        MATCH (c:Component)
        OPTIONAL MATCH (c)-[r:USES|REQUIRES]->(dep:Component)
        WHERE dep IS NULL AND r IS NOT NULL
        RETURN c as component_with_missing_dependency, COUNT(r) as orphaned_relationships
        """
