# Task Breakdown: MasterPlan Visibility Improvements

## Overview
Total Tasks: 28
Total Effort: 48 hours / 6 work days
Critical Path: Core Components → Integration → Error Handling → Testing
**Status**: Ready for Implementation

---

## Phase 1: MVP (Desktop-First) - Days 1-6

### Phase 1A: Foundation & Setup (Day 1 - 8 hours)

#### Task Group 1: Project Setup & Types
**Dependencies**: None
**Timeline**: Day 1 (4 hours)

- [ ] 1.1 Create TypeScript type definitions
  - **Effort**: 1.5 hours
  - **Description**: Define all interfaces needed for progress tracking
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/types/masterplan.ts` (new)
  - **Deliverable**:
    ```typescript
    // Include: ProgressState, PhaseStatus, ErrorInfo, EntityCounts, PhaseCounts
    interface ProgressState {
      tokensReceived: number;
      estimatedTotalTokens: number;
      percentage: number;
      currentPhase: string;
      phasesFound: number;
      milestonesFound: number;
      tasksFound: number;
      startTime: Date | null;
      elapsedSeconds: number;
      estimatedDurationSeconds: number;
      isParsing: boolean;
      isValidating: boolean;
      isSaving: boolean;
      isComplete: boolean;
      error?: ErrorInfo;
    }
    ```
  - **Acceptance Criteria**:
    - All types compile without errors
    - Matches WebSocket event data structures
    - No `any` types (strict TypeScript)

- [ ] 1.2 Create i18n infrastructure
  - **Effort**: 1.5 hours
  - **Description**: Set up localization for English and Spanish
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/i18n/en.json` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/i18n/es.json` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/i18n/useTranslation.ts` (new - if hook needed)
  - **Deliverable**:
    - Complete translation keys for all UI elements
    - Support for: phase labels, status messages, error messages, buttons
  - **Acceptance Criteria**:
    - Both language files have identical key structures
    - All component text has translation keys
    - Hook/context provides translations to components

- [ ] 1.3 Set up component directory structure
  - **Effort**: 1 hour
  - **Description**: Create directories and index files for new components
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/masterplan/` (new dir)
    - `index.ts` (exports all components)
  - **Deliverable**:
    - Directory ready for component development
    - Index file exporting all components
  - **Acceptance Criteria**:
    - All files compile without import errors

---

### Phase 1B: Core Components (Days 2-3 - 16 hours)

#### Task Group 2: Modal Infrastructure
**Dependencies**: Task Group 1
**Timeline**: Day 2 (8 hours)

- [ ] 2.1 Create MasterPlanProgressModal container
  - **Effort**: 3 hours
  - **Description**: Main modal component following ReviewModal.tsx pattern
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/MasterPlanProgressModal.tsx` (new)
  - **Spec Reference**: Section "Component Hierarchy" + "ReviewModal.tsx Pattern"
  - **Deliverable**:
    ```typescript
    interface MasterPlanProgressModalProps {
      event: MasterPlanProgressEvent | null;
      open: boolean;
      onClose: () => void;
      masterplanId?: string;
    }

    export function MasterPlanProgressModal(props: MasterPlanProgressModalProps) {
      // Render modal with backdrop, header, scrollable body, footer
    }
    ```
  - **Implementation Requirements**:
    - Fixed modal overlay with dark backdrop
    - Header with title + close button (X)
    - Scrollable body (max height: calc(100vh - 300px))
    - Footer with action buttons
    - ESC key closes modal
    - Click outside closes modal (optional)
    - Use GlassCard for consistent styling
  - **Acceptance Criteria**:
    - Modal renders without errors
    - Opens when `open={true}`
    - Closes on: X button, ESC key, backdrop click
    - Content scrollable when exceeds viewport
    - Focus trapped within modal
    - ARIA labels for accessibility

