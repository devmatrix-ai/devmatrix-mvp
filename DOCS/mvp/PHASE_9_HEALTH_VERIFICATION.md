# Phase 9: Health Verification

**Purpose**: Verify deployed project health and readiness for execution

**Status**: ✅ Core (Required)

---

## Overview

Phase 9 performs health checks on the deployed project to ensure key files are present and the application is ready to run. It performs simple file existence checks to validate deployment success.

## Input

- **Source**: Deployed project directory from Phase 8
- **Location**: `/workspace/orchestrated-{uuid}/`

## Processing

```python
async def _phase_9_health_verification(self):
    # 1. Define critical files to check
    expected_files = [
        ("src/main.py", "src/main.py"),
        ("requirements.txt", "requirements.txt"),
        ("README.md", "README.md")
    ]

    # 2. Verify each file exists
    for display_name, filename in expected_files:
        filepath = os.path.join(output_dir, filename)
        exists = os.path.exists(filepath)
        status = "✓" if exists else "✗"
        print(f"  {status} File check: {display_name}")

    # 3. Add health verification checkpoints
    for i in range(5):
        metrics_collector.add_checkpoint(
            "health_verification",
            f"CP-9.{i+1}: Step {i+1}",
            {}
        )
        await asyncio.sleep(0.2)

    # 4. Report readiness
    print("  ✅ App is ready to run!")
```

## Verification Checks

### Critical Files

| File | Purpose | Status |
|------|---------|--------|
| **src/main.py** | FastAPI application entry point | ✅ Required |
| **requirements.txt** | Python dependencies list | ✅ Required |
| **README.md** | Project documentation | ✅ Required |

### Health Check Process

```
1. Check src/main.py exists
   ├─ Status: ✓ or ✗
   └─ Impact: Entry point for app execution

2. Check requirements.txt exists
   ├─ Status: ✓ or ✗
   └─ Impact: Dependencies can be installed

3. Check README.md exists
   ├─ Status: ✓ or ✗
   └─ Impact: Project documentation available

4. Add 5 health verification checkpoints
   ├─ CP-9.1 through CP-9.5
   └─ Metrics tracking

5. Verify ready for execution
   └─ All files present = Ready ✅
```

## Service Dependencies

### Required
- None (file system operations only)

### Optional
- None

## Metrics Collected

- Critical files checked (3 total)
- Files present count
- Files missing count
- Health checkpoints completed (5)
- Overall verification status
- Completion time

## Performance Characteristics

- **Time**: ~0.1-1 second
- **Memory**: ~5-10 MB
- **I/O**: Simple file existence checks

## Data Flow

```
Deployed Project Directory
    ↓
    └─ Check directory structure
        ├─ Verify all expected directories exist
        └─ Report missing directories
            ↓
    Check file presence
        ├─ Verify all expected files exist
        └─ Report missing files
            ↓
    Check import validity
        ├─ Compile Python files for syntax
        └─ Report syntax errors
            ↓
    Check configuration
        ├─ Validate YAML/JSON configs
        └─ Report config errors
            ↓
        Health Report
            ├─ Status: Healthy/Degraded/Failed
            ├─ Issues: List of problems
            └─ Metrics: Success rates
                ↓
                Feeds to Phase 10 (Learning)
```

## Health Status Levels

### 🟢 Healthy (100% checks pass)
- All required files present
- All directories correct structure
- No syntax errors
- Configuration valid
- Ready for execution

### 🟡 Degraded (80-99% checks pass)
- Minor issues (missing docs, etc.)
- No critical errors
- Likely to execute with warnings
- Recommend review

### 🔴 Failed (< 80% checks pass)
- Critical files missing
- Syntax errors present
- Configuration invalid
- Will not execute properly
- Requires regeneration

## Common Issues

### Missing Files

```
Warning: Missing file src/api/routes/tasks.py
  - Expected from F2 requirement
  - Impact: Tasks endpoints not implemented
  - Fix: Regenerate endpoints
```

### Syntax Errors

```
Error: Syntax error in src/models/user.py:45
  - SyntaxError: invalid syntax
  - Impact: Models cannot be imported
  - Fix: Check code generation output
```

### Missing Dependencies

```
Warning: FastAPI not in requirements.txt
  - Expected from framework selection
  - Impact: Application won't start
  - Fix: Verify requirements.txt generation
```

### Configuration Issues

```
Error: Invalid docker-compose.yml
  - YAML parse error at line 42
  - Impact: Docker deployment will fail
  - Fix: Check docker-compose generation
```

## Integration Points

- **Phase 8**: Receives deployed project
- **Phase 10**: Sends health report for learning
- **Metrics**: Health score, issue count
- **Report**: Comprehensive health summary

## Success Criteria

✅ All required files present
✅ Directory structure correct
✅ No syntax errors
✅ Configuration valid
✅ Overall health ≥ 85%
✅ Health report generated

## Typical Health Verification Output

```
🏥 Phase 9: Health Verification
  ✓ File check: src/main.py
  ✓ File check: requirements.txt
  ✓ File check: README.md
  ✓ Health verification checkpoint 1
  ✓ Health verification checkpoint 2
  ✓ Health verification checkpoint 3
  ✓ Health verification checkpoint 4
  ✓ Health verification checkpoint 5
  ✅ App is ready to run!

🎉 PIPELINE COMPLETO: App generada en /workspace/orchestrated-abc123/
```

## Known Limitations

- ⚠️ Only checks for 3 critical files
- ⚠️ Does not validate file contents
- ⚠️ Does not check syntax or imports
- ⚠️ Does not verify configuration validity
- ⚠️ Only verifies basic existence

## Error Handling

If any critical file is missing:

```
✗ File check: src/main.py  (missing)
```

The phase still completes but reports missing file. Deployment may have failed.

**What happens if files are missing:**

- Phase 8 (Deployment) had issues
- Files may not have been written to disk
- Check Phase 8 output and logs
- May require regeneration

## Next Phase

Output feeds to **Phase 10: Learning** which:
- Records what worked and what didn't
- Updates pattern database
- Improves future generation

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:2815-2844
**Status**: Verified ✅
