# Landing Page - Level 1 Synthetic Spec

## Overview
Modern, responsive landing page for a SaaS product using Next.js 14 with App Router, Tailwind CSS, and shadcn/ui components.

## Tech Stack
- **Frontend**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS 3.4+
- **Components**: shadcn/ui
- **Icons**: Lucide React
- **Deployment**: Vercel (or static export)
- **Testing**: Vitest, Testing Library

## Features

### F1: Hero Section
- Large heading with gradient text effect
- Subheading with value proposition
- Primary CTA button (opens modal or navigates)
- Secondary CTA button (scrolls to features)
- Hero image or illustration (right side on desktop, below on mobile)
- Subtle background pattern or gradient

### F2: Features Section
- 3-column grid on desktop, 1-column on mobile
- Each feature card with:
  - Icon (Lucide React)
  - Title (h3)
  - Description (2-3 sentences)
  - Hover effect (subtle scale or shadow)
- Section heading and subheading

### F3: Social Proof Section
- Customer testimonials carousel or grid
- 3 testimonials minimum
- Each testimonial:
  - Quote text
  - Customer name
  - Customer role/company
  - Avatar image (can use placeholder)
  - 5-star rating display
- Auto-rotating carousel (optional) or static grid

### F4: CTA Section
- Final call-to-action before footer
- Compelling headline
- Supporting text
- Primary CTA button
- Background with accent color or gradient
- Full-width section with centered content

### F5: Responsive Navigation
- Sticky header with logo
- Desktop: Horizontal nav links (Features, Testimonials, Pricing, Contact)
- Mobile: Hamburger menu with slide-in drawer
- CTA button in header
- Smooth scroll to sections
- Active section highlighting

### F6: Footer
- 4-column layout on desktop, stacked on mobile
- Columns:
  1. Logo + tagline
  2. Product links
  3. Company links
  4. Social media icons
- Copyright notice
- Privacy Policy and Terms links

## Design Requirements

### Typography
- Font: Inter or similar modern sans-serif
- Heading hierarchy: h1 (48px), h2 (36px), h3 (24px)
- Body text: 16px base, 18px for hero subheading
- Line height: 1.5 for body, 1.2 for headings
- Font weights: 400 (regular), 600 (semibold), 700 (bold)

### Color Palette
```css
/* Primary Colors */
primary: #6366f1 (indigo-500)
primary-dark: #4f46e5 (indigo-600)
primary-light: #818cf8 (indigo-400)

/* Neutral Colors */
background: #ffffff
text-primary: #0f172a (slate-900)
text-secondary: #475569 (slate-600)
border: #e2e8f0 (slate-200)

/* Accent */
accent: #f59e0b (amber-500)
success: #10b981 (emerald-500)
```

### Spacing
- Section padding: py-16 (desktop), py-12 (mobile)
- Container max-width: 1280px
- Grid gap: gap-8 (desktop), gap-6 (mobile)
- Component padding: p-6

### Responsive Breakpoints
```
sm: 640px   (mobile)
md: 768px   (tablet)
lg: 1024px  (desktop)
xl: 1280px  (wide desktop)
```

## Component Structure

### Layout Components
- `app/layout.tsx` - Root layout with fonts and metadata
- `app/page.tsx` - Landing page composition
- `components/layout/Header.tsx` - Sticky navigation
- `components/layout/Footer.tsx` - Footer section

### Section Components
- `components/sections/Hero.tsx` - Hero section with CTA
- `components/sections/Features.tsx` - Feature cards grid
- `components/sections/Testimonials.tsx` - Social proof section
- `components/sections/CTA.tsx` - Final call-to-action
- `components/ui/*` - shadcn/ui components (button, card, etc.)

### Utility Components
- `components/ui/button.tsx` - shadcn/ui Button component
- `components/ui/card.tsx` - shadcn/ui Card component
- `lib/utils.ts` - cn() utility for class merging

## Accessibility Requirements

### WCAG 2.1 AA Compliance
- Color contrast ratio ≥ 4.5:1 for text
- Color contrast ratio ≥ 3:1 for UI components
- All interactive elements keyboard accessible
- Focus indicators visible and clear
- Semantic HTML (header, nav, main, section, footer)
- ARIA labels for icon-only buttons
- Alt text for all images
- Skip to main content link

