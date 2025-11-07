# 🧪 Testing MasterPlan Progress Modal - Quick Start Guide

Ariel, acá te dejo los 3 caminos para testear y debuggear el modal:

---

## 🚀 Opción 1: Validación Rápida (2 minutos)

```bash
cd /home/kwar/code/agentic-ai

# Ejecuta el script de validación
./src/ui/tests/validate-masterplan-sync.sh
```

**Qué hace:**
- ✅ Verifica que todos los archivos están en su lugar
- ✅ Chequea que React hooks tienen 16 listeners
- ✅ Valida que el state machine está implementado
- ✅ Revisa que el backend tiene todos los emitters
- ✅ Comprueba test coverage

**Output esperado:**
```
✅ All critical checks passed!

Next steps:
  1. Start the app and test the MasterPlan generation
  2. Open DevTools console (F12)
  3. Import the debugger:
     import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'
     setupMasterPlanDebugger()
  4. Generate a MasterPlan
  5. Run: window.__masterplanDebug.analyze()
```

---

## 🧪 Opción 2: E2E Tests Completos (10 minutos)

```bash
cd /home/kwar/code/agentic-ai/src/ui

# Ejecuta todos los tests
npm test -- MasterPlanProgressModal.e2e.test.ts

# O con UI interactivo
npx playwright test --ui MasterPlanProgressModal.e2e.test.ts

# O un test específico
npx playwright test -g "Discovery phase" MasterPlanProgressModal.e2e.test.ts
```

**Tests incluidos:**
1. ✅ Modal rendering
2. ✅ Discovery phase complete
3. ✅ Full flow (discovery → masterplan)
4. ✅ Real-time data sync
5. ✅ Entity counts
6. ✅ Session ID filtering
7. ✅ Error handling
8. ✅ Modal cleanup
9. ✅ Page reload recovery
10. ✅ Out-of-order events
11. ✅ Duplicate deduplication
12. ✅ Lazy loading
13. ✅ WebSocket room joining
14. ✅ Phase timeline
15. ✅ Cost calculation

---

## 🔍 Opción 3: Debugging Manual en Browser (15 minutos)

### Paso 1: Inicia la app
```bash
# Terminal 1 - API
cd /home/kwar/code/agentic-ai
python -m uvicorn src.api.main:app --reload --port 8000

# Terminal 2 - Frontend
cd /home/kwar/code/agentic-ai/src/ui
npm run dev  # Vite dev server en puerto 3000
```

### Paso 2: Abre el browser
```
http://localhost:3000
```

### Paso 3: Abre DevTools (F12) → Console

### Paso 4: Pega esto en la console
```javascript
// Importa el debugger
import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'

// Inicia el debugging
setupMasterPlanDebugger()

// Espera 5 segundos, el debugger auto-analiza...
```

### Paso 5: Genera un MasterPlan
- Escribe algo en el chat como: "Analyze a user authentication system"
- Click en "Generate MasterPlan"
- Mira el modal abrirse y llenarse de datos

### Paso 6: Revisa el análisis
```javascript
// En cualquier momento, obtén un reporte:
window.__masterplanDebug.analyze()

// Ver trace completa
window.__masterplanDebug.getFlowTrace()

// Exportar todo a JSON
const report = window.__masterplanDebug.exportFlow()
```

---

## 🎯 Qué Buscar en el Analysis

### ✅ Si todo está bien verás:

```
📊 MASTERPLAN PROGRESS FLOW ANALYSIS
═════════════════════════════════════════

⏱️  TIMELINE
  Start: 2025-11-06T14:22:45.123Z
  End:   2025-11-06T14:23:52.456Z
  Total Duration: 67350ms

📈 EVENT COUNTS
  discovery_generation_start: 1
  discovery_tokens_progress: 8
  discovery_entity_discovered: 3
  discovery_parsing_complete: 1
  discovery_generation_complete: 1
  masterplan_generation_start: 1
  masterplan_tokens_progress: 15
  masterplan_entity_discovered: 3
  masterplan_parsing_complete: 1
  masterplan_validation_start: 1
  masterplan_saving_start: 1
  masterplan_generation_complete: 1

✅ EVENT SEQUENCE
  ✅ discovery_generation_start
  ✅ discovery_generation_complete
  ✅ masterplan_generation_start
  ✅ masterplan_generation_complete
```

### ❌ Si hay problemas verás:

```
⚠️  ISSUES FOUND
  ❌ Invalid percentage: 150 for event discovery_tokens_progress
  ⚠️ Tokens received (9000) > estimated (8000)

✓ EVENT SEQUENCE
  ✅ discovery_generation_start
  ❌ discovery_generation_complete
  ❌ masterplan_generation_start
  ❌ masterplan_generation_complete
```

---

## 🐛 Problemas Comunes & Soluciones

### Problema: "Modal nunca abre"

