# Specification: Profile Page Glassmorphism Redesign

## Goal
Complete Phase 4 of UI unification by migrating the Profile Page to glassmorphism design system, achieving 100% visual consistency with MasterplansPage, ReviewQueue, and Admin Dashboard.

## User Stories
- As a user, I want consistent glassmorphism styling across my profile page
- As a developer, I want the profile page to follow the same design patterns as other migrated pages
- As a user, I want all my usage statistics displayed with the glassmorphism aesthetic
- As a user, I want all existing functionality preserved (usage data, quota limits, formatting)

## Core Requirements

**Page Structure**: ProfilePage.tsx (270 lines - Pure Tailwind CSS)
- Current: Dark theme with `bg-gray-800`, `border-gray-700`
- Target: Glassmorphism with gradient background, GlassCard components
- 2 main sections: Account Information + Usage Statistics
- 4 metric cards with progress bars
- 1 verified badge
- Loading and empty states
- ~20-25 elements needing glassmorphism conversion

## Technical Approach

### Migration Strategy
```
Background & Header (Foundation)
  ↓
Account Information Card
  ↓ (independent)
Usage Statistics Container
  ↓ (independent)
Metric Cards (4 cards with progress bars)
  ↓ (final styling)
Loading/Empty States
```

### Component Specifications

#### 1. Background & Page Header

**Current**:
```tsx
<div className="flex-1 p-8 overflow-auto">
  <div className="max-w-4xl mx-auto space-y-6">
    <div>
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Profile</h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Manage your account and view usage statistics
      </p>
    </div>
```

**Target**:
```tsx
<div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
  <div className="max-w-4xl mx-auto space-y-6">
    <PageHeader
      emoji="👤"
      title="Profile"
      subtitle="Manage your account and view usage statistics"
    />
```

#### 2. Account Information Card

**Current**: Standard dark card with border
**Target**: GlassCard with glassmorphism

```tsx
<GlassCard className="p-6">
  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
    <FiUser /> Account Information
  </h2>
  <div className="space-y-4">
    {/* Username */}
    <div className="flex items-start gap-3">
      <FiUser className="text-gray-400 mt-1" />
      <div>
        <p className="text-sm text-gray-400">Username</p>
        <p className="font-medium text-white">{user.username}</p>
      </div>
    </div>

    {/* Email with Verified Badge */}
    <div className="flex items-start gap-3">
      <FiMail className="text-gray-400 mt-1" />
      <div className="flex-1">
        <p className="text-sm text-gray-400">Email</p>
        <div className="flex items-center gap-2">
          <p className="font-medium text-white">{user.email}</p>
          {user.is_verified && (
            <StatusBadge status="success">✓ Verified</StatusBadge>
          )}
        </div>
      </div>
    </div>

    {/* Member Since */}
    <div className="flex items-start gap-3">
      <FiCalendar className="text-gray-400 mt-1" />
      <div>
        <p className="text-sm text-gray-400">Member Since</p>
        <p className="font-medium text-white">
          {new Date(user.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  </div>
</GlassCard>
```

**Changes**:
- Container: `bg-white dark:bg-gray-800 border` → `<GlassCard>`
- Title: `text-gray-900 dark:text-white` → `text-white`
- Labels: `text-gray-500 dark:text-gray-400` → `text-gray-400`
- Values: `text-gray-900 dark:text-white` → `text-white`
- Badge: Custom badge → `<StatusBadge status="success">`

#### 3. Usage Statistics Container

**Current**: Standard dark card
**Target**: GlassCard

```tsx
<GlassCard>
  <div className="border-b border-white/10 p-6">
    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
      <FiTrendingUp /> Usage Statistics
    </h2>
  </div>

  {isLoading ? (
    <div className="p-12">
      <LoadingState />
    </div>
  ) : usage ? (
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* 4 Metric Cards */}
    </div>
  ) : (
    <div className="p-12 text-center text-gray-400">
      No usage data available
    </div>
  )}
</GlassCard>
```

**Loading State**:
- Current: Custom spinner
- Target: `<LoadingState />`

**Empty State**:
- Current: `text-gray-600 dark:text-gray-400`
- Target: `text-gray-400` with GlassCard context

#### 4. Metric Cards (4 variations)

**Pattern for each metric**:

```tsx
<GlassCard className="p-4">
  {/* Header with Icon */}
  <div className="flex items-center justify-between mb-3">
    <div className="flex items-center gap-2">
      <div className="p-2 bg-{color}-500/20 backdrop-blur-sm rounded-lg">
        <FiIcon className="text-{color}-400" size={20} />
      </div>
      <h3 className="text-sm font-medium text-gray-300">Metric Name</h3>
    </div>
  </div>

  {/* Value */}
  <p className="text-2xl font-bold text-white mb-2">
    {formattedValue}
  </p>

  {/* Optional: Additional Info */}
  {additionalInfo && (
    <p className="text-xs text-gray-400">{additionalInfo}</p>
  )}

  {/* Optional: Progress Bar */}
  {hasQuota && (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{percentage}% used</span>
        <span>{formatNumber(limit)} limit</span>
      </div>
      <div className="w-full bg-white/10 rounded-full h-2">
        <div
          className="bg-{color}-500 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )}
</GlassCard>
```

