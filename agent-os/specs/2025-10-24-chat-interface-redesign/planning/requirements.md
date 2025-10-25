# Phase 5: Chat Interface Glassmorphism Redesign - Requirements

## Executive Summary

**Scope**: 9 components, 1602 lines of code
**Complexity**: HIGH (Most complex phase - real-time WebSocket, markdown rendering, progress tracking)
**Estimated Replacements**: ~113 elements (20 containers, 14 buttons, 1 input, 60 text colors, 8 progress indicators, 10 special elements)
**Estimated Duration**: ~28 hours (3.5 days)
**Risk Level**: HIGH (WebSocket integration, markdown rendering, complex animations)

## Component Breakdown

### 1. ChatWindow.tsx (301 lines) - **HIGH Complexity**

**Main Container Component** orchestrating entire chat interface

**UI Elements** (10 elements):
1. Main container with dark theme and shadows (Line 137)
2. Header bar with gradient from-primary-600 to-primary-700 (Line 139)
3. Connection status indicator with animated pulse (Lines 146-154)
4. Export button with hover state (Lines 161-169)
5. New Project button with hover state (Lines 171-179)
6. Minimize/Close buttons (Lines 180-197)
7. Empty state container with centered icon and text (Lines 205-223)
8. Debug footer with conversation ID (Lines 293-297)
9. Messages container with scroll (Line 204)
10. Input container with border-top (Line 277)

**Current Patterns**:
- 10 dark mode classes
- Gradient backgrounds on header
- Border utilities for separation
- Shadow-xl on main container
- Animated connection status dots

**Migration Target**:
- Main container → GlassCard with gradient background
- Header → Glass header with colored overlay
- Empty state → Glass container with centered content
- Action buttons → Glass buttons with hover effects
- Connection status → Preserve animation, add glass backdrop

**Dependencies**: MessageList, ChatInput, ProgressIndicator, MasterPlanProgressIndicator, ConversationHistory, useChat hook, useKeyboardShortcuts

**Risk**: HIGH - WebSocket integration, progress event routing must remain functional

---

### 2. MessageList.tsx (137 lines) - **MEDIUM Complexity**

**Message Rendering** with ReactMarkdown and syntax highlighting

**UI Elements** (6 types):
1. User message bubble - bg-primary-600 text-white (Line 58)
2. Assistant message - bg-gray-100 dark:bg-gray-800 (Line 61)
3. System message - bg-yellow-50 dark:bg-yellow-900/20 with borders (Line 60)
4. Avatar circles with role-specific colors (Lines 78-79)
5. Hover action buttons (copy/regenerate) (Lines 112-131)
6. Loading dots with bounce animation (Lines 23-34)

**Current Patterns**:
- 12 dark mode classes
- Gradient backgrounds for message types
- Group hover for action buttons
- Flex-row-reverse for user messages (right-aligned)
- Markdown prose styling

**Migration Target**:
- User bubbles → Glass with primary tint (right-aligned)
- Assistant bubbles → Glass with neutral tint (left-aligned)
- System bubbles → Glass with yellow tint
- Hover actions → Glass buttons with smooth transitions
- Avatar circles → Keep current style or subtle glass border
- Loading dots → Preserve animation, glass container

**Dependencies**: ReactMarkdown, remarkGfm, rehypeHighlight, CodeBlock component, date-fns, Clipboard API

**Risk**: MEDIUM - Markdown rendering readability with glass backgrounds must be tested

---

### 3. ChatInput.tsx (158 lines) - **MEDIUM Complexity**

**Interactive Input** with command autocomplete and suggestions

**UI Elements** (5 elements):
1. Suggestions dropdown - bg-white dark:bg-gray-800 with shadow (Line 106)
2. Selected suggestion - bg-primary-50 dark:bg-primary-900/20 (Lines 113-115)
3. Textarea - bg-gray-50 dark:bg-gray-800 with focus ring (Line 135)
4. Keyboard hint badge - bg-gray-200 dark:bg-gray-700 (Line 139)
5. Send button - bg-primary-600 with hover (Line 149)

**Current Patterns**:
- 4 dark mode classes
- Focus ring on textarea (focus:ring-2 focus:ring-primary-500)
- Disabled states on input and button
- Auto-resizing textarea (max-height: 200px)

**Migration Target**:
- Suggestions → GlassCard with backdrop-blur-md
- Selected item → Glass with primary tint
- Textarea → Glass input with subtle border glow
- Send button → Glass button with primary overlay
- Keyboard hint → Glass badge
- Focus ring → Enhanced glass glow effect

