# sessionId Race Condition Fix - Verification Analysis

**Date**: 2025-11-06
**Status**: ✅ CODE FIX APPLIED - AWAITING USER TEST VERIFICATION

---

## Problem Statement (Original)

Modal was receiving WebSocket events but **NOT updating visually**:
- Percentage stuck at 0%
- currentPhase stuck at 'idle'
- UI completely frozen despite events arriving

**Root Cause**: React state race condition
- Modal receives event with `session_id` field
- Modal tries to pass this to hook via `useState` state
- But `setState` is asynchronous - React renders BEFORE state updates
- Hook receives `undefined` instead of actual sessionId
- Hook can't filter events → state doesn't update → UI stays frozen

---

## Fix Applied: useRef-Based Approach

### Before (Broken)
```typescript
const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

// ❌ PROBLEM: setState is async, hook gets undefined
const { state: progressState } = useMasterPlanProgress(sessionId)
```

**Timeline of Failure**:
1. Event arrives: `eventData.session_id = 'abc123'`
2. `setState` queued (asynchronous)
3. Render happens immediately (sessionId still undefined)
4. Hook called with undefined
5. Hook can't filter events → no state update → frozen UI

### After (Fixed)
```typescript
// Store sessionId in ref ONCE - prevents race condition
const sessionIdRef = useRef<string | undefined>(propMasterplanId)
const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

// Initialize immediately on render if event has sessionId
if (!sessionIdRef.current && eventData?.session_id) {
  sessionIdRef.current = eventData.session_id
  if (!sessionId) {
    setSessionId(eventData.session_id)
  }
}

// Use ref value - ALWAYS consistent, NEVER undefined after first event
const effectiveSessionId = sessionIdRef.current

// Pass STABLE value to hook (not dependent on setState)
const { state: progressState } = useMasterPlanProgress(effectiveSessionId)
```

**Why This Works**:
1. Event arrives: `eventData.session_id = 'abc123'`
2. Ref is updated IMMEDIATELY in render: `sessionIdRef.current = 'abc123'`
3. `effectiveSessionId = sessionIdRef.current` → Always has the value
4. Hook gets consistent value → Can filter events properly → State updates → UI updates ✅

---

## Code Changes Verification

### File: MasterPlanProgressModal.tsx (Lines 50-107)

✅ **Ref created and initialized**:
```typescript
const sessionIdRef = useRef<string | undefined>(propMasterplanId)  // Line 53
const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)  // Line 54
```

✅ **Ref updated immediately on first event**:
```typescript
if (!sessionIdRef.current && eventData?.session_id) {  // Line 57
  sessionIdRef.current = eventData.session_id  // Line 58
  if (!sessionId) {
    setSessionId(eventData.session_id)  // Line 60
  }
}
```

✅ **Computed effectiveSessionId from ref**:
```typescript
const effectiveSessionId = sessionIdRef.current  // Line 65
```

✅ **Passed to hook immediately**:
```typescript
const {
  state: progressState,
  phases,
  handleRetry,
  clearError,
  isLoading,
} = useMasterPlanProgress(effectiveSessionId);  // Line 107
```

✅ **Backup room joins use correct ID**:
```typescript
wsService.send('join_discovery', { session_id: effectiveSessionId });  // Line 85
wsService.send('join_masterplan', { masterplan_id: effectiveSessionId });  // Line 86
```

✅ **All useEffect dependencies updated**:
```typescript
}, [open, effectiveSessionId]);  // Line 96 - uses effectiveSessionId, not sessionId
```

### File: useMasterPlanProgress.ts (Lines 158)

✅ **Fallback sessionId extraction**:
```typescript
const effectiveSessionId = sessionId || latestEvent?.data?.session_id  // Line 158
```

This provides double protection:
- If hook receives sessionId from modal → use it
- If not → try to extract from latest event

---

## Expected Behavior After Fix

### When Generation Starts

**Console logs should show**:
```
[MasterPlanProgressModal] Current sessionId: {
  sessionId: undefined,
  effectiveSessionId: "abc123xyz",  // ← KEY: Should NOT be undefined
  propMasterplanId: undefined,
  eventSessionId: "abc123xyz"
}

[useMasterPlanProgress] Filtering events for session: {
  sessionId: "abc123xyz",  // ← KEY: Hook receives correct sessionId
  totalEvents: 3,
  filteredEvents: 3,
  latestEvent: "discovery_generation_start",
  matchedEvents: ["discovery_generation_start"]
}
```

### UI Updates Should Show

1. **Progress bar moving**: 0% → 25% → 50% → 75% → 100%
2. **Phase changing**:
   - "Generating" → "Parsing" → "Validating" → "Saving" → "Complete"
3. **Tokens increasing**: 0 → 100 → 500 → 2500 → 5000+
4. **Duration increasing**: 1s → 5s → 15s → 30s+

---

## If Modal Still Doesn't Update

### Diagnosis Steps

1. **Check effectiveSessionId is NOT undefined**:
   - Open DevTools → Console
   - Look for `[MasterPlanProgressModal] Current sessionId` log
   - Verify `effectiveSessionId` has a value (not undefined)
   - If undefined → sessionId not being extracted from event

