# Gold Set - Proyectos Canario para MGE V2

**Version:** 1.0
**Created:** 2025-11-11
**Owner:** Ariel
**Status:** ✅ FROZEN (Ready for baseline)

---

## Objetivo

Definir un conjunto **congelado** de 15 proyectos representativos para validar:
- Precisión ≥98% sostenida (2 semanas consecutivas)
- Coste <$200 por proyecto
- Latencia p95 estable
- Cobertura de lenguajes, frameworks y arquitecturas

---

## Criterios de Selección

### Diversidad Técnica
- **Lenguajes:** Python, TypeScript/JavaScript, Go, Rust
- **Frameworks:** FastAPI, Express, Next.js, React, Vue, Django
- **Arquitecturas:** Monolito, Microservicios, Monorepo, Serverless
- **Complejidad:** Baja (5-10 archivos), Media (20-50 archivos), Alta (100+ archivos)

### Representatividad
- Patrones comunes de producción
- APIs REST y GraphQL
- Bases de datos (PostgreSQL, MongoDB, Redis)
- Autenticación (JWT, OAuth)
- Testing (pytest, jest, vitest)

---

## 📋 Gold Set (15 Proyectos)

### Tier 1: Python (5 proyectos)

#### 1. FastAPI REST API - Task Management ⭐
**Complejidad:** Media
**Archivos:** ~30 archivos
**Stack:** FastAPI + PostgreSQL + JWT + Alembic
**Características:**
- CRUD completo (Tasks, Users, Categories, Tags)
- Autenticación JWT con roles
- Validación con Pydantic
- Migraciones Alembic
- Tests con pytest + asyncio

**Baseline V1:**
- Tiempo: N/A (nuevo proyecto)
- Coste: ~$6.56
- Precisión: TBD

**Ubicación:** `/tests/e2e/fixtures/fastapi-task-management/`

---

#### 2. Django Blog API
**Complejidad:** Media
**Archivos:** ~40 archivos
**Stack:** Django REST Framework + PostgreSQL + Celery
**Características:**
- Blog con Posts, Comments, Users
- Django ORM
- Celery para tareas async
- Django Admin
- Tests con Django TestCase

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/django-blog-api/`

---

#### 3. Python CLI Tool - Code Analyzer
**Complejidad:** Baja
**Archivos:** ~15 archivos
**Stack:** Click + Rich + AST parsing
**Características:**
- Parse y análisis de código Python
- Output coloreado con Rich
- Configuración YAML
- Tests con pytest

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/python-cli-analyzer/`

---

#### 4. Flask Microservice - Payment Gateway
**Complejidad:** Alta
**Archivos:** ~60 archivos
**Stack:** Flask + Redis + RabbitMQ + Stripe API
**Características:**
- Integración Stripe
- Event-driven con RabbitMQ
- Cache con Redis
- Idempotency keys
- Tests con pytest + mocks

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/flask-payment-service/`

---

#### 5. Python Data Pipeline
**Complejidad:** Media
**Archivos:** ~25 archivos
**Stack:** Pandas + SQLAlchemy + S3 + Airflow
**Características:**
- ETL pipeline
- S3 integration
- Airflow DAGs
- Data validation
- Tests con pytest

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/python-data-pipeline/`

---

### Tier 2: TypeScript/JavaScript (5 proyectos)

#### 6. Next.js E-commerce Frontend
**Complejidad:** Alta
**Archivos:** ~80 archivos
**Stack:** Next.js 14 + TypeScript + Tailwind + Prisma
**Características:**
- App Router (RSC)
- Server Actions
- Product catalog + Cart
- Stripe checkout
- Tests con Vitest + Playwright

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/nextjs-ecommerce/`

---

#### 7. Express GraphQL API
**Complejidad:** Media
**Archivos:** ~35 archivos
**Stack:** Express + TypeScript + GraphQL + PostgreSQL
**Características:**
- GraphQL schema
- DataLoader para N+1
- JWT auth
- TypeORM
- Tests con Jest

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/express-graphql-api/`

---

#### 8. React Admin Dashboard
**Complejidad:** Alta
**Archivos:** ~100 archivos
**Stack:** React + TypeScript + Material-UI + React Query
**Características:**
- CRUD interfaces
- Charts (recharts)
- Data tables
- Real-time updates (WebSocket)
- Tests con Vitest + Testing Library

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/react-admin-dashboard/`

---

#### 9. Vue 3 SPA - Project Management
**Complejidad:** Media
**Archivos:** ~45 archivos
**Stack:** Vue 3 + TypeScript + Pinia + Vite
**Características:**
- Composition API
- Kanban board
- Drag & drop
- Vuetify components
- Tests con Vitest

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/vue3-project-mgmt/`

---

