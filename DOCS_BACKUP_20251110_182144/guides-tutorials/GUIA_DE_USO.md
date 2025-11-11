# 🚀 Guía de Uso de DevMatrix

**Versión**: 0.4.0
**Estado**: Production Ready
**Última Actualización**: 2025-10-16

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Uso de la Web UI](#uso-de-la-web-ui)
3. [Ejemplos Prácticos](#ejemplos-prácticos)
4. [Comandos Disponibles](#comandos-disponibles)
5. [Atajos de Teclado](#atajos-de-teclado)
6. [Preguntas Frecuentes](#preguntas-frecuentes)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Inicio Rápido

### 1. Verificar que Todo Esté Corriendo

```bash
# Ir al directorio del proyecto
cd /home/kwar/code/agentic-ai

# Verificar servicios Docker
docker ps

# Deberías ver 3 servicios healthy:
# - devmatrix-api (puerto 8000)
# - devmatrix-redis (puerto 6379)
# - devmatrix-postgres (puerto 5432)
```

**Si los servicios NO están corriendo**:
```bash
# Iniciar servicios
docker compose up -d

# Verificar que estén healthy
docker ps
```

### 2. Abrir la Aplicación

**Opción 1: Navegador Web** (RECOMENDADO)
```
Abrí tu navegador en: http://localhost:8000
```

**Opción 2: Desde WSL**
```bash
# Si estás en WSL2, podés usar:
explorer.exe http://localhost:8000

# O usar curl para verificar:
curl http://localhost:8000
```

### 3. Primera Interacción

Cuando abras http://localhost:8000, vas a ver:

```
┌─────────────────────────────────────────────────┐
│  DevMatrix Chat                    [🟢 Connected]│
├─────────────────────────────────────────────────┤
│                                                  │
│  Start a conversation                           │
│                                                  │
│  Ask me to create workflows, analyze code,      │
│  or help with development tasks.                │
│                                                  │
│  Try: /orchestrate Create a REST API            │
│  Or: /help for available commands               │
│                                                  │
├─────────────────────────────────────────────────┤
│  Type a message or /help for commands... [Send] │
└─────────────────────────────────────────────────┘
```

---

## 💬 Uso de la Web UI

### Tipos de Interacciones

DevMatrix tiene **2 modos**:

#### Modo 1: Conversacional (Charla Casual)

**Cuándo lo usa**: Cuando hacés preguntas, saludos, o querés discutir ideas.

**Ejemplos**:
```
Vos: Hola
DevMatrix: ¡Hola! Soy DevMatrix, tu asistente para desarrollo...

Vos: Podríamos diseñar una app de tareas?
DevMatrix: ¡Dale! Task manager suena bien. ¿Qué features principales
          necesitás? (autenticación, asignación de tareas, etc.)

Vos: Qué me recomendás para una API REST?
DevMatrix: Depende del caso de uso. FastAPI es genial para APIs
          modernas y rápidas...
```

#### Modo 2: Orquestación (Implementación)

**Cuándo lo usa**: Cuando pedís crear/implementar algo específico.

**Palabras clave que lo activan**:
- crear, create
- generar, generate
- implementar, implement
- hacer, make
- escribir, write
- desarrollar, develop
- armar, build

**Ejemplo**:
```
Vos: Crear una calculadora con operaciones básicas

DevMatrix: [Inicia orquestación automáticamente]
           ⚙️ Analizando alcance del proyecto...
           ✓ 5 tareas identificadas
           🚀 Ejecutando tareas...

           [Muestra progreso en tiempo real:]
           🔄 1/5 - Implement calculator class
           ✓ 2/5 - Add division with zero handling
           ✓ 3/5 - Create unit tests
           ...
```

---

## 🎯 Ejemplos Prácticos

### Ejemplo 1: Saludar y Explorar

```
Vos: Buenos días

DevMatrix: ¡Hola! Soy DevMatrix, tu asistente para desarrollo de software.
          Puedo ayudarte a diseñar arquitecturas, planear proyectos, y
          orquestar la implementación con múltiples agentes especializados.
          ¿En qué puedo ayudarte hoy?

Vos: Qué podés hacer?

DevMatrix: Puedo ayudarte con:
          - Diseñar arquitecturas de software
          - Implementar código Python (funciones, clases, APIs)
          - Generar tests automáticamente
          - Crear documentación
          - Responder preguntas técnicas

          Cuando estés listo para implementar algo, solo decime
          "crear X" o "implementar Y" y lo orquesto.
```

### Ejemplo 2: Discutir una Idea

```
Vos: Estoy pensando en hacer una app de gestión de proyectos

DevMatrix: ¡Buena idea! Para entender mejor, algunas preguntas:
          - ¿Qué features principales necesitás? (kanban, gantt, sprints?)
          - ¿Cuántos usuarios aproximadamente?
          - ¿Necesitás autenticación y roles?

Vos: Kanban, sprints, roles (Dev/PM/Lead), y colaboración en tiempo real

DevMatrix: Perfecto, tengo claro el scope. Cuando quieras arrancar con
          la implementación, decime algo como:
          "crear task manager con FastAPI, kanban, sprints y roles"
          y lo orquesto.
```

### Ejemplo 3: Implementación Directa

```
Vos: Quiero hacer una API REST para gestión de usuarios con FastAPI,
     autenticación JWT, y CRUD completo

DevMatrix: ⚙️ Analizando alcance del proyecto...

          ## 📊 Project Analysis
          Type: backend_api
          Complexity: 7.2

          ✓ 12 tareas identificadas

          ## 🎯 Execution Plan

          ### 💻 Implementation Tasks
          - **task_1**: Project structure and dependencies
          - **task_2**: Database models (User, Session)
          - **task_3**: JWT authentication middleware
          - **task_4**: User CRUD endpoints
          - **task_5**: Password hashing utilities
          ...

          ### 🧪 Testing Tasks
          - **task_8**: Unit tests for auth
          - **task_9**: Integration tests for CRUD
          ...

          ### 📝 Documentation Tasks
          - **task_11**: API documentation
          - **task_12**: README with setup guide

          🚀 Starting Task Execution...

          🔄 1/12 - Creating project structure...
          ✓ 1/12 - Project structure complete (3 files)

          🔄 2/12 - Creating database models...
          ✓ 2/12 - Database models complete (2 files)

          [Continúa ejecutando todas las tareas...]

          ## ✅ Orchestration Complete

          **Workspace**: workspace_abc123
          **Tasks Completed**: 12/12
          **Files Generated**: 18

          ### Files Created:
          - `main.py` (FastAPI app)
          - `models.py` (User model)
          - `auth.py` (JWT middleware)
          - `crud.py` (CRUD operations)
          - `test_auth.py` (tests)
          - `README.md` (documentation)
          ...
```

### Ejemplo 4: Proyecto Simple

```
Vos: Crear una función para validar emails

DevMatrix: ⚙️ Analizando alcance del proyecto...

          ## 📊 Project Analysis
          Type: simple function
          Complexity: 2.1

          ✓ 3 tareas identificadas

          🚀 Executing tasks...

          ✓ 1/3 - Email validation function complete
          ✓ 2/3 - Unit tests complete
          ✓ 3/3 - Documentation complete

          ## ✅ Orchestration Complete

          ### Generated Code:
          ```python
          import re
          from typing import Optional

          def validate_email(email: str) -> bool:
              """
              Validate email address format.

              Args:
                  email: Email address to validate

              Returns:
                  True if valid, False otherwise
              """
              pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
              return bool(re.match(pattern, email))
          ```

          [Botón de copiar código aparece al hacer hover]
```

---

## 🎮 Comandos Disponibles

### Comandos de Chat

Podés usar estos comandos especiales:

#### `/help` - Mostrar ayuda
```
Vos: /help

DevMatrix: Available commands:
          /orchestrate: Orchestrate multi-agent workflow
          /analyze: Analyze project or code
          /test: Run tests
          /help: Show available commands
          /clear: Clear conversation history
          /workspace: Show current workspace info
```

#### `/orchestrate <descripción>` - Forzar orquestación
```
Vos: /orchestrate Create a REST API for user management

DevMatrix: [Inicia orquestación directamente]
```

#### `/clear` - Limpiar historial
```
Vos: /clear

DevMatrix: Conversation cleared.
```

#### `/workspace` - Ver info del workspace actual
```
Vos: /workspace

DevMatrix: Workspace Info:
          workspace_id: workspace_abc123
          conversation_id: conv_xyz789
          message_count: 15
```

---

## ⌨️ Atajos de Teclado

### Shortcuts Disponibles

| Atajo | Acción | Descripción |
|-------|--------|-------------|
| `Ctrl+K` / `⌘+K` | Focus Input | Mueve el cursor al input de texto |
| `Ctrl+L` / `⌘+L` | Clear Messages | Borra todos los mensajes (con confirmación) |
| `Ctrl+N` / `⌘+N` | New Project | Inicia un nuevo proyecto (refresca la página) |

**Ejemplo de uso**:
1. Estás leyendo una respuesta larga
2. Apretás `Ctrl+K`
3. El cursor salta al input automáticamente
4. Empezás a escribir tu próxima pregunta

---

## 🎨 Funcionalidades de la UI

### 1. Copiar Código

Cuando DevMatrix muestra código, vas a ver:

```python
def hello():        [Python] [📋 Copy]
    return "Hello"
```

**Hacer hover** sobre el bloque de código → aparece botón **Copy**
**Click en Copy** → código copiado al clipboard
**Feedback visual**: Copy → ✓ Copied!

### 2. Copiar Mensaje Completo

**Hacer hover** sobre cualquier mensaje del asistente:
```
🤖 Asistente - 14:30                [📋] [🔄]
Aquí está el código...
```

**[📋]** = Copy mensaje completo
**[🔄]** = Regenerate respuesta (próximamente)

### 3. Exportar Conversación

**Botón en el header**: `[Exportar]`

**Click** → Descarga archivo `.md` con:
```markdown
# DevMatrix Chat Export

Conversation ID: conv_xyz789
Workspace: workspace_abc123
Exported: 2025-10-16 14:30:00

---

### **Usuario** - 14:30:15
Crear una calculadora

---

### **Asistente** - 14:30:20
## Orchestration Complete
...
```

### 4. Dark Mode

**Ir a Settings** (ícono ⚙️ en sidebar)

**Seleccionar tema**:
- ☀️ **Light**: Tema claro
- 🌙 **Dark**: Tema oscuro
- 🖥️ **System**: Sigue preferencia del sistema

**Persiste entre sesiones** (usa LocalStorage)

### 5. Nuevo Proyecto

**Botón en el header**: `[Nuevo]`

**Click** → Confirmación: "¿Empezar un nuevo proyecto?"
**Aceptar** → Borra historial y refresca conversación

---

## ❓ Preguntas Frecuentes

### ¿Cuánto tarda en generar código?

**Depende del proyecto**:
- Función simple: ~30 segundos
- Módulo pequeño: ~1-2 minutos
- API REST completa: ~3-5 minutos

**Vas a ver progreso en tiempo real**:
```
🔄 1/12 - Creating project structure...
✓ 1/12 - Project structure complete
🔄 2/12 - Creating database models...
```

### ¿Dónde se guarda el código generado?

**Ubicación**: `/tmp/devmatrix-workspace-{workspace_id}/`

**Ejemplo**:
```bash
/tmp/devmatrix-workspace-abc123/
├── calculator.py
├── test_calculator.py
├── calculator_docs.md
└── README.md
```

**Para ver tus archivos**:
```bash
# Listar workspaces
ls /tmp/devmatrix-workspace-*/

# Ver archivos de un workspace específico
ls -la /tmp/devmatrix-workspace-abc123/
```

### ¿Puedo interrumpir la ejecución?

**Actualmente no hay botón de stop**, pero podés:
1. Cerrar el navegador
2. La tarea seguirá corriendo en backend
3. Al reconectar verás el resultado final

**Próxima versión**: Botón de cancelación

### ¿Cómo veo el código generado?

**Opción 1**: En la UI
- DevMatrix muestra el código con syntax highlighting
- Podés copiarlo con el botón Copy

**Opción 2**: En el filesystem
```bash
# Ver archivos generados
cd /tmp/devmatrix-workspace-abc123/
cat calculator.py
```

**Opción 3**: Exportar conversación
- Click en [Exportar]
- Descarga Markdown con todo el código

### ¿Puedo modificar el código generado?

**Sí, de varias formas**:

**Opción 1**: Pedir modificación en el chat
```
Vos: Modificá la función add para que acepte múltiples números

DevMatrix: [Regenera el código con las modificaciones]
```

**Opción 2**: Editar manualmente
```bash
# Editar archivo generado
vim /tmp/devmatrix-workspace-abc123/calculator.py
```

**Opción 3**: Copiar y pegar en tu proyecto
- Copiar código de la UI
- Pegar en tu editor favorito
- Modificar como quieras

---

## 🔧 Troubleshooting

### Problema: "Disconnected" en la UI

**Síntomas**:
```
🔴 Disconnected
Connecting...
```

**Solución 1**: Verificar backend
```bash
# Ver si el servidor está corriendo
docker ps | grep devmatrix-api

# Si no está corriendo, iniciarlo
docker compose up -d devmatrix-api
```

**Solución 2**: Refrescar navegador
```
F5 o Ctrl+R
```

**Solución 3**: Verificar logs
```bash
# Ver logs del API
docker logs devmatrix-api --tail 50
```

### Problema: No Genera Código

**Síntomas**:
```
⚙️ Analizando proyecto...
[Se queda trabado]
```

**Solución 1**: Verificar API key
```bash
# Ver si la variable existe
echo $ANTHROPIC_API_KEY

# Si no existe, configurarla
export ANTHROPIC_API_KEY="tu-api-key"
```

**Solución 2**: Verificar Redis/PostgreSQL
```bash
# Ver estado de servicios
docker ps

# Reiniciar si es necesario
docker compose restart
```

**Solución 3**: Ver logs
```bash
# Logs del API
docker logs devmatrix-api --tail 100 -f
```

### Problema: Error "Failed to connect to Redis"

**Síntomas** en logs:
```
Failed to connect to Redis at redis:6379
```

**Causa**: Redis no está corriendo

**Solución**:
```bash
# Iniciar Redis
docker compose up -d devmatrix-redis

# Verificar que esté healthy
docker ps | grep redis
```

**Nota**: El sistema sigue funcionando sin Redis (usa fallbacks), pero es más lento.

### Problema: Código No Aparece en el Chat

**Síntomas**:
```
✅ Orchestration Complete
[No muestra código]
```

**Causa Posible**: Markdown rendering issue

**Solución**:
1. Refrescar navegador (F5)
2. Exportar conversación para ver código
3. Verificar archivos en filesystem:
   ```bash
   ls /tmp/devmatrix-workspace-*/
   ```

### Problema: Dark Mode No Persiste

**Síntomas**: Cada vez que abro vuelve a Light mode

**Causa**: LocalStorage bloqueado

**Solución**:
1. Verificar que el navegador permita LocalStorage
2. Abrir DevTools → Application → Local Storage
3. Verificar que exista `devmatrix-theme`

---

## 💡 Tips y Mejores Prácticas

### 1. Sé Específico en tus Requests

**❌ Vago**:
```
Crear una app
```

**✅ Específico**:
```
Crear una API REST con FastAPI para gestión de usuarios,
con autenticación JWT, roles (admin/user), y endpoints
CRUD para usuarios y perfiles
```

### 2. Dale Contexto Técnico

**❌ Sin contexto**:
```
Hacer una calculadora
```

**✅ Con contexto**:
```
Crear una calculadora en Python con las 4 operaciones básicas,
manejo de errores (división por cero), type hints, y tests unitarios
```

### 3. Usa Comandos para Casos Específicos

**Quiero discutir primero**: Preguntá directamente
```
Qué me recomendás para hacer una app de tareas?
```

**Quiero implementar ya**: Usá palabras de acción
```
Crear una app de tareas con FastAPI y React
```

**Quiero forzar orquestación**: Usá `/orchestrate`
```
/orchestrate Create a task management app
```

### 4. Revisá el Plan Antes de Ejecutar

DevMatrix muestra el plan ANTES de ejecutar:
```
## 🎯 Execution Plan

### 💻 Implementation Tasks
- task_1: Create project structure
- task_2: Implement models
...

🚀 Starting Task Execution...
```

**Si el plan no te convence**: Podés empezar de nuevo con Ctrl+N

### 5. Exportá tus Conversaciones

**Después de cada proyecto importante**:
1. Click en [Exportar]
2. Guardá el `.md` como documentación
3. Incluye código + decisiones + conversación

---

## 🎓 Ejemplos de Proyectos Completos

### Proyecto 1: REST API Simple

**Request**:
```
Crear una API REST con FastAPI para gestión de libros.
Necesito endpoints para listar, crear, actualizar y eliminar libros.
Cada libro tiene: título, autor, ISBN, año de publicación.
Incluir validación de datos y documentación OpenAPI.
```

**Resultado Esperado**:
- `main.py` - FastAPI app
- `models.py` - Pydantic models
- `database.py` - SQLite setup
- `crud.py` - CRUD operations
- `test_api.py` - Tests
- `README.md` - Documentation

### Proyecto 2: Script de Utilidades

**Request**:
```
Crear un script Python para procesar archivos CSV:
- Leer CSV con pandas
- Filtrar filas según criterios
- Calcular estadísticas (promedio, suma, conteo)
- Exportar resultados a Excel
- Incluir manejo de errores y logging
```

**Resultado Esperado**:
- `csv_processor.py` - Script principal
- `config.py` - Configuración
- `test_processor.py` - Tests
- `requirements.txt` - Dependencias
- `README.md` - Instrucciones de uso

### Proyecto 3: Módulo de Autenticación

**Request**:
```
Implementar un módulo de autenticación con:
- Registro de usuarios (email, password)
- Login con JWT tokens
- Password hashing con bcrypt
- Decorador para rutas protegidas
- Tests unitarios y de integración
```

**Resultado Esperado**:
- `auth.py` - Módulo de auth
- `models.py` - User model
- `jwt_handler.py` - JWT utilities
- `decorators.py` - @require_auth
- `test_auth.py` - Tests completos
- `README.md` - Guía de uso

---

## 🚀 Próximos Pasos

**Ahora que sabés usar DevMatrix**:

1. ✅ Probá con un proyecto simple (función o script)
2. ✅ Explorá las features de la UI (dark mode, export, shortcuts)
3. ✅ Experimentá con proyectos más complejos (APIs, módulos)
4. ✅ Exportá tus conversaciones para documentación
5. ✅ Familiarizate con los atajos de teclado

**Si tenés problemas**: Ver sección [Troubleshooting](#troubleshooting)

**Si querés reportar bugs o sugerir features**:
- Crear issue en el repo
- O charlarlo directamente en el chat

---

## 📞 Soporte

**Logs del Sistema**:
```bash
# API logs
docker logs devmatrix-api -f

# Redis logs
docker logs devmatrix-redis -f

# PostgreSQL logs
docker logs devmatrix-postgres -f
```

**Servicios**:
```bash
# Status
docker ps

# Restart all
docker compose restart

# Stop all
docker compose down

# Start all
docker compose up -d
```

---

**¡Listo para empezar!** 🎉

Abrí http://localhost:8000 y empezá a crear código con DevMatrix.
