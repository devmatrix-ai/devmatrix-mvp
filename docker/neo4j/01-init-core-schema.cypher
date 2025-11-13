// ============================================================================
// NEO4J INITIALIZATION SCRIPT - DevMatrix MVP
// ============================================================================
// Archivo: 01-init-core-schema.cypher
// Propósito: Crear constraints, índices y estructura base del grafo
// Ejecutar: En Neo4j al iniciar (copiar a /var/lib/neo4j/import/)
// ============================================================================

// =============================================================================
// PARTE 1: CONSTRAINTS (Unicidad e Integridad)
// =============================================================================

// Template constraints
CREATE CONSTRAINT template_id IF NOT EXISTS FOR (t:Template) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT template_name_version IF NOT EXISTS FOR (t:Template) REQUIRE (t.name, t.version) IS UNIQUE;

// Design System constraints
CREATE CONSTRAINT design_token_key IF NOT EXISTS FOR (d:DesignToken) REQUIRE d.key IS UNIQUE;
CREATE CONSTRAINT ui_component_id IF NOT EXISTS FOR (u:UIComponent) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT figma_import_id IF NOT EXISTS FOR (f:FigmaImport) REQUIRE f.id IS UNIQUE;

// Domain & Specs constraints
CREATE CONSTRAINT domain_model_id IF NOT EXISTS FOR (dm:DomainModel) REQUIRE dm.id IS UNIQUE;
CREATE CONSTRAINT use_case_id IF NOT EXISTS FOR (uc:UseCase) REQUIRE uc.id IS UNIQUE;
CREATE CONSTRAINT project_spec_id IF NOT EXISTS FOR (ps:ProjectSpec) REQUIRE ps.id IS UNIQUE;

// Project constraints
CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;

// Workflow constraints
CREATE CONSTRAINT workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT stage_id IF NOT EXISTS FOR (s:Stage) REQUIRE s.id IS UNIQUE;

// Customization constraints
CREATE CONSTRAINT template_override_id IF NOT EXISTS FOR (t:TemplateOverride) REQUIRE t.id IS UNIQUE;

// Generated artifacts constraints
CREATE CONSTRAINT generated_file_id IF NOT EXISTS FOR (gf:GeneratedFile) REQUIRE gf.id IS UNIQUE;
CREATE CONSTRAINT generation_plan_id IF NOT EXISTS FOR (gp:GenerationPlan) REQUIRE gp.id IS UNIQUE;

// Metrics constraints
CREATE CONSTRAINT metric_id IF NOT EXISTS FOR (m:Metric) REQUIRE m.id IS UNIQUE;

// =============================================================================
// PARTE 2: ÍNDICES (Performance para queries frecuentes)
// =============================================================================

// Template indexes
CREATE INDEX template_category IF NOT EXISTS FOR (t:Template) ON (t.category);
CREATE INDEX template_stack IF NOT EXISTS FOR (t:Template) ON (t.stack);
CREATE INDEX template_language IF NOT EXISTS FOR (t:Template) ON (t.language);
CREATE INDEX template_precision IF NOT EXISTS FOR (t:Template) ON (t.precision);
CREATE INDEX template_tags IF NOT EXISTS FOR (t:Template) ON (t.tag);

// Multi-tenancy indexes (CRÍTICO)
CREATE INDEX tenant_id IF NOT EXISTS FOR (n) ON (n.tenant_id);
CREATE INDEX tenant_created IF NOT EXISTS FOR (n) ON (n.tenant_id, n.created_at);

// Design System indexes
CREATE INDEX design_token_tenant IF NOT EXISTS FOR (d:DesignToken) ON (d.tenant_id);
CREATE INDEX design_token_category IF NOT EXISTS FOR (d:DesignToken) ON (d.category);
CREATE INDEX ui_component_tenant IF NOT EXISTS FOR (u:UIComponent) ON (u.tenant_id);

// Domain Model indexes
CREATE INDEX domain_model_tenant IF NOT EXISTS FOR (dm:DomainModel) ON (dm.tenant_id);
CREATE INDEX domain_model_domain IF NOT EXISTS FOR (dm:DomainModel) ON (dm.domain);

// Project indexes
CREATE INDEX project_tenant IF NOT EXISTS FOR (p:Project) ON (p.tenant_id);
CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status);

// Workflow indexes
CREATE INDEX workflow_tenant IF NOT EXISTS FOR (w:Workflow) ON (w.tenant_id);
CREATE INDEX stage_workflow IF NOT EXISTS FOR (s:Stage) ON (s.workflow_id);

// Generated artifacts indexes
CREATE INDEX generated_file_project IF NOT EXISTS FOR (gf:GeneratedFile) ON (gf.project_id);
CREATE INDEX generated_file_path IF NOT EXISTS FOR (gf:GeneratedFile) ON (gf.path);
CREATE INDEX generation_plan_project IF NOT EXISTS FOR (gp:GenerationPlan) ON (gp.project_id);

// Metrics indexes
CREATE INDEX metric_template IF NOT EXISTS FOR (m:Metric) ON (m.template_id);
CREATE INDEX metric_tenant IF NOT EXISTS FOR (m:Metric) ON (m.tenant_id);
CREATE INDEX metric_measured IF NOT EXISTS FOR (m:Metric) ON (m.measured_at);

// =============================================================================
// PARTE 3: FULLTEXT INDEXES (Para búsquedas)
// =============================================================================

// Template search
CREATE FULLTEXT INDEX template_search IF NOT EXISTS FOR (t:Template) ON EACH [t.name, t.description, t.tag];

// Domain Model search
CREATE FULLTEXT INDEX domain_search IF NOT EXISTS FOR (dm:DomainModel) ON EACH [dm.name];

// Use Case search
CREATE FULLTEXT INDEX usecase_search IF NOT EXISTS FOR (uc:UseCase) ON EACH [uc.name, uc.description];

// =============================================================================
// PARTE 4: NODOS INICIALES (Estructura mínima viable)
// =============================================================================

// Crear categorías base de templates
CREATE (:Category {
    id: "infrastructure",
    name: "Infrastructure",
    description: "Docker, Dockerfile, docker-compose, CI/CD",
    icon: "⚙️",
    order: 0,
    created_at: datetime()
});

CREATE (:Category {
    id: "backend",
    name: "Backend",
    description: "API routes, services, models",
    icon: "🔌",
    order: 1,
    created_at: datetime()
});

CREATE (:Category {
    id: "frontend",
    name: "Frontend",
    description: "React components, pages, layouts",
    icon: "🎨",
    order: 2,
    created_at: datetime()
});

CREATE (:Category {
    id: "database",
    name: "Database",
    description: "Schema, migrations, ORM",
    icon: "💾",
    order: 3,
    created_at: datetime()
});

CREATE (:Category {
    id: "auth",
    name: "Authentication",
    description: "JWT, OAuth, session management",
    icon: "🔐",
    order: 4,
    created_at: datetime()
});

CREATE (:Category {
    id: "domain",
    name: "Domain Models",
    description: "Entities, aggregates, value objects",
    icon: "🎯",
    order: 5,
    created_at: datetime()
});

// =============================================================================
// FIN DEL SCRIPT
// =============================================================================
