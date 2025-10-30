# MasterPlan Progress Components

Comprehensive documentation for MasterPlan generation progress tracking UI components.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
  - [MasterPlanProgressModal](#1-masterplanprogressmodal)
  - [ProgressMetrics](#2-progressmetrics)
  - [ProgressTimeline](#3-progresstimeline)
  - [ErrorPanel](#4-errorpanel)
  - [FinalSummary](#5-finalsummary)
  - [useMasterPlanProgress Hook](#6-usemasterplanprogress-hook)
- [Usage Examples](#usage-examples)
- [WebSocket Events](#websocket-events)
- [Translation Keys](#translation-keys)
- [Customization](#customization)
- [Testing](#testing)
- [Known Limitations](#known-limitations)

---

## Overview

The MasterPlan Progress system provides real-time visual feedback during MasterPlan generation with:

- **Full-screen modal** with detailed statistics and phase timeline
- **Inline progress header** always visible during generation
- **Real-time event processing** from WebSocket streams
- **Session persistence** for page refresh recovery
- **Error handling** with retry mechanism
- **Accessibility compliance** (WCAG 2.1 AA)

### Key Features

- 📊 **Real-time metrics**: Token usage, cost estimation, elapsed time
- 🔄 **Phase tracking**: 4 phases (Discovery → Parsing → Validation → Saving)
- 🎯 **Entity discovery**: Track bounded contexts, aggregates, entities
- ⚠️ **Error handling**: Detailed error panel with retry functionality
- 💾 **Session recovery**: Resume progress after page refresh (5min expiry)
- ♿ **Accessible**: Full keyboard navigation, ARIA attributes, screen reader support

---

## Architecture

### Component Hierarchy

```
MasterPlanProgressModal (Container)
├── ProgressTimeline (Phase indicators)
├── ProgressMetrics (Statistics display)
│   ├── Primary Metrics (Progress bar, time)
│   ├── Secondary Metrics (Tokens, cost, entities)
│   └── Tertiary Metrics (Raw data, debugging)
├── ErrorPanel (Error state)
│   ├── Error message & code
│   ├── Expandable details
│   └── Retry button
└── FinalSummary (Complete state)
    ├── Statistics summary
    ├── Architecture info
    └── Action buttons
```

### Data Flow

```
WebSocket Event
    ↓
useMasterPlanProgress Hook
    ↓ (processes event)
ProgressState Update
    ↓
Component Re-render
    ↓
sessionStorage Persistence
```

### State Management

**Custom Hook**: `useMasterPlanProgress`
- Processes 12 WebSocket event types
- Manages progress state (percentage, phase, metrics)
- Handles elapsed time calculation
- Persists to sessionStorage
- Provides retry mechanism

**Storage**: `masterplanStorage` utilities
- Store/retrieve session data
- 5-minute expiry
- Automatic cleanup on completion/error

---

## Components

### 1. MasterPlanProgressModal

**Location**: `/src/ui/src/components/chat/MasterPlanProgressModal.tsx`

Full-screen modal container for MasterPlan generation progress.

#### Props

```typescript
interface MasterPlanProgressModalProps {
  event: MasterPlanProgressEvent | null;
  open: boolean;
  onClose: () => void;
  masterplanId?: string;
}
```

#### Features

- **Escape key handling**: Close modal with ESC
- **Backdrop click**: Close on backdrop click
- **Body scroll lock**: Prevents body scroll when open
- **Lazy loading**: Child components load on demand
- **Conditional rendering**: Shows different content based on event state

#### Usage

```tsx
import MasterPlanProgressModal from '@/components/chat/MasterPlanProgressModal';

function MyComponent() {
  const [modalOpen, setModalOpen] = useState(false);
  const [event, setEvent] = useState<MasterPlanProgressEvent | null>(null);

  return (
    <MasterPlanProgressModal
      event={event}
      open={modalOpen}
      onClose={() => setModalOpen(false)}
    />
  );
}
```

---

### 2. ProgressMetrics

**Location**: `/src/ui/src/components/chat/ProgressMetrics.tsx`

Displays detailed generation statistics in three collapsible sections.

#### Props

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

#### Sections

**Primary Metrics** (always visible):
- Progress bar (0-100%)
- Elapsed time
- Time remaining (if not complete)

**Secondary Metrics** (collapsible, expanded by default):
- Token usage (8,500 / 17,000)
- Cost estimation ($0.2567)
- Entity counts (bounded contexts, aggregates, entities, phases, milestones, tasks)

**Tertiary Metrics** (collapsible, collapsed by default):
- Raw JSON data for debugging
- Detailed breakdown

---

### 3. ProgressTimeline

**Location**: `/src/ui/src/components/chat/ProgressTimeline.tsx`

Visual timeline showing 4 generation phases with status indicators.

#### Props

```typescript
interface ProgressTimelineProps {
  phases: PhaseStatus[];
  currentPhase: string;
  animateActive?: boolean;
}

interface PhaseStatus {
  name: string;
  status: 'pending' | 'in_progress' | 'completed';
  icon: string;
  label: string;
  duration?: number; // seconds (only for completed phases)
}
```

#### Features

- **Status colors**:
  - `completed`: Green (#10B981)
  - `in_progress`: Blue (#3B82F6) with pulse animation
  - `pending`: Gray (#6B7280)
- **Duration display**: Shows completion time for finished phases
- **Responsive**: Horizontal layout (desktop) → Vertical layout (mobile)
- **Animated**: Pulse effect on active phase

---

### 4. ErrorPanel

**Location**: `/src/ui/src/components/chat/ErrorPanel.tsx`

Displays error information with expandable details and retry functionality.

#### Props

```typescript
interface ErrorPanelProps {
  error: {
    message: string;
    code: string;
    details?: Record<string, any>;
    stackTrace?: string;
    timestamp?: Date;
    source?: string;
  };
  onRetry: () => void | Promise<void>;
  isRetrying: boolean;
}
```

---

### 5. FinalSummary

**Location**: `/src/ui/src/components/chat/FinalSummary.tsx`

Displays completion summary with statistics and action buttons.

#### Props

```typescript
interface FinalSummaryProps {
  stats: {
    totalTokens: number;
    totalCost: number;
    totalDuration: number;
    entities: {
      boundedContexts: number;
      aggregates: number;
      entities: number;
    };
    phases: {
      phases: number;
      milestones: number;
      tasks: number;
    };
  };
  architectureStyle?: string;
  techStack?: string[];
  onViewDetails: () => void;
  onStartExecution: () => void;
}
```

---

### 6. useMasterPlanProgress Hook

**Location**: `/src/ui/src/hooks/useMasterPlanProgress.ts`

Custom hook for managing MasterPlan progress state.

#### Usage

```typescript
import { useMasterPlanProgress } from '@/hooks/useMasterPlanProgress';

const {
  state,
  sessionId,
  phases,
  handleRetry,
  clearError,
  isLoading,
} = useMasterPlanProgress(event);
```

#### Return Value

```typescript
interface UseMasterPlanProgressResult {
  state: ProgressState;
  sessionId: string | null;
  phases: PhaseStatus[];
  handleRetry: () => Promise<void>;
  clearError: () => void;
  isLoading: boolean;
}
```

---

## Usage Examples

### Basic Modal Integration

```tsx
import React, { useState, useEffect } from 'react';
import MasterPlanProgressModal from '@/components/chat/MasterPlanProgressModal';
import { useMasterPlanProgress } from '@/hooks/useMasterPlanProgress';

function ChatInterface() {
  const [modalOpen, setModalOpen] = useState(false);
  const [event, setEvent] = useState<MasterPlanProgressEvent | null>(null);

  const { state, phases } = useMasterPlanProgress(event);

  // Listen to WebSocket events
  useEffect(() => {
    const socket = io('ws://localhost:8000');

    socket.on('masterplan_progress', (data) => {
      setEvent(data);

      // Auto-open modal on start
      if (data.event === 'discovery_generation_start') {
        setModalOpen(true);
      }
    });

    return () => socket.disconnect();
  }, []);

  return (
    <>
      {/* Inline progress header (always visible) */}
      {state.currentPhase && !state.isComplete && (
        <div className="inline-progress-header">
          <span>{state.currentPhase}: {state.percentage}%</span>
          <button onClick={() => setModalOpen(true)}>
            View Details
          </button>
        </div>
      )}

      {/* Full-screen modal */}
      <MasterPlanProgressModal
        event={event}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
}
```

---

## WebSocket Events

### Event Flow

```
Discovery Phase:
1. discovery_generation_start
2. discovery_tokens_progress (multiple)
3. discovery_entity_discovered (multiple)
4. discovery_parsing_complete
5. discovery_saving_start
6. discovery_generation_complete

MasterPlan Phase:
7. masterplan_generation_start
8. masterplan_tokens_progress (multiple)
9. masterplan_entity_discovered (multiple)
10. masterplan_parsing_complete
11. masterplan_validation_start
12. masterplan_saving_start
13. masterplan_generation_complete

Error:
14. generation_error
```

### Key Event Examples

#### discovery_generation_start

```typescript
{
  event: 'discovery_generation_start',
  data: {
    estimated_tokens: 10000,
    estimated_duration_seconds: 120
  }
}
```

#### masterplan_tokens_progress

```typescript
{
  event: 'masterplan_tokens_progress',
  data: {
    tokens_received: 3500,
    percentage: 50,  // Maps to 50-92.5% range
    current_phase: 'parsing'
  }
}
```

#### masterplan_generation_complete

```typescript
{
  event: 'masterplan_generation_complete',
  data: {
    total_cost: 0.45,
    total_phases: 3,
    total_milestones: 17,
    total_tasks: 120
  }
}
```

---

## Translation Keys

### Modal

```
masterplan.title
masterplan.status.generating
masterplan.status.complete
masterplan.status.failed
masterplan.accessibility.closeModal
masterplan.buttons.close
masterplan.buttons.viewDetails
masterplan.buttons.startExecution
```

### Timeline

```
masterplan.timeline.title
masterplan.phase.discovery
masterplan.phase.parsing
masterplan.phase.validation
masterplan.phase.saving
masterplan.timeline.duration
```

### Metrics

```
masterplan.metrics.primary
masterplan.metrics.secondary
masterplan.metrics.tertiary
masterplan.metrics.tokens
masterplan.metrics.cost
masterplan.metrics.entities
masterplan.metrics.boundedContexts
masterplan.metrics.aggregates
```

---

## Customization

### Styling

All components use Tailwind CSS utility classes.

### Colors

```scss
$completed: #10B981 (green-500)
$in-progress: #3B82F6 (blue-500)
$pending: #6B7280 (gray-500)
$error: #EF4444 (red-500)
```

### Breakpoints

```
sm: 640px   // Mobile landscape
md: 768px   // Tablet
lg: 1024px  // Desktop
```

---

## Testing

### Test Files

```
__tests__/
├── MasterPlanProgressModal.test.tsx       (405 lines)
├── ProgressMetrics.test.tsx               (362 lines)
├── ProgressTimeline.test.tsx              (300+ lines)
├── ErrorPanel.test.tsx                    (250+ lines)
├── FinalSummary.test.tsx                  (200+ lines)
└── integration.test.tsx                   (627 lines)

hooks/__tests__/
└── useMasterPlanProgress.test.ts          (654 lines)
```

### Coverage Targets

- **Line coverage**: >80%
- **Branch coverage**: >75%
- **Function coverage**: >85%

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- MasterPlanProgressModal.test.tsx

# Run in watch mode
npm test -- --watch
```

### Accessibility Testing

All components tested with `axe-core` for WCAG 2.1 AA compliance.

---

## Known Limitations

### Current Limitations

1. **Session Expiry**: 5-minute limit for session recovery
2. **No Real-time Sync**: No cross-tab synchronization
3. **Modal Focus Trap**: Basic focus management
4. **Percentage Capping**: Discovery capped at 48%, masterplan at 92.5%
5. **No Pause/Resume**: Generation cannot be paused

### Future Enhancements

- [ ] Real-time collaboration (multiple users viewing same progress)
- [ ] Historical progress logs
- [ ] Export progress report (PDF/CSV)
- [ ] Customizable phase names and icons
- [ ] Dark mode support
- [ ] Progressive Web App (PWA) support

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainers**: Frontend Team