- [ ] 2.2 Create ProgressMetrics component
  - **Effort**: 2.5 hours
  - **Description**: Display primary, secondary, and tertiary statistics
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressMetrics.tsx` (new)
  - **Spec Reference**: Section "Real-time Metrics Cards"
  - **Deliverable**:
    ```typescript
    interface ProgressMetricsProps {
      tokensUsed: number;
      estimatedTokens: number;
      cost: number;
      duration: number;
      estimatedDuration: number;
      entities: EntityCounts;
      isComplete: boolean;
    }

    // Render three collapsible sections:
    // 1. Primary (always visible): phase, percentage, time remaining
    // 2. Secondary (collapsible): tokens, cost, entities, phases/milestones/tasks
    // 3. Tertiary (expandable): detailed breakdown, raw JSON
    ```
  - **Implementation Requirements**:
    - Grid layout for metrics cards
    - Primary metrics always visible
    - Secondary metrics collapsible (toggle)
    - Tertiary metrics expandable (JSON viewer)
    - Use GlassCard for each metric
    - Format numbers: tokens with commas, cost as USD
    - Time remaining calculation: estimated - elapsed
  - **Acceptance Criteria**:
    - All metrics render correctly
    - Collapsible sections toggle without errors
    - Numbers formatted properly
    - Responsive grid (desktop-first: 2-3 columns)

- [ ] 2.3 Create ProgressTimeline component
  - **Effort**: 2.5 hours
  - **Description**: Visualize 4 phases with status indicators
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressTimeline.tsx` (new)
  - **Spec Reference**: Section "Phase Timeline Visualization"
  - **Deliverable**:
    ```typescript
    interface ProgressTimelineProps {
      phases: PhaseStatus[];
      currentPhase: string;
      animateActive?: boolean;
    }

    // Render horizontal/vertical timeline with 4 phases:
    // Discovery → Parsing → Validation → Saving
    // Color-coded: Pending (gray), Active (blue animated), Completed (green), Failed (red)
    ```
  - **Implementation Requirements**:
    - 4-phase timeline: Discovery, Parsing, Validation, Saving
    - Status indicators: pending, in_progress, completed, failed
    - Icons for each phase
    - Color coding (pending: gray, active: blue with animation, complete: green, failed: red)
    - Duration display when phase complete
    - Animated entry/exit transitions
  - **Acceptance Criteria**:
    - All 4 phases render correctly
    - Status colors match spec
    - Animations smooth (300-500ms)
    - Duration displays for completed phases
    - Works desktop viewport

---

#### Task Group 3: Supporting Components
**Dependencies**: Task Group 1
**Timeline**: Day 3 (8 hours)

- [ ] 3.1 Create PhaseIndicator component
  - **Effort**: 2 hours
  - **Description**: Individual phase card with status and timing info
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/PhaseIndicator.tsx` (new)
  - **Spec Reference**: Section "Visual Design - Component Hierarchy"
  - **Deliverable**:
    ```typescript
    interface PhaseIndicatorProps {
      phase: PhaseStatus;
      isActive: boolean;
      showDuration?: boolean;
    }

    // Render single phase card with:
    // - Icon + phase name
    // - Status badge (pending/active/complete/failed)
    // - Duration (if showDuration=true)
    ```
  - **Acceptance Criteria**:
    - Renders phase information correctly
    - Status styling matches spec colors
    - Duration displays when provided
    - Animated active state

- [ ] 3.2 Create ErrorPanel component
  - **Effort**: 2 hours
  - **Description**: Display errors with diagnostics and retry mechanism
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ErrorPanel.tsx` (new)
  - **Spec Reference**: Section "Error Handling & Recovery"
  - **Deliverable**:
    ```typescript
    interface ErrorPanelProps {
      error: {
        message: string;
        code: string;
        details?: Record<string, any>;
        stackTrace?: string;
      };
      onRetry: () => void;
      isRetrying: boolean;
    }

    // Render error with:
    // - Error message and code
    // - Expandable details section
    // - Retry button
    // - Loading state while retrying
    ```
  - **Acceptance Criteria**:
    - Error message displays clearly
    - Details expandable/collapsible
    - Retry button triggers callback
    - Loading state shown during retry
    - Color scheme: red for error

- [ ] 3.3 Create FinalSummary component
  - **Effort**: 2 hours
  - **Description**: Completion screen with stats and action buttons
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/FinalSummary.tsx` (new)
  - **Spec Reference**: Section "Final Summary Screen"
  - **Deliverable**:
    ```typescript
    interface FinalSummaryProps {
      stats: {
        totalTokens: number;
        totalCost: number;
        totalDuration: number;
        entities: EntityCounts;
        phases: PhaseCounts;
      };
      architectureStyle?: string;
      techStack?: string[];
      onViewDetails: () => void;
      onStartExecution: () => void;
      onExport?: () => void;
    }

    // Render completion screen with:
    // - Success indicator (checkmark animation)
    // - Final statistics
    // - Detailed breakdown (phases, architecture, tech stack)
    // - Action buttons: Close, View Details, Start Execution, Export
    ```
  - **Implementation Requirements**:
    - Success checkmark animation
    - Display all statistics with proper formatting
    - Show phases with task counts
    - Architecture style and tech stack (if available)
    - GlassButton for actions
  - **Acceptance Criteria**:
    - All stats display correctly
    - Checkmark animation plays on mount
    - All action buttons render
    - Button clicks trigger callbacks

- [ ] 3.4 Create InlineProgressHeader component (refactor)
  - **Effort**: 2 hours
  - **Description**: Extract inline header from existing MasterPlanProgressIndicator
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/InlineProgressHeader.tsx` (new)
  - **Spec Reference**: Section "Inline Progress Header"
  - **Deliverable**:
    ```typescript
    interface InlineProgressHeaderProps {
      event: MasterPlanProgressEvent | null;
      onClick: () => void;
    }

    // Render compact header (50px height) with:
    // - Phase indicator (emoji + text)
    // - Progress bar (0-100%)
    // - Time remaining
    // - Click handler to open modal
    ```
  - **Implementation Requirements**:
    - Fixed height 50px
    - Inline in chat flow
    - Always visible (independent of modal)
    - Click opens detailed modal
    - Shows phase emoji + current phase text
    - Progress bar smooth width animation
    - Time remaining: "~{seconds}s remaining"
  - **Acceptance Criteria**:
    - Header renders with correct height
    - Progress bar updates smoothly
    - Click handler fires correctly
    - Time remaining calculates properly

