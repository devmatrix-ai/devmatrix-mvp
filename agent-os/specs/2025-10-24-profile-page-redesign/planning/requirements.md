# Phase 4: Profile Page Redesign - Requirements Analysis

## File Overview
- **File**: `src/ui/src/pages/ProfilePage.tsx`
- **Total Lines**: 270 lines
- **Current State**: 100% Tailwind CSS (NO Material-UI)
- **Complexity**: Low-Medium

## Current Structure

### Page Layout
```
ProfilePage
├── Header (title + description)
├── Account Information Card
│   ├── Username field
│   ├── Email field (with "Verified" badge)
│   └── Member since field
└── Usage Statistics Section
    ├── Loading State
    ├── 4 Metric Cards
    │   ├── LLM Tokens (with progress bar)
    │   ├── Masterplans (with progress bar)
    │   ├── Storage (with progress bar)
    │   └── API Calls (rate limit info)
    └── Empty State
```

## Elements to Migrate (~20-25 replacements)

### 1. Background & Header (Lines 75-85)
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
    <PageHeader emoji="👤" title="Profile" subtitle="Manage your account and view usage statistics" />
```

### 2. Account Information Card (Lines 88-126)
**Current**: `bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6`

**Target**: `<GlassCard className="p-6">`

**Badge "Verified"** (Line 107):
- Current: `<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">`
- Target: `<StatusBadge status="success">✓ Verified</StatusBadge>`

### 3. Usage Statistics Container (Lines 129-265)
**Current**: `bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700`

**Target**: `<GlassCard>`

### 4. Loading State (Lines 134-141)
**Current**: Custom spinner with animations
```tsx
<div className="flex justify-center py-12">
  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
</div>
```

**Target**: `<LoadingState />`

### 5. Metric Cards (4 cards, ~25 lines each)

#### Pattern for each card:
**Current**:
```tsx
<div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
  <div className="flex items-center justify-between mb-3">
    <div className="flex items-center gap-2">
      <FiCpu className="text-primary-600 dark:text-primary-400" />
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">LLM Tokens</h3>
    </div>
  </div>
  <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
    {formatNumber(usage.current_month.llm_tokens_used)}
  </p>
  {usage.quota.llm_tokens_monthly_limit && (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
        <span>{calculatePercentage(...)}% used</span>
        <span>{formatNumber(usage.quota.llm_tokens_monthly_limit)} limit</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
        <div className="bg-primary-600 h-2 rounded-full transition-all" style={{ width: `${...}%` }}></div>
      </div>
    </div>
  )}
</div>
```

**Target**:
```tsx
<GlassCard className="p-4">
  <div className="flex items-center justify-between mb-3">
    <div className="flex items-center gap-2">
      <div className="p-2 bg-purple-500/20 backdrop-blur-sm rounded-lg">
        <FiCpu className="text-purple-400" size={20} />
      </div>
      <h3 className="text-sm font-medium text-gray-300">LLM Tokens</h3>
    </div>
  </div>
  <p className="text-2xl font-bold text-white mb-2">
    {formatNumber(usage.current_month.llm_tokens_used)}
  </p>
  {usage.quota.llm_tokens_monthly_limit && (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{calculatePercentage(...)}% used</span>
        <span>{formatNumber(usage.quota.llm_tokens_monthly_limit)} limit</span>
      </div>
      <div className="w-full bg-white/10 rounded-full h-2">
        <div className="bg-purple-500 h-2 rounded-full transition-all" style={{ width: `${...}%` }}></div>
      </div>
    </div>
  )}
</GlassCard>
```

### 6. Progress Bars (3 instances)
**Pattern**:
- Container: `bg-gray-200 dark:bg-gray-600` → `bg-white/10`
- Fill: `bg-primary-600` → Color-coded per metric
  - LLM Tokens: `bg-purple-500`
  - Masterplans: `bg-blue-500`
  - Storage: `bg-emerald-500`

### 7. Icon Containers (4 metric cards)
**Current**: Direct icon without container

**Target**: Glassmorphism icon container with backdrop blur
```tsx
<div className="p-2 bg-{color}-500/20 backdrop-blur-sm rounded-lg">
  <FiIcon className="text-{color}-400" size={20} />
</div>
```

Color mapping:
- LLM Tokens: purple
- Masterplans: blue
- Storage: emerald
- API Calls: amber

## Component Mappings

| Current Element | Target Component | Count |
|----------------|------------------|-------|
| `bg-white dark:bg-gray-800 rounded-lg border` | `<GlassCard>` | 2 |
| Custom header | `<PageHeader>` | 1 |
| Verified badge | `<StatusBadge status="success">` | 1 |
| Loading spinner | `<LoadingState />` | 1 |
| Metric cards | `<GlassCard>` with glassmorphic styling | 4 |
| Progress bars | Glassmorphic progress bars | 3 |
| Icon containers | Glassmorphic icon containers | 4 |
| Text colors | Updated to glassmorphism palette | ~10 |

## Visual Design Patterns

### Color Scheme
- **Background**: `bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20`
- **Primary text**: `text-white`
- **Secondary text**: `text-gray-300`
- **Tertiary text**: `text-gray-400`
- **Borders**: `border-white/10`

### Metric Colors
- **LLM Tokens**: Purple (`bg-purple-500/20`, `text-purple-400`, progress `bg-purple-500`)
- **Masterplans**: Blue (`bg-blue-500/20`, `text-blue-400`, progress `bg-blue-500`)
- **Storage**: Emerald (`bg-emerald-500/20`, `text-emerald-400`, progress `bg-emerald-500`)
- **API Calls**: Amber (`bg-amber-500/20`, `text-amber-400`)

### Spacing
- Page padding: `p-8`
- Card padding: `p-6` (main cards), `p-4` (metric cards)
- Section gap: `space-y-6`
- Grid gap: `gap-6`

## Out of Scope
- Changes to data fetching logic
- Changes to utility functions (formatBytes, formatNumber, calculatePercentage)
- Changes to API endpoints
- New features beyond current functionality
- Other pages migration (Phase 5+)

## Success Criteria
- Gradient background applied
- All cards use GlassCard component
- PageHeader component used
- StatusBadge for verified badge
- LoadingState for loading spinner
- All 4 metric cards with glassmorphism
- Progress bars with glassmorphism styling
- Icon containers with glassmorphism
- 100% visual consistency with Phases 1-3
- No TypeScript errors
- Build succeeds
- Responsive design maintained
