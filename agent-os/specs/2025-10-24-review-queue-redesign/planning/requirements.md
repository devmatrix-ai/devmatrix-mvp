# Spec Requirements: Review Queue Complete Redesign

## Initial Description
Complete the migration of ReviewQueue page from Material-UI to the custom glassmorphism design system. This is Phase 2 of the larger UI unification project.

## Requirements Discussion

### First Round Questions

**Q1:** ¿Preferís mantener el layout de tabla o cambiarlo a un layout de cards como en MasterplansPage?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables basados en MasterplansPage

**Q2:** ¿El modal de review detail debería ser un overlay full-screen o un modal centrado?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q3:** ¿Necesitás algún componente adicional en el design system (ej: GlassTable, GlassModal) o adaptamos con los existentes?
**Answer:** No tengo especificaciones adicionales - crear componentes necesarios

### Existing Code to Reference

**Similar Features Identified:**
- Feature: MasterplansPage - Path: `src/ui/src/pages/MasterplansPage.tsx`
  - Card-based layout instead of tables
  - Filter buttons for status
  - Search functionality
- Feature: MasterplansList - Path: `src/ui/src/components/masterplans/MasterplansList.tsx`
  - Card grid layout pattern
  - Empty state handling
- Feature: Current ReviewQueue POC - Path: `src/ui/src/pages/review/ReviewQueue.tsx`
  - 5 components already migrated
  - Functionality working correctly

**Components already available:**
- Design system: GlassCard, GlassButton, StatusBadge, GlassInput, SearchBar, FilterButton, PageHeader, SectionHeader
- Review components: CodeDiffViewer, AISuggestionsPanel, ReviewActions, ConfidenceIndicator

## Visual Assets

### Files Provided:
No additional visual assets provided.

### Visual Insights:
Using MasterplansPage as reference:
- Card-based layout with grid (not tables)
- Empty state with centered message
- Loading state with spinner
- Error state with alert message
- Modal/dialog uses full backdrop blur
- Responsive grid: 1 column mobile, 2-3 columns tablet/desktop

## Requirements Summary

### Functional Requirements

**Must Preserve All Current Functionality:**
- Review queue loading with status filter
- Search by description/file/ID
- Sorting by priority/confidence/date
- View review detail (modal)
- Review actions (approve, reject, edit, regenerate)
- Real-time queue updates

**UI Components to Replace:**

1. **Table → Card Grid**
   - Replace Material-UI Table with GlassCard grid
   - Each review item = 1 card
   - Cards show: priority, confidence, description, file, issues, status, recommendation
   - Hover effects on cards
   - Click card to open review detail

2. **Dialog → Custom Modal**
   - Full-screen backdrop with glassmorphism
   - Centered modal with GlassCard
   - Close button with GlassButton
   - Responsive width (90% mobile, 80% tablet, 60% desktop max)

3. **Grid → Tailwind Grid**
   - Use Tailwind CSS grid utilities
   - Responsive columns: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
   - Gap between cards: `gap-6`

4. **Alert → Custom Alert**
   - GlassCard with error/warning/info styling
   - StatusBadge for severity icon
   - Dismiss button with GlassButton

5. **CircularProgress → Custom Spinner**
   - Glassmorphism loading card
   - Purple spinning animation
   - Centered in page

6. **Other Material-UI** → Design System
   - Remove all Material-UI imports
   - Use Tailwind CSS for layout
   - Use design system components for UI

### Layout Changes

**Current (Table-based):**
```
[Header]
[Filters]
[Table with rows]
[Dialog overlay]
```

**New (Card-based):**
```
[PageHeader with emoji 🔍]
[SearchBar + FilterButtons in GlassCard]
[Card Grid (responsive columns)]
  [ReviewCard] [ReviewCard] [ReviewCard]
  [ReviewCard] [ReviewCard] [ReviewCard]
[Modal with GlassCard content]
```

### Component Structure

**ReviewCard** (new component to create):
- Props: `review` (ReviewItem), `onClick`
- Layout: GlassCard with hover effect
- Content:
  - Top: Priority badge + Confidence indicator
  - Middle: Description + File path
  - Bottom: Issues summary + Status + Recommendation
  - Action: View button

**ReviewModal** (new component to create):
- Props: `review` (ReviewItem), `open` (boolean), `onClose`
- Layout: Backdrop blur + centered GlassCard
- Content:
  - Header: Title + Close button
  - Body: CodeDiffViewer + AISuggestionsPanel (side by side on desktop, stacked on mobile)
  - Footer: ReviewActions

**LoadingState** (new component to create):
- Centered GlassCard with spinner
- Purple accent animation

**EmptyState** (new component to create):
- Centered content with icon
- Message text
- Optional action button

**ErrorState** (new component to create):
- Alert-style GlassCard
- Error message
- Retry button

### Reusability Opportunities
- ReviewCard pattern can be reused for other list views
- Modal pattern can be extracted to design system
- Loading/Empty/Error states can be reused across app

### Scope Boundaries

**In Scope:**
- Complete Material-UI removal from ReviewQueue
- New ReviewCard component
- New ReviewModal component
- Loading/Empty/Error state components
- Card-based grid layout
- Responsive design
- All existing functionality preserved
- Visual consistency with MasterplansPage

**Out of Scope:**
- Changes to review functionality/logic
- Backend API changes
- Other review components (CodeDiffViewer, AISuggestionsPanel, ReviewActions) - already working
- Other pages migration - future phases
- New features not in current ReviewQueue

### Technical Considerations

**Technology Stack:**
- React 18+ with TypeScript
- Tailwind CSS for layout
- Design system components
- No Material-UI

**Integration Points:**
- Use existing review components (CodeDiffViewer, etc.)
- Use design system components
- Maintain existing API calls
- Preserve state management

**Code Patterns:**
- Follow MasterplansPage layout patterns
- Use GlassCard for all containers
- Use Tailwind grid for responsive layout
- Consistent spacing (p-8, gap-6)

**Performance:**
- Lazy load modal content
- Virtual scrolling if >100 items (future enhancement)
- Optimize re-renders with React.memo

**Accessibility:**
- Keyboard navigation (Tab, Enter, Escape)
- ARIA labels for buttons without text
- Focus management in modal
- Screen reader friendly

**Defaults Assumed:**
1. **Layout**: Card-based like MasterplansPage (better than table for responsive)
2. **Modal**: Centered with backdrop blur (consistent with design system)
3. **Components**: Create minimal new components (ReviewCard, ReviewModal) with existing design system
4. **Responsive**: Mobile-first with 1-2-3 column grid
5. **Sorting**: Keep in-memory sorting (no UI changes needed)
6. **Empty state**: Follow MasterplansPage pattern
