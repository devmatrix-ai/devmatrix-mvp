# Specification: Admin Dashboard Glassmorphism Redesign

## Goal
Complete Phase 3 of UI unification by migrating the Admin Dashboard page from dark theme with standard borders to the glassmorphism design system, achieving 100% visual consistency with MasterplansPage and ReviewQueue.

## User Stories
- As an admin, I want consistent glassmorphism styling across all dashboard sections (Overview, Users, Analytics)
- As a developer, I want the admin page to follow the same design patterns as other migrated pages for visual coherence
- As an admin, I want all interactive elements (stats cards, tables, modals) to match the established aesthetic
- As a user, I want all existing functionality preserved (user management, analytics, quota updates)

## Core Requirements

**Page Structure:**

1. **AdminDashboardPage.tsx** (672 lines - Pure Tailwind CSS)
   - Current: Dark theme with `bg-gray-800`, `border-gray-700`
   - Target: Glassmorphism with gradient background, GlassCard components
   - 3 tabs: Overview, Users, Analytics
   - 2 modals: UserEditModal, DeleteConfirmModal
   - ~30-35 elements needing glassmorphism conversion

**Tab Sections:**

- **Overview Tab**: 4 stats cards (Users, Active Conversations, Storage, API Calls)
- **Users Tab**: Search bar, users table with pagination, inline actions
- **Analytics Tab**: Top users metric selector, top users list

## Technical Approach

### Migration Strategy
```
Page Structure (Background + Header + Tabs)
  ↓ (foundation)
Stats Cards (Overview Tab - 4 cards)
  ↓ (independent)
Search Bar & Users Table (Users Tab)
  ↓ (independent)
Analytics Charts (Analytics Tab - Top Users)
  ↓ (depends on tables pattern)
Modals (UserEditModal + DeleteConfirmModal)
  ↓ (final integration)
Visual QA & Testing
```

### Component Specifications

#### 1. Page Background & Header

**File:** `src/ui/src/pages/AdminDashboardPage.tsx`

**Current Structure:**
```tsx
<div className="flex-1 p-8 overflow-auto">
  <div className="max-w-7xl mx-auto space-y-6">
    <h1 className="text-4xl font-bold text-white dark:text-white mb-8">
      Admin Dashboard
    </h1>

    {/* Tabs */}
    <div className="border-b border-gray-200 dark:border-gray-700">
      <nav className="flex space-x-8">
        <button className={/* tab styles */}>
          Overview
        </button>
      </nav>
    </div>
  </div>
</div>
```

**Target Design System:**
```tsx
<div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
  <div className="max-w-7xl mx-auto space-y-6">
    {/* Page Header with Emoji */}
    <PageHeader emoji="🛡️" title="Admin Dashboard" />

    {/* Tabs with Glassmorphism */}
    <div className="flex gap-2 border-b border-white/10 pb-2">
      <button
        className={cn(
          'px-4 py-2 rounded-t-lg font-medium text-sm transition-all',
          activeTab === 'overview'
            ? 'bg-purple-600 text-white'
            : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
        onClick={() => setActiveTab('overview')}
      >
        Overview
      </button>
      {/* ... other tabs */}
    </div>
  </div>
</div>
```

**Tab Styling Pattern:**
- Active tab: `bg-purple-600 text-white` (matching CodeDiffViewer tabs)
- Inactive tab: `text-gray-400 hover:text-white hover:bg-white/10`
- Container: `border-b border-white/10`

#### 2. Stats Cards (Overview Tab)

**Current Pattern:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Users</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_users}</p>
      </div>
      <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
        <FiUsers className="text-blue-600 dark:text-blue-400" size={24} />
      </div>
    </div>
  </div>
</div>
```

**Target Design System:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  <GlassCard className="p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-300">Total Users</p>
        <p className="text-2xl font-bold text-white">{stats.total_users}</p>
      </div>
      <div className="p-2 bg-blue-500/20 rounded-lg backdrop-blur-sm">
        <FiUsers className="text-blue-400" size={24} />
      </div>
    </div>
  </GlassCard>
</div>
```

**Icon Container Pattern:**
- Users: `bg-blue-500/20`, `text-blue-400`
- Activity: `bg-emerald-500/20`, `text-emerald-400`
- Database: `bg-purple-500/20`, `text-purple-400`
- CPU: `bg-amber-500/20`, `text-amber-400`

#### 3. Search Bar (Users Tab)

**Current Pattern:**
```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
  <div className="relative">
    <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
    <input
      type="text"
      placeholder="Search by email or username..."
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
      className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
    />
  </div>
</div>
```

**Target Design System:**
```tsx
<GlassCard className="p-4">
  <SearchBar
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    placeholder="Search by email or username..."
  />
</GlassCard>
```