**Dependencies**: forwardRef, useImperativeHandle, auto-resize effect

**Risk**: MEDIUM - Focus management and auto-resize must remain smooth

---

### 4. ProgressIndicator.tsx (135 lines) - **MEDIUM Complexity**

**Task Progress Tracking** for real-time execution

**UI Elements** (3 elements):
1. Progress bar container - gradient from-blue-50 to-indigo-50 (Line 98)
2. Progress bar fill - gradient from-blue-500 to-indigo-600 (Line 109)
3. Event message card - border-2 border-blue-300 (Line 123)

**Current Patterns**:
- 9 dark mode classes
- Gradient backgrounds for depth
- Animated progress bar transitions
- Color-coded event types (green/red/blue)

**Migration Target**:
- Container → GlassCard with blue tint
- Progress bar → Glass container with solid gradient fill
- Event messages → Glass cards with status-colored borders
- Preserve smooth transitions

**Dependencies**: ProgressEvent interface, WebSocket events, task counter state

**Risk**: MEDIUM - Real-time updates must remain smooth with glass effects

---

### 5. MasterPlanProgressIndicator.tsx (440 lines) - **HIGH Complexity**

**MasterPlan Generation Tracking** with multi-phase progress

**UI Elements** (6 main elements):
1. Main container - gradient from-purple-50 via-blue-50 to-indigo-50, border-2 border-purple-300 (Lines 282-284)
2. Progress bar - gradient from-purple-500 via-blue-600 to-indigo-600 (Line 318)
3. Entity counters - 3-column grid (Line 351)
4. Status timeline - bg-white dark:bg-gray-800/50 (Line 376)
5. Completion banner - bg-green-100 with green borders (Line 426)
6. Animated icons with pulse/bounce effects

**Current Patterns**:
- 9 dark mode classes
- Complex gradient combinations
- Multiple animation types (pulse, bounce, scale)
- Conditional styling based on completion state

**Migration Target**:
- Main container → GlassCard with purple-blue gradient overlay
- Progress bar → Glass container with solid gradient fill
- Entity counters → Handled by EntityCounter component (glass cards)
- Status timeline → Glass background
- Completion banner → Glass with green tint overlay
- Preserve all animations

**Dependencies**: EntityCounter, StatusItem, complex event state machine, timer

**Risk**: HIGH - Complex state machine, multiple simultaneous animations

---

### 6. ConversationHistory.tsx (220 lines) - **MEDIUM-HIGH Complexity**

**Sidebar Drawer** with conversation list and API integration

**UI Elements** (8 elements):
1. Toggle button - bg-gray-800 fixed position (Lines 95-103)
2. Sidebar drawer - bg-gray-900 full height with transform (Lines 106-109)
3. Header with border-bottom (Line 113)
4. New conversation button - bg-blue-600 (Line 131)
5. Conversation items - border-gray-800 with hover (Lines 167-205)
6. Active conversation - blue left border (Line 174)
7. Delete button - hover text-red-400 (Lines 195-203)
8. Overlay - bg-black bg-opacity-50 (Lines 212-217)

**Current Patterns**:
- 26 dark mode classes (highest count)
- Transform transitions for slide-in effect
- Fixed positioning with z-index layers
- Hover states on interactive elements

**Migration Target**:
- Sidebar → Full glass overlay with backdrop-blur-lg
- Conversation items → Glass cards with hover states
- Active item → Enhanced glass with colored left border
- Delete button → Glass hover with red tint
- Overlay → Increase blur for focus effect
- Preserve slide animation performance

**Dependencies**: API calls (/api/v1/conversations), date-fns (es locale), loading/error states

**Risk**: HIGH - Slide animation performance, API integration, overlay z-index coordination

---

### 7. CodeBlock.tsx (60 lines) - **LOW Complexity**

**Syntax Highlighting** for inline and block code

**UI Elements** (4 elements):
1. Inline code - bg-gray-200 dark:bg-gray-700 (Line 26)
2. Code block header - bg-gray-800 text-gray-300 (Line 35)
3. Copy button with hover bg-gray-700 (Line 39)
4. Code block body - bg-gray-900 text-gray-100 (Line 55)

**Current Patterns**:
- 1 dark mode class
- Fixed dark theme for code blocks (intentional for readability)
- Rounded corners on header/body
- Copy button with state feedback

**Migration Target**:
- Keep dark background for readability
- Add subtle glass border to blocks
- Glass overlay on header
- Glass hover state on copy button

**Dependencies**: Clipboard API, react-icons

**Risk**: LOW - Simple component, dark theme intentional for code readability