---

### Phase 1C: State Management (Day 4 - 8 hours)

#### Task Group 4: Custom Hook & Integration
**Dependencies**: Task Group 2, Task Group 3
**Timeline**: Day 4 (8 hours)

- [ ] 4.1 Create useMasterPlanProgress custom hook
  - **Effort**: 3 hours
  - **Description**: Manage progress state from WebSocket events
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/hooks/useMasterPlanProgress.ts` (new)
  - **Spec Reference**: Section "Custom Hook: useMasterPlanProgress"
  - **Deliverable**:
    ```typescript
    export function useMasterPlanProgress(event: MasterPlanProgressEvent | null) {
      const [state, setState] = useState<ProgressState>(initialState);
      const [sessionId, setSessionId] = useState<string | null>(null);

      // Initialize from sessionStorage
      // Process incoming events
      // Calculate elapsed time with timer
      // Return state and sessionId
    }
    ```
  - **Implementation Requirements**:
    - Initialize from sessionStorage on mount
    - Update state from incoming WebSocket events
    - Calculate elapsed time with interval timer
    - Handle all event types from WebSocket
    - Cleanup timers on unmount
    - Calculate percentage based on tokens/estimated
  - **Key Events to Handle**:
    - `discovery_generation_start` → Start phase 1
    - `discovery_tokens_progress` → Update percentage, tokens
    - `discovery_parsing_complete` → Mark phase complete, update counts
    - `discovery_saving_start` → Show saving indicator
    - `discovery_generation_complete` → Complete phase 1
    - `masterplan_generation_start` → Start phase 2 (reset percentage to 50%)
    - `masterplan_tokens_progress` → Update percentage (50-92.5% range)
    - `masterplan_entity_discovered` → Increment counts
    - `masterplan_parsing_complete` → Mark parsing complete
    - `masterplan_validation_start` → Show validation phase
    - `masterplan_saving_start` → Show saving phase
    - `masterplan_generation_complete` → Mark complete (100%), store masterplan_id
  - **Acceptance Criteria**:
    - Hook compiles without errors
    - All event handlers fire correctly
    - State updates trigger re-renders
    - Timer cleans up properly
    - Types are strict (no `any`)

- [ ] 4.2 Wire components to useChat hook
  - **Effort**: 2 hours
  - **Description**: Connect components to existing masterPlanProgress state in useChat
  - **Files**:
    - Modify component integration points in parent component
    - Reference: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ChatWindow.tsx`
  - **Implementation Pattern**:
    ```typescript
    // In ChatWindow or similar parent:
    const { masterPlanProgress } = useChat();
    const [modalOpen, setModalOpen] = useState(false);

    return (
      <>
        {masterPlanProgress && (
          <InlineProgressHeader
            event={masterPlanProgress}
            onClick={() => setModalOpen(true)}
          />
        )}
        <MasterPlanProgressModal
          event={masterPlanProgress}
          open={modalOpen}
          onClose={() => setModalOpen(false)}
        />
      </>
    );
    ```
  - **Acceptance Criteria**:
    - Components receive state correctly
    - Modal open/close toggles properly
    - Events flow through to components
    - No prop drilling beyond necessary levels

