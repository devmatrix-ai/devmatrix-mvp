# MasterPlan Generation Progress UI - Design Document

**Fecha**: 2025-10-20
**Estado**: Design Phase

---

## 1. Objetivo

Crear una UI de progreso en tiempo real que muestre la generación del MasterPlan en el chat mientras el LLM está trabajando (60-120 segundos).

El usuario debe ver:
- **Progreso global** (barra de progreso basada en tokens)
- **Fase actual** (qué está haciendo el sistema)
- **Entidades descubiertas** (contador de fases, milestones, tareas a medida que se parsean)

---

## 2. Arquitectura de la Solución

### 2.1. Flujo de Generación con Progreso

```
User Request
    ↓
Discovery Agent (completado)
    ↓
[INICIO] MasterPlan Generator
    ↓
    ├─→ WebSocket: "masterplan_generation_start"
    │   {estimated_tokens: 17000, estimated_duration: 90}
    │
    ├─→ [Streaming LLM Call]
    │   │
    │   ├─→ WebSocket: "masterplan_tokens_progress"
    │   │   {tokens_received: 1500, estimated_total: 17000, percentage: 8}
    │   │   (cada 500 tokens o cada 5 segundos)
    │   │
    │   ├─→ [Parsing Incremental JSON]
    │   │   │
    │   │   ├─→ WebSocket: "masterplan_entity_discovered"
    │   │   │   {type: "phase", count: 1, name: "Setup"}
    │   │   │
    │   │   ├─→ WebSocket: "masterplan_entity_discovered"
    │   │   │   {type: "milestone", count: 3, phase: "Setup"}
    │   │   │
    │   │   └─→ WebSocket: "masterplan_entity_discovered"
    │   │       {type: "task", count: 12, milestone: "Database Setup"}
    │   │
    │   └─→ [LLM Completo]
    │
    ├─→ WebSocket: "masterplan_parsing_complete"
    │   {total_phases: 3, total_milestones: 17, total_tasks: 50}
    │
    ├─→ WebSocket: "masterplan_validation_start"
    │
    ├─→ [Validación]
    │
    ├─→ WebSocket: "masterplan_saving_start"
    │
    ├─→ [Guardar en PostgreSQL]
    │
    └─→ WebSocket: "masterplan_generation_complete"
        {
          masterplan_id: "uuid",
          total_phases: 3,
          total_milestones: 17,
          total_tasks: 50,
          generation_cost_usd: 0.132,
          duration_seconds: 106
        }
```

---

## 3. WebSocket Events Specification

### 3.1. Event: `masterplan_generation_start`

**Cuándo**: Inicio de la generación del MasterPlan

**Payload**:
```typescript
{
  event: "masterplan_generation_start",
  data: {
    discovery_id: string,
    session_id: string,
    estimated_tokens: number,      // ~17000
    estimated_duration_seconds: number  // ~90
  }
}
```

**UI Action**: Mostrar componente de progreso con barra al 0%

---

### 3.2. Event: `masterplan_tokens_progress`

**Cuándo**: Durante streaming del LLM (cada 500 tokens o cada 5 segundos)

**Payload**:
```typescript
{
  event: "masterplan_tokens_progress",
  data: {
    tokens_received: number,       // 2500
    estimated_total: number,       // 17000
    percentage: number,            // 14
    current_phase: string          // "Generating tasks..."
  }
}
```

**UI Action**: Actualizar barra de progreso y texto de fase

---

### 3.3. Event: `masterplan_entity_discovered`

**Cuándo**: Cuando el parser incremental encuentra una entidad completa

**Payload**:
```typescript
{
  event: "masterplan_entity_discovered",
  data: {
    type: "phase" | "milestone" | "task",
    count: number,                 // Total encontrado hasta ahora
    name?: string,                 // Nombre de la entidad (opcional)
    parent?: string                // Padre (milestone → phase, task → milestone)
  }
}
```

**UI Action**: Actualizar contador de entidades descubiertas

**Ejemplos**:
```json
// Primera fase descubierta
{
  "type": "phase",
  "count": 1,
  "name": "Setup"
}

// Milestone descubierto
{
  "type": "milestone",
  "count": 3,
  "name": "Database Setup",
  "parent": "Setup"
}

// Tarea descubierta
{
  "type": "task",
  "count": 23,
  "name": "Create User model",
  "parent": "Database Setup"
}
```