```javascript
// Verifica en console que ves esto:
✅ [useChat] Registering 16 masterplan listeners...
🔍 [useChat::discovery_generation_start] LISTENER FIRED!

// Si NO ves estos logs:
// → El useChat hook no está mounted
// → WebSocketProvider no está wrapping la app
// → Event listener no se registró
```

### Problema: "Porcentaje stuck en 0%"

```javascript
// Verifica que ves esto en console:
📊 [WebSocket] discovery_tokens_progress received:

// Si NO ves estos logs:
// → Backend no está emitiendo eventos
// → Events se están perdiendo en WebSocket
// → Room join falló
```

### Problema: "Entity counts son 0"

```javascript
// Verifica que ves esto en console:
🔍 [WebSocket] discovery_entity_discovered received:

// Si NO ves estos logs:
// → Backend no emitiendo entity events
// → Entity type format incorrecto
// → State machine no actualizando counts
```

---

## 📊 Flujo de Datos (visualizado)

```
Backend emits:
  discovery_generation_start
        ↓
WebSocket (Socket.IO)
        ↓
useWebSocket Hook (CircularEventBuffer)
        ↓
useChat Hook (16 event listeners)
        ↓
setMasterPlanProgress (React state)
        ↓
useMasterPlanProgress Hook (State Machine)
        ↓
Zustand Store (persist + subscribers)
        ↓
Components (ProgressTimeline, ProgressMetrics)
        ↓
UI (Modal renders with data)
```

---

## 📚 Archivos Creados

Te dejé estos archivos para debugging:

```
✅ /src/ui/tests/MasterPlanProgressModal.e2e.test.ts
   └─ 15 test cases exhaustivos

✅ /src/ui/tests/debug-masterplan-flow.ts
   └─ Debugger que monitorea todo el flujo

✅ /src/ui/tests/validate-masterplan-sync.sh
   └─ Script de validación rápida

✅ /MASTERPLAN_PROGRESS_DEBUGGING_GUIDE.md
   └─ Guía completa (15 páginas)

✅ /TESTING_MASTERPLAN_MODAL.md
   └─ Este archivo (quick start)
```

---

## 🎬 Ejemplo Completo en 3 Steps

### Step 1: Validar estructura
```bash
./src/ui/tests/validate-masterplan-sync.sh
# Espera que diga "✅ All critical checks passed!"
```

### Step 2: Ejecutar E2E tests (1 test)
```bash
cd src/ui
npx playwright test -g "Full flow" MasterPlanProgressModal.e2e.test.ts
# Espera que pase sin errores
```

### Step 3: Debugging manual
```javascript
// En console del browser
import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'
setupMasterPlanDebugger()

// Genera un MasterPlan en la UI
// Luego:
window.__masterplanDebug.analyze()
```

---

## 💡 Pro Tips

1. **Para debug más detallado**, abre DevTools → Sources y pone breakpoints en:
   - `useMasterPlanProgress.ts` línea 214 (switch statement)
   - `MasterPlanProgressModal.tsx` línea 94 (useMasterPlanProgress call)

2. **Para ver el estado Zustand en tiempo real**, instala:
   - Chrome: Redux DevTools extension
   - Configura para Zustand

3. **Para monitorear WebSocket**, usa DevTools → Network → WS:
   - Busca `discovery_tokens_progress` messages
   - Verifica que llegan cada 100-200ms

4. **Para verificar localStorage**, usa:
   ```javascript
   localStorage.getItem('masterplan-store') // Zustand persistence
   ```

---

## ❓ FAQ

**P: ¿Cuánto tarda un test E2E?**
R: Cada test tarda ~5-15 segundos. Suite completa ~2 minutos.

**P: ¿Puedo correr un test específico?**
R: Sí, usa: `npx playwright test -g "Full flow"`

**P: ¿Qué pasa si un test falla?**
R: Playwright guarda videos/screenshots en `test-results/`

**P: ¿Puedo debuggear un test mientras corre?**
R: Sí, usa `--debug` flag: `npx playwright test --debug`

**P: ¿El debugger auto-stops después de cierto tiempo?**
R: No, corre indefinidamente. Llama `window.__masterplanDebug.clearFlowTrace()` para resetear.

---

## 🎯 Próximos Pasos

1. **Ejecuta la validación:**
   ```bash
   ./src/ui/tests/validate-masterplan-sync.sh
   ```

2. **Corre un test E2E:**
   ```bash
   cd src/ui && npx playwright test -g "Full flow"
   ```

3. **Debuggea manualmente si hay issues:**
   ```javascript
   setupMasterPlanDebugger()
   window.__masterplanDebug.analyze()
   ```

4. **Si todo está bien:**
   ```bash
   git commit -am "feat: Add comprehensive MasterPlan modal testing suite"
   ```

---

**¡Anda a probarlo, Ariel!** 🚀

Si encontrás algún problema, el análisis del debugger te dirá exactamente dónde está.
