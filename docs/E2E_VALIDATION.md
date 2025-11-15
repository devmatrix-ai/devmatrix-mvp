# E2E Validation Framework

Comprehensive end-to-end validation system for generated applications.

## Overview

The E2E Validation Framework validates complete applications through a 4-layer validation pipeline:

1. **Build Validation**: Docker Compose setup, dependency installation
2. **Unit Test Validation**: Test coverage ≥95%
3. **E2E Test Validation**: Golden tests pass (PRIMARY METRIC: ≥88% precision)
4. **Production Ready**: Documentation, security, code quality

## Architecture

```
┌─────────────────────────────────────────────┐
│         E2E Validation Pipeline             │
├─────────────────────────────────────────────┤
│                                             │
│  Layer 1: Build Validation                 │
│  ├─ Docker Compose up                      │
│  ├─ Services healthy                       │
│  └─ Dependencies installed                 │
│                                             │
│  Layer 2: Unit Test Validation             │
│  ├─ pytest (backend)                       │
│  ├─ vitest/jest (frontend)                 │
│  └─ Coverage ≥95%                          │
│                                             │
│  Layer 3: E2E Test Validation ⭐           │
│  ├─ Run golden Playwright tests            │
│  ├─ Calculate precision (passed/total)     │
│  └─ Target: ≥88% precision                 │
│                                             │
│  Layer 4: Production Ready                 │
│  ├─ README.md exists                       │
│  ├─ No hardcoded secrets                   │
│  ├─ .env.example, .gitignore               │
│  └─ Linting passes                         │
│                                             │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│         E2E Metrics Collector               │
├─────────────────────────────────────────────┤
│  - Track precision (PRIMARY METRIC)         │
│  - Per-spec breakdown                       │
│  - Historical trends                        │
│  - Generate reports                         │
└─────────────────────────────────────────────┘
```

## Components

### 1. Synthetic Specifications (`tests/e2e/synthetic_specs/`)

Template-based specifications for testing code generation:

- **Level 1** (Simple): TODO Backend API, Landing Page
- **Level 2** (Moderate): TODO Fullstack App, Blog Platform
- **Level 3** (Complex): E-commerce Minimal

Each spec includes:
- Tech stack definition
- Feature requirements
- Database schemas
- API endpoints
- Validation rules
- Performance requirements
- Success criteria

### 2. Golden E2E Tests (`tests/e2e/golden_tests/`)

Manually written Playwright tests defining expected behavior:

- `01_todo_backend_api.spec.ts` (15 tests)
- `02_landing_page.spec.ts` (8 tests)
- `03_todo_fullstack.spec.ts` (25 tests)
- `04_blog_platform.spec.ts` (30 tests)
- `05_ecommerce_minimal.spec.ts` (40 tests)

**Total: 118 golden tests**

### 3. E2E Production Validator (`src/cognitive/validation/e2e_production_validator.py`)

4-layer validation system:

```python
from cognitive.validation.e2e_production_validator import E2EProductionValidator

validator = E2EProductionValidator(
    app_path=Path("/path/to/generated/app"),
    spec_name="01_todo_backend_api",
    min_coverage=0.95,
    timeout_seconds=600
)

# Run validation
report = validator.validate()

# Cleanup
validator.cleanup()

# Check results
if report.overall_status == ValidationStatus.PASSED:
    print(f"E2E Precision: {report.precision_score:.2%}")
else:
    for layer, result in report.layers.items():
        print(f"{layer}: {result.status} - {result.message}")
```

### 4. E2E Metrics Collector (`src/cognitive/metrics/e2e_metrics_collector.py`)

Collects and analyzes validation metrics:

```python
from cognitive.metrics import E2EMetricsCollector

collector = E2EMetricsCollector()

# Collect from validation report
metrics = collector.collect_from_report(report)

# Aggregate metrics
aggregated = collector.aggregate_metrics()

# Check precision target
target_status = collector.get_precision_target_status(target=0.88)
print(f"Meets 88% target: {target_status['meets_target']}")

# Generate report
print(collector.generate_report())
```