- [ ] 4.3 Implement sessionStorage persistence
  - **Effort**: 2 hours
  - **Description**: Store/retrieve masterplan_id and progress state on page refresh
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/utils/masterplanStorage.ts` (new)
  - **Spec Reference**: Section "State Persistence on Refresh"
  - **Deliverable**:
    ```typescript
    // Store on generation start
    export function storeMasterPlanSession(data: {
      masterplan_id: string;
      started_at: string;
      current_phase: string;
      progress_percentage: number;
    }): void {}

    // Retrieve on mount
    export function getMasterPlanSession(): MasterPlanSession | null {}

    // Clear on completion/error
    export function clearMasterPlanSession(): void {}
    ```
  - **Schema**:
    ```json
    {
      "masterplan_id": "mp_xxx",
      "started_at": "2025-10-30T12:00:00Z",
      "current_phase": "parsing",
      "progress_percentage": 65,
      "_timestamp": 1730000000000
    }
    ```
  - **Session Validity**: 5-minute expiry
  - **Acceptance Criteria**:
    - Data stored correctly in sessionStorage
    - Data retrieved on page reload
    - Stale entries (>5min) cleared
    - No errors if sessionStorage unavailable

- [ ] 4.4 Create API integration for status recovery
  - **Effort**: 1 hour
  - **Description**: Fetch current generation status from backend API on refresh
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/api/masterplanClient.ts` (new)
  - **API Endpoint**:
    ```
    GET /api/v1/masterplans/{masterplan_id}/status
    ```
  - **Deliverable**:
    ```typescript
    export async function fetchMasterPlanStatus(
      masterplan_id: string
    ): Promise<MasterPlanStatusResponse> {
      const response = await fetch(
        `/api/v1/masterplans/${masterplan_id}/status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return response.json();
    }
    ```
  - **Integration in Hook**: Call this on mount if sessionStorage has masterplan_id
  - **Acceptance Criteria**:
    - API call succeeds during generation
    - Response parsed correctly
    - Handles 404 (masterplan not found)
    - Handles network errors gracefully

---

### Phase 1D: Error Handling & Edge Cases (Day 5 - 8 hours)

#### Task Group 5: Error Recovery & Validation
**Dependencies**: Task Group 4
**Timeline**: Day 5 (8 hours)

- [ ] 5.1 Implement error state handling in hook
  - **Effort**: 2 hours
  - **Description**: Track and expose errors from WebSocket events
  - **Files**:
    - Extend: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useMasterPlanProgress.ts`
  - **Implementation**:
    - Add `error` field to ProgressState
    - Listen for error events from WebSocket
    - Parse error details (message, code, stack trace)
    - Expose `onRetry` callback
  - **Error Types to Handle** (from spec):
    - Database connection errors
    - LLM API errors
    - WebSocket disconnection
    - Validation failures
    - Invalid column configurations
    - Rate limiting
  - **Acceptance Criteria**:
    - Error state captures correctly
    - Error details parsed properly
    - Error doesn't crash component
    - Retry callback accessible

- [ ] 5.2 Implement retry mechanism
  - **Effort**: 2 hours
  - **Description**: Re-trigger generation with reset state
  - **Files**:
    - Extend: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useMasterPlanProgress.ts`
    - Reference: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useChat.ts` (sendMessage)
  - **Deliverable**:
    ```typescript
    const handleRetry = async () => {
      // 1. Clear error state
      setError(null);
      setIsRetrying(true);

      // 2. Clear sessionStorage
      clearMasterPlanSession();

      // 3. Re-trigger masterplan command
      await sendMessage('/masterplan {project context}');
    };
    ```
  - **Integration with ErrorPanel**:
    - Pass `onRetry` callback to ErrorPanel
    - Show loading state while retrying
  - **Acceptance Criteria**:
    - Retry clears error state
    - Generation restarts successfully
    - sessionStorage cleared
    - Loading indicator shown

- [ ] 5.3 Add WebSocket reconnection handling
  - **Effort**: 2 hours
  - **Description**: Resume progress tracking on connection recovery
  - **Files**:
    - Extend: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useMasterPlanProgress.ts`
  - **Implementation**:
    - Detect WebSocket disconnection
    - Show reconnecting indicator
    - Fetch status from API endpoint
    - Resume progress display
    - Continue listening for events
  - **UX Flow**:
    - Show "Reconnecting..." message
    - Fetch latest status
    - Update UI with latest stats
    - Resume normal event listening
  - **Acceptance Criteria**:
    - Reconnection detected
    - Status fetched and updated
    - UI shows reconnection state
    - Progress continues tracking

- [ ] 5.4 Add validation for user experience
  - **Effort**: 2 hours
  - **Description**: Validate state transitions and data consistency
  - **Files**:
    - Extend: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useMasterPlanProgress.ts`
  - **Validations**:
    - Percentage stays 0-100%
    - Elapsed time <= estimated time (with tolerance)
    - Phase order: discovery → parsing → validation → saving
    - Token counts increase monotonically
    - Durations non-negative
  - **Error Handling**: Log warnings for inconsistent state, don't crash
  - **Acceptance Criteria**:
    - All validations working
    - Invalid states logged but handled
    - No crashes from bad data

---

### Phase 1E: Styling & Animations (Day 5 - 8 hours)

#### Task Group 6: Visual Polish & Animations
**Dependencies**: Task Group 2, Task Group 3
**Timeline**: Day 5 afternoon (concurrent with 5.1-5.4) (4 hours)

