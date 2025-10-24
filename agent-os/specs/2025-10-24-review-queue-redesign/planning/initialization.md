# Initial Idea: Review Queue Complete Redesign

## User's Original Request

Complete the redesign of the Review Queue page by removing all remaining Material-UI components and applying the glassmorphism design system throughout the entire page.

## Context

**Phase 1 (Completed)**: UI Design System created with 8 glassmorphism components
**Phase 2 (Current)**: Apply design system to entire ReviewQueue page

The ReviewQueue page currently has a mix:
- ✅ 5 components already migrated (PageHeader, SearchBar, FilterButton, GlassCard, StatusBadge)
- ❌ Many Material-UI components remaining (Table, Dialog, Grid, Alert, etc.)

## Goal

Replace ALL remaining Material-UI components in ReviewQueue with custom design system components, achieving 100% visual consistency with MasterplansPage aesthetic.

## Source Material

- Design system: `src/ui/src/components/design-system/`
- Current ReviewQueue: `src/ui/src/pages/review/ReviewQueue.tsx`
- Reference design: `src/ui/src/pages/MasterplansPage.tsx`
- Workflow document: `agent-os/workflows/ui-unification-design.md` (Phase 2 section)

## Components to Replace

From Material-UI to Design System:
1. **Table/TableContainer** → Custom card-based layout with GlassCard
2. **Dialog** → Custom modal with glassmorphism backdrop
3. **Grid** → Tailwind CSS grid utilities
4. **Alert** → Custom alert with StatusBadge + GlassCard
5. **CircularProgress** → Custom loading spinner
6. **TableHead/TableBody/TableRow/TableCell** → Custom table or card list
7. Any remaining Material-UI imports

## Success Criteria

- Zero Material-UI components remaining in ReviewQueue
- 100% visual consistency with MasterplansPage
- All functionality preserved (sorting, filtering, search, review actions)
- Responsive design working on all breakpoints
- No console errors or TypeScript errors