---

### 3.4. Event: `masterplan_parsing_complete`

**Cuándo**: JSON completamente parseado

**Payload**:
```typescript
{
  event: "masterplan_parsing_complete",
  data: {
    total_phases: number,          // 3
    total_milestones: number,      // 17
    total_tasks: number            // 50
  }
}
```

**UI Action**: Mostrar check ✓ en parsing, iniciar validación

---

### 3.5. Event: `masterplan_validation_start`

**Cuándo**: Inicio de validación del plan

**Payload**:
```typescript
{
  event: "masterplan_validation_start",
  data: {}
}
```

**UI Action**: Mostrar "🔍 Validando dependencias..."

---

### 3.6. Event: `masterplan_saving_start`

**Cuándo**: Inicio de guardado en PostgreSQL

**Payload**:
```typescript
{
  event: "masterplan_saving_start",
  data: {
    total_entities: number         // 70 (3 + 17 + 50)
  }
}
```

**UI Action**: Mostrar "💾 Guardando en base de datos..."

---

### 3.7. Event: `masterplan_generation_complete`

**Cuándo**: MasterPlan completamente generado y guardado

**Payload**:
```typescript
{
  event: "masterplan_generation_complete",
  data: {
    masterplan_id: string,
    project_name: string,
    total_phases: number,
    total_milestones: number,
    total_tasks: number,
    generation_cost_usd: number,
    duration_seconds: number,
    estimated_total_cost_usd: number,
    estimated_duration_minutes: number
  }
}
```

**UI Action**: Mostrar resumen final y ocultar progreso

---

## 4. UI Components

### 4.1. `MasterPlanProgressIndicator.tsx`

**Componente principal** que muestra el progreso de generación.

**Props**:
```typescript
interface MasterPlanProgressIndicatorProps {
  event: MasterPlanProgressEvent | null
}

type MasterPlanProgressEvent =
  | MasterPlanGenerationStartEvent
  | MasterPlanTokensProgressEvent
  | MasterPlanEntityDiscoveredEvent
  | MasterPlanParsingCompleteEvent
  | MasterPlanValidationStartEvent
  | MasterPlanSavingStartEvent
  | MasterPlanGenerationCompleteEvent
```

**Estado Interno**:
```typescript
interface MasterPlanProgressState {
  // Progreso global
  tokensReceived: number
  estimatedTotalTokens: number
  percentage: number

  // Fase actual
  currentPhase: string  // "Generating tasks...", "Validating...", etc.

  // Entidades descubiertas
  phasesFound: number
  milestonesFound: number
  tasksFound: number

  // Timing
  startTime: Date | null
  elapsedSeconds: number
  estimatedRemainingSeconds: number
}
```

**Render**:
```tsx
<div className="space-y-3 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg border-2 border-purple-300 dark:border-purple-700">
  {/* 1. Header */}
  <div className="flex items-center gap-2">
    <div className="animate-spin">🤖</div>
    <h3 className="font-bold text-purple-900 dark:text-purple-100">
      Generando MasterPlan
    </h3>
  </div>

  {/* 2. Progress Bar (Token-based) */}
  <div className="space-y-1">
    <div className="flex justify-between text-xs text-purple-700 dark:text-purple-300">
      <span>{currentPhase}</span>
      <span>{percentage}%</span>
    </div>
    <div className="w-full bg-purple-200 dark:bg-purple-800 rounded-full h-4">
      <div
        className="h-full bg-gradient-to-r from-purple-500 to-blue-600 rounded-full transition-all duration-300"
        style={{ width: `${percentage}%` }}
      />
    </div>
    <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
      <span>{tokensReceived.toLocaleString()} tokens</span>
      <span>{elapsedSeconds}s / ~{estimatedRemainingSeconds}s</span>
    </div>
  </div>

  {/* 3. Entities Discovered */}
  <div className="grid grid-cols-3 gap-2 text-center">
    <EntityCounter
      icon="📦"
      label="Fases"
      count={phasesFound}
      total={3}
      complete={phasesFound === 3}
    />
    <EntityCounter
      icon="🎯"
      label="Milestones"
      count={milestonesFound}
      total={17}
      complete={milestonesFound >= 17}
    />
    <EntityCounter
      icon="✅"
      label="Tareas"
      count={tasksFound}
      total={50}
      complete={tasksFound === 50}
    />
  </div>

  {/* 4. Status Messages */}
  <div className="space-y-1">
    <StatusItem icon="✓" text="Discovery completado" status="done" />
    <StatusItem icon="⚙️" text={currentPhase} status="in_progress" />
    {phasesFound === 3 && (
      <StatusItem icon="✓" text="Fases completas" status="done" />
    )}
    {milestonesFound >= 17 && (
      <StatusItem icon="✓" text="Milestones completos" status="done" />
    )}
  </div>
</div>
```

