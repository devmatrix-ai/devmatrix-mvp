# MasterPlan: Diseño del Sistema de Planificación Central

**Fecha**: 2025-10-20
**Estado**: ✅ Diseño completado + Arquitectura computacional definida
**Autor**: Ariel Ghysels + Claude
**Docs relacionados**: `LLM_COMPUTATIONAL_ARCHITECTURE.md`

---

## 🎯 Visión

El **MasterPlan** es el "cerebro central" de cada proyecto en DevMatrix. Mantiene **toda la verdad** sobre el estado del desarrollo:

- Stack tecnológico elegido
- Lógica de negocio y reglas del dominio
- Entidades y modelos de datos
- Plan de implementación con tareas atómicas
- Dependencias entre tareas
- Estado actual de cada tarea
- Resultados y outputs generados

### El Problema que Resuelve

Sin MasterPlan, el sistema actual:
- No tiene memoria estructurada del plan general
- Las tareas se ejecutan pero no hay tracking centralizado
- Si el servidor se reinicia, se pierde el contexto del proyecto
- El usuario no puede ver fácilmente "qué falta hacer"
- No hay forma de modificar el plan a mitad de ejecución

Con MasterPlan:
- **Persistencia**: El plan sobrevive reinicios
- **Visibilidad**: El usuario ve el progreso en tiempo real
- **Control**: El usuario puede aprobar/modificar antes de ejecutar
- **Trazabilidad**: Cada decisión y resultado queda registrado
- **Evolución**: El plan puede actualizarse con nuevos features

---

## 📦 Componentes del MasterPlan

### 1. Metadata General

```json
{
  "masterplan_id": "mp_uuid_1234",
  "workspace_id": "ws_uuid_5678",
  "conversation_id": "conv_uuid_9012",
  "project_name": "User Management API",
  "created_at": "2025-01-20T10:30:00Z",
  "updated_at": "2025-01-20T10:45:00Z",
  "status": "in_progress",  // draft | approved | in_progress | completed | failed
  "user_request_original": "Crea una API REST para gestión de usuarios con autenticación JWT"
}
```

### 2. Stack Tecnológico

```json
{
  "stack": {
    "backend": {
      "framework": "FastAPI",
      "version": "0.104.0",
      "justification": "Elegido por ser moderno, async, y con validación automática"
    },
    "database": {
      "primary": "PostgreSQL",
      "version": "16",
      "orm": "SQLAlchemy",
      "migrations": "Alembic"
    },
    "authentication": {
      "method": "JWT",
      "library": "python-jose"
    },
    "testing": {
      "framework": "pytest",
      "coverage_target": 80
    },
    "deployment": {
      "containerization": "Docker",
      "orchestration": "docker-compose"
    }
  },
  "dependencies": [
    "fastapi>=0.104.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=7.4.0"
  ]
}
```

### 3. Lógica de Negocio

```json
{
  "business_logic": {
    "domain": "User Management & Authentication",
    "rules": [
      {
        "id": "br_001",
        "description": "Users must have unique email addresses",
        "enforcement": "database_constraint"
      },
      {
        "id": "br_002",
        "description": "Passwords must be hashed with bcrypt",
        "enforcement": "application_layer"
      },
      {
        "id": "br_003",
        "description": "JWT tokens expire after 24 hours",
        "enforcement": "application_layer"
      },
      {
        "id": "br_004",
        "description": "Only admin users can delete other users",
        "enforcement": "authorization_middleware"
      }
    ],
    "workflows": [
      {
        "name": "User Registration",
        "steps": [
          "Validate email format",
          "Check email uniqueness",
          "Hash password",
          "Create user record",
          "Send welcome email (future)"
        ]
      },
      {
        "name": "User Login",
        "steps": [
          "Validate credentials",
          "Generate JWT token",
          "Return token to client"
        ]
      }
    ]
  }
}
```

### 4. Entidades del Dominio

```json
{
  "entities": [
    {
      "name": "User",
      "type": "model",
      "description": "Represents a system user",
      "attributes": [
        {
          "name": "id",
          "type": "UUID",
          "primary_key": true,
          "auto_generate": true
        },
        {
          "name": "email",
          "type": "String",
          "max_length": 255,
          "unique": true,
          "nullable": false,
          "indexed": true
        },
        {
          "name": "password_hash",
          "type": "String",
          "max_length": 255,
          "nullable": false
        },
        {
          "name": "full_name",
          "type": "String",
          "max_length": 255,
          "nullable": true
        },
        {
          "name": "is_active",
          "type": "Boolean",
          "default": true
        },
        {
          "name": "is_superuser",
          "type": "Boolean",
          "default": false
        },
        {
          "name": "created_at",
          "type": "DateTime",
          "auto_now_add": true
        },
        {
          "name": "updated_at",
          "type": "DateTime",
          "auto_now": true
        }
      ],
      "relations": [
        {
          "name": "role",
          "type": "many_to_one",
          "target_entity": "Role",
          "foreign_key": "role_id"
        }
      ],
      "validations": [
        "email must be valid format",
        "password_hash must not be empty"
      ]
    },
    {
      "name": "Role",
      "type": "model",
      "description": "User roles for authorization",
      "attributes": [
        {
          "name": "id",
          "type": "UUID",
          "primary_key": true
        },
        {
          "name": "name",
          "type": "String",
          "max_length": 50,
          "unique": true
        },
        {
          "name": "permissions",
          "type": "JSON",
          "description": "List of permission strings"
        }
      ],
      "relations": [
        {
          "name": "users",
          "type": "one_to_many",
          "target_entity": "User"
        }
      ]
    }
  ]
}
```

### 5. Jerarquía de Trabajo (Phases → Milestones → Tasks → Subtasks)

#### Estructura Jerárquica Completa

```json
{
  "masterplan_hierarchy": {
    "phases": [
      {
        "phase_id": "phase_01",
        "name": "Foundation & Infrastructure",
        "description": "Setup project structure, database, and core infrastructure",
        "order": 1,
        "status": "in_progress",
        "estimated_duration_hours": 3,

        "milestones": [
          {
            "milestone_id": "milestone_01_01",
            "name": "Project Structure Setup",
            "description": "Initialize project with directory structure and core dependencies",
            "phase_id": "phase_01",
            "order": 1,
            "status": "completed",
            "estimated_duration_hours": 0.5,
            "acceptance_criteria": [
              "Project structure follows best practices",
              "All required directories created",
              "requirements.txt with core dependencies",
              "Environment configuration template (.env.example)"
            ],

            "tasks": [
              {
                "task_id": "task_001",
                "milestone_id": "milestone_01_01",
                "title": "Create Project Directory Structure",
                "description": "Initialize FastAPI project with proper directory structure and __init__.py files",
                "task_type": "setup",
                "priority": "critical",
                "complexity": "low",
                "estimated_time_minutes": 5,
                "story_points": 1,

                "acceptance_criteria": [
                  "Directory structure matches project template",
                  "All __init__.py files created",
                  "README.md with project overview"
                ],

                "labels": ["setup", "infrastructure", "foundation"],
                "assigned_agent": "ImplementationAgent",
                "depends_on": [],
                "blocks": ["task_002", "task_003"],

                "status": "completed",
                "status_history": [
                  {"status": "pending", "timestamp": "2025-01-20T10:30:00Z"},
                  {"status": "in_progress", "timestamp": "2025-01-20T10:32:00Z"},
                  {"status": "completed", "timestamp": "2025-01-20T10:35:00Z"}
                ],

                "output": {
                  "files_created": [
                    "src/__init__.py",
                    "src/api/__init__.py",
                    "src/models/__init__.py",
                    "src/services/__init__.py",
                    "README.md"
                  ],
                  "lines_of_code": 45
                },

                "jira_mapping": {
                  "issue_type": "Story",
                  "epic_link": "phase_01",
                  "fix_version": "milestone_01_01"
                },

                "subtasks": []
              },
              {
                "task_id": "task_002",
                "milestone_id": "milestone_01_01",
                "title": "Setup Dependencies and Requirements",
                "description": "Create requirements.txt with all necessary dependencies (FastAPI, SQLAlchemy, etc.)",
                "task_type": "setup",
                "priority": "critical",
                "complexity": "low",
                "estimated_time_minutes": 3,
                "story_points": 1,

                "acceptance_criteria": [
                  "requirements.txt with pinned versions",
                  "Dev requirements separated (requirements-dev.txt)",
                  "Dependencies install without errors"
                ],

                "labels": ["setup", "dependencies"],
                "assigned_agent": "ImplementationAgent",
                "depends_on": ["task_001"],
                "blocks": ["task_003", "task_004"],

                "status": "completed",

                "jira_mapping": {
                  "issue_type": "Story",
                  "epic_link": "phase_01",
                  "fix_version": "milestone_01_01"
                },

                "subtasks": []
              }
            ]
          },

          {
            "milestone_id": "milestone_01_02",
            "name": "Database Layer Complete",
            "description": "Database connection, models, and migrations configured",
            "phase_id": "phase_01",
            "order": 2,
            "status": "in_progress",
            "estimated_duration_hours": 2,
            "acceptance_criteria": [
              "Database connection working",
              "All models defined with proper relationships",
              "Alembic migrations working",
              "Seed data script available"
            ],

            "tasks": [
              {
                "task_id": "task_003",
                "milestone_id": "milestone_01_02",
                "title": "Setup Database Configuration",
                "description": "Configure SQLAlchemy database connection, session management, and Base class",
                "task_type": "implementation",
                "priority": "critical",
                "complexity": "medium",
                "estimated_time_minutes": 12,
                "story_points": 3,

                "acceptance_criteria": [
                  "Database connection string configurable via env",
                  "Session management with context manager",
                  "Connection pooling configured",
                  "Base class for all models defined"
                ],

                "labels": ["database", "infrastructure", "sqlalchemy"],
                "assigned_agent": "ImplementationAgent",
                "depends_on": ["task_002"],
                "blocks": ["task_004", "task_005"],

                "status": "in_progress",

                "jira_mapping": {
                  "issue_type": "Story",
                  "epic_link": "phase_01",
                  "fix_version": "milestone_01_02"
                },

                "subtasks": [
                  {
                    "subtask_id": "subtask_003_01",
                    "title": "Create database/base.py with Base class",
                    "estimated_minutes": 3,
                    "status": "completed"
                  },
                  {
                    "subtask_id": "subtask_003_02",
                    "title": "Create database/connection.py with session factory",
                    "estimated_minutes": 5,
                    "status": "completed"
                  },
                  {
                    "subtask_id": "subtask_003_03",
                    "title": "Create database/config.py with settings",
                    "estimated_minutes": 4,
                    "status": "in_progress"
                  }
                ]
              },

              {
                "task_id": "task_004",
                "milestone_id": "milestone_01_02",
                "title": "Implement User SQLAlchemy Model",
                "description": "Create User model with all attributes, relationships, and validations",
                "task_type": "implementation",
                "priority": "high",
                "complexity": "medium",
                "estimated_time_minutes": 15,
                "story_points": 5,

                "acceptance_criteria": [
                  "User model inherits from Base",
                  "All fields properly typed (UUID, String, DateTime, etc.)",
                  "Email field has unique constraint and index",
                  "Password hash field never exposes plaintext",
                  "Relationships to Role defined",
                  "Timestamps (created_at, updated_at) auto-managed",
                  "Model has __repr__ method"
                ],

                "labels": ["model", "user", "authentication"],
                "assigned_agent": "ImplementationAgent",
                "depends_on": ["task_003"],
                "blocks": ["task_006", "task_007"],

                "status": "pending",

                "jira_mapping": {
                  "issue_type": "Story",
                  "epic_link": "phase_01",
                  "fix_version": "milestone_01_02"
                },

                "subtasks": [
                  {
                    "subtask_id": "subtask_004_01",
                    "title": "Define User table schema with all fields",
                    "estimated_minutes": 8,
                    "status": "pending"
                  },
                  {
                    "subtask_id": "subtask_004_02",
                    "title": "Add relationships and indexes",
                    "estimated_minutes": 4,
                    "status": "pending"
                  },
                  {
                    "subtask_id": "subtask_004_03",
                    "title": "Add validation methods and __repr__",
                    "estimated_minutes": 3,
                    "status": "pending"
                  }
                ]
              }
            ]
          }
        ]
      },

      {
        "phase_id": "phase_02",
        "name": "Authentication & Authorization",
        "description": "Implement complete authentication system with JWT and role-based access control",
        "order": 2,
        "status": "pending",
        "estimated_duration_hours": 6,
        "depends_on_phases": ["phase_01"],

        "milestones": [
          {
            "milestone_id": "milestone_02_01",
            "name": "JWT Authentication Working",
            "description": "Users can register, login, and receive JWT tokens",
            "phase_id": "phase_02",
            "order": 1,
            "status": "pending",
            "estimated_duration_hours": 3,
            "acceptance_criteria": [
              "Users can register with email/password",
              "Users can login and receive JWT token",
              "JWT tokens can be validated",
              "Refresh tokens working",
              "Token expiration handled properly"
            ],

            "tasks": [
              {
                "task_id": "task_010",
                "milestone_id": "milestone_02_01",
                "title": "Implement JWT Token Service",
                "description": "Create service for generating, validating, and refreshing JWT tokens",
                "task_type": "implementation",
                "priority": "critical",
                "complexity": "high",
                "estimated_time_minutes": 20,
                "story_points": 8,

                "acceptance_criteria": [
                  "generate_token(user) creates valid JWT",
                  "Token includes user_id, email, role in claims",
                  "Token expiration configurable via env",
                  "verify_token() validates signature and expiration",
                  "Refresh token flow implemented",
                  "All security best practices followed"
                ],

                "labels": ["authentication", "jwt", "security"],
                "assigned_agent": "ImplementationAgent",
                "depends_on": ["task_004"],
                "blocks": ["task_011", "task_012"],

                "status": "pending",

                "jira_mapping": {
                  "issue_type": "Story",
                  "epic_link": "phase_02",
                  "fix_version": "milestone_02_01"
                },

                "subtasks": [
                  {
                    "subtask_id": "subtask_010_01",
                    "title": "Implement token generation with python-jose",
                    "estimated_minutes": 10,
                    "status": "pending"
                  },
                  {
                    "subtask_id": "subtask_010_02",
                    "title": "Implement token validation and claims extraction",
                    "estimated_minutes": 6,
                    "status": "pending"
                  },
                  {
                    "subtask_id": "subtask_010_03",
                    "title": "Implement refresh token logic",
                    "estimated_minutes": 4,
                    "status": "pending"
                  }
                ]
              }
            ]
          },

          {
            "milestone_id": "milestone_02_02",
            "name": "Role-Based Access Control (RBAC) Complete",
            "description": "Authorization system with roles and permissions working",
            "phase_id": "phase_02",
            "order": 2,
            "status": "pending",
            "estimated_duration_hours": 3,
            "acceptance_criteria": [
              "Roles can be assigned to users",
              "Permissions checked on protected endpoints",
              "Authorization middleware working",
              "Admin-only endpoints protected"
            ],

            "tasks": []
          }
        ]
      },

      {
        "phase_id": "phase_03",
        "name": "API Endpoints Implementation",
        "description": "Implement all CRUD endpoints for user management",
        "order": 3,
        "status": "pending",
        "estimated_duration_hours": 5,
        "depends_on_phases": ["phase_02"],

        "milestones": []
      },

      {
        "phase_id": "phase_04",
        "name": "Testing & Quality Assurance",
        "description": "Comprehensive test suite and code quality validation",
        "order": 4,
        "status": "pending",
        "estimated_duration_hours": 8,
        "depends_on_phases": ["phase_03"],

        "milestones": []
      },

      {
        "phase_id": "phase_05",
        "name": "Documentation & Deployment",
        "description": "API documentation, deployment scripts, and production readiness",
        "order": 5,
        "status": "pending",
        "estimated_duration_hours": 4,
        "depends_on_phases": ["phase_04"],

        "milestones": []
      }
    ]
  }
}
```

#### Mapeo a Jira

| MasterPlan | Jira Equivalent | Descripción |
|------------|----------------|-------------|
| **Phase** | **Epic** o **Initiative** | Alto nivel, agrupa múltiples milestones |
| **Milestone** | **Feature** o **Fix Version** | Entrega tangible, agrupa tareas relacionadas |
| **Task** | **Story** o **Task** | Tarea atómica ejecutable (1 archivo, 200-300 LOC) |
| **Subtask** | **Subtask** | Pasos opcionales dentro de una tarea compleja |

#### Campos Adicionales para Jira Export

```json
{
  "jira_export_fields": {
    "task_level": {
      "issue_type": "Story",
      "summary": "task.title",
      "description": "task.description + acceptance_criteria",
      "epic_link": "phase.phase_id",
      "fix_version": "milestone.milestone_id",
      "labels": "task.labels",
      "story_points": "task.story_points",
      "priority": "task.priority",
      "assignee": "task.assigned_agent (mapped to Jira user)",
      "estimated_time": "task.estimated_time_minutes",
      "depends_on": "Linked Issues (blocks/is blocked by)",
      "custom_fields": {
        "complexity": "task.complexity",
        "task_type": "task.task_type",
        "agent_assigned": "task.assigned_agent"
      }
    },

    "milestone_level": {
      "issue_type": "Feature",
      "summary": "milestone.name",
      "description": "milestone.description + acceptance_criteria",
      "epic_link": "phase.phase_id",
      "fix_version": "milestone.milestone_id"
    },

    "phase_level": {
      "issue_type": "Epic",
      "summary": "phase.name",
      "description": "phase.description",
      "epic_name": "phase.name"
    }
  }
}
```

### 6. Exportación a Jira

#### Servicio de Exportación

