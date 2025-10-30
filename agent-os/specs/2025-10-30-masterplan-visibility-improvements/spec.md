# Specification: MasterPlan Visibility Improvements

## Executive Summary

This specification details the implementation of enhanced visibility and real-time progress tracking for MasterPlan generation. The feature implements a hybrid modal + inline indicator approach that provides comprehensive progress visualization, detailed statistics, error handling, and state persistence during MasterPlan generation workflows. The solution leverages existing WebSocket event infrastructure and design system components while adding sophisticated visualization capabilities.

---

## Feature Overview

### Core Objectives

1. **Real-time Progress Visualization** - Display live updates during Discovery and MasterPlan generation phases
2. **Comprehensive Statistics Display** - Show tokens used, cost, entity counts, timing, and detailed breakdowns
3. **Multi-level Information Architecture** - Primary (always visible), Secondary (metrics), Tertiary (expandable/debugging)
4. **Hybrid UI Approach** - Compact inline header + full-featured modal for detailed analysis
5. **Robust Error Handling** - Display errors with retry capabilities and detailed diagnostics
6. **State Persistence** - Resume progress tracking on page refresh during generation
7. **Accessibility & Localization** - English and Spanish support with ARIA labels and keyboard navigation
8. **Smooth Animations** - 300-500ms transitions between states for professional polish

---

## User Stories

- As a user, I want to see real-time progress updates while my MasterPlan is generating so I understand what phase the system is in
- As a user, I want to view detailed statistics (tokens, cost, entities) without disrupting my chat flow, so I can use the modal for in-depth analysis
- As a user, I want the progress indicator to remain visible inline even if I close the modal, so I can keep track of progress
- As a user, I want the system to resume progress tracking if I refresh the page during generation, so I don't lose context
- As a user, I want clear error messages and retry options if something fails, so I can recover gracefully
- As a user, I want to see a final summary with all metrics when generation completes, so I can review what was created
- As a user, I want keyboard shortcuts (ESC to close) and screen reader support, so the interface is accessible
- As a user, I want smooth animations that clearly show state transitions, so the interface feels responsive

---

## Core Requirements

### Functional Requirements

#### 1. Inline Progress Header
- Display compact progress indicator (50px height) inline in chat messages
- Show current phase with emoji indicator
- Display progress percentage (0-100%)
- Show estimated time remaining
- Always visible, independent of modal state
- Update in real-time on every WebSocket event
- Click to open detailed modal

#### 2. Progress Modal
- Full-featured modal for detailed progress analysis
- Implement using ReviewModal.tsx pattern for consistency
- Support both desktop and mobile (desktop-first in Phase 1)
- Header: Title + close button (X)
- Escapable via ESC key
- Closable by clicking outside (optional)
- Scrollable content for lists exceeding viewport
- Max height: calc(100vh - 300px)

#### 3. Phase Timeline Visualization
- Multi-phase display with visual indicators
- Phases: Discovery → Parsing → Validation → Saving
- Color-coded states:
  - Pending: Gray/inactive
  - Active: Animated blue/purple gradient
  - Completed: Green checkmark
  - Failed: Red error indicator
- Show phase-specific icons
- Display phase duration when complete

#### 4. Real-time Metrics Cards
- Primary metrics (always visible):
  - Current phase with animated indicator
  - Progress percentage (0-100%)
  - Estimated time remaining
  - Elapsed time

- Secondary metrics (collapsible panel):
  - Tokens used / Estimated total
  - Generation cost (USD)
  - Bounded contexts count
  - Aggregates count
  - Entities count
  - Tasks/Phases/Milestones generated

- Tertiary metrics (expandable section):
  - Detailed breakdown by phase
  - Raw JSON data (debugging)
  - Timestamps for each phase transition

#### 5. Error Handling & Recovery
- **Error Display Location**: Dedicated error panel in modal
- **In-Progress Errors**: Show in progress panel, allow retry
- **Completion Errors**: Show detailed message + optional stack trace
- **Network Errors**: Show recovery UI with reconnection indicators
- **Error Sources to Handle**:
  - Database connection errors
  - LLM API errors
  - WebSocket disconnection
  - Validation failures
  - Invalid column configurations
  - Rate limiting

- **Recovery Mechanism**:
  - "Retry Generation" button resets state and re-triggers /masterplan command
  - Clear error display when retry begins
  - Show connection status for network errors

#### 6. Final Summary Screen
- Success indicator with checkmark animation
- Final statistics:
  - Total tokens used
  - Total generation cost (USD)
  - Total duration (seconds)
  - Bounded contexts / Aggregates / Entities
  - Phases / Milestones / Tasks generated
- Detailed breakdown:
  - List of phases with task counts
  - Architecture style detected (if available)
  - Tech stack extracted (if available)
- Action buttons:
  - "Close" - dismiss panel
  - "View MasterPlan Details" - navigate to detailed view
  - "Start Execution" - navigate to execution flow
  - "Export" - prepare for future export functionality

#### 7. State Persistence on Refresh
- On page refresh during generation:
  - Fetch current MasterPlan status from backend API
  - Resume progress display with latest stats
  - No restart of generation needed
  - Restore WebSocket connection and continue listening
- Store `masterplan_id` in sessionStorage for session-scoped persistence
- Retrieve and validate on component mount
- Clear sessionStorage on generation completion or error

