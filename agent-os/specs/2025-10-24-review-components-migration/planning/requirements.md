# Spec Requirements: Review Components Material-UI Migration

## Initial Description
Migrate the remaining 4 review components from Material-UI to the custom glassmorphism design system. This completes Phase 2 of the UI unification project.

## Requirements Discussion

### Component Analysis

**Current State:**
All 4 components use extensive Material-UI imports:

1. **CodeDiffViewer.tsx** (265 lines)
   - Material-UI: Box, Paper, Typography, Tabs, Tab, Chip, Tooltip, IconButton, Alert
   - Material-UI Icons: ContentCopy, Error, Warning, Info
   - Keep: Monaco Editor (user explicitly wants syntax highlighting)
   - Functionality: Code viewer, diff view, issues list, copy button

2. **AISuggestionsPanel.tsx** (339 lines)
   - Material-UI: Box, Paper, Typography, Accordion, AccordionSummary, AccordionDetails, Chip, List, ListItem, ListItemText, Divider, Alert, Button, Tooltip
   - Material-UI Icons: ExpandMore, Lightbulb, BugReport, Code, TrendingUp, ContentCopy
   - Imports: ConfidenceIndicator (also needs migration)
   - Functionality: Confidence score, AI recommendation, issues summary, issue details, alternatives

3. **ReviewActions.tsx** (351 lines)
   - Material-UI: Box, Button, TextField, Dialog, DialogTitle, DialogContent, DialogActions, Alert, CircularProgress
   - Material-UI Icons: CheckCircle, Cancel, Edit, Refresh
   - Functionality: 4 action buttons (approve, reject, edit, regenerate), 3 dialogs with forms

4. **ConfidenceIndicator.tsx** (104 lines)
   - Material-UI: Box, Tooltip, Typography
   - Material-UI Icons: CheckCircle, Warning, Error, Dangerous
   - Functionality: Visual confidence score with icon + label, color-coded (green/orange/red)

### Migration Strategy

**Approach: Component-by-Component**
- Start with simplest (ConfidenceIndicator) to most complex (CodeDiffViewer)
- Ensure each component works independently before moving to next
- Test each component in ReviewModal context after migration

### Existing Code to Reference

**Design System Components Available:**
- GlassCard - Container with glassmorphism
- GlassButton - Buttons with purple glow
- GlassInput - Form inputs (needed for ReviewActions dialogs)
- StatusBadge - Color-coded badges (perfect for severity indicators)
- PageHeader, SectionHeader - Headers
- SearchBar, FilterButton - Interactive controls

**Icons:**
- Use react-icons/fi (Feather Icons) for consistency with existing components
- Map Material-UI icons to Feather equivalents

## Requirements Summary

### Functional Requirements

**Must Preserve All Current Functionality:**
- CodeDiffViewer: Monaco Editor, tabs, diff view, copy button, issues list
- AISuggestionsPanel: Confidence display, recommendations, issues, alternatives, suggestions
- ReviewActions: 4 actions (approve, reject, edit, regenerate), dialogs, form validation
- ConfidenceIndicator: Visual score display, color coding, tooltips

**UI Components to Replace:**

1. **CodeDiffViewer Migration**
   - Paper → GlassCard
   - Tabs → Custom tabs with Tailwind
   - Chip → StatusBadge
   - Tooltip → Custom tooltip or keep for simplicity
   - IconButton → GlassButton (icon variant)
   - Alert → Custom alert with GlassCard + StatusBadge
   - Typography → Tailwind text classes
   - Box → div with Tailwind

2. **AISuggestionsPanel Migration**
   - Paper → GlassCard
   - Accordion → Custom accordion with Tailwind
   - Chip → StatusBadge
   - List/ListItem → Tailwind flex/grid
   - Alert → Custom alert with GlassCard
   - Button → GlassButton
   - Tooltip → Custom tooltip
   - ConfidenceIndicator → Migrated version

3. **ReviewActions Migration**
   - Button → GlassButton (4 variants: success, error, primary, warning)
   - Dialog → Custom modal with GlassCard + backdrop blur
   - TextField → GlassInput (multiline support needed)
   - Alert → Custom alert with StatusBadge
   - CircularProgress → LoadingState (already created)