```python
# src/services/jira_export_service.py

from typing import List, Dict, Optional
import requests
from dataclasses import dataclass

@dataclass
class JiraConfig:
    """Configuración para conexión a Jira."""
    base_url: str  # https://your-domain.atlassian.net
    email: str
    api_token: str
    project_key: str  # ej: "DEVMX"

class JiraExportService:
    """
    Servicio para exportar MasterPlan a Jira.
    """

    def __init__(self, config: JiraConfig):
        self.config = config
        self.auth = (config.email, config.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def export_masterplan(self, masterplan: MasterPlan) -> Dict[str, str]:
        """
        Exporta MasterPlan completo a Jira.

        Returns:
            Mapeo de IDs locales → IDs de Jira
            {
                "phase_01": "DEVMX-123",
                "milestone_01_01": "DEVMX-124",
                "task_001": "DEVMX-125",
                ...
            }
        """
        id_mapping = {}

        # 1. Crear Epics (Phases)
        for phase in masterplan.phases:
            epic_key = await self.create_epic(phase)
            id_mapping[phase.phase_id] = epic_key

        # 2. Crear Fix Versions (Milestones)
        for phase in masterplan.phases:
            for milestone in phase.milestones:
                version_id = await self.create_version(milestone)
                id_mapping[milestone.milestone_id] = version_id

        # 3. Crear Stories (Tasks)
        for phase in masterplan.phases:
            epic_key = id_mapping[phase.phase_id]
            for milestone in phase.milestones:
                version_id = id_mapping[milestone.milestone_id]
                for task in milestone.tasks:
                    story_key = await self.create_story(
                        task=task,
                        epic_key=epic_key,
                        fix_version_id=version_id
                    )
                    id_mapping[task.task_id] = story_key

                    # 4. Crear Subtasks
                    for subtask in task.subtasks:
                        subtask_key = await self.create_subtask(
                            subtask=subtask,
                            parent_key=story_key
                        )
                        id_mapping[subtask.subtask_id] = subtask_key

        # 5. Crear Links de dependencias
        await self.create_dependency_links(masterplan, id_mapping)

        return id_mapping

    async def create_epic(self, phase) -> str:
        """Crea un Epic en Jira."""
        url = f"{self.config.base_url}/rest/api/3/issue"

        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "issuetype": {"name": "Epic"},
                "summary": phase.name,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": phase.description}
                            ]
                        }
                    ]
                },
                "customfield_10011": phase.name,  # Epic Name
                "priority": {"name": "High"},
                "labels": ["masterplan", f"phase_{phase.order}"]
            }
        }

        response = requests.post(
            url,
            json=payload,
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["key"]  # ej: "DEVMX-123"

    async def create_version(self, milestone) -> str:
        """Crea una Fix Version en Jira."""
        url = f"{self.config.base_url}/rest/api/3/version"

        payload = {
            "name": milestone.name,
            "description": milestone.description,
            "project": self.config.project_key,
            "released": milestone.status == "completed"
        }

        response = requests.post(
            url,
            json=payload,
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["id"]

    async def create_story(
        self,
        task,
        epic_key: str,
        fix_version_id: str
    ) -> str:
        """Crea una Story en Jira."""
        url = f"{self.config.base_url}/rest/api/3/issue"

        # Formatear acceptance criteria
        ac_text = "\n".join([f"✓ {ac}" for ac in task.acceptance_criteria])

        description = f"""
{task.description}

*Acceptance Criteria:*
{ac_text}

*Complexity:* {task.complexity}
*Estimated Time:* {task.estimated_time_minutes} minutes
*Assigned Agent:* {task.assigned_agent}
"""

        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "issuetype": {"name": "Story"},
                "summary": task.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description}
                            ]
                        }
                    ]
                },
                "priority": self._map_priority(task.priority),
                "labels": task.labels + ["masterplan", "automated"],
                "customfield_10016": task.story_points,  # Story Points
                "customfield_10014": epic_key,  # Epic Link
                "fixVersions": [{"id": fix_version_id}]
            }
        }

        response = requests.post(
            url,
            json=payload,
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["key"]

    async def create_subtask(self, subtask, parent_key: str) -> str:
        """Crea un Subtask en Jira."""
        url = f"{self.config.base_url}/rest/api/3/issue"

        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": parent_key},
                "summary": subtask.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Estimated: {subtask.estimated_minutes} min"
                                }
                            ]
                        }
                    ]
                },
                "timetracking": {
                    "originalEstimate": f"{subtask.estimated_minutes}m"
                }
            }
        }

        response = requests.post(
            url,
            json=payload,
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["key"]

    async def create_dependency_links(
        self,
        masterplan: MasterPlan,
        id_mapping: Dict[str, str]
    ):
        """Crea links de dependencias entre issues."""
        url = f"{self.config.base_url}/rest/api/3/issueLink"

        for phase in masterplan.phases:
            for milestone in phase.milestones:
                for task in milestone.tasks:
                    task_key = id_mapping[task.task_id]

                    # Crear link para cada dependencia
                    for dep_task_id in task.depends_on:
                        dep_key = id_mapping.get(dep_task_id)
                        if not dep_key:
                            continue

                        payload = {
                            "type": {"name": "Blocks"},
                            "inwardIssue": {"key": dep_key},
                            "outwardIssue": {"key": task_key}
                        }

                        response = requests.post(
                            url,
                            json=payload,
                            auth=self.auth,
                            headers=self.headers
                        )
                        # Ignorar errores de duplicados
                        if response.status_code not in [200, 201, 400]:
                            response.raise_for_status()

    def _map_priority(self, priority: str) -> Dict[str, str]:
        """Mapea prioridad del MasterPlan a Jira."""
        mapping = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low"
        }
        return {"name": mapping.get(priority, "Medium")}
```

#### Uso del Servicio

```python
# En OrchestratorAgent o MasterPlanService

async def export_to_jira(masterplan: MasterPlan):
    """
    Exporta el MasterPlan a Jira.
    """
    # Configuración desde variables de entorno
    jira_config = JiraConfig(
        base_url=os.getenv("JIRA_BASE_URL"),
        email=os.getenv("JIRA_EMAIL"),
        api_token=os.getenv("JIRA_API_TOKEN"),
        project_key=os.getenv("JIRA_PROJECT_KEY", "DEVMX")
    )

    jira_service = JiraExportService(jira_config)

    # Exportar
    id_mapping = await jira_service.export_masterplan(masterplan)

    # Guardar mapeo en la DB para sincronización futura
    await save_jira_mapping(masterplan.masterplan_id, id_mapping)

    return {
        "success": True,
        "jira_issues_created": len(id_mapping),
        "jira_board_url": f"{jira_config.base_url}/jira/software/projects/{jira_config.project_key}/board",
        "id_mapping": id_mapping
    }
```

#### Formato de Exportación CSV (Alternativo)

Si prefieres importar manualmente a Jira, también podemos generar CSV:

```python
import csv
from io import StringIO

def export_to_csv(masterplan: MasterPlan) -> str:
    """
    Genera CSV compatible con Jira Importer.

    Format: https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/
    """
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Issue Type",
        "Summary",
        "Description",
        "Priority",
        "Labels",
        "Story Points",
        "Epic Link",
        "Fix Version",
        "Parent",
        "Estimated Time (minutes)"
    ])

    # Epics (Phases)
    for phase in masterplan.phases:
        writer.writerow([
            "Epic",
            phase.name,
            phase.description,
            "High",
            f"phase_{phase.order}",
            "",
            "",
            "",
            "",
            int(phase.estimated_duration_hours * 60)
        ])

    # Stories (Tasks)
    for phase in masterplan.phases:
        for milestone in phase.milestones:
            for task in milestone.tasks:
                ac_text = "\n".join([f"* {ac}" for ac in task.acceptance_criteria])
                description = f"{task.description}\n\nAcceptance Criteria:\n{ac_text}"

                writer.writerow([
                    "Story",
                    task.title,
                    description,
                    task.priority.capitalize(),
                    ",".join(task.labels),
                    task.story_points,
                    phase.name,  # Epic Link
                    milestone.name,  # Fix Version
                    "",
                    task.estimated_time_minutes
                ])

                # Subtasks
                for subtask in task.subtasks:
                    writer.writerow([
                        "Sub-task",
                        subtask.title,
                        "",
                        "Medium",
                        "",
                        "",
                        "",
                        "",
                        task.title,  # Parent
                        subtask.estimated_minutes
                    ])

    return output.getvalue()

# Uso
csv_content = export_to_csv(masterplan)

# Guardar a archivo
with open("masterplan_jira_import.csv", "w") as f:
    f.write(csv_content)

# O devolver via API
return Response(
    content=csv_content,
    media_type="text/csv",
    headers={"Content-Disposition": "attachment; filename=masterplan.csv"}
)
```

#### WebSocket Event para Exportación

```python
# En websocket.py

@sio.event
async def export_masterplan_to_jira(sid, data):
    """
    Exporta MasterPlan a Jira.

    Expected data:
        {
            "masterplan_id": "mp_uuid_1234",
            "export_format": "jira_api" | "csv"
        }
    """
    try:
        masterplan_id = data.get('masterplan_id')
        export_format = data.get('export_format', 'jira_api')

        masterplan = masterplan_service.get_by_id(masterplan_id)

        if export_format == "jira_api":
            # Exportación directa via API
            result = await jira_service.export_masterplan(masterplan)

            await sio.emit('jira_export_complete', {
                'success': True,
                'issues_created': result['jira_issues_created'],
                'board_url': result['jira_board_url']
            }, room=sid)

        elif export_format == "csv":
            # Generar CSV para importación manual
            csv_content = export_to_csv(masterplan)

            await sio.emit('jira_csv_ready', {
                'success': True,
                'csv_content': csv_content,
                'filename': f'masterplan_{masterplan_id}.csv'
            }, room=sid)

    except Exception as e:
        logger.error(f"Error exporting to Jira: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)
```

#### Configuración en .env

```bash
# Jira Integration
JIRA_ENABLED=true
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=DEVMX
```

### 7. Grafo de Dependencias

```json
{
  "dependency_graph": {
    "task_001": [],
    "task_002": ["task_001"],
    "task_003": ["task_002"],
    "task_004": ["task_002", "task_003"],
    "task_005": ["task_003", "task_004"],
    "task_006": ["task_002", "task_003", "task_004", "task_005"],
    "task_007": ["task_006"],
    "task_008": ["task_004", "task_005"]
  },
  "parallel_execution_groups": [
    ["task_001"],
    ["task_002"],
    ["task_003"],
    ["task_004"],
    ["task_005"],
    ["task_006", "task_008"],
    ["task_007"]
  ]
}
```

---

## 🔄 Estados de las Tareas

### Flujo de Estados

```
pending → in_progress → ready_for_test → tested → done
                           ↓
                        failed
                           ↓
                        pending (retry)
```

### Definición de Estados

| Estado | Descripción | Quién lo Actualiza | Siguiente Estado Posible |
|--------|-------------|-------------------|-------------------------|
| **pending** | Tarea definida, esperando ejecución | Sistema al crear MasterPlan | in_progress |
| **in_progress** | Un agente está ejecutando la tarea | Agent al iniciar | ready_for_test, failed |
| **ready_for_test** | Código generado, listo para validar | Agent al completar | tested |
| **tested** | Tests ejecutados (pueden pasar o fallar) | TestingAgent | done, failed |
| **failed** | La tarea falló (test o ejecución) | Agent o TestingAgent | pending (para retry) |
| **done** | Tarea completamente validada y finalizada | Sistema tras tests exitosos | - |

### Metadata por Estado

```json
{
  "status": "tested",
  "status_metadata": {
    "started_at": "2025-01-20T10:35:00Z",
    "completed_at": "2025-01-20T10:37:00Z",
    "duration_seconds": 120,
    "agent_used": "ImplementationAgent",
    "test_results": {
      "total_tests": 5,
      "passed": 5,
      "failed": 0,
      "coverage_percent": 85.3
    },
    "retry_count": 0,
    "last_error": null
  }
}
```

---

## 🔍 Phase 0: Discovery & Domain Modeling (DDD)

### Visión General

**ANTES** de descomponer en tareas técnicas, debemos entender profundamente:
- **¿QUÉ** estamos construyendo? (Dominio de negocio)
- **¿PARA QUIÉN?** (Usuarios, stakeholders)
- **¿CÓMO** funciona el negocio? (Procesos, reglas, flujos)
- **¿DÓNDE** se integra? (Sistemas externos, APIs, servicios)
- **¿POR QUÉ?** (Objetivos de negocio, valor entregado)

**Principio fundamental**: "No podemos diseñar la solución técnica sin entender el problema de negocio"

---

### Fase 0.1: Business Domain Analysis

#### Preguntas Fundamentales del Discovery

```python
DISCOVERY_QUESTIONNAIRE = {
    "business_domain": [
        "¿Cuál es el dominio de negocio principal? (ej: E-commerce, Fintech, Healthcare, Logistics)",
        "¿Qué problema específico del negocio estamos resolviendo?",
        "¿Quiénes son los usuarios finales? (roles, perfiles)",
        "¿Cuáles son los procesos de negocio críticos?",
        "¿Qué reglas de negocio son INVARIANTES? (nunca pueden violarse)",
    ],

    "industry_context": [
        "¿Qué industria/vertical? (SaaS, Banking, Retail, etc.)",
        "¿Hay regulaciones específicas? (GDPR, HIPAA, PCI-DSS, etc.)",
        "¿Volumen esperado? (usuarios, transacciones/día)",
        "¿Criticidad? (tiempo de inactividad aceptable, SLA)",
    ],

    "existing_systems": [
        "¿Hay sistemas legacy con los que debemos integrarnos?",
        "¿Qué APIs externas se deben consumir?",
        "¿Qué servicios third-party se usarán? (Stripe, SendGrid, etc.)",
        "¿Hay fuentes de datos existentes? (bases de datos, data lakes)",
    ],

    "workflows": [
        "Describir el flujo de trabajo principal (paso a paso)",
        "¿Qué flujos excepcionales existen? (errores, compensaciones)",
        "¿Hay workflows asíncronos? (emails, notificaciones, jobs)",
        "¿Qué eventos de dominio son importantes?",
    ]
}
```

#### Ejemplo: API REST de Gestión de Usuarios

```json
{
  "discovery_results": {
    "business_domain": "User Management & Authentication for B2B SaaS",
    "problem_statement": "Necesitamos autenticar usuarios de múltiples organizaciones con roles granulares",
    "industry": "SaaS / Multi-tenant",
    "regulations": ["GDPR (EU users)", "SOC2 compliance desired"],

    "users": [
      {
        "role": "End User",
        "needs": ["Registrarse", "Iniciar sesión", "Actualizar perfil"],
        "permissions": "Basic access to own data"
      },
      {
        "role": "Organization Admin",
        "needs": ["Gestionar usuarios de su org", "Asignar roles"],
        "permissions": "Admin within tenant boundary"
      },
      {
        "role": "Platform Admin",
        "needs": ["Gestionar todas las orgs", "Ver métricas globales"],
        "permissions": "Super admin - cross-tenant"
      }
    ],

    "critical_workflows": [
      {
        "name": "User Registration",
        "trigger": "User submits registration form",
        "steps": [
          "Validate email format and uniqueness",
          "Validate password strength",
          "Hash password with bcrypt",
          "Create user record",
          "Send verification email",
          "Create default user settings"
        ],
        "business_rules": [
          "Email must be unique across the entire platform",
          "Password must be at least 12 chars with special chars",
          "User starts as 'pending_verification' status"
        ],
        "failure_scenarios": [
          "Email already exists → Return 409 Conflict",
          "Email service down → Queue for retry, allow login with warning"
        ]
      },
      {
        "name": "User Authentication",
        "trigger": "User submits login credentials",
        "steps": [
          "Look up user by email",
          "Verify password hash",
          "Check if user is active",
          "Generate JWT token with claims",
          "Return token + refresh token"
        ],
        "business_rules": [
          "Inactive users cannot login",
          "Max 5 failed attempts → lock account for 15 min",
          "JWT expires in 24 hours"
        ]
      }
    ],

    "external_integrations": [
      {
        "service": "SendGrid",
        "purpose": "Email notifications",
        "operations": ["send_verification_email", "send_password_reset"]
      },
      {
        "service": "Existing CRM (optional)",
        "purpose": "Sync user data",
        "operations": ["push_new_user_to_crm"]
      }
    ]
  }
}
```

---

### Fase 0.2: DDD Strategic Design (Modelado Estratégico)

#### Bounded Contexts

**Definición**: Límites explícitos donde un modelo de dominio específico es válido.

```python
# Para el ejemplo de User Management:

BOUNDED_CONTEXTS = {
    "Identity & Access Management (IAM)": {
        "description": "Gestión de usuarios, autenticación y autorización",
        "responsibilities": [
            "User registration and profile management",
            "Authentication (login, JWT generation)",
            "Authorization (roles, permissions)",
            "Session management"
        ],
        "entities": ["User", "Role", "Permission", "Session"],
        "ubiquitous_language": {
            "User": "A person with credentials who can access the system",
            "Role": "A named set of permissions",
            "Permission": "An allowed action on a resource",
            "Session": "An authenticated period of user activity"
        },
        "upstream_dependencies": [],  # Este es el core
        "downstream_consumers": ["Audit Log", "Notification"]
    },

    "Audit Log": {
        "description": "Registro inmutable de eventos de seguridad",
        "responsibilities": [
            "Record all authentication attempts",
            "Record permission changes",
            "Provide audit trail for compliance"
        ],
        "entities": ["AuditEvent"],
        "upstream_dependencies": ["IAM"],  # Consume eventos de IAM
        "downstream_consumers": []
    },

    "Notification": {
        "description": "Envío de notificaciones a usuarios",
        "responsibilities": [
            "Send verification emails",
            "Send password reset emails",
            "Send security alerts"
        ],
        "entities": ["EmailNotification", "NotificationTemplate"],
        "upstream_dependencies": ["IAM"],
        "downstream_consumers": []
    }
}
```

#### Context Mapping

**Relaciones entre Bounded Contexts**:

```
[Identity & Access Management (IAM)]
         │
         │ Publishes Domain Events:
         │  - UserRegistered
         │  - UserLoggedIn
         │  - PasswordChanged
         │
         ├──────────► [Audit Log]
         │            (Customer/Supplier)
         │            Audit Log MUST record all IAM events
         │
         └──────────► [Notification]
                      (Customer/Supplier)
                      Notification sends emails on IAM events
```

**Tipos de relaciones**:
- **Customer/Supplier**: IAM provee eventos, los otros consumen
- **Conformist**: Los consumidores aceptan el modelo de IAM sin negociación
- **Anti-Corruption Layer**: Si integramos con CRM externo, usamos ACL para traducir modelos

---

