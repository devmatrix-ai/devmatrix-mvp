# 🗃️ NEO4J SCHEMA - DevMatrix SaaS MVP

**Objetivo**: Generar apps completas (CRM + Task + Ecommerce) en monorepo con Docker + GitHub

---

## 📊 GRAFOS NECESARIOS (NO 7, LOS QUE HACEN FALTA)

### GRAFO 1: TEMPLATES CORE (Global)
```cypher
(:Template {
    id: "urn:template:...",
    name: "FastAPIMainApp",
    category: "infrastructure|auth|api|model|service|react-component|form|table|infra-docker|infra-github",
    stack: "backend|frontend|infra",
    language: "python|javascript|yaml|dockerfile",
    code: "...",
    parameters: [...],
    version: "1.0.0",
    precision: 0.95,
    usage_count: 0,
    success_rate: 0,
    tag: ["security", "ddd", "fastapi", ...]
})
```

**Relaciones**:
- `:REQUIRES` → otro Template (ej: JWT auth requiere User entity)
- `:CONFLICTS_WITH` → incompatible
- `:IMPLEMENTS` → patrón DDD
- `:USES_TOKEN` → DesignToken (para React components)
- `:GENERATES_FILE` → qué archivo crea

**Templates Necesarios (~80 total)**:
```
BACKEND (FastAPI + DDD):
  ├─ Infrastructure (5): MainApp, AppSetup, Settings, Error handling, Logging
  ├─ Auth (5): JWTAuth, PasswordHasher, OAuthIntegration, SessionManager, RefreshToken
  ├─ Database (5): SQLAlchemy setup, Migrations (Alembic), Repositories, UnitOfWork
  ├─ API (10): CRUDEndpoints, PaginationFormatter, ErrorResponses, RequestValidation
  ├─ DDD (8): Entity base, ValueObject, Aggregate, DomainEvent, Repository, Service
  ├─ CRM Models (8): Contact, Deal, Pipeline, Activity, Note, Task relationship
  ├─ Task Models (5): Task entity, Status workflow, Priority, Assignment
  ├─ Ecommerce Models (8): Product, Category, Cart, Order, Payment, Shipping
  └─ Services (10): EmailService, NotificationService, SearchService, CachingService

FRONTEND (React + Tailwind):
  ├─ Infrastructure (5): App.tsx, Router setup, API client, Theme provider
  ├─ Auth Components (4): LoginForm, SignupForm, ProtectedRoute, ProfileMenu
  ├─ Shared (8): Button, Input, Modal, Card, Table, Form, Pagination, Toast
  ├─ CRM Pages (12): ContactsTable, ContactDetail, DealsBoard, Pipeline, Activities
  ├─ Task Pages (8): TasksTable, TaskDetail, BoardView, CalendarView, TaskForm
  ├─ Ecommerce Pages (12): ProductCatalog, ProductDetail, Cart, Checkout, OrderHistory
  └─ Layouts (4): MainLayout, AdminLayout, AuthLayout, EmptyLayout

INFRASTRUCTURE:
  ├─ Docker (4): Dockerfile.api, Dockerfile.ui, docker-compose.yml, .dockerignore
  ├─ GitHub (3): CI pipeline (tests), CD pipeline (deploy), Actions
  ├─ Database Migrations (5): Initial schema, Add CRM tables, Add Task tables, Add Ecommerce tables
  └─ Config (5): .env.example, pyproject.toml, package.json, tsconfig.json
```

---

### GRAFO 2: FIGMA ASSETS (Per Tenant)
```cypher
(:FigmaImport {
    id: "uuid",
    tenant_id: "uuid",
    figma_file_id: "string",
    imported_at: datetime,
    status: "pending|processing|success|failed"
})

(:DesignToken {
    key: "color.primary|color.secondary|spacing.base|font.body|font.heading",
    value: "#0ea5e9|1rem|'Inter'",
    tenant_id: "uuid",
    source: "figma|manual",
    category: "color|spacing|font|size"
})

(:UIComponent {
    id: "uuid",
    tenant_id: "uuid",
    name: "Button|Card|Table|Form",
    figma_component_id: "string",
    tailwind_classes: "bg-primary text-white...",
    responsive_variants: {sm, md, lg, xl},
    dark_mode_support: true,
    code_template: "..."
})
```

