# MasterPlan Visibility Improvements - Requirements

## User Answers & Analysis

### 1. UI Location: Modal + Hybrid Approach
**User Answer**: Modal, pero tené en cuenta que ya hay algo inline
**Analysis**:
- Current: `MasterPlanProgressIndicator.tsx` (14.2 KB) displays inline in chat messages
- Recommendation: **Hybrid approach** - Keep compact header inline (50px), offer modal for detailed view
- Benefits: No disruption to chat, always visible, details on-demand
- Reference: Use `ReviewModal.tsx` pattern for modal implementation
- Estimated effort: 2-3 hours

### 2. Progress Style: Creative Visualization
**User Answer**: Sé creativo
**Analysis**:
- Current: Simple text-based status messages
- Recommendation: **Multi-layered progress visualization**
  - Phase timeline with icons (Discovery → Parsing → Validation → Saving)
  - Animated progress bar with phase indicators
  - Real-time metrics cards showing tokens/cost/entities
  - Color-coded phase states (pending/active/completed/failed)
  - Smooth animations between states
- Reference: Combine GlassCard styling with custom SVG timeline

### 3. Statistics Display Priority
**User Answer**: Revisa como está hecho actualmente en /chat
**Analysis**:
- Current display (MasterPlanProgressIndicator):
  - Phase status messages
  - Estimated duration
  - Bounded contexts, aggregates, entities count
  - Generation cost (when available)

**Proposed Priority Order**:
1. **Primary (always visible)**
   - Current phase with animated indicator
   - Progress percentage (0-100%)
   - Estimated time remaining

2. **Secondary (metrics panel)**
   - Tokens used / Estimated
   - Cost (USD)
   - Bounded contexts / Aggregates / Entities
   - Tasks / Phases generated

3. **Tertiary (expandable)**
   - Detailed breakdown by phase
   - Raw JSON data for debugging
   - Timestamps for each phase

### 4. Update Frequency
**User Answer**: Tiempo real
**Implementation**:
- Update on every WebSocket event (real-time)
- Backend sends: discovery_*, masterplan_* events
- Hook handles: useChat.ts processes events → state update → component re-render
- Current system: Socket.IO listeners already in place

### 5. Error Handling
**User Answer**: Todo
**Implementation**:
- **Display location**: Modal panel with error section
- **Error states**:
  - In-progress error: Show in progress panel, allow retry
  - Completion error: Show detailed error message + stack trace option
  - Network error: Show recovery UI

- **Retry mechanism**:
  - "Retry Generation" button
  - Reset state and re-trigger /masterplan command

- **Error sources**:
  - Column mismatches (now fixed)
  - Database connection errors
  - LLM API errors
  - WebSocket disconnection
  - Validation failures

### 6. Final Summary
**User Answer**: Todo
**Content**:
- ✅ Success indicator with checkmark animation
- 📊 Final statistics:
  - Total tokens used
  - Total cost (USD)
  - Duration (seconds)
  - Bounded contexts / Aggregates / Entities
  - Phases / Milestones / Tasks generated

- 🔍 Detailed breakdown:
  - List of phases with task counts
  - Architecture style detected
  - Tech stack extracted

- 🎯 Action buttons:
  - "Close" button
  - "View MasterPlan Details" (link to detailed view)
  - "Start Execution" (navigate to execution flow)
  - "Export" (future: PDF, JSON, etc.)

### 7. Mobile Responsiveness
**User Answer**: Desktop por ahora
**Implementation**: Desktop-first design, mobile support deferred to Phase 2

### 8. State Persistence
**User Answer**: Sí
**Implementation**:
- On page refresh during generation:
  - Fetch current MasterPlan status from backend API
  - Resume progress display with latest stats
  - No restart needed

- API endpoint needed:
  - GET `/api/v1/masterplans/{masterplan_id}/status`
  - Returns: current phase, progress %, stats

- Storage:
  - Cache masterplan_id in sessionStorage
  - Retrieve on component mount

### 9. Accessibility
**User Answer**: Sí
**Implementation**:
- Multi-language: English + Spanish
  - Phase labels (Discovery, Parsing, Validation, Saving)
  - Status messages
  - Error messages

- Screen reader support:
  - ARIA labels for progress bar
  - ARIA live region for status updates
  - Role="status" for dynamic updates

- Keyboard navigation:
  - Tab through action buttons
  - ESC to close modal
  - Focus management

### 10. Animations
**User Answer**: Suave
**Implementation**:
- Smooth transitions between phases
- Animated progress bar updates
- Fade in/out for statistics
- Success checkmark animation
- Use: Framer Motion or CSS transitions
- Duration: 300-500ms per transition

### 11. Dismissal
**User Answer**: Manual
**Implementation**:
- Close button (X) in top-right
- ESC key to close
- Click outside modal to close (optional)
- Panel persists until user closes or navigates away
- Inline header stays visible even if modal closed

### 12. Data Overflow
**User Answer**: Scroll
**Implementation**:
- Use vertical scroll for lists exceeding viewport
- Max height: calc(100vh - 300px)
- Smooth scroll behavior
- Scrollbar: styled to match design system

---

## WebSocket Events to Handle

| Event | Phase | Data | Display |
|-------|-------|------|---------|
| discovery_generation_start | Discovery | estimated_tokens, estimated_duration_seconds | Phase start |
| discovery_parsing_complete | Discovery | domain, total_bounded_contexts, aggregates, entities | Stats update |
| discovery_saving_start | Discovery | total_entities | Saving indicator |
| discovery_generation_complete | Discovery | discovery_id, cost, duration | Phase complete |
| masterplan_generation_start | MasterPlan | estimated_tokens, estimated_duration_seconds | Phase start |
| masterplan_parsing_complete | MasterPlan | total_phases, total_milestones, total_tasks | Stats update |
| masterplan_validation_start | MasterPlan | - | Validation indicator |
| masterplan_saving_start | MasterPlan | total_entities | Saving indicator |
| masterplan_generation_complete | MasterPlan | masterplan_id, all stats | Final summary |

---

## Design System Integration

**Existing Components to Reuse**:
- GlassCard: For statistics panels
- GlassButton: For action buttons
- ReviewModal: Modal pattern reference
- useChat hook: WebSocket event handling
- Socket.IO: Real-time communication

**New Components to Create**:
- MasterPlanProgressModal: Main modal component
- ProgressTimeline: Phase visualization
- ProgressMetrics: Statistics display
- PhaseIndicator: Individual phase card
- ErrorPanel: Error display with retry

---

## Implementation Priority

**Phase 1 (MVP)**:
1. Modal structure (ReviewModal pattern)
2. Phase timeline visualization
3. Real-time statistics display
4. Basic error handling

**Phase 2**:
1. State persistence on refresh
2. Accessibility (i18n + ARIA)
3. Advanced error states
4. Animations/polish

**Phase 3**:
1. Mobile responsiveness
2. Export functionality
3. Detailed view integration
4. Analytics tracking