### Fase 0.3: DDD Tactical Design (Modelado Táctico)

#### Aggregates, Entities, Value Objects

Para cada Bounded Context, identificamos:

```python
# Bounded Context: Identity & Access Management

AGGREGATES = {
    "User": {
        "aggregate_root": "User",
        "description": "El usuario es el aggregate root que protege invariantes de identidad",

        "entities": [
            {
                "name": "User",
                "type": "Entity (Aggregate Root)",
                "identity": "user_id (UUID)",
                "attributes": [
                    "user_id: UUID",
                    "email: Email (Value Object)",
                    "password_hash: HashedPassword (Value Object)",
                    "profile: UserProfile (Value Object)",
                    "status: UserStatus (Enum)",
                    "role: Role (Entity Reference)",
                    "created_at: DateTime",
                    "updated_at: DateTime"
                ],
                "invariants": [
                    "Email must be unique across system",
                    "Password must never be stored in plaintext",
                    "Active users must have verified email",
                    "User must always have exactly one role"
                ],
                "behavior": [
                    "register(email, password) -> User",
                    "authenticate(password) -> bool",
                    "change_password(old, new) -> Result",
                    "activate() -> Result",
                    "deactivate() -> Result",
                    "assign_role(role) -> Result"
                ]
            }
        ],

        "value_objects": [
            {
                "name": "Email",
                "attributes": ["address: str"],
                "validations": [
                    "Must match email regex",
                    "Must be lowercase",
                    "Max 255 chars"
                ],
                "immutable": True
            },
            {
                "name": "HashedPassword",
                "attributes": ["hash: str", "algorithm: str"],
                "validations": [
                    "Must be bcrypt hash",
                    "Never expose raw value"
                ],
                "immutable": True,
                "behavior": [
                    "verify(plaintext: str) -> bool",
                    "from_plaintext(plaintext: str) -> HashedPassword"
                ]
            },
            {
                "name": "UserProfile",
                "attributes": [
                    "full_name: str",
                    "avatar_url: Optional[str]",
                    "timezone: str"
                ],
                "immutable": False  # Puede actualizarse
            }
        ],

        "domain_events": [
            {
                "name": "UserRegistered",
                "attributes": [
                    "user_id: UUID",
                    "email: str",
                    "registered_at: DateTime"
                ],
                "triggers": "After successful user.register()"
            },
            {
                "name": "UserAuthenticated",
                "attributes": [
                    "user_id: UUID",
                    "authenticated_at: DateTime",
                    "ip_address: str"
                ],
                "triggers": "After successful user.authenticate()"
            },
            {
                "name": "UserPasswordChanged",
                "attributes": [
                    "user_id: UUID",
                    "changed_at: DateTime"
                ],
                "triggers": "After user.change_password()"
            }
        ]
    },

    "Role": {
        "aggregate_root": "Role",
        "description": "Rol con conjunto de permisos",

        "entities": [
            {
                "name": "Role",
                "type": "Entity (Aggregate Root)",
                "identity": "role_id (UUID)",
                "attributes": [
                    "role_id: UUID",
                    "name: RoleName (Value Object)",
                    "permissions: Set[Permission]",
                    "description: str",
                    "created_at: DateTime"
                ],
                "invariants": [
                    "Role name must be unique",
                    "Role must have at least one permission",
                    "Cannot delete role if users are assigned to it"
                ],
                "behavior": [
                    "add_permission(permission) -> Result",
                    "remove_permission(permission) -> Result",
                    "has_permission(permission) -> bool"
                ]
            }
        ],

        "value_objects": [
            {
                "name": "Permission",
                "attributes": [
                    "resource: str",
                    "action: str"
                ],
                "examples": [
                    "Permission('users', 'read')",
                    "Permission('users', 'write')",
                    "Permission('roles', 'manage')"
                ],
                "immutable": True
            }
        ]
    }
}
```

#### Repositories

```python
REPOSITORIES = {
    "UserRepository": {
        "aggregate": "User",
        "operations": [
            "add(user: User) -> None",
            "get_by_id(user_id: UUID) -> Optional[User]",
            "get_by_email(email: Email) -> Optional[User]",
            "update(user: User) -> None",
            "delete(user_id: UUID) -> None",
            "find_all(filters: dict, pagination: Pagination) -> List[User]"
        ],
        "persistence": "PostgreSQL via SQLAlchemy"
    },

    "RoleRepository": {
        "aggregate": "Role",
        "operations": [
            "add(role: Role) -> None",
            "get_by_id(role_id: UUID) -> Optional[Role]",
            "get_by_name(name: str) -> Optional[Role]",
            "find_all() -> List[Role]"
        ],
        "persistence": "PostgreSQL via SQLAlchemy"
    }
}
```

#### Domain Services

```python
DOMAIN_SERVICES = {
    "AuthenticationService": {
        "responsibility": "Orquestar el proceso de autenticación",
        "methods": [
            "authenticate(email: Email, password: str) -> Result[AuthToken]",
            "generate_token(user: User) -> AuthToken",
            "verify_token(token: str) -> Result[User]",
            "refresh_token(refresh_token: str) -> Result[AuthToken]"
        ],
        "dependencies": [
            "UserRepository",
            "JWTTokenGenerator (Infrastructure)"
        ]
    },

    "PasswordResetService": {
        "responsibility": "Gestionar el flujo de reset de contraseña",
        "methods": [
            "initiate_reset(email: Email) -> Result[ResetToken]",
            "verify_reset_token(token: str) -> Result[User]",
            "complete_reset(token: str, new_password: str) -> Result"
        ],
        "dependencies": [
            "UserRepository",
            "EmailService (Infrastructure)"
        ]
    }
}
```

---

### Fase 0.4: Ubiquitous Language (Lenguaje Ubicuo)

**Glosario de términos del dominio** que TODOS (devs, stakeholders, usuarios) comparten:

```markdown
# Ubiquitous Language - Identity & Access Management

## Core Concepts

**User**: A person who has registered an account and can authenticate to access the system.

**Role**: A named collection of permissions that can be assigned to a user.

**Permission**: An allowed action on a specific resource (e.g., "read:users", "write:posts").

**Session**: An authenticated period during which a user can interact with the system.

**Authentication**: The process of verifying a user's identity through credentials.

**Authorization**: The process of determining if an authenticated user has permission to perform an action.

## User Lifecycle

- **Registered**: User created but email not verified
- **Verified**: Email verified, account active
- **Suspended**: Temporarily deactivated (can be reactivated)
- **Deleted**: Permanently removed (soft delete)

## Business Rules (Always True)

1. **Email Uniqueness**: No two users can have the same email address
2. **Password Security**: Passwords are ALWAYS hashed, NEVER stored in plaintext
3. **Role Requirement**: Every user MUST have exactly one role
4. **Permission Inheritance**: Users inherit ALL permissions from their assigned role

## Events (Things That Happen)

- **UserRegistered**: A new user completed registration
- **UserAuthenticated**: A user successfully logged in
- **UserPasswordChanged**: A user changed their password
- **UserRoleChanged**: An admin changed a user's role
- **UserSuspended**: An admin suspended a user account
```

---

### Fase 0.5: Integration Requirements Discovery

#### APIs Externas a Consumir

```json
{
  "external_apis": [
    {
      "service": "SendGrid API",
      "purpose": "Email delivery",
      "endpoints": [
        {
          "operation": "POST /v3/mail/send",
          "use_case": "Send verification emails, password resets",
          "authentication": "API Key",
          "rate_limits": "100 emails/second"
        }
      ],
      "error_handling": "Queue for retry on 5xx, fail fast on 4xx"
    },
    {
      "service": "OAuth Provider (Google, GitHub)",
      "purpose": "Social login (future feature)",
      "endpoints": [
        "OAuth 2.0 authorization flow",
        "User info endpoint"
      ],
      "authentication": "OAuth 2.0 client credentials",
      "data_mapping": "Map OAuth user to our User model"
    }
  ],

  "internal_systems": [
    {
      "system": "Legacy CRM",
      "purpose": "Sync user data to sales team",
      "integration_type": "Anti-Corruption Layer (ACL)",
      "protocol": "REST API",
      "data_flow": "One-way: DevMatrix → CRM",
      "mapping": {
        "User.email": "CRM.Contact.Email",
        "User.full_name": "CRM.Contact.Name",
        "User.created_at": "CRM.Contact.LeadCreatedDate"
      }
    }
  ]
}
```

---

### Fase 0.6: Output del Discovery → MasterPlan Input

El resultado del Discovery alimenta DIRECTAMENTE el MasterPlan:

```python
{
  "discovery_output": {
    # Esto se convierte en...
    "bounded_contexts": {...},
    "aggregates": {...},
    "workflows": {...},
    "business_rules": {...},
    "external_integrations": {...}
  },

  # Se transforma en:
  "masterplan_input": {
    "business_logic": {
      "domain": "Identity & Access Management",
      "bounded_contexts": [...],
      "workflows": [...],
      "rules": [...]
    },

    "entities": [
      # Derivadas de los Aggregates
      {"name": "User", "attributes": [...], "validations": [...]},
      {"name": "Role", "attributes": [...], "validations": [...]}
    ],

    "stack": {
      # Influenciado por requisitos del Discovery
      "database": "PostgreSQL",  # Por ACID requirements
      "orm": "SQLAlchemy",        # Para mapear Aggregates
      "events": "Redis Pub/Sub",  # Para Domain Events
      "queue": "Celery + Redis"   # Para emails asíncronos
    },

    "tasks": [
      # Tareas atómicas derivadas de las entidades y workflows
      {"task_id": "task_001", "title": "Implement User Aggregate with invariants", ...},
      {"task_id": "task_002", "title": "Implement Role Aggregate", ...},
      {"task_id": "task_003", "title": "Implement AuthenticationService", ...},
      ...
    ]
  }
}
```

---

### Fase 0.7: DiscoveryAgent - Automatización del Discovery

**Nuevo agente especializado en hacer Discovery**:

```python
class DiscoveryAgent:
    """
    Agente que conduce el proceso de Discovery con el usuario.
    """

    async def conduct_discovery(
        self,
        user_request: str,
        conversation_id: str
    ) -> DiscoveryResult:
        """
        Realiza Discovery interactivo con el usuario.

        Flujo:
        1. Analizar pedido inicial
        2. Identificar gaps de información
        3. Hacer preguntas al usuario (via WebSocket)
        4. Modelar el dominio con DDD
        5. Validar con el usuario
        6. Generar Discovery Document
        """

        # 1. Análisis inicial
        initial_analysis = await self.llm.analyze(
            prompt=f"""
            Analiza este pedido y extrae lo que YA sabemos:

            User request: {user_request}

            Extrae:
            - Dominio de negocio (si es claro)
            - Entidades mencionadas
            - Operaciones/acciones mencionadas
            - Stack tecnológico (si se menciona)

            Identifica qué información FALTA para hacer un buen diseño DDD.
            """
        )

        # 2. Generar preguntas inteligentes
        questions = await self.generate_discovery_questions(initial_analysis)

        # 3. Hacer preguntas al usuario (interactivo via WebSocket)
        answers = await self.ask_user_questions(questions, conversation_id)

        # 4. Modelar el dominio con DDD
        domain_model = await self.model_domain_with_ddd(
            user_request=user_request,
            initial_analysis=initial_analysis,
            user_answers=answers
        )

        # 5. Presentar modelo al usuario para validación
        validated_model = await self.validate_with_user(domain_model, conversation_id)

        # 6. Generar Discovery Document
        discovery_doc = DiscoveryDocument(
            business_domain=validated_model.domain,
            bounded_contexts=validated_model.contexts,
            aggregates=validated_model.aggregates,
            workflows=validated_model.workflows,
            business_rules=validated_model.rules,
            ubiquitous_language=validated_model.glossary,
            integrations=validated_model.integrations,
            created_at=datetime.now()
        )

        return discovery_doc

    async def model_domain_with_ddd(self, user_request, initial_analysis, user_answers):
        """
        Usa LLM para modelar el dominio siguiendo DDD patterns.
        """
        prompt = f"""
        Eres un experto en Domain-Driven Design (DDD).

        REQUEST: {user_request}
        ANÁLISIS INICIAL: {initial_analysis}
        RESPUESTAS DEL USUARIO: {user_answers}

        Tarea: Modela el dominio siguiendo DDD:

        1. BOUNDED CONTEXTS
           - Identifica los contextos delimitados
           - Define responsabilidades claras
           - Mapea relaciones entre contextos

        2. AGGREGATES
           - Para cada bounded context, identifica aggregates
           - Define aggregate roots
           - Identifica entities vs value objects
           - Define invariantes que el aggregate protege

        3. DOMAIN EVENTS
           - Qué eventos importantes ocurren en el dominio
           - Cuándo se emiten
           - Quién los consume

        4. UBIQUITOUS LANGUAGE
           - Glosario de términos del dominio
           - Definiciones que todos comparten

        5. WORKFLOWS
           - Procesos de negocio paso a paso
           - Reglas de negocio en cada paso

        Genera el modelo en formato estructurado JSON.
        """

        domain_model = await self.llm.generate(prompt)
        return domain_model
```

#### Ejemplo de Preguntas Generadas por DiscoveryAgent

```json
{
  "discovery_questions": [
    {
      "id": "q1",
      "category": "business_domain",
      "question": "¿En qué industria opera este sistema? (SaaS, E-commerce, Healthcare, etc.)",
      "why_we_ask": "Determina regulaciones y patrones de diseño aplicables",
      "examples": ["SaaS multi-tenant", "E-commerce B2C", "Healthcare (HIPAA)"]
    },
    {
      "id": "q2",
      "category": "users",
      "question": "¿Qué tipos de usuarios usarán el sistema y qué pueden hacer?",
      "why_we_ask": "Define el modelo de autorización y casos de uso principales",
      "format": "Lista de roles con sus responsabilidades"
    },
    {
      "id": "q3",
      "category": "workflows",
      "question": "Describe el flujo de registro de un usuario paso a paso",
      "why_we_ask": "Identifica reglas de negocio y validaciones requeridas",
      "format": "Paso 1, Paso 2, ..."
    },
    {
      "id": "q4",
      "category": "integrations",
      "question": "¿Hay sistemas externos con los que debemos integrarnos?",
      "why_we_ask": "Planifica anti-corruption layers y adaptadores",
      "examples": ["APIs de terceros", "Bases de datos legacy", "Servicios de email"]
    },
    {
      "id": "q5",
      "category": "scalability",
      "question": "¿Cuántos usuarios/transacciones esperas? ¿Hay picos de tráfico?",
      "why_we_ask": "Determina arquitectura (monolito vs microservicios, caching, etc.)",
      "options": ["< 1K users", "1K-10K users", "10K-100K users", "100K+ users"]
    }
  ]
}
```

---

### Fase 0.8: Discovery Document → Persistent Storage

El resultado del Discovery se guarda en PostgreSQL:

```sql
-- Tabla de Discovery Documents
CREATE TABLE discovery_documents (
    discovery_id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(workspace_id),
    conversation_id UUID REFERENCES conversations(conversation_id),

    -- User request original
    user_request_original TEXT NOT NULL,

    -- Discovery results (JSONB)
    business_domain JSONB NOT NULL,  -- Industry, problem statement, users
    bounded_contexts JSONB NOT NULL, -- DDD bounded contexts
    aggregates JSONB NOT NULL,       -- Aggregates, entities, value objects
    workflows JSONB NOT NULL,        -- Business processes
    business_rules JSONB NOT NULL,   -- Invariants and rules
    ubiquitous_language JSONB,       -- Glossary
    integrations JSONB,              -- External systems

    -- Metadata
    status VARCHAR(50) DEFAULT 'in_progress',  -- in_progress, validated, completed
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,

    -- Link to generated MasterPlan
    masterplan_id UUID REFERENCES masterplans(masterplan_id)
);

CREATE INDEX idx_discovery_workspace ON discovery_documents(workspace_id);
CREATE INDEX idx_discovery_status ON discovery_documents(status);
```

---

## 🔄 Ciclo de Vida del MasterPlan (ACTUALIZADO)

### Flujo Completo: Discovery → MasterPlan → Ejecución

```
Usuario: "Crea una API REST para gestión de usuarios con JWT"
   ↓
ChatService detecta que es un pedido de implementación
   ↓
┌──────────────────────────────────────────────────────┐
│ PHASE 0: DISCOVERY (NUEVO)                          │
└──────────────────────────────────────────────────────┘
   ↓
DiscoveryAgent.conduct_discovery()
   ├─► Analiza pedido inicial
   ├─► Identifica gaps de información
   ├─► Hace preguntas al usuario (interactivo via WS)
   │   - ¿Industria? ¿Regulaciones?
   │   - ¿Tipos de usuarios? ¿Roles?
   │   - ¿Flujos de negocio?
   │   - ¿Integraciones externas?
   ├─► Usuario responde preguntas
   ├─► DiscoveryAgent modela dominio con DDD:
   │   - Bounded Contexts
   │   - Aggregates (Entities + Value Objects)
   │   - Domain Events
   │   - Workflows
   │   - Business Rules
   │   - Ubiquitous Language
   ├─► Presenta modelo al usuario para validación
   └─► Usuario valida/ajusta modelo
   ↓
DiscoveryDocument generado y guardado
   ↓
┌──────────────────────────────────────────────────────┐
│ PHASE 1: MASTERPLAN CREATION                        │
└──────────────────────────────────────────────────────┘
   ↓
OrchestratorAgent.create_masterplan(discovery_doc)
   ├─► Usa Discovery Document como input
   ├─► Infiere stack tecnológico basado en requisitos
   ├─► Transforma Aggregates → Entidades técnicas
   ├─► Descompone workflows → Tareas atómicas
   ├─► Construye grafo de dependencias
   └─► Estima tiempos
   ↓
MasterPlan generado (status: "draft")
   ↓
┌──────────────────────────────────────────────────────┐
│ PHASE 2: APPROVAL                                   │
└──────────────────────────────────────────────────────┘
   ↓
Usuario revisa y aprueba MasterPlan
   ↓
┌──────────────────────────────────────────────────────┐
│ PHASE 3: EXECUTION                                  │
└──────────────────────────────────────────────────────┘
   ↓
Ejecución de tareas atómicas con validación estricta
```

