# Specification: Review Components Material-UI Migration

## Goal
Complete Phase 2 of UI unification by migrating the remaining 4 review components from Material-UI to the glassmorphism design system, achieving zero Material-UI dependencies in the entire review workflow.

## User Stories
- As a reviewer, I want consistent glassmorphism styling across all review components
- As a developer, I want zero Material-UI dependencies in review components for eventual library removal
- As a user, I want all interactive elements (buttons, dialogs, alerts) to match the MasterplansPage aesthetic
- As a reviewer, I want all existing functionality preserved (Monaco Editor, tabs, dialogs, suggestions)

## Core Requirements

**Components to Migrate (in order of complexity):**

1. **ConfidenceIndicator** (Simplest - 104 lines)
   - Visual confidence score with icon + label
   - Color-coded: green (high), amber (medium), red (low/critical)
   - Tooltip with confidence explanation
   - Used in: AISuggestionsPanel, ReviewCard

2. **ReviewActions** (Medium - 351 lines)
   - 4 action buttons: Approve, Reject, Edit Code, Regenerate
   - 3 dialogs with forms (reject feedback, edit code, regenerate instructions)
   - Form validation and API calls
   - Loading and error states

3. **AISuggestionsPanel** (Complex - 339 lines)
   - Confidence score display (uses ConfidenceIndicator)
   - AI recommendation alert
   - Issues summary with badges
   - Expandable issue details list
   - Alternatives accordion
   - Suggestions accordion

4. **CodeDiffViewer** (Most Complex - 265 lines)
   - Monaco Editor integration (KEEP - user wants syntax highlighting)
   - Tab navigation (Current Code / Diff View)
   - Code language badge
   - Copy button with tooltip
   - Issues count badge
   - Issues list below editor
   - Diff view with side-by-side editors

## Technical Approach

### Migration Order
```
ConfidenceIndicator (Day 1 - 1 hour)
  ↓ (no dependencies)
ReviewActions (Day 1 - 2 hours)
  ↓ (independent)
AISuggestionsPanel (Day 2 - 2 hours)
  ↓ (depends on ConfidenceIndicator)
CodeDiffViewer (Day 2 - 2 hours)
  ↓ (most complex)
Integration Testing (Day 2 - 1 hour)
```

### Component Specifications

#### 1. ConfidenceIndicator

**File:** `src/ui/src/components/review/ConfidenceIndicator.tsx`

**Current Material-UI:**
- Box, Tooltip, Typography
- Icons: CheckCircle, Warning, Error, Dangerous

**Target Design System:**
```typescript
interface ConfidenceIndicatorProps {
  score: number; // 0.0-1.0
  showLabel?: boolean;
  size?: 'small' | 'medium' | 'large';
}

// Visual structure
<div className="group relative flex items-center gap-2">
  {/* Icon - color-coded */}
  <FiCheckCircle size={iconSize} className="text-emerald-400" />

  {/* Label */}
  {showLabel && (
    <span className={cn(
      'font-bold',
      size === 'small' && 'text-xs',
      size === 'medium' && 'text-sm',
      size === 'large' && 'text-base'
    )} style={{ color: getColor() }}>
      {(score * 100).toFixed(0)}% ({getLevel()})
    </span>
  )}

  {/* Tooltip on hover */}
  <div className="absolute left-0 top-full mt-2 hidden group-hover:block z-50">
    <GlassCard className="px-3 py-2 text-xs whitespace-nowrap">
      {getTooltip()}
    </GlassCard>
  </div>
</div>
```

**Color Scheme:**
```typescript
high (≥0.85): text-emerald-400 (#10b981)
medium (0.70-0.84): text-amber-400 (#f59e0b)
low (0.50-0.69): text-orange-500 (#f97316)
critical (<0.50): text-red-500 (#ef4444)
```

**Icon Mapping:**
```typescript
high → FiCheckCircle
medium → FiAlertTriangle
low → FiAlertCircle
critical → FiAlertOctagon
```

#### 2. ReviewActions

**File:** `src/ui/src/components/review/ReviewActions.tsx`

**Current Material-UI:**
- Button, TextField, Dialog, Alert, CircularProgress

