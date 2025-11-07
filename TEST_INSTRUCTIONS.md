# 🧪 Instrucciones de Test - MasterPlan Progress Modal Fix

**Objetivo**: Verificar que el fix del race condition funciona correctamente

---

## Preparación (5 minutos)

### Paso 1: Asegurarse que todo está corriendo
```bash
docker compose ps
# Debe mostrar todos los containers en estado "Up" o "healthy"
```

### Paso 2: Abrir la aplicación
```
Abrir navegador: http://localhost:3000
Debe mostrar: DevMatrix Chat Interface
```

### Paso 3: Verificar conexión
- Buscar en el header del chat: punto verde "Connected" ✅
- Si es rojo "Disconnected" → Recargar página (F5)

---

## Test Principal (2 minutos por generación)

### Paso 1: Abrir DevTools
```
Presionar: F12 o Ctrl+Shift+I
Ir a: Console tab
Limpiar logs previos: Ctrl+L o click en ícono de basura
```

### Paso 2: Enviar comando para generar MasterPlan
En el chat escribir:
```
/masterplan Create a simple Todo list API
```

**Resultado esperado**: Modal se abre inmediatamente (< 2 segundos)

### Paso 3: Observar progreso en el modal

**Debe ver movimiento en estos elementos**:

#### a) Progress Bar
- Comienza en 0%
- Aumenta gradualmente: 0% → 25% → 50% → 75% → 100%
- NO debe quedarse en 0% por > 5 segundos

#### b) Current Phase Text
- Comienza: "Generating"
- Progresa: "Parsing" → "Validating" → "Saving" → "Complete"
- NO debe quedarse en "idle"

#### c) Tokens Display
- Comienza en 0
- Aumenta: 100 → 500 → 1000 → 2000 → 5000+
- NO debe quedarse en 0

#### d) Duration / Timer
- Comienza contando: 1s → 2s → 3s → ... → 35s+
- Debe mostrar tiempo real de ejecución

### Paso 4: Verificar logs en DevTools Console

**Buscar estas líneas (orden importante)**:

1️⃣ **DENTRO DE 1 SEGUNDO**: Modal abre y sessionId se establece
```
[MasterPlanProgressModal] Current sessionId: {
  sessionId: undefined,
  effectiveSessionId: "AQUI_DEBE_HABER_UN_ID",  ← ¡¡CRÍTICO!!
  propMasterplanId: undefined,
  ...
}
```
✅ **CLAVE**: `effectiveSessionId` debe tener valor (ej: "abc123xyz")
❌ **PROBLEMA**: Si dice `undefined`, el fix no está funcionando

2️⃣ **DENTRO DE 2-3 SEGUNDOS**: Hook empieza a filtrar eventos
```
[useMasterPlanProgress] Filtering events for session: {
  sessionId: "AQUI_DEBE_SER_EL_MISMO_ID",  ← Debe coincidir con arriba
  totalEvents: 3,
  filteredEvents: 3,  ← ¡¡DEBE SER > 0!!
  latestEvent: "discovery_generation_start",
  matchedEvents: [...]
}
```
✅ **CLAVE**: `filteredEvents` debe ser > 0
❌ **PROBLEMA**: Si es 0, los eventos no se están filtrando correctamente

3️⃣ **DURANTE GENERACIÓN**: Eventos siendo procesados
```
[useMasterPlanProgress] Processing event: {
  eventType: "discovery_tokens_progress",
  ...
}
```
✅ **CLAVE**: Debe ver múltiples líneas de "Processing event"
❌ **PROBLEMA**: Si no ve nada, los eventos no se procesan

4️⃣ **AL FINAL**: Generación completa
```
[useMasterPlanProgress] Processing event: {
  eventType: "masterplan_generation_complete",
  ...
}
```
✅ **CLAVE**: `masterplan_generation_complete` debe aparecer
❌ **PROBLEMA**: Si nunca aparece, la generación no termina (error backend)

---

## Resultados Esperados

### ✅ SUCCESS (Fix funciona correctamente)
- [x] Modal se abre en < 2 segundos
- [x] Progress bar se mueve (no congelado en 0%)
- [x] Fase cambia (no congelado en 'idle')
- [x] Tokens aumentan
- [x] DevTools muestra `effectiveSessionId` con valor
- [x] DevTools muestra `filteredEvents: > 0`
- [x] DevTools muestra líneas de "Processing event"
- [x] Modal muestra completion o summary al final

**Tiempo total**: 30-60 segundos

### ❌ FAILURE (Fix no funciona)
- [ ] Modal no se abre
- [ ] Modal se abre pero progress bar congelado en 0%
- [ ] Fase congelada en 'idle'
- [ ] Tokens no aumentan
- [ ] DevTools muestra `effectiveSessionId: undefined`
- [ ] DevTools muestra `filteredEvents: 0`
- [ ] Ninguna línea "Processing event"
- [ ] Modal se cierra antes de completar

---

## Diagnóstico Si Falla

### ¿Qué significa cada síntoma?

#### Síntoma: Modal no abre
**Posibles causas**:
- WebSocket no conectada (verificar punto verde en header)
- Backend no respondiendo (verificar logs de API)
- Error en frontend (ver console para errores rojo)

**Acción**:
```bash
# Verificar backend
curl -s http://localhost:8000/health | jq
# Debe retornar status: "healthy"

# Verificar WebSocket
# En DevTools ver Network tab → WS → Messages
```

#### Síntoma: `effectiveSessionId: undefined`
**Significa**: El sessionId no se extrajo del evento
**Posibles causas**:
- Event prop vacío
- Event.data no tiene session_id field
- useRef no inicializado correctamente

