# Phase 8: Deployment

**Purpose**: Write validated code files to disk and create project structure

**Status**: ✅ Core (Required)

---

## Overview

Phase 8 writes all validated generated code files to the workspace directory. It creates the complete project structure with:
- Source code files
- Test files
- Configuration files
- Documentation
- Docker setup
- Migration files

## Input

- **Source**: Validated code from Phase 7
- **Contains**: Dictionary of filename -> code_content pairs

## Processing

```python
async def _phase_8_deployment(self):
    # 1. Create project directory
    workspace_path = Path(f"/workspace/orchestrated-{project_id}/")
    workspace_path.mkdir(parents=True, exist_ok=True)

    # 2. Write each file to disk
    for filename, code in generated_files.items():
        filepath = workspace_path / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(code)

    # 3. Set file permissions
    # 4. Create symlinks if needed
    # 5. Log deployment summary
```

## Output

### Deployed Project

```
/workspace/orchestrated-{uuid}/
├── src/
│   ├── models/
│   │   ├── user.py
│   │   ├── task.py
│   │   └── __init__.py
│   ├── api/
│   │   ├── routes/
│   │   │   ├── users.py
│   │   │   ├── tasks.py
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── validations/
│   │   ├── user.py
│   │   ├── task.py
│   │   └── __init__.py
│   ├── config.py
│   ├── main.py
│   └── database.py
├── tests/
│   ├── test_models.py
│   ├── test_users.py
│   ├── test_tasks.py
│   └── conftest.py
├── migrations/
│   ├── alembic.ini
│   └── versions/
│       ├── 001_create_users.py
│       └── 002_create_tasks.py
├── docs/
│   ├── API.md
│   ├── ENTITIES.md
│   ├── ARCHITECTURE.md
│   └── SETUP.md
├── scripts/
│   ├── init_db.py
│   ├── seed_data.py
│   └── run_tests.sh
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── README.md
├── pytest.ini
└── pyproject.toml
```

## Service Dependencies

### Required
- None (file system operations only)

### Optional
- None

## Deployment Strategy

### Phase Order

1. **Create Root Directory**
   ```bash
   mkdir -p /workspace/orchestrated-{uuid}/
   ```

2. **Create Subdirectories**
   ```bash
   mkdir -p src/{models,api/routes,api/schemas,validations}
   mkdir -p tests
   mkdir -p migrations/versions
   mkdir -p docs scripts
   ```

3. **Write Python Files**
   - All .py files with proper encoding (UTF-8)
   - Set executable bit on scripts
   - Preserve shebang lines

4. **Write Configuration Files**
   - requirements.txt
   - docker-compose.yml
   - Dockerfile
   - pyproject.toml
   - pytest.ini

5. **Write Documentation**
   - README.md
   - API.md
   - Architecture guides
   - Setup instructions

6. **Create Special Files**
   - .gitignore
   - .env.example
   - .env (if template)

## File Categories

| Category | Count | Purpose |
|----------|-------|---------|
| **Models** | 3-10 | SQLAlchemy ORM definitions |
| **Routes** | 5-20 | FastAPI endpoint handlers |
| **Schemas** | 5-15 | Pydantic request/response |
| **Validations** | 3-10 | Business logic validators |
| **Tests** | 5-15 | Pytest test modules |
| **Config** | 2-5 | Settings, database config |
| **Migrations** | 5-15 | Alembic migration files |
| **Docs** | 3-5 | Markdown documentation |
| **Scripts** | 2-5 | Utility scripts |
| **Docker** | 2-3 | Dockerfile, docker-compose |
| **Meta** | 2-5 | README, .gitignore, etc. |

## Performance Characteristics

- **Time**: ~1-2 seconds (disk I/O dependent)
- **Memory**: ~50-100 MB
- **Disk Space**: ~5-15 MB (project size)

## Deployment Safety Checks

```python
# Before writing
✓ Validate file paths (no ../ escapes)
✓ Check disk space available
✓ Verify no conflicts with existing files

# During writing
✓ Create parent directories as needed
✓ Atomic writes (write to temp, then move)
✓ Preserve file permissions

# After writing
✓ Verify all files written
✓ Count files and compare with expected
✓ Sample-check file contents
```