**Target Design System:**
```typescript
interface ReviewActionsProps {
  reviewId: string;
  atomId: string;
  currentCode: string;
  onActionComplete: () => void;
}

// Action Buttons
<div className="flex gap-2">
  <GlassButton variant="primary" onClick={handleApprove}>
    <FiCheckCircle className="mr-2" /> Approve
  </GlassButton>

  <GlassButton variant="ghost" onClick={() => setRejectDialogOpen(true)}>
    <FiXCircle className="mr-2 text-red-400" /> Reject
  </GlassButton>

  <GlassButton variant="ghost" onClick={() => setEditDialogOpen(true)}>
    <FiEdit2 className="mr-2" /> Edit Code
  </GlassButton>

  <GlassButton variant="ghost" onClick={() => setRegenerateDialogOpen(true)}>
    <FiRefreshCw className="mr-2 text-amber-400" /> Regenerate
  </GlassButton>
</div>

// Status Messages
{loading && <LoadingState message="Processing..." />}
{error && <CustomAlert severity="error" message={error} onClose={() => setError(null)} />}
{success && <CustomAlert severity="success" message={success} onClose={() => setSuccess(null)} />}

// Dialog Pattern (Reject Dialog example)
{rejectDialogOpen && (
  <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
       onClick={() => setRejectDialogOpen(false)}>
    <GlassCard className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
      {/* Header */}
      <div className="border-b border-white/10 p-4">
        <h3 className="text-lg font-bold text-white">Reject Atom</h3>
      </div>

      {/* Content */}
      <div className="p-4">
        <GlassInput
          multiline
          rows={4}
          placeholder="Explain why this code is being rejected..."
          value={rejectFeedback}
          onChange={(e) => setRejectFeedback(e.target.value)}
        />
      </div>

      {/* Actions */}
      <div className="border-t border-white/10 p-4 flex justify-end gap-2">
        <GlassButton variant="ghost" onClick={() => setRejectDialogOpen(false)}>
          Cancel
        </GlassButton>
        <GlassButton variant="primary" onClick={handleReject} disabled={loading}>
          Reject
        </GlassButton>
      </div>
    </GlassCard>
  </div>
)}
```

**New Component Needed:**
- **CustomAlert** - Alert with glassmorphism + colored border

```typescript
interface CustomAlertProps {
  severity: 'success' | 'error' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
}

<GlassCard className={cn(
  'border-l-4 p-4',
  severity === 'success' && 'border-emerald-500 bg-emerald-500/10',
  severity === 'error' && 'border-red-500 bg-red-500/10',
  severity === 'warning' && 'border-amber-500 bg-amber-500/10',
  severity === 'info' && 'border-blue-500 bg-blue-500/10'
)}>
  <div className="flex items-start gap-3">
    {getIcon(severity)}
    <p className="text-sm text-white flex-1">{message}</p>
    {onClose && (
      <button onClick={onClose} className="text-gray-400 hover:text-white">
        <FiX size={16} />
      </button>
    )}
  </div>
</GlassCard>
```

**GlassInput Enhancement Needed:**
```typescript
// Add multiline support
interface GlassInputProps {
  // ... existing props
  multiline?: boolean;
  rows?: number;
}

// In component
{multiline ? (
  <textarea
    ref={ref}
    rows={rows}
    className={cn(/* same styles */, 'resize-none')}
    {...props}
  />
) : (
  <input ref={ref} className={cn(/* styles */)} {...props} />
)}
```

#### 3. AISuggestionsPanel

**File:** `src/ui/src/components/review/AISuggestionsPanel.tsx`

**Current Material-UI:**
- Paper, Accordion, Chip, List, Alert, Button

