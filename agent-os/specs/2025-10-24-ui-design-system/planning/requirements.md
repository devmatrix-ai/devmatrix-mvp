# Spec Requirements: UI Design System

## Initial Description
Create a reusable glassmorphism design system component library for DevMatrix UI unification. Phase 1 of a larger UI unification project to apply the MasterplansPage look & feel throughout the entire application.

## Requirements Discussion

### First Round Questions

**Q1:** Variantes de componentes - Asumo que los componentes deberían tener variantes (ej: GlassButton con size="sm|md|lg", variant="primary|secondary|ghost"). ¿Es correcto, o preferís mantenerlos simples por ahora y agregar variantes después?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q2:** Tipado TypeScript - Estoy pensando en usar interfaces estrictas para las props (ej: `interface GlassCardProps { children: ReactNode; className?: string; hover?: boolean }`). ¿Debería incluir también variantes de color para cada componente o mantengo purple como único accent?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q3:** Accesibilidad - ¿Incluyo props de accesibilidad como `aria-label`, `role`, etc. en todos los componentes interactivos, o lo dejamos para una fase posterior?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q4:** Animaciones - Los componentes del Masterplans page usan `transition-all`. ¿Querés que sea configurable (ej: `animation="fade|slide|none"`) o siempre `transition-all`?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q5:** Responsive - ¿Los componentes deberían manejar breakpoints internamente o confiar en que el componente padre use las clases de Tailwind (ej: `md:col-span-2`)?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q6:** Documentación - ¿Creo un Storybook o similar para documentar los componentes, o con comentarios JSDoc es suficiente?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q7:** Testing - ¿Incluyo tests unitarios para cada componente en esta fase, o los dejamos para después?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

**Q8:** Scope - ¿Hay algo que NO debería incluir en esta primera fase? Por ejemplo, ¿componentes más complejos como modales, dropdowns, tooltips deberían quedar afuera?
**Answer:** No tengo especificaciones adicionales - usar defaults razonables

### Existing Code to Reference

**Similar Features Identified:**
- Feature: MasterplansPage - Path: `src/ui/src/pages/MasterplansPage.tsx`
  - Reference for: Page layout, gradient backgrounds, emoji headers, glassmorphism cards
- Feature: MasterplansList - Path: `src/ui/src/components/masterplans/MasterplansList.tsx`
  - Reference for: Search bars, filter buttons, card layouts, hover effects
- Feature: MasterplanCard - Path: `src/ui/src/components/masterplans/MasterplanCard.tsx`
  - Reference for: Card styling, status badges, glassmorphism effects

**Components to potentially reuse:**
- Icon components from react-icons (FiSearch, etc.)
- Tailwind CSS utility classes already configured
- Dark theme patterns established in the application

**Design patterns to follow:**
- Dark gradient backgrounds: `bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20`
- Glassmorphism: `backdrop-blur-lg bg-white/5 border border-white/10`
- Purple accents: `bg-purple-600 shadow-lg shadow-purple-500/50`
- Smooth transitions: `transition-all`
- Rounded corners: `rounded-2xl` for cards, `rounded-lg` for buttons/inputs

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
Using existing MasterplansPage implementation as visual reference:
- Dark aesthetic with gradient overlays
- Glassmorphism cards with backdrop blur
- Purple accent color for active states and CTAs
- Large emoji headers (text-5xl)
- Consistent spacing with p-6, gap-6 patterns
- High contrast text: white for headers, gray-300 for body
- Hover effects with shadow-xl and subtle scale

## Requirements Summary

### Functional Requirements

**Core Components to Build (8 total):**

1. **GlassCard**
   - Props: children, className, hover (boolean)
   - Default styling: glassmorphism with backdrop-blur-lg
   - Hover state: shadow-xl transition

2. **GlassButton**
   - Props: children, onClick, variant ("primary" | "secondary" | "ghost"), size ("sm" | "md" | "lg"), disabled, className
   - Variants:
     - primary: purple background with glow (bg-purple-600 shadow-lg shadow-purple-500/50)
     - secondary: white/10 background (bg-white/10)
     - ghost: transparent with border (bg-transparent border border-white/20)
   - Hover effects: bg-white/20 for secondary/ghost, enhanced glow for primary

3. **GlassInput**
   - Props: value, onChange, placeholder, type, className, icon (optional React.ReactNode)
   - Styling: bg-white/5 border border-white/20 rounded-lg
   - Focus state: ring-2 ring-purple-500
   - Icon support: pl-12 when icon provided