#### 8. Localization (i18n)
- Support English and Spanish
- Phase labels: Discovery, Parsing, Validation, Saving
- Status messages: "Analyzing DDD Requirements", "Generating Plan Structure", etc.
- Error messages with appropriate translations
- Time remaining format: "~{seconds}s remaining" / "~{seconds}s restante"

#### 9. Accessibility
- **ARIA Labels**:
  - aria-label for progress bar showing percentage
  - aria-live="polite" for real-time updates
  - role="progressbar" on main progress element
  - role="status" for phase updates

- **Keyboard Navigation**:
  - Tab through action buttons
  - ESC to close modal
  - Focus management on modal open/close
  - Focus trap within modal

- **Screen Reader Support**:
  - Semantic HTML structure
  - Descriptive labels for interactive elements
  - Status updates announced as regions update

#### 10. Animations
- **Transitions**: 300-500ms per state change
- **Progress Bar**: Smooth width transition on percentage update
- **Phase Indicators**: Animated entry/completion
- **Success Checkmark**: Bounce animation on completion
- **Statistics**: Fade in/out transitions
- **Implementation**: Use Framer Motion or CSS transitions
- **Disable for reduced motion**: Respect prefers-reduced-motion preference

---

## Visual Design

### Component Hierarchy

```
MasterPlanProgressContainer
├── InlineProgressHeader
│   ├── PhaseIndicator (animated)
│   ├── ProgressBar (animated)
│   └── TimeRemaining
└── MasterPlanProgressModal
    ├── ModalHeader
    │   ├── Title
    │   └── CloseButton
    ├── ModalBody (scrollable)
    │   ├── ProgressMetrics
    │   │   ├── PrimaryStats
    │   │   │   ├── PhaseStatus
    │   │   │   ├── ProgressPercentage
    │   │   │   └── TimeRemaining
    │   │   ├── SecondaryMetrics (collapsible)
    │   │   │   ├── TokensCard
    │   │   │   ├── CostCard
    │   │   │   └── EntitiesCard
    │   │   └── TertiaryMetrics (expandable)
    │   │       ├── PhaseBreakdown
    │   │       └── RawJSON
    │   ├── ProgressTimeline
    │   │   ├── PhaseCard (Discovery)
    │   │   ├── PhaseCard (Parsing)
    │   │   ├── PhaseCard (Validation)
    │   │   └── PhaseCard (Saving)
    │   ├── ErrorPanel (conditional)
    │   │   ├── ErrorMessage
    │   │   ├── ErrorDetails
    │   │   └── RetryButton
    │   └── FinalSummary (conditional)
    │       ├── SuccessIndicator
    │       ├── FinalStats
    │       ├── DetailedBreakdown
    │       └── ActionButtons
    └── ModalFooter
        └── ActionButtons

```

### UI Element References

**Existing Components to Reuse**:
- `GlassCard`: Background and card styling for metrics panels
- `GlassButton`: Action buttons (Close, Retry, View Details, Start Execution, Export)
- `ReviewModal`: Modal pattern and structure
- `EntityCounter`: Entity display pattern (reusable component reference)
- `StatusItem`: Phase status display pattern

**Design System Files**:
- `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/GlassCard.tsx`
- `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/GlassButton.tsx`
- `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/PageHeader.tsx`

### Color Scheme