**Target Design System:**
```typescript
interface AISuggestionsPanelProps {
  analysis: AIAnalysis;
  confidenceScore: number;
}

// Structure
<div className="flex flex-col gap-4 h-full">
  {/* Confidence Score */}
  <GlassCard className="p-4">
    <h4 className="text-sm font-medium text-gray-300 mb-2">Confidence Score</h4>
    <ConfidenceIndicator score={confidenceScore} size="large" />
  </GlassCard>

  {/* AI Recommendation */}
  <CustomAlert severity={getRecommendationSeverity()} message={analysis.recommendation} />

  {/* Issues Summary */}
  <GlassCard className="p-4">
    <div className="flex items-center gap-2 mb-3">
      <FiBug className="text-red-400" />
      <h4 className="text-sm font-medium text-white">Issues Detected ({analysis.total_issues})</h4>
    </div>

    <div className="flex gap-2 flex-wrap">
      {analysis.issues_by_severity.critical > 0 && (
        <StatusBadge status="error">{analysis.issues_by_severity.critical} Critical</StatusBadge>
      )}
      {/* ... other severity badges */}
    </div>
  </GlassCard>

  {/* Issue Details List */}
  <GlassCard className="flex-1 overflow-auto">
    <div className="border-b border-white/10 p-4">
      <h4 className="text-sm font-medium text-white">Issue Details</h4>
    </div>

    <div className="divide-y divide-white/10">
      {analysis.issues.map((issue, index) => (
        <div key={index} className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <StatusBadge status={getSeverityStatus(issue.severity)}>
              {issue.severity}
            </StatusBadge>
            <p className="text-sm font-medium text-white">{issue.description}</p>
          </div>
          <p className="text-xs text-gray-400 mb-2">{issue.explanation}</p>
          {issue.line_number && (
            <p className="text-xs text-gray-500">Line {issue.line_number}</p>
          )}
          {issue.code_snippet && (
            <pre className="mt-2 p-2 bg-black/30 rounded text-xs font-mono text-gray-300 overflow-x-auto">
              {issue.code_snippet}
            </pre>
          )}
        </div>
      ))}
    </div>
  </GlassCard>

  {/* Alternatives Accordion */}
  {analysis.alternatives?.length > 0 && (
    <CustomAccordion
      title={`Alternative Implementations (${analysis.alternatives.length})`}
      icon={<FiCode />}
    >
      <div className="divide-y divide-white/10">
        {analysis.alternatives.map((alt, index) => (
          <div key={index} className="p-4 flex justify-between items-start gap-4">
            <div className="flex-1">
              <p className="text-xs text-gray-400 mb-1">Alternative {index + 1}</p>
              <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">{alt}</pre>
            </div>
            <GlassButton
              variant="ghost"
              size="sm"
              onClick={() => handleCopyAlternative(alt, index)}
            >
              <FiCopy size={14} />
            </GlassButton>
          </div>
        ))}
      </div>
    </CustomAccordion>
  )}
</div>
```

**New Component Needed:**
- **CustomAccordion** - Expandable section with glassmorphism

```typescript
interface CustomAccordionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

<GlassCard className="overflow-hidden">
  <button
    onClick={() => setExpanded(!expanded)}
    className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
  >
    <div className="flex items-center gap-2">
      {icon}
      <span className="text-sm font-medium text-white">{title}</span>
    </div>
    <FiChevronDown className={cn(
      'text-gray-400 transition-transform',
      expanded && 'rotate-180'
    )} />
  </button>

  {expanded && (
    <div className="border-t border-white/10">
      {children}
    </div>
  )}
</GlassCard>
```

#### 4. CodeDiffViewer

**File:** `src/ui/src/components/review/CodeDiffViewer.tsx`

**Current Material-UI:**
- Paper, Tabs, Tab, Chip, Tooltip, IconButton, Alert