4. **ConfidenceIndicator Migration**
   - Box → div with Tailwind
   - Tooltip → Custom tooltip with glassmorphism
   - Typography → Tailwind text classes
   - Icons → react-icons/fi equivalents
   - Color scheme: Green (#4caf50) → #10b981 (emerald-500)
   - Color scheme: Orange (#ff9800) → #f59e0b (amber-500)
   - Color scheme: Red (#f44336) → #ef4444 (red-500)

### Visual Design

**Color Mapping:**
```typescript
// Material-UI → Tailwind
success: green → emerald-500 (#10b981)
warning: orange → amber-500 (#f59e0b)
error: red → red-500 (#ef4444)
info: blue → blue-500 (#3b82f6)
```

**Glassmorphism Effects:**
- All Paper → GlassCard: `backdrop-blur-lg bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-white/10 rounded-2xl`
- Alerts: GlassCard with colored left border (border-l-4 border-red-500)
- Modals: Full backdrop blur + centered GlassCard

**Icon Mapping (Material-UI → Feather Icons):**
```typescript
ContentCopy → FiCopy
Error → FiAlertCircle
Warning → FiAlertTriangle
Info → FiInfo
CheckCircle → FiCheckCircle
Cancel → FiXCircle
Edit → FiEdit2
Refresh → FiRefreshCw
Lightbulb → FiZap
BugReport → FiBug
Code → FiCode
TrendingUp → FiTrendingUp
ExpandMore → FiChevronDown
Dangerous → FiAlertOctagon
```

### Component Structure

**ConfidenceIndicator (Simplest - Start Here)**
```typescript
// BEFORE (Material-UI)
<Tooltip title={getTooltip()}>
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    {getIcon()} {/* Material-UI icon */}
    <Typography variant="body2">{getLabel()}</Typography>
  </Box>
</Tooltip>

// AFTER (Design System)
<div className="group relative flex items-center gap-2">
  {getIcon()} {/* Feather icon */}
  <span className="text-sm font-bold" style={{ color: getColor() }}>
    {getLabel()}
  </span>
  {/* Custom tooltip on hover */}
  <div className="absolute left-0 top-full mt-2 hidden group-hover:block">
    <GlassCard className="px-3 py-2 text-xs whitespace-nowrap">
      {getTooltip()}
    </GlassCard>
  </div>
</div>
```

**ReviewActions (Dialog Pattern)**
```typescript
// BEFORE (Material-UI)
<Dialog open={open} onClose={onClose}>
  <DialogTitle>Title</DialogTitle>
  <DialogContent>
    <TextField multiline rows={4} />
  </DialogContent>
  <DialogActions>
    <Button>Cancel</Button>
    <Button variant="contained">Submit</Button>
  </DialogActions>
</Dialog>

// AFTER (Design System)
{open && (
  <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
    <GlassCard className="w-full max-w-md">
      <div className="border-b border-white/10 p-4">
        <h3 className="text-lg font-bold text-white">Title</h3>
      </div>
      <div className="p-4">
        <GlassInput multiline rows={4} />
      </div>
      <div className="border-t border-white/10 p-4 flex justify-end gap-2">
        <GlassButton variant="ghost" onClick={onClose}>Cancel</GlassButton>
        <GlassButton variant="primary" onClick={onSubmit}>Submit</GlassButton>
      </div>
    </GlassCard>
  </div>
)}
```

**Custom Alert Pattern**
```typescript
// BEFORE (Material-UI)
<Alert severity="error" icon={<ErrorIcon />}>
  <Typography>Error message</Typography>
</Alert>

// AFTER (Design System)
<GlassCard className="border-l-4 border-red-500 bg-red-500/10">
  <div className="flex items-start gap-3 p-4">
    <FiAlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
    <div>
      <p className="text-sm text-white">{message}</p>
    </div>
  </div>
</GlassCard>
```

**Custom Tabs Pattern**
```typescript
// BEFORE (Material-UI)
<Tabs value={activeTab} onChange={onChange}>
  <Tab label="Tab 1" value="tab1" />
  <Tab label="Tab 2" value="tab2" />
</Tabs>

// AFTER (Design System)
<div className="flex gap-2 border-b border-white/10 pb-2">
  <button
    className={cn(
      'px-4 py-2 rounded-t-lg transition-all',
      activeTab === 'tab1'
        ? 'bg-purple-600 text-white'
        : 'text-gray-400 hover:text-white hover:bg-white/10'
    )}
    onClick={() => onChange('tab1')}
  >
    Tab 1
  </button>
  <button
    className={cn(
      'px-4 py-2 rounded-t-lg transition-all',
      activeTab === 'tab2'
        ? 'bg-purple-600 text-white'
        : 'text-gray-400 hover:text-white hover:bg-white/10'
    )}
    onClick={() => onChange('tab2')}
  >
    Tab 2
  </button>
</div>
```

### New Components Needed

**GlassInput Enhancement:**
- Add `multiline` prop support (use textarea instead of input)
- Add `rows` prop for multiline
- Ensure works in ReviewActions dialogs

**Custom Components to Create:**
- **CustomAlert** - Reusable alert with severity styling (could be in design-system or review/)
- **CustomTooltip** - Simple tooltip wrapper with glassmorphism (optional - could keep simple HTML title)

### Scope Boundaries

**In Scope:**
- Migrate all 4 components from Material-UI to design system
- Enhance GlassInput for multiline support
- Create custom alert/tooltip patterns
- Preserve all existing functionality
- Maintain visual consistency with glassmorphism

**Out of Scope:**
- Changes to Monaco Editor configuration
- Changes to review API logic
- Changes to review workflow/state management
- Other page migrations (Phase 3+)
- New features not in current components

### Technical Considerations

**Dependencies to Add:**
- react-icons (if not already installed) - for Feather Icons

**Dependencies to Remove:**
- @mui/material (from these 4 files only)
- @mui/icons-material (from these 4 files only)

**Code Patterns:**
- Use cn() utility for className merging
- Use StatusBadge for all severity/status indicators
- Use GlassCard for all containers
- Use GlassButton for all buttons
- Consistent spacing: p-4, gap-3, rounded-lg

**Performance:**
- Keep Monaco Editor lazy loading
- React.memo for ConfidenceIndicator (used multiple times)
- No unnecessary re-renders

**Accessibility:**
- ARIA labels for icon buttons
- Keyboard navigation for tabs
- Focus management in dialogs
- Screen reader friendly labels

**Defaults Assumed:**
1. **Icon Library**: react-icons/fi (Feather Icons) for consistency
2. **Tooltips**: Simple CSS-based tooltips, not complex library
3. **Alerts**: Custom GlassCard with colored border pattern
4. **Modals**: Full backdrop blur pattern like ReviewModal
5. **Tabs**: Simple button-based tabs with purple active state
6. **Multiline Input**: Enhance GlassInput to support textarea