2. **Check hook receives sessionId**:
   - Look for `[useMasterPlanProgress] Filtering events for session` log
   - Verify `sessionId` field has value
   - If undefined → hook not receiving ID from modal

3. **Check events are being filtered**:
   - Look at `filteredEvents` count vs `totalEvents`
   - If filteredEvents = 0 → events not matching sessionId filter
   - If filteredEvents > 0 → events filtered correctly

4. **Check state update is processing**:
   - Look for `[useMasterPlanProgress] Processing event:` logs
   - Should see event types: `discovery_generation_start`, `discovery_tokens_progress`, etc.
   - If no logs → state update not running

---

## Root Cause of Previous Failures

### First Fix Attempt (Failed)
```typescript
// ❌ WRONG: This recalculates on EVERY render
const effectiveSessionId = sessionId || eventData?.session_id

// Problem: sessionId changes as state updates → dependency issues
// Results: Inconsistent values passed to hook, events re-processed incorrectly
```

**User reported**: "pues nada cada vez peor ahora directamente no muestra avance alguno"
- **Why it failed**: Recalculating on each render caused hook dependency instability
- **Effect**: Made things worse because sessionId value was jumping between undefined and actual value

### Current Fix (Should Work)
```typescript
// ✅ CORRECT: Use ref for stable value
const sessionIdRef = useRef<string | undefined>(propMasterplanId)

// Initialize once, never changes
if (!sessionIdRef.current && eventData?.session_id) {
  sessionIdRef.current = eventData.session_id
}

// Always consistent
const effectiveSessionId = sessionIdRef.current
```

**Why this works**:
- Ref value is stable across renders
- Hook receives same sessionId consistently
- Events filtered correctly every time
- State updates work as expected

---

## Critical Dependencies Checked

### useEffect in MasterPlanProgressModal (Line 96)
```typescript
useEffect(() => {
  if (open && effectiveSessionId) {
    // Join rooms...
  }
}, [open, effectiveSessionId]);  // ✅ Uses effectiveSessionId not sessionId
```

✅ **CORRECT**: Dependencies use `effectiveSessionId` (stable ref value)

### useEffect in useMasterPlanProgress (Line 476)
```typescript
useEffect(() => {
  // Event processing...
}, [events, sessionId, latestEvent, updatePhaseStatus, calculateElapsedSeconds])
```

✅ **CORRECT**: `sessionId` dependency will trigger updates when hook is called with different value

---

## Test Checklist

- [ ] Open browser at http://localhost:3000
- [ ] Navigate to chat interface
- [ ] Type `/masterplan Create a Task Management API`
- [ ] Send message
- [ ] **Observe modal opens** (within 2 seconds)
- [ ] **Check progress bar moves** (not stuck at 0%)
- [ ] **Check phase updates** (not stuck at 'idle')
- [ ] **Check tokens increase** (visible number changes)
- [ ] **Check duration increases** (seconds ticking up)
- [ ] **Modal completes** (shows final summary or closes)
- [ ] **Check DevTools console** for key logs:
  - `[MasterPlanProgressModal] Current sessionId:` - effectiveSessionId should have value
  - `[useMasterPlanProgress] Filtering events:` - sessionId should match
  - `[useMasterPlanProgress] Processing event:` - multiple event types shown

---

## Expected Timeline

| Event | Time | Indicator |
|-------|------|-----------|
| Modal opens | 0s | First event received |
| Discovery starts | 0-2s | Phase: "Generating" |
| Discovery tokens flow | 2-10s | Percentage: 5-20%, Tokens: 0-1000 |
| Discovery complete | 10-15s | Phase: "Discovery Complete", Percentage: 25% |
| MasterPlan starts | 15-16s | Phase: "MasterPlan Generation" |
| Parsing | 16-20s | Phase: "Parsing", Percentage: 40-50% |
| Validation | 20-25s | Phase: "Validating", Percentage: 70% |
| Saving | 25-30s | Phase: "Saving", Percentage: 90% |
| Complete | 30-35s | Phase: "Complete", Percentage: 100% |

---

## Files Modified in This Session

1. ✅ `src/ui/src/components/chat/MasterPlanProgressModal.tsx` - useRef fix applied
2. ✅ `src/ui/src/hooks/useMasterPlanProgress.ts` - fallback sessionId extraction
3. ✅ `src/ui/src/components/chat/ChatWindow.tsx` - preserved progress via ref
4. ✅ `src/ui/src/stores/masterplanStore.ts` - added currentDiscoveryId field
5. ✅ `src/websocket/manager.py` - added metadata fields to emissions
6. ✅ `src/services/masterplan_generator.py` - pass metadata to websocket

---

## Conclusion

✅ **Code fix is syntactically correct and logically sound**

The useRef-based approach:
- Eliminates the race condition by providing stable sessionId
- Passes stable value to hook for consistent event filtering
- Uses fallback for additional safety
- Has all correct dependencies

**Next Step**: User should test MasterPlan generation and verify the modal updates properly.

If modal still frozen after this test, debug with the diagnosis steps above to identify the exact bottleneck.