### Keyboard Navigation
- Tab order follows visual flow
- Enter/Space activate buttons
- Escape closes mobile menu
- Arrow keys for carousel (if implemented)

## Performance Requirements

### Core Web Vitals
- Largest Contentful Paint (LCP): < 2.5s
- First Input Delay (FID): < 100ms
- Cumulative Layout Shift (CLS): < 0.1
- First Contentful Paint (FCP): < 1.8s

### Optimization
- Images: WebP format with fallback
- Images: Lazy loading for below-fold content
- Images: Responsive sizes with Next.js Image component
- CSS: Tailwind purge for production
- JavaScript: Code splitting via Next.js
- Fonts: Self-hosted with font-display: swap

### Lighthouse Scores
- Performance: ≥ 90
- Accessibility: ≥ 95
- Best Practices: ≥ 95
- SEO: ≥ 95

## SEO Requirements

### Meta Tags
```html
<title>Product Name - Value Proposition</title>
<meta name="description" content="Compelling 150-160 char description" />
<meta property="og:title" content="Product Name - Value Proposition" />
<meta property="og:description" content="Social media description" />
<meta property="og:image" content="/og-image.jpg" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
```

### Structured Data
- Organization schema
- WebSite schema with search action
- Breadcrumb schema (if multi-page)

## Animation & Interactions

### Scroll Animations
- Fade in on scroll for sections (using Intersection Observer)
- Stagger animations for feature cards
- Parallax effect for hero background (subtle)

### Hover States
- Buttons: Background color change + scale(1.05)
- Feature cards: Lift effect with shadow
- Links: Underline or color change
- Social icons: Color fill transition

### Transitions
- Duration: 200-300ms for interactive elements
- Easing: ease-in-out or custom cubic-bezier
- Smooth scroll: scroll-behavior: smooth

## Validation Rules

### Form Validation (if contact form included)
- Email: Valid email format required
- Name: Minimum 2 characters
- Message: Minimum 10 characters, maximum 500
- Real-time validation with error messages
- Submit button disabled until valid

## Error Handling
- 404 page with navigation back to home
- Error boundary for React errors
- Fallback UI for failed image loads
- Graceful degradation for JavaScript disabled

## Testing Requirements

### Unit Tests
- Component rendering tests
- Button click handlers
- Mobile menu toggle functionality
- Smooth scroll navigation
- Coverage: ≥ 90%

### E2E Tests (8 scenarios)
1. **Homepage Load**: Page loads successfully with all sections visible
2. **Navigation**: Click nav links, verify smooth scroll to sections
3. **Mobile Menu**: Open/close mobile menu, navigate to sections
4. **CTA Buttons**: Click primary CTA, verify modal opens or navigation
5. **Responsive Layout**: Test on mobile (375px), tablet (768px), desktop (1280px)
6. **Accessibility**: Keyboard navigation through all interactive elements
7. **Performance**: Lighthouse scores meet requirements
8. **SEO**: Meta tags present and correct

## File Structure
```
landing-page/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   └── favicon.ico
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   └── Footer.tsx
│   ├── sections/
│   │   ├── Hero.tsx
│   │   ├── Features.tsx
│   │   ├── Testimonials.tsx
│   │   └── CTA.tsx
│   └── ui/
│       ├── button.tsx
│       └── card.tsx
├── lib/
│   └── utils.ts
├── public/
│   ├── hero-image.png
│   ├── feature-*.svg
│   └── og-image.jpg
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

## Dependencies
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "lucide-react": "^0.294.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "playwright": "^1.40.0"
  }
}
```

## Success Criteria

1. ✅ All 6 sections render correctly
2. ✅ Fully responsive (mobile, tablet, desktop)
3. ✅ WCAG 2.1 AA compliant
4. ✅ Lighthouse scores ≥ 90 (Performance), ≥ 95 (others)
5. ✅ All E2E tests passing (8 scenarios)
6. ✅ Unit tests ≥ 90% coverage
7. ✅ SEO meta tags and structured data present
8. ✅ Smooth animations and transitions
9. ✅ Mobile menu functional
10. ✅ Keyboard navigation complete