### 1. Creación (Generación) - ACTUALIZADO

**Trigger**: Usuario envía un pedido de proyecto

```
Usuario: "Crea una API REST para gestión de usuarios con JWT"
   ↓
ChatService detecta que es un pedido de implementación
   ↓
DiscoveryAgent.conduct_discovery()  ← NUEVO
   ↓
DiscoveryDocument generado
   ↓
OrchestratorAgent.create_masterplan(discovery_doc)
   ↓
   ├─► Usa discovery_doc.bounded_contexts
   ├─► Usa discovery_doc.aggregates → Genera entidades técnicas
   ├─► Usa discovery_doc.workflows → Genera tareas
   ├─► Usa discovery_doc.integrations → Identifica dependencias externas
   ├─► Infiere/propone stack tecnológico
   ├─► Construye grafo de dependencias
   └─► Estima tiempos
   ↓
MasterPlan generado (status: "draft")
```

### 2. Presentación y Aprobación

**El sistema muestra el MasterPlan al usuario ANTES de ejecutar**

```
DevMatrix:
📋 He analizado tu pedido. Aquí está el MasterPlan propuesto:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PROYECTO: API REST Gestión de Usuarios

📦 STACK TECNOLÓGICO:
  • Backend: FastAPI
  • Database: PostgreSQL + SQLAlchemy
  • Auth: JWT
  • Testing: pytest

🏗️ ENTIDADES:
  • User (id, email, password_hash, full_name, ...)
  • Role (id, name, permissions)

📝 TAREAS (8 total):
  1. [PENDING] Setup FastAPI project structure (5 min)
  2. [PENDING] Create database models (10 min)
  3. [PENDING] Implement authentication middleware (15 min)
  4. [PENDING] Create POST /users endpoint (10 min)
  5. [PENDING] Create GET /users endpoints (8 min)
  6. [PENDING] Write unit tests (20 min)
  7. [PENDING] Write integration tests (20 min)
  8. [PENDING] Generate API documentation (15 min)

⏱️ Tiempo estimado total: ~1h 43min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Opciones:
[✅ Aprobar y Ejecutar]  [📝 Modificar Plan]  [❌ Cancelar]
```

**Acciones del usuario:**
- **Aprobar**: MasterPlan.status → "approved", comienza ejecución
- **Modificar**: Usuario puede editar tareas, cambiar stack, reordenar
- **Cancelar**: Descarta el MasterPlan

### 3. Ejecución

```
MasterPlan.status = "in_progress"
   ↓
Para cada tarea (respetando dependencias):
   ├─► task.status = "in_progress"
   ├─► Agent ejecuta la tarea
   ├─► task.status = "ready_for_test" (si genera código)
   ├─► TestingAgent valida (si aplicable)
   ├─► task.status = "tested" / "failed"
   └─► task.status = "done" (si todo OK)
   ↓
   └─► WebSocket emite actualizaciones en tiempo real
       → Frontend actualiza UI del MasterPlan
```

**Progreso en tiempo real:**

```
[✅ DONE] 1. Setup FastAPI project structure
[✅ DONE] 2. Create database models
[🔄 IN_PROGRESS] 3. Implement authentication middleware
[⏸️ PENDING] 4. Create POST /users endpoint
[⏸️ PENDING] 5. Create GET /users endpoints
...

Progreso: 2/8 tareas completadas (25%)
Tiempo transcurrido: 5 minutos
Tiempo estimado restante: 15 minutos
```

### 4. Actualización Dinámica

**El usuario puede modificar el MasterPlan durante la ejecución:**

```
Usuario: "Agrega también endpoints para actualizar y eliminar usuarios"
   ↓
OrchestratorAgent.update_masterplan()
   ├─► Analiza la nueva solicitud
   ├─► Crea nuevas tareas:
   │   - task_009: "Create PUT /users/{id} endpoint"
   │   - task_010: "Create DELETE /users/{id} endpoint"
   ├─► Actualiza dependencias
   └─► Inserta en el plan existente
   ↓
MasterPlan actualizado, continúa ejecución
```

### 5. Completación

```
Todas las tareas en status "done"
   ↓
MasterPlan.status = "completed"
   ↓
Sistema genera reporte final:
   ├─► Archivos creados
   ├─► Tests ejecutados (resultados)
   ├─► Coverage alcanzado
   ├─► Tiempo total de ejecución
   └─► Próximos pasos sugeridos
```

---

## 💾 Persistencia

### Tablas de PostgreSQL

```sql
-- ==========================================
-- Tabla principal del MasterPlan
-- ==========================================
CREATE TABLE masterplans (
    masterplan_id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(workspace_id),
    conversation_id UUID REFERENCES conversations(conversation_id),
    discovery_id UUID REFERENCES discovery_documents(discovery_id),
    project_name VARCHAR(255) NOT NULL,
    user_request_original TEXT NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('draft', 'approved', 'in_progress', 'completed', 'failed', 'cancelled')),

    -- JSON fields
    stack JSONB NOT NULL,
    business_logic JSONB,
    entities JSONB NOT NULL,

    -- Jira Integration
    jira_exported BOOLEAN DEFAULT FALSE,
    jira_project_key VARCHAR(50),
    jira_id_mapping JSONB,  -- Mapeo de IDs locales → Jira keys

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,

    CONSTRAINT unique_masterplan_per_workspace UNIQUE (workspace_id)
);

CREATE INDEX idx_masterplans_workspace ON masterplans(workspace_id);
CREATE INDEX idx_masterplans_status ON masterplans(status);
CREATE INDEX idx_masterplans_discovery ON masterplans(discovery_id);
CREATE INDEX idx_masterplans_jira_exported ON masterplans(jira_exported);

-- ==========================================
-- Tabla de Phases (Epics en Jira)
-- ==========================================
CREATE TABLE masterplan_phases (
    phase_id VARCHAR(50) PRIMARY KEY,
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    order_number INTEGER NOT NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'cancelled')),

    estimated_duration_hours FLOAT,
    actual_duration_hours FLOAT,

    -- Dependencias entre phases
    depends_on_phases TEXT[] DEFAULT '{}',

    -- Jira mapping
    jira_epic_key VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT unique_phase_order UNIQUE (masterplan_id, order_number)
);

CREATE INDEX idx_phases_masterplan ON masterplan_phases(masterplan_id);
CREATE INDEX idx_phases_status ON masterplan_phases(status);
CREATE INDEX idx_phases_order ON masterplan_phases(masterplan_id, order_number);

-- ==========================================
-- Tabla de Milestones (Fix Versions en Jira)
-- ==========================================
CREATE TABLE masterplan_milestones (
    milestone_id VARCHAR(50) PRIMARY KEY,
    phase_id VARCHAR(50) NOT NULL REFERENCES masterplan_phases(phase_id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    order_number INTEGER NOT NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked')),

    -- Acceptance Criteria
    acceptance_criteria JSONB DEFAULT '[]',

    estimated_duration_hours FLOAT,
    actual_duration_hours FLOAT,

    -- Jira mapping
    jira_version_id VARCHAR(50),
    jira_version_name VARCHAR(255),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT unique_milestone_order UNIQUE (phase_id, order_number)
);

CREATE INDEX idx_milestones_phase ON masterplan_milestones(phase_id);
CREATE INDEX idx_milestones_status ON masterplan_milestones(status);
CREATE INDEX idx_milestones_order ON masterplan_milestones(phase_id, order_number);

-- ==========================================
-- Tabla de Tasks (Stories en Jira)
-- ==========================================
CREATE TABLE masterplan_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    milestone_id VARCHAR(50) NOT NULL REFERENCES masterplan_milestones(milestone_id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,

    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('setup', 'implementation', 'testing', 'documentation', 'deployment', 'refactoring')),
    priority VARCHAR(20) CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    complexity VARCHAR(20) CHECK (complexity IN ('low', 'medium', 'high')),

    -- Estimation
    estimated_time_minutes INTEGER,
    story_points INTEGER,
    actual_time_minutes INTEGER,

    -- Acceptance Criteria
    acceptance_criteria JSONB DEFAULT '[]',

    -- Labels
    labels TEXT[] DEFAULT '{}',

    -- Dependencies (array of task_ids)
    depends_on TEXT[] DEFAULT '{}',
    blocks TEXT[] DEFAULT '{}',

    -- Agent assignment
    assigned_agent VARCHAR(100),

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'ready_for_test', 'tested', 'failed', 'done', 'blocked', 'cancelled')),
    status_metadata JSONB,
    status_history JSONB DEFAULT '[]',

    -- Output
    output JSONB,
    test_results JSONB,

    -- Validation
    validation_results JSONB,
    definition_of_done_satisfied BOOLEAN DEFAULT FALSE,

    -- Retries
    attempt_count INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,

    -- Jira mapping
    jira_issue_key VARCHAR(50),
    jira_issue_id VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,

    CONSTRAINT max_retries_check CHECK (attempt_count <= max_attempts)
);

CREATE INDEX idx_tasks_milestone ON masterplan_tasks(milestone_id);
CREATE INDEX idx_tasks_status ON masterplan_tasks(status);
CREATE INDEX idx_tasks_assigned_agent ON masterplan_tasks(assigned_agent);
CREATE INDEX idx_tasks_priority ON masterplan_tasks(priority);
CREATE INDEX idx_tasks_labels ON masterplan_tasks USING GIN(labels);
CREATE INDEX idx_tasks_jira_key ON masterplan_tasks(jira_issue_key);

-- ==========================================
-- Tabla de Subtasks
-- ==========================================
CREATE TABLE masterplan_subtasks (
    subtask_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL REFERENCES masterplan_tasks(task_id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT,

    estimated_minutes INTEGER,
    actual_minutes INTEGER,

    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),

    -- Jira mapping
    jira_subtask_key VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_subtasks_task ON masterplan_subtasks(task_id);
CREATE INDEX idx_subtasks_status ON masterplan_subtasks(status);

-- ==========================================
-- Tabla de historial de cambios al MasterPlan
-- ==========================================
CREATE TABLE masterplan_history (
    id SERIAL PRIMARY KEY,
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) ON DELETE CASCADE,

    change_type VARCHAR(50) NOT NULL,  -- 'created', 'approved', 'phase_added', 'milestone_added', 'task_added', 'task_updated', 'completed', 'exported_to_jira'
    change_description TEXT,
    changed_by VARCHAR(50),  -- 'user' or agent name

    -- Referencias opcionales
    phase_id VARCHAR(50),
    milestone_id VARCHAR(50),
    task_id VARCHAR(50),

    previous_value JSONB,
    new_value JSONB,

    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_history_masterplan ON masterplan_history(masterplan_id);
CREATE INDEX idx_history_timestamp ON masterplan_history(timestamp);
CREATE INDEX idx_history_change_type ON masterplan_history(change_type);

-- ==========================================
-- Vistas útiles para reporting
-- ==========================================

-- Vista: Progreso por Phase
CREATE VIEW masterplan_phase_progress AS
SELECT
    p.phase_id,
    p.masterplan_id,
    p.name AS phase_name,
    p.status AS phase_status,
    COUNT(DISTINCT m.milestone_id) AS total_milestones,
    COUNT(DISTINCT CASE WHEN m.status = 'completed' THEN m.milestone_id END) AS completed_milestones,
    COUNT(DISTINCT t.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.task_id END) AS completed_tasks,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.task_id END) /
        NULLIF(COUNT(DISTINCT t.task_id), 0),
        2
    ) AS progress_percent,
    SUM(t.estimated_time_minutes) AS estimated_time_minutes,
    SUM(t.actual_time_minutes) AS actual_time_minutes
FROM masterplan_phases p
LEFT JOIN masterplan_milestones m ON p.phase_id = m.phase_id
LEFT JOIN masterplan_tasks t ON m.milestone_id = t.milestone_id
GROUP BY p.phase_id, p.masterplan_id, p.name, p.status;

-- Vista: Progreso por Milestone
CREATE VIEW masterplan_milestone_progress AS
SELECT
    m.milestone_id,
    m.phase_id,
    m.name AS milestone_name,
    m.status AS milestone_status,
    COUNT(t.task_id) AS total_tasks,
    COUNT(CASE WHEN t.status = 'done' THEN 1 END) AS completed_tasks,
    COUNT(CASE WHEN t.status = 'failed' THEN 1 END) AS failed_tasks,
    COUNT(CASE WHEN t.status = 'blocked' THEN 1 END) AS blocked_tasks,
    ROUND(
        100.0 * COUNT(CASE WHEN t.status = 'done' THEN 1 END) /
        NULLIF(COUNT(t.task_id), 0),
        2
    ) AS progress_percent,
    SUM(t.story_points) AS total_story_points,
    SUM(CASE WHEN t.status = 'done' THEN t.story_points ELSE 0 END) AS completed_story_points
FROM masterplan_milestones m
LEFT JOIN masterplan_tasks t ON m.milestone_id = t.milestone_id
GROUP BY m.milestone_id, m.phase_id, m.name, m.status;

-- Vista: Tasks listas para ejecutar (dependencias satisfechas)
CREATE VIEW masterplan_executable_tasks AS
SELECT
    t.task_id,
    t.milestone_id,
    t.title,
    t.priority,
    t.estimated_time_minutes,
    t.assigned_agent,
    t.depends_on
FROM masterplan_tasks t
WHERE
    t.status = 'pending'
    AND (
        -- No tiene dependencias
        t.depends_on = '{}'
        OR
        -- Todas las dependencias están completadas
        NOT EXISTS (
            SELECT 1
            FROM unnest(t.depends_on) dep_id
            LEFT JOIN masterplan_tasks dep ON dep.task_id = dep_id
            WHERE dep.status != 'done'
        )
    )
ORDER BY
    CASE t.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    t.created_at;
```

---

## 🔧 Integración con el Sistema Actual

### Cambios en el Flujo Actual

#### 1. En `OrchestratorAgent`

**ANTES:**
```python
def orchestrate(user_request, context):
    # Analiza, descompone, ejecuta tareas
    # NO hay persistencia estructurada
    return result
```

**DESPUÉS:**
```python
def orchestrate(user_request, context):
    # 1. Crear MasterPlan
    masterplan = self.create_masterplan(user_request, context)

    # 2. Mostrar al usuario (WebSocket)
    await self.present_masterplan_for_approval(masterplan)

    # 3. Esperar aprobación del usuario
    approved = await self.wait_for_user_approval()

    if not approved:
        return {"cancelled": True}

    # 4. Ejecutar según MasterPlan
    result = await self.execute_masterplan(masterplan)

    return result
```

#### 2. Nuevos Métodos en `OrchestratorAgent`

```python
class OrchestratorAgent:

    async def create_masterplan(self, user_request: str, context: dict) -> MasterPlan:
        """
        Genera MasterPlan completo analizando el pedido.

        Pasos:
        1. Analizar complejidad y alcance
        2. Proponer stack tecnológico
        3. Identificar entidades
        4. Descomponer en tareas atómicas
        5. Construir grafo de dependencias
        6. Estimar tiempos
        """
        pass

    async def present_masterplan_for_approval(self, masterplan: MasterPlan):
        """
        Emite el MasterPlan via WebSocket para que el usuario lo vea.
        """
        await self.websocket.emit('masterplan_created', {
            'masterplan': masterplan.to_dict(),
            'awaiting_approval': True
        })

    async def wait_for_user_approval(self) -> bool:
        """
        Espera evento 'masterplan_approved' o 'masterplan_rejected' del usuario.
        """
        pass

    async def execute_masterplan(self, masterplan: MasterPlan):
        """
        Ejecuta todas las tareas según el MasterPlan, respetando dependencias.
        Actualiza status de cada tarea en tiempo real.
        """
        for task in masterplan.get_executable_tasks():  # Respeta dependencias
            await self.execute_task(task, masterplan)
            task.status = 'done'
            await self.update_masterplan(masterplan)

    async def update_masterplan(self, masterplan: MasterPlan):
        """
        Persiste cambios en PostgreSQL y emite actualización via WebSocket.
        """
        masterplan.save_to_db()
        await self.websocket.emit('masterplan_updated', {
            'masterplan': masterplan.to_dict()
        })
```

#### 3. Nueva Clase `MasterPlan`

```python
# src/state/masterplan.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

@dataclass
class Task:
    task_id: str
    title: str
    description: str
    task_type: str  # 'implementation', 'testing', 'documentation'
    complexity: str  # 'low', 'medium', 'high'
    estimated_time_minutes: int
    depends_on: List[str] = field(default_factory=list)
    assigned_agent: str = ""
    status: str = "pending"
    status_metadata: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None

    def can_execute(self, completed_tasks: List[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep in completed_tasks for dep in self.depends_on)

@dataclass
class MasterPlan:
    masterplan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = ""
    conversation_id: str = ""
    project_name: str = ""
    user_request_original: str = ""
    status: str = "draft"  # draft, approved, in_progress, completed, failed

    # Core data
    stack: Dict[str, Any] = field(default_factory=dict)
    business_logic: Dict[str, Any] = field(default_factory=dict)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def get_executable_tasks(self) -> List[Task]:
        """Return tasks that can be executed now (dependencies met)."""
        completed = [t.task_id for t in self.tasks if t.status == 'done']
        return [t for t in self.tasks if t.status == 'pending' and t.can_execute(completed)]

    def get_progress(self) -> Dict[str, Any]:
        """Calculate current progress."""
        total = len(self.tasks)
        done = len([t for t in self.tasks if t.status == 'done'])
        in_progress = len([t for t in self.tasks if t.status == 'in_progress'])
        failed = len([t for t in self.tasks if t.status == 'failed'])

        return {
            'total_tasks': total,
            'completed_tasks': done,
            'in_progress_tasks': in_progress,
            'failed_tasks': failed,
            'progress_percent': (done / total * 100) if total > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'masterplan_id': self.masterplan_id,
            'workspace_id': self.workspace_id,
            'project_name': self.project_name,
            'status': self.status,
            'stack': self.stack,
            'business_logic': self.business_logic,
            'entities': self.entities,
            'tasks': [vars(t) for t in self.tasks],
            'dependency_graph': self.dependency_graph,
            'progress': self.get_progress(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def save_to_db(self):
        """Persist to PostgreSQL."""
        from src.state.postgres_manager import PostgresManager
        db = PostgresManager()
        db.save_masterplan(self)
```