#### 4. Users Table

**Current Pattern:**
```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
    <thead className="bg-gray-50 dark:bg-gray-700">
      <tr>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
          Email
        </th>
      </tr>
    </thead>
    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
      <tr className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
        <td className="px-6 py-4 whitespace-nowrap">
          <div className="text-sm text-gray-900 dark:text-white">{user.email}</div>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**Target Design System:**
```tsx
<GlassCard className="overflow-hidden">
  <table className="w-full">
    <thead className="bg-white/5 border-b border-white/10">
      <tr>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
          Email
        </th>
      </tr>
    </thead>
    <tbody className="divide-y divide-white/10">
      <tr className="hover:bg-white/5 transition-colors">
        <td className="px-6 py-4 whitespace-nowrap">
          <div className="text-sm text-white">{user.email}</div>
        </td>
      </tr>
    </tbody>
  </table>
</GlassCard>
```

**Table Styling:**
- Header: `bg-white/5 border-b border-white/10`
- Rows: `divide-y divide-white/10`
- Hover: `hover:bg-white/5 transition-colors`
- Text: `text-white` (primary), `text-gray-300` (secondary), `text-gray-400` (tertiary)

#### 5. Status Badges

**Current Pattern:**
```tsx
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">
  Active
</span>
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200">
  ✓ Verified
</span>
```

**Target Design System:**
```tsx
<StatusBadge status="success">Active</StatusBadge>
<StatusBadge status="default">Inactive</StatusBadge>
<StatusBadge status="info">✓ Verified</StatusBadge>
```

**Status Mapping:**
- Active: `status="success"` (emerald)
- Inactive: `status="default"` (gray)
- Verified: `status="info"` (blue)
- Superuser: `status="warning"` (amber)

#### 6. Action Buttons

**Current Patterns:**
```tsx
{/* Primary Actions */}
<button className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors">
  Save Changes
</button>

{/* Secondary Actions */}
<button className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors">
  Cancel
</button>

{/* Icon Buttons */}
<button className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors">
  <FiEdit2 size={16} />
</button>

{/* Danger Actions */}
<button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors">
  Delete User
</button>
```

**Target Design System:**
```tsx
{/* Primary Actions */}
<GlassButton variant="primary">Save Changes</GlassButton>

{/* Secondary Actions */}
<GlassButton variant="ghost">Cancel</GlassButton>

{/* Icon Buttons */}
<GlassButton variant="ghost" size="sm">
  <FiEdit2 size={16} />
</GlassButton>

{/* Danger Actions */}
<GlassButton variant="primary" className="bg-red-600 hover:bg-red-700">
  Delete User
</GlassButton>
```

#### 7. Form Inputs

**Current Patterns:**
```tsx
{/* Text Inputs */}
<input
  type="text"
  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
/>

{/* Number Inputs (Quotas) */}
<input
  type="number"
  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
/>

{/* Checkboxes */}
<input type="checkbox" className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500" />
```

**Target Design System:**
```tsx
{/* Text Inputs */}
<GlassInput type="text" value={email} onChange={(e) => setEmail(e.target.value)} />

{/* Number Inputs (Quotas) */}
<GlassInput type="number" value={quota} onChange={(e) => setQuota(e.target.value)} />

{/* Checkboxes - Keep Native (too complex for scope) */}
<input
  type="checkbox"
  className="w-4 h-4 text-purple-600 bg-white/10 border-white/20 rounded focus:ring-2 focus:ring-purple-500"
/>
```

**Note:** Checkboxes maintain native styling with glassmorphism colors to reduce scope complexity.

#### 8. Select Dropdown (Metric Selector)

**Current Pattern:**
```tsx
<select
  value={topUsersMetric}
  onChange={(e) => setTopUsersMetric(e.target.value as any)}
  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
>
  <option value="tokens">By Tokens</option>
  <option value="masterplans">By Masterplans</option>
  <option value="storage">By Storage</option>
  <option value="api_calls">By API Calls</option>
</select>
```

**Target Design System:**
```tsx
<select
  value={topUsersMetric}
  onChange={(e) => setTopUsersMetric(e.target.value as any)}
  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
>
  <option value="tokens" className="bg-gray-800">By Tokens</option>
  <option value="masterplans" className="bg-gray-800">By Masterplans</option>
  <option value="storage" className="bg-gray-800">By Storage</option>
  <option value="api_calls" className="bg-gray-800">By API Calls</option>
