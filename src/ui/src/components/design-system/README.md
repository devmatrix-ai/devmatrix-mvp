# Design System - Core Components

Reusable glassmorphism components for DevMatrix UI.

## Components Implemented (Task Group 1)

### GlassCard
Glassmorphism card container with backdrop blur and gradient borders.

**Props:**
- `children`: React.ReactNode
- `className?`: string (additional Tailwind classes)
- `hover?`: boolean (enable hover shadow effect)

**Example:**
```tsx
<GlassCard hover>
  <h2>Card Title</h2>
  <p>Card content</p>
</GlassCard>
```

### GlassButton
Interactive button with variants, sizes, and purple accent glow.

**Props:**
- `children`: React.ReactNode
- `variant?`: 'primary' | 'secondary' | 'ghost' (default: 'primary')
- `size?`: 'sm' | 'md' | 'lg' (default: 'md')
- `disabled?`: boolean
- `className?`: string
- All standard button HTML attributes

**Example:**
```tsx
<GlassButton variant="primary" size="md" onClick={handleClick}>
  Click Me
</GlassButton>
```

### StatusBadge
Color-coded status indicators with glassmorphism background.

**Props:**
- `children`: React.ReactNode
- `status?`: 'success' | 'warning' | 'error' | 'info' | 'default' (default: 'default')
- `className?`: string

**Example:**
```tsx
<StatusBadge status="success">Completed</StatusBadge>
<StatusBadge status="error">Failed</StatusBadge>
```

## Usage

Import components from the design system:

```tsx
import { GlassCard, GlassButton, StatusBadge } from '@/components/design-system'
```

All components:
- Support dark theme only
- Accept `className` prop for custom styling
- Use TypeScript with exported interfaces
- Include JSDoc documentation
- Apply smooth transitions with `transition-all`

## Testing

Run tests for design system components:

```bash
npm run test:run -- src/components/design-system
```

Current test coverage:
- **22 tests** across 3 test files
- Tests cover: className merging, variant rendering, accessibility, ref forwarding, user interactions

## Visual Demo

See `demo.tsx` for a visual reference of all components in action.

## Next Steps (Task Groups 2-5)

- Task Group 2: GlassInput, SearchBar, FilterButton, PageHeader, SectionHeader
- Task Group 3: Library integration and exports
- Task Group 4: Additional strategic tests
- Task Group 5: Real-world integration in ReviewQueue page