#### 4. Nuevos Endpoints WebSocket

```python
# src/api/routers/websocket.py

@sio.event
async def approve_masterplan(sid, data):
    """
    User approves the MasterPlan to start execution.

    Expected data:
        {
            "masterplan_id": "mp_uuid_1234",
            "modifications": {...}  # optional changes
        }
    """
    masterplan_id = data.get('masterplan_id')
    modifications = data.get('modifications')

    # Apply modifications if any
    if modifications:
        masterplan_service.apply_modifications(masterplan_id, modifications)

    # Update status and start execution
    masterplan_service.approve_and_execute(masterplan_id)

@sio.event
async def reject_masterplan(sid, data):
    """
    User rejects the MasterPlan.
    """
    masterplan_id = data.get('masterplan_id')
    masterplan_service.reject(masterplan_id)

@sio.event
async def get_masterplan(sid, data):
    """
    Get current MasterPlan for a workspace.
    """
    workspace_id = data.get('workspace_id')
    masterplan = masterplan_service.get_by_workspace(workspace_id)

    await sio.emit('masterplan_data', {
        'masterplan': masterplan.to_dict() if masterplan else None
    }, room=sid)
```

#### 5. Nuevo Componente React: `MasterPlanView`

```typescript
// src/ui/src/components/masterplan/MasterPlanView.tsx

interface MasterPlanViewProps {
  workspaceId: string;
}

export function MasterPlanView({ workspaceId }: MasterPlanViewProps) {
  const [masterplan, setMasterplan] = useState<MasterPlan | null>(null);
  const { socket } = useWebSocket();

  useEffect(() => {
    // Request MasterPlan
    socket.emit('get_masterplan', { workspace_id: workspaceId });

    // Listen for updates
    socket.on('masterplan_created', handleMasterPlanCreated);
    socket.on('masterplan_updated', handleMasterPlanUpdated);

    return () => {
      socket.off('masterplan_created');
      socket.off('masterplan_updated');
    };
  }, [workspaceId]);

  const handleApprove = () => {
    socket.emit('approve_masterplan', {
      masterplan_id: masterplan.masterplan_id
    });
  };

  const handleReject = () => {
    socket.emit('reject_masterplan', {
      masterplan_id: masterplan.masterplan_id
    });
  };

  return (
    <div className="masterplan-view">
      <h2>📋 MasterPlan: {masterplan?.project_name}</h2>

      {/* Stack Section */}
      <section>
        <h3>📦 Stack Tecnológico</h3>
        {/* Render stack details */}
      </section>

      {/* Entities Section */}
      <section>
        <h3>🏗️ Entidades</h3>
        {/* Render entities */}
      </section>

      {/* Tasks Section */}
      <section>
        <h3>📝 Tareas</h3>
        <TaskList tasks={masterplan?.tasks} />

        {/* Progress Bar */}
        <ProgressBar progress={masterplan?.progress} />
      </section>

      {/* Actions */}
      {masterplan?.status === 'draft' && (
        <div className="actions">
          <button onClick={handleApprove}>✅ Aprobar y Ejecutar</button>
          <button onClick={handleReject}>❌ Rechazar</button>
        </div>
      )}
    </div>
  );
}
```

---

## 🔄 Modificaciones al MasterPlan Durante Ejecución

### Escenario: Usuario Agrega Nuevos Requisitos

```
Usuario (durante ejecución): "Agrega también un endpoint para exportar usuarios a CSV"
```

**Flujo de modificación**:

```python
class MasterPlanModificationService:
    """
    Maneja modificaciones al MasterPlan durante la ejecución.
    """

    async def handle_modification_request(
        self,
        masterplan_id: str,
        new_requirement: str,
        conversation_id: str
    ):
        """
        1. PAUSAR ejecución actual
        2. Analizar nueva solicitud
        3. Calcular impacto en plan existente
        4. Generar nuevas tareas/fases
        5. Presentar cambios al usuario para aprobación
        6. Resumir ejecución
        """

        # 1. Pausar ejecución
        masterplan = await self.pause_execution(masterplan_id)
        current_state = self.capture_current_state(masterplan)

        # 2. Analizar nueva solicitud con Discovery (si es complejo)
        if self.requires_discovery(new_requirement):
            discovery_supplement = await discovery_agent.analyze_supplement(
                new_requirement,
                existing_masterplan=masterplan
            )
        else:
            discovery_supplement = None

        # 3. Análisis de impacto
        impact_analysis = await self.analyze_impact(
            masterplan=masterplan,
            new_requirement=new_requirement,
            discovery=discovery_supplement
        )

        # 4. Generar plan modificado
        modified_plan = await self.generate_modified_plan(
            original_masterplan=masterplan,
            impact_analysis=impact_analysis,
            new_requirement=new_requirement
        )

        # 5. Presentar al usuario
        await self.present_modification_for_approval(
            conversation_id=conversation_id,
            original_plan=masterplan,
            modified_plan=modified_plan,
            impact_analysis=impact_analysis
        )

        # Esperar aprobación del usuario
        approved = await self.wait_for_modification_approval(conversation_id)

        if approved:
            # 6. Crear nueva versión del MasterPlan
            new_version = await self.create_masterplan_version(
                original=masterplan,
                modified=modified_plan,
                change_reason=new_requirement
            )

            # 7. Resumir ejecución desde el punto donde se pausó
            await self.resume_execution(new_version, from_state=current_state)

        return approved

    async def analyze_impact(
        self,
        masterplan: MasterPlan,
        new_requirement: str,
        discovery: Optional[DiscoveryDocument]
    ) -> ImpactAnalysis:
        """
        Analiza el impacto de la modificación en el plan existente.
        """
        impact = ImpactAnalysis()

        # Usar LLM para análisis inteligente
        analysis_prompt = f"""
        MasterPlan actual: {masterplan.to_dict()}
        Progreso actual: {masterplan.get_progress()}

        Nueva solicitud: {new_requirement}

        Analiza el impacto:

        1. ¿Afecta a tareas ya completadas? (requiere refactoring)
        2. ¿Afecta a tareas en progreso? (requiere re-análisis)
        3. ¿Es independiente de lo existente? (agregar al final)
        4. ¿Requiere nuevas dependencias? (npm install, etc.)
        5. ¿Cambia el stack tecnológico?
        6. ¿Requiere modificar entidades existentes?
        7. ¿Cuántas tareas nuevas se necesitan?
        8. ¿Dónde insertar las nuevas tareas? (phase, milestone)
        """

        llm_analysis = await self.llm.analyze(analysis_prompt)

        impact.affected_completed_tasks = llm_analysis.get('affected_completed_tasks', [])
        impact.affected_in_progress_tasks = llm_analysis.get('affected_in_progress_tasks', [])
        impact.new_dependencies = llm_analysis.get('new_dependencies', [])
        impact.new_tasks_count = llm_analysis.get('new_tasks_count', 0)
        impact.estimated_additional_time = llm_analysis.get('estimated_time_hours', 0)
        impact.requires_refactoring = len(impact.affected_completed_tasks) > 0
        impact.insertion_point = llm_analysis.get('insertion_point')  # {"phase": "phase_03", "milestone": "milestone_03_02"}

        return impact

    async def present_modification_for_approval(
        self,
        conversation_id: str,
        original_plan: MasterPlan,
        modified_plan: MasterPlan,
        impact_analysis: ImpactAnalysis
    ):
        """
        Muestra al usuario el análisis de impacto y el plan modificado.
        """
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 MODIFICACIÓN AL MASTERPLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ESTADO ACTUAL:
  • Progreso: {original_plan.get_progress()['progress_percent']:.1f}%
  • Tareas completadas: {original_plan.get_progress()['completed_tasks']}
  • Tareas pendientes: {original_plan.get_progress()['total_tasks'] - original_plan.get_progress()['completed_tasks']}

🎯 NUEVA SOLICITUD:
  {impact_analysis.new_requirement}

📈 ANÁLISIS DE IMPACTO:

{"⚠️  REQUIERE REFACTORING" if impact_analysis.requires_refactoring else "✅ No afecta tareas completadas"}

{"📝 Tareas completadas afectadas:" if impact_analysis.affected_completed_tasks else ""}
{chr(10).join([f"  • {t}" for t in impact_analysis.affected_completed_tasks])}

{"🔄 Tareas en progreso afectadas:" if impact_analysis.affected_in_progress_tasks else ""}
{chr(10).join([f"  • {t}" for t in impact_analysis.affected_in_progress_tasks])}

➕ NUEVAS TAREAS A AGREGAR: {impact_analysis.new_tasks_count}

📦 NUEVAS DEPENDENCIAS:
{chr(10).join([f"  • {dep}" for dep in impact_analysis.new_dependencies])}

⏱️  TIEMPO ADICIONAL ESTIMADO: {impact_analysis.estimated_additional_time} horas

📍 INSERCIÓN EN:
  • Phase: {impact_analysis.insertion_point['phase']}
  • Milestone: {impact_analysis.insertion_point['milestone']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PLAN MODIFICADO (Resumen):

{self._format_plan_summary(modified_plan)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

¿Aprobar modificación?
[✅ Aprobar]  [❌ Rechazar]  [📝 Ajustar]
"""

        await websocket.emit('masterplan_modification_proposal', {
            'original_plan': original_plan.to_dict(),
            'modified_plan': modified_plan.to_dict(),
            'impact_analysis': impact_analysis.to_dict(),
            'message': message
        }, room=conversation_id)
```

---

## ⏸️ Pausar y Resumir Ejecución

### Casos de Uso

1. **Usuario pausa manualmente** - Necesita revisar algo, tomar un break
2. **Sistema pausa por modificación** - Nueva solicitud requiere re-análisis
3. **Sistema pausa por error crítico** - Fallo que requiere intervención
4. **Sistema pausa por aprobación pendiente** - Decisión del usuario necesaria

### Implementación

```python
class ExecutionControlService:
    """
    Controla la ejecución del MasterPlan (pausar, resumir, cancelar).
    """

    async def pause_execution(
        self,
        masterplan_id: str,
        reason: str,
        paused_by: str = "user"
    ):
        """
        Pausa la ejecución del MasterPlan.

        1. Detiene todas las tareas en progreso (gracefully)
        2. Guarda el estado actual (snapshot)
        3. Marca MasterPlan como "paused"
        """
        masterplan = await self.get_masterplan(masterplan_id)

        # Capturar estado actual
        snapshot = ExecutionSnapshot(
            masterplan_id=masterplan_id,
            paused_at=datetime.now(),
            paused_by=paused_by,
            reason=reason,

            # Estado de cada tarea
            tasks_state={
                task.task_id: {
                    'status': task.status,
                    'attempt_count': task.attempt_count,
                    'started_at': task.started_at,
                    'partial_output': task.output  # Si hay output parcial
                }
                for task in masterplan.get_all_tasks()
            },

            # Tareas que estaban ejecutándose
            in_progress_tasks=[
                task.task_id
                for task in masterplan.get_all_tasks()
                if task.status == 'in_progress'
            ],

            # Scratchpad state
            scratchpad_state=scratchpad.get_full_state()
        )

        # Guardar snapshot
        await self.save_execution_snapshot(snapshot)

        # Detener agentes activos
        for task_id in snapshot.in_progress_tasks:
            await agent_manager.stop_task(task_id, gracefully=True)

        # Actualizar status del MasterPlan
        masterplan.status = 'paused'
        masterplan.paused_at = datetime.now()
        masterplan.pause_reason = reason
        await masterplan.save()

        # Emitir evento
        await websocket.emit('masterplan_paused', {
            'masterplan_id': masterplan_id,
            'reason': reason,
            'snapshot_id': snapshot.snapshot_id,
            'can_resume': True
        })

        return snapshot

    async def resume_execution(
        self,
        masterplan_id: str,
        from_snapshot: Optional[str] = None
    ):
        """
        Reanuda la ejecución del MasterPlan desde donde se pausó.
        """
        masterplan = await self.get_masterplan(masterplan_id)

        if masterplan.status != 'paused':
            raise ValueError(f"MasterPlan is not paused (status: {masterplan.status})")

        # Cargar snapshot más reciente si no se especifica
        if not from_snapshot:
            snapshot = await self.get_latest_snapshot(masterplan_id)
        else:
            snapshot = await self.load_snapshot(from_snapshot)

        # Restaurar scratchpad state
        scratchpad.restore_state(snapshot.scratchpad_state)

        # Actualizar status
        masterplan.status = 'in_progress'
        masterplan.resumed_at = datetime.now()
        await masterplan.save()

        # Emitir evento
        await websocket.emit('masterplan_resumed', {
            'masterplan_id': masterplan_id,
            'resumed_from': snapshot.snapshot_id
        })

        # Continuar ejecución desde las tareas pendientes
        await orchestrator.execute_masterplan(
            masterplan=masterplan,
            resume_from_snapshot=snapshot
        )

    async def cancel_execution(
        self,
        masterplan_id: str,
        reason: str
    ):
        """
        Cancela la ejecución del MasterPlan permanentemente.
        """
        masterplan = await self.get_masterplan(masterplan_id)

        # Detener todas las tareas activas
        await self.pause_execution(masterplan_id, reason, paused_by="system")

        # Marcar como cancelado
        masterplan.status = 'cancelled'
        masterplan.cancelled_at = datetime.now()
        masterplan.cancellation_reason = reason
        await masterplan.save()

        await websocket.emit('masterplan_cancelled', {
            'masterplan_id': masterplan_id,
            'reason': reason
        })
```

### Tabla de Snapshots

```sql
-- Tabla de snapshots de ejecución
CREATE TABLE masterplan_execution_snapshots (
    snapshot_id UUID PRIMARY KEY,
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) ON DELETE CASCADE,

    paused_at TIMESTAMP NOT NULL DEFAULT NOW(),
    paused_by VARCHAR(50),  -- 'user', 'system'
    reason TEXT,

    -- Estado completo al momento de pausar
    tasks_state JSONB NOT NULL,
    in_progress_tasks TEXT[] DEFAULT '{}',
    scratchpad_state JSONB,

    -- Metadata
    can_resume BOOLEAN DEFAULT TRUE,
    resumed_at TIMESTAMP
);

CREATE INDEX idx_snapshots_masterplan ON masterplan_execution_snapshots(masterplan_id);
CREATE INDEX idx_snapshots_paused_at ON masterplan_execution_snapshots(paused_at);
```

---

## 📚 Versionado de MasterPlans

### Sistema de Versiones

Cada modificación aprobada crea una nueva versión del MasterPlan:

```
v1 (original) → v2 (added CSV export) → v3 (added email notifications)
```

### Tabla de Versiones

```sql
-- Tabla de versiones del MasterPlan
CREATE TABLE masterplan_versions (
    version_id UUID PRIMARY KEY,
    masterplan_id UUID NOT NULL REFERENCES masterplans(masterplan_id) ON DELETE CASCADE,

    version_number INTEGER NOT NULL,

    -- Snapshot completo del plan en esta versión
    plan_snapshot JSONB NOT NULL,  -- Estructura completa: phases, milestones, tasks, subtasks

    -- Qué cambió
    change_summary TEXT NOT NULL,
    change_type VARCHAR(50),  -- 'initial', 'modification', 'refactoring', 'scope_reduction'
    changes_detail JSONB,  -- Diff detallado

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50),
    parent_version_id UUID REFERENCES masterplan_versions(version_id),

    -- Estado cuando se creó esta versión
    progress_at_creation JSONB,

    CONSTRAINT unique_version_number UNIQUE (masterplan_id, version_number)
);

CREATE INDEX idx_versions_masterplan ON masterplan_versions(masterplan_id);
CREATE INDEX idx_versions_number ON masterplan_versions(masterplan_id, version_number);
CREATE INDEX idx_versions_parent ON masterplan_versions(parent_version_id);
```

### Creación de Versiones

```python
async def create_masterplan_version(
    self,
    original: MasterPlan,
    modified: MasterPlan,
    change_reason: str
) -> MasterPlanVersion:
    """
    Crea una nueva versión del MasterPlan.
    """

    # Obtener última versión
    latest_version = await self.get_latest_version(original.masterplan_id)
    new_version_number = (latest_version.version_number + 1) if latest_version else 1

    # Calcular diff
    changes_detail = self.compute_diff(
        old_plan=original.to_dict(),
        new_plan=modified.to_dict()
    )

    # Crear versión
    version = MasterPlanVersion(
        version_id=uuid.uuid4(),
        masterplan_id=original.masterplan_id,
        version_number=new_version_number,
        plan_snapshot=modified.to_dict(),
        change_summary=change_reason,
        change_type='modification',
        changes_detail=changes_detail,
        created_by='user',
        parent_version_id=latest_version.version_id if latest_version else None,
        progress_at_creation=original.get_progress()
    )

    await version.save()

    # Registrar en historial
    await history_service.record_change(
        masterplan_id=original.masterplan_id,
        change_type='version_created',
        change_description=f'Version {new_version_number}: {change_reason}',
        new_value={'version_id': str(version.version_id)}
    )

    return version

def compute_diff(self, old_plan: dict, new_plan: dict) -> dict:
    """
    Calcula diferencias entre dos versiones del plan.
    """
    diff = {
        'phases_added': [],
        'phases_removed': [],
        'phases_modified': [],
        'milestones_added': [],
        'milestones_removed': [],
        'tasks_added': [],
        'tasks_removed': [],
        'tasks_modified': [],
        'stack_changes': {},
        'entities_added': [],
        'entities_modified': []
    }

    # Comparar phases
    old_phase_ids = {p['phase_id'] for p in old_plan.get('phases', [])}
    new_phase_ids = {p['phase_id'] for p in new_plan.get('phases', [])}

    diff['phases_added'] = list(new_phase_ids - old_phase_ids)
    diff['phases_removed'] = list(old_phase_ids - new_phase_ids)

    # ... continuar con milestones, tasks, etc.

    return diff
```

### Ver Historial de Versiones

