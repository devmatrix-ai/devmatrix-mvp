# DevMatrix Constitution Compliance Scripts

This directory contains scripts for validating compliance with the DevMatrix Constitution.

## 📋 Available Scripts

### Main Compliance Checker

**`check-constitution.sh`** - Complete compliance validation
```bash
./scripts/check-constitution.sh
```

Runs all compliance checks and generates a compliance score. Target: ≥95%

### Individual Check Scripts

1. **`check-type-hints.py`** - Validates Python type hints
   ```bash
   python3 scripts/check-type-hints.py
   ```
   - Ensures all public functions have type annotations
   - Checks parameter and return types
   - Skips private functions and tests

2. **`check-function-length.py`** - Validates function length
   ```bash
   python3 scripts/check-function-length.py --max-lines 100
   ```
   - Default max: 100 lines per function
   - Checks both Python functions and methods

3. **`check-component-length.py`** - Validates React component length
   ```bash
   python3 scripts/check-component-length.py --max-lines 300
   ```
   - Default max: 300 lines per component
   - Checks .tsx files in src/ui/src/

4. **`check-bundle-size.py`** - Validates frontend bundle size
   ```bash
   python3 scripts/check-bundle-size.py --max-size 300
   ```
   - Default max: 300KB (gzipped)
   - Requires `npm run build` first

5. **`check-accessibility.py`** - Basic accessibility validation
   ```bash
   python3 scripts/check-accessibility.py
   ```
   - Checks for ARIA labels on buttons
   - Validates alt text on images
   - Ensures interactive elements have proper roles

## 🚀 Usage

### Pre-commit Hook

Install pre-commit hooks to automatically check compliance:

```bash
pip install pre-commit
pre-commit install
```

The hooks will run on `git push` (not every commit).

### Manual Checks

```bash
# Full compliance check
./scripts/check-constitution.sh

# Individual checks
python3 scripts/check-type-hints.py
python3 scripts/check-function-length.py
python3 scripts/check-component-length.py
python3 scripts/check-bundle-size.py
python3 scripts/check-accessibility.py
```

### CI/CD Integration

The compliance check runs automatically on:
- Pull requests to `main` or `develop`
- Pushes to `main` or `develop`

See `.github/workflows/constitution-compliance.yml`

## 📊 Compliance Scoring

The main script (`check-constitution.sh`) calculates a compliance percentage:

- **100%**: Perfect compliance ✅
- **≥95%**: Excellent compliance ✅
- **≥80%**: Acceptable compliance ⚠️
- **<80%**: Below threshold ❌

## 🔧 Customization

### Adjusting Thresholds

Edit the scripts to adjust thresholds:

```python
# check-function-length.py
parser.add_argument('--max-lines', type=int, default=100)

# check-component-length.py
parser.add_argument('--max-lines', type=int, default=300)

# check-bundle-size.py
parser.add_argument('--max-size', type=int, default=300)
```

### Adding New Checks

1. Create a new Python script in `scripts/`
2. Make it executable: `chmod +x scripts/your-check.py`
3. Add it to `check-constitution.sh`
4. Update this README

## 📝 Example Output

```bash
$ ./scripts/check-constitution.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   DevMatrix Constitution Compliance Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRINCIPLE 1: Code Quality Standards
────────────────────────────────────────
[1] Checking: TypeScript strict mode enabled...
    ✓ PASS
[2] Checking: No 'any' types in production...
    ✓ PASS
[3] Checking: Python files have type hints...
    ✓ PASS

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Checks: 15
Passed: 14
Failed: 1

Compliance Score: 93.3%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚠ ACCEPTABLE COMPLIANCE (≥80%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failed checks:
  • Backend test coverage ≥80%
```

## 🐛 Troubleshooting

### "Permission denied" error

```bash
chmod +x scripts/*.sh scripts/*.py
```

### "Module not found" error

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### "npm command not found"

```bash
cd src/ui && npm install
```

## 📚 Related Documentation

- [DevMatrix Constitution](../.specify/memory/constitution.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Development Checklist](../DEVELOPMENT_CHECKLIST.md)

---

**Last Updated**: 2025-11-03  
**Version**: 1.0.0
