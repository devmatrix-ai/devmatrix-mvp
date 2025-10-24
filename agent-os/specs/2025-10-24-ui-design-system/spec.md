# Specification: UI Design System - Glassmorphism Components

## Goal
Create a reusable component library of 8 glassmorphism-styled UI primitives that implement the MasterplansPage aesthetic across all DevMatrix pages, enabling visual consistency and reducing code duplication.

## User Stories
- As a developer, I want pre-built glassmorphism components so that I can quickly build new pages with consistent styling
- As a developer, I want TypeScript-typed components so that I get autocomplete and type safety when using them
- As a user, I want a visually consistent interface so that navigation feels predictable and professional
- As a developer, I want extensible components (via className prop) so that I can customize them for specific use cases

## Core Requirements
- **GlassCard**: Reusable card container with backdrop-blur and gradient borders
- **GlassButton**: Interactive button with purple accent glow and three variants (primary/secondary/ghost)
- **GlassInput**: Text input with glassmorphism styling and optional icon support
- **StatusBadge**: Color-coded status indicators with glassmorphism background
- **PageHeader**: Standardized page header with emoji + title + optional subtitle
- **SectionHeader**: Consistent section titles across pages
- **SearchBar**: Integrated search input with icon and glassmorphism styling
- **FilterButton**: Toggle button for filtering with active/inactive states

All components must:
- Accept className prop for Tailwind utility extension
- Use TypeScript with exported interfaces
- Support dark theme only (no light mode)
- Include basic accessibility (ARIA labels, semantic HTML)
- Use purple (#a855f7) as accent color
- Apply transition-all for smooth animations

## Visual Design
- **Reference implementation**: `src/ui/src/pages/MasterplansPage.tsx` and `src/ui/src/components/masterplans/`
- **Key visual elements**:
  - Dark gradient backgrounds: `bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20`
  - Glassmorphism effect: `backdrop-blur-lg bg-white/5 border border-white/10`
  - Purple glow on active: `bg-purple-600 shadow-lg shadow-purple-500/50`
  - Smooth transitions: `transition-all`
  - Typography: white for headers, gray-300 for body text
  - Spacing: p-6 for cards, gap-6 for layouts
- **Responsive**: Components provide base styling, parent controls breakpoints

## Reusable Components

### Existing Code to Leverage
- **Gradient patterns**: Already used in MasterplansPage, LoginPage, RegisterPage, ChatWindow
- **Icons**: react-icons library already installed (FiSearch, etc.)
- **Tailwind config**: Dark theme and purple color palette already configured
- **TypeScript setup**: Existing interfaces pattern from MasterplanCard and other components

### Existing Patterns to Follow
- **Card styling** from `src/ui/src/components/masterplans/MasterplanCard.tsx`:
  - `bg-gradient-to-r from-purple-900/20 to-blue-900/20`
  - `backdrop-blur-lg rounded-2xl border border-white/10`
  - `hover:shadow-xl transition-all`

- **Search bar** from `src/ui/src/components/masterplans/MasterplansList.tsx`:
  - `w-full px-4 py-3 pl-12 bg-white/5 border border-white/20 rounded-lg`
  - `focus:outline-none focus:ring-2 focus:ring-purple-500`

- **Filter buttons** from MasterplansList:
  - Active: `bg-purple-600 text-white shadow-lg shadow-purple-500/50`
  - Inactive: `bg-white/10 text-gray-300 hover:bg-white/20`

- **Status badges** from MasterplanCard:
  - `px-3 py-1 rounded-full text-xs font-medium`
  - Color-coded backgrounds with 20% opacity

### New Components Required
All 8 components are new because:
- No existing design system directory
- Current patterns are duplicated across files (DRY violation)
- Need TypeScript interfaces for type safety
- Require unified API (props, variants, accessibility)
- Must be tree-shakeable and importable from single index

## Technical Approach

### Technology Stack
- React 18+ functional components with TypeScript
- Tailwind CSS for all styling (no CSS modules or styled-components)
- react-icons for icons (already installed, no new deps)

### Component Architecture
- All components are presentational (stateless)
- Use React.forwardRef for inputs and buttons (ref forwarding)
- Props interfaces exported separately for reusability
- className prop merging: `className={cn("base-classes", className)}`
- JSDoc comments for documentation

### File Structure
```
src/ui/src/components/design-system/
├── GlassCard.tsx          # Card container
├── GlassButton.tsx        # Interactive button
├── GlassInput.tsx         # Text input
├── StatusBadge.tsx        # Status indicator
├── PageHeader.tsx         # Page header
├── SectionHeader.tsx      # Section title
├── SearchBar.tsx          # Search input
├── FilterButton.tsx       # Filter toggle
└── index.ts               # Barrel exports
```

### Accessibility
- Semantic HTML (button, input, header tags)
- ARIA labels for icon-only buttons
- Keyboard navigation support (focus states visible)
- WCAG AA contrast ratios (white/purple on dark meets standards)

### Integration Plan
- Phase 2: Replace Material-UI in ReviewQueue with design system components
- Phase 3-8: Apply to Admin, Profile, Chat, Auth, Settings pages
- Phase 9: Remove Material-UI dependency from package.json

## Out of Scope
- Complex components (modals, dropdowns, tooltips, popovers) - future phase
- Storybook or component documentation site - future enhancement
- Unit tests - deferred to Phase 10 QA (will be added later)
- Multiple color themes - purple accent only for now
- Light theme support - dark mode only
- Form validation logic - components are presentational
- State management - components are controlled/stateless
- Animation variants beyond transition-all
- CSS-in-JS or styled-components - Tailwind only

## Success Criteria
- All 8 components implemented and exported from index.ts
- TypeScript strict mode passes with no errors
- Components used successfully in at least 3 pages (ReviewQueue, Profile, Admin)
- Code duplication reduced by 40%+ (measured by repeated glassmorphism patterns)
- Bundle size does not increase (no new dependencies)
- Visual consistency verified across all pages using components
- Components accept className prop and merge correctly with base styles
- Basic accessibility validated (semantic HTML, ARIA labels, keyboard nav)
