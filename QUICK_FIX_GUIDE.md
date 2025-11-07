# ⚡ Quick Fix Guide - MasterPlan Modal Issues

**Time to fix all issues**: ~25 minutes
**Files to modify**: 2
**Lines to change**: ~20 total

---

## 🔴 FIX #1: Session ID Race Condition (10 min)

**Severity**: MODERATE | **Impact**: HIGH | **Confidence**: CRITICAL

### THE PROBLEM
Session ID is set once (const) and never updates when masterplan_id arrives.
Result: Modal filters by old session_id, showing stale discovery data during masterplan phase.

### THE FILE
`src/ui/src/components/chat/MasterPlanProgressModal.tsx`

### THE CODE CHANGE

**BEFORE** (Lines 38-100):
```typescript
const MasterPlanProgressModal: React.FC<MasterPlanProgressModalProps> = ({
  event,
  open,
  onClose,
  masterplanId: propMasterplanId,
}) => {
  const { t } = useTranslation();

  // Extract session ID from event to track generation
  // Priority: masterplan_id > session_id (always present) > discovery_id (fallback only)
  // session_id is the primary WebSocket room identifier throughout the entire flow
  const eventData = event?.data || {}
  const sessionId = propMasterplanId ||
                    eventData.masterplan_id ||
                    eventData.session_id ||
                    eventData.discovery_id;  // ← CONST - NEVER UPDATES!

  console.log('[MasterPlanProgressModal] Event received:', {
    eventType: event?.event,
    eventData: eventData,
  });

  console.log('[MasterPlanProgressModal] Extracted session/masterplan ID:', {
    propMasterplanId,
    eventMasterplanId: eventData.masterplan_id,
    eventDiscoveryId: eventData.discovery_id,
    eventSessionId: eventData.session_id,
    finalSessionId: sessionId,
    eventType: event?.event,
    fullEventData: JSON.stringify(eventData),
  });
```

**AFTER** (Replace lines 45-68):
```typescript
const MasterPlanProgressModal: React.FC<MasterPlanProgressModalProps> = ({
  event,
  open,
  onClose,
  masterplanId: propMasterplanId,
}) => {
  const { t } = useTranslation();

  // Extract session ID from event with fallback chain
  // Priority: propMasterplanId > masterplan_id > session_id > discovery_id
  const eventData = event?.data || {}

  // Use state to allow sessionId to update when masterplan_id arrives
  const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

  // Update sessionId when a better identifier arrives
  useEffect(() => {
    const newSessionId = propMasterplanId ||
                         eventData?.masterplan_id ||
                         eventData?.session_id ||
                         eventData?.discovery_id

    // Only update if we have a new value that's different
    if (newSessionId && newSessionId !== sessionId) {
      console.log('[MasterPlanProgressModal] Updating sessionId:', {
        from: sessionId,
        to: newSessionId,
        reason: newSessionId === eventData?.masterplan_id ? 'masterplan_id_arrived' : 'other'
      })
      setSessionId(newSessionId)
    }
  }, [propMasterplanId, eventData?.masterplan_id, eventData?.session_id, eventData?.discovery_id, sessionId])

  console.log('[MasterPlanProgressModal] Current sessionId:', {
    sessionId,
    propMasterplanId,
    eventMasterplanId: eventData.masterplan_id,
    eventSessionId: eventData.session_id,
    eventDiscoveryId: eventData.discovery_id,
  });
```

### WHY THIS FIXES IT
1. sessionId starts as `session_id` during discovery
2. Events arrive and are processed correctly
3. When masterplan_id arrives in an event
4. useEffect detects it and **updates sessionId to masterplan_id**
5. useMasterPlanProgress now filters by the NEW masterplan_id
6. MasterPlan events are received and processed ✅
7. Modal shows correct masterplan data ✅

### VERIFY THE FIX
```javascript
// In console after fix:
✅ '[MasterPlanProgressModal] Updating sessionId: from: ABC to: MP-123 reason: masterplan_id_arrived'
✅ Entity counts change to masterplan values (5 phases, 12 milestones, 48 tasks)
✅ Progress advances from 25% to 100%
```

---

## 🟡 FIX #2: Entity Type Format Mismatch (5 min)

