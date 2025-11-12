# 🗃️ TEMPLATES NEO4J DESIGN
## Sistema de Templates como Grafos Navegables

**Versión**: 1.0
**Fecha**: 2025-11-12
**Estado**: Diseño Completo
**Precisión Target**: 99% para código determinístico

---

## 📋 RESUMEN EJECUTIVO

### Concepto Revolucionario

> **"Los templates no son archivos, son NODOS en un grafo de conocimiento"**
>
> Cada template es un nodo con relaciones, métricas, y evolución continua.

### Ventajas del Approach

```
✅ Navegación inteligente entre templates
✅ Compatibilidad verificable automáticamente
✅ Evolución basada en uso real
✅ Aprendizaje continuo incorporado
✅ Debugging transparente del proceso de generación
```

---

## 🏗️ ARQUITECTURA DEL GRAFO DE TEMPLATES

### Estructura de Nodos

```cypher
// Definición de un Template Node
(:Template {
    // Identificación
    id: "uuid-v4",
    name: "JWTAuthService",
    version: "2.1.0",

    // Categorización
    category: "auth",          // auth, model, service, api, ui, etc.
    stack: "fastapi",          // fastapi, react, both
    pattern: "ddd",            // ddd, mvc, functional, etc.

    // Métricas de Calidad
    precision: 0.99,           // Precisión histórica
    usage_count: 1247,         // Veces usado
    success_rate: 0.98,        // Tasa de éxito
    last_updated: datetime(),

    // Código y Configuración
    code_template: "...",      // Template string o función
    parameters: ["expire_minutes", "algorithm", "secret_source"],
    constraints: ["requires_user_model", "needs_redis"],

    // Metadata
    author: "system",
    description: "JWT authentication with refresh tokens",
    tags: ["security", "authentication", "jwt", "oauth2"],
    examples: [...]            // Ejemplos de uso
})
```

### Tipos de Relaciones

```cypher
// Relaciones entre Templates
(:Template)-[:REQUIRES]->(:Template)       // Dependencia fuerte
(:Template)-[:USES]->(:Template)           // Dependencia opcional
(:Template)-[:EXTENDS]->(:Template)        // Herencia/extensión
(:Template)-[:COMPATIBLE_WITH]->(:Template) // Compatibilidad verificada
(:Template)-[:CONFLICTS_WITH]->(:Template)  // Incompatibilidad conocida
(:Template)-[:GENERATES]->(:CodeBlock)      // Produce código
(:Template)-[:IMPLEMENTS]->(:Pattern)       // Implementa un patrón
(:Template)-[:TESTED_WITH]->(:TestSuite)    // Tests asociados
(:Template)-[:EVOLVED_FROM]->(:Template)    // Versión anterior
```

---

## 💎 LOS 55 TEMPLATES CORE

### Backend - FastAPI (30 Templates)

