# MGE V2 - Plan de Generación de Proyectos Completos

## Problema Actual

**Estado Actual (Incompleto):**
- ✅ Genera código de aplicación (models, services, routes)
- ❌ NO genera archivos de configuración
- ❌ NO genera Dockerfile
- ❌ NO genera docker-compose.yml
- ❌ NO genera .env / .env.example
- ❌ NO genera requirements.txt / package.json
- ❌ NO genera README.md con instrucciones
- ❌ NO genera .gitignore
- ❌ NO genera scripts de inicialización
- ❌ NO genera tests

**Resultado:** Proyecto no ejecutable, no deployable, no listo para GitHub

---

## Objetivo

Generar proyectos **100% completos y listos para producción**:
- ✅ Ejecutable con `docker-compose up` sin configuración adicional
- ✅ Listo para subir a GitHub con README completo
- ✅ Incluye toda la infraestructura necesaria
- ✅ Tests funcionales incluidos
- ✅ CI/CD pipelines opcionales

---

## Arquitectura de la Solución

### Fase 1: Extender MasterPlan Generator

**Componente:** `src/services/masterplan_generator.py`

**Cambios:**
1. Agregar fase "Infrastructure" al MasterPlan
2. Generar tasks para archivos de infraestructura
3. Detectar tipo de proyecto (FastAPI, React, Node.js, etc.)

**Nuevas Tasks de Infraestructura:**
```yaml
Infrastructure_Phase:
  - Task: "Generate Dockerfile for application"
  - Task: "Generate docker-compose.yml with services"
  - Task: "Generate .env.example with all required variables"
  - Task: "Generate requirements.txt / package.json"
  - Task: "Generate .gitignore for project type"
  - Task: "Generate README.md with setup instructions"
  - Task: "Generate database initialization scripts"
  - Task: "Generate health check endpoints"
  - Task: "Generate logging configuration"
  - Task: "Generate CI/CD pipeline (GitHub Actions)"
```

---

### Fase 2: Template System para Infraestructura

**Componente:** `src/services/infrastructure_template_service.py` (NUEVO)

**Responsabilidad:** Generar archivos de infraestructura basados en templates

#### 2.1 Template Categories

**A. Docker & Containerization**
```
templates/docker/
├── python_fastapi.dockerfile
├── nodejs_express.dockerfile
├── react_vite.dockerfile
├── nextjs.dockerfile
└── docker-compose.yml.j2
```

**B. Configuration Files**
```
templates/config/
├── python_requirements.txt.j2
├── nodejs_package.json.j2
├── env_fastapi.example.j2
├── env_nodejs.example.j2
└── env_react.example.j2
```

**C. Git & Documentation**
```
templates/git/
├── gitignore_python.txt
├── gitignore_nodejs.txt
├── gitignore_react.txt
├── README_fastapi.md.j2
├── README_express.md.j2
└── README_react.md.j2
```

**D. CI/CD Pipelines**
```
templates/cicd/
├── github_actions_python.yml.j2
├── github_actions_nodejs.yml.j2
└── gitlab_ci.yml.j2
```

**E. Database & Scripts**
```
templates/database/
├── postgres_init.sql.j2
├── mysql_init.sql.j2
└── mongodb_init.js.j2
```

---

### Fase 3: Infrastructure Generation Service

**Archivo:** `src/services/infrastructure_generation_service.py` (NUEVO)

**Clase:** `InfrastructureGenerationService`

