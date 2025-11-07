# 🔍 MasterPlan Progress Modal - Comprehensive Debugging Guide

**Última actualización**: Nov 6, 2025
**Problema reportado**: Modal desincronizado, datos no mostrándose correctamente
**Ultrathink Analysis**: ✅ Completo

---

## 📋 Tabla de Contenidos

1. [Quick Start](#-quick-start)
2. [Flujo de Datos Completo](#-flujo-de-datos-completo)
3. [Tests Disponibles](#-tests-disponibles)
4. [Debugging Manual](#-debugging-manual)
5. [Casos Comunes de Issues](#-casos-comunes-de-issues)
6. [Checklist de Validación](#-checklist-de-validación)
7. [Performance Tips](#-performance-tips)

---

## 🚀 Quick Start

### Opción 1: Ejecutar Tests E2E Completos

```bash
# Desde src/ui/
npm test -- MasterPlanProgressModal.e2e.test.ts

# O con watch mode
npm test -- MasterPlanProgressModal.e2e.test.ts --watch

# Con UI de Playwright
npx playwright test --ui MasterPlanProgressModal.e2e.test.ts
```

**Qué hacen estos tests:**
- ✅ TEST 1: Modal rendering básico
- ✅ TEST 2: Discovery phase complete
- ✅ TEST 3: Full flow (discovery + masterplan)
- ✅ TEST 4: Real-time data sync
- ✅ TEST 5: Entity counts
- ✅ TEST 6: Session ID filtering
- ✅ TEST 7: Error handling
- ✅ TEST 8: Modal cleanup
- ✅ TEST 9: Page reload recovery
- ✅ TEST 10: Out-of-order events
- ✅ TEST 11: Duplicate deduplication
- ✅ TEST 12: Lazy loading
- ✅ TEST 13: WebSocket room joining
- ✅ TEST 14: Phase timeline transitions
- ✅ TEST 15: Cost calculation

### Opción 2: Debugging Manual en Browser

```javascript
// 1. Abre browser DevTools (F12)
// 2. Pega en console:

import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'
setupMasterPlanDebugger()

// 3. Abre el modal (genera un MasterPlan)
// 4. Cuando termina o en cualquier momento:

window.__masterplanDebug.analyze()

// 5. Para ver datos crudos:
window.__masterplanDebug.getFlowTrace()

// 6. Para exportar todo a JSON:
window.__masterplanDebug.exportFlow()
```

---

## 📊 Flujo de Datos Completo

### Capas del Sistema

```
┌─────────────────────────────────────────────────────────────────────────┐
│ BACKEND (Python)                                                         │
│ ├─ discovery_generation_start                                           │
│ ├─ discovery_tokens_progress (streaming)                                │
│ ├─ discovery_entity_discovered (múltiples)                              │
│ ├─ discovery_parsing_complete                                           │
│ ├─ discovery_saving_start                                               │
│ ├─ discovery_generation_complete                                        │
│ │                                                                         │
│ ├─ masterplan_generation_start                                          │
│ ├─ masterplan_tokens_progress (streaming)                               │
│ ├─ masterplan_entity_discovered (múltiples)                             │
│ ├─ masterplan_parsing_complete                                          │
│ ├─ masterplan_validation_start                                          │
│ ├─ masterplan_saving_start                                              │
│ └─ masterplan_generation_complete                                       │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
                    WebSocket (Socket.IO)
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FRONTEND - useWebSocket Hook                                            │
│ ├─ CircularEventBuffer (máx 100 eventos)                                │
│ ├─ Deduplicación (mismo evento dentro de 100ms)                         │
│ └─ WebSocketContext (singleton provider)                                │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FRONTEND - useChat Hook                                                 │
│ ├─ 16 event listeners (1 por cada tipo de evento)                       │
│ ├─ setMasterPlanProgress (React state)                                  │
│ └─ Zustand store updates                                                │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FRONTEND - useMasterPlanProgress Hook                                   │
│ ├─ State machine (switch por event type)                                │
│ ├─ ProgressState (tokens, %, fases)                                     │
│ └─ Phase timeline updates                                               │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FRONTEND - Zustand Store                                                │
│ ├─ Persistencia en localStorage                                         │
│ └─ Múltiples subscribers (modal, chat, navbar, etc)                     │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ UI COMPONENTS                                                            │
│ ├─ MasterPlanProgressModal                                              │
│ ├─ ProgressTimeline                                                     │
│ ├─ ProgressMetrics                                                      │
│ ├─ ErrorPanel                                                           │
│ └─ FinalSummary                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Transform en Cada Capa

| Capa | Input | Transformation | Output |
|------|-------|-----------------|--------|
| WebSocket | Raw evento JSON | Envuelve en MasterPlanProgressEvent | CircularBuffer |
| useChat | CircularBuffer | 16 listeners, setMasterPlanProgress | React state |
| useMasterPlanProgress | Events + sessionId | State machine switch | ProgressState |
| Zustand | ProgressState | Atomic updates + persist | localStorage + subscribers |
| Components | Zustand state | Conditional rendering | UI visual |

---

## 🧪 Tests Disponibles

### Ejecutar Individual Test

```bash
# Test específico
npx playwright test MasterPlanProgressModal.e2e.test.ts -g "Discovery phase"

# Con debug
npx playwright test MasterPlanProgressModal.e2e.test.ts -g "Discovery phase" --debug

# Con output detallado
npx playwright test MasterPlanProgressModal.e2e.test.ts -g "Discovery phase" --reporter=verbose
```

### Casos de Prueba Clave

**TEST 2: Discovery Phase** 🔍
```javascript
// Verifica:
// ✓ Modal abre al recibir discovery_generation_start
// ✓ Token progress se actualiza (2K → 4K → 7.5K)
// ✓ Entity counts se acumulan (3 BC, 7 AGG, 24 ENT)
// ✓ Parsing complete dispara transición de fase
// ✓ Datos correctos al completarse discovery
```

**TEST 3: Full Flow** 🚀
```javascript
// Verifica:
// ✓ Discovery completa al 25%
// ✓ MasterPlan comienza automáticamente
// ✓ Tokens progress suben de 30% → 100%
// ✓ Fases avanzan: discovery → parsing → validation → saving
// ✓ Counts finales correctos (5 phases, 12 milestones, 48 tasks)
// ✓ Modal muestra "Complete" al final
```

**TEST 9: Page Reload Recovery** 💾
```javascript
// Verifica:
// ✓ localStorage persiste antes del reload
// ✓ Estado se recupera después del reload
// ✓ Modal reaparece si generación aún en progreso
// ✓ Eventos nuevos se procesan correctamente
```

### Interpretar Resultados

```
✅ PASSED = Test passou completamente, comportamiento correcto
⚠️ FLAKY = Test a veces passa, a veces falha (timing issues)
❌ FAILED = Test falló, hay un bug real

Causas comunes:
- FLAKY: Timeouts demasiado cortos (aumentar wait times)
- FAILED: EventListener no registrado
- FAILED: Session ID extraction wrong
- FAILED: Data not appearing in DOM
```

---

## 🔧 Debugging Manual

### Paso 1: Monitorear Console Logs

Abre DevTools (F12) y busca estos patterns:

```javascript
// ✅ BUENO - Eventos siendo capturados
✅ [useChat] Registering 16 masterplan listeners...
🔍 [useChat::discovery_generation_start] LISTENER FIRED!
📊 [WebSocket] discovery_tokens_progress received:
✅ [useMasterPlanProgress] Event processing complete

// ❌ MALO - Problemas
⚠️ [useChat] Current masterPlanProgress state: null
⚠️ [useMasterPlanProgress] No event to process, skipping update
❌ [MasterPlanProgressModal] Extracted session/masterplan ID: undefined
```

### Paso 2: Activar Debugger Automático

```javascript
// En console (cuando modal está abierto):
import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'
setupMasterPlanDebugger()

// Espera 5 segundos, el debugger auto-analiza y reporta
```

### Paso 3: Inspeccionar Estado Actual

```javascript
// Ver último evento
window.__masterplanDebug.getFlowTrace().events.slice(-1)[0]

// Ver timeline completa
window.__masterplanDebug.getFlowTrace().events.forEach(e => {
  console.log(`${new Date(e.timestamp).toISOString()} | ${e.layer} | ${e.eventType}`)
})

// Ver problemas detectados
window.__masterplanDebug.getFlowTrace().issues

// Ver conteo por tipo de evento
window.__masterplanDebug.getFlowTrace().eventCounts
```

### Paso 4: Validar Data Integrity

```javascript
const trace = window.__masterplanDebug.getFlowTrace()

// Check 1: ¿Hay discovery_generation_start?
trace.events.some(e => e.eventType === 'discovery_generation_start')
// ✓ true = Backend emitiendo eventos

// Check 2: ¿Hay eventos tokens_progress?
trace.events.filter(e => e.eventType.includes('tokens_progress')).length
// ✓ > 0 = WebSocket entregando eventos

// Check 3: ¿Hay transiciones de fase?
['discovery_parsing_complete', 'masterplan_validation_start', 'masterplan_saving_start']
  .map(type => trace.events.some(e => e.eventType === type))
// ✓ [true, true, true] = State machine funcionando

// Check 4: ¿Percentages son válidos?
trace.events
  .filter(e => e.layer === 'useMasterPlanProgress')
  .map(e => ({
    type: e.eventType,
    percentage: e.data.percentage,
    valid: e.data.percentage >= 0 && e.data.percentage <= 100
  }))
// ✓ Todos valid: true
```

---

## 🐛 Casos Comunes de Issues

### Issue #1: Modal No Abre

```
Síntoma: Modal nunca aparece al generar MasterPlan
Causa probable: Event listener no registrado en useChat

Debugging:
1. ¿Aparece "[useChat] Registering 16 masterplan listeners..." en console?
   NO → useChat.ts no está montado
   SÍ → Ir a step 2

2. ¿Aparece "discovery_generation_start" en console?
   NO → Backend no emitiendo evento
   SÍ → Ir a step 3

3. ¿Aparece "setMasterPlanProgress" después de discovery_generation_start?
   NO → Listener no disparado (bug en on() function)
   SÍ → Modal debería estar abierto, revisar CSS (z-index, display)

Solución:
- Verificar que WebSocketProvider wrappea toda la app
- Verificar que useChat effect dependencia array es vacío: useEffect(() => {...}, [])
- Revisar que event listener callbacks tienen scope correcto (closure)
```

### Issue #2: Porcentaje Stuck en 0%

```
Síntoma: Progress bar no avanza, siempre muestra 0%
Causa probable: tokens_progress events no siendo procesados

Debugging:
1. Verificar event arrival en useChat:
   - ¿Aparece "discovery_tokens_progress received:" en console?
   - SÍ → Evento llega, ir a step 2
   - NO → WebSocket room no joined, backend no emitiendo, o evento perdido

2. Verificar event processing en useMasterPlanProgress:
   - ¿Aparece en console después del tokens_progress?
   - SÍ → Estado actualizado, verificar DOM
   - NO → Event no pasa al useMasterPlanProgress hook

3. Verificar cálculo de percentage:
   const percentage = Math.min((tokens / estimated) * 100, 95)
   // tokens = ? / estimated = ?
   // ¿Son ambos > 0?

4. Verificar render:
   document.querySelector('[data-testid="metrics-percentage"]')?.textContent
   // ¿Muestra el porcentaje correcto?

Solución:
- Agregar console.log en useMasterPlanProgress switch case para discovery_tokens_progress
- Verificar que estimated_total viene en event data
- Verificar que component está usando el estado del hook
```

### Issue #3: Entity Counts No Actualizándose

```
Síntoma: Bounded Contexts, Aggregates, Entities siempre muestran 0
Causa probable: entity_discovered events perdidos o mal procesados

Debugging:
1. ¿Llegan discovery_entity_discovered eventos?
   // Buscar en console
   "discovery_entity_discovered"
   SÍ → Ir a step 2
   NO → Backend no emitiendo, o event filter incorrecto

2. ¿Entity type está siendo extraído correctamente?
   window.__masterplanDebug.getFlowTrace().events
     .filter(e => e.eventType.includes('entity_discovered'))
     .map(e => ({type: e.eventType, entityType: e.data.entity_type}))

3. ¿State machine está matcheando entity_type?
   // En useMasterPlanProgress.ts línea 373-395
   // ¿Entity type es lowercase?
   const entityType = (eventData.entity_type || eventData.type)?.toLowerCase()

4. ¿Count está siendo actualizado?
   const state = await getProgressState(page)
   state.metrics.entities
   // ¿Tienen valores > 0?

Solución:
- Verificar format de entity_type en backend (debe ser lowercase: 'bounded_context', no 'BoundedContext')
- Agregar console.log en entity_discovered case para ver qué se está procesando
- Verificar que component está usando state.boundedContexts, no state.boundedcontexts
```

### Issue #4: Modal Desincronizado (Data Mismatch)

```
Síntoma: UI muestra datos viejos o incorrectos después de eventos nuevos
Causa probable: Deduplicación incorrecta o race condition

Debugging:
1. ¿Qué evento fue el último procesado?
   window.__masterplanDebug.getFlowTrace().events.slice(-1)[0]
   // timestamp = ?
   // eventType = ?
   // data = ?

2. ¿Hay eventos duplicados siendo deduplicados?
   const events = window.__masterplanDebug.getFlowTrace().events
   const eventKeys = events.map(e => `${e.eventType}:${e.timestamp}`)
   const duplicates = eventKeys.filter((k, i, a) => a.indexOf(k) !== i)
   // ¿Hay duplicates? Si > 5, hay problema

3. ¿Session ID filtering está funcionando?
   window.__masterplanDebug.getFlowTrace().sessionIds
   // Debería haber solo 1 session ID

   window.__masterplanDebug.getFlowTrace().events.length
   window.__masterplanDebug.getFlowTrace().events
     .filter(e => e.sessionId === 'expected-session-id').length
   // Debería ser el mismo número

4. ¿Timing está correcto?
   const trace = window.__masterplanDebug.getFlowTrace().events
   trace.forEach((e, i) => {
     if (i > 0) {
       const delay = e.timestamp - trace[i-1].timestamp
       if (delay > 1000) console.warn(`Large gap: ${delay}ms`)
     }
   })

Solución:
- Revisar que lastProcessedEventRef no está siendo seteado prematuramente
- Verificar que sessionId filtering en useMasterPlanProgress es correcto
- Agregar timestamps en cada transición de estado
- Usar React DevTools para ver cuando components re-render
```

### Issue #5: Modal No Cierra Después de Completarse

```
Síntoma: Modal sigue visible con "100%" incluso después de generation_complete
Causa probable: isComplete flag no siendo seteado

Debugging:
1. ¿Llegó masterplan_generation_complete event?
   window.__masterplanDebug.getFlowTrace().events
     .some(e => e.eventType === 'masterplan_generation_complete')

2. ¿isComplete fue seteado en state?
   window.__masterplanDebug.getFlowTrace().events
     .filter(e => e.eventType === 'masterplan_generation_complete')
     .map(e => ({
       percentage: e.data.percentage,
       isComplete: e.data.isComplete,
       phasesFound: e.data.phasesFound
     }))

3. ¿Render condicional está correcto?
   // En MasterPlanProgressModal.tsx línea 239
   // {isComplete && !isError && (
   //   <FinalSummary />
   // )}
   // ¿isComplete === true en props?

Solución:
- Verificar que masterplan_generation_complete event tiene percentage: 100, isComplete: true
- Verificar que FinalSummary component se muestra
- User puede cerrar manualmente con X button o Escape key
```

---

## ✅ Checklist de Validación

Use este checklist para validar que todo está funcionando:

### Fase 1: WebSocket Connectivity
- [ ] Backend está corriendo en puerto 8000
- [ ] Frontend está corriendo en puerto 3000
- [ ] WebSocket conexión established (DevTools → Network → WS)
- [ ] "chat_joined" event aparece en console al cargar app

### Fase 2: Event Emission
- [ ] Iniciar generación de MasterPlan
- [ ] "discovery_generation_start" aparece en console
- [ ] Modal abre automáticamente
- [ ] Discovery room join aparece en console

### Fase 3: Token Progress
- [ ] "discovery_tokens_progress" eventos llegan múltiples veces
- [ ] Porcentaje incrementa de 0% hacia arriba
- [ ] Progress bar visual se actualiza

### Fase 4: Entity Discovery
- [ ] "discovery_entity_discovered" eventos aparecen
- [ ] Bounded Contexts count incrementa
- [ ] Aggregates count incrementa
- [ ] Entities count incrementa

### Fase 5: Phase Transitions
- [ ] "discovery_parsing_complete" → fase changes
- [ ] "masterplan_generation_start" → continúa con siguiente fase
- [ ] "masterplan_validation_start" → validation phase
- [ ] "masterplan_saving_start" → saving phase

### Fase 6: Completion
- [ ] "masterplan_generation_complete" → 100% y "Complete" status
- [ ] Final summary muestra totales correctos
- [ ] Timeline completa muestra todas las fases

### Fase 7: Post-Completion
- [ ] User puede cerrar modal con X button
- [ ] User puede cerrar con Escape key
- [ ] localStorage se limpia apropiadamente
- [ ] Puedo iniciar nueva generación

---

## ⚡ Performance Tips

### 1. Monitoring Without Overhead

```javascript
// ❌ MALO - Spam de console
useEffect(() => {
  console.log('[Hook] state changed:', state)
}, [state])

// ✅ BUENO - Conditional logging
const DEBUG = process.env.NODE_ENV === 'development'
useEffect(() => {
  if (DEBUG) console.log('[Hook] state changed:', state)
}, [state])
```

### 2. Event Deduplication

```javascript
// ✅ Ya implementado en useWebSocket.ts
// CircularEventBuffer deduplica eventos con:
// - Mismo type
// - Timestamp dentro de 100ms
```

### 3. Session ID Filtering Optimization

```javascript
// Problema: Filter en cada render
if (sessionId && events.length > 0) {
  const sessionEvents = events.filter(e => e.sessionId === sessionId)
}

// Solución: Cache filtered events
const memoizedSessionEvents = useMemo(
  () => events.filter(e => e.sessionId === sessionId),
  [events, sessionId]
)
```

### 4. Component Lazy Loading

```javascript
// ✅ Ya implementado
const ProgressMetrics = React.lazy(() => import('./ProgressMetrics'))

// Muestra fallback mientras carga
<Suspense fallback={<div>Loading...</div>}>
  <ProgressMetrics {...props} />
</Suspense>
```

---

## 📞 Contacto & Escalation

Si después de seguir esta guía el problema persiste:

1. **Generar Report Completo**:
   ```javascript
   const report = window.__masterplanDebug.exportFlow()
   console.save(report, 'masterplan-debug-report.json')
   ```

2. **Incluir en Issue Report**:
   - Debug report (JSON)
   - Console logs (error/warning)
   - Browser & OS version
   - Reproducción steps
   - Expected vs Actual behavior

3. **Archivos a Revisar**:
   - `src/websocket/manager.py` - Event emission logic
   - `src/ui/src/hooks/useWebSocket.ts` - Event capture
   - `src/ui/src/hooks/useChat.ts` - Event listening (16 listeners)
   - `src/ui/src/hooks/useMasterPlanProgress.ts` - State machine
   - `src/ui/src/components/chat/MasterPlanProgressModal.tsx` - UI rendering

---

## 📊 Métricas Esperadas

**Discovery Phase** (25% of total):
- Duration: 30-60 segundos
- Tokens: 4,000-8,000 tokens
- Entities: 2-10 bounded contexts, 5-15 aggregates, 15-50 entities

**MasterPlan Phase** (75% of total):
- Duration: 60-180 segundos
- Tokens: 10,000-30,000 tokens
- Entities: 3-10 phases, 8-20 milestones, 30-100 tasks

**Total Cost**: $0.05-$0.50 USD

---

**✅ Debugger Ready!** 🚀

Anda a la app, abre DevTools, genera un MasterPlan, y en la console:
```javascript
setupMasterPlanDebugger()
```

Luego en cualquier momento:
```javascript
window.__masterplanDebug.analyze()
```

Good luck, Ariel! 💪