- [ ] 6.1 Add animations to progress components
  - **Effort**: 2 hours
  - **Description**: Implement smooth transitions between states
  - **Files**:
    - Update: all components created in Task Groups 2-3
    - Style file: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/masterplan/animations.css` (new)
  - **Animations Required**:
    - Progress bar width transition (300-500ms)
    - Phase status entry/exit (fade in/out)
    - Completed phase checkmark bounce (0.6s)
    - Success container scale animation (0.5s)
    - Statistics card fade in/out
  - **CSS Implementation**:
    ```css
    @keyframes slideIn {
      from { width: 0; opacity: 0; }
      to { width: 100%; opacity: 1; }
    }

    @keyframes checkBounce {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.2); }
    }

    @keyframes fadeInScale {
      from {
        opacity: 0;
        transform: scale(0.8);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }
    ```
  - **Respect prefers-reduced-motion**: Skip animations if enabled
  - **Acceptance Criteria**:
    - Animations smooth and performant (60fps)
    - Durations match spec (300-500ms)
    - Reduced motion respected
    - No jank or stuttering

- [ ] 6.2 Apply design system styling
  - **Effort**: 2 hours
  - **Description**: Use GlassCard, GlassButton, colors from design system
  - **Files**:
    - Update: all components in Task Groups 2-3
    - Reference:
      - `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/GlassCard.tsx`
      - `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/GlassButton.tsx`
  - **Styling Requirements**:
    - Primary colors: Purple/blue gradient
    - Success: Green (#10b981)
    - Error: Red (#ef4444)
    - Warning: Yellow (#f59e0b)
    - Neutral: Gray (#6b7280)
    - Background: Transparent with backdrop blur
    - Borders: White 10-30% opacity
    - Text: White with varying opacity
  - **Layout Requirements**:
    - Modal: 95% width with max-width 90vw
    - Metrics grid: 2-3 columns (desktop)
    - Proper spacing/padding
  - **Acceptance Criteria**:
    - Colors match design system
    - GlassCard/GlassButton used consistently
    - Layout responsive (desktop 1280px+)
    - Contrast ratios meet WCAG AA (4.5:1)

---

### Phase 1F: Accessibility & Localization (Day 6 - 8 hours)

#### Task Group 7: i18n & ARIA Implementation
**Dependencies**: Task Group 1, Task Groups 2-3
**Timeline**: Day 6 (8 hours)

- [ ] 7.1 Implement ARIA labels and roles
  - **Effort**: 2 hours
  - **Description**: Add accessibility attributes to all components
  - **Files**:
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/MasterPlanProgressModal.tsx`
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressMetrics.tsx`
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressTimeline.tsx`
    - Update: other components
  - **ARIA Requirements**:
    - Progress bar: `role="progressbar"` + `aria-valuenow` + `aria-valuemax`
    - Status updates: `aria-live="polite"` region
    - Modal: `role="dialog"` + `aria-modal="true"` + `aria-labelledby`
    - Phase updates: `role="status"`
    - Buttons: descriptive `aria-label`
    - Error panel: `aria-label="Generation Error"` + live region
  - **Implementation Example**:
    ```typescript
    <div
      role="progressbar"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Progress: ${percentage}% complete`}
    >
      {/* progress bar */}
    </div>
    ```
  - **Acceptance Criteria**:
    - All interactive elements have ARIA labels
    - Live regions for dynamic content
    - Roles match component function
    - No axe-core violations

- [ ] 7.2 Add keyboard navigation support
  - **Effort**: 1.5 hours
  - **Description**: Ensure keyboard-only usage possible
  - **Files**:
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/MasterPlanProgressModal.tsx`
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ErrorPanel.tsx`
    - Update: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/FinalSummary.tsx`
  - **Requirements**:
    - Tab navigation through all buttons/interactive elements
    - ESC key closes modal
    - Focus trap within modal (Tab/Shift+Tab)
    - Focus returned to trigger element on close
    - Visible focus indicators
  - **Implementation Pattern**:
    ```typescript
    useEffect(() => {
      const handleEscKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };

      if (open) {
        document.addEventListener('keydown', handleEscKey);
        // Set focus to modal
      }

      return () => {
        document.removeEventListener('keydown', handleEscKey);
      };
    }, [open, onClose]);
    ```
  - **Acceptance Criteria**:
    - Tab navigation works in logical order
    - ESC closes modal
    - Focus indicators visible
    - All buttons accessible via keyboard

