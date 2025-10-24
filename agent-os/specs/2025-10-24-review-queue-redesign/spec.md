# Specification: Review Queue Complete Redesign

## Goal
Complete the migration of ReviewQueue page from Material-UI to the custom glassmorphism design system, achieving 100% visual consistency with MasterplansPage while preserving all existing functionality.

## User Stories
- As a reviewer, I want a visually consistent interface so that navigation between pages feels seamless
- As a developer, I want zero Material-UI dependencies in ReviewQueue so that we can eventually remove the library
- As a user, I want the review queue to work on mobile/tablet/desktop so that I can review code anywhere
- As a reviewer, I want the same filtering and search capabilities so that my workflow isn't disrupted

## Core Requirements

**Layout Transformation:**
- Replace table-based layout with card-based grid layout (like MasterplansPage)
- Responsive grid: 1 column (mobile), 2 columns (tablet), 3 columns (desktop)
- Each review = 1 GlassCard with hover effects

**Components to Create:**
1. **ReviewCard** - Individual review item card
   - Shows: priority, confidence, description, file, issues, status, recommendation
   - Click to open detail modal
   - Hover effects with shadow-xl

2. **ReviewModal** - Review detail overlay
   - Full backdrop blur
   - Centered GlassCard container
   - Two-column layout (code + suggestions) on desktop
   - Stacked layout on mobile

3. **LoadingState** - Loading indicator
   - Centered GlassCard with spinner
   - Purple accent animation

4. **EmptyState** - No results message
   - Centered icon + message
   - Follow MasterplansPage pattern

5. **ErrorState** - Error display
   - GlassCard with error styling
   - Retry button

**Material-UI Removals:**
- All Table components (Table, TableHead, TableBody, TableRow, TableCell, TableContainer, TableSortLabel)
- Dialog and DialogTitle, DialogContent, DialogActions
- Grid components (use Tailwind grid instead)
- Alert component (use custom alert with GlassCard)
- CircularProgress (use custom spinner)
- All @mui/material imports

**Functionality Preservation:**
- Search by description/file/ID
- Filter by status (all, pending, in_review, approved, rejected)
- Sorting by priority/confidence/created_at
- View review details in modal
- Perform review actions (approve, reject, edit, regenerate)
- Real-time queue refresh

## Visual Design

**Reference**: `src/ui/src/pages/MasterplansPage.tsx` and `src/ui/src/components/masterplans/MasterplansList.tsx`

**Layout Pattern:**
```
┌─────────────────────────────────────────┐
│ 🔍 Review Queue                         │ PageHeader
│ Low-confidence atoms flagged            │
├─────────────────────────────────────────┤
│ [Search] [All] [Pending] [In Review]   │ GlassCard with filters
├─────────────────────────────────────────┤
│ ┌───────┐ ┌───────┐ ┌───────┐          │
│ │ Card  │ │ Card  │ │ Card  │          │ Grid of ReviewCards
│ │ P:80  │ │ P:65  │ │ P:50  │          │
│ └───────┘ └───────┘ └───────┘          │
│ ┌───────┐ ┌───────┐ ┌───────┐          │
│ │ Card  │ │ Card  │ │ Card  │          │
│ └───────┘ └───────┘ └───────┘          │
└─────────────────────────────────────────┘
```

**ReviewCard Structure:**
```
┌───────────────────────────────────┐
│ [Priority 80] [Confidence ●●●○○]  │ Top badges
│                                   │
│ Create user authentication        │ Description
│ src/auth/login.py                 │ File path
│                                   │
│ [2 Critical] [3 High] [1 Medium]  │ Issues summary
│                                   │
│ Status: PENDING                   │ Status
│ Recommendation: REVIEW CAREFULLY  │ AI recommendation
│                                   │
│              [View Review →]      │ Action button
└───────────────────────────────────┘
```