- **Primary**: Purple/Blue gradient (existing design system)
- **Success**: Green (#10b981)
- **Error**: Red (#ef4444)
- **Warning**: Yellow/Orange (#f59e0b)
- **Neutral**: Gray (#6b7280)
- **Background**: Transparent with backdrop blur
- **Border**: White/10-30% opacity
- **Text**: White with varying opacity

### Responsive Design

**Desktop (Phase 1)** - Primary focus:
- Modal width: 95% with max-width 90vw
- Metrics grid: 2-3 columns
- Timeline: Horizontal or vertical

**Tablet/Mobile (Phase 2)**:
- Modal: Full width with padding
- Metrics: Single column
- Timeline: Vertical stack
- Touch-friendly button sizing

---

## Reusable Components

### Existing Code to Leverage

#### 1. MasterPlanProgressIndicator.tsx
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/MasterPlanProgressIndicator.tsx`

**Current Functionality**:
- Handles all MasterPlan WebSocket events
- State management for progress tracking
- Phase status indicators
- Entity counter display
- Token/time tracking

**Reuse Strategy**:
- Extract pure logic into custom hooks (useProgressState, usePhaseTracking)
- Create smaller, composable components
- Maintain existing event handling pattern
- Refactor rendering into separate UI components

#### 2. ReviewModal.tsx Pattern
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/review/ReviewModal.tsx`

**Pattern Elements**:
- Fixed modal overlay with backdrop
- Escapable with keyboard listener
- Header with close button
- Scrollable body content
- Footer with action buttons
- Use of GlassCard for consistent styling

**Reuse Strategy**:
- Use exact same modal structure
- Adapt header/footer for MasterPlan context
- Implement same keyboard/backdrop close handlers

#### 3. useChat Hook
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/hooks/useChat.ts`

**Event Handling Pattern**:
- WebSocket event listeners for all progress events
- Master state management for `masterPlanProgress`
- Cleanup functions for proper unmounting
- Real-time state updates

**Reuse Strategy**:
- Continue using existing masterPlanProgress state
- Leverage established event listener pattern
- No changes needed to hook itself
- Components consume `masterPlanProgress` prop

#### 4. GlassCard & GlassButton
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/design-system/`

**Styling Pattern**:
- Consistent glass-morphism design
- Backdrop blur effects
- Border and shadow treatments
- Color variants

**Reuse Strategy**:
- Use GlassCard for all metric panels and cards
- Use GlassButton for action buttons with variants

### New Components Required

#### 1. MasterPlanProgressModal
**Purpose**: Main modal container for detailed progress view
**Why New**: Need full modal implementation for MasterPlan-specific context
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/MasterPlanProgressModal.tsx`

**Props Interface**:
```typescript
interface MasterPlanProgressModalProps {
  event: MasterPlanProgressEvent | null;
  open: boolean;
  onClose: () => void;
  masterplanId?: string;
}
```

#### 2. ProgressTimeline
**Purpose**: Visualize phases in sequential order with status indicators
**Why New**: Multi-phase timeline visualization not available in existing code
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressTimeline.tsx`

**Props Interface**:
```typescript
interface ProgressTimelineProps {
  phases: PhaseStatus[];
  currentPhase: string;
  animateActive?: boolean;
}

interface PhaseStatus {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: number;
  startTime?: Date;
  endTime?: Date;
  icon: string;
}
```

#### 3. ProgressMetrics
**Purpose**: Display primary, secondary, and tertiary metrics
**Why New**: Complex metrics panel with collapsible sections needed
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ProgressMetrics.tsx`

**Props Interface**:
```typescript
interface ProgressMetricsProps {
  tokensUsed: number;
  estimatedTokens: number;
  cost: number;
  duration: number;
  estimatedDuration: number;
  entities: {
    boundedContexts: number;
    aggregates: number;
    entities: number;
    phases: number;
    milestones: number;
    tasks: number;
  };
  isComplete: boolean;
}
```

#### 4. PhaseIndicator
**Purpose**: Individual phase card with status and timing
**Why New**: Custom phase card component for timeline
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/PhaseIndicator.tsx`

**Props Interface**:
```typescript
interface PhaseIndicatorProps {
  phase: PhaseStatus;
  isActive: boolean;
  showDuration?: boolean;
}
```

#### 5. ErrorPanel
**Purpose**: Display errors with diagnostics and retry mechanism
**Why New**: MasterPlan-specific error handling and recovery UI
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/ErrorPanel.tsx`

**Props Interface**:
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
```

#### 6. FinalSummary
**Purpose**: Completion screen with success indicator and action buttons
**Why New**: Specialized completion view for MasterPlan generation
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/components/chat/FinalSummary.tsx`

**Props Interface**:
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
```

---

## Technical Approach

### Architecture Overview

#### State Management Strategy
- Use existing `useChat` hook's `masterPlanProgress` state
- No Redux/Context needed - prop drilling acceptable for component depth
- sessionStorage for masterplan_id persistence
- Local component state for UI toggles (modal open/close, expandable sections)

#### Event Flow
```
WebSocket Server
    ↓
useChat Hook (event listeners)
    ↓
masterPlanProgress state update
    ↓
Parent Component receives state
    ↓
MasterPlanProgressModal (detailed view)
├── Inline Header (always visible)
├── Modal Components (conditional rendering)
└── Error Panel (error conditional)
```

#### Styling Strategy
- Tailwind CSS for responsive design
- Custom animations via CSS keyframes or Framer Motion
- Design system components for consistency
- Glass-morphism effects for modern aesthetic
- Gradients for visual interest

#### WebSocket Integration
No changes needed - existing event handlers in `useChat.ts` already provide:
- `discovery_generation_start` → Start timer, set phase
- `discovery_tokens_progress` → Update percentage
- `discovery_parsing_complete` → Mark discovery complete
- `discovery_generation_complete` → Transition to MasterPlan
- `masterplan_generation_start` → Start MasterPlan phase
- `masterplan_tokens_progress` → Update percentage
- `masterplan_entity_discovered` → Increment entity counts
- `masterplan_parsing_complete` → Mark parsing complete
- `masterplan_validation_start` → Show validation phase
- `masterplan_saving_start` → Show saving phase
- `masterplan_generation_complete` → Show completion summary

### Data Persistence

#### sessionStorage Schema
```typescript
// Store during generation
sessionStorage.setItem('masterplan_session', JSON.stringify({
  masterplan_id: string;
  started_at: ISO8601 timestamp;
  current_phase: string;
  progress_percentage: number;
}));

// Retrieve and validate on mount
if (sessionStorage.getItem('masterplan_session')) {
  // Fetch status from API
  GET /api/v1/masterplans/{masterplan_id}/status

  // Resume progress display with latest stats
  // Continue listening for WebSocket events
}

// Clear on completion
sessionStorage.removeItem('masterplan_session');
```

#### API Endpoint for Status Recovery
**Endpoint**: `GET /api/v1/masterplans/{masterplan_id}/status`
**Location**: `/home/kwar/code/agentic-ai/src/api/routers/masterplans.py`

**Response Schema**:
```json
{
  "masterplan_id": "mp_xxx",
  "current_phase": "parsing",
  "progress_percentage": 65,
  "started_at": "2025-10-30T12:00:00Z",
  "stats": {
    "tokens_used": 8500,
    "estimated_tokens": 17000,
    "cost": 0.25,
    "duration_seconds": 120,
    "entities": {
      "bounded_contexts": 5,
      "aggregates": 12,
      "entities": 45,
      "phases": 3,
      "milestones": 17,
      "tasks": 120
    }
  },
  "is_complete": false,
  "is_error": false
}
```

### Localization Implementation

#### i18n File Structure
**Location**: `/home/kwar/code/agentic-ai/src/ui/src/i18n/` (create if needed)

```typescript
// en.json
{
  "masterplan": {
    "phase": {
      "discovery": "Analyzing DDD Requirements",
      "parsing": "Generating Plan Structure",
      "validation": "Validating Dependencies",
      "saving": "Saving to Database"
    },
    "status": {
      "generating": "Generating MasterPlan",
      "complete": "MasterPlan Generated",
      "timeRemaining": "{seconds}s remaining",
      "elapsedTime": "{seconds}s"
    },
    "metrics": {
      "tokens": "Tokens Used",
      "cost": "Generation Cost",
      "boundedContexts": "Bounded Contexts",
      "aggregates": "Aggregates",
      "entities": "Entities",
      "phases": "Phases",
      "milestones": "Milestones",
      "tasks": "Tasks"
    },
    "buttons": {
      "close": "Close",
      "viewDetails": "View MasterPlan Details",
      "startExecution": "Start Execution",
      "export": "Export",
      "retry": "Retry Generation"
    },
    "errors": {
      "failed": "Generation Failed",
      "retry": "Retrying..."
    }
  }
}

// es.json
{
  "masterplan": {
    "phase": {
      "discovery": "Analizando Requisitos DDD",
      "parsing": "Generando Estructura del Plan",
      "validation": "Validando Dependencias",
      "saving": "Guardando en Base de Datos"
    },
    // ... etc
  }
}
```

### Animations Implementation

#### Progress Bar Animation
```css
@keyframes slideIn {
  from { width: 0; }
  to { width: var(--progress-width); }
}

.progress-bar {
  animation: slideIn 0.7s ease-out;
  transition: width 0.3s ease-out;
}
```

#### Phase Completion Checkmark
```css
@keyframes checkBounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

.checkmark {
  animation: checkBounce 0.6s ease-out;
}
```

#### Success Celebration
```css
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

.completion-card {
  animation: fadeInScale 0.5s ease-out;
}
```

---

## Component Integration Points

### Parent Component Integration

```typescript
// In ChatWindow.tsx or similar
import { MasterPlanProgressModal } from './MasterPlanProgressModal';
import { useChat } from '../hooks/useChat';

export function ChatWindow() {
  const { masterPlanProgress } = useChat();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <MessageList messages={messages} />

      {/* Inline header always visible */}
      {masterPlanProgress && (
        <InlineProgressHeader
          event={masterPlanProgress}
          onClick={() => setModalOpen(true)}
        />
      )}

      {/* Detailed modal */}
      <MasterPlanProgressModal
        event={masterPlanProgress}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
}
```

### WebSocket Event Handling

The existing `useChat.ts` hook already handles all required events. No modifications needed - just consume the `masterPlanProgress` state:

```typescript
// Events automatically captured by useChat hook
- discovery_generation_start
- discovery_tokens_progress
- discovery_entity_discovered
- discovery_parsing_complete
- discovery_saving_start
- discovery_generation_complete
- masterplan_generation_start
- masterplan_tokens_progress
- masterplan_entity_discovered
- masterplan_parsing_complete
- masterplan_validation_start
- masterplan_saving_start
- masterplan_generation_complete
```

### Error Recovery Integration

```typescript
// In MasterPlanProgressModal
const handleRetry = async () => {
  // Clear error state
  setError(null);
  setIsRetrying(true);

  // Reset progress
  sessionStorage.removeItem('masterplan_session');

  // Re-trigger masterplan command
  await sendMessage('/masterplan {project context}');
};
```

---

## Implementation Details

### File Structure

```
src/ui/src/components/chat/
├── MasterPlanProgressIndicator.tsx       (existing - minimal changes)
├── MasterPlanProgressModal.tsx           (new - main modal container)
├── ProgressTimeline.tsx                  (new - phase visualization)
├── ProgressMetrics.tsx                   (new - statistics display)
├── PhaseIndicator.tsx                    (new - phase card)
├── ErrorPanel.tsx                        (new - error handling)
├── FinalSummary.tsx                      (new - completion screen)
└── hooks/
    └── useMasterPlanProgress.ts          (new - state management)

src/ui/src/hooks/
└── useChat.ts                            (existing - no changes)

src/ui/src/i18n/
├── en.json                               (new - English translations)
└── es.json                               (new - Spanish translations)
```

### Type Definitions

```typescript
// masterplan-types.ts
export interface ProgressState {
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

export interface PhaseStatus {
  name: 'discovery' | 'parsing' | 'validation' | 'saving';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: number;
  startTime?: Date;
  endTime?: Date;
  icon: string;
  label: string;
}

export interface ErrorInfo {
  message: string;
  code: string;
  details?: Record<string, any>;
  stackTrace?: string;
  timestamp: Date;
  source: 'validation' | 'database' | 'llm' | 'websocket' | 'unknown';
}

export interface EntityCounts {
  boundedContexts: number;
  aggregates: number;
  entities: number;
}

export interface PhaseCounts {
  phases: number;
  milestones: number;
  tasks: number;
}
```

### Custom Hook: useMasterPlanProgress

```typescript
// Location: src/ui/src/components/chat/hooks/useMasterPlanProgress.ts
export function useMasterPlanProgress(event: MasterPlanProgressEvent | null) {
  const [state, setState] = useState<ProgressState>(initialState);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem('masterplan_session');
    if (stored) {
      const session = JSON.parse(stored);
      setSessionId(session.masterplan_id);
      // Fetch latest status
      fetchMasterPlanStatus(session.masterplan_id);
    }
  }, []);

  // Process incoming events
  useEffect(() => {
    if (!event) return;
    updateStateFromEvent(event);
  }, [event]);

  // Timer for elapsed time
  useEffect(() => {
    if (!state.startTime || state.isComplete) return;
    const timer = setInterval(() => {
      setState(prev => ({
        ...prev,
        elapsedSeconds: Math.floor((Date.now() - prev.startTime!.getTime()) / 1000)
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, [state.startTime, state.isComplete]);

  return { state, sessionId };
}
```

### Integration with Existing Components

**MasterPlanProgressIndicator.tsx** - Minimal refactor:
- Extract state management to `useMasterPlanProgress` hook
- Split UI into InlineProgressHeader + ModalComponents
- Keep existing event handling logic
- Export hook for reuse in modal components

**No changes required to**:
- `useChat.ts` - Already provides masterPlanProgress state
- `ReviewModal.tsx` - Pattern to follow
- `GlassCard.tsx` / `GlassButton.tsx` - Design system components

---

## Testing Strategy

### Unit Tests

#### Components
- `ProgressTimeline.tsx` - Render phases, state transitions
- `ProgressMetrics.tsx` - Display calculations, formatting
- `PhaseIndicator.tsx` - Status indicators, animations
- `ErrorPanel.tsx` - Error display, retry handler
- `FinalSummary.tsx` - Button actions, data display

#### Hooks
- `useMasterPlanProgress.ts` - Event processing, state updates
- sessionStorage persistence, recovery

### Integration Tests

- Modal open/close behavior
- Inline header visibility independent of modal
- WebSocket event flow through component tree
- Keyboard navigation (ESC, Tab)
- Error handling and retry flow

### E2E Tests (using Playwright)

- Full generation flow with mock events
- Page refresh during generation → status recovery
- Error scenario → retry flow
- Modal interactions (open, close, actions)
- Accessibility validation (WCAG 2.1 AA)

### Test File Locations
- `/home/kwar/code/agentic-ai/src/ui/src/components/chat/__tests__/`

### Example Test Cases

```typescript
// MasterPlanProgressModal.test.tsx
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
    const errorEvent = { event: 'error', data: { message: 'Generation failed' } };
    render(<MasterPlanProgressModal open={true} event={errorEvent} />);
    expect(screen.getByText(/Generation failed/i)).toBeInTheDocument();
  });

  it('should show final summary on completion', () => {
    const completeEvent = {
      event: 'masterplan_generation_complete',
      data: { total_phases: 3, total_tasks: 120 }
    };
    render(<MasterPlanProgressModal open={true} event={completeEvent} />);
    expect(screen.getByText(/MasterPlan generated/i)).toBeInTheDocument();
  });
});
```

---

## Success Criteria

### Functional Success
- Real-time progress updates reflect all WebSocket events within 100ms
- Inline header visible immediately upon generation start
- Modal opens/closes without lag (<200ms)
- Page refresh recovers generation state within 2 seconds
- Error retry successfully re-initiates generation
- Final summary displays all required statistics correctly

### Performance Success
- Modal interaction performance: 60fps animations
- Re-renders only when relevant state changes (no unnecessary updates)
- Memory usage stable during 10+ minute generations
- sessionStorage operations < 10ms

### User Experience Success
- Users understand current phase at any time (clear labels + emoji)
- Statistics are scannable in <5 seconds for primary metrics
- Error messages are clear and actionable
- All interactive elements are keyboard accessible
- Animations enhance rather than distract

### Accessibility Success
- WCAG 2.1 AA compliance on all components
- Screen reader announces progress updates
- Color contrast ratios meet minimum standards (4.5:1)
- Focus indicators visible and logical
- Works in both English and Spanish

### Code Quality Success
- All components < 300 lines (single responsibility)
- Test coverage > 80%
- TypeScript strict mode compliance
- No prop drilling beyond 2 levels (use composition/context if needed)
- Consistent error handling patterns

---

## Out of Scope

### Phase 1 (MVP) - Explicitly Excluded
- Mobile responsiveness (desktop-first only)
- Export functionality (PDF, JSON, CSV)
- Detailed architecture diagram visualization
- Performance profiling/metrics dashboard
- Export to project management tools
- Webhook notifications
- Analytics/tracking integration
- Dark mode toggle (use system preference if available)

### Future Phases (Phase 2+)
- Mobile optimization (responsive design)
- Export to multiple formats
- Detailed breakdown by entity type
- Comparative analysis (previous generations)
- Scheduled generation with cron
- Generation templates/presets

### Known Limitations
- Desktop browser only (Phase 1)
- Maximum 120 tasks per generation (backend limit)
- Cost calculation assumes current pricing
- Timestamps based on client system clock (can drift if client time wrong)

---

## Dependencies & Prerequisites

### Frontend Dependencies
- React 18+
- React Router DOM
- TypeScript 4.9+
- Tailwind CSS 3+
- Framer Motion 6+ (for animations, optional if using CSS)
- React Icons (for icons)

### Backend Dependencies (API)
- FastAPI
- Socket.IO
- SQLAlchemy
- Pydantic

### Infrastructure
- WebSocket connection to backend (already established)
- REST API endpoint for status recovery
- sessionStorage support in browser

### Existing Integration Points
- `useChat` hook providing `masterPlanProgress` state
- WebSocket event listeners for all progress events
- Design system components (GlassCard, GlassButton)
- ReviewModal pattern for consistency

### Required API Endpoints

#### 1. Status Recovery
```
GET /api/v1/masterplans/{masterplan_id}/status
Headers: Authorization: Bearer {token}
Response: MasterPlanStatusResponse (see schema above)
```

**Implementation Location**: `/home/kwar/code/agentic-ai/src/api/routers/masterplans.py`

**Acceptance Criteria**:
- Endpoint exists and returns current generation status
- Works during and after generation
- Includes all required fields
- Handles non-existent masterplan_id gracefully (404)

#### 2. Retry Generation (re-use existing)
```
POST /api/v1/chat/send_message
Body: { conversation_id, content: "/masterplan ..." }
```

**No new endpoint needed** - reuses existing send_message flow

---

## Risks & Mitigation

### Risk 1: WebSocket Disconnection During Generation
**Impact**: User loses progress visibility, doesn't know generation status
**Probability**: Medium (network interruptions happen)
**Mitigation**:
- Store masterplan_id in sessionStorage on generation_start event
- On reconnection, fetch status from API endpoint
- Show "Reconnecting..." UI while fetching
- Resume progress display with latest stats
- Add visual indicator when connection is lost/regained

### Risk 2: Stale sessionStorage After Browser Crash
**Impact**: User has stale masterplan_id that doesn't match actual generation
**Probability**: Low
**Mitigation**:
- Add timestamp to sessionStorage entry (5-minute expiry)
- Validate retrieved masterplan_id against current conversation
- Clear sessionStorage if validation fails
- Show warning if resuming very old generation

### Risk 3: Cost Calculation Inaccuracy
**Impact**: Users see incorrect cost estimates
**Probability**: Low (static pricing)
**Mitigation**:
- Use current pricing from environment config
- Clearly label as "Estimated" cost
- Show cost breakdown with token counts
- Add note about pricing subject to change

### Risk 4: Localization Missing for New Components
**Impact**: Spanish users see English text in new features
**Probability**: High (easy to miss)
**Mitigation**:
- Use translation keys consistently
- Add i18n validation in tests
- Provide complete translation files with both languages
- Test with ES locale enabled

### Risk 5: Performance Degradation on Long Generations
**Impact**: UI becomes laggy/unresponsive after 30+ minutes
**Probability**: Medium
**Mitigation**:
- Implement virtual scrolling for long lists
- Debounce state updates to 500ms minimum
- Use React.memo for non-updating sub-components
- Monitor memory usage during E2E tests

### Risk 6: Accessibility Regression
**Impact**: Screen reader users unable to track progress
**Probability**: Low (if tested)
**Mitigation**:
- Run axe-core accessibility tests in CI
- Test with NVDA/JAWS before release
- Implement aria-live regions correctly
- Manual accessibility review by QA

---

## Timeline & Effort Estimation

### Phase 1 (MVP) - 5-6 Work Days

#### Day 1-2: Core Components (16 hours)
- Refactor MasterPlanProgressIndicator into smaller components
- Create ProgressTimeline component with SVG or CSS
- Create ProgressMetrics component with grid layout
- Basic styling with Tailwind + design system

**Deliverables**:
- MasterPlanProgressModal.tsx (basic structure)
- ProgressTimeline.tsx (phase visualization)
- ProgressMetrics.tsx (statistics display)

#### Day 3: Integration & State Management (8 hours)
- Create useMasterPlanProgress hook
- Integrate with useChat hook's masterPlanProgress state
- Wire event handlers to update state
- Test event flow

**Deliverables**:
- useMasterPlanProgress.ts hook
- Event handler integration
- State management tests

#### Day 4: Error Handling & Edge Cases (8 hours)
- Create ErrorPanel component
- Implement retry logic
- Add sessionStorage persistence
- Implement state recovery API integration

**Deliverables**:
- ErrorPanel.tsx component
- sessionStorage persistence logic
- Status recovery API integration
- Error flow tests

#### Day 5: Polish & Animations (8 hours)
- Add Framer Motion animations
- Create FinalSummary component
- Implement keyboard navigation
- Add smooth transitions

**Deliverables**:
- FinalSummary.tsx component
- Animation implementations
- Keyboard handler tests
- Visual polish

#### Day 6: Localization & Testing (8 hours)
- Add i18n support (EN/ES)
- Create translation files
- Add accessibility labels (ARIA)
- Write unit tests for all components
- Manual testing and bug fixes

**Deliverables**:
- i18n configuration
- Translation files (en.json, es.json)
- ARIA labels
- Unit test suite (>80% coverage)
- Bug fixes

### Phase 2 (Enhancement) - Future
- Mobile responsiveness (3-4 days)
- Export functionality (2-3 days)
- Accessibility audit and remediation (2 days)
- Performance optimization (2 days)
- Analytics integration (2 days)

### Effort Summary (Phase 1)

| Component | Effort | Status |
|-----------|--------|--------|
| Core Components | 16h | Critical Path |
| Integration | 8h | Dependent |
| Error Handling | 8h | Critical |
| Animations | 8h | Enhancement |
| Localization & Testing | 8h | Critical |
| **Total** | **48h / 6 days** | **MVP Complete** |

### Critical Path

1. Core Components (Day 1-2) - blocks everything
2. Integration (Day 3) - unblocks error handling
3. Error Handling (Day 4) - unblocks testing
4. Testing & Localization (Day 6) - must complete
5. Animations (Day 5) - nice-to-have, non-blocking

---

## Acceptance Criteria

### MVP Acceptance (Phase 1)

#### Functional Requirements Met
- [ ] Inline progress header displays and updates in real-time
- [ ] Modal opens/closes without errors
- [ ] All 8 WebSocket events handled correctly
- [ ] Progress percentage calculates accurately (0-100%)
- [ ] Tokens and cost display correctly
- [ ] Entity counts update in real-time
- [ ] Error messages display with retry option
- [ ] Final summary shows on completion
- [ ] Page refresh recovers generation state

#### UI/UX Requirements Met
- [ ] Animations are smooth (60fps, <500ms transitions)
- [ ] Color scheme matches design system
- [ ] Layout is responsive on desktop (1280px+)
- [ ] All text is readable (contrast ratios meet WCAG AA)
- [ ] Modal is dismissible (ESC key, click outside, X button)

#### Code Quality Requirements Met
- [ ] TypeScript strict mode compliance (no `any`)
- [ ] All components <300 lines
- [ ] Proper error boundaries implemented
- [ ] No console errors in normal operation
- [ ] Memory usage stable during 10+ minute generations

#### Testing Requirements Met
- [ ] Unit tests >80% coverage
- [ ] Integration tests for event flow
- [ ] Manual testing checklist completed
- [ ] No accessibility violations (axe-core)
- [ ] Works in EN and ES locales

#### Documentation Requirements Met
- [ ] Code comments for complex logic
- [ ] TypeScript interfaces documented
- [ ] Component props documented
- [ ] i18n keys documented
- [ ] README with usage examples

### Sign-Off Process

1. **Code Review**:
   - PR review by tech lead
   - Accessibility review
   - Performance review

2. **QA Testing**:
   - Manual QA test plan
   - E2E test suite runs
   - Accessibility testing

3. **User Acceptance**:
   - Demo to product owner
   - Feedback incorporation
   - Final approval

---

## Questions & Decisions

### Key Decisions Made

1. **Modal Implementation**: Use ReviewModal.tsx pattern for consistency with existing codebase
2. **State Management**: No Redux/Context - prop drilling acceptable for component depth
3. **Localization**: Use simple JSON-based i18n, not i18next (keep it simple)
4. **Animations**: CSS transitions preferred over Framer Motion for smaller bundle
5. **Mobile**: Desktop-first in Phase 1, mobile in Phase 2
6. **Error Recovery**: Simple "Retry" button that re-triggers /masterplan command

### Open Questions for Clarification

1. **Export Functionality**: What formats are required? (PDF, JSON, CSV?)
   - **Current**: Out of scope for MVP
   - **Decision**: Include "Export" button stub for future implementation

2. **Cost Calculation**: Should cost update in real-time or only at completion?
   - **Current Assumption**: Update in real-time based on tokens/estimated total
   - **Alternative**: Show only at completion

3. **Architecture Diagram**: Should Phase 1 include visual architecture rendering?
   - **Current**: No - show in Final Summary as text/JSON only
   - **Alternative**: Add SVG diagram in Phase 2

4. **Mobile Support**: Desktop-first for Phase 1 - how much responsive work needed?
   - **Current**: None in Phase 1, full responsive in Phase 2

---

## Appendix: WebSocket Event Details

### Event: discovery_generation_start
**Phase**: Discovery
**Triggered**: Start of discovery analysis
**Data**:
```json
{
  "estimated_tokens": 8000,
  "estimated_duration_seconds": 30
}
```
**UI Action**: Start timer, set phase, show "Analyzing DDD Requirements"

### Event: discovery_tokens_progress
**Phase**: Discovery
**Triggered**: After each token batch
**Data**:
```json
{
  "tokens_received": 2000,
  "estimated_total": 8000,
  "percentage": 25,
  "current_phase": "Parsing domain..."
}
```
**UI Action**: Update percentage, tokens display

### Event: discovery_parsing_complete
**Phase**: Discovery
**Triggered**: After DDD entity extraction
**Data**:
```json
{
  "domain": "E-commerce Platform",
  "total_bounded_contexts": 5,
  "aggregates": 12,
  "entities": 45
}
```
**UI Action**: Mark discovery parsing complete, show 48% progress

### Event: discovery_saving_start
**Phase**: Discovery
**Triggered**: Before saving entities to DB
**Data**:
```json
{
  "total_entities": 62
}
```
**UI Action**: Show "Saving to Database" phase

### Event: discovery_generation_complete
**Phase**: Discovery
**Triggered**: After discovery saved
**Data**:
```json
{
  "discovery_id": "disc_xxx",
  "cost": 0.15,
  "duration": 45
}
```
**UI Action**: Mark discovery complete, transition to MasterPlan generation

### Event: masterplan_generation_start
**Phase**: MasterPlan
**Triggered**: Start of MasterPlan generation
**Data**:
```json
{
  "estimated_tokens": 17000,
  "estimated_duration_seconds": 90
}
```
**UI Action**: Start phase 2, reset percentage to 50%, show "Generating Plan Structure"

### Event: masterplan_tokens_progress
**Phase**: MasterPlan
**Triggered**: After each token batch
**Data**:
```json
{
  "tokens_received": 8500,
  "estimated_total": 17000,
  "percentage": 50,
  "current_phase": "Creating phases..."
}
```
**UI Action**: Update percentage (map to 50-92.5% range), tokens display

### Event: masterplan_entity_discovered
**Phase**: MasterPlan
**Triggered**: After each entity discovery
**Data**:
```json
{
  "type": "phase|milestone|task",
  "count": 3
}
```
**UI Action**: Increment phase/milestone/task counter

### Event: masterplan_parsing_complete
**Phase**: MasterPlan
**Triggered**: After all entities parsed
**Data**:
```json
{
  "total_phases": 3,
  "total_milestones": 17,
  "total_tasks": 120
}
```
**UI Action**: Mark parsing complete, show 93% progress

### Event: masterplan_validation_start
**Phase**: MasterPlan
**Triggered**: Start validation
**Data**: (empty)
**UI Action**: Show "Validating Dependencies", set to 95% progress

### Event: masterplan_saving_start
**Phase**: MasterPlan
**Triggered**: Before saving MasterPlan
**Data**:
```json
{
  "total_entities": 140
}
```
**UI Action**: Show "Saving to Database", set to 97% progress

### Event: masterplan_generation_complete
**Phase**: MasterPlan
**Triggered**: Generation fully complete
**Data**:
```json
{
  "masterplan_id": "mp_xxx",
  "total_phases": 3,
  "total_milestones": 17,
  "total_tasks": 120,
  "total_cost": 0.40,
  "total_duration": 135,
  "discovery_id": "disc_xxx",
  "architecture_style": "DDD",
  "tech_stack": ["React", "FastAPI", "PostgreSQL"]
}
```
**UI Action**: Mark complete (100%), show FinalSummary with all stats

---

## Appendix: Component API Reference

### MasterPlanProgressModal

```typescript
export interface MasterPlanProgressModalProps {
  event: MasterPlanProgressEvent | null;
  open: boolean;
  onClose: () => void;
  masterplanId?: string;
}

// Usage
<MasterPlanProgressModal
  event={masterPlanProgress}
  open={isModalOpen}
  onClose={() => setIsModalOpen(false)}
/>
```

### ProgressTimeline

```typescript
export interface ProgressTimelineProps {
  phases: PhaseStatus[];
  currentPhase: string;
  animateActive?: boolean;
}

interface PhaseStatus {
  name: 'discovery' | 'parsing' | 'validation' | 'saving';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: number;
  startTime?: Date;
  endTime?: Date;
  icon: string;
  label: string;
}

// Usage
<ProgressTimeline
  phases={[
    { name: 'discovery', status: 'completed', duration: 45, icon: '✓', label: 'Discovery' },
    { name: 'parsing', status: 'in_progress', startTime: new Date(), icon: '⚙️', label: 'Parsing' },
    { name: 'validation', status: 'pending', icon: '⏳', label: 'Validation' },
    { name: 'saving', status: 'pending', icon: '⏳', label: 'Saving' }
  ]}
  currentPhase="parsing"
/>
```

### ProgressMetrics

```typescript
export interface ProgressMetricsProps {
  tokensUsed: number;
  estimatedTokens: number;
  cost: number;
  duration: number;
  estimatedDuration: number;
  entities: {
    boundedContexts: number;
    aggregates: number;
    entities: number;
    phases: number;
    milestones: number;
    tasks: number;
  };
  isComplete: boolean;
}

// Usage
<ProgressMetrics
  tokensUsed={8500}
  estimatedTokens={17000}
  cost={0.25}
  duration={65}
  estimatedDuration={135}
  entities={{
    boundedContexts: 5,
    aggregates: 12,
    entities: 45,
    phases: 3,
    milestones: 17,
    tasks: 120
  }}
  isComplete={false}
/>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-30 | Initial specification for MVP |

---

## Sign-Off

**Document Author**: Claude Code (Product Specification)
**Date**: 2025-10-30
**Status**: Ready for Development
**Approval**: Pending (to be completed by tech lead)

This specification provides all technical details necessary for implementation without requiring clarification from the user. The feature is well-scoped, achievable in 6 days, and builds on existing patterns in the codebase.