4. **StatusBadge**
   - Props: children, status ("success" | "warning" | "error" | "info" | "default"), className
   - Styling: px-3 py-1 rounded-full text-xs font-medium
   - Color-coded:
     - success: bg-green-500/20 text-green-400 border-green-500/50
     - warning: bg-yellow-500/20 text-yellow-400 border-yellow-500/50
     - error: bg-red-500/20 text-red-400 border-red-500/50
     - info: bg-blue-500/20 text-blue-400 border-blue-500/50
     - default: bg-gray-500/20 text-gray-400 border-gray-500/50

5. **PageHeader**
   - Props: emoji, title, subtitle (optional), className
   - Layout: emoji (text-5xl) + title (text-4xl font-bold text-white)
   - Subtitle: text-gray-400 below title

6. **SectionHeader**
   - Props: children, className
   - Styling: text-2xl font-bold text-white

7. **SearchBar**
   - Props: value, onChange, placeholder, className
   - Integrated icon: FiSearch from react-icons
   - Styling: w-full px-4 py-3 pl-12 bg-white/5 border-white/20 rounded-lg
   - Focus: ring-2 ring-purple-500 border-transparent

8. **FilterButton**
   - Props: children, active (boolean), onClick, className
   - Active state: bg-purple-600 text-white shadow-lg shadow-purple-500/50
   - Inactive state: bg-white/10 text-gray-300
   - Hover: bg-white/20 when inactive

### Reusability Opportunities
- All components should accept className prop for Tailwind utility extension
- Use React.forwardRef for components that might need refs (inputs, buttons)
- Export TypeScript interfaces for all props
- Create centralized index.ts for clean imports

### Scope Boundaries

**In Scope:**
- 8 foundational design system components
- TypeScript interfaces for all props
- JSDoc documentation for each component
- Tailwind CSS styling only (no CSS modules or styled-components)
- Basic accessibility (semantic HTML, ARIA labels where needed)
- Glassmorphism aesthetic matching MasterplansPage
- Purple accent color system
- Responsive support via Tailwind utilities

**Out of Scope:**
- Complex components (modals, dropdowns, tooltips) - future phase
- Storybook documentation - future enhancement
- Unit tests - future phase (will be added in Phase 10 QA)
- Animation variants beyond transition-all - keep simple
- Multiple color themes - purple accent only
- Light theme support - dark mode only
- Form validation logic - components are presentational only
- State management - components are controlled (stateless)

### Technical Considerations

**Technology Stack:**
- React 18+ with TypeScript
- Tailwind CSS for all styling
- react-icons for icons (already installed)
- No additional dependencies

**Integration Points:**
- Components will be imported across 15+ pages
- Must work with existing dark theme setup
- Should integrate with current Tailwind configuration
- No conflicts with existing component libraries

**Code Patterns to Follow:**
- Functional components with TypeScript
- Props interfaces exported separately
- className prop merging with existing styles
- forwardRef for inputs and buttons
- Consistent naming: Glass* prefix for glassmorphism components

**File Structure:**
```
src/ui/src/components/design-system/
├── GlassCard.tsx
├── GlassButton.tsx
├── GlassInput.tsx
├── StatusBadge.tsx
├── PageHeader.tsx
├── SectionHeader.tsx
├── SearchBar.tsx
├── FilterButton.tsx
└── index.ts (exports all components)
```

**Accessibility Standards:**
- Use semantic HTML elements
- Include ARIA labels for interactive elements without text
- Ensure keyboard navigation works (focus states)
- Maintain WCAG AA contrast ratios (already met with white/purple on dark)
- Support screen readers with proper roles

**Performance Considerations:**
- Lightweight components (no heavy deps)
- CSS classes only (no runtime CSS-in-JS)
- Tree-shakeable exports
- No unnecessary re-renders (React.memo if needed)

**Defaults Assumed (Based on Best Practices):**
1. **Variantes**: Include basic size/variant props but keep simple (sm/md/lg, primary/secondary/ghost)
2. **TypeScript**: Strict interfaces with required props clearly marked
3. **Accessibility**: Basic ARIA support included (aria-label, role, aria-disabled)
4. **Animations**: Always use transition-all (no configurability for simplicity)
5. **Responsive**: Components provide base styling, parent controls breakpoints
6. **Documentation**: JSDoc comments sufficient (no Storybook for now)
7. **Testing**: Tests deferred to Phase 10 QA
8. **Scope**: Only 8 foundational components, no complex UI patterns yet