## Creating Synthetic Specs

### Template Structure

```markdown
# [Application Name] - Level [1-3] Synthetic Spec

## Overview
Brief description of the application

## Tech Stack
- Frontend: Next.js 14, React 18, Tailwind CSS
- Backend: FastAPI, PostgreSQL, Redis
- Auth: JWT
- Deployment: Docker Compose

## Features

### F1: [Feature Name]
- Detailed feature requirements
- User stories
- Acceptance criteria

### F2: [Another Feature]
...

## Database Schema
SQL schemas with indexes

## API Endpoints
RESTful endpoints with request/response formats

## Validation Rules
Input validation requirements

## Error Handling
Error cases and messages

## Performance Requirements
Response time targets, cache hit rates

## Test Coverage Requirements
- Unit tests: ≥95%
- E2E tests: [N scenarios]

## Success Criteria
1. ✅ Criterion 1
2. ✅ Criterion 2
...
```

### Complexity Levels

**Level 1: Simple (Single Component)**
- Backend API OR Frontend page
- 1-2 services in Docker Compose
- 15-25 E2E tests
- Examples: TODO Backend API, Landing Page

**Level 2: Moderate (Full Stack)**
- Frontend + Backend + Database
- 3-4 services in Docker Compose
- 25-30 E2E tests
- Examples: TODO Fullstack App, Blog Platform

**Level 3: Complex (Production-like)**
- Frontend + Backend + Database + External Services
- 4+ services in Docker Compose
- 40+ E2E tests
- Examples: E-commerce with Stripe, SaaS Platform

## Writing Golden E2E Tests

### Test File Structure

```typescript
/**
 * Golden E2E Tests: [Application Name] (Level [1-3])
 *
 * Covers [N] scenarios for [tech stack description]
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// Helper functions
async function loginUser(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
}

test.describe('[Application] - [Category] Tests', () => {

  /**
   * Test 1: [Test description]
   */
  test('should [expected behavior]', async ({ page }) => {
    // Arrange
    await page.goto(BASE_URL);

    // Act
    await page.click('button:has-text("Action")');

    // Assert
    await expect(page.locator('text=Success')).toBeVisible();
  });

  // More tests...
});
```

### Test Coverage Guidelines

**Must Cover:**
- Happy paths (primary user flows)
- Error cases (validation, auth failures)
- Edge cases (empty states, pagination)
- Responsive design (mobile, tablet, desktop)
- Accessibility (keyboard navigation, ARIA)
- Performance (load times, cache hits)
- Security (XSS prevention, CSRF protection)

**Test Naming:**
- Use descriptive names: `should create TODO when authenticated`
- Group by feature: `describe('TODO CRUD Operations')`
- Document edge cases: `Test 10: Update TODO status (invalid transition - show error)`

## Running Validations

### Single Application Validation

```bash
# Generate application from spec
python -m cognitive.generate_app \
  --spec tests/e2e/synthetic_specs/01_todo_backend_api.md \
  --output /tmp/generated_apps/todo_backend_api

# Run validation
python scripts/validate_e2e.py \
  --app-path /tmp/generated_apps/todo_backend_api \
  --spec-name 01_todo_backend_api

# View report
cat metrics/e2e/e2e_summary.json
```

### Batch Validation

```bash
# Validate all synthetic specs
python scripts/batch_validate_e2e.py \
  --specs-dir tests/e2e/synthetic_specs \
  --output-dir /tmp/generated_apps

# Generate metrics report
python -c "
from cognitive.metrics import E2EMetricsCollector
collector = E2EMetricsCollector()
print(collector.generate_report())
"
```

## Metrics and Reporting

### Primary Metric: E2E Precision

**Definition**: Percentage of golden E2E tests that pass