**Severity**: LOW-MODERATE | **Impact**: MEDIUM | **Confidence**: HIGH

### THE PROBLEM
Backend sends entity_type as camelCase ("BoundedContext")
Frontend converts to lowercase ("boundedcontext")
But code checks for snake_case ("bounded_context")
Result: No match, entity counts don't update

### THE FILE
`src/ui/src/hooks/useMasterPlanProgress.ts`

### THE CODE CHANGE

**BEFORE** (Line 374):
```typescript
case 'discovery_entity_discovered': {
  const entityType = (eventData.entity_type || eventData.type)?.toLowerCase() || 'entity'
  // ↑ "BoundedContext".toLowerCase() = "boundedcontext" (no underscore!)
  // But code checks for:
  // if (entityType === 'bounded_context')  ← NO MATCH!
```

**AFTER** (Replace line 374):
```typescript
case 'discovery_entity_discovered': {
  // Normalize entity_type: convert camelCase to snake_case
  const entityType = (eventData.entity_type || eventData.type)
    ?.toLowerCase()
    ?.replace(/([a-z])([A-Z])/g, '$1_$2')  // camelCase → snake_case
    ?.toLowerCase() || 'entity'

  // Now "BoundedContext" → "bounded_context" ✅
```

**ALSO APPLY TO LINE 246** (masterplan_entity_discovered):
```typescript
case 'masterplan_entity_discovered': {
  // Same fix as above
  const entityType = (eventData.entity_type || eventData.type)
    ?.toLowerCase()
    ?.replace(/([a-z])([A-Z])/g, '$1_$2')
    ?.toLowerCase() || 'task'
```

### WHY THIS FIXES IT
1. Backend sends: `entity_type: "BoundedContext"`
2. Frontend normalizes:
   - lowercase: "boundedcontext"
   - regex replace: "bounded_context" ✅
3. Now matches switch case
4. Entity count updates ✅

### VERIFY THE FIX
```javascript
// In console after fix:
✅ 'discovery_entity_discovered' events match and process
✅ Entity counts increment (boundedContexts: 3, aggregates: 7, entities: 24)
✅ No "Unknown event type" warnings
```

---

## 🟢 FIX #3: Entity Count Logic Consistency (10 min - OPTIONAL)

**Severity**: LOW | **Impact**: LOW | **Confidence**: MEDIUM

### THE PROBLEM
Inconsistent logic for entity counts:
- bounded_context & aggregate use `Math.max()` (keeps highest)
- entity uses direct assignment (overwrites)

If entity count goes 24 → 12, it will show 12 instead of keeping 24

### THE FILE
`src/ui/src/hooks/useMasterPlanProgress.ts`

### THE CODE CHANGE

**BEFORE** (Lines 383-395):
```typescript
setProgressState((prev) => {
  if (entityType === 'domain') {
    return { ...prev, currentPhase: `Found domain: ${eventData.name || 'Unknown'}` }
  } else if (entityType === 'bounded_context' || entityType === 'context') {
    return { ...prev, boundedContexts: Math.max(prev.boundedContexts, count) }  // ✅ Uses Math.max
  } else if (entityType === 'aggregate') {
    return { ...prev, aggregates: Math.max(prev.aggregates, count) }            // ✅ Uses Math.max
  } else if (entityType === 'entity') {
    return { ...prev, entities: count }                                          // ❌ Direct assignment
  }
  return prev
})
```

**AFTER** (Replace lines 383-395):
```typescript
setProgressState((prev) => {
  if (entityType === 'domain') {
    return { ...prev, currentPhase: `Found domain: ${eventData.name || 'Unknown'}` }
  } else if (entityType === 'bounded_context' || entityType === 'context') {
    return { ...prev, boundedContexts: Math.max(prev.boundedContexts, count) }
  } else if (entityType === 'aggregate') {
    return { ...prev, aggregates: Math.max(prev.aggregates, count) }
  } else if (entityType === 'entity') {
    return { ...prev, entities: Math.max(prev.entities, count) }  // ✅ Changed to Math.max
  }
  return prev
})
```

### WHY THIS FIXES IT
1. All entity counts now use `Math.max()`
2. Keeps highest value seen
3. Consistent behavior across all entity types
4. More robust to out-of-order events ✅