```python
fastapi_template_nodes = [
    # === INFRAESTRUCTURA BASE (10) ===
    {
        "name": "FastAPIMainApp",
        "category": "infrastructure",
        "code": """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_db()
    yield
    # Shutdown
    await shutdown_db()

app = FastAPI(
    title="{app_name}",
    version="{version}",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins={origins},
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
        """,
        "relations": [
            ("REQUIRES", "DatabaseSetup"),
            ("REQUIRES", "ConfigManagement"),
            ("GENERATES", "MainApplication")
        ]
    },

    {
        "name": "JWTAuthService",
        "category": "auth",
        "precision": 0.99,
        "code": """
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

class JWTAuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.SECRET_KEY = secrets.token_urlsafe(32)
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = {expire_minutes}

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def verify_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return payload
        except JWTError:
            return None
        """,
        "relations": [
            ("REQUIRES", "UserModel"),
            ("USES", "RedisCache"),
            ("GENERATES", "AuthenticationEndpoints"),
            ("COMPATIBLE_WITH", "CRUDEndpoints")
        ]
    },

    # === DDD PATTERNS (10) ===
    {
        "name": "AggregateRoot",
        "category": "ddd",
        "precision": 0.98,
        "code": """
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class {AggregrateName}(BaseModel):
    \"\"\"
    Aggregate Root for {AggregrateName} bounded context
    \"\"\"
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    version: int = Field(default=1)

    # Domain Events
    _events: List[DomainEvent] = []

    def add_event(self, event: DomainEvent):
        self._events.append(event)

    def get_events(self) -> List[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    # Business Invariants
    def validate_invariants(self):
        {invariant_checks}
        """,
        "relations": [
            ("REQUIRES", "DomainEvent"),
            ("GENERATES", "Repository"),
            ("GENERATES", "Service"),
            ("IMPLEMENTS", "DDDPattern")
        ]
    },

    {
        "name": "RepositoryPattern",
        "category": "ddd",
        "precision": 0.99,
        "code": """
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

class {EntityName}Repository(ABC):
    @abstractmethod
    async def find_by_id(self, id: UUID) -> Optional[{EntityName}]:
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[{EntityName}]:
        pass

    @abstractmethod
    async def save(self, entity: {EntityName}) -> {EntityName}:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass

class {EntityName}RepositoryImpl({EntityName}Repository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, id: UUID) -> Optional[{EntityName}]:
        result = await self.db.get({EntityName}Model, id)
        return result.to_domain() if result else None

    async def save(self, entity: {EntityName}) -> {EntityName}:
        model = {EntityName}Model.from_domain(entity)
        self.db.add(model)
        await self.db.commit()
        return model.to_domain()
        """,
        "relations": [
            ("REQUIRES", "AggregateRoot"),
            ("REQUIRES", "DatabaseSetup"),
            ("COMPATIBLE_WITH", "UnitOfWork"),
            ("GENERATES", "RepositoryImplementation")
        ]
    },

    # === API PATTERNS (10) ===
    {
        "name": "CRUDEndpoints",
        "category": "api",
        "precision": 0.97,
        "code": """
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/{resource_plural}", tags=["{resource_name}"])

@router.get("/", response_model=List[{ResourceName}Response])
async def list_{resource_plural}(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: {ResourceName}Service = Depends(get_{resource_name}_service)
):
    return await service.list(skip=skip, limit=limit)

@router.get("/{{id}}", response_model={ResourceName}Response)
async def get_{resource_name}(
    id: UUID,
    service: {ResourceName}Service = Depends(get_{resource_name}_service)
):
    result = await service.get(id)
    if not result:
        raise HTTPException(status_code=404, detail="{ResourceName} not found")
    return result

@router.post("/", response_model={ResourceName}Response, status_code=201)
async def create_{resource_name}(
    data: {ResourceName}CreateRequest,
    service: {ResourceName}Service = Depends(get_{resource_name}_service)
):
    return await service.create(data)

@router.put("/{{id}}", response_model={ResourceName}Response)
async def update_{resource_name}(
    id: UUID,
    data: {ResourceName}UpdateRequest,
    service: {ResourceName}Service = Depends(get_{resource_name}_service)
):
    result = await service.update(id, data)
    if not result:
        raise HTTPException(status_code=404, detail="{ResourceName} not found")
    return result

@router.delete("/{{id}}", status_code=204)
async def delete_{resource_name}(
    id: UUID,
    service: {ResourceName}Service = Depends(get_{resource_name}_service)
):
    if not await service.delete(id):
        raise HTTPException(status_code=404, detail="{ResourceName} not found")
        """,
        "relations": [
            ("REQUIRES", "Service"),
            ("REQUIRES", "DTOModels"),
            ("COMPATIBLE_WITH", "JWTAuthService"),
            ("GENERATES", "APIEndpoints")
        ]
    }
]
```

### Frontend - React/Next.js (25 Templates)