```
E2E Precision = (Passed E2E Tests / Total E2E Tests) × 100%
```

**Target**: ≥88% (MVP), ≥92% (Production)

### Layer Success Rates

- **Build Success**: % of apps that build and start successfully
- **Unit Test Success**: % of apps with ≥95% test coverage
- **E2E Test Success**: % of apps passing all golden tests
- **Production Ready**: % of apps meeting quality standards

### Per-Spec Breakdown

Track precision by application complexity:

```
Level 1 (Simple):     90-95% precision expected
Level 2 (Moderate):   85-90% precision expected
Level 3 (Complex):    80-85% precision expected
```

### Historical Trend

Monitor precision improvement over time:

```
Week 1: 75% → Week 2: 82% → Week 3: 88% ✅
```

## Example Workflow

### Step 1: Create New Synthetic Spec

```bash
# Create spec template
cat > tests/e2e/synthetic_specs/06_kanban_board.md <<EOF
# Kanban Board - Level 2 Synthetic Spec

## Overview
Task management app with drag-and-drop Kanban board

## Tech Stack
- Frontend: Next.js 14, React 18, @dnd-kit, Tailwind CSS
- Backend: FastAPI, PostgreSQL
- Auth: JWT
...
EOF
```

### Step 2: Write Golden E2E Tests

```typescript
// tests/e2e/golden_tests/06_kanban_board.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Kanban Board - Drag and Drop', () => {
  test('should move card between columns', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Drag card from "To Do" to "In Progress"
    const card = page.locator('[data-card-id="1"]');
    const inProgressColumn = page.locator('[data-column="in_progress"]');

    await card.dragTo(inProgressColumn);

    // Verify card moved
    await expect(inProgressColumn.locator('[data-card-id="1"]')).toBeVisible();
  });

  // 20 more tests...
});
```

### Step 3: Generate Application

```python
from cognitive import CognitiveArchitecture

arch = CognitiveArchitecture()

# Generate from spec
app = arch.generate_application(
    spec_path="tests/e2e/synthetic_specs/06_kanban_board.md",
    output_path="/tmp/generated_apps/kanban_board"
)
```

### Step 4: Run Validation

```python
from pathlib import Path
from cognitive.validation import E2EProductionValidator
from cognitive.metrics import E2EMetricsCollector

# Validate
validator = E2EProductionValidator(
    app_path=Path("/tmp/generated_apps/kanban_board"),
    spec_name="06_kanban_board"
)

report = validator.validate()
validator.cleanup()

# Collect metrics
collector = E2EMetricsCollector()
metrics = collector.collect_from_report(report)

# Check results
if report.precision_score >= 0.88:
    print(f"✅ SUCCESS: {report.precision_score:.2%} precision")
else:
    print(f"❌ FAILED: {report.precision_score:.2%} precision (target: 88%)")

    # Analyze failures
    e2e_layer = report.layers[ValidationLayer.E2E_TESTS]
    for test_name in e2e_layer.details.get("failed_tests", []):
        print(f"  - {test_name}")
```

### Step 5: Iterate and Improve

```python
# Generate report to identify patterns
print(collector.generate_report())

# Output:
# E2E VALIDATION METRICS REPORT
# ====================================================
# 📊 Total Runs: 6
# ⏱️  Avg Duration: 245.32s
#
# 🎯 PRIMARY METRIC: E2E Precision
#    Current: 87.3%
#    Target:  88%
#    Status:  ❌ BELOW TARGET
#
# 🔍 Per-Spec Breakdown:
#    06_kanban_board      | Precision: 85.7% | Success: 85.7% | Runs: 3
#
# Common failure: Drag-and-drop timing issues
# → Fix: Add explicit waits in golden tests
# → Regenerate with improved patterns
```

## Troubleshooting

### Build Failures

**Symptom**: Layer 1 fails with "Docker build failed"