---

### 4.2. `EntityCounter.tsx`

**Subcomponente** para mostrar contador de entidades.

```tsx
interface EntityCounterProps {
  icon: string
  label: string
  count: number
  total: number
  complete: boolean
}

export const EntityCounter: React.FC<EntityCounterProps> = ({
  icon,
  label,
  count,
  total,
  complete
}) => {
  return (
    <div className={`p-2 rounded-lg ${
      complete
        ? 'bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-600'
        : 'bg-white dark:bg-gray-800 border border-purple-200 dark:border-purple-700'
    }`}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className={`text-lg font-bold ${
        complete ? 'text-green-700 dark:text-green-300' : 'text-purple-700 dark:text-purple-300'
      }`}>
        {count} / {total}
      </div>
      <div className="text-xs text-gray-600 dark:text-gray-400">{label}</div>
    </div>
  )
}
```

---

### 4.3. `StatusItem.tsx`

**Subcomponente** para items de estado.

```tsx
interface StatusItemProps {
  icon: string
  text: string
  status: 'pending' | 'in_progress' | 'done'
}

export const StatusItem: React.FC<StatusItemProps> = ({
  icon,
  text,
  status
}) => {
  const colorClass = {
    pending: 'text-gray-500 dark:text-gray-400',
    in_progress: 'text-blue-600 dark:text-blue-400 animate-pulse',
    done: 'text-green-600 dark:text-green-400'
  }[status]

  return (
    <div className={`flex items-center gap-2 text-sm ${colorClass}`}>
      <span>{icon}</span>
      <span>{text}</span>
    </div>
  )
}
```

---

## 5. Backend Implementation

### 5.1. Modified `MasterPlanGenerator.generate_masterplan()`

**Cambios**:
1. Agregar parámetro `websocket_manager` opcional
2. Emitir eventos durante la generación
3. Implementar streaming incremental
4. Parsear JSON progresivamente

```python
async def generate_masterplan(
    self,
    discovery_id: UUID,
    session_id: str,
    user_id: str,
    websocket_manager: Optional[WebSocketManager] = None
) -> UUID:
    """
    Generate MasterPlan with real-time progress updates.

    Args:
        discovery_id: Discovery document UUID
        session_id: Session ID
        user_id: User ID
        websocket_manager: Optional WebSocket manager for progress updates

    Returns:
        masterplan_id: UUID of created MasterPlan
    """

    # Emit start event
    if websocket_manager:
        await websocket_manager.emit_to_session(
            session_id,
            "masterplan_generation_start",
            {
                "discovery_id": str(discovery_id),
                "session_id": session_id,
                "estimated_tokens": 17000,
                "estimated_duration_seconds": 90
            }
        )

    # Load discovery
    discovery = self._load_discovery(discovery_id)

    # Generate with streaming
    tokens_received = 0
    json_buffer = ""

    async for chunk in self._generate_masterplan_streaming(discovery):
        # Update token progress
        tokens_received += len(chunk.split())
        json_buffer += chunk

        # Emit progress every 500 tokens
        if tokens_received % 500 < 10 and websocket_manager:
            await websocket_manager.emit_to_session(
                session_id,
                "masterplan_tokens_progress",
                {
                    "tokens_received": tokens_received,
                    "estimated_total": 17000,
                    "percentage": min(95, int(tokens_received / 17000 * 100)),
                    "current_phase": self._get_current_phase(tokens_received)
                }
            )

        # Try incremental parsing
        entities = self._parse_incomplete_json(json_buffer)

        # Emit entity discoveries
        if websocket_manager:
            for entity in entities:
                await websocket_manager.emit_to_session(
                    session_id,
                    "masterplan_entity_discovered",
                    entity
                )

    # Parsing complete
    if websocket_manager:
        await websocket_manager.emit_to_session(
            session_id,
            "masterplan_parsing_complete",
            {
                "total_phases": 3,
                "total_milestones": 17,
                "total_tasks": 50
            }
        )

    # Validation
    if websocket_manager:
        await websocket_manager.emit_to_session(
            session_id,
            "masterplan_validation_start",
            {}
        )

    self._validate_masterplan(masterplan_data)

    # Saving
    if websocket_manager:
        await websocket_manager.emit_to_session(
            session_id,
            "masterplan_saving_start",
            {"total_entities": 70}
        )

    masterplan_id = self._save_masterplan(...)

    # Complete
    if websocket_manager:
        await websocket_manager.emit_to_session(
            session_id,
            "masterplan_generation_complete",
            {
                "masterplan_id": str(masterplan_id),
                "project_name": masterplan.project_name,
                "total_phases": 3,
                "total_milestones": 17,
                "total_tasks": 50,
                "generation_cost_usd": 0.132,
                "duration_seconds": 106
            }
        )

    return masterplan_id
```