**Target Design System:**
```typescript
interface CodeDiffViewerProps {
  code: string;
  language: string;
  issues: Issue[];
  originalCode?: string;
}

// Structure
<GlassCard className="h-full flex flex-col">
  {/* Header */}
  <div className="border-b border-white/10 p-4">
    <div className="flex justify-between items-center">
      <h3 className="text-lg font-bold text-white">Code Review</h3>

      <div className="flex items-center gap-2">
        {/* Copy Button */}
        <GlassButton
          variant="ghost"
          size="sm"
          onClick={handleCopyCode}
          className="group"
        >
          <FiCopy size={16} />
          <span className="ml-2 text-xs">{copiedShown ? 'Copied!' : 'Copy'}</span>
        </GlassButton>

        {/* Issues Badge */}
        <StatusBadge status={issues.length > 0 ? 'error' : 'success'}>
          {issues.length} issues
        </StatusBadge>

        {/* Language Badge */}
        <StatusBadge status="default">{language}</StatusBadge>
      </div>
    </div>

    {/* Tabs (if diff view available) */}
    {originalCode && (
      <div className="flex gap-2 mt-4 border-b border-white/10">
        <button
          className={cn(
            'px-4 py-2 text-sm font-medium rounded-t-lg transition-all',
            activeTab === 'current'
              ? 'bg-purple-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-white/10'
          )}
          onClick={() => setActiveTab('current')}
        >
          Current Code
        </button>
        <button
          className={cn(
            'px-4 py-2 text-sm font-medium rounded-t-lg transition-all',
            activeTab === 'diff'
              ? 'bg-purple-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-white/10'
          )}
          onClick={() => setActiveTab('diff')}
        >
          Diff View
        </button>
      </div>
    )}
  </div>

  {/* Monaco Editor Section */}
  <div className="flex-1 overflow-auto">
    {activeTab === 'current' ? (
      <Editor
        height="100%"
        language={getMonacoLanguage(language)}
        value={code}
        theme="vs-dark"
        options={{/* existing options */}}
      />
    ) : (
      <div className="flex h-full">
        {/* Original Code */}
        <div className="flex-1 border-r border-white/10">
          <div className="bg-red-500/20 border-b border-white/10 px-4 py-2">
            <span className="text-xs text-red-200 font-medium">Original</span>
          </div>
          <Editor
            height="calc(100% - 40px)"
            language={getMonacoLanguage(language)}
            value={originalCode || ''}
            theme="vs-dark"
            options={{/* existing options */}}
          />
        </div>

        {/* Modified Code */}
        <div className="flex-1">
          <div className="bg-emerald-500/20 border-b border-white/10 px-4 py-2">
            <span className="text-xs text-emerald-200 font-medium">Modified</span>
          </div>
          <Editor
            height="calc(100% - 40px)"
            language={getMonacoLanguage(language)}
            value={code}
            theme="vs-dark"
            options={{/* existing options */}}
          />
        </div>
      </div>
    )}
  </div>

  {/* Issues List */}
  {issues.length > 0 && (
    <div className="border-t border-white/10 p-4 max-h-[200px] overflow-auto">
      <h4 className="text-sm font-medium text-white mb-3">Issues Found ({issues.length})</h4>

      <div className="space-y-2">
        {Array.from(issueLines.entries()).map(([lineNum, lineIssues]) => (
          <div key={lineNum}>
            {lineIssues.map((issue, idx) => (
              <CustomAlert
                key={idx}
                severity={getSeverityType(issue.severity)}
                message={
                  <div>
                    <p className="font-medium">Line {lineNum}: {issue.description}</p>
                    <p className="text-xs mt-1 opacity-80">{issue.explanation}</p>
                  </div>
                }
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )}

  {/* Issues Summary Footer */}
  {issues.length > 0 && (
    <div className="border-t border-white/10 px-4 py-2 bg-white/5">
      <p className="text-xs text-gray-400">
        {issues.filter(i => i.severity === 'critical' || i.severity === 'high').length} critical/high •{' '}
        {issues.filter(i => i.severity === 'medium').length} medium •{' '}
        {issues.filter(i => i.severity === 'low').length} low
      </p>
    </div>
  )}
</GlassCard>
```

## Reusable Components

### From Design System (Already Available)
- GlassCard - Container with glassmorphism
- GlassButton - Buttons with purple glow
- GlassInput - Form inputs (needs multiline enhancement)
- StatusBadge - Status indicators
- LoadingState - Loading spinner
- cn() - className utility

### To Create (New)
1. **CustomAlert** (`src/ui/src/components/review/CustomAlert.tsx`)
   - Props: severity, message, onClose
   - Glassmorphism with colored left border
   - Icon + message + close button

2. **CustomAccordion** (`src/ui/src/components/review/CustomAccordion.tsx`)
   - Props: title, icon, children, defaultExpanded
   - Expandable section with chevron
   - Smooth animation

### To Enhance (Existing)
1. **GlassInput** (`src/ui/src/components/design-system/GlassInput.tsx`)
   - Add multiline prop (boolean)
   - Add rows prop (number)
   - Render textarea when multiline=true

## Out of Scope
- Changes to Monaco Editor configuration
- Changes to review API logic
- Changes to review workflow
- Other page migrations (Phase 3+)
- New features beyond current functionality

## Success Criteria
- Zero Material-UI imports in all 4 review components
- All existing functionality preserved (Monaco Editor, forms, dialogs, tabs)
- 100% visual consistency with design system
- No TypeScript errors
- No console errors or warnings
- All components work in ReviewModal context
- Tests passing for all migrated components
- Build succeeds

## Implementation Notes

**Order of Operations:**
1. Create CustomAlert component
2. Create CustomAccordion component
3. Enhance GlassInput for multiline support
4. Migrate ConfidenceIndicator (simplest, no dependencies)
5. Migrate ReviewActions (uses GlassInput, CustomAlert)
6. Migrate AISuggestionsPanel (uses ConfidenceIndicator, CustomAlert, CustomAccordion)
7. Migrate CodeDiffViewer (uses CustomAlert, most complex)
8. Integration testing in ReviewQueue/ReviewModal

**Testing Strategy:**
- Unit tests for new components (CustomAlert, CustomAccordion)
- Unit tests for each migrated component
- Integration tests in ReviewModal context
- Visual QA against design system standards

**Dependencies:**
- react-icons (Feather Icons)
- Remove @mui/material imports from 4 files
- Remove @mui/icons-material imports from 4 files