- [ ] 7.3 Integrate translations into components
  - **Effort**: 2 hours
  - **Description**: Replace hardcoded text with translation keys
  - **Files**:
    - Update: all components in Task Groups 2-3
    - Reference: `/home/kwar/code/agentic-ai/src/ui/src/i18n/en.json` + `es.json`
  - **Implementation Pattern**:
    ```typescript
    import { useTranslation } from '../i18n/useTranslation';

    export function Component() {
      const t = useTranslation();
      return <h2>{t('masterplan.phase.discovery')}</h2>;
    }
    ```
  - **Translation Keys to Use**:
    - `masterplan.phase.discovery` → "Analyzing DDD Requirements"
    - `masterplan.phase.parsing` → "Generating Plan Structure"
    - `masterplan.phase.validation` → "Validating Dependencies"
    - `masterplan.phase.saving` → "Saving to Database"
    - `masterplan.status.generating` → "Generating MasterPlan"
    - `masterplan.status.complete` → "MasterPlan Generated"
    - `masterplan.buttons.close` → "Close"
    - `masterplan.buttons.viewDetails` → "View MasterPlan Details"
    - `masterplan.buttons.startExecution` → "Start Execution"
    - `masterplan.buttons.retry` → "Retry Generation"
    - And more (see spec section "Localization Implementation")
  - **Acceptance Criteria**:
    - All text uses translation keys
    - Both EN and ES translations present
    - Components render correct language based on locale
    - No hardcoded English strings

- [ ] 7.4 Test accessibility compliance
  - **Effort**: 2.5 hours
  - **Description**: Validate WCAG 2.1 AA compliance
  - **Files**:
    - Create test file: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/accessibility.test.tsx`
  - **Tests to Include**:
    - axe-core automated accessibility check
    - Color contrast validation (4.5:1 minimum)
    - Keyboard navigation paths
    - ARIA labels presence
    - Focus management
    - Screen reader text verification
  - **Manual Testing Checklist**:
    - Test with NVDA (Windows) or VoiceOver (Mac)
    - Verify all content announced correctly
    - Test all keyboard paths
    - Verify color contrast in browser DevTools
  - **Acceptance Criteria**:
    - Zero axe-core violations
    - All contrast ratios meet WCAG AA
    - Keyboard navigation works completely
    - Screen reader announces all content

- [ ] 7.5 Test localization in both languages
  - **Effort**: 1 hour
  - **Description**: Verify Spanish and English text displays correctly
  - **Files**:
    - Manual testing in UI
  - **Testing Steps**:
    - Change locale to Spanish
    - Verify all text in Spanish
    - Check text doesn't overflow UI
    - Verify numbers format correctly in both locales
    - Test with RTL considerations (if applicable)
  - **Acceptance Criteria**:
    - All text displays in correct language
    - No untranslated strings visible
    - Text doesn't overflow
    - Numbers/currencies format properly

---

### Phase 1G: Testing & Documentation (Day 6 - 8 hours)

#### Task Group 8: Unit Tests & Integration Tests
**Dependencies**: All previous task groups
**Timeline**: Day 6 (8 hours)

- [ ] 8.1 Write unit tests for components
  - **Effort**: 3 hours
  - **Description**: Test individual component behavior
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/MasterPlanProgressModal.test.tsx` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/ProgressMetrics.test.tsx` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/ProgressTimeline.test.tsx` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/ErrorPanel.test.tsx` (new)
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/FinalSummary.test.tsx` (new)
  - **Test Coverage Targets**:
    - ProgressMetrics: Rendering, calculations, collapsible sections
    - ProgressTimeline: Phase rendering, status styling, animations
    - ErrorPanel: Error display, retry callback, loading state
    - FinalSummary: Stats display, button clicks, animations
    - MasterPlanProgressModal: Open/close, ESC key, backdrop click
  - **Example Tests** (from spec):
    ```typescript
    describe('MasterPlanProgressModal', () => {
      it('should render modal when open prop is true', () => {
        render(<MasterPlanProgressModal open={true} event={mockEvent} />);
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      it('should close on ESC key', () => {
        const onClose = jest.fn();
        render(<MasterPlanProgressModal open={true} onClose={onClose} />);
        fireEvent.keyDown(document, { key: 'Escape' });
        expect(onClose).toHaveBeenCalled();
      });

      it('should display error panel when error occurs', () => {
        const errorEvent = { event: 'error', data: { message: 'Failed' } };
        render(<MasterPlanProgressModal open={true} event={errorEvent} />);
        expect(screen.getByText(/Failed/i)).toBeInTheDocument();
      });
    });
    ```
  - **Coverage Target**: >80% line coverage
  - **Acceptance Criteria**:
    - All components have unit tests
    - Coverage >80%
    - All tests passing
    - Mocks for WebSocket/API calls

