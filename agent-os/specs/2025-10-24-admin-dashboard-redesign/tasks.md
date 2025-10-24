# Task Breakdown: Admin Dashboard Glassmorphism Redesign

## Overview
Total Tasks: 5 task groups
Estimated Time: 4-6 hours
Testing Approach: Visual QA and functional testing
Strategy: Adaptive (systematic migration with visual consistency validation)

## Task List

### Task Group 1: Page Structure & Navigation
**Dependencies:** Phase 1 Design System (completed), Phase 2b Review Components (completed)

- [ ] 1.0 Complete page structure and navigation styling
  - [ ] 1.1 Add gradient background to page container
    - File: `src/ui/src/pages/AdminDashboardPage.tsx`
    - Replace: `<div className="flex-1 p-8 overflow-auto">`
    - With: `<div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">`
    - Pattern: Same as MasterplansPage and ReviewQueue
  - [ ] 1.2 Replace page header with PageHeader component
    - Remove: `<h1 className="text-4xl font-bold text-white dark:text-white mb-8">Admin Dashboard</h1>`
    - Add: `<PageHeader emoji="🛡️" title="Admin Dashboard" />`
    - Import: `import { PageHeader } from '../components/design-system'`
  - [ ] 1.3 Update tab navigation styling
    - Current: Border-based tabs with gray colors
    - Target: Glassmorphism tabs with purple active state
    - Active tab: `bg-purple-600 text-white`
    - Inactive tab: `text-gray-400 hover:text-white hover:bg-white/10`
    - Container: `border-b border-white/10`
    - Reference: CodeDiffViewer tabs pattern
  - [ ] 1.4 Add design system imports
    - Import: `GlassCard, GlassButton, GlassInput, SearchBar, StatusBadge, PageHeader, LoadingState`
    - Import: `CustomAlert` from review components
    - Import: `cn` utility from lib/utils

**Acceptance Criteria:**
- Gradient background visible across entire page
- PageHeader displays with shield emoji
- Tab navigation uses purple active state
- All design system components imported
- TypeScript compiles without errors

---

### Task Group 2: Stats Cards (Overview Tab)
**Dependencies:** Task Group 1