---

### 5.2. Incremental JSON Parser

```python
def _parse_incomplete_json(self, buffer: str) -> List[Dict]:
    """
    Parse incomplete JSON to extract completed entities.

    Returns list of newly discovered entities.
    """
    entities = []

    # Try to find complete phase objects
    phase_pattern = r'"phases":\s*\[(.*?)\]'
    phase_match = re.search(phase_pattern, buffer, re.DOTALL)

    if phase_match:
        # Extract phases
        # ... parsing logic
        pass

    return entities
```

---

## 6. Integration with Chat

### 6.1. Update `MessageList.tsx`

```tsx
// Add MasterPlanProgressIndicator
import { MasterPlanProgressIndicator } from './MasterPlanProgressIndicator'

// In MessageList component
{masterPlanProgress && (
  <MasterPlanProgressIndicator event={masterPlanProgress} />
)}
```

### 6.2. Update Chat Hook

```tsx
// In useChat.ts or similar
const [masterPlanProgress, setMasterPlanProgress] = useState<MasterPlanProgressEvent | null>(null)

// Listen to WebSocket events
ws.on('masterplan_generation_start', (data) => {
  setMasterPlanProgress({ event: 'masterplan_generation_start', data })
})

ws.on('masterplan_tokens_progress', (data) => {
  setMasterPlanProgress({ event: 'masterplan_tokens_progress', data })
})

// ... more events
```

---

## 7. Estimated Development Time

| Task | Tiempo Estimado |
|------|----------------|
| Backend: Streaming & Events | 4-6 horas |
| Backend: Incremental JSON Parser | 2-3 horas |
| Frontend: MasterPlanProgressIndicator | 3-4 horas |
| Frontend: Subcomponents | 1-2 horas |
| Frontend: Integration with Chat | 1-2 horas |
| Testing & Polish | 2-3 horas |
| **TOTAL** | **13-20 horas** |

---

## 8. Success Criteria

✅ El usuario ve progreso en tiempo real durante los 60-120 segundos de generación
✅ La barra de progreso se actualiza cada 5 segundos (o cada 500 tokens)
✅ Los contadores de entidades se actualizan a medida que se parsean
✅ El componente se muestra SOLO durante la generación del MasterPlan
✅ El componente desaparece cuando la generación está completa
✅ Los eventos WebSocket no afectan la performance

---

## 9. Future Enhancements (v2)

1. **Visualización de Estructura**:
   - Mostrar árbol de fases → milestones → tareas
   - Expandir/colapsar secciones

2. **Animaciones**:
   - Transición suave cuando aparecen entidades
   - Confetti cuando se completa 🎉

3. **Detalles de Entidades**:
   - Mostrar nombres de tasks a medida que aparecen
   - Preview de dependencias

4. **Cancelación**:
   - Botón "Cancel" para detener generación
   - Guardar progreso parcial

---

## 10. Questions for User

1. ¿Quieres que el componente muestre TODOS los tasks descubiertos (1-50) con scroll, o solo un contador?
2. ¿Prefieres que el progreso sea más "conservador" (llega a 95% y espera) o "optimista" (puede pasar de 100%)?
3. ¿Quieres animaciones o prefieres una UI más minimalista?

---

**Fin del documento de diseño**