```python
react_template_nodes = [
    # === SETUP & CONFIG (8) ===
    {
        "name": "NextAppRouter",
        "category": "setup",
        "stack": "react",
        "code": """
// app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from './providers'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '{app_name}',
  description: '{description}',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={{inter.className}}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
        """,
        "relations": [
            ("REQUIRES", "Providers"),
            ("GENERATES", "Layout"),
            ("COMPATIBLE_WITH", "AuthContext")
        ]
    },

    {
        "name": "DataTable",
        "category": "component",
        "stack": "react",
        "precision": 0.95,
        "code": """
import { useState, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  ColumnDef,
} from '@tanstack/react-table'

interface DataTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  searchKey?: string
  pageSize?: number
}

export function DataTable<T>({
  data,
  columns,
  searchKey,
  pageSize = 10,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState([])
  const [filtering, setFiltering] = useState('')
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize,
  })

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter: filtering,
      pagination,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFiltering,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  return (
    <div className="space-y-4">
      {searchKey && (
        <input
          type="text"
          placeholder={`Search by ${searchKey}...`}
          value={filtering}
          onChange={(e) => setFiltering(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        />
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="text-left p-2 border-b cursor-pointer hover:bg-gray-50"
                  >
                    {header.column.columnDef.header}
                    {header.column.getIsSorted() && (
                      <span>{header.column.getIsSorted() === 'asc' ? ' ↑' : ' ↓'}</span>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="hover:bg-gray-50">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="p-2 border-b">
                    {cell.getValue()}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
        <span>
          Page {pagination.pageIndex + 1} of {table.getPageCount()}
        </span>
      </div>
    </div>
  )
}
        """,
        "relations": [
            ("REQUIRES", "TanStackTable"),
            ("COMPATIBLE_WITH", "APIClient"),
            ("GENERATES", "TableComponent")
        ]
    },

    {
        "name": "FormBuilder",
        "category": "component",
        "stack": "react",
        "precision": 0.94,
        "code": """
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

// Dynamic form schema
const createSchema = (fields: FieldConfig[]) => {
  const schemaObject: any = {}
  fields.forEach(field => {
    let validator = z.string()
    if (field.required) validator = validator.min(1, 'Required')
    if (field.type === 'email') validator = validator.email()
    if (field.type === 'number') validator = z.number()
    if (field.min) validator = validator.min(field.min)
    if (field.max) validator = validator.max(field.max)
    schemaObject[field.name] = validator
  })
  return z.object(schemaObject)
}

export function FormBuilder({ fields, onSubmit }: FormBuilderProps) {
  const schema = createSchema(fields)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm({
    resolver: zodResolver(schema),
  })

  const onSubmitForm = async (data: any) => {
    await onSubmit(data)
    reset()
  }

  return (
    <form onSubmit={handleSubmit(onSubmitForm)} className="space-y-4">
      {fields.map(field => (
        <div key={field.name}>
          <label className="block text-sm font-medium mb-1">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>

          {field.type === 'textarea' ? (
            <textarea
              {...register(field.name)}
              className="w-full px-3 py-2 border rounded-lg"
              rows={field.rows || 4}
            />
          ) : field.type === 'select' ? (
            <select
              {...register(field.name)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Select...</option>
              {field.options?.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={field.type || 'text'}
              {...register(field.name)}
              className="w-full px-3 py-2 border rounded-lg"
            />
          )}

          {errors[field.name] && (
            <p className="text-red-500 text-sm mt-1">
              {errors[field.name]?.message}
            </p>
          )}
        </div>
      ))}

      <button
        type="submit"
        disabled={isSubmitting}
        className="px-6 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
      >
        {isSubmitting ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  )
}
        """,
        "relations": [
            ("REQUIRES", "ReactHookForm"),
            ("REQUIRES", "Zod"),
            ("COMPATIBLE_WITH", "APIClient"),
            ("GENERATES", "FormComponent")
        ]
    }
]
```

---

## 🔄 SISTEMA DE EVOLUCIÓN

### Aprendizaje Continuo

```python
class TemplateEvolution:
    """
    Sistema que mejora templates basado en uso real
    """

    def track_usage(self, template_id: str, result: GenerationResult):
        """
        Registra cada uso de un template
        """
        query = """
        MATCH (t:Template {id: $template_id})
        SET t.usage_count = t.usage_count + 1
        SET t.last_used = datetime()

        WITH t
        CREATE (u:Usage {
            id: $usage_id,
            template_id: $template_id,
            timestamp: datetime(),
            success: $success,
            error_message: $error_message,
            execution_time: $execution_time,
            user_feedback: $user_feedback
        })

        CREATE (t)-[:USED_IN]->(u)

        // Update success rate
        WITH t,
             count{(t)-[:USED_IN]->(:Usage {success: true})} as successes,
             count{(t)-[:USED_IN]->(:Usage)} as total
        SET t.success_rate = toFloat(successes) / toFloat(total)

        RETURN t
        """

        return self.db.query(query, {
            'template_id': template_id,
            'usage_id': result.id,
            'success': result.success,
            'error_message': result.error_message,
            'execution_time': result.execution_time,
            'user_feedback': result.feedback
        })

    def evolve_template(self, template_id: str):
        """
        Mejora un template basado en patrones de uso
        """
        # 1. Analizar patrones de fallo
        failure_patterns = self.analyze_failures(template_id)

        # 2. Identificar mejoras comunes
        common_fixes = self.identify_common_fixes(template_id)

        # 3. Generar nueva versión
        if failure_patterns or common_fixes:
            new_version = self.generate_improved_version(
                template_id,
                failure_patterns,
                common_fixes
            )

            # 4. Crear nueva versión en el grafo
            self.create_new_version(template_id, new_version)
```

