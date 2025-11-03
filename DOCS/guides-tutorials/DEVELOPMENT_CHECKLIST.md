# Development Checklist

Quick reference checklist for common development tasks.

## 📋 Before Starting Work

- [ ] Pull latest changes: `git pull origin develop`
- [ ] Create feature branch: `git checkout -b feature/my-feature`
- [ ] Services running: `docker compose up -d`
- [ ] Dependencies up to date: `pip install -r requirements.txt && cd src/ui && npm install`

## 🔨 During Development

### Every Save
- [ ] No linting errors
- [ ] No type errors
- [ ] Code compiles

### Every Feature
- [ ] Tests written (TDD preferred)
- [ ] Tests passing
- [ ] Documentation updated

### Every Commit
- [ ] Follows conventional commit format
- [ ] Commit message is descriptive
- [ ] Changes are atomic (one logical change)

## ✅ Before Committing

- [ ] All tests passing: `pytest && cd src/ui && npm test`
- [ ] Constitution compliance: `./scripts/check-constitution.sh`
- [ ] No console.log statements
- [ ] No commented-out code
- [ ] Self-review completed

## 🚀 Before Creating PR

- [ ] Branch up to date: `git rebase develop`
- [ ] All commits squashed if needed
- [ ] PR description complete
- [ ] Screenshots added (if UI changes)
- [ ] Breaking changes documented
- [ ] Changelog updated (if user-facing)

## 📝 After PR Created

- [ ] All CI checks passing
- [ ] Responded to review comments
- [ ] Requested re-review after changes
- [ ] Merged after approval

## 🎉 After Merge

- [ ] Delete feature branch
- [ ] Verify deployment (if applicable)
- [ ] Close related issues
- [ ] Update project board

---

## 📊 Constitution Compliance Targets

| Check | Target | Current |
|-------|--------|---------|
| Test Coverage | ≥80% | Check with `pytest --cov` |
| Type Hints | 100% | Check with `check-type-hints.py` |
| Function Length | ≤100 lines | Check with `check-function-length.py` |
| Component Length | ≤300 lines | Check with `check-component-length.py` |
| Overall Compliance | ≥95% | Check with `check-constitution.sh` |

---

## 🐛 Debugging Tips

### Backend Issues
```bash
# Check logs
docker compose logs api

# Enter container
docker compose exec api bash

# Run specific test
pytest tests/path/to/test.py::test_name -v
```

### Frontend Issues
```bash
# Check browser console
# Open DevTools → Console

# Check TypeScript errors
cd src/ui && npm run build

# Run specific test
npm test -- MasterPlanProgressModal.test.tsx
```

### Database Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Connect to database
docker compose exec postgres psql -U devmatrix -d devmatrix

# Run migration
alembic upgrade head
```

---

## 🔍 Quick Commands

```bash
# Full test suite
pytest && cd src/ui && npm test && cd ../..

# Format code
black src/ && cd src/ui && npm run lint:fix && cd ../..

# Check types
mypy src/ && cd src/ui && npm run build && cd ../..

# Constitution compliance
./scripts/check-constitution.sh

# Update dependencies
pip install -r requirements.txt && cd src/ui && npm install && cd ../..

# Clean up
docker compose down -v && rm -rf src/ui/node_modules src/ui/dist
```

---

**Quick Reference**: Keep this checklist handy during development!

