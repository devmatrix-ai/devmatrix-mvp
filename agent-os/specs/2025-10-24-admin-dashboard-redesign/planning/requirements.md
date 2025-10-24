# Spec Requirements: Admin Dashboard Redesign

## Initial Description
Migrate the Admin Dashboard page from dark theme with standard borders to the glassmorphism design system. This is Phase 3 of the UI unification project.

## Requirements Discussion

### Component Analysis

**Current State:**
AdminDashboardPage.tsx (672 lines) uses pure Tailwind CSS with dark mode:
- No Material-UI or other UI libraries
- React Icons (Feather Icons) already in use
- 3 tabs: Overview, Users, Analytics
- 2 modals: UserEditModal, DeleteConfirmModal
- Standard dark theme styling: `bg-gray-800`, `border-gray-700`
- ~30-35 elements need glassmorphism conversion

**Target State:**
- Replace all `bg-gray-800 border-gray-700` with glassmorphism
- Use design system components (GlassCard, GlassButton, GlassInput, SearchBar, StatusBadge)
- Add gradient background
- Add emoji to header
- Purple accent colors for interactive elements
- 100% visual consistency with MasterplansPage and ReviewQueue

### Existing Code to Reference

**Design System Components Available:**
- GlassCard - For all containers
- GlassButton - For all buttons
- GlassInput - For all inputs (including SearchBar)
- SearchBar - Pre-configured search input
- StatusBadge - For status indicators
- PageHeader - For page title with emoji
- LoadingState - For loading spinners
- CustomAlert - For error messages

**Similar Patterns:**
- ReviewQueue page - Card-based layout, search bar, filters
- MasterplansPage - Reference for visual consistency

## Requirements Summary

### Functional Requirements

**Must Preserve All Current Functionality:**
- Tab navigation (Overview, Users, Analytics)
- Stats cards display (4 metrics)
- User table with search and pagination
- Top users analytics with metric selector
- User editing modal
- User deletion confirm modal
- All API calls and state management
- Loading and error states

### UI Components to Migrate

**Categorized by type:**

#### 1. Page Structure
- **Background**: Add gradient `bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20`
- **Header**: Replace with PageHeader component (emoji: 🛡️)
- **Tabs**: Style with glassmorphism (active: purple, inactive: gray hover)

#### 2. Stats Cards (Overview Tab - 4 cards)
Current:
```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
```

Target:
```tsx
<GlassCard className="p-6">
```

Icon containers need glassmorphism too:
```tsx
// Before
<div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">

// After
<div className="p-2 bg-blue-500/20 rounded-lg backdrop-blur-sm">
```

#### 3. Search Bar (Users Tab)
Current:
```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
  <div className="relative">
    <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
    <input ... />
  </div>
</div>
```

Target:
```tsx
<GlassCard className="p-4">
  <SearchBar value={searchQuery} onChange={...} placeholder="Search by email or username..." />
</GlassCard>
```

#### 4. Users Table
Current: Standard table with `bg-gray-800` container and `bg-gray-700` header

Target:
```tsx
<GlassCard className="overflow-hidden">
  <table className="w-full">
    <thead className="bg-white/5 border-b border-white/10">
      {/* ... */}
    </thead>
    <tbody className="divide-y divide-white/10">
      <tr className="hover:bg-white/5 transition-colors">
        {/* ... */}
      </tr>
    </tbody>
  </table>
</GlassCard>
```

#### 5. Status Badges
Current:
```tsx
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">
  Active
</span>
```

Target:
```tsx
<StatusBadge status="success">Active</StatusBadge>
<StatusBadge status="default">Inactive</StatusBadge>
<StatusBadge status="info">Verified</StatusBadge>
```

#### 6. Buttons
Current (multiple patterns for primary, secondary, danger):
```tsx
// Primary
className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"

// Secondary
className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg"

// Danger
className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
```

Target:
```tsx
<GlassButton variant="primary">Edit</GlassButton>
<GlassButton variant="ghost">Cancel</GlassButton>
<GlassButton variant="primary" className="bg-red-600 hover:bg-red-700">Delete</GlassButton>
```

#### 7. Inputs
Current:
```tsx
<input
  type="text"
  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
/>
```

Target:
```tsx
<GlassInput type="text" value={...} onChange={...} placeholder="..." />
```

For number inputs (quota management):
```tsx
<GlassInput type="number" value={...} onChange={...} />
```

#### 8. Select (Metric Selector)
Current:
```tsx
<select className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg">
```

Target: Create custom select with glassmorphism or style native select:
```tsx
<select className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500">
```