```python
@sio.event
async def get_masterplan_versions(sid, data):
    """
    Obtiene todas las versiones de un MasterPlan.
    """
    masterplan_id = data.get('masterplan_id')

    versions = await masterplan_service.get_all_versions(masterplan_id)

    await sio.emit('masterplan_versions', {
        'masterplan_id': masterplan_id,
        'versions': [
            {
                'version_id': str(v.version_id),
                'version_number': v.version_number,
                'change_summary': v.change_summary,
                'created_at': v.created_at.isoformat(),
                'created_by': v.created_by,
                'progress_at_creation': v.progress_at_creation,
                'is_current': v.version_number == versions[0].version_number
            }
            for v in versions
        ]
    }, room=sid)
```

---

## 🧠 RAG Learning: Aprendiendo de MasterPlans

### Estrategia: Aprender de TODO

El sistema RAG debe aprender de:

1. **MasterPlans exitosos** - Patrones de estructura, estimaciones precisas
2. **MasterPlans fallidos** - Qué salió mal, estimaciones incorrectas
3. **Modificaciones frecuentes** - Requisitos que se agregan comúnmente
4. **Tareas exitosas** - Código que funcionó a la primera
5. **Tareas fallidas** - Errores comunes, validaciones que fallan

### Colecciones en ChromaDB

```python
RAG_COLLECTIONS = {
    "successful_masterplans": {
        "description": "MasterPlans que se completaron exitosamente",
        "learns_from": "Estructura, estimaciones, stack choices, DDD modeling"
    },

    "failed_masterplans": {
        "description": "MasterPlans que fallaron o fueron cancelados",
        "learns_from": "Qué causó el fallo, estimaciones incorrectas, problemas de diseño"
    },

    "masterplan_modifications": {
        "description": "Modificaciones hechas durante la ejecución",
        "learns_from": "Requisitos que se olvidan inicialmente, patrones de cambio"
    },

    "successful_tasks": {
        "description": "Tareas atómicas que pasaron todas las validaciones",
        "learns_from": "Código que funciona, patrones correctos"
    },

    "failed_tasks": {
        "description": "Tareas que fallaron después de 3 intentos",
        "learns_from": "Errores comunes, validaciones que fallan, preconditions incorrectas"
    },

    "discovery_patterns": {
        "description": "Patrones de Discovery exitosos por industria/dominio",
        "learns_from": "Bounded contexts comunes, aggregates típicos, workflows estándar"
    }
}
```

### Aprendizaje Automático

```python
class MasterPlanRAGLearningService:
    """
    Aprende de MasterPlans completados para mejorar futuras generaciones.
    """

    async def learn_from_completed_masterplan(self, masterplan: MasterPlan):
        """
        Al completarse un MasterPlan, extrae patrones y guarda en RAG.
        """
        if masterplan.status != 'completed':
            return

        # 1. Recopilar métricas de éxito
        metrics = self.calculate_success_metrics(masterplan)

        # 2. Extraer patrones útiles
        patterns = await self.extract_patterns(masterplan, metrics)

        # 3. Guardar en RAG
        if metrics['success_rate'] >= 0.8:  # 80% de tareas exitosas
            await self.save_successful_masterplan(masterplan, patterns, metrics)
        else:
            await self.save_failed_masterplan(masterplan, patterns, metrics)

        # 4. Aprender de modificaciones
        if masterplan.versions_count > 1:
            await self.learn_from_modifications(masterplan)

    def calculate_success_metrics(self, masterplan: MasterPlan) -> dict:
        """
        Calcula métricas de éxito del MasterPlan.
        """
        all_tasks = masterplan.get_all_tasks()
        total = len(all_tasks)

        return {
            'total_tasks': total,
            'completed_tasks': len([t for t in all_tasks if t.status == 'done']),
            'failed_tasks': len([t for t in all_tasks if t.status == 'failed']),
            'success_rate': len([t for t in all_tasks if t.status == 'done']) / total if total > 0 else 0,

            'estimation_accuracy': self._calculate_estimation_accuracy(all_tasks),
            'first_time_success_rate': self._calculate_first_time_success(all_tasks),

            'total_time_estimated': sum(t.estimated_time_minutes for t in all_tasks),
            'total_time_actual': sum(t.actual_time_minutes or 0 for t in all_tasks),
            'time_variance': self._calculate_time_variance(all_tasks),

            'modifications_count': masterplan.versions_count - 1,
            'discovery_quality_score': self._assess_discovery_quality(masterplan)
        }

    async def extract_patterns(self, masterplan: MasterPlan, metrics: dict) -> dict:
        """
        Extrae patrones del MasterPlan usando LLM.
        """
        prompt = f"""
        Analiza este MasterPlan completado y extrae patrones útiles:

        MASTERPLAN:
        - Dominio: {masterplan.business_logic.get('domain')}
        - Stack: {masterplan.stack}
        - Entidades: {len(masterplan.entities)}
        - Tareas: {metrics['total_tasks']}
        - Success Rate: {metrics['success_rate']:.2%}
        - Estimation Accuracy: {metrics['estimation_accuracy']:.2%}

        ESTRUCTURA:
        {json.dumps(masterplan.to_dict(), indent=2)}

        Extrae:
        1. Patrones de estructura de phases/milestones que funcionaron bien
        2. Estimaciones que fueron precisas vs imprecisas
        3. Stack choices acertados para este dominio
        4. Bounded Contexts bien identificados
        5. Dependencias entre tareas que causaron/evitaron problemas
        6. Lecciones aprendidas (qué hacer / qué evitar)
        """

        patterns = await self.llm.analyze(prompt)
        return patterns

    async def save_successful_masterplan(
        self,
        masterplan: MasterPlan,
        patterns: dict,
        metrics: dict
    ):
        """
        Guarda MasterPlan exitoso en RAG.
        """
        document = {
            "masterplan_id": str(masterplan.masterplan_id),
            "project_name": masterplan.project_name,
            "domain": masterplan.business_logic.get('domain'),
            "industry": masterplan.business_logic.get('industry'),

            # Estructura
            "phases_count": len(masterplan.phases),
            "milestones_count": sum(len(p.milestones) for p in masterplan.phases),
            "tasks_count": metrics['total_tasks'],

            # Stack
            "stack": masterplan.stack,

            # Métricas de éxito
            "success_rate": metrics['success_rate'],
            "estimation_accuracy": metrics['estimation_accuracy'],
            "first_time_success_rate": metrics['first_time_success_rate'],

            # Patrones extraídos
            "successful_patterns": patterns.get('successful_patterns', []),
            "stack_choices": patterns.get('stack_choices', {}),
            "ddd_modeling": patterns.get('ddd_modeling', {}),

            # Para búsqueda semántica
            "description": f"""
            MasterPlan exitoso para {masterplan.project_name} en {masterplan.business_logic.get('domain')}.
            Stack: {', '.join([f"{k}={v}" for k,v in masterplan.stack.items()])}.
            {metrics['total_tasks']} tareas con {metrics['success_rate']:.0%} de éxito.
            {patterns.get('summary', '')}
            """,

            "tags": [
                masterplan.business_logic.get('domain'),
                masterplan.business_logic.get('industry'),
                "successful",
                f"success_rate_{int(metrics['success_rate'] * 10) * 10}"  # 80, 90, 100
            ],

            "created_at": datetime.now().isoformat()
        }

        # Agregar a ChromaDB
        await self.rag_system.add_to_collection(
            collection="successful_masterplans",
            document=document,
            embedding_text=document['description']
        )

        logger.info(f"Learned from successful MasterPlan: {masterplan.project_name}")

    async def learn_from_modifications(self, masterplan: MasterPlan):
        """
        Aprende de modificaciones frecuentes.
        """
        versions = await self.get_all_versions(masterplan.masterplan_id)

        for i in range(1, len(versions)):
            prev_version = versions[i-1]
            curr_version = versions[i]

            modification = {
                "masterplan_id": str(masterplan.masterplan_id),
                "domain": masterplan.business_logic.get('domain'),
                "version_from": prev_version.version_number,
                "version_to": curr_version.version_number,
                "change_summary": curr_version.change_summary,
                "changes_detail": curr_version.changes_detail,

                # Analizar el cambio
                "what_was_added": curr_version.changes_detail.get('tasks_added', []),
                "what_was_modified": curr_version.changes_detail.get('tasks_modified', []),
                "new_dependencies": curr_version.changes_detail.get('new_dependencies', []),

                # Contexto
                "progress_when_modified": curr_version.progress_at_creation,

                # Pattern recognition
                "pattern": self._identify_modification_pattern(curr_version.changes_detail),

                "description": f"""
                Modificación común: {curr_version.change_summary}.
                En proyectos de {masterplan.business_logic.get('domain')}, usuarios frecuentemente agregan: {curr_version.changes_detail.get('tasks_added', [])}.
                """,

                "tags": [
                    "modification",
                    masterplan.business_logic.get('domain'),
                    self._identify_modification_pattern(curr_version.changes_detail)
                ]
            }

            await self.rag_system.add_to_collection(
                collection="masterplan_modifications",
                document=modification
            )

    async def use_rag_for_masterplan_generation(
        self,
        user_request: str,
        discovery: DiscoveryDocument
    ) -> dict:
        """
        Usa RAG para mejorar la generación del MasterPlan.
        """

        # 1. Buscar MasterPlans similares exitosos
        similar_successful = await self.rag_system.search(
            query=f"{discovery.business_domain['domain']} {user_request}",
            collection="successful_masterplans",
            top_k=3,
            filters={"success_rate": {"$gte": 0.8}}
        )

        # 2. Buscar modificaciones comunes para este dominio
        common_modifications = await self.rag_system.search(
            query=f"{discovery.business_domain['domain']}",
            collection="masterplan_modifications",
            top_k=5
        )

        # 3. Buscar patrones de Discovery similares
        discovery_patterns = await self.rag_system.search(
            query=f"{discovery.business_domain['industry']} {discovery.business_domain['domain']}",
            collection="discovery_patterns",
            top_k=2
        )

        # 4. Compilar aprendizajes
        learnings = {
            "similar_successful_plans": [
                {
                    "project": mp['project_name'],
                    "stack": mp['stack'],
                    "structure": {
                        "phases": mp['phases_count'],
                        "milestones": mp['milestones_count'],
                        "tasks": mp['tasks_count']
                    },
                    "patterns": mp['successful_patterns'],
                    "estimation_accuracy": mp['estimation_accuracy']
                }
                for mp in similar_successful
            ],

            "common_modifications_to_anticipate": [
                {
                    "modification": mod['change_summary'],
                    "what_users_add": mod['what_was_added'],
                    "pattern": mod['pattern']
                }
                for mod in common_modifications
            ],

            "ddd_patterns_for_industry": [
                {
                    "bounded_contexts": dp.get('typical_bounded_contexts', []),
                    "aggregates": dp.get('common_aggregates', []),
                    "domain_events": dp.get('typical_domain_events', [])
                }
                for dp in discovery_patterns
            ],

            "recommended_stack": self._recommend_stack_from_learnings(similar_successful),
            "estimated_task_count": self._estimate_task_count(similar_successful, discovery),
            "estimated_time_hours": self._estimate_time(similar_successful, discovery)
        }

        return learnings

    def _recommend_stack_from_learnings(self, similar_plans: list) -> dict:
        """
        Recomienda stack basado en planes similares exitosos.
        """
        if not similar_plans:
            return {}

        # Votar por stack más común
        stack_votes = {}
        for plan in similar_plans:
            for component, tech in plan['stack'].items():
                key = f"{component}:{tech}"
                stack_votes[key] = stack_votes.get(key, 0) + 1

        # Reconstruir stack ganador
        recommended = {}
        for key, votes in sorted(stack_votes.items(), key=lambda x: x[1], reverse=True):
            component, tech = key.split(':', 1)
            if component not in recommended:
                recommended[component] = {
                    "technology": tech,
                    "confidence": votes / len(similar_plans),
                    "reason": f"Used in {votes}/{len(similar_plans)} similar successful projects"
                }

        return recommended
```

### Uso de RAG en Generación

```python
# En OrchestratorAgent.create_masterplan()

async def create_masterplan(self, user_request: str, discovery: DiscoveryDocument):
    """
    Genera MasterPlan usando Discovery + RAG learnings.
    """

    # 1. Obtener aprendizajes del RAG
    learnings = await rag_learning_service.use_rag_for_masterplan_generation(
        user_request=user_request,
        discovery=discovery
    )

    # 2. Usar aprendizajes en el prompt del LLM
    masterplan_prompt = f"""
    Genera un MasterPlan para: {user_request}

    DISCOVERY COMPLETO:
    {discovery.to_dict()}

    APRENDIZAJES DE PROYECTOS SIMILARES EXITOSOS:

    Proyectos similares exitosos:
    {json.dumps(learnings['similar_successful_plans'], indent=2)}

    Modificaciones que usuarios frecuentemente agregan (anticipar):
    {json.dumps(learnings['common_modifications_to_anticipate'], indent=2)}

    Stack recomendado basado en éxitos previos:
    {json.dumps(learnings['recommended_stack'], indent=2)}

    Patrones DDD típicos para esta industria:
    {json.dumps(learnings['ddd_patterns_for_industry'], indent=2)}

    Estimación de tareas: ~{learnings['estimated_task_count']} tareas
    Estimación de tiempo: ~{learnings['estimated_time_hours']} horas

    INSTRUCCIONES:

    1. USA el stack recomendado (a menos que el usuario especifique otro)
    2. ANTICIPA las modificaciones comunes (agrégalas al plan inicial)
    3. USA los patrones DDD probados para esta industria
    4. Estructura el plan similar a los exitosos (phases, milestones, granularidad)
    5. Ajusta estimaciones según la precisión histórica

    Genera el MasterPlan completo en formato JSON.
    """

    masterplan_dict = await self.llm.generate(masterplan_prompt)

    # 3. Crear MasterPlan
    masterplan = MasterPlan.from_dict(masterplan_dict)

    return masterplan
```

---

## 📊 Ejemplo Completo: MasterPlan para "API REST de Usuarios"

Ver secciones anteriores que muestran el MasterPlan completo para este caso de uso.

---

## 🎯 Atomicidad de Tareas: Estrategia para 99% de Precisión

### Principio Fundamental

**"1 Responsabilidad, 1 Output Verificable, 0 Ambigüedad"**

Una tarea atómica es aquella que:
- Tiene un único objetivo claro y medible
- Genera exactamente 1 archivo principal (o configura 1 componente)
- Puede ser validada automáticamente en su totalidad
- No supera 200-300 líneas de código
- Puede completarse en 10-15 minutos

### Niveles de Granularidad

#### ✅ Granularidad Correcta

```python
# BIEN - Tarea atómica clara
{
  "task_id": "task_003",
  "title": "Implement User SQLAlchemy model with authentication fields",
  "description": "Create src/models/user.py with User class including id, email, password_hash, created_at fields and relationships",
  "outputs": ["src/models/user.py"],
  "estimated_time": 10,
  "lines_of_code_estimate": 150
}
```

#### ❌ Granularidad Incorrecta

```python
# MAL - Demasiado amplio
{
  "task": "Create complete authentication system",
  "outputs": ["models", "services", "endpoints", "middleware", "tests"]
}
# Problema: Demasiado complejo, alta probabilidad de fallo

# MAL - Demasiado granular
{
  "task": "Import uuid module in user.py"
}
# Problema: Overhead enorme para tarea trivial
```

### Criterios Específicos de Granularidad

| Criterio | Valor | Justificación |
|----------|-------|---------------|
| **Max archivos generados** | 1 archivo principal | Facilita validación y debugging |
| **Max líneas de código** | 200-300 LOC | Agente mantiene contexto completo |
| **Max dependencias directas** | 3-4 tareas | Minimiza cascadas de fallos |
| **Min valor funcional** | 1 feature completo testeable | Debe poder probarse aisladamente |
| **Max tiempo estimado** | 10-15 minutos | Si tarda más, dividir en sub-tareas |
| **Max complejidad ciclomática** | 10 por función | Código mantenible y testeable |

### Ejemplos por Nivel de Complejidad

#### Nivel 1: Setup Tasks (1-3 min)
```python
[
  "Create project directory structure",
  "Create __init__.py files for Python packages",
  "Create requirements.txt with core dependencies",
  "Create .env.example template",
  "Create main.py with FastAPI app initialization"
]
```
**Características**: Triviales, sin dependencias entre sí, ejecutables en paralelo.

#### Nivel 2: Foundation Tasks (5-10 min)
```python
[
  "Setup database configuration (base.py, connection.py)",
  "Setup logging configuration with StructuredLogger",
  "Setup environment config with Pydantic Settings",
  "Create Alembic migration template"
]
```
**Características**: Dependen de setup, pero independientes entre sí.

#### Nivel 3: Model Tasks (8-12 min)
```python
[
  "Implement User SQLAlchemy model with all fields",
  "Implement Role SQLAlchemy model with permissions",
  "Create UserSchema Pydantic for validation",
  "Create RoleSchema Pydantic for validation"
]
```
**Características**: User y Role son independientes, schemas dependen de models.

#### Nivel 4: Business Logic (10-15 min)
```python
[
  "Implement UserRepository with CRUD operations",
  "Implement RoleRepository with CRUD operations",
  "Implement UserService with business rules",
  "Implement AuthService with JWT logic"
]
```

#### Nivel 5: API Endpoints (8-12 min cada uno)
```python
[
  "Implement POST /auth/register endpoint",
  "Implement POST /auth/login endpoint",
  "Implement GET /users endpoint with pagination",
  "Implement GET /users/{id} endpoint",
  "Implement PUT /users/{id} endpoint",
  "Implement DELETE /users/{id} endpoint"
]
```
**Características**: Todos los endpoints son independientes entre sí.

### Contratos Explícitos: Preconditions & Postconditions

Cada tarea DEBE declarar:

```python
{
  "task_id": "task_004",
  "title": "Implement User SQLAlchemy model",

  # ========================================
  # PRECONDITIONS (Qué DEBE existir antes)
  # ========================================
  "preconditions": [
    {
      "type": "file_exists",
      "path": "src/database/base.py",
      "description": "SQLAlchemy Base class definition",
      "critical": True
    },
    {
      "type": "class_available",
      "class": "Base",
      "from": "src.database.base",
      "description": "declarative_base for ORM models"
    },
    {
      "type": "import_available",
      "module": "sqlalchemy",
      "description": "SQLAlchemy library installed"
    },
    {
      "type": "directory_exists",
      "path": "src/models",
      "description": "Models directory structure"
    }
  ],

  # ========================================
  # POSTCONDITIONS (Qué GARANTIZA después)
  # ========================================
  "postconditions": [
    {
      "type": "file_exists",
      "path": "src/models/user.py",
      "description": "User model file created"
    },
    {
      "type": "class_available",
      "class": "User",
      "from": "src.models.user",
      "description": "User class can be imported"
    },
    {
      "type": "syntax_valid",
      "file": "src/models/user.py",
      "description": "Python syntax is correct"
    },
    {
      "type": "imports_resolve",
      "file": "src/models/user.py",
      "description": "All imports can be resolved"
    },
    {
      "type": "table_defined",
      "table": "users",
      "description": "__tablename__ attribute exists"
    },
    {
      "type": "has_primary_key",
      "model": "User",
      "description": "Model has primary key field"
    }
  ],

  # ========================================
  # OUTPUTS ESPERADOS
  # ========================================
  "expected_outputs": {
    "files": ["src/models/user.py"],
    "classes": ["User"],
    "tables": ["users"],
    "exports": ["User"],
    "lines_of_code": "120-180"
  }
}
```

### Contexto Completo para el Agente

El agente NO debe adivinar. Se le proporciona:

```python
{
  "task": {...},

  "context": {
    # Estructura actual del proyecto
    "project_structure": {
      "src/": ["api/", "database/", "models/", "schemas/", "services/"],
      "src/database/": ["__init__.py", "base.py", "connection.py"],
      "src/models/": ["__init__.py"]
    },

    # Archivos relevantes como referencia
    "reference_files": {
      "src/database/base.py": "from sqlalchemy.ext.declarative import declarative_base\n\nBase = declarative_base()\n",
      "src/database/connection.py": "# Database session logic..."
    },

    # Convenciones del proyecto (crítico)
    "conventions": {
      "table_naming": "plural_lowercase",     # users, not Users
      "class_naming": "PascalCase",           # User, not user
      "primary_key_type": "UUID",
      "timestamps": ["created_at", "updated_at"],
      "orm": "sqlalchemy",
      "base_class": "Base from src.database.base",
      "field_naming": "snake_case",
      "use_type_hints": True,
      "docstring_style": "Google"
    },

    # Schema detallado de la entidad
    "entity_schema": {
      "name": "User",
      "table": "users",
      "description": "User authentication and profile model",
      "fields": [
        {
          "name": "id",
          "type": "UUID",
          "sqlalchemy_type": "UUID(as_uuid=True)",
          "primary_key": True,
          "default": "uuid.uuid4",
          "nullable": False
        },
        {
          "name": "email",
          "type": "str",
          "sqlalchemy_type": "String(255)",
          "unique": True,
          "nullable": False,
          "indexed": True
        },
        {
          "name": "password_hash",
          "type": "str",
          "sqlalchemy_type": "String(255)",
          "nullable": False
        },
        {
          "name": "full_name",
          "type": "Optional[str]",
          "sqlalchemy_type": "String(255)",
          "nullable": True
        },
        {
          "name": "is_active",
          "type": "bool",
          "sqlalchemy_type": "Boolean",
          "default": True
        },
        {
          "name": "created_at",
          "type": "datetime",
          "sqlalchemy_type": "DateTime",
          "default": "datetime.utcnow",
          "nullable": False
        }
      ],
      "relations": [
        {
          "name": "role",
          "type": "many_to_one",
          "target": "Role",
          "foreign_key": "role_id",
          "back_populates": "users"
        }
      ],
      "indexes": [
        {"fields": ["email"], "unique": True, "name": "ix_users_email"}
      ]
    },

    # Ejemplos similares del RAG
    "successful_examples": [
      {
        "description": "SQLAlchemy User model with UUID and timestamps",
        "code": "from sqlalchemy import Column, String, Boolean, DateTime\nfrom sqlalchemy.dialects.postgresql import UUID\nimport uuid\nfrom datetime import datetime\nfrom src.database.base import Base\n\nclass User(Base):\n    __tablename__ = 'users'\n    \n    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)\n    email = Column(String(255), unique=True, nullable=False, index=True)\n    password_hash = Column(String(255), nullable=False)\n    is_active = Column(Boolean, default=True)\n    created_at = Column(DateTime, default=datetime.utcnow)\n    \n    def __repr__(self):\n        return f'<User {self.email}>'",
        "source": "task_042_successful",
        "similarity_score": 0.94
      }
    ],

    # Errores comunes a EVITAR
    "common_mistakes_to_avoid": [
      {
        "mistake": "Using String instead of String(255)",
        "error": "TypeError: String requires length",
        "how_to_avoid": "Always specify length for String type: String(255)"
      },
      {
        "mistake": "Forgetting to import UUID from sqlalchemy.dialects.postgresql",
        "error": "NameError: name 'UUID' is not defined",
        "how_to_avoid": "Import: from sqlalchemy.dialects.postgresql import UUID"
      }
    ]
  }
}
```

---

## 🔄 Sistema de Re-intentos Inteligente

### Estrategia: 3 Intentos con Feedback Progresivo

Cada intento proporciona feedback cada vez MÁS detallado:

```python
class TaskExecutionStrategy:

    async def execute_with_intelligent_retries(
        self,
        task: AtomicTask,
        agent: Agent,
        max_attempts: int = 3
    ) -> TaskResult:
        """
        Ejecuta tarea con re-intentos progresivamente más detallados.
        """

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Task {task.task_id} - Attempt {attempt}/{max_attempts}")

            # Preparar contexto según el intento
            context = self.prepare_context_for_attempt(task, attempt)

            # Ejecutar agente
            result = await agent.execute(task, context)

            # Validar resultado
            validation = await self.validate_comprehensive(task, result)

            if validation.all_passed:
                # ✅ Éxito
                return TaskResult(
                    success=True,
                    output=result,
                    attempts=attempt,
                    validation=validation
                )

            # ❌ Falló - Generar feedback progresivo
            feedback = self.generate_progressive_feedback(
                task, result, validation, attempt
            )

            # Guardar en historial
            task.attempt_history.append({
                "attempt": attempt,
                "result": result,
                "validation": validation,
                "feedback": feedback
            })

            await self.emit_retry_event(task, attempt, feedback)

        # Después de 3 intentos → Análisis profundo
        return await self.handle_persistent_failure(task)
```

### Feedback Progresivo por Intento

#### Intento 1: Feedback Básico
```
❌ Syntax Error en línea 15: invalid syntax
❌ Import Error: sqlalchemy.UUID no se puede resolver
❌ Type Error: String requires a length argument
```

#### Intento 2: Feedback + Ejemplos del RAG
```
❌ Syntax Error en línea 15: invalid syntax

EJEMPLO de cómo resolverlo:
from sqlalchemy.dialects.postgresql import UUID

❌ Import Error: sqlalchemy.UUID no se puede resolver

SOLUCIÓN:
El tipo UUID no está en sqlalchemy directamente.
Usa: from sqlalchemy.dialects.postgresql import UUID
```

#### Intento 3: Feedback + Diff + Sugerencias Específicas
```
❌ Type Error: String requires a length argument

SUGERENCIAS ESPECÍFICAS:
Línea 12: Column(String, unique=True)
          ^^^^^^^^^^^^^^^^
          Cambiar a: Column(String(255), unique=True)

DIFF RECOMENDADO:
- email = Column(String, unique=True)
+ email = Column(String(255), unique=True, index=True)

EXPLICACIÓN:
SQLAlchemy String siempre requiere longitud máxima.
Usa String(255) para emails (estándar de la industria).
Agrega index=True para queries rápidas por email.
```

---

## 🚨 Manejo de Fallos Persistentes

Cuando una tarea falla después de 3 intentos, activar **DebugAgent**:

### DebugAgent: Análisis con Máximo Uso de LLM

```python
async def handle_persistent_failure(self, task: AtomicTask) -> TaskResult:
    """
    Analiza fallo persistente con LLM y propone soluciones.
    """

    # 1. Recopilar TODO el contexto
    failure_context = {
        "task": task.to_dict(),
        "attempt_history": task.attempt_history,
        "all_errors": [v.errors for v in task.attempt_history],
        "project_state": scratchpad.get_full_state(),
        "recent_successful_tasks": self.get_recent_successful_tasks(5)
    }

    # 2. DebugAgent analiza con LLM
    debug_agent = DebugAgent(llm=self.llm)

    analysis = await debug_agent.analyze_persistent_failure(failure_context)
    # Usa LLM para encontrar CAUSA RAÍZ, no solo síntoma

    # 3. Proponer múltiples soluciones
    proposals = await debug_agent.propose_solutions(analysis)
    # LLM genera 3 soluciones ordenadas por probabilidad de éxito

    # 4. Emitir al usuario para intervención
    await self.emit_failure_analysis({
        "task_id": task.task_id,
        "analysis": analysis,
        "proposals": proposals,
        "requires_user_intervention": True
    })

    return TaskResult(
        success=False,
        failure_reason="persistent_failure",
        analysis=analysis,
        proposals=proposals,
        awaiting_user_decision=True
    )
```

### Ejemplo de Análisis de DebugAgent

```json
{
  "task_id": "task_003",
  "task_title": "Implement User SQLAlchemy model",
  "status": "failed_persistently",
  "attempts": 3,

  "analysis": {
    "root_cause": "Missing database Base class definition",
    "symptoms": [
      "Import error: 'from src.database.base import Base'",
      "File src/database/base.py does not exist"
    ],
    "why_retries_failed": [
      "Agent kept trying to import non-existent Base",
      "Precondition 'file_exists: src/database/base.py' was not properly verified before execution"
    ],
    "hidden_dependency": "Task depends on task_002 (Setup database config) which was not completed",
    "conclusion": "The task logic is correct, but a critical dependency was not created first."
  },

  "proposed_solutions": [
    {
      "id": "sol_1",
      "title": "Create missing database base configuration",
      "description": "Create src/database/base.py with SQLAlchemy declarative base, then retry task_003",
      "action": "create_dependency_task",
      "new_tasks": [{
        "task_id": "task_002b",
        "title": "Create SQLAlchemy Base configuration",
        "priority": "critical",
        "insert_before": "task_003"
      }],
      "success_probability": 95,
      "estimated_time_minutes": 3
    },
    {
      "id": "sol_2",
      "title": "Modify task to be self-contained",
      "description": "Change task_003 to create both base.py AND user.py together",
      "action": "modify_task_scope",
      "success_probability": 75,
      "estimated_time_minutes": 8
    },
    {
      "id": "sol_3",
      "title": "Define Base inline (workaround)",
      "description": "Allow task to define declarative_base() inline in user.py",
      "action": "modify_task_context",
      "success_probability": 60,
      "note": "Not recommended for production, but unblocks the task"
    }
  ],

  "user_options": [
    "Apply Solution 1 (Recommended)",
    "Apply Solution 2",
    "Provide manual fix",
    "Skip this task",
    "Pause MasterPlan execution"
  ]
}
```

---

## 🧠 RAG Learning System: Éxitos Y Fracasos

### Estrategia Dual: Aprender de Ambos

```python
class RAGLearningSystem:
    """
    Aprende TANTO de éxitos como de fracasos.
    """

    async def learn_from_success(self, task: AtomicTask, result: TaskResult):
        """
        Guarda ejemplo exitoso para futuras tareas similares.
        """
        example = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "title": task.title,
            "description": task.description,
            "context": task.context,
            "code": result.output.code,
            "validation_passed": True,
            "validation_results": result.validation.to_dict(),
            "tags": self._extract_tags(task),
            "success_factors": [
                "preconditions_met",
                "clear_schema_provided",
                "good_examples_from_rag"
            ],
            "created_at": datetime.now()
        }

        await self.rag_system.add_to_collection(
            collection="successful_tasks",
            document=example
        )

    async def learn_from_failure(self, task: AtomicTask, failure_analysis: FailureAnalysis):
        """
        Guarda patrón de fallo para EVITARLO en el futuro.
        """
        failure_pattern = {
            "task_type": task.task_type,
            "failure_signature": self._compute_failure_signature(task, failure_analysis),
            "root_cause": failure_analysis.root_cause,
            "error_patterns": failure_analysis.errors,
            "context_that_led_to_failure": task.context,
            "what_was_missing": failure_analysis.missing_preconditions,
            "solution_that_worked": None,  # Se actualiza si luego funciona
            "tags": self._extract_tags(task) + ["failure", "avoid"],
            "created_at": datetime.now()
        }

        await self.rag_system.add_to_collection(
            collection="failure_patterns",
            document=failure_pattern
        )
```

### Uso Dual en Preparación de Tareas

```python
async def prepare_task_with_dual_learning(self, task: AtomicTask):
    """
    Enriquece contexto con ejemplos positivos Y negativos.
    """

    # 1. Buscar ejemplos exitosos (qué HACER)
    successful_examples = await rag_system.search(
        query=f"{task.title} {task.description}",
        collection="successful_tasks",
        filters={"validation_passed": True},
        top_k=3
    )

    # 2. Buscar patrones de fallo (qué NO hacer)
    failure_patterns = await rag_system.search(
        query=f"{task.title} {task.description}",
        collection="failure_patterns",
        top_k=2
    )

    # 3. Enriquecer contexto
    task.context['successful_examples'] = [
        {"code": ex.code, "why_it_worked": ex.success_factors}
        for ex in successful_examples
    ]

    task.context['common_mistakes_to_avoid'] = [
        {"mistake": fp.root_cause, "how_to_avoid": fp.what_was_missing}
        for fp in failure_patterns
    ]

    return task.context
```

**Beneficio**: El agente ve ejemplos de éxito Y aprende de errores previos.

---

## ✅ Validación Estricta: TODAS Deben Pasar

### Capas de Validación

```python
VALIDATION_LAYERS = [
    ("syntax", SyntaxValidator, "critical"),
    ("imports", ImportValidator, "critical"),
    ("types", TypeValidator, "critical"),
    ("postconditions", PostconditionValidator, "critical"),
    ("linting", LintingValidator, "important"),
    ("security", SecurityValidator, "important"),
    ("performance", PerformanceValidator, "nice_to_have"),
]
```

### Validación Estricta

```python
class StrictValidator:

    async def validate_strict(self, task: AtomicTask, output: TaskOutput):
        """
        TODAS las validaciones críticas e importantes deben pasar.
        """
        results = []

        for name, validator_class, severity in self.VALIDATION_LAYERS:
            validator = validator_class()
            result = await validator.validate(output)
            result.severity = severity
            results.append(result)

            # Si falla validación crítica, DETENER
            if not result.passed and severity == "critical":
                return ValidationResult(
                    all_passed=False,
                    first_failure=result,
                    can_proceed=False
                )

        # Verificar que TODAS críticas e importantes pasaron
        critical_passed = all(r.passed for r in results if r.severity == "critical")
        important_passed = all(r.passed for r in results if r.severity == "important")

        return ValidationResult(
            all_passed=critical_passed and important_passed,
            critical_passed=critical_passed,
            important_passed=important_passed,
            results=results,
            can_proceed=critical_passed and important_passed
        )
```

### Validadores Específicos

#### 1. SyntaxValidator
```python
class SyntaxValidator:
    async def validate(self, output: TaskOutput):
        for file_path, content in output.files.items():
            try:
                ast.parse(content)
            except SyntaxError as e:
                return ValidationResult(
                    passed=False,
                    error=f"Syntax error in {file_path} line {e.lineno}: {e.msg}"
                )
        return ValidationResult(passed=True)
```

#### 2. ImportValidator
```python
class ImportValidator:
    async def validate(self, output: TaskOutput):
        for file_path, content in output.files.items():
            imports = extract_imports_from_code(content)
            for imp in imports:
                if not can_resolve_import(imp, project_structure):
                    return ValidationResult(
                        passed=False,
                        error=f"Cannot resolve import '{imp}' in {file_path}"
                    )
        return ValidationResult(passed=True)
```

#### 3. TypeValidator
```python
class TypeValidator:
    async def validate(self, output: TaskOutput):
        for file_path in output.files.keys():
            result = subprocess.run(['mypy', file_path, '--strict'], capture_output=True)
            if result.returncode != 0:
                return ValidationResult(
                    passed=False,
                    error=f"Type errors:\n{result.stderr}"
                )
        return ValidationResult(passed=True)
```

#### 4. SecurityValidator
```python
class SecurityValidator:
    async def validate(self, output: TaskOutput):
        dangerous_patterns = [
            (r'eval\(', "eval() usage - security risk"),
            (r'exec\(', "exec() usage - security risk"),
            (r'pickle\.loads', "pickle.loads without validation"),
            (r'sql.*\%\s*\(', "String formatting in SQL - injection risk"),
        ]

        for file_path, content in output.files.items():
            for pattern, message in dangerous_patterns:
                if re.search(pattern, content):
                    return ValidationResult(passed=False, error=message)

        return ValidationResult(passed=True)
```

---

## ✅ Definition of Done (DoD)

Una tarea está **DONE** solo si cumple TODOS estos criterios verificables automáticamente:

### Criterios CRÍTICOS 🔴 (Deben pasar SÍ o SÍ)

#### 1. Código
- [ ] **Syntax válido** (ast.parse sin errores)
- [ ] **Imports resuelven** (todos accesibles)
- [ ] **Sigue convenciones** (naming, estructura)

#### 2. Calidad
- [ ] **Type checking pasa** (mypy --strict ✓)
- [ ] **Linting pasa** (ruff sin errores)
- [ ] **Sin vulnerabilidades** (bandit/safety ✓)

#### 3. Funcionalidad
- [ ] **Todas postconditions cumplidas**
- [ ] **Outputs generados** (archivos en paths correctos)
- [ ] **Exportaciones funcionan** (import X funciona)
- [ ] **No rompe código existente**

#### 4. Testing (si aplica)
- [ ] **Tests unitarios existen**
- [ ] **Tests pasan 100%**

#### 5. Documentación
- [ ] **Docstrings completos** (funciones/clases públicas)
- [ ] **Type hints completos** (params y returns)

#### 6. Integración
- [ ] **No conflictos git**
- [ ] **Backward compatible**
- [ ] **Dependencies declaradas**

#### 7. Persistencia
- [ ] **Guardado en RAG**
- [ ] **Task metadata en DB**
- [ ] **MasterPlan actualizado**

