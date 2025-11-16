# Console Tool - Guía de Usuario (Español)

**Versión**: 2.0.0
**Estado**: Producción ✅
**Fecha**: 2025-11-16

---

## 📖 Índice

1. [Inicio Rápido](#inicio-rápido)
2. [Comandos Disponibles](#comandos-disponibles)
3. [Características Principales](#características-principales)
4. [Ejemplos Prácticos](#ejemplos-prácticos)
5. [Configuración](#configuración)
6. [Solución de Problemas](#solución-de-problemas)

---

## Inicio Rápido - Flujo SaaS

### 🎯 El Modelo: Claude Orchestrates Everything

DevMatrix no es una herramienta CLI que abres manualmente. Es una **plataforma SaaS** donde:

1. **Describes tu necesidad en chat** (lenguaje natural)
2. **Claude hace preguntas inteligentes** (especificación)
3. **Responde iterativamente** (refinamiento)
4. **Claude genera el masterplan** (120 tareas)
5. **Claude ejecuta automáticamente** (con progreso en tiempo real)
6. **Ves los resultados** (en el chat)

### Ejemplo de Conversación Real

```
Tu: "Quiero un sitio web de e-commerce"

Claude: 🔍 Analizando tu requisito...
        📱 Tipo: E-commerce

        Para ser más preciso, tengo algunas preguntas:

        1️⃣ ¿Cuántos productos aproximadamente?
        2️⃣ ¿Qué métodos de pago?
        3️⃣ ¿Necesita wishlist, reseñas, búsqueda avanzada?

Tu: "500 productos, tarjeta y PayPal, sí a todo"

Claude: ✅ Entendido. Siguiente pregunta:

        ¿Cuántos usuarios esperas en el primer mes?

Tu: "Unos 100-200 usuarios por día"

Claude: [Después de suficientes respuestas]

        🎉 ¡Especificación completa!
        📝 Generando masterplan (120 tareas)...

        [Muestra bonita visualización del plan]

Tu: "Dale, ejecuta"

Claude: 🚀 Ejecutando...

        Progress: [████████░░] 45%
        Tarea actual: Implementar carrito de compras ✅
        Archivos creados: 18

        [Actualización en tiempo real]

Tu: "¿Listos los tests?"

Claude: ✅ EJECUCIÓN COMPLETA

        Duration: 45 minutos
        Tests: 347/347 pasados ✅
        Archivos: 87 creados
        Costo: $1.02
```

### No Necesitas Abrir Terminal

Todo sucede en el chat. Claude:
- ✅ Analiza tu requisito
- ✅ Hace preguntas clarificadoras
- ✅ Genera el masterplan
- ✅ Ejecuta las 120 tareas
- ✅ Reporta progreso en tiempo real
- ✅ Valida los resultados

---

## Cómo Funciona - Behind the Scenes

### 🔧 Los Comandos (Para Desarrolladores)

Claude usa estos comandos internamente. **No los escribes tú directamente**, pero es útil entender cómo funcionan:

### 1️⃣ `spec` - Recopilación Inteligente de Requisitos

Claude invoca este comando para:
- Analizar tu requisito inicial
- Detectar tipo de aplicación
- Generar preguntas clarificadoras
- Validar completitud de especificación

**Cómo lo usa Claude:**

```
1. /spec "Quiero un sitio de e-commerce"
   └─ Detecta: AppType.ECOMMERCE
   └─ Genera: 3-5 preguntas prioritarias
   └─ Te pregunta: "¿Cuántos productos?"

2. /spec answer "500 productos con categorías"
   └─ Registra respuesta
   └─ Calcula: 40% completo
   └─ Siguiente pregunta: "¿Métodos de pago?"

3. /spec show
   └─ Muestra especificación actual
   └─ Completitud: 60%

4. /spec ready
   └─ Valida que esté ≥80% completo
   └─ Si está lista: "Listo para masterplan"
   └─ Si no: "Te faltan estas preguntas..."
```

**Tipos de aplicación detectados:**
- Web App (React, Vue, Next.js)
- API Backend (REST, GraphQL)
- Mobile App (iOS, Android)
- SaaS Platform (servicios por suscripción)
- E-commerce (tiendas online)
- Dashboard (analytics, admin)
- Integration (conectores)

**Completitud requerida:**
- ✅ usuarios (¿quién usa esto?)
- ✅ features (¿qué hace?)
- ✅ autenticación (¿seguridad?)
- ✅ escala (¿cuántos usuarios?)
- ✅ timeline (¿para cuándo?)

---

### 2️⃣ `plan` - Visualización del Masterplan

Claude lo usa para:
- Generar plan de 120 tareas
- Mostrar diferentes vistas
- Visualizar dependencias
- Permitir revisión antes de ejecutar

**Vistas disponibles:**

```
/plan show --view overview   # Resumen rápido con barras
/plan show --view timeline   # Timeline de 5 fases
/plan show --view tasks      # Tabla de 120 tareas
/plan show --view stats      # Estadísticas y métricas
/plan show --view dependencies # Grafo ASCII de dependencias
/plan show --view full       # Todo combinado
```

**Lo que ves:**

```
📋 MASTERPLAN OVERVIEW
Progress: [████████░░] 80%
Total Tasks: 120

Phase 0 (Discovery):      5 tasks  ✅ Complete
Phase 1 (Analysis):      15 tasks  ✅ Complete
Phase 2 (Planning):      50 tasks  🔄 In Progress
Phase 3 (Execution):     40 tasks  ⏳ Pending
Phase 4 (Validation):    10 tasks  ⏳ Pending

Duration: ~8-10 hours
Tokens: ~180K tokens
Cost: ~$1.20
```

---

### 3️⃣ `execute` - Ejecución Automática

Claude invoca esto y luego monitorea el progreso:

```
/execute --parallel --max-workers 4

🚀 Ejecutando masterplan...

[Real-time progress via WebSocket]

Progress: [████████░░] 45% (54/120)
Phase: Execution (Phase 3)
Current Task: Implement payment gateway ✅

Artifacts Created: 18
├── src/services/payment.py ✅
├── src/models/order.py ✅
├── tests/payment_test.py ✅
└── ...

Tokens Used: 45,230 / 200,000 (22%)
```

**Opciones:**
- `--parallel`: Ejecutar en paralelo (default: true)
- `--max-workers`: Número de workers concurrentes
- `--dry-run`: Simular sin hacer cambios

---

### 4️⃣ `validate` - Validación de Resultados

Después de ejecutar:

```
/validate --strict

✅ VALIDACIÓN EXITOSA

Tests: 347/347 passed ✅
Coverage: 92%
Linting: Clean ✅
Performance: Within targets ✅

Summary:
- 87 files generated
- 0 errors, 0 warnings
- Ready for deployment
```

**Opciones:**
- `--strict`: Falla en warnings (no solo errores)
- `--check syntax|tests|coverage|performance`: Validar aspecto específico

---

### 5️⃣ `test` - Ejecutar Tests

```bash
# Run toda la suite
> test all

# Solo unit tests
> test unit

# Con profundidad
> test unit --depth comprehensive

# Suite específica
> test console --focus websocket
```

---

### 4️⃣ `show` - Mostrar Información

```bash
# Ver pipeline actual
> show pipeline

# Ver artifacts creados
> show artifacts

# Ver tokens gastados
> show tokens

# Ver logs
> show logs

# Información completa
> show status
```

---

### 5️⃣ `logs` - Ver y Filtrar Logs

```bash
# Mostrar todos los logs
> logs

# Solo errores
> logs --level ERROR

# Solo warnings
> logs --level WARN

# De una fuente específica
> logs --source websocket

# Buscar palabra clave
> logs --query "connection"

# Estadísticas
> logs --stats
```

---

### 6️⃣ `session` - Gestionar Sesiones

```bash
# Crear nueva sesión
> session create

# Listar sesiones
> session list

# Cargar sesión anterior
> session load 20251116_abc123

# Ver estadísticas
> session stats

# Información de sesión actual
> session info
```

---

### 7️⃣ `config` - Configuración

```bash
# Ver toda la configuración
> config

# Ver setting específico
> config token_budget

# Cambiar setting
> config token_budget 50000

# Ver tema actual
> config theme
```

---

### 8️⃣ `cancel` - Cancelar Tareas

```bash
# Cancelar tarea en ejecución
> cancel task_123

# Con ID de tarea completo
> cancel feature_dev_20251116_001
```

---

### 9️⃣ `retry` - Reintentar Tareas

```bash
# Reintentar tarea fallida
> retry task_123

# Con más intentos
> retry task_123 --attempts 3
```

---

### 🔟 `help` - Ayuda

```bash
# Ayuda general
> help

# Ayuda de comando específico
> help run
> help logs
> help plan

# Atajos disponibles
> help aliases
```

---

### ❌ `exit` / `q` - Salir

```bash
# Salir de la consola
> exit

# O usar atajo
> q
```

---

## Características Principales

### 🎯 1. Visualización en Tiempo Real

La consola muestra:
- ✅ Tareas completadas
- 🔄 Tareas en progreso
- ⏳ Tareas pendientes
- ❌ Tareas fallidas
- ⚠️ Advertencias

```
Pipeline Status:
├── Task 1: ✅ Complete (12s)
├── Task 2: 🔄 Running... (45%)
├── Task 3: ⏳ Pending
└── Task 4: ❌ Failed
```

---

### 💾 2. Persistencia de Sesiones

Se guarda automáticamente cada 30 segundos:
- Historial de comandos
- Estado de la pipeline
- Artifacts creados
- Métricas de uso
- Logs de errores

```bash
# Cargar sesión anterior
> session load previous_session_id

# Todo está ahí: artifacts, historial, etc.
```

---

### 🎯 3. Seguimiento de Tokens

Monitorea uso de API:
- Presupuesto total
- Tokens usados
- Costo estimado
- Desglose por modelo
- Alertas automáticas

```bash
> show tokens

# Output:
# Total: 45,000 / 100,000 (45%)
# Cost: $0.34 / $10.00
# Claude: 30,000 tokens
# GPT-4: 15,000 tokens
```

---

### 🎨 4. Preview de Artifacts

Visualiza archivos generados:
- Syntax highlighting automático
- Soporte para 20+ lenguajes
- Tamaño formateado (B/KB/MB/GB)
- Metadatos de archivo

```bash
> show artifacts

# Output:
# src/auth.py (3.2 KB) - Python ✅
# src/models.py (5.1 KB) - Python ✅
# tests/test_auth.py (2.8 KB) - Python ✅
```

---

### ⚡ 5. Autocomplete Inteligente

```bash
# Escribir inicio + TAB para sugerencias
> run auth<TAB>
# Suggestions:
# - run authentication_feature
# - run authorization_check
# - run auth_refactor

# Buscar en historial
Ctrl+R → buscar comandos anteriores
```

---

### 📝 6. Logging Avanzado

```bash
# Filtrar por nivel
> logs --level ERROR    # Solo errores
> logs --level WARN     # Solo warnings
> logs --level INFO     # Solo info

# Filtrar por fuente
> logs --source websocket
> logs --source api

# Buscar
> logs --query "timeout"
> logs --query "connection"

# Estadísticas
> logs --stats
# Output: Total: 245 | ERROR: 3 | WARN: 12 | INFO: 230
```

---

## Ejemplos Prácticos

### Ejemplo 1: Desarrollar un Feature Nuevo

```bash
# 1. Crear sesión
> session create
# Created: session_20251116_xyz789

# 2. Ver configuración
> config
# Token budget: 100,000
# Cost limit: $10.00

# 3. Generar plan
> plan feature --focus authentication
# Plan generated: 8 steps

# 4. Ejecutar feature
> run authentication_feature

# 5. Monitorear progreso
> show pipeline
# Progress: [████████░░] 80%

# 6. Ver artifacts
> show artifacts
# - auth.py (2.1 KB)
# - auth_test.py (1.8 KB)

# 7. Verificar logs
> logs --level ERROR
# No errors found ✅

# 8. Verificar tokens
> show tokens
# Used: 32,000 / 100,000 (32%)
```

---

### Ejemplo 2: Debugging de Tarea Fallida

```bash
# 1. Ver errores
> logs --level ERROR
# Connection timeout in websocket_client.py:123

# 2. Más contexto
> logs --query "websocket" --level WARN
# [WARN] Reconnecting... attempt 1/10
# [WARN] Reconnecting... attempt 2/10
# [ERROR] Max reconnection attempts exceeded

# 3. Cargar sesión anterior
> session load previous_session
# Session loaded: previous_session_20251116

# 4. Reintentar
> retry failed_task_001

# 5. Monitorear
> show pipeline

# 6. Revisar nuevamente
> logs --query "websocket"
# [INFO] Connection established ✅
```

---

### Ejemplo 3: Gestión de Presupuesto

```bash
# 1. Verificar uso
> show tokens
# Used: $8.50 / $10.00 (85%) ⚠️

# 2. Ver desglose
> logs --source api
# API calls:
# - GPT-4: 25 calls = $0.75
# - Claude: 100 calls = $7.75

# 3. Aumentar presupuesto
> config token_budget 150000
# Updated: token_budget = 150000

# O reducir límite de costo
> config cost_limit 5.0
# Updated: cost_limit = 5.0

# 4. Continuar trabajo
> run next_feature

# 5. Monitorear
> show tokens
# Used: $8.50 / $5.00... ⚠️ (budget exceeded)
```

---

### Ejemplo 4: Revisar Historial de Sesiones

```bash
# 1. Listar todas las sesiones
> session list
# Sessions:
# 1. session_20251116_abc123 - Created: 2025-11-16 14:30
# 2. session_20251115_xyz789 - Created: 2025-11-15 09:15
# 3. session_20251114_def456 - Created: 2025-11-14 16:45

# 2. Ver estadísticas de una sesión
> session stats
# Current Session:
# - Commands executed: 24
# - Duration: 1h 23m
# - Artifacts created: 8
# - Errors: 0

# 3. Cargar sesión anterior si es necesario
> session load session_20251115_xyz789
# Session loaded successfully
```

---

## Configuración

### Archivo de Configuración

Ubicaciones (en orden de prioridad):
1. `.devmatrix/config.yaml` (carpeta del proyecto)
2. `~/.devmatrix/config.yaml` (home global)
3. Valores por defecto (en el código)

### Opciones Principales

```yaml
# Tema de la consola
theme: "dark"              # dark, light, auto

# Nivel de verbosidad
verbosity: "normal"        # quiet, normal, verbose, debug

# Presupuesto de tokens
token_budget: 100000       # Total tokens permitidos
cost_limit: 10.0           # Límite de costo en USD

# Alertas
cost_warning_threshold: 0.75   # Alerta al 75%
token_warning_threshold: 0.90  # Alerta al 90%

# Sesiones
session_auto_save_interval: 30000  # ms
session_retention_days: 30         # Retener 30 días
max_session_history: 1000          # Máximo historial

# WebSocket
websocket_url: "ws://localhost:8000/socket.io/"
api_base_url: "http://localhost:8000"
websocket_timeout: 30000           # ms
```

### Cambiar Configuración en Tiempo de Ejecución

```bash
# Ver todo
> config

# Ver setting específico
> config token_budget
# Output: 100000

# Cambiar setting
> config token_budget 50000
# Output: Updated token_budget = 50000

# Ver de nuevo
> config token_budget
# Output: 50000
```

---

## Solución de Problemas

### ❌ La consola no inicia

```bash
# Verificar dependencias
pip list | grep -E "rich|pydantic"

# Reinstalar si es necesario
pip install rich pydantic python-socketio

# Intentar de nuevo
python -m src.console
```

---

### ❌ No se conecta al WebSocket

```bash
# Verificar que el servidor está corriendo
curl http://localhost:8000/health

# Verificar configuración
> config websocket_url
# Output: ws://localhost:8000/socket.io/

# Esperar reconexión automática
# (La consola intentará reconectarse cada 5s, máximo 10 intentos)
```

---

### ❌ Se acabó el presupuesto de tokens

```bash
# Ver uso actual
> show tokens
# Output: Used: 100,000 / 100,000 (100%) ❌

# Aumentar presupuesto
> config token_budget 150000

# O reducir límite para próxima sesión
> config cost_limit 5.0

# Cargar sesión anterior
> session load previous_session
```

---

### ❌ Tarea fallida

```bash
# 1. Ver logs de error
> logs --level ERROR

# 2. Más contexto
> logs --query "error_text"

# 3. Cargar sesión anterior
> session load previous_session

# 4. Reintentar
> retry failed_task_id

# 5. Monitorear
> show pipeline
```

---

### ❌ No puedo encontrar sesión anterior

```bash
# Listar todas las sesiones
> session list

# Buscar en la carpeta
ls ~/.devmatrix/sessions/

# Si no está, revisar retention
> config session_retention_days
# Default: 30 días (sesiones más viejas se eliminan)
```

---

## Atajos de Teclado

| Atajo | Función |
|-------|---------|
| `Tab` | Autocomplete |
| `Ctrl+R` | Buscar en historial |
| `Ctrl+A` | Ir al inicio |
| `Ctrl+E` | Ir al final |
| `Ctrl+D` | Salir (exit) |
| `Ctrl+C` | Cancelar comando actual |

---

## Consejos y Trucos

### ⚡ Acelerar Navegación

```bash
# Usar atajos
> q                    # En lugar de: exit
> h                    # En lugar de: help
> ?                    # En lugar de: help

# Autocomplete
> run auth<TAB>        # Ver sugerencias
> Ctrl+R auth          # Buscar en historial

# Comandos recientes
> show pipeline        # Última vez que lo usaste
# Presiona arriba para repetir
```

---

### 💰 Optimizar Tokens

```bash
# Monitorear regularmente
> show tokens          # Cada 30 minutos

# Usar depth apropiado
> run task --depth quick           # Menos tokens
> run task --depth comprehensive   # Más tokens

# Filtrar logs antes de buscar
> logs --level ERROR               # Solo errores
> logs --source api                # Solo API calls
```

---

### 📊 Entender Logs Mejor

```bash
# Ver estadísticas primero
> logs --stats
# Total: 1,245 | ERROR: 3 | WARN: 15 | INFO: 1,227

# Luego filtrar
> logs --level ERROR               # Solo los 3 errores
> logs --level WARN                # Solo los 15 warnings

# Buscar patrón específico
> logs --query "timeout"           # Problemas de timeout
> logs --query "connection"        # Problemas de conexión
```

---

### 💾 Gestionar Sesiones

```bash
# Sesiones se guardan automáticamente cada 30s
# Puedes cerrar la consola sin perder datos

# Después, simplemente cargar:
> session load <session_id>

# Tu historial, artifacts, todo está ahí

# Limpiar sesiones viejas (>30 días)
# Ocurre automáticamente, pero puedes cambiar:
> config session_retention_days 60  # Retener 60 días
```

---

## Información Adicional

### Documentación Completa

- **Este archivo**: Guía de usuario (conceptos y ejemplos)
- **src/console/README.md**: Referencia técnica
- **Tests**: `tests/console/` (ver ejemplos de uso)
- **Código fuente**: `src/console/` (docstrings detallados)

### Versión

- **Console Tool**: 2.0.0
- **Lanzamiento**: 2025-11-16
- **Estado**: ✅ Producción

---

**¿Preguntas? Revisa los archivos de documentación o corre los tests para ver ejemplos de uso.**

¡Bienvenido al Console Tool! 🚀
