# Initial Idea: Review Components Material-UI Migration

## User's Original Request

Complete Phase 2 of UI unification by migrating the remaining review components from Material-UI to the glassmorphism design system.

## Context

**Phase 1 (Completed)**: UI Design System created with 8 glassmorphism components
**Phase 2a (Completed)**: ReviewQueue page migrated (table → card grid, zero Material-UI)
**Phase 2b (Current)**: Migrate remaining review components still using Material-UI

The review system currently has a mix:
- ✅ ReviewQueue page fully migrated (Phase 2a)
- ✅ ReviewCard, ReviewModal, LoadingState, EmptyState, ErrorState created
- ❌ 4 components still have Material-UI dependencies:
  - CodeDiffViewer.tsx
  - AISuggestionsPanel.tsx
  - ReviewActions.tsx
  - ConfidenceIndicator.tsx

## Goal

Remove ALL remaining Material-UI imports from review components, achieving 100% design system consistency across the entire review workflow.

## Source Material

- Design system: `src/ui/src/components/design-system/`
- Review components: `src/ui/src/components/review/`
- Workflow: `agent-os/workflows/ui-unification-design.md` (Phase 2 tasks 2.2-2.5)
- Phase 2a reference: `agent-os/specs/2025-10-24-review-queue-redesign/`

## Components to Migrate

From Workflow Document (Phase 2 tasks 2.2-2.5):

1. **CodeDiffViewer** (Task 2.2)
   - Keep Monaco Editor
   - Add glassmorphism wrapper
   - Update tabs styling
   - Update issue alerts styling
   - Add purple accent colors

2. **AISuggestionsPanel** (Task 2.3)
   - Remove Material-UI Alert components
   - Add glassmorphism card container
   - Style issues list with custom badges
   - Update suggestions display

3. **ReviewActions** (Task 2.4)
   - Remove Material-UI Button
   - Use GlassButton from design system
   - Add purple glow on active state
   - Add hover effects

4. **ConfidenceIndicator** (Task 2.5)
   - Remove Material-UI Chip
   - Create custom badge with glassmorphism
   - Add color-coded borders (green → yellow → red)

## Success Criteria

- Zero Material-UI imports in all review components
- 100% visual consistency with design system
- All functionality preserved (Monaco Editor, suggestions, actions)
- No console errors or TypeScript errors
- Tests passing for all migrated components