---

### 8. EntityCounter.tsx (68 lines) - **LOW Complexity**

**Progress Counter Card** for individual entity counts

**UI Elements** (3 states):
1. Complete state - gradient from-green-100 to-green-50 with scale (Lines 25-26)
2. Pending state - bg-white dark:bg-gray-800 with purple border (Line 26)
3. Mini progress bar with gradient fill (Lines 54-64)

**Current Patterns**:
- 6 dark mode classes
- Conditional gradients based on completion
- Scale transform on completion
- Pulse animation during progress

**Migration Target**:
- Cards → Full glass with conditional tint (green/purple)
- Border → Glass border with scale animation on complete
- Mini progress → Glass container, solid fill
- Preserve pulse and scale animations

**Dependencies**: None (pure presentational)

**Risk**: LOW - Simple presentational component

---

### 9. StatusItem.tsx (83 lines) - **LOW Complexity**

**Timeline Status Item** for individual status indicators

**UI Elements** (3 states):
1. Pending - text-gray-500 with opacity (Lines 17-20)
2. In-progress - bg-blue-50 with spinner (Lines 23-26)
3. Done - bg-green-50 with checkmark (Lines 29-32)

**Current Patterns**:
- 6 dark mode classes
- Conditional backgrounds
- Icon animations (pulse, spin, scale-in)

**Migration Target**:
- Item backgrounds → Subtle glass for in_progress/done states
- Spinner/Checkmark → Keep solid for visibility
- Timeline → Glass dividers between items
- Preserve all animations

**Dependencies**: None (pure presentational)

**Risk**: LOW - Simple state-driven component

---

## Migration Scope Summary

### Total Replacements by Category

| Category | Count | Priority |
|----------|-------|----------|
| Container/Card Elements | 20 | HIGH |
| Buttons and Interactive | 14 | MEDIUM |
| Input Fields | 1 | MEDIUM |
| Text Color Changes | 60 | MEDIUM |
| Progress Bars/Indicators | 8 | MEDIUM |
| Special UI Elements | 10 | LOW |
| **Total** | **113** | - |

### Dark Mode Classes Inventory

| Component | Dark Mode Classes | Complexity |
|-----------|------------------|------------|
| ConversationHistory | 26 | Highest |
| MessageList | 12 | High |
| ChatWindow | 10 | High |
| ProgressIndicator | 9 | Medium |
| MasterPlanProgressIndicator | 9 | High |
| EntityCounter | 6 | Low |
| StatusItem | 6 | Low |
| ChatInput | 4 | Medium |
| CodeBlock | 1 | Low |
| **Total** | **83** | - |

---

## Technical Specifications

### Glassmorphism Palette

**Base Glass Styles**:
```css
/* Light glass */
.glass-light: backdrop-blur-sm bg-white/80 border border-white/20

/* Dark glass */
.glass-dark: backdrop-blur-sm bg-gray-900/80 border border-white/10

/* Glass variants */
.glass-primary: backdrop-blur-md bg-primary-500/20 border border-primary-300/30
.glass-success: backdrop-blur-md bg-green-500/20 border border-green-300/30
.glass-warning: backdrop-blur-md bg-yellow-500/20 border border-yellow-300/30
.glass-error: backdrop-blur-md bg-red-500/20 border border-red-300/30
```

**Blur Intensity Guidelines**:
- Overlays: `backdrop-blur-md` (8px)
- Cards/Containers: `backdrop-blur-sm` (4px)
- Dropdowns: `backdrop-blur-md` (8px)
- Sidebars: `backdrop-blur-lg` (12px)
- Progress indicators: `backdrop-blur-sm` (4px) or none

**Color Tints**:
- User messages: Primary blue tint
- Assistant messages: Neutral gray tint
- System messages: Yellow warning tint
- Success states: Green tint
- Error states: Red tint

---

## Integration Requirements

### External Dependencies
- **ReactMarkdown**: Must maintain readability with glass backgrounds
- **rehype-highlight**: Syntax highlighting with dark code blocks
- **remark-gfm**: GitHub Flavored Markdown support
- **date-fns**: Spanish locale for timestamps
- **react-icons**: All current icons preserved

### State Management
- **WebSocket**: Real-time message streaming must remain smooth
- **Progress Events**: Two systems (task execution, masterplan generation)
- **Auto-scroll**: Triggered on new messages
- **Keyboard Shortcuts**: Ctrl+K, Ctrl+L, Ctrl+N must work
- **Focus Management**: ChatInput focus control