**Metric-Specific Configurations**:

##### LLM Tokens Card
- Icon: `<FiCpu />` in `bg-purple-500/20` container
- Icon color: `text-purple-400`
- Progress bar: `bg-purple-500`
- Additional info: Cost in USD

##### Masterplans Card
- Icon: `<FiActivity />` in `bg-blue-500/20` container
- Icon color: `text-blue-400`
- Progress bar: `bg-blue-500`
- No additional info

##### Storage Card
- Icon: `<FiDatabase />` in `bg-emerald-500/20` container
- Icon color: `text-emerald-400`
- Progress bar: `bg-emerald-500`
- Value formatted with `formatBytes()`

##### API Calls Card
- Icon: `<FiActivity />` in `bg-amber-500/20` container
- Icon color: `text-amber-400`
- No progress bar
- Additional info: Rate limit per minute

#### 5. Progress Bar Pattern

**Current**:
```tsx
<div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
  <div
    className="bg-primary-600 h-2 rounded-full transition-all"
    style={{ width: `${percentage}%` }}
  />
</div>
```

**Target**:
```tsx
<div className="w-full bg-white/10 rounded-full h-2">
  <div
    className="bg-{color}-500 h-2 rounded-full transition-all"
    style={{ width: `${percentage}%` }}
  />
</div>
```

**Color Mapping**:
- LLM Tokens: `bg-purple-500`
- Masterplans: `bg-blue-500`
- Storage: `bg-emerald-500`

## Reusable Components

### From Design System (Already Available)
- **GlassCard** - Container with glassmorphism
- **PageHeader** - Page title with emoji
- **StatusBadge** - For verified badge
- **LoadingState** - Loading spinner
- **cn()** - className utility

### No New Components Needed
All required components already exist from Phases 1-3.

## Visual Design

### Background Gradient
```tsx
className="bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20"
```

### Container Structure
```tsx
<div className="max-w-4xl mx-auto space-y-6">
```

### Color Scheme
- **Purple accent**: LLM Tokens metric
- **Blue accent**: Masterplans metric
- **Emerald accent**: Storage metric
- **Amber accent**: API Calls metric
- **Text hierarchy**: `text-white` (primary), `text-gray-300` (secondary), `text-gray-400` (tertiary)

### Spacing
- Page: `p-8`
- Cards: `p-6` (main), `p-4` (metrics)
- Gaps: `space-y-6`, `gap-6`

## Migration Summary

### Elements to Replace (~20-25)

1. Background: Add gradient → 1 replacement
2. Header: PageHeader → 1 replacement
3. Account Info card: GlassCard → 1 replacement
4. Verified badge: StatusBadge → 1 replacement
5. Usage Stats container: GlassCard → 1 replacement
6. Loading state: LoadingState → 1 replacement
7. Metric cards: GlassCard → 4 replacements
8. Icon containers: Glassmorphic containers → 4 replacements
9. Progress bars: Glassmorphic styling → 3 replacements
10. Text colors: Update to glassmorphism → ~10 replacements

**Total: ~28 replacements in ProfilePage.tsx**

### Import Changes

**Add**:
```tsx
import {
  GlassCard,
  PageHeader,
  StatusBadge,
  LoadingState,
} from '../components/design-system'
import { cn } from '../lib/utils'
```

**Keep**:
```tsx
import { FiUser, FiMail, FiCalendar, FiActivity, FiCpu, FiDatabase, FiTrendingUp } from 'react-icons/fi'
```

## Out of Scope
- Changes to data fetching logic
- Changes to utility functions
- Changes to API endpoints
- New features beyond current functionality
- Other pages migration (Phase 5+)

## Success Criteria
- Gradient background applied to entire page
- All cards converted to GlassCard
- PageHeader used for page title
- StatusBadge used for verified badge
- LoadingState used for loading spinner
- All 4 metric cards with glassmorphism styling
- Progress bars with glassmorphism colors
- Icon containers with glassmorphism effect
- 100% visual consistency with Phases 1-3
- No TypeScript errors
- Build succeeds
- Responsive design maintained
- All functionality preserved

## Implementation Notes

**Order of Operations**:
1. Add gradient background and PageHeader
2. Migrate Account Information card
3. Update verified badge
4. Migrate Usage Statistics container
5. Update loading state
6. Migrate all 4 metric cards with progress bars
7. Verify responsiveness

**Testing Strategy**:
- Visual QA: Compare with Phases 1-3
- Functional testing: Verify usage data displays correctly
- Responsive testing: Desktop, tablet, mobile
- Dark mode: Ensure glassmorphism works (dark only)

**Performance Considerations**:
- No performance impact (CSS-only changes)
- Same component structure
- Glassmorphism uses GPU-accelerated backdrop-filter