**Solutions**:
1. Check Dockerfile syntax
2. Verify base image availability
3. Check dependency compatibility
4. Increase build timeout

### Unit Test Failures

**Symptom**: Layer 2 fails with "Coverage below 95%"

**Solutions**:
1. Generate more comprehensive unit tests
2. Test edge cases and error paths
3. Add integration tests for complex flows
4. Mock external dependencies

### E2E Test Failures

**Symptom**: Layer 3 fails with "Golden tests failed"

**Solutions**:
1. Review failed test output for specific errors
2. Check timing issues (add explicit waits)
3. Verify selector stability (use data-testid)
4. Ensure services are fully initialized
5. Check for race conditions in async operations

### Production Ready Failures

**Symptom**: Layer 4 fails with "README.md too short"

**Solutions**:
1. Generate comprehensive README with:
   - Project description
   - Installation instructions
   - Usage examples
   - API documentation
2. Create .env.example with all required variables
3. Add .gitignore with common patterns
4. Run linters and fix code quality issues

## Best Practices

### Spec Writing

1. **Be Specific**: Define exact API endpoints, schemas, and validation rules
2. **Include Examples**: Provide sample requests, responses, and error messages
3. **Set Clear Criteria**: Define measurable success criteria
4. **Consider Edge Cases**: Document error handling and boundary conditions

### Test Writing

1. **Atomic Tests**: Each test should verify one specific behavior
2. **Stable Selectors**: Use data-testid attributes, avoid CSS class selectors
3. **Explicit Waits**: Wait for specific conditions, not arbitrary timeouts
4. **Clean State**: Reset database/state between tests
5. **Descriptive Names**: Test names should describe expected behavior

### Validation

1. **Run Locally First**: Validate on local machine before CI/CD
2. **Monitor Metrics**: Track precision trends to identify regressions
3. **Iterate Quickly**: Fix failures incrementally, don't batch changes
4. **Document Patterns**: Record common failure patterns and solutions

## Continuous Improvement

### Metrics-Driven Development

1. **Baseline**: Establish current E2E precision (Week 3: ~75%)
2. **Target**: Set incremental goals (Week 4: 80%, Week 5: 85%, Week 6: 88%)
3. **Measure**: Run validations after each improvement
4. **Analyze**: Identify common failure patterns
5. **Iterate**: Fix patterns, update tests, regenerate apps

### Pattern Recognition

Track failure patterns:

```
Pattern: "Authentication redirects fail"
Frequency: 15/40 failed E2E tests (37.5%)
Root Cause: Missing await on navigation
Fix: Add `await page.waitForURL()` after auth actions
Impact: +12% precision improvement
```

### Test Suite Maintenance

- **Review** golden tests quarterly for relevance
- **Update** tests when tech stack changes
- **Add** tests for new features discovered
- **Remove** obsolete tests for deprecated features

---

## Quick Reference

### Commands

```bash
# Generate app from spec
python -m cognitive.generate_app --spec [spec_path] --output [output_path]

# Run validation
python scripts/validate_e2e.py --app-path [path] --spec-name [name]

# View metrics
python -c "from cognitive.metrics import E2EMetricsCollector; print(E2EMetricsCollector().generate_report())"

# Export metrics
python -c "from cognitive.metrics import E2EMetricsCollector; E2EMetricsCollector().export_metrics(Path('metrics.json'))"
```

### Key Metrics

- **E2E Precision** (PRIMARY): ≥88% target
- **Unit Test Coverage**: ≥95% required
- **Build Success Rate**: ≥90% expected
- **Production Ready Rate**: ≥80% expected

### File Locations

- Specs: `tests/e2e/synthetic_specs/`
- Golden Tests: `tests/e2e/golden_tests/`
- Validator: `src/cognitive/validation/e2e_production_validator.py`
- Metrics: `src/cognitive/metrics/e2e_metrics_collector.py`
- Reports: `metrics/e2e/`