### Criterios IMPORTANTES 🟡 (Deseables)

- [ ] Sin código debug (print/console.log)
- [ ] Formatting correcto (black/prettier)
- [ ] Complejidad aceptable (cyclomatic < 10)
- [ ] Coverage suficiente (>= 80%)
- [ ] Comentarios en lógica compleja

### Verificación Automática

```python
class DefinitionOfDoneChecker:

    async def check_all(self, task: AtomicTask, output: TaskOutput) -> DoDResult:
        """
        Verifica TODOS los criterios del DoD.
        """
        results = {
            "code": await self.check_code_criteria(output),
            "quality": await self.check_quality_criteria(output),
            "functionality": await self.check_functional_criteria(task, output),
            "testing": await self.check_testing_criteria(task, output),
            "documentation": await self.check_documentation_criteria(output),
            "integration": await self.check_integration_criteria(output),
            "persistence": await self.check_persistence_criteria(task, output)
        }

        # Recopilar fallos críticos
        critical_failures = [
            check for category in results.values()
            for check in category
            if not check.passed and check.critical
        ]

        # DoD solo pasa si NO hay fallos críticos
        dod_satisfied = len(critical_failures) == 0

        return DoDResult(
            satisfied=dod_satisfied,
            critical_failures=critical_failures,
            all_checks=results,
            can_mark_as_done=dod_satisfied
        )
```

### Reporte de DoD

```
📋 Definition of Done - Verification Report
============================================================

✅ ALL CRITERIA SATISFIED - Task is DONE

CODE:
  ✅ Syntax valid
  ✅ Imports resolve
  ✅ Follows conventions

QUALITY:
  ✅ Type checking passes
  ✅ Linting passes
  ✅ No security vulnerabilities

FUNCTIONALITY:
  ✅ All postconditions met
  ✅ Outputs generated
  ✅ Exports work
  ✅ No breaking changes

TESTING:
  ✅ Tests exist
  ✅ Tests pass 100%

DOCUMENTATION:
  ✅ Docstrings complete
  ✅ Type hints complete

INTEGRATION:
  ✅ No git conflicts
  ✅ Backward compatible
  ✅ Dependencies declared

PERSISTENCE:
  ✅ Saved in RAG
  ✅ Task metadata updated
  ✅ MasterPlan updated
```

### Checklist Completo: Tarea Bien Definida

Una tarea está bien definida si cumple:

**Definición (Pre-Ejecución)**:
- [x] Título descriptivo y único
- [x] Descripción detallada de QUÉ hacer
- [x] Declara todas las preconditions
- [x] Declara todas las postconditions
- [x] Tiene contexto completo (estructura, convenciones, schemas)
- [x] Tiene ejemplos del RAG
- [x] Tiene validaciones automáticas
- [x] Tiene Definition of Done definido
- [x] Es suficientemente granular (1 archivo, <300 LOC)
- [x] Sus dependencias son explícitas y mínimas

**Definition of Done (Post-Ejecución)**:
- [x] Todos los criterios críticos pasan
- [x] La mayoría de criterios importantes pasan
- [x] La tarea puede marcarse como "done"

---

## 📊 Resumen de Decisiones Finales

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Granularidad** | 1 tarea = 1 archivo, 200-300 LOC max, 1 responsabilidad | Balance óptimo para 99% éxito |
| **Re-intentos** | 3 intentos con feedback progresivo | Suficiente para corregir errores comunes |
| **Fallos persistentes** | Análisis con DebugAgent (LLM) + propuestas al usuario | LLM analiza causa raíz y propone soluciones |
| **RAG** | Aprende de éxitos Y fracasos | Agente sabe qué hacer Y qué evitar |
| **Validación** | TODAS las críticas e importantes deben pasar (stricto) | Garantiza código que realmente funciona |
| **Definition of Done** | 20+ criterios verificables automáticamente | Sin ambigüedad sobre cuándo una tarea está completa |

---

## ✅ Decisiones de Diseño - RESUELTAS

### 1. Modificaciones al MasterPlan Durante Ejecución
**Decisión**: Se PAUSA la ejecución, se analiza el impacto, se rehacen los planes y se crea una nueva versión.

**Flujo**:
1. Usuario solicita modificación durante ejecución
2. Sistema PAUSA automáticamente
3. DiscoveryAgent analiza nueva solicitud (si es compleja)
4. ImpactAnalysisService calcula:
   - Tareas afectadas (completadas/en progreso)
   - Nuevas dependencias necesarias
   - Estimación de tiempo adicional
   - Punto de inserción (phase/milestone)
5. Sistema genera plan modificado
6. Usuario aprueba/rechaza
7. Se crea nueva versión del MasterPlan
8. Se RESUME ejecución desde snapshot guardado

**Ver**: Sección "🔄 Modificaciones al MasterPlan Durante Ejecución" (línea 2857)

### 2. Pausar y Resumir Ejecución
**Decisión**: SÍ, el usuario puede pausar/resumir en cualquier momento.

**Casos de uso**:
- Usuario pausa manualmente (necesita revisar algo)
- Sistema pausa automáticamente (modificación, error crítico)
- Sistema pausa por decisión pendiente

**Implementación**:
- ExecutionSnapshot guarda estado completo
- Scratchpad state preservado
- Tareas en progreso se detienen gracefully
- Resume desde el mismo punto

**Ver**: Sección "⏸️ Pausar y Resumir Ejecución" (línea 3046)

### 3. Versionado de MasterPlans
**Decisión**: SÍ, se guardan TODAS las versiones históricas.

**Sistema de versiones**:
- Cada modificación aprobada = nueva versión
- Versiones numeradas secuencialmente (v1, v2, v3...)
- Snapshot completo del plan en cada versión
- Diff detallado entre versiones
- Parent-child relationship (árbol de versiones)
- Progress snapshot al momento de crear versión

**Tabla**: `masterplan_versions` con plan_snapshot (JSONB completo)

**Ver**: Sección "📚 Versionado de MasterPlans" (línea 3222)

### 4. RAG Learning de MasterPlans
**Decisión**: SÍ, aprendemos de TODO (éxitos, fracasos, modificaciones).

**Colecciones en ChromaDB**:
1. `successful_masterplans` - Patrones de éxito, estimaciones precisas
2. `failed_masterplans` - Qué salió mal, lecciones aprendidas
3. `masterplan_modifications` - Requisitos que se agregan frecuentemente
4. `successful_tasks` - Código que funcionó
5. `failed_tasks` - Errores comunes
6. `discovery_patterns` - Patrones DDD por industria

**Aprendizajes aplicados**:
- Stack recomendado basado en éxitos previos
- Modificaciones comunes ANTICIPADAS en plan inicial
- Patrones DDD probados para la industria
- Estimaciones ajustadas según precisión histórica

**Ver**: Sección "🧠 RAG Learning: Aprendiendo de MasterPlans" (línea 3376)

### 5. Jerarquía de Trabajo
**Decisión**: 4 niveles compatibles con Jira.

```
MasterPlan
├── Phases (Epics en Jira)
│   ├── Milestones (Fix Versions)
│   │   ├── Tasks (Stories)
│   │   │   └── Subtasks (Subtasks)
```

**Ver**: Sección "5. Jerarquía de Trabajo" (línea 251)

### 6. Exportación a Jira
**Decisión**: Dos métodos de exportación.

1. **Via API REST** - Automático, crea Epics/Stories/Subtasks/Links
2. **Via CSV** - Manual, para importación con Jira Importer

**Mapeo guardado**: `jira_id_mapping` (JSONB) para sincronización bidireccional futura

**Ver**: Sección "6. Exportación a Jira" (línea 691)

---

## 🚀 Próximos Pasos de Implementación

### Fase 1: Base de Datos (Prioridad: ALTA)
- [ ] Crear migrations para todas las tablas:
  - `discovery_documents`
  - `masterplans`, `masterplan_phases`, `masterplan_milestones`, `masterplan_tasks`, `masterplan_subtasks`
  - `masterplan_versions`
  - `masterplan_execution_snapshots`
  - `masterplan_history`
- [ ] Crear vistas SQL para reporting
- [ ] Seed data para testing

### Fase 2: Backend Core (Prioridad: ALTA)
- [ ] Implementar modelos SQLAlchemy:
  - `DiscoveryDocument`
  - `MasterPlan`, `Phase`, `Milestone`, `Task`, `Subtask`
  - `MasterPlanVersion`
- [ ] `DiscoveryAgent` - Conducir Discovery con DDD
- [ ] `MasterPlanService` - CRUD + generación
- [ ] `MasterPlanModificationService` - Análisis de impacto
- [ ] `ExecutionControlService` - Pausar/resumir
- [ ] `MasterPlanRAGLearningService` - Aprender de planes

### Fase 3: Integración con OrchestratorAgent (Prioridad: ALTA)
- [ ] Modificar `OrchestratorAgent.orchestrate()`:
  - Llamar a `DiscoveryAgent` PRIMERO
  - Generar `MasterPlan` con RAG learnings
  - Presentar para aprobación
  - Ejecutar con validación estricta
- [ ] Integrar validación de Definition of Done
- [ ] Integrar sistema de re-intentos con DebugAgent

### Fase 4: WebSocket Events (Prioridad: MEDIA)
- [ ] Events para Discovery:
  - `start_discovery`, `discovery_question`, `discovery_complete`
- [ ] Events para MasterPlan:
  - `masterplan_created`, `masterplan_approved`, `masterplan_updated`
  - `pause_execution`, `resume_execution`, `cancel_execution`
  - `request_modification`, `modification_proposal`, `modification_approved`
- [ ] Events para Jira:
  - `export_to_jira`, `jira_export_complete`, `get_jira_mapping`

### Fase 5: Exportación Jira (Prioridad: BAJA)
- [ ] `JiraExportService` - Integración con API REST
- [ ] CSV export para importación manual
- [ ] WebSocket events para exportación

### Fase 6: Frontend (Prioridad: MEDIA)
- [ ] `DiscoveryQuestionsView` - Formulario interactivo
- [ ] `DomainModelView` - Visualizar Bounded Contexts/Aggregates
- [ ] `MasterPlanView` - Panel principal:
  - Vista de phases/milestones/tasks
  - Progress bars por nivel
  - Botones de aprobación/modificación/pausa
- [ ] `MasterPlanVersionsView` - Historial de versiones
- [ ] `TaskDetailView` - Vista detallada de tarea con:
  - Acceptance criteria
  - Preconditions/postconditions
  - Validation results
  - Retry history

### Fase 7: RAG Integration (Prioridad: ALTA)
- [ ] Crear colecciones en ChromaDB
- [ ] Implementar learning automático al completar MasterPlans
- [ ] Integrar learnings en generación de nuevos planes
- [ ] Dashboard de métricas de aprendizaje

### Fase 8: Testing (Prioridad: ALTA)
- [ ] Tests unitarios para todos los servicios
- [ ] Tests de integración:
  - Discovery → MasterPlan → Ejecución
  - Modificación durante ejecución
  - Pausar/resumir
  - Versionado
- [ ] QA manual del flujo completo
- [ ] Performance testing (planes con 100+ tareas)

---

## 💻 Arquitectura Computacional y Decisiones de Implementación MVP

### Documento Relacionado
**Ver**: `LLM_COMPUTATIONAL_ARCHITECTURE.md` para análisis completo de viabilidad computacional.

### Decisiones Clave para MVP

#### 1. Estrategia de Modelos LLM (Hybrid)

```python
MODEL_STRATEGY_MVP = {
    "discovery": "Sonnet 4.5",           # Siempre
    "masterplan": "Sonnet 4.5",          # Siempre
    "tasks_simple_medium": "Haiku 4.5",  # 60% de tasks
    "tasks_complex": "Sonnet 4.5",       # 40% de tasks
    "opus": "NO usado en MVP"            # Solo v2
}
```

**Justificación**:
- Haiku 4.5 tiene reasoning y 64K output (game-changer)
- 3x más barato que Sonnet ($1/$5 vs $3/$15)
- Hybrid strategy = Best cost/quality balance

#### 2. Prompt Caching (CRÍTICO - 32% cost reduction)

```python
PROMPT_CACHING = {
    "enabled": True,                     # MUST desde día 1
    "cacheable_context": [
        "system_prompt",                 # 3K
        "discovery_document",            # 8K
        "rag_examples",                  # 20K
        "database_schema"                # 3K
    ],
    "cache_savings": "58% en task execution"
}
```

**Impacto**: Sin caching = $17.50, Con caching = $11.88 (32% savings)

#### 3. MasterPlan Generation (Monolithic)

```python
MASTERPLAN_GENERATION = {
    "approach": "Monolithic",            # Una sola llamada
    "reason": "64K output cabe 50 tasks",
    "input": "21.5K tokens",
    "output": "17K tokens",
    "cost": "$0.32",
    "vs_hierarchical": "$1.08",          # 71% más caro
}
```

**Decisión**: Aprovechamos 64K output de Sonnet/Haiku para generar plan completo.

#### 4. Task Execution (Sequential para MVP)

```python
EXECUTION_STRATEGY_MVP = {
    "mode": "Sequential",
    "reason": [
        "Evita race conditions en scratchpad",
        "Más simple de implementar",
        "Suficientemente rápido (15-18min)"
    ],
    "parallel": "v2 - Requiere locking mechanism"
}
```

**Latencia esperada**: 15-18 minutos (Tier 2, parallel 2x)

#### 5. Validation Layers

```python
VALIDATION_MVP = {
    "masterplan": [
        "JSON structure validation",
        "Required fields check",
        "Dependencies exist",
        "No circular dependencies (Neo4j)"
    ],
    "task_output": [
        "JSON validation",
        "Syntax check (compile for Python/JS)",
        "Files created verification"
    ]
}
```

#### 6. Retry Strategy

```python
RETRY_STRATEGY = {
    "max_retries": 1,                    # Solo 1 retry en MVP
    "include_error_feedback": True,      # Pasa error al LLM
    "expected_fail_rate": "20%",         # 10 tasks de 50
    "retry_cost": "$1.90"                # 20% del execution cost
}
```

### Costos Estimados MVP (50 tasks)

```python
MVP_COST_BREAKDOWN = {
    "discovery_sonnet": "$0.09",
    "masterplan_monolithic": "$0.32",
    "task_execution_hybrid": "$9.52",    # Con prompt caching
    "summaries_haiku": "$0.05",
    "retries_20%": "$1.90",

    "TOTAL_MVP": "$11.88"                # LLM API only
}

ALTERNATIVES = {
    "all_sonnet_conservative": "$14.21",
    "all_haiku_budget": "$7.94"          # Menos quality
}
```

### Métricas de Éxito MVP

```python
SUCCESS_METRICS = {
    "cost_per_project": "$10-15",
    "latency": "10-20 minutos",
    "success_rate": "70-80%",            # Código compila + funciona
    "cache_hit_rate": "50-70%",
    "user_satisfaction": "3.5+/5 stars"
}
```

### Scope Definitivo MVP

**IN SCOPE** (8 semanas):
- ✅ Discovery (3 passes con Sonnet)
- ✅ MasterPlan generation (monolithic)
- ✅ Task execution (sequential, hybrid models)
- ✅ Prompt caching implementation
- ✅ Basic validation (JSON + syntax)
- ✅ Retry logic (1 retry max)
- ✅ Progress streaming
- ✅ Cost tracking

**OUT OF SCOPE** (v2):
- ❌ Parallel execution (requires locking)
- ❌ Opus model (over-engineered para MVP)
- ❌ Extended context 1M (beta, tier 4 only)
- ❌ Advanced testing automation
- ❌ Security scanning
- ❌ Workspace integration (existing code)

### Timeline Implementación

```python
MVP_TIMELINE = {
    "week_1_2": "LLM integration + Storage setup",
    "week_3_4": "Discovery + MasterPlan generation",
    "week_5_6": "Task execution + Validation",
    "week_7_8": "Observability + QA",

    "total": "8 semanas para MVP funcional"
}
```

### Arquitectura de Almacenamiento

```python
STORAGE_ARCHITECTURE = {
    "postgresql": "Persistent state (MasterPlans, Tasks, History)",
    "redis": "Session cache + Prompt cache tracking",
    "chromadb": "RAG storage (successful/failed patterns)",
    "neo4j": "Dependency graph (O(1) queries)",
    "self_hosted": "MVP usa Docker local"
}
```

### Rate Limits Consideration

```python
RATE_LIMITS_HANDLING = {
    "tier_1": "Sequential only (40K TPM limit)",
    "tier_2": "Parallel 2x recommended (400K TPM)",
    "tier_4": "Parallel 5x (4M TPM) - no necesario MVP",

    "exponential_backoff": "Implementar desde día 1"
}
```

---

## 📝 Notas Finales

Este documento es el **diseño definitivo** del sistema MasterPlan.

**Todas las decisiones de diseño han sido resueltas**:
✅ Modificaciones durante ejecución → Pausar, analizar, rehacer
✅ Pausar/resumir → Sí, con snapshots
✅ Versionado → Sí, histórico completo
✅ RAG learning → Sí, de TODO (éxitos y fracasos)
✅ Jerarquía → 4 niveles (Phase/Milestone/Task/Subtask)
✅ Exportación Jira → API REST + CSV

**Todas las decisiones de implementación MVP resueltas**:
✅ Model strategy → Hybrid (60% Haiku, 40% Sonnet)
✅ Prompt caching → Implementar desde día 1 (32% savings)
✅ MasterPlan generation → Monolithic (71% más barato)
✅ Execution → Sequential para MVP (parallel en v2)
✅ Validation → JSON + syntax + file checks
✅ Cost target → $11.88 per project (LLM only)
✅ Latency target → 15-18 minutos (Tier 2)
✅ Success target → 70-80% (código funciona)

**Documentos complementarios**:
- `MASTERPLAN_DESIGN.md` (este) - Diseño funcional completo
- `LLM_COMPUTATIONAL_ARCHITECTURE.md` - Análisis de viabilidad computacional

**Documento listo para implementación.**

---

**Última actualización**: 2025-10-20
**Autor**: Ariel Ghysels + Claude
**Estado**: ✅ Diseño completado + Arquitectura computacional definida
**Líneas totales**: ~5100
**Decisiones tomadas**: 14/14 (6 funcionales + 8 computacionales)