</select>
```

**Note:** Using styled native select with glassmorphism pattern. Custom select component out of scope.

#### 9. Modals

**Current Pattern (UserEditModal):**
```tsx
{selectedUser && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
      <div className="border-b border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Edit User
          </h2>
          <button onClick={() => setSelectedUser(null)}>
            <FiX size={24} />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Form fields */}
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 p-6 flex justify-end gap-4">
        <button>Cancel</button>
        <button>Save Changes</button>
      </div>
    </div>
  </div>
)}
```

**Target Design System:**
```tsx
{selectedUser && (
  <div
    className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
    onClick={() => setSelectedUser(null)}
  >
    <GlassCard
      className="max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="border-b border-white/10 p-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Edit User</h2>
        <button
          onClick={() => setSelectedUser(null)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <FiX size={24} />
        </button>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        {/* Form fields with GlassInput */}
      </div>

      {/* Footer */}
      <div className="border-t border-white/10 p-6 flex justify-end gap-4">
        <GlassButton variant="ghost" onClick={() => setSelectedUser(null)}>
          Cancel
        </GlassButton>
        <GlassButton variant="primary" onClick={handleUpdateUser}>
          Save Changes
        </GlassButton>
      </div>
    </GlassCard>
  </div>
)}
```

**Modal Pattern:**
- Backdrop: `bg-black/50 backdrop-blur-sm`
- Container: GlassCard with `max-w-2xl` (edit) or `max-w-md` (delete confirm)
- Click outside to close: `onClick` on backdrop + `stopPropagation` on card
- Sections: Header (border-b), Content (p-6), Footer (border-t)

**DeleteConfirmModal Pattern:**
Same structure but smaller (`max-w-md`) with danger button styling.

#### 10. Top Users List (Analytics Tab)

**Current Pattern:**
```tsx
<div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
  <div className="flex items-center gap-2 mb-4">
    <FiTrendingUp className="text-purple-600 dark:text-purple-400" />
    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
      Top Users by {topUsersMetric}
    </h2>
  </div>

  <div className="space-y-3">
    {topUsers.map((user, index) => (
      <div key={user.user_id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            #{index + 1}
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{user.username}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
          </div>
        </div>
      </div>
    ))}
  </div>
</div>
```

**Target Design System:**
```tsx
<GlassCard className="p-6">
  <div className="flex items-center gap-2 mb-4">
    <FiTrendingUp className="text-purple-400" />
    <h2 className="text-xl font-bold text-white">
      Top Users by {topUsersMetric}
    </h2>
  </div>

  <div className="space-y-3">
    {topUsers.map((user, index) => (
      <div
        key={user.user_id}
        className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
      >
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-purple-400">
            #{index + 1}
          </span>
          <div>
            <p className="font-medium text-white">{user.username}</p>
            <p className="text-sm text-gray-400">{user.email}</p>
          </div>
        </div>
        {/* Value display */}
      </div>
    ))}
  </div>
</GlassCard>
```

#### 11. Loading State

**Current Pattern:**
```tsx
{isLoading && (
  <div className="flex justify-center py-12">
    <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
  </div>
)}
```

**Target Design System:**
```tsx
{isLoading && <LoadingState />}
```

#### 12. Error Display

**Current Pattern:**
```tsx
{error && (
  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
    <div className="flex items-center gap-2">
      <FiAlertCircle className="text-red-600 dark:text-red-400" />
      <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
    </div>
  </div>
)}
```

**Target Design System:**
```tsx
{error && <CustomAlert severity="error" message={error} />}
```

#### 13. Pagination Buttons

**Current Pattern:**
```tsx
<div className="flex items-center justify-between mt-6">
  <button
    disabled={currentPage === 1}
    className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
  >
    Previous
  </button>

  <span className="text-sm text-gray-600 dark:text-gray-400">
    Page {currentPage} of {Math.ceil(totalUsers / pageSize)}
  </span>

  <button
    disabled={currentPage >= Math.ceil(totalUsers / pageSize)}
    className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
  >
    Next
  </button>
</div>
```

**Target Design System:**
```tsx
<div className="flex items-center justify-between mt-6">
  <GlassButton
    variant="ghost"
    disabled={currentPage === 1}
    onClick={() => setCurrentPage(currentPage - 1)}
  >
    Previous
  </GlassButton>

  <span className="text-sm text-gray-400">
    Page {currentPage} of {Math.ceil(totalUsers / pageSize)}
  </span>

  <GlassButton
    variant="ghost"
    disabled={currentPage >= Math.ceil(totalUsers / pageSize)}
    onClick={() => setCurrentPage(currentPage + 1)}
  >
    Next
  </GlassButton>
</div>
```

## Reusable Components

### From Design System (Already Available)
- **GlassCard** - Container with glassmorphism effect
- **GlassButton** - Buttons with purple glow (variants: primary, ghost)
- **GlassInput** - Form inputs (supports multiline from Phase 2b)
- **SearchBar** - Pre-configured search input with icon
- **StatusBadge** - Status indicators (success, error, warning, info, default)
- **PageHeader** - Page title with emoji
- **LoadingState** - Loading spinner with message
- **cn()** - className utility for conditional styling

### From Review Components (Phase 2b)
- **CustomAlert** - Alert with severity colors and optional close button

### Design System Only (No New Components Needed)
All required components already exist from Phase 1 and Phase 2b. No new components need to be created.

## Visual Design

### Background Gradient
```tsx
className="bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20"
```

### Container Structure
```tsx
<div className="max-w-7xl mx-auto space-y-6">
```

### Consistent Spacing
- Cards: `p-6`
- Gaps: `gap-6` (grids), `space-y-6` (stacks), `gap-2` (buttons)
- Borders: `border-white/10` (dividers)

### Color Scheme
- **Purple accent**: `bg-purple-600`, `text-purple-400`, `border-purple-500/50`
- **Status colors**: emerald (active), gray (inactive), blue (verified), amber (superuser)
- **Hover effects**: `hover:bg-white/10`, `hover:bg-white/5`
- **Text hierarchy**: `text-white` (headings), `text-gray-300` (primary), `text-gray-400` (secondary), `text-gray-500` (tertiary)

## Migration Summary

### Elements to Replace

**Replacements by Type:**
1. Background: Add gradient → 1 replacement
2. Header: PageHeader with emoji → 1 replacement
3. Tabs: Custom glassmorphism tabs → 1 replacement
4. Stats cards: GlassCard → 4 replacements
5. Search bar: SearchBar in GlassCard → 1 replacement
6. Users table: GlassCard container → 1 replacement
7. Status badges: StatusBadge → 3-4 replacements
8. Buttons: GlassButton → ~10 replacements
9. Inputs: GlassInput → ~8 replacements
10. Select: Styled native select → 1 replacement
11. Modals: GlassCard with backdrop blur → 2 replacements
12. Loading: LoadingState → 1 replacement
13. Error: CustomAlert → 1 replacement
14. Top users list: GlassCard → 1 replacement
15. Pagination: GlassButton → 2 replacements

**Total: ~40-50 replacements in AdminDashboardPage.tsx**

### Import Changes

**Remove (None - No Material-UI):**
- No Material-UI imports to remove

**Add:**
```tsx
import {
  GlassCard,
  GlassButton,
  GlassInput,
  SearchBar,
  StatusBadge,
  PageHeader,
  LoadingState,
} from '../components/design-system'
import { CustomAlert } from '../components/review/CustomAlert'
import { cn } from '../lib/utils'
```

**Keep:**
```tsx
import { FiUsers, FiActivity, FiDatabase, FiCpu, FiSearch, FiEdit2, FiTrash2, FiX, FiCheck, FiAlertCircle, FiTrendingUp } from 'react-icons/fi'
```

## Out of Scope

- Changes to adminService.ts logic
- Changes to API calls or data fetching
- New features beyond current functionality
- Other pages migration (Phase 4+)
- Changes to routing
- Custom select component (using styled native select)
- Custom checkbox component (using styled native checkbox)

## Success Criteria

- Gradient background applied to entire page
- All cards converted to GlassCard components
- All buttons converted to GlassButton components
- Search bar uses SearchBar component
- Status badges use StatusBadge component
- Tab navigation styled with glassmorphism (purple active, gray hover)
- Modals use backdrop blur pattern with GlassCard
- All inputs use GlassInput component
- Loading state uses LoadingState component
- Error display uses CustomAlert component
- 100% visual consistency with MasterplansPage and ReviewQueue
- No TypeScript errors
- No console errors or warnings
- All functionality preserved (user management, quotas, analytics)
- Build succeeds
- Page responsive on desktop, tablet, mobile

## Implementation Notes

**Preservation Requirements:**
- All tab functionality (Overview, Users, Analytics)
- All user management operations (edit, delete, quota updates)
- All form validation and error handling
- All pagination logic
- All search and filtering functionality
- All API calls and state management

**Testing Strategy:**
- Visual QA: Compare with MasterplansPage and ReviewQueue for consistency
- Functional testing: Test all tabs, modals, forms, and user operations
- Responsive testing: Verify layout on desktop, tablet, mobile
- Dark mode: Ensure glassmorphism works correctly (already dark theme only)
- Browser testing: Chrome/Edge primary target

**Performance Considerations:**
- No performance impact expected (CSS-only changes)
- Glassmorphism uses GPU-accelerated backdrop-filter
- No new JavaScript, only styling changes
- Same component structure, different visual presentation

**Accessibility:**
- Preserve all existing ARIA labels
- Maintain keyboard navigation
- Ensure color contrast meets WCAG standards (purple on dark background)
- Focus management in modals preserved
- Form labels and error messages maintained