**Relaciones**:
- `:USES_TOKEN` → DesignToken
- `:GENERATES_COMPONENT` → React component template
- `:BELONGS_TO_FIGMA` → FigmaImport

---

### GRAFO 3: CHAT SPECS (Per Tenant)
```cypher
(:ProjectSpec {
    id: "uuid",
    tenant_id: "uuid",
    raw_spec: "string (chat conversation)",
    parsed_at: datetime,
    status: "parsed|validated|ready"
})

(:DomainModel {
    id: "uuid",
    tenant_id: "uuid",
    name: "Contact|Deal|Task|Product",
    domain: "crm|task_manager|ecommerce",
    fields: [{name, type, required, validation}],
    relationships: [{name, target, cardinality}],
    extracted_from_spec: true
})

(:UseCase {
    id: "uuid",
    tenant_id: "uuid",
    name: "Create Contact|View Task Board|Checkout Order",
    actor: "user|admin",
    steps: [...],
    domain: "crm|task_manager|ecommerce"
})

(:CustomWorkflow {
    id: "uuid",
    tenant_id: "uuid",
    name: "Deal approval flow|Task escalation",
    stages: [{name, rules, actions}],
    triggers: [...],
    domain: "crm|task_manager|ecommerce"
})
```

**Relaciones**:
- `:EXTRACTED_FROM` → ProjectSpec
- `:USES_MODEL` → DomainModel
- `:DEFINES_WORKFLOW` → CustomWorkflow
- `:REQUIRES_TEMPLATE` → Template (si el parser lo detecta)

---

### GRAFO 4: PROJECT (Per Tenant)
```cypher
(:Project {
    id: "uuid",
    tenant_id: "uuid",
    name: "Acme CRM",
    description: "...",
    domains: ["crm", "task_manager"],  // cuáles incluir en este MVP
    created_at: datetime,
    status: "setup|generating|ready|deployed"
})
```

**Relaciones**:
- `:HAS_SPEC` → ProjectSpec
- `:HAS_FIGMA_IMPORT` → FigmaImport
- `:HAS_CUSTOMIZATION` → CustomizationOverride
- `:USES_TEMPLATE` → Template (queda después de generar)
- `:GENERATED` → GeneratedArtifact

---

### GRAFO 5: CUSTOMIZATIONS (Per Tenant)
```cypher
(:TemplateOverride {
    id: "uuid",
    tenant_id: "uuid",
    template_id: "urn:template:...",
    override_code: "string (modificado)",
    override_reason: "string",
    created_at: datetime
})

(:WorkflowCustomization {
    id: "uuid",
    tenant_id: "uuid",
    workflow_id: "uuid",
    modifications: [{field, old_value, new_value}]
})
```

---

### GRAFO 6: GENERATED ARTIFACTS (Per Project/Generation)
```cypher
(:GeneratedFile {
    id: "uuid",
    project_id: "uuid",
    path: "src/api/routes/users.py",
    content: "...",
    generated_from_template: "urn:template:...",
    generated_at: datetime,
    lines_of_code: 150,
    test_coverage: 0.95
})

(:GenerationPlan {
    id: "uuid",
    project_id: "uuid",
    generated_at: datetime,
    templates_used: ["urn:template:...", ...],
    total_files: 45,
    total_loc: 12500,
    estimated_precision: 0.92
})
```

**Relaciones**:
- `:GENERATED_FROM` → Template
- `:GENERATED_IN_PLAN` → GenerationPlan
- `:PART_OF_PROJECT` → Project