```python
class InfrastructureGenerationService:
    """
    Genera archivos de infraestructura completos para el proyecto.

    Flow:
    1. Detectar tipo de proyecto (FastAPI, Express, React, etc.)
    2. Seleccionar templates apropiados
    3. Extraer información del MasterPlan (puertos, servicios, DBs)
    4. Generar archivos usando Jinja2 templates
    5. Guardar archivos en workspace
    """

    def __init__(self, db: Session):
        self.db = db
        self.template_loader = Jinja2TemplateLoader()

    async def generate_infrastructure(
        self,
        masterplan_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Genera TODOS los archivos de infraestructura.

        Returns:
            {
                "dockerfile": "path/to/Dockerfile",
                "docker_compose": "path/to/docker-compose.yml",
                "env_example": "path/to/.env.example",
                "readme": "path/to/README.md",
                "gitignore": "path/to/.gitignore",
                "requirements": "path/to/requirements.txt",
                "github_actions": "path/to/.github/workflows/ci.yml"
            }
        """
        pass

    def _detect_project_type(self, masterplan: MasterPlan) -> str:
        """Detecta tipo de proyecto basado en tasks y tecnologías."""
        pass

    def _extract_project_metadata(self, masterplan: MasterPlan) -> Dict:
        """
        Extrae metadata del proyecto:
        - Puerto de aplicación
        - Servicios requeridos (PostgreSQL, Redis, etc.)
        - Variables de entorno necesarias
        - Dependencias externas
        """
        pass

    def _generate_dockerfile(self, project_type: str, metadata: Dict) -> str:
        """Genera Dockerfile optimizado para el tipo de proyecto."""
        pass

    def _generate_docker_compose(self, metadata: Dict) -> str:
        """
        Genera docker-compose.yml con:
        - Aplicación
        - PostgreSQL (si es necesario)
        - Redis (si es necesario)
        - Networks y volumes
        """
        pass

    def _generate_env_example(self, metadata: Dict) -> str:
        """
        Genera .env.example con todas las variables necesarias:
        - DATABASE_URL
        - REDIS_URL
        - SECRET_KEY
        - API_KEYS
        - Puertos
        """
        pass

    def _generate_readme(self, masterplan: MasterPlan, metadata: Dict) -> str:
        """
        Genera README.md completo con:
        - Descripción del proyecto
        - Requisitos
        - Instrucciones de instalación (Docker)
        - Variables de entorno
        - Comandos útiles
        - Estructura del proyecto
        - API endpoints
        """
        pass
```

---

### Fase 4: Integración con MGE V2 Orchestration

**Archivo:** `src/services/mge_v2_orchestration_service.py`

**Modificaciones:**

```python
async def orchestrate_from_discovery(self, discovery_id, session_id, user_id):
    # ... código existente ...

    # Step 6: Generate Infrastructure (NUEVO)
    yield {
        "type": "status",
        "phase": "infrastructure_generation",
        "message": "Generating project infrastructure (Docker, configs, docs)...",
        "timestamp": datetime.utcnow().isoformat()
    }

    from src.services.infrastructure_generation_service import InfrastructureGenerationService
    infra_service = InfrastructureGenerationService(db=self.db)

    infra_result = await infra_service.generate_infrastructure(
        masterplan_id=masterplan_id
    )

    if infra_result["success"]:
        yield {
            "type": "status",
            "phase": "infrastructure_generation",
            "message": f"Infrastructure generated: {len(infra_result['files'])} files",
            "files": infra_result['files'],
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Estructura Completa del Proyecto Generado

### Proyecto FastAPI (Ejemplo)

```
todo-list-rest-api/
├── .github/
│   └── workflows/
│       └── ci.yml                    ✅ GitHub Actions CI/CD
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py    ✅ Generated migrations
│   └── env.py                        ✅ Alembic config
├── src/
│   ├── api/                          ✅ Generated application code
│   ├── models/
│   ├── services/
│   ├── domain/
│   ├── infrastructure/
│   └── main.py
├── tests/                            ✅ Generated tests
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_todos.py
├── scripts/                          ✅ Utility scripts
│   ├── init_db.sh
│   └── run_tests.sh
├── .env.example                      ✅ Environment template
├── .gitignore                        ✅ Git ignore rules
├── Dockerfile                        ✅ Multi-stage Docker build
├── docker-compose.yml                ✅ Full stack setup
├── requirements.txt                  ✅ Python dependencies
├── pyproject.toml                    ✅ Python project config
├── README.md                         ✅ Complete documentation
└── LICENSE                           ✅ Optional license file
```

---

## Templates Detallados

### Template 1: Dockerfile (FastAPI)

```dockerfile
# templates/docker/python_fastapi.dockerfile
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE {{ port }}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:{{ port }}/health || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "{{ port }}"]
```

### Template 2: docker-compose.yml

```yaml
# templates/docker/docker-compose.yml.j2
version: '3.8'