#### 10. Node.js Monorepo - Multi-tenant SaaS
**Complejidad:** Alta
**Archivos:** ~120 archivos
**Stack:** Turborepo + Next.js + Express + Shared packages
**Características:**
- Monorepo con 4 packages
- Shared UI components
- Shared utilities
- Multi-tenant architecture
- Tests con Jest + Playwright

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/nodejs-monorepo-saas/`

---

### Tier 3: Go & Rust (3 proyectos)

#### 11. Go REST API - URL Shortener
**Complejidad:** Baja
**Archivos:** ~20 archivos
**Stack:** Gin + PostgreSQL + Redis
**Características:**
- URL shortening service
- Click analytics
- Rate limiting
- Tests con go test

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/go-url-shortener/`

---

#### 12. Go Microservices - Event Sourcing
**Complejidad:** Alta
**Archivos:** ~70 archivos
**Stack:** Go + gRPC + Kafka + PostgreSQL
**Características:**
- Event sourcing pattern
- CQRS
- gRPC services
- Kafka events
- Tests con testify

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/go-event-sourcing/`

---

#### 13. Rust CLI - File Processor
**Complejidad:** Media
**Archivos:** ~30 archivos
**Stack:** Clap + Tokio + Serde
**Características:**
- Async file processing
- Multi-threaded
- CLI with subcommands
- Tests con cargo test

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/rust-file-processor/`

---

### Tier 4: Arquitecturas Especiales (2 proyectos)

#### 14. Serverless AWS Lambda - Image Resizer
**Complejidad:** Media
**Archivos:** ~25 archivos
**Stack:** AWS Lambda + S3 + TypeScript + Sharp
**Características:**
- Lambda handler
- S3 triggers
- Image processing
- CDK infrastructure
- Tests con Jest + LocalStack

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/aws-lambda-image-resizer/`

---

#### 15. Full-Stack Monolith - Social Network
**Complejidad:** Alta
**Archivos:** ~150 archivos
**Stack:** Django + React + PostgreSQL + Redis + Celery
**Características:**
- User profiles + Posts + Comments + Likes
- Real-time notifications (WebSocket)
- Background jobs (Celery)
- Full-text search (PostgreSQL)
- Tests con pytest + Jest

**Baseline V1:** TBD
**Ubicación:** `/tests/e2e/fixtures/fullstack-social-network/`

---

## 📊 Distribución

### Por Lenguaje
- Python: 5 proyectos (33%)
- TypeScript/JavaScript: 5 proyectos (33%)
- Go: 2 proyectos (13%)
- Rust: 1 proyecto (7%)
- Multi-lenguaje: 2 proyectos (13%)

### Por Complejidad
- Baja (5-20 archivos): 3 proyectos (20%)
- Media (20-60 archivos): 7 proyectos (47%)
- Alta (60+ archivos): 5 proyectos (33%)

### Por Arquitectura
- Monolito: 6 proyectos (40%)
- Microservicios: 3 proyectos (20%)
- Serverless: 1 proyecto (7%)
- Monorepo: 1 proyecto (7%)
- Full-stack: 2 proyectos (13%)
- CLI: 2 proyectos (13%)

---

## 🎯 Baseline V1 (Próximo Paso)

Para cada proyecto, medir:

### Métricas de Tiempo
- **Tiempo total:** Discovery → Deployment
- **Tiempo por fase:** Discovery, MasterPlan, Code Gen, Atomization, etc.
- **P50, P95, P99 latency**

### Métricas de Coste
- **Coste LLM total:** Suma de todos los prompts
- **Coste por tarea**
- **Coste por átomo**

### Métricas de Precisión
- **Spec Conformance:** % requisitos implementados correctamente
- **Integration Pass:** % tests de integración pasando
- **Validation Pass:** % validaciones L1-L4 pasando
- **Precision Score:** Fórmula compuesta (50% + 30% + 20%)

### Métricas de Calidad
- **Syntax errors:** Errores de sintaxis en código generado
- **Import errors:** Imports incorrectos
- **Type errors:** Errores de tipado
- **Retry rate:** % de tareas que requirieron retry

---

## 🔒 Reglas de Congelación

### ✅ Permitido
- Agregar mediciones baseline
- Actualizar métricas observadas
- Documentar hallazgos

### ❌ No Permitido
- Cambiar la lista de proyectos
- Modificar stack técnico de proyectos
- Alterar complejidad o scope

**Próxima revisión:** Solo si Precision Score <90% después de 2 semanas

---

## 📝 Registro de Cambios

### 2025-11-11
- ✅ Gold Set definido con 15 proyectos
- ✅ Distribución validada (lenguajes, complejidad, arquitectura)
- ✅ Set congelado y listo para baseline
- 🔄 Pendiente: Baseline V1 measurements

---

## 🚀 Next Steps

1. **Week 1:** Ejecutar baseline V1 en los 15 proyectos
2. **Week 1:** Documentar métricas en `baseline-results.md`
3. **Week 2:** Comparar MGE V2 vs Baseline V1
4. **Week 4:** Dual-run en proyectos seleccionados (3-5)

---

**Owner:** Ariel
**Status:** ✅ FROZEN
**Last Updated:** 2025-11-11