## Metrics Collected

- Total files written
- Total lines of code written
- Disk space used
- Deployment time
- Errors (if any)
- File permission changes

## Data Flow

```
Validated Code Dictionary
  {
    "src/models/user.py": code_string,
    "src/api/routes/users.py": code_string,
    "tests/test_users.py": code_string,
    ...
  }
    ↓
    └─ For each (filepath, code):
        ├─ Create parent directories
        ├─ Write file with UTF-8 encoding
        ├─ Set permissions (0o644 for code, 0o755 for scripts)
        └─ Verify write successful
            ↓
        Project Directory Structure
            ↓
            /workspace/orchestrated-{uuid}/
            ├── src/ (sources)
            ├── tests/ (test suite)
            ├── migrations/ (DB migrations)
            ├── docs/ (documentation)
            └── ... (config files)
                ↓
                Feeds to Phase 9 (Health Verification)
```

## File Permissions

```python
# Regular Python/config files
chmod 0o644 .py .txt .md .yml .yaml .json

# Executable scripts
chmod 0o755 *.sh scripts/*

# Migration files
chmod 0o644 migrations/versions/*.py

# Docker files
chmod 0o644 Dockerfile docker-compose.yml
```

## Typical Deployment Output

```
Deployment Summary:
  Project ID: 550e8400-e29b-41d4-a716-446655440000
  Location: /workspace/orchestrated-550e8400.../

Files Written: 52
  - Python source: 28 files
  - Test files: 12 files
  - Migration files: 5 files
  - Config files: 4 files
  - Documentation: 3 files

Code Written: 3,847 lines
  - Models: 486 lines
  - API: 892 lines
  - Schemas: 384 lines
  - Validations: 721 lines
  - Tests: 986 lines
  - Other: 378 lines

Disk Usage: 12.3 MB
  - Python files: 8.2 MB
  - Test files: 2.1 MB
  - Docs: 0.8 MB
  - Config: 1.2 MB

Directory Structure:
  ✓ src/models/
  ✓ src/api/routes/
  ✓ src/api/schemas/
  ✓ src/validations/
  ✓ tests/
  ✓ migrations/versions/
  ✓ docs/
  ✓ scripts/

Configuration Files:
  ✓ requirements.txt (15 dependencies)
  ✓ Dockerfile (Python 3.11)
  ✓ docker-compose.yml (PostgreSQL + App)
  ✓ pytest.ini (test config)
  ✓ pyproject.toml (project metadata)

Deployment Status: ✅ SUCCESS
  - All files written
  - All permissions set
  - All directories created
  - Ready for execution
```

## Error Handling

### Disk Space Exceeded

```python
OSError: No space left on device
```
**Resolution**: Free disk space, retry deployment

### Permission Denied

```python
PermissionError: Permission denied for /workspace/...
```
**Resolution**: Check permissions on /workspace directory

### Invalid File Path

```python
ValueError: Path contains invalid characters: ../
```
**Resolution**: Validate generated code paths

## Integration Points

- **Phase 7**: Receives validated code
- **Phase 9**: Checks deployed project health
- **Metrics**: Files written, LOC, disk space
- **Workspace**: Project stored in /workspace/{project_id}/

## Success Criteria

✅ All files written to disk
✅ Correct directory structure created
✅ File permissions set correctly
✅ All 50-60 files accounted for
✅ Total LOC > 1,000
✅ No write errors

## Deployment Verification

```python
# Verify deployment
deployed_files = list(project_dir.rglob("*.py"))
assert len(deployed_files) >= 40  # At least 40 Python files
assert sum(f.stat().st_size for f in deployed_files) > 100_000  # >100KB
assert (project_dir / "requirements.txt").exists()
assert (project_dir / "docker-compose.yml").exists()
```

## Cleanup on Failure

If deployment fails:
1. Remove partially written files
2. Remove empty directories
3. Log error details
4. Raise exception for Phase 9

## Next Phase

Output feeds to **Phase 9: Health Verification** which:
- Checks project structure validity
- Verifies all files are present
- Validates imports and dependencies
- Generates final status report

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:2767-2814
**Status**: Verified ✅