**Acción**:
- Verificar en console: ¿event tiene data?
- Verificar: ¿event.data.session_id existe?

#### Síntoma: `filteredEvents: 0`
**Significa**: Hook recibió sessionId pero eventos no coinciden
**Posibles causas**:
- sessionId no es el mismo entre modal y hook
- Eventos tienen session_id diferente
- Bug en lógica de filtrado

**Acción**:
```javascript
// En console, ejecutar:
console.log("Buscando sessionId en eventos");
// Copiar sessionId del log
// Buscar en WebSocket events si coincide
```

#### Síntoma: Progress bar congelado pero logs muestran eventos
**Significa**: Eventos se procesan pero UI no actualiza
**Posibles causas**:
- Component no re-renderiza
- State update no dispara
- Props no cambian

**Acción**:
```javascript
// En console, ejecutar:
// 1. Revisar si progressState cambia
// 2. Ver si ProgressMetrics component actualiza
// 3. Revisar dependencies en useEffect
```

---

## Capturas de Pantalla Esperadas

### Durante Generación
```
┌─ MasterPlan Generation Progress ─────────────┐
│                                              │
│  Phase: Generating (Discovery)              │
│                                              │
│  Progress: ████████░░░░░░░░░░░░░ 35%       │
│                                              │
│  Tokens: 1,245 / 8,000                     │
│  Duration: 12 seconds                       │
│                                              │
│  ✓ Discovery phase                         │
│  ◐ Parsing phase (in progress)            │
│  ○ Validation phase                        │
│  ○ Saving phase                            │
│                                              │
│  [View Details] [Start Execution]          │
└──────────────────────────────────────────────┘
```

### Al Completar
```
┌─ MasterPlan Generation Complete ──────────────┐
│                                               │
│  ✓ Successfully completed!                   │
│                                               │
│  Summary:                                    │
│  • Total Tokens: 5,234 / 8,000 (65%)        │
│  • Generation Cost: $0.32 USD                │
│  • Duration: 42 seconds                      │
│  • Bounded Contexts: 3                       │
│  • Aggregates: 12                            │
│  • Entities: 45                              │
│  • Phases: 4                                 │
│  • Milestones: 18                            │
│  • Tasks: 256                                │
│                                               │
│  [Close] [View Details] [Start Execution]    │
└───────────────────────────────────────────────┘
```

---

## Reporte de Resultados

### Si el test FUNCIONA ✅
Por favor reportar:
```
RESULTADO: ✅ SUCCESS
Timestamp: [Ahora - HH:MM]
Generación: Todo funcionó normalmente
Observaciones: [Detalles adicionales si hay]
```

### Si el test FALLA ❌
Por favor reportar CON ESTA INFORMACIÓN:
```
RESULTADO: ❌ FAILURE
Timestamp: [Ahora - HH:MM]
Síntoma: [Descripción de qué no funciona]
Logs de console:
[Copiar/pegar logs relevantes aquí, especialmente:]
  - [MasterPlanProgressModal] Current sessionId
  - [useMasterPlanProgress] Filtering events
  - [Cualquier error rojo en console]
Pasos para reproducir: [Lista de acciones]
```

---

## Tips de Debugging Avanzado

### 1. Usar browser DevTools bien
```
F12 → Console
- Filtrar por palabra: "MasterPlanProgressModal"
- Copiar logs enteros para analizar
- Usar $copy() para copiar al clipboard
```

### 2. Monitorear WebSocket en tiempo real
```
F12 → Network tab → WS tab → (WebSocket URL)
- Expandir "Messages"
- Ver qué eventos se emiten en tiempo real
- Buscar "session_id" en los eventos
```

### 3. Verificar state en React DevTools (si instalado)
```
F12 → React Components
- Buscar: MasterPlanProgressModal
- Expandir: Props y State
- Verificar: sessionId values, effectiveSessionId, progressState
```

### 4. Ejecutar diagnóstico desde console
```javascript
// Ejecutar esto en console mientras genera:
setInterval(() => {
  console.log("WebSocket connected:", window.socket?.connected);
  console.log("Modal visible:", document.querySelector('[role="dialog"]') !== null);
}, 2000);
```

---

## Escalada si No Funciona

Si después de diagnosticar el problema persiste:

1. **Guardar logs completos**:
   - Seleccionar todo en console (Ctrl+A)
   - Copiar (Ctrl+C)
   - Pegar en archivo `debug_logs.txt`

2. **Captura de pantalla**:
   - Tomar screenshot del modal y console
   - Guardar como `modal_test_failure.png`

3. **Reportar con evidencia**:
   - Descripción clara del síntoma
   - Logs completos del console
   - Screenshot del estado
   - Exactamente qué mensajes ves o NO ves

---

## Checklist Final

Antes de considerar el test como "COMPLETADO":

- [ ] Abrí http://localhost:3000 en navegador
- [ ] WebSocket conectada (punto verde)
- [ ] Envié comando `/masterplan`
- [ ] Modal se abrió < 2 segundos
- [ ] Observé progreso en 3+ de estos: barra, fase, tokens, duración
- [ ] Abría DevTools durante generación
- [ ] Vi logs de `effectiveSessionId` con valor
- [ ] Vi logs de `filteredEvents: > 0`
- [ ] Vi logs de `Processing event` múltiples veces
- [ ] Generación completó (o mostró error específico)
- [ ] Capturé screenshot o logs si algo falló

---

**¡Listo! Comienza el test 🚀**

Reporta resultados cuando completes.