---

### GRAFO 7: METRICS (Global + Per Tenant)
```cypher
(:Metric {
    id: "uuid",
    template_id: "urn:template:...",
    metric_name: "precision|success_rate|usage_count|avg_execution_time",
    value: 0.95,
    tenant_id: "uuid" (null = global),
    measured_at: datetime
})
```

---

## 🔄 FLUJO DE GENERACIÓN

```
1. User uploads Figma file
   └─ Figma Importer → DesignToken + UIComponent nodes

2. User sends spec via chat
   └─ Spec Parser → DomainModel + UseCase + CustomWorkflow nodes

3. Planner/Orquestador:
   ├─ Lee Project spec + Figma imports + Customizations
   ├─ Navega Template graph:
   │  ├─ Encuentra templates para cada Domain Model
   │  ├─ Resuelve dependencies (REQUIRES, CONFLICTS_WITH)
   │  ├─ Aplica DesignTokens a React components
   │  ├─ Aplica CustomWorkflows a backend services
   │  └─ Ordena topológicamente para generación
   ├─ Crea GenerationPlan
   └─ Dry-run: preview de archivos a crear

4. Generador:
   ├─ Para cada template en plan:
   │  ├─ Renderiza con tenant params
   │  ├─ Inyecta DesignTokens
   │  ├─ Aplica customizaciones
   │  └─ Crea GeneratedFile node
   ├─ Crea docker-compose.yml
   ├─ Crea Dockerfile
   ├─ Crea GitHub Actions
   ├─ Crea monorepo structure
   ├─ Pushea a GitHub
   └─ Crea GenerationPlan con métricas

5. Output:
   ├─ Repo de GitHub completamente funcional
   ├─ docker-compose up -d → app corriendo
   ├─ Todos los GeneratedFile nodes creados
   └─ Metrics actualizadas
```

---

## 📋 CONSTRAINTS E ÍNDICES CRÍTICOS

```cypher
// Identificadores únicos
CREATE CONSTRAINT template_id FOR (t:Template) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT figma_import_id FOR (f:FigmaImport) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT project_id FOR (p:Project) REQUIRE p.id IS UNIQUE;

// Multi-tenancy (crítico)
CREATE INDEX FOR (n) ON (n.tenant_id);
CREATE INDEX FOR (n) ON (n.tenant_id, n.created_at);

// Performance
CREATE INDEX FOR (t:Template) ON (t.category, t.stack);
CREATE INDEX FOR (t:Template) ON (t.version);
CREATE INDEX FOR (d:DesignToken) ON (d.key);
CREATE INDEX FOR (d:DomainModel) ON (d.tenant_id, d.domain);
```

---

## 🎯 SUMMARY: GRAFOS PARA MVP

```
✅ GRAFO 1: Templates Core (80 templates, relaciones)
✅ GRAFO 2: Figma Assets (per tenant)
✅ GRAFO 3: Chat Specs (per tenant)
✅ GRAFO 4: Project (per tenant)
✅ GRAFO 5: Customizations (per tenant)
✅ GRAFO 6: Generated Artifacts (per project)
✅ GRAFO 7: Metrics (tracking)

= 7 GRAFOS pero MUCHO más específicos y pragmáticos
```

---

## 🚀 IMPLEMENTACIÓN POR FASES

**Fase 1 (Semana 1)**: Setup Neo4j + Grafo 1 (Templates Core)
**Fase 2 (Semana 1-2)**: Grafo 2 (Figma Importer)
**Fase 3 (Semana 2-3)**: Grafo 3 (Spec Parser)
**Fase 4 (Semana 3)**: Grafo 4-5 (Project + Customizations)
**Fase 5 (Semana 3-4)**: Planner/Orquestador + Generador
**Fase 6 (Semana 4)**: Grafo 6-7 + Testing completo

---

*Actualizado: 2025-11-12 por Dany*
