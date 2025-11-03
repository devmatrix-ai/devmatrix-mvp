# Contributing to DevMatrix

Thank you for your interest in contributing to DevMatrix! This guide will help you understand our development workflow, standards, and best practices.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Constitution Compliance](#constitution-compliance)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Code Review Process](#code-review-process)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Style Guides](#style-guides)

---

## 📜 Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize project quality over individual preferences
- Follow the [DevMatrix Constitution](.specify/memory/constitution.md)

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.12+
- **Node.js**: 20+
- **Docker**: Latest version
- **Git**: 2.30+

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/devmatrix/devmatrix-mvp.git
cd devmatrix-mvp

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

cd src/ui
npm install
cd ../..

# 3. Start services
docker compose up -d

# 4. Run migrations
alembic upgrade head

# 5. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 6. Verify setup
./scripts/check-constitution.sh
```

---

## ⚖️ Constitution Compliance

All contributions **MUST** comply with the [DevMatrix Constitution](.specify/memory/constitution.md).

### Running Compliance Checks

```bash
# Full compliance check (recommended before committing)
./scripts/check-constitution.sh

# Individual checks
python3 scripts/check-type-hints.py
python3 scripts/check-function-length.py
python3 scripts/check-component-length.py
python3 scripts/check-accessibility.py
```

### Common Compliance Issues

#### ❌ Type Safety Violations

```typescript
// BAD: Using 'any'
const handleData = (data: any) => { ... }

// GOOD: Proper typing
interface DataPayload {
  id: string;
  value: number;
}
const handleData = (data: DataPayload) => { ... }
```

```python
# BAD: No type hints
def process_data(data):
    return data['value']

# GOOD: Type hints
def process_data(data: Dict[str, Any]) -> int:
    return data['value']
```

---

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
# Branch naming convention
git checkout -b feature/add-export-functionality
git checkout -b bugfix/fix-websocket-reconnection
git checkout -b hotfix/security-vulnerability-fix
git checkout -b docs/update-api-documentation
```

### 2. Make Changes

- Write code following [Style Guides](#style-guides)
- Write tests (TDD preferred)
- Update documentation
- Run local compliance checks

### 3. Test Locally

```bash
# Backend
pytest --cov=src --cov-report=term-missing

# Frontend
cd src/ui && npm test && npm run build

# Constitution compliance
./scripts/check-constitution.sh
```

### 4. Commit Changes

Follow [Commit Guidelines](#commit-guidelines).

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## 🧪 Testing Requirements

### Minimum Coverage

| Layer | Required | Target |
|-------|----------|--------|
| API Routes | 90% | 95% |
| Services | 85% | 90% |
| Models | 95% | 98% |
| Utils | 90% | 95% |
| UI Components | 80% | 85% |
| Hooks | 85% | 90% |

### Test Categories

#### Unit Tests (60% of tests)

**Requirements:**
- Test individual functions in isolation
- Mock all external dependencies
- Fast execution (<10ms per test)
- No database, network, or file I/O

**Example:**

```python
def test_validate_email_with_valid_input():
    # Given
    email = "user@example.com"
    
    # When
    result = validate_email(email)
    
    # Then
    assert result is True
```

---

## 👀 Code Review Process

### As a Reviewer

**Check:**
- [ ] Constitution compliance
- [ ] Tests included and passing
- [ ] Code is readable and maintainable
- [ ] No performance regressions
- [ ] Security considerations addressed
- [ ] Documentation updated
- [ ] No unnecessary complexity

**Response Time:**
- Initial review within 24 hours
- Follow-up within 12 hours

### As an Author

**Before Requesting Review:**
- [ ] All tests passing locally
- [ ] Constitution compliance check passed
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] PR description complete

---

## 📝 Commit Guidelines

### Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(masterplan): add export to PDF` |
| `fix` | Bug fix | `fix(auth): resolve JWT expiration bug` |
| `docs` | Documentation only | `docs(api): update endpoint docs` |
| `style` | Formatting | `style: format code with black` |
| `refactor` | Code change neither fixes nor adds | `refactor(parser): simplify AST logic` |
| `perf` | Performance improvement | `perf(db): add index on user_id` |
| `test` | Adding/updating tests | `test(masterplan): add integration tests` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `ci` | CI/CD changes | `ci: add constitution check` |

### Examples

```bash
# Feature
git commit -m "feat(ui): add dark mode toggle"

# Bug fix
git commit -m "fix(websocket): handle reconnection on network error"

# Breaking change
git commit -m "feat(api)!: change masterplan response format

BREAKING CHANGE: Response now includes nested phases object"
```

---

## 🔀 Pull Request Process

### PR Checklist

Before submitting:

- [ ] Branch is up to date with `develop`
- [ ] All tests passing
- [ ] Constitution compliance: ≥95%
- [ ] Code reviewed by yourself
- [ ] Documentation updated
- [ ] No console.log or debug statements
- [ ] PR description complete

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Constitution Compliance
Constitution Compliance: 98.5%
All checks passing ✓

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

---

## 🎨 Style Guides

### Python

**Follow:**
- [PEP 8](https://pep8.org/)
- [PEP 484](https://peps.python.org/pep-0484/) (Type Hints)
- [Black](https://black.readthedocs.io/) formatting
- [Ruff](https://docs.astral.sh/ruff/) linting

**Example:**
```python
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def generate_masterplan(
    discovery_id: UUID,
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Generate a complete MasterPlan from a Discovery Document.
    
    Args:
        discovery_id: UUID of the existing discovery document
        session_id: Session identifier for tracking
        user_id: User identifier
        
    Returns:
        Dictionary containing masterplan_id and status
        
    Raises:
        DiscoveryNotFoundError: If discovery document doesn't exist
    """
    logger.info("Generating masterplan", extra={"discovery_id": str(discovery_id)})
    # Implementation...
    return {"masterplan_id": str(masterplan_id), "status": "draft"}
```

### TypeScript/React

**Follow:**
- Functional components with hooks
- Props interfaces defined
- No `any` types

**Example:**
```typescript
interface MasterPlanProgressModalProps {
  event: MasterPlanProgressEvent | null;
  open: boolean;
  onClose: () => void;
}

export function MasterPlanProgressModal({
  event,
  open,
  onClose,
}: MasterPlanProgressModalProps): JSX.Element {
  const { t } = useTranslation();
  
  if (!open || !event) {
    return null;
  }
  
  return (
    <div role="dialog" aria-modal="true">
      {/* Content */}
    </div>
  );
}
```

---

## 🔒 Security Guidelines

### Never Commit:
- API keys
- Passwords
- Private keys
- Tokens
- `.env` files

### Always:
- Use environment variables
- Hash passwords (bcrypt ≥12 rounds)
- Validate all user input
- Parameterize SQL queries
- Enable HTTPS in production

---

## 📚 Additional Resources

- [DevMatrix Constitution](.specify/memory/constitution.md)
- [Architecture Documentation](DOCS/reference/ARCHITECTURE.md)
- [API Reference](DOCS/reference/API_REFERENCE.md)
- [Troubleshooting Guide](DOCS/guides/TROUBLESHOOTING.md)

---

**Thank you for contributing to DevMatrix!** 🚀

