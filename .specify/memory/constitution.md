# DevMatrix Constitution

**Version**: 1.0.0  
**Ratified**: 2025-11-03  
**Last Amended**: 2025-11-03

---

## 🎯 Mission Statement

DevMatrix is an AI-powered autonomous software development system that generates production-ready code with human-in-the-loop oversight. We prioritize **code quality**, **user experience**, **testing rigor**, and **performance** in every decision.

---

## Core Principles

### I. Code Quality Standards

**Type Safety (NON-NEGOTIABLE)**
- All TypeScript code MUST use strict mode (`"strict": true`)
- Zero `any` types allowed in production code
- Python code MUST use type hints (PEP 484)
- All public functions MUST have type annotations

**Documentation Requirements**
- All public APIs MUST have docstrings/JSDoc
- Complex algorithms MUST include inline comments explaining WHY
- README files required in component directories
- API endpoints MUST have OpenAPI/Swagger documentation

**Code Structure**
- Functions MUST be ≤100 lines (exceptions require justification)
- Components MUST be ≤300 lines
- Files MUST be ≤500 lines (except models/types)
- Cyclomatic complexity MUST be ≤10 per function

**Error Handling**
- Never swallow exceptions silently
- Log all errors with context (user_id, request_id, stack trace)
- Use custom exception classes for domain errors
- Provide meaningful error messages to users

### II. Testing Standards (NON-NEGOTIABLE)

**Coverage Requirements**
- Minimum 80% line coverage
- Minimum 75% branch coverage
- Minimum 85% function coverage
- All new features MUST include tests
- No PRs merged without passing tests

**Test Distribution**
- Unit tests: 60% of total tests
- Integration tests: 30% of total tests
- E2E tests: 10% of total tests

**Test Quality**
- Test names MUST describe behavior, not implementation
- Use Given-When-Then or Arrange-Act-Assert
- Tests MUST be deterministic (no flakiness)
- Tests MUST clean up after themselves

### III. User Experience Consistency

**Design System**
- Use design system components (GlassCard, GlassButton)
- Consistent color palette (no arbitrary colors)
- Consistent spacing (Tailwind scale: 4, 8, 12, 16, 24, 32, 48, 64px)

**Accessibility (WCAG 2.1 AA)**
- All interactive elements MUST be keyboard accessible
- All images MUST have alt text
- Color contrast MUST be ≥4.5:1 for text
- ARIA attributes for dynamic content
- Focus indicators visible and clear

**Loading States**
- All async operations MUST show loading state
- Loading indicators MUST appear within 100ms
- Progress bars for operations >3 seconds

**Internationalization**
- NO hardcoded strings in components
- All text MUST use translation keys
- Support EN and ES at minimum

### IV. Performance Requirements

**Response Times**
- API response (simple): <100ms target, <500ms max
- API response (complex): <1s target, <3s max
- Page load (initial): <2s target, <4s max
- WebSocket latency: <50ms target, <200ms max

**Frontend Performance**
- Lighthouse Performance score ≥90
- First Contentful Paint (FCP) <1.5s
- Largest Contentful Paint (LCP) <2.5s
- Cumulative Layout Shift (CLS) <0.1
- Animations MUST run at 60fps

**Bundle Size**
- Initial bundle ≤300KB (gzipped)
- Each lazy chunk ≤100KB (gzipped)

**Backend Performance**
- Database connection pooling enabled
- Redis caching for frequent queries
- N+1 query prevention (use eager loading)
- Pagination for large datasets

### V. Security Standards

**Authentication & Authorization**
- JWT with RS256 (not HS256)
- Token expiry ≤1 hour
- RBAC for all endpoints
- 2FA for admin accounts

**Data Protection**
- Passwords hashed with bcrypt (≥12 rounds)
- API keys encrypted at rest
- HTTPS only in production
- Secrets in environment variables only

**Rate Limiting**
- 100 requests/minute per user
- 1000 requests/minute per IP
- 10 failed logins then lockout (15min)

---

## Development Workflow

### Code Review Requirements
- All code MUST be peer-reviewed
- CI MUST pass before merge
- No PRs >500 lines (split into smaller PRs)
- 1 approval required (2 for breaking changes)

### Git Practices
- Conventional commits (feat:, fix:, docs:, etc.)
- Branch naming: `feature/`, `bugfix/`, `hotfix/`
- Commits MUST be atomic (one logical change)
- No force push to main/develop

### Pre-commit Checks
- Linting (ESLint, Ruff)
- Type checking (mypy, tsc)
- Formatting (Black, Prettier)

### CI Pipeline Requirements
- All tests pass
- Coverage ≥80%
- No security vulnerabilities
- Bundle size check
- Constitution compliance check

---

## Monitoring & Observability

**Logging Requirements**
- Structured logging (JSON in production)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include context: user_id, request_id, timestamp
- Never log sensitive data

**Metrics Requirements**
- Track all critical paths
- Response time percentiles (p50, p95, p99)
- Error rates by endpoint
- LLM token usage and cost

**Error Tracking**
- All unhandled exceptions tracked
- Error grouping by type
- Stack traces captured
- User impact assessment

---

## Documentation Standards

**Code Documentation**
- All public APIs documented
- Examples in documentation
- Architecture Decision Records (ADR) for major decisions

**User Documentation**
- Getting started guide
- API reference
- Troubleshooting guide
- FAQ updated quarterly

---

## Enforcement

### Automated Checks

**Pre-commit:**
- Linting
- Type checking
- Formatting

**CI Pipeline:**
- All tests pass
- Coverage ≥80%
- No security vulnerabilities
- Bundle size check
- Constitution compliance ≥95%

### Constitution Compliance Score

Target: **≥95% compliance**

Run compliance check:
```bash
./scripts/check-constitution.sh
```

---

## Governance

### Constitution Updates

**Process:**
1. Propose change via RFC (Request for Comments)
2. Team discussion (minimum 3 days)
3. Vote (requires 75% approval)
4. Update version number
5. Announce to team

### Non-Negotiable Principles

The following principles are **NON-NEGOTIABLE** and require unanimous approval to change:

1. Testing Standards (80% minimum coverage)
2. Type Safety (no `any` types)
3. Security Standards (authentication, encryption)
4. Code Review (all code must be reviewed)

### Compliance Violations

**Minor violations** (1-2 failures):
- Warning issued
- Fix required before next PR

**Major violations** (3+ failures):
- PR blocked
- Immediate fix required
- Team discussion if systemic

---

## Decision Priority Order

When in doubt, prioritize in this order:

1. **Security** - Never compromise security
2. **User Experience** - Users come first
3. **Code Quality** - Maintainability matters
4. **Performance** - Fast is better than slow
5. **Developer Happiness** - Sustainable development

---

**This constitution is a living document that evolves with our project.**

**Version History:**
- 1.0.0 (2025-11-03): Initial constitution based on codebase analysis

---

*For detailed implementation guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md)*