### Métricas de Calidad

```cypher
// Dashboard de templates más exitosos
MATCH (t:Template)
WHERE t.usage_count > 10
RETURN t.name, t.category, t.precision, t.success_rate, t.usage_count
ORDER BY t.success_rate DESC, t.usage_count DESC
LIMIT 20

// Templates que necesitan mejora
MATCH (t:Template)
WHERE t.success_rate < 0.9 AND t.usage_count > 5
RETURN t.name, t.success_rate, t.category
ORDER BY t.usage_count DESC

// Relaciones más comunes
MATCH (t1:Template)-[r:REQUIRES]->(t2:Template)
RETURN t1.name, t2.name, count(r) as frequency
ORDER BY frequency DESC
LIMIT 10
```

---

## 🔍 NAVEGACIÓN INTELIGENTE

### Búsqueda de Templates

```python
class TemplateNavigator:
    """
    Navega el grafo para encontrar templates óptimos
    """

    def find_templates_for_requirement(self, requirement):
        """
        Encuentra los mejores templates para un requirement
        """
        query = """
        // Buscar templates relevantes
        MATCH (t:Template)
        WHERE t.category IN $categories
        AND t.stack IN $stacks
        AND t.precision > 0.9

        // Verificar compatibilidad con contexto
        OPTIONAL MATCH (t)-[:COMPATIBLE_WITH]->(ctx:Template)
        WHERE ctx.name IN $context_templates

        // Calcular score
        WITH t,
             t.precision * 0.4 +
             t.success_rate * 0.3 +
             (t.usage_count / 1000.0) * 0.2 +
             count(ctx) * 0.1 as score

        RETURN t, score
        ORDER BY score DESC
        LIMIT 5
        """

        return self.db.query(query, {
            'categories': requirement.categories,
            'stacks': requirement.stacks,
            'context_templates': requirement.context
        })

    def find_dependency_chain(self, template_name):
        """
        Encuentra todas las dependencias de un template
        """
        query = """
        MATCH path = (t:Template {name: $template_name})-[:REQUIRES*]->(dep:Template)
        RETURN path
        ORDER BY length(path) DESC
        """

        return self.db.query(query, {'template_name': template_name})

    def validate_template_combination(self, template_names):
        """
        Valida si un conjunto de templates es compatible
        """
        query = """
        UNWIND $template_names AS name1
        UNWIND $template_names AS name2
        WHERE name1 < name2

        MATCH (t1:Template {name: name1})
        MATCH (t2:Template {name: name2})

        OPTIONAL MATCH conflict = (t1)-[:CONFLICTS_WITH]-(t2)

        RETURN
            name1,
            name2,
            CASE WHEN conflict IS NULL THEN true ELSE false END as compatible,
            conflict
        """

        return self.db.query(query, {'template_names': template_names})
```

### Generación Guiada por Grafo

```python
def generate_from_graph(self, requirements):
    """
    Pipeline completo de generación usando el grafo
    """
    # 1. Encontrar templates relevantes
    templates = self.navigator.find_templates_for_requirement(requirements)

    # 2. Resolver dependencias
    all_templates = []
    for template in templates:
        deps = self.navigator.find_dependency_chain(template.name)
        all_templates.extend(deps)

    # 3. Ordenar topológicamente
    ordered_templates = self.topological_sort(all_templates)

    # 4. Validar compatibilidad
    validation = self.navigator.validate_template_combination(
        [t.name for t in ordered_templates]
    )

    if not all(v.compatible for v in validation):
        # Resolver conflictos
        ordered_templates = self.resolve_conflicts(ordered_templates, validation)

    # 5. Generar código en orden
    generated_code = {}
    for template in ordered_templates:
        code = self.generate_from_template(template, requirements)
        generated_code[template.name] = code

        # Registrar uso
        self.evolution.track_usage(template.id, code)

    return generated_code
```

---

## 📊 CONFIGURACIÓN DE NEO4J

### Índices Críticos

```cypher
// Índices de búsqueda rápida
CREATE INDEX template_name IF NOT EXISTS FOR (t:Template) ON (t.name);
CREATE INDEX template_category IF NOT EXISTS FOR (t:Template) ON (t.category);
CREATE INDEX template_stack IF NOT EXISTS FOR (t:Template) ON (t.stack);
CREATE INDEX template_precision IF NOT EXISTS FOR (t:Template) ON (t.precision);

// Índice de texto completo
CREATE FULLTEXT INDEX template_search IF NOT EXISTS
FOR (t:Template)
ON EACH [t.name, t.description, t.tags];

// Constraints de integridad
CREATE CONSTRAINT unique_template_id IF NOT EXISTS
FOR (t:Template) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT unique_template_name_version IF NOT EXISTS
FOR (t:Template) REQUIRE (t.name, t.version) IS UNIQUE;
```