- [ ] 8.2 Write hook tests
  - **Effort**: 2 hours
  - **Description**: Test custom useMasterPlanProgress hook
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/hooks/__tests__/useMasterPlanProgress.test.ts` (new)
  - **Tests to Include**:
    - Event processing (all WebSocket events)
    - State updates trigger correctly
    - Elapsed time calculation
    - sessionStorage persistence
    - Error handling
    - Retry mechanism
  - **Test Cases**:
    - Event stream: discovery_start → parsing_complete → masterplan_start → complete
    - Percentage calculation: correct 0-100% mapping
    - Session storage: store/retrieve/clear
    - Status recovery: API fetch and restore state
    - Error scenarios: error → retry → success
  - **Acceptance Criteria**:
    - All events processed correctly
    - State calculations accurate
    - Timer cleans up properly
    - Error scenarios handled

- [ ] 8.3 Write integration tests
  - **Effort**: 2 hours
  - **Description**: Test component interaction and event flow
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/integration.test.tsx` (new)
  - **Test Scenarios**:
    - Modal open/close independent of inline header
    - Inline header always visible during generation
    - Event flow: mock event → hook update → component render
    - Modal closes on ESC while header remains
    - Error state shows in modal, inline header shows retry
    - Session recovery on page refresh
    - Keyboard navigation through modal
  - **Acceptance Criteria**:
    - All integration scenarios pass
    - Event flow works end-to-end
    - Component interactions correct

- [ ] 8.4 Create documentation
  - **Effort**: 1 hour
  - **Description**: Document components and patterns
  - **Files**:
    - `/home/kwar/code/agentic-ai/src/ui/src/components/chat/masterplan/README.md` (new)
  - **Documentation Content**:
    - Component overview and architecture
    - Usage examples for each component
    - Props interface documentation
    - WebSocket event handling explanation
    - Translation key reference
    - Customization guide
    - Known limitations
  - **Example Structure**:
    ```markdown
    # MasterPlan Progress Components

    ## Overview
    Components for displaying real-time MasterPlan generation progress.

    ## Architecture
    [Diagram of component hierarchy]

    ## Components
    - MasterPlanProgressModal
    - ProgressMetrics
    - ProgressTimeline
    - ErrorPanel
    - FinalSummary

    ## Usage Example
    ```typescript
    <MasterPlanProgressModal
      event={masterPlanProgress}
      open={isOpen}
      onClose={handleClose}
    />
    ```

    ## WebSocket Events
    [Event reference table]

    ## Translation Keys
    [i18n key reference]
    ```
  - **Acceptance Criteria**:
    - All components documented
    - Usage examples complete
    - Props documented
    - Searchable for developers

- [ ] 8.5 Run full test suite and fix issues
  - **Effort**: 1 hour
  - **Description**: Execute all tests and resolve failures
  - **Files**:
    - All test files from 8.1-8.3
  - **Test Execution**:
    ```bash
    npm test -- --coverage
    # Target: >80% coverage
    ```
  - **Checks**:
    - All unit tests passing
    - All integration tests passing
    - Coverage >80%
    - No TypeScript errors
    - No console warnings/errors
  - **Acceptance Criteria**:
    - All tests passing
    - Coverage >80%
    - No lint errors
    - TypeScript strict mode compliance

---

## Phase 2: Enhancements (Deferred - Post MVP)

### Task Group 9: Advanced Features (Not in MVP)
**Status**: Deferred to Phase 2
**Estimated Effort**: 12-16 hours

These tasks are explicitly OUT OF SCOPE for MVP but documented for future reference:

- [ ] 9.1 Mobile responsiveness
  - Full responsive design (tablet/mobile)
  - Touch-friendly interactions
  - Single-column layout for mobile
  - Full-width modal on small screens
  - Estimated: 3-4 days

- [ ] 9.2 Export functionality
  - PDF export
  - JSON export
  - CSV export (partial)
  - Email sharing
  - Estimated: 2-3 days

- [ ] 9.3 Advanced visualization
  - Architecture diagram rendering
  - Dependency graph visualization
  - Timeline chart
  - Statistics dashboard
  - Estimated: 3-4 days

- [ ] 9.4 Performance optimization
  - Virtual scrolling for long lists
  - Debouncing state updates
  - Memory optimization for long generations
  - Network optimization
  - Estimated: 1-2 days

- [ ] 9.5 Analytics integration
  - Track generation completion rate
  - Monitor performance metrics
  - User behavior tracking
  - Cost analytics
  - Estimated: 1-2 days

---

## Summary: Task Organization & Dependencies

### Critical Path (Blocking Order)
```
Day 1: Setup (1.1 + 1.2 + 1.3)
  ↓
Days 2-3: Core Components (2.1 + 2.2 + 2.3 + 3.1 + 3.2 + 3.3 + 3.4)
  ↓
Day 4: Integration & State (4.1 + 4.2 + 4.3 + 4.4)
  ↓
Day 5: Error Handling (5.1 + 5.2 + 5.3 + 5.4) + Animations (6.1 + 6.2)
  ↓
Day 6: Accessibility (7.1 + 7.2 + 7.3 + 7.4 + 7.5) + Testing (8.1 + 8.2 + 8.3 + 8.4 + 8.5)
```

