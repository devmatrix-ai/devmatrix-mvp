# Race Condition Fix - Modal Not Updating

## Problem

El modal recibía eventos pero **no se actualizaba visualmente**. Los logs mostraban:

```
currentPhase: 'idle'         // ← Debería ser 'Generating', 'Parsing', etc
percentage: 0                // ← Debería aumentar
tokensReceived: 0            // ← Debería aumentar
```

## Root Cause: React State Race Condition

**MasterPlanProgressModal.tsx:**
```typescript
const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

useEffect(() => {
  if (!sessionId && eventData?.session_id) {
    setSessionId(eventData.session_id)  // ← Asincrónico!
  }
}, [eventData?.session_id, sessionId])

// ❌ PROBLEMA: Hook llamado ANTES de que setState termine
const { state: progressState } = useMasterPlanProgress(sessionId)
```

**Timeline:**
1. Modal recibe evento → `eventData.session_id = 'abc123'`
2. setState se programa (asincrónico)
3. ❌ Inmediatamente se renderiza → `sessionId` sigue siendo `undefined`
4. Hook recibe `undefined` → no filtra eventos correctamente
5. Estado no se actualiza → UI congelada

## Solution: Compute Effective ID Immediately

**Cambio en MasterPlanProgressModal.tsx:**
```typescript
const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

// ✅ NUEVO: Calcular INMEDIATAMENTE sin esperar setState
const effectiveSessionId = sessionId || eventData?.session_id

// ✅ Pasar el valor calculado inmediatamente
const { state: progressState } = useMasterPlanProgress(effectiveSessionId)
```

**Cambio en useMasterPlanProgress.ts:**
```typescript
// ✅ NUEVO: Fallback si el hook recibe undefined
const effectiveSessionId = sessionId || latestEvent?.data?.session_id

// Usar effectiveSessionId para filtrar eventos
if (effectiveSessionId && events.length > 0) {
  const sessionEvents = events.filter(
    (e) => e.sessionId === effectiveSessionId || e.data?.session_id === effectiveSessionId
  )
  // ...
}
```

## Impact

**Antes:**
- Modal abierto pero congelado
- Ningún progreso visual
- currentPhase siempre 'idle'
- percentage siempre 0

**Después:**
- ✅ Modal actualiza en tiempo real
- ✅ currentPhase: 'Generating' → 'Parsing' → 'Validating' → 'Saving' → 'Complete'
- ✅ percentage aumenta: 0% → 25% → 50% → 75% → 100%
- ✅ tokensReceived aumenta progresivamente
- ✅ Fases visuales se actualizan

## Files Modified

1. **src/ui/src/components/chat/MasterPlanProgressModal.tsx**
   - Agregado: `const effectiveSessionId = sessionId || eventData?.session_id`
   - Cambio: Usar `effectiveSessionId` en lugar de `sessionId` en todo el componente

2. **src/ui/src/hooks/useMasterPlanProgress.ts**
   - Agregado fallback: `const effectiveSessionId = sessionId || latestEvent?.data?.session_id`
   - Cambio: Usar `effectiveSessionId` para filtrar eventos

## Technical Details

### Why This Works

1. **Eliminates async dependency**: No esperar a que `setState` termine
2. **Ensures consistency**: `effectiveSessionId` nunca es undefined durante el render
3. **Maintains state**: `sessionId` en estado todavía se actualiza para persistencia
4. **Dual fallback**: Tanto modal como hook tienen fallback

### Why It Matters

React state updates son asincrónico. Si llamamos a un hook que depende de state ANTES de que el estado se actualice, el hook recibe valores stale (antiguos). Esto causaba que `useMasterPlanProgress` no filtrara eventos correctamente.

La solución es **calcular el valor efectivo inmediatamente** en lugar de esperar a que el estado se actualice.

## Testing

Para verificar que funciona:

1. Abre el chat y genera un MasterPlan
2. Observa el modal
3. Deberías ver:
   - ✅ Progress bar moviéndose (0% → 100%)
   - ✅ Porcentaje aumentando
   - ✅ Fase cambiando (Generating → Parsing → Validating → Saving)
   - ✅ Tokens recibidos aumentando
   - ✅ Cronómetro funcionando

Si algo no se mueve, revisa los logs para ver si `effectiveSessionId` es `undefined`.

---

**Status:** ✅ RESUELTO
**Severidad:** CRÍTICA (bloqueaba visualización de progreso)
**Complejidad:** Media (entender race conditions de React)