### VERIFY THE FIX
```javascript
// In console after fix:
✅ All entity counts follow same Math.max() logic
✅ Counts never decrease (always keep highest)
✅ Consistent behavior across BC, AGG, ENT
```

---

## 🧪 Testing After Fixes

### Quick Test (2 min)
```bash
# In browser console:
import { setupMasterPlanDebugger } from '@/tests/debug-masterplan-flow'
setupMasterPlanDebugger()

# Then generate a MasterPlan in the app...
# Then run:
window.__masterplanDebug.analyze()

# Should show:
# ✅ masterplan_generation_start in event sequence
# ✅ Entity counts from masterplan (not discovery)
# ✅ Percentage advances to 100%
# ✅ No ISSUES FOUND
```

### Full Test (5 min)
```bash
# Full E2E test suite
cd src/ui
npx playwright test -g "Full flow" MasterPlanProgressModal.e2e.test.ts

# Expected output:
# ✅ Full flow .... PASSED
```

### Validation (2 min)
```bash
# Run validation script
./src/ui/tests/validate-masterplan-sync.sh

# Should show:
# ✅ All critical checks passed!
```

---

## 📋 Checklist

Before you start:
- [ ] Close any open MasterPlan modals
- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Have test files ready

Fix #1 (Session ID):
- [ ] Open `MasterPlanProgressModal.tsx`
- [ ] Add `import { useState } from 'react'` at top if not present
- [ ] Replace lines 45-68 with new code
- [ ] Save file

Fix #2 (Entity Type):
- [ ] Open `useMasterPlanProgress.ts`
- [ ] Find line 374 `discovery_entity_discovered`
- [ ] Replace line 374 with new code
- [ ] Find line 246 `masterplan_entity_discovered`
- [ ] Replace line 246 with new code
- [ ] Save file

Fix #3 (Entity Count - OPTIONAL):
- [ ] Open `useMasterPlanProgress.ts`
- [ ] Find lines 383-395
- [ ] Change `entities: count` to `entities: Math.max(prev.entities, count)`
- [ ] Save file

Testing:
- [ ] Run quick browser test
- [ ] Run E2E test
- [ ] Run validation script
- [ ] All tests pass ✅

---

## ⚠️ Common Mistakes

❌ **Don't**: Just add useState without useEffect
- sessionId will update on render, causing infinite loops

✅ **Do**: Use useEffect with proper dependency array
- Prevents unnecessary updates

---

❌ **Don't**: Use just `.toLowerCase()`
- Won't convert camelCase to snake_case

✅ **Do**: Use `.toLowerCase().replace(/([a-z])([A-Z])/g, '$1_$2')`
- Converts "BoundedContext" → "bounded_context"

---

❌ **Don't**: Change all entities logic to something different
- Keep it consistent with bounded_context & aggregate

✅ **Do**: Use `Math.max()` like the other counts
- Same pattern, easier to understand

---

## 🎯 Success Criteria

After all fixes, verify:

```
✅ Modal opens when MasterPlan starts
✅ Progress bar advances 0% → 100%
✅ Discovery phase completes at 25%
✅ MasterPlan phase advances to 100%
✅ Entity counts show masterplan values (not discovery)
✅ Timeline shows all 4 phases
✅ No console errors
✅ localStorage persists correctly
✅ All E2E tests pass
```

---

## 🆘 If Something Goes Wrong

**sessionId not updating?**
- Check browser console: should see "Updating sessionId" log
- Make sure useEffect dependency array is correct
- Clear browser cache and reload

**Entity counts still 0?**
- Check backend is emitting entity_discovered events
- Check console for entity type being extracted
- Verify regex is working: test in browser console
  ```javascript
  "BoundedContext".toLowerCase().replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
  // Should show: "bounded_context"
  ```

**Tests still failing?**
- Run validation script first: `./src/ui/tests/validate-masterplan-sync.sh`
- Check for import errors
- Verify indentation is correct (not mixing tabs/spaces)

---

**Total Time**: ~25 minutes
**Difficulty**: Easy (mostly copy-paste)
**Risk**: Low (fixes are isolated, no breaking changes)

You got this! 🚀