### API Integration
- **GET /api/v1/conversations**: Conversation list
- **DELETE /api/v1/conversations/:id**: Delete conversation
- **WebSocket**: Message streaming
- **Clipboard API**: Copy functionality

---

## Risk Assessment

### High-Risk Components
1. **ChatWindow**: WebSocket integration, progress routing
2. **MasterPlanProgressIndicator**: Complex state machine, multiple animations
3. **ConversationHistory**: Slide animation, API calls, z-index coordination

### Medium-Risk Components
4. **ChatInput**: Focus management, auto-resize behavior
5. **MessageList**: Markdown readability with glass backgrounds
6. **ProgressIndicator**: Real-time progress updates

### Low-Risk Components
7. **CodeBlock**: Simple copy functionality
8. **EntityCounter**: Pure presentational
9. **StatusItem**: Pure presentational

### Performance Concerns
- **Backdrop-blur**: Expensive CSS property, may impact 60fps target
- **Message list**: Could grow to 100+ messages with glass backgrounds
- **Real-time updates**: WebSocket events every 100-500ms during execution
- **Auto-resize**: Recalculates on every keystroke
- **Multiple animations**: During masterplan generation

**Mitigation**:
- Conditional blur based on device capabilities
- Prefers-reduced-motion media query support
- Performance monitoring during testing
- Fallback to solid backgrounds if performance degrades

---

## Accessibility Requirements

### WCAG AA Compliance
- Text contrast ≥ 4.5:1 for normal text
- Text contrast ≥ 3:1 for large text
- Focus states visible with glass effects
- Keyboard navigation preserved
- Screen reader compatibility

### Specific Checks
- Message text readable on glass backgrounds (all 3 types)
- Code blocks maintain contrast (dark theme)
- Focus rings visible on glass inputs
- Hover states perceptible
- Status colors distinguishable

---

## Implementation Strategy

### Sub-Phase Breakdown

**Phase 5a - Low-Risk Components** (2-3 hours):
- CodeBlock: Subtle glass borders
- EntityCounter: Glass card backgrounds
- StatusItem: Glass timeline dividers

**Phase 5b - Medium-Risk Components** (4-5 hours):
- ChatInput: Glass suggestions, glass textarea
- MessageList: Glass message bubbles (test readability)
- ProgressIndicator: Glass progress containers

**Phase 5c - High-Risk Components** (6-8 hours):
- ChatWindow: Glass header, glass main container
- ConversationHistory: Glass sidebar with slide animation
- MasterPlanProgressIndicator: Glass accents on complex UI

**Phase 5d - Integration Testing** (3-4 hours):
- WebSocket real-time with glass effects
- Markdown rendering readability
- Animation performance
- Keyboard navigation
- Dark mode contrast

### Testing Checklist
- [ ] WebSocket messages render correctly
- [ ] Markdown code blocks readable
- [ ] Progress animations smooth (60fps)
- [ ] ConversationHistory slide animation performant
- [ ] ChatInput autocomplete keyboard navigation works
- [ ] Copy/export functionality preserved
- [ ] Dark mode contrast meets WCAG AA
- [ ] Auto-scroll behavior unaffected
- [ ] Focus states visible
- [ ] Performance acceptable on target devices

---

## Success Criteria

### Visual Quality
- Consistent glass aesthetic across all chat components
- Depth hierarchy clear (overlays > containers > backgrounds)
- Color tints appropriate for message types
- Dark mode glass effects maintain brand consistency

### Performance
- 60fps during message rendering with glass effects
- No jank during ConversationHistory slide animation
- Progress bar updates smooth (< 16ms frame time)
- Textarea auto-resize responsive (< 100ms)

### Functionality
- WebSocket real-time updates unaffected
- Markdown rendering readable
- Code syntax highlighting preserved
- Keyboard shortcuts functional
- Copy/export features working
- API calls successful

### Accessibility
- Text contrast ≥ 4.5:1 (WCAG AA)
- Focus states visible
- Keyboard navigation preserved
- Screen reader compatible

---

## Out of Scope

- WebSocket protocol changes
- Markdown rendering engine changes
- API endpoint modifications
- New chat features beyond glassmorphism styling
- Other page migrations (Phase 6+)

---

## Dependencies on Previous Phases

- **Phase 1-2**: UI Design System with GlassCard, GlassButton, GlassInput
- **Phase 3**: ReviewQueue glassmorphism patterns proven
- **Phase 4**: ProfilePage patterns for complex layouts with progress bars
- **Shared utilities**: Glassmorphism classes, dark mode toggle, performance monitoring

---

**End of Requirements Document**