**Modal Structure:**
```
[Backdrop blur overlay]
  ┌─────────────────────────────────────┐
  │ Review: Description          [X]    │ Header
  ├─────────────────────────────────────┤
  │ ┌─────────────┐ ┌────────────────┐ │
  │ │ Code Diff   │ │ AI Suggestions │ │ Two columns
  │ │ Viewer      │ │ Panel          │ │
  │ │             │ │                │ │
  │ └─────────────┘ └────────────────┘ │
  ├─────────────────────────────────────┤
  │ [Approve] [Reject] [Edit] [Regen]  │ Actions
  └─────────────────────────────────────┘
```

**Color/Styling:**
- Background: `bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20`
- Cards: glassmorphism with `backdrop-blur-lg`
- Hover: `hover:shadow-xl transition-all`
- Active filters: purple glow
- Status badges: color-coded (green/yellow/red)

## Reusable Components

### From Design System (Already Available)
- GlassCard - Card containers
- GlassButton - All buttons
- StatusBadge - Status indicators
- SearchBar - Search input
- FilterButton - Filter toggles
- PageHeader - Page title with emoji
- GlassInput - Any additional inputs

### From Review Components (Already Available)
- CodeDiffViewer - Code display with syntax highlighting
- AISuggestionsPanel - AI analysis display
- ReviewActions - Action buttons (approve, reject, etc.)
- ConfidenceIndicator - Confidence score display

### New Components Required
1. **ReviewCard** (`src/ui/src/components/review/ReviewCard.tsx`)
   - Why new: Specific to review queue layout, not generic enough for design system
   - Reuses: GlassCard, StatusBadge, GlassButton, ConfidenceIndicator

2. **ReviewModal** (`src/ui/src/components/review/ReviewModal.tsx`)
   - Why new: Specific modal structure for review workflow
   - Reuses: GlassCard, GlassButton, CodeDiffViewer, AISuggestionsPanel, ReviewActions

3. **LoadingState** (`src/ui/src/components/review/LoadingState.tsx`)
   - Why new: Simple loading indicator
   - Reuses: GlassCard

4. **EmptyState** (`src/ui/src/components/review/EmptyState.tsx`)
   - Why new: Review-specific empty state
   - Reuses: GlassCard

5. **ErrorState** (`src/ui/src/components/review/ErrorState.tsx`)
   - Why new: Error display component
   - Reuses: GlassCard, StatusBadge, GlassButton

## Technical Approach

**Component Architecture:**
- ReviewQueue (page) - Main component, state management
  - SearchBar + FilterButton row
  - ReviewCard grid (mapped from reviews array)
  - ReviewModal (conditional render)
  - LoadingState / EmptyState / ErrorState (conditional)

**State Management:**
- Keep existing useState hooks for reviews, filters, selected review
- No state management library needed (current approach works)

**Responsive Strategy:**
- Tailwind breakpoints: mobile-first
- Grid columns: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- Modal width: `w-11/12 md:w-5/6 lg:w-4/5 xl:w-3/4 max-w-7xl`
- Two-column layout in modal: `grid-cols-1 lg:grid-cols-3` (2:1 ratio)

**Performance:**
- Keep existing pagination (limit 50)
- React.memo on ReviewCard if needed
- Lazy modal content (only render when open)

**Accessibility:**
- Keyboard: Tab navigation, Enter to open, Escape to close modal
- ARIA: role="button" on cards, aria-label on icon buttons
- Focus management: trap focus in modal, return focus on close
- Screen readers: semantic HTML, descriptive labels

## Out of Scope
- Changes to review logic or API calls
- Modifications to CodeDiffViewer, AISuggestionsPanel, ReviewActions components
- New review features
- Other pages migration
- Monaco Editor changes
- Backend changes

## Success Criteria
- Zero Material-UI imports in ReviewQueue.tsx
- Zero Material-UI components rendered
- All existing functionality works (search, filter, sort, review actions)
- Visual appearance matches MasterplansPage aesthetic 100%
- Responsive design works on mobile/tablet/desktop
- No TypeScript errors
- No console errors or warnings
- Build succeeds
- Code is cleaner and more maintainable than before