- [ ] 2.0 Complete stats cards migration (4 cards)
  - [ ] 2.1 Migrate Total Users card
    - Replace container: `bg-gray-800 border-gray-700` → `<GlassCard className="p-6">`
    - Update icon container: `bg-blue-900/20` → `bg-blue-500/20 backdrop-blur-sm`
    - Update text colors: `text-gray-400` → `text-gray-300`, `text-white` stays
    - Pattern: GlassCard wrapper, glassmorphism icon container
  - [ ] 2.2 Migrate Active Conversations card
    - Same pattern as 2.1
    - Icon container: `bg-emerald-500/20 backdrop-blur-sm`
    - Icon color: `text-emerald-400`
  - [ ] 2.3 Migrate Total Storage card
    - Same pattern as 2.1
    - Icon container: `bg-purple-500/20 backdrop-blur-sm`
    - Icon color: `text-purple-400`
  - [ ] 2.4 Migrate Total API Calls card
    - Same pattern as 2.1
    - Icon container: `bg-amber-500/20 backdrop-blur-sm`
    - Icon color: `text-amber-400`
  - [ ] 2.5 Verify grid layout responsiveness
    - Grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6`
    - Test: Desktop (4 columns), tablet (2 columns), mobile (1 column)

**Acceptance Criteria:**
- All 4 stats cards use GlassCard component
- Icon containers have glassmorphism effect
- Color scheme: blue (users), emerald (conversations), purple (storage), amber (API calls)
- Responsive grid layout works correctly
- Visual consistency with MasterplansPage stats

---

### Task Group 3: Users Table & Search (Users Tab)
**Dependencies:** Task Group 1

- [ ] 3.0 Complete users table and search migration
  - [ ] 3.1 Migrate search bar
    - Current: Custom input with gray background
    - Target: `<GlassCard className="p-4"><SearchBar ... /></GlassCard>`
    - Props: `value={searchQuery}`, `onChange={(e) => setSearchQuery(e.target.value)}`
    - Placeholder: "Search by email or username..."
  - [ ] 3.2 Migrate users table container
    - Replace: `bg-gray-800 border-gray-700` → `<GlassCard className="overflow-hidden">`
    - Table structure preserved, only container changes
  - [ ] 3.3 Update table header styling
    - Current: `bg-gray-700`
    - Target: `bg-white/5 border-b border-white/10`
    - Text: `text-gray-300` for column headers
  - [ ] 3.4 Update table rows styling
    - Current: `bg-gray-800 divide-gray-700`
    - Target: `divide-y divide-white/10`
    - Hover: `hover:bg-white/5 transition-colors`
    - Text: `text-white` (primary), `text-gray-300` (secondary)
  - [ ] 3.5 Migrate status badges
    - Active: `<StatusBadge status="success">Active</StatusBadge>`
    - Inactive: `<StatusBadge status="default">Inactive</StatusBadge>`
    - Verified: `<StatusBadge status="info">✓ Verified</StatusBadge>`
    - Remove all Material-UI-style badge classes
  - [ ] 3.6 Migrate action buttons (Edit, Delete)
    - Edit button: `<GlassButton variant="ghost" size="sm"><FiEdit2 /></GlassButton>`
    - Delete button: `<GlassButton variant="ghost" size="sm"><FiTrash2 className="text-red-400" /></GlassButton>`
    - Replace all standard button classes
  - [ ] 3.7 Migrate pagination controls
    - Previous/Next: `<GlassButton variant="ghost" disabled={...}>...</GlassButton>`
    - Page info: `text-gray-400` for page count display
    - Layout: `flex items-center justify-between mt-6`

**Acceptance Criteria:**
- Search bar uses SearchBar component in GlassCard
- Table container uses GlassCard with overflow-hidden
- Table header uses glassmorphism background (bg-white/5)
- Table rows have glassmorphism hover effect
- Status badges use StatusBadge component (3 types)
- Action buttons use GlassButton component
- Pagination uses GlassButton for Previous/Next
- Visual consistency with ReviewQueue table patterns

---

### Task Group 4: Analytics & Top Users (Analytics Tab)
**Dependencies:** Task Group 1

- [ ] 4.0 Complete analytics and top users migration
  - [ ] 4.1 Migrate metric selector dropdown
    - Current: Standard select with gray background
    - Target: Styled native select with glassmorphism
    - Classes: `bg-white/5 border border-white/20 rounded-lg text-white focus:ring-2 focus:ring-purple-500`
    - Options: Add `className="bg-gray-800"` to each option
    - Keep native select (custom select out of scope)
  - [ ] 4.2 Migrate top users list container
    - Replace: `bg-gray-800 border-gray-700` → `<GlassCard className="p-6">`
    - Header icon: `text-purple-400` (already correct)
    - Header text: `text-white` (already correct)
  - [ ] 4.3 Update top users list items
    - Current: `bg-gray-700/50 hover:bg-gray-700`
    - Target: `bg-white/5 rounded-lg hover:bg-white/10 transition-colors`
    - Rank number: `text-purple-400` (keep)
    - Username: `text-white` (keep)
    - Email: `text-gray-400` (update from text-gray-400)
    - Value display: `text-gray-300`
  - [ ] 4.4 Verify metric switching works
    - Test all 4 metrics: tokens, masterplans, storage, api_calls
    - Ensure list updates correctly
    - Check value formatting for each metric type

**Acceptance Criteria:**
- Metric selector uses glassmorphism styling
- Top users container uses GlassCard
- List items use glassmorphism hover effects
- Color scheme consistent (purple rank, white username, gray email)
- All 4 metrics switch correctly
- Visual consistency with other card-based lists

---

### Task Group 5: Modals & Forms
**Dependencies:** Task Groups 1-4

- [ ] 5.0 Complete modals and forms migration
  - [ ] 5.1 Migrate UserEditModal structure
    - Backdrop: `fixed inset-0 bg-black/50 backdrop-blur-sm z-50`
    - Click handler: `onClick={() => setSelectedUser(null)}`
    - Container: `<GlassCard className="max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">`
    - Stop propagation: `onClick={(e) => e.stopPropagation()}`
  - [ ] 5.2 Update UserEditModal sections
    - Header: `border-b border-white/10 p-6`
    - Title: `text-2xl font-bold text-white`
    - Close button: `text-gray-400 hover:text-white transition-colors`
    - Content: `p-6 space-y-4`
    - Footer: `border-t border-white/10 p-6 flex justify-end gap-4`
  - [ ] 5.3 Migrate form inputs in UserEditModal
    - Email input: `<GlassInput type="email" value={...} onChange={...} />`
    - Username input: `<GlassInput type="text" value={...} onChange={...} />`
    - Quota inputs: `<GlassInput type="number" value={...} onChange={...} />` (4 quotas)
    - Checkboxes: Style with glassmorphism colors
      - Classes: `text-purple-600 bg-white/10 border-white/20 rounded focus:ring-2 focus:ring-purple-500`
      - Keep native checkbox (custom checkbox out of scope)
  - [ ] 5.4 Migrate form buttons in UserEditModal
    - Cancel: `<GlassButton variant="ghost" onClick={() => setSelectedUser(null)}>Cancel</GlassButton>`
    - Save: `<GlassButton variant="primary" onClick={handleUpdateUser}>Save Changes</GlassButton>`
  - [ ] 5.5 Migrate DeleteConfirmModal
    - Same pattern as UserEditModal but smaller
    - Container: `max-w-md` instead of `max-w-2xl`
    - Danger button: `<GlassButton variant="primary" className="bg-red-600 hover:bg-red-700">Delete User</GlassButton>`
  - [ ] 5.6 Migrate loading and error states
    - Loading: Replace spinner with `<LoadingState />`
    - Error: Replace error div with `<CustomAlert severity="error" message={error} />`
    - Success: Add `<CustomAlert severity="success" message={success} onClose={...} />`
    - Location: Above content sections, after header

**Acceptance Criteria:**
- Both modals use backdrop blur effect
- Modal containers use GlassCard with correct max-width
- Click outside to close works correctly
- All form inputs use GlassInput component (7 inputs)
- Checkboxes use glassmorphism colors
- Cancel/Save buttons use GlassButton
- Delete button has red danger styling
- LoadingState component replaces spinner
- CustomAlert component replaces error/success divs
- Visual consistency with ReviewActions modals

---

### Task Group 6: Quality Assurance & Testing
**Dependencies:** Task Groups 1-5

- [ ] 6.0 Complete QA and testing
  - [ ] 6.1 Visual QA checklist
    - [ ] Compare with MasterplansPage for gradient background
    - [ ] Compare with ReviewQueue for table styling
    - [ ] Compare with CodeDiffViewer for tab navigation
    - [ ] Verify glassmorphism effects consistent (backdrop-blur-lg, bg-white/5)
    - [ ] Check purple accent colors (#a855f7, bg-purple-600)
    - [ ] Verify dark theme consistency (no light mode artifacts)
    - [ ] Check all StatusBadges use correct colors
    - [ ] Verify all GlassButtons have consistent styling
  - [ ] 6.2 Functional testing
    - [ ] Test Overview tab: Stats cards display correctly
    - [ ] Test Users tab: Search, table, pagination work
    - [ ] Test Analytics tab: Metric selector and top users work
    - [ ] Test UserEditModal: Open, edit fields, save, cancel
    - [ ] Test DeleteConfirmModal: Open, confirm, cancel
    - [ ] Test all user CRUD operations work correctly
    - [ ] Test quota updates work correctly
    - [ ] Test error handling displays CustomAlert
    - [ ] Test loading state displays LoadingState
  - [ ] 6.3 Responsive testing
    - [ ] Desktop (>1024px): 4-column grid, full table
    - [ ] Tablet (768-1024px): 2-column grid, responsive table
    - [ ] Mobile (<768px): 1-column grid, mobile table
    - [ ] Modals: Test responsiveness with mx-4 margin
  - [ ] 6.4 Build verification
    - [ ] Run TypeScript compilation: `npm run build` in src/ui/
    - [ ] Verify 0 TypeScript errors
    - [ ] Verify 0 console errors
    - [ ] Check bundle size (should be similar or smaller)
  - [ ] 6.5 Browser testing
    - [ ] Chrome/Edge: Primary testing target
    - [ ] Firefox: Secondary validation
    - [ ] Test glassmorphism effects render correctly
    - [ ] Test backdrop-blur performance
  - [ ] 6.6 Update documentation
    - [ ] Create INTEGRATION_GUIDE.md with:
      - Migration patterns used
      - Before/after examples
      - Common gotchas and solutions
      - Future phase reference patterns
      - Visual QA results
      - Testing scenarios covered

**Acceptance Criteria:**
- Visual appearance 100% consistent with MasterplansPage and ReviewQueue
- All 3 tabs work correctly (Overview, Users, Analytics)
- All modals work correctly (UserEdit, DeleteConfirm)
- All CRUD operations functional
- Build succeeds with 0 errors
- Responsive on desktop, tablet, mobile
- Browser compatibility validated
- Documentation created with migration patterns

---

## Execution Order

Recommended implementation sequence:
1. **Page Structure** (Task Group 1) - Foundation for all other changes
2. **Stats Cards** (Task Group 2) - Independent, can be done early
3. **Users Table** (Task Group 3) - Most complex table migration
4. **Analytics** (Task Group 4) - Similar patterns to Task Group 2 & 3
5. **Modals** (Task Group 5) - Depends on understanding all form patterns
6. **QA & Testing** (Task Group 6) - Final validation and documentation

---

## Notes

**Reference Files:**
- Design system: `src/ui/src/components/design-system/`
- Review components: `src/ui/src/components/review/` (CustomAlert)
- Phase 1 reference: `agent-os/specs/2025-10-24-ui-design-system/`
- Phase 2a reference: `agent-os/specs/2025-10-24-review-queue-redesign/`
- Phase 2b reference: `agent-os/specs/2025-10-24-review-components-migration/`
- Current workflow: `agent-os/workflows/ui-unification-design.md`

**Design Patterns:**
- All containers → GlassCard
- All buttons → GlassButton
- All badges → StatusBadge
- All inputs → GlassInput
- Search bars → SearchBar component
- Loading → LoadingState component
- Errors/Success → CustomAlert component
- Consistent spacing: p-6, gap-6, space-y-6
- Consistent borders: border-white/10
- Consistent hover: hover:bg-white/5 or hover:bg-white/10

**Icon Library:**
- Use react-icons/fi (Feather Icons) - already imported
- Consistent sizes: 16 (small), 20 (medium), 24 (large)

**Color Scheme:**
- Purple accent: #a855f7 (bg-purple-600)
- Active states: bg-purple-600 text-white
- Inactive states: text-gray-400 hover:text-white
- Icon containers: bg-{color}-500/20 with backdrop-blur-sm
- Status: emerald (success), red (error), amber (warning), blue (info)

**Glassmorphism Patterns:**
- Cards: backdrop-blur-lg bg-white/5 border-white/10
- Hover: hover:bg-white/10 transition-colors
- Active: bg-white/20
- Gradients: from-gray-900 via-purple-900/20 to-blue-900/20

**Success Metrics:**
- ~40-50 replacements across AdminDashboardPage.tsx
- Zero TypeScript errors
- Visual consistency 100%
- All functionality preserved
- Build succeeds
- Responsive design validated