services:
  app:
    build: .
    container_name: {{ project_name }}-app
    ports:
      - "{{ app_port }}:{{ app_port }}"
    environment:
      - DATABASE_URL=postgresql://{{ db_user }}:{{ db_password }}@postgres:5432/{{ db_name }}
      {% if needs_redis %}
      - REDIS_URL=redis://redis:6379/0
      {% endif %}
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    depends_on:
      postgres:
        condition: service_healthy
      {% if needs_redis %}
      redis:
        condition: service_healthy
      {% endif %}
    volumes:
      - ./src:/app/src
    networks:
      - {{ project_name }}-network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: {{ project_name }}-postgres
    environment:
      - POSTGRES_USER={{ db_user }}
      - POSTGRES_PASSWORD={{ db_password }}
      - POSTGRES_DB={{ db_name }}
    ports:
      - "{{ db_port }}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ db_user }}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - {{ project_name }}-network
    restart: unless-stopped

  {% if needs_redis %}
  redis:
    image: redis:7-alpine
    container_name: {{ project_name }}-redis
    ports:
      - "{{ redis_port }}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - {{ project_name }}-network
    restart: unless-stopped
  {% endif %}

volumes:
  postgres_data:

networks:
  {{ project_name }}-network:
    driver: bridge
```

### Template 3: README.md

```markdown
# templates/git/README_fastapi.md.j2
# {{ project_name }}

{{ project_description }}

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd {{ project_slug }}
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start services:
```bash
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose exec app alembic upgrade head
```

5. Access the application:
- API: http://localhost:{{ app_port }}
- API Docs: http://localhost:{{ app_port }}/docs
- ReDoc: http://localhost:{{ app_port }}/redoc

## 📁 Project Structure

```
{{ project_slug }}/
├── src/
│   ├── api/          # API routes and schemas
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── main.py       # Application entry point
├── tests/            # Test files
├── alembic/          # Database migrations
└── scripts/          # Utility scripts
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secret key for JWT tokens
{% if needs_redis %}
- `REDIS_URL`: Redis connection string
{% endif %}

## 🧪 Testing

Run tests:
```bash
docker-compose exec app pytest
```

Run tests with coverage:
```bash
docker-compose exec app pytest --cov=src tests/
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user

{% for endpoint in api_endpoints %}
### {{ endpoint.category }}
{% for route in endpoint.routes %}
- `{{ route.method }} {{ route.path }}` - {{ route.description }}
{% endfor %}
{% endfor %}

## 🛠️ Development

### Running Locally

```bash
docker-compose up
```

### Database Migrations

Create new migration:
```bash
docker-compose exec app alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
docker-compose exec app alembic upgrade head
```

### Logs

View logs:
```bash
docker-compose logs -f app
```

## 📝 License

{{ license }}

## 🤝 Contributing

Generated with MGE V2 - MasterPlan Generation Engine
```

### Template 4: .env.example

```bash
# templates/config/env_fastapi.example.j2
# Application
PROJECT_NAME={{ project_name }}
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT={{ app_port }}

# Database
DATABASE_URL=postgresql://{{ db_user }}:{{ db_password }}@postgres:5432/{{ db_name }}
DB_ECHO=false
DB_POOL_SIZE=5

# Authentication
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

{% if needs_redis %}
# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300
{% endif %}

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