#### 9. Modals (2 modals)

**UserEditModal:**
Current:
```tsx
<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full">
```

Target:
```tsx
<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
  <GlassCard className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
```

**DeleteConfirmModal:**
Same pattern but smaller (max-w-md)

#### 10. Loading State
Current:
```tsx
<div className="flex justify-center py-12">
  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
</div>
```

Target:
```tsx
<LoadingState />
```

#### 11. Error Display
Current:
```tsx
<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
```

Target:
```tsx
<CustomAlert severity="error" message={error} />
```

#### 12. Top Users List (Analytics Tab)
Current: Cards with `bg-gray-800` and items with `bg-gray-700/50`

Target:
```tsx
<GlassCard className="p-6">
  <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
```

#### 13. Pagination Buttons
Current:
```tsx
<button className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg">
```

Target:
```tsx
<GlassButton variant="ghost" disabled={...}>Previous</GlassButton>
<GlassButton variant="ghost" disabled={...}>Next</GlassButton>
```

### Tab Navigation Styling

Current (standard Tailwind):
```tsx
<button
  className={`pb-4 border-b-2 font-medium transition-colors ${
    activeTab === 'overview'
      ? 'border-primary-600 text-primary-600'
      : 'border-transparent text-gray-500 hover:text-gray-700'
  }`}
>
```

Target (glassmorphism with purple):
```tsx
<button
  className={cn(
    'px-4 py-2 rounded-t-lg font-medium transition-all',
    activeTab === 'overview'
      ? 'bg-purple-600 text-white'
      : 'text-gray-400 hover:text-white hover:bg-white/10'
  )}
>
```

### Visual Design

**Background Gradient:**
```tsx
<div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
```

**Container:**
```tsx
<div className="max-w-7xl mx-auto space-y-6">
```

**Consistent Spacing:**
- Cards: `p-6` (already used)
- Gaps: `gap-6` for grids, `space-y-6` for stacks
- Borders: `border-white/10` for dividers

**Color Scheme:**
- Purple accent: `bg-purple-600`, `text-purple-400`
- Status colors: emerald (active), gray (inactive), blue (verified)
- Hover effects: `hover:bg-white/10`, `hover:bg-white/5`

### Component Summary

**Replacements needed:**
1. ~15 instances of `bg-gray-800 border-gray-700` → GlassCard
2. ~8 inputs → GlassInput
3. 1 search input → SearchBar
4. ~10 buttons → GlassButton
5. 3-4 status badges → StatusBadge
6. 1 loading spinner → LoadingState
7. 1 error display → CustomAlert
8. 2 modal overlays → add `backdrop-blur-sm`
9. 1 select → style with glassmorphism
10. 1 header → PageHeader with emoji

**Total estimated changes:** ~40-50 replacements in one file

### Scope Boundaries

**In Scope:**
- All visual styling in AdminDashboardPage.tsx
- Replace all standard borders with glassmorphism
- Use all design system components
- Add gradient background
- Add PageHeader with emoji
- Style all interactive elements
- Update all modals

**Out of Scope:**
- Changes to adminService.ts logic
- Changes to API calls or data fetching
- New features not in current page
- Other pages migration (Phase 4+)
- Changes to routing

### Technical Considerations

**Dependencies:**
- No new dependencies needed
- All design system components already available
- React Icons (Feather) already in use
- No Material-UI to remove

**Code Patterns:**
- Import design system components from `@/components/design-system`
- Import review components from `@/components/review` (CustomAlert)
- Use cn() utility for className merging
- Preserve all existing logic and state management

**Performance:**
- No performance impact expected
- Glassmorphism uses GPU-accelerated properties (backdrop-filter)
- No new JavaScript, only CSS changes

**Accessibility:**
- Preserve all ARIA labels
- Maintain keyboard navigation
- Ensure color contrast meets WCAG standards
- Focus management in modals

### Testing Strategy

- Visual QA: Compare with MasterplansPage and ReviewQueue
- Functional testing: All tabs, modals, forms must work
- Responsive testing: Desktop, tablet, mobile
- Dark mode: Verify glassmorphism works correctly
- Browser testing: Chrome/Edge primary

### Defaults Assumed

1. **Icon containers**: Use semi-transparent color backgrounds (e.g., `bg-blue-500/20`)
2. **Select styling**: Use glassmorphism pattern for native select
3. **Tab navigation**: Purple active, gray hover (consistent with CodeDiffViewer tabs)
4. **Error display**: CustomAlert with error severity
5. **Loading**: LoadingState component (centralized)
6. **Checkboxes**: Keep native styling (too complex for scope)