### Parallel Opportunities
- **Day 5**: Error Handling (Tasks 5.1-5.4) can run in parallel with Animations (Tasks 6.1-6.2)
- **Day 6**: Accessibility (Tasks 7.1-7.5) can run in parallel with Testing (Tasks 8.1-8.5)

### Team Distribution (If Parallel)
- **Frontend Engineer 1**: Tasks 2.1-2.3, 4.1-4.4 (Core Components + Integration)
- **Frontend Engineer 2**: Tasks 3.1-3.4, 5.1-5.4 (Supporting Components + Error Handling)
- **UI/Animation Specialist**: Tasks 6.1-6.2 (Animations + Styling)
- **QA/Accessibility**: Tasks 7.1-7.5, 8.1-8.5 (Accessibility + Testing)

### Effort Breakdown
| Phase | Component | Effort | Percentage |
|-------|-----------|--------|------------|
| Setup | Foundation | 4 h | 8% |
| Components | Core UI | 16 h | 33% |
| Integration | State & Hooks | 8 h | 17% |
| Error Handling | Resilience | 8 h | 17% |
| Polish | Animations & Styling | 4 h | 8% |
| Accessibility | i18n & ARIA | 8 h | 17% |
| **Total** | **MVP** | **48 h** | **100%** |

---

## Success Metrics

### Functional Success
- ✅ Real-time updates <100ms latency
- ✅ All 12 WebSocket events handled
- ✅ Page refresh recovers state <2 seconds
- ✅ Inline header visible during generation
- ✅ Modal open/close <200ms

### Performance Success
- ✅ 60fps animations
- ✅ Memory stable during 10+ minute generations
- ✅ No unnecessary re-renders

### Code Quality
- ✅ TypeScript strict mode compliance
- ✅ Test coverage >80%
- ✅ All components <300 lines
- ✅ Zero console errors in normal operation

### Accessibility
- ✅ WCAG 2.1 AA compliance
- ✅ Zero axe-core violations
- ✅ Works with screen readers
- ✅ Keyboard navigation complete

### Localization
- ✅ English and Spanish fully translated
- ✅ No hardcoded English strings

---

## File Structure (Post-Implementation)
```
src/ui/src/
├── components/chat/
│   ├── MasterPlanProgressModal.tsx
│   ├── InlineProgressHeader.tsx
│   ├── ProgressTimeline.tsx
│   ├── ProgressMetrics.tsx
│   ├── PhaseIndicator.tsx
│   ├── ErrorPanel.tsx
│   ├── FinalSummary.tsx
│   ├── masterplan/
│   │   ├── animations.css
│   │   ├── index.ts
│   │   └── README.md
│   └── __tests__/
│       ├── MasterPlanProgressModal.test.tsx
│       ├── ProgressMetrics.test.tsx
│       ├── ProgressTimeline.test.tsx
│       ├── ErrorPanel.test.tsx
│       ├── FinalSummary.test.tsx
│       ├── integration.test.tsx
│       └── accessibility.test.tsx
├── hooks/
│   ├── useMasterPlanProgress.ts
│   └── __tests__/
│       └── useMasterPlanProgress.test.ts
├── types/
│   └── masterplan.ts
├── api/
│   └── masterplanClient.ts
├── utils/
│   └── masterplanStorage.ts
└── i18n/
    ├── useTranslation.ts
    ├── en.json
    └── es.json
```

---

## Notes for Implementation

### Key Patterns to Follow
1. **Components**: Keep <300 lines, single responsibility
2. **State**: Use hook pattern, no Redux for this feature
3. **Styling**: GlassCard/GlassButton + Tailwind + custom CSS for animations
4. **Testing**: TDD preferred - test file for each component
5. **i18n**: Use translation keys, never hardcode text
6. **Accessibility**: ARIA first, test with axe-core

### Browser Support
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari 14+
- Not supporting IE11 or mobile browsers in Phase 1

### Build Artifacts
- Bundle size impact: ~15-20KB gzipped (estimate)
- No new external dependencies beyond existing stack
- Animations use CSS only (no Framer Motion required)

### Future Considerations
- **Phase 2**: Mobile responsiveness, export, advanced visualizations
- **Phase 3**: Analytics, performance dashboard, scheduled generation
- **Technical Debt**: Evaluate Context API if prop drilling becomes excessive

---

**Document Status**: Ready for Development
**Last Updated**: 2025-10-30
**Specification Version**: 1.0