{% for var in custom_env_vars %}
# {{ var.category }}
{{ var.name }}={{ var.default_value }}
{% endfor %}
```

---

## Plan de Implementación

### Sprint 1: Template System (Semana 1)
- [ ] Crear directorio `templates/` con estructura
- [ ] Implementar templates para FastAPI
- [ ] Implementar templates para Node.js/Express
- [ ] Implementar templates para React/Next.js
- [ ] Tests unitarios de templates

### Sprint 2: Infrastructure Service (Semana 2)
- [ ] Crear `InfrastructureGenerationService`
- [ ] Implementar detección de tipo de proyecto
- [ ] Implementar extracción de metadata
- [ ] Implementar generación de archivos
- [ ] Tests de integración

### Sprint 3: Integration (Semana 3)
- [ ] Integrar con `MGE_V2_OrchestrationService`
- [ ] Agregar fase "Infrastructure" al MasterPlan
- [ ] Actualizar `FileWriterService` para archivos raíz
- [ ] Tests E2E completos

### Sprint 4: Validation & Polish (Semana 4)
- [ ] Validar proyectos generados (docker-compose up funciona)
- [ ] Agregar más templates (Go, Rust, etc.)
- [ ] Documentación completa
- [ ] Performance optimization

---

## Cambios Necesarios

### 1. `src/services/masterplan_generator.py`

```python
# Agregar fase Infrastructure
INFRASTRUCTURE_PHASE = {
    "name": "Infrastructure & Configuration",
    "order": 99,  # Última fase
    "tasks": [
        "Generate Dockerfile optimized for production",
        "Generate docker-compose.yml with all services",
        "Generate .env.example with documented variables",
        "Generate requirements.txt / package.json",
        "Generate .gitignore for project type",
        "Generate comprehensive README.md",
        "Generate database initialization scripts",
        "Generate CI/CD pipeline configuration",
        "Generate test configuration files",
        "Generate logging and monitoring setup"
    ]
}
```

### 2. `src/services/file_writer_service.py`

```python
# Agregar soporte para archivos en raíz del proyecto
def write_atoms_to_files(self, masterplan_id, workspace_name):
    # ... código existente ...

    # NUEVO: Escribir archivos de infraestructura en raíz
    infrastructure_files = self._get_infrastructure_files(masterplan_id)
    for file_name, content in infrastructure_files.items():
        root_file_path = workspace_path / file_name  # Raíz, no src/
        root_file_path.write_text(content, encoding='utf-8')
```

### 3. `src/models.py`

```python
# Agregar columna para tipo de archivo en MasterPlanTask
class MasterPlanTask(Base):
    # ... campos existentes ...

    file_location = Column(String, nullable=True)  # "src", "root", "scripts", etc.
    is_infrastructure = Column(Boolean, default=False)
```

---

## Validación de Éxito

### Checklist de Proyecto Completo

Un proyecto está completo cuando:

- [ ] `docker-compose up` levanta todo sin errores
- [ ] La aplicación responde en el puerto especificado
- [ ] Health check endpoint retorna 200 OK
- [ ] Database migrations se aplican correctamente
- [ ] Tests pasan sin errores
- [ ] README.md tiene instrucciones claras y completas
- [ ] `.env.example` tiene todas las variables necesarias
- [ ] `.gitignore` previene commits de archivos sensibles
- [ ] GitHub Actions CI pasa (si está configurado)
- [ ] Proyecto puede clonarse y ejecutarse en otra máquina sin cambios

---

## Métricas de Éxito

| Métrica | Objetivo |
|---------|----------|
| Tiempo de generación total | < 90 segundos |
| Proyectos ejecutables al primer intento | > 95% |
| Archivos de infraestructura generados | 100% completos |
| Tests incluidos y pasando | > 80% coverage |
| README accuracy | 100% instrucciones correctas |

---

## Próximos Pasos

1. **Revisar y aprobar este plan**
2. **Priorizar tipo de proyecto** (empezar con FastAPI o Node.js)
3. **Crear templates** en `templates/` directory
4. **Implementar `InfrastructureGenerationService`**
5. **Integrar con pipeline MGE V2**
6. **Test E2E con proyecto completo**

---

## Notas Adicionales

### Consideraciones de Seguridad

- `.env.example` NO debe contener valores reales
- Generar SECRET_KEY único por proyecto
- Incluir instrucciones de seguridad en README
- Configurar permisos apropiados en scripts

### Performance

- Templates deben cachearse en memoria
- Generación paralela de archivos de infraestructura
- Validación lazy de templates

### Extensibilidad

- Sistema de plugins para templates custom
- Templates community-contributed
- Soporte para frameworks custom del usuario
