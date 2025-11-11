# Infrastructure Generation System

## Overview

El sistema de generación de infraestructura de MGE V2 produce **proyectos completos y listos para desplegar**, no solo código fuente. Cada proyecto generado incluye toda la configuración necesaria para ejecutarse con `docker-compose up` y estar listo para subir a GitHub.

## ¿Qué genera?

### Archivos de Infraestructura (6 archivos)

1. **Dockerfile** - Multi-stage build optimizado para producción
2. **docker-compose.yml** - Orquestación completa (app + DB + Redis)
3. **.env.example** - Variables de entorno documentadas
4. **requirements.txt** - Dependencias con versiones pinneadas
5. **README.md** - Documentación completa del proyecto
6. **.gitignore** - Exclusiones estándar para Python/Node.js

### Tipos de Proyecto Soportados

- ✅ **FastAPI** - API REST con PostgreSQL + Redis (opcional)
- 🔄 **Express** - Node.js API (próximamente)
- 🔄 **React** - Frontend SPA (próximamente)
- 🔄 **Next.js** - Full-stack framework (próximamente)

## Quick Start

### 1. Generar Proyecto con MGE V2

```python
# El sistema detecta automáticamente el tipo de proyecto
# y genera toda la infraestructura necesaria
masterplan_id = "..."
workspace_path = Path("/workspace/my-project")

await orchestrator.orchestrate_masterplan_execution(
    masterplan_id=masterplan_id,
    workspace_path=workspace_path
)
```

### 2. Ejecutar Proyecto Generado

```bash
cd /workspace/my-project

# 1. Copiar configuración
cp .env.example .env

# 2. Editar credenciales (opcional en desarrollo)
nano .env

# 3. Levantar servicios
docker-compose up -d

# 4. Ver logs
docker-compose logs -f app

# ✅ API disponible en http://localhost:8000
```

### 3. Verificar Funcionamiento

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

## Características Clave

### 🎯 Auto-Detección

El sistema analiza automáticamente:

- **Tipo de proyecto** - FastAPI, Express, React (keywords en tasks)
- **Base de datos** - PostgreSQL, MySQL, MongoDB (análisis de dependencias)
- **Servicios adicionales** - Redis (detección de palabras clave "cache", "redis")
- **Puertos** - 8000 para FastAPI, 3000 para Express/React
- **Dependencias** - Extracción de imports y requirements

### 🔐 Seguridad por Defecto

- Contraseñas generadas con `secrets.token_hex(16)`
- `.env.example` sin credenciales reales
- `.gitignore` protege archivos sensibles
- Health checks en todos los servicios
- Usuario no-root en containers de producción

### 🚀 Optimización para Producción

- **Multi-stage builds** - Imágenes optimizadas
- **Health checks** - Restart automático de servicios
- **Volume persistence** - Datos de DB preservados
- **Networking** - Red aislada por proyecto
- **Resource limits** - Control de memoria y CPU

### 📦 Docker Compose Completo

```yaml
services:
  app:          # Aplicación principal
  postgres:     # Base de datos
  redis:        # Cache (condicional)

volumes:
  postgres-data:  # Persistencia

networks:
  project-network:  # Aislamiento
```

## Integración con MGE V2

El sistema se ejecuta como **Step 6** en el pipeline de generación:

```
Phase 1: Discovery          → Análisis del dominio
Phase 2: Atomization        → Descomposición en tareas
Phase 3: MasterPlan         → Plan de implementación
Phase 4: Execution          → Generación de código
Phase 5: File Writing       → Escritura de archivos
Phase 6: Infrastructure ⭐  → Generación de infraestructura (NUEVO)
```

## Estructura de Templates

```
templates/
├── docker/
│   ├── python_fastapi.dockerfile      # FastAPI multi-stage
│   └── docker-compose.yml.j2          # Orquestación
├── config/
│   ├── env_fastapi.example.j2         # Variables de entorno
│   └── requirements_fastapi.txt.j2    # Dependencias Python
└── git/
    ├── README_fastapi.md.j2           # Documentación
    └── gitignore_python.txt           # Exclusiones
```

Todos los templates usan **Jinja2** para renderizado dinámico.

## Resultados de E2E Test

```
✓ Generation completed in 25s
✓ Infrastructure generated: 6 files (fastapi)
✓ Total files: 24 (18 code + 6 infrastructure)
✓ Project ready for docker-compose up
```

## Próximos Pasos

1. **[Architecture](./architecture.md)** - Diseño técnico detallado
2. **[Templates Guide](./templates-guide.md)** - Cómo usar y personalizar templates
3. **[Usage Examples](./usage-examples.md)** - Ejemplos completos de proyectos generados
4. **[Troubleshooting](./troubleshooting.md)** - Problemas comunes y soluciones

## Estado Actual

- ✅ **Implementado** - Sistema funcional y testeado
- ✅ **FastAPI completo** - Todos los templates necesarios
- 🔄 **Express/React** - En desarrollo
- 📋 **CI/CD templates** - Planificado (GitHub Actions, GitLab CI)