### Configuración de Performance

```yaml
neo4j_config:
  # Memoria
  dbms.memory.heap.initial_size: 8G
  dbms.memory.heap.max_size: 16G
  dbms.memory.pagecache.size: 10G

  # Query tuning
  cypher.min_replan_interval: 10s
  cypher.statistics_divergence_threshold: 0.9

  # Conexiones
  dbms.connector.bolt.thread_pool_max_size: 400
  dbms.connector.http.thread_pool_max_size: 200

  # Cache
  dbms.query_cache_size: 100
```

---

## 🚀 IMPLEMENTACIÓN PRÁCTICA

### Inicialización del Sistema

```python
class TemplateGraphSystem:
    """
    Sistema completo de templates en Neo4j
    """

    def __init__(self):
        self.db = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        self.navigator = TemplateNavigator(self.db)
        self.evolution = TemplateEvolution(self.db)
        self.generator = TemplateGenerator(self.db)

    def initialize_templates(self):
        """
        Carga inicial de los 55 templates
        """
        templates = load_template_definitions()

        with self.db.session() as session:
            for template in templates:
                # Crear nodo de template
                session.run("""
                    CREATE (t:Template {
                        id: $id,
                        name: $name,
                        category: $category,
                        stack: $stack,
                        code: $code,
                        precision: $precision,
                        usage_count: 0,
                        success_rate: 1.0,
                        created_at: datetime()
                    })
                """, template)

                # Crear relaciones
                for rel_type, target in template.relations:
                    session.run(f"""
                        MATCH (t1:Template {{name: $source}})
                        MATCH (t2:Template {{name: $target}})
                        CREATE (t1)-[:{rel_type}]->(t2)
                    """, source=template.name, target=target)

    def generate_project(self, requirements):
        """
        Genera un proyecto completo desde templates
        """
        # 1. Analizar requirements
        analysis = self.analyze_requirements(requirements)

        # 2. Generar desde grafo
        code = self.generate_from_graph(analysis)

        # 3. Validar resultado
        validation = self.validate_generated_code(code)

        # 4. Evolucionar templates
        for template_id, result in validation.items():
            self.evolution.track_usage(template_id, result)

        return code
```

---

## 📈 MÉTRICAS Y MONITOREO

### Dashboard Queries

```cypher
// Performance global del sistema
MATCH (t:Template)
RETURN
    avg(t.precision) as avg_precision,
    avg(t.success_rate) as avg_success,
    sum(t.usage_count) as total_uses,
    count(t) as total_templates

// Templates más usados esta semana
MATCH (t:Template)-[:USED_IN]->(u:Usage)
WHERE u.timestamp > datetime() - duration('P7D')
RETURN t.name, count(u) as uses_this_week
ORDER BY uses_this_week DESC
LIMIT 10

// Evolución de precisión
MATCH (t:Template)-[:EVOLVED_FROM*]->(original:Template)
RETURN original.name, t.version, t.precision
ORDER BY t.version
```

---

## 🎯 VENTAJAS DEL SISTEMA

### 1. Navegación Inteligente
- Encuentra automáticamente templates compatibles
- Resuelve dependencias sin intervención
- Detecta y previene conflictos

### 2. Evolución Continua
- Mejora con cada uso
- Aprende de errores pasados
- Se adapta a patrones del proyecto

### 3. Debugging Transparente
```cypher
// "¿Por qué se generó este código?"
MATCH path = (req:Requirement)-[*]-(t:Template {name: $template_used})
RETURN path
```

### 4. Reutilización Máxima
- Templates compartidos entre proyectos
- Conocimiento acumulativo
- Mejoras benefician a todos

---

## 🔮 ROADMAP

### Fase 1 (Mes 1)
- [ ] Implementar 20 templates core
- [ ] Setup Neo4j básico
- [ ] Navigator simple

### Fase 2 (Mes 2)
- [ ] Completar 55 templates
- [ ] Sistema de evolución
- [ ] Métricas básicas

### Fase 3 (Mes 3)
- [ ] Optimización de queries
- [ ] Dashboard de monitoreo
- [ ] API de templates

---

*Sistema de Templates como Grafos*
*DevMatrix 2.0*
*Neo4j + FastAPI + React*