# Infrastructure Generation - Troubleshooting

## Common Issues and Solutions

### Template Issues

#### Issue 1: Template Not Found

**Error Message**:
```
jinja2.exceptions.TemplateNotFound: docker/python_fastapi.dockerfile
```

**Cause**: Template file doesn't exist or isn't in the correct location

**Solutions**:

**A. Verify template exists locally**:
```bash
ls -la templates/docker/python_fastapi.dockerfile
# Should show the file

# If missing, create it:
mkdir -p templates/docker
# Copy template from repository or create new one
```

**B. Check Docker container has templates**:
```bash
docker exec devmatrix-api ls -la /app/templates/docker/
# Should show all templates

# If empty/missing:
# 1. Verify Dockerfile copies templates
grep "COPY templates" Dockerfile
# Should have: COPY templates/ ./templates/

# 2. Rebuild container
docker compose build api --no-cache
docker compose up -d api
```

**C. Check templates_dir configuration**:
```python
# In infrastructure_generation_service.py
self.templates_dir = Path(templates_dir) if templates_dir else Path(__file__).parent.parent.parent / "templates"

# Verify path resolves correctly
print(f"Templates directory: {self.templates_dir}")
print(f"Exists: {self.templates_dir.exists()}")
```

---

#### Issue 2: Template Rendering Error

**Error Message**:
```
jinja2.exceptions.UndefinedError: 'project_description' is undefined
```

**Cause**: Template references variable that wasn't provided

**Solutions**:

**A. Use default values in template**:
```jinja2
# BEFORE (fails if missing)
DESCRIPTION={{ project_description }}

# AFTER (safe with default)
DESCRIPTION={{ project_description|default("A FastAPI application") }}
```

**B. Make template block conditional**:
```jinja2
{% if project_description is defined -%}
# Description
{{ project_description }}
{% endif -%}
```

**C. Add variable to metadata extraction**:
```python
# In _extract_project_metadata()
metadata = {
    # ... other variables
    "project_description": masterplan.description or f"A {project_type} application",
}
```

**D. Verify variable name matches**:
```python
# Check metadata keys
print(f"Metadata keys: {list(metadata.keys())}")

# Check template variables
# Search for {{ variable }} in template
grep -o "{{ [a-z_]* }}" templates/docker/docker-compose.yml.j2
```

---

#### Issue 3: Extra Whitespace in Generated Files

**Problem**: Generated files have excessive blank lines

**Example**:
```yaml
services:


  app:
```

**Solutions**:

**A. Configure Jinja2 trim blocks**:
```python
self.jinja_env = Environment(
    loader=FileSystemLoader(str(self.templates_dir)),
    trim_blocks=True,      # ← Add this
    lstrip_blocks=True     # ← Add this
)
```

**B. Use `-` in template blocks**:
```jinja2
# BEFORE (creates blank lines)
{% if needs_redis %}
redis:
  image: redis:7-alpine
{% endif %}

# AFTER (clean)
{% if needs_redis -%}
redis:
  image: redis:7-alpine
{% endif -%}
```

---

### Database Issues

#### Issue 4: MasterPlan Not Found

**Error Message**:
```
AttributeError: 'NoneType' object has no attribute 'project_name'
```

**Cause**: Database query returned None (MasterPlan doesn't exist)

**Solutions**:

**A. Verify MasterPlan exists in database**:
```bash
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -c "
SELECT id, project_name, status, created_at
FROM masterplans
ORDER BY created_at DESC
LIMIT 5;
"
```

**B. Add error handling in service**:
```python
# In generate_infrastructure()
masterplan = self.db.query(MasterPlan).filter(MasterPlan.id == masterplan_id).first()
if not masterplan:
    return {
        "success": False,
        "errors": [f"MasterPlan {masterplan_id} not found"],
        "files_generated": [],
        "project_type": "unknown"
    }
```

**C. Check UUID format**:
```python
# Ensure UUID is valid
try:
    masterplan_id = uuid.UUID(masterplan_id_string)
except ValueError:
    return {"success": False, "errors": ["Invalid UUID format"]}
```

---

#### Issue 5: Attribute Error (project_description)

**Error Message**:
```
AttributeError: 'MasterPlan' object has no attribute 'project_description'
```

**Cause**: Incorrect column name (database uses `description`, not `project_description`)

**Solution**:

**A. Verify database schema**:
```bash
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -c "\d masterplans"
# Look for column names - should be "description", not "project_description"
```

**B. Fix code to use correct column**:
```python
# BEFORE (WRONG)
project_description = masterplan.project_description or "Default"

# AFTER (CORRECT)
project_description = masterplan.description or "Default"
```

**C. Search and replace all occurrences**:
```bash
# Find all references
grep -n "project_description" src/services/infrastructure_generation_service.py

# Replace with correct column name
sed -i 's/masterplan\.project_description/masterplan.description/g' src/services/infrastructure_generation_service.py
```

---

### Docker Issues

#### Issue 6: Permission Denied Writing Files

**Error Message**:
```
PermissionError: [Errno 13] Permission denied: '/workspace/project/Dockerfile'
```

**Cause**: Container doesn't have write permissions to workspace directory

**Solutions**:

**A. Check workspace volume permissions**:
```bash
# On host
ls -ld /workspace
# Should be writable by container user (usually 1000:1000)

# Fix permissions
sudo chown -R 1000:1000 /workspace
sudo chmod -R 755 /workspace
```

**B. Verify workspace_path is correct**:
```python
# In orchestration service
workspace_path = Path("/workspace/project-name")
print(f"Workspace path: {workspace_path}")
print(f"Exists: {workspace_path.exists()}")
print(f"Is directory: {workspace_path.is_dir()}")
print(f"Writable: {os.access(workspace_path, os.W_OK)}")
```

**C. Create directory with correct permissions**:
```python
workspace_path.mkdir(parents=True, exist_ok=True)
os.chmod(workspace_path, 0o755)
```

---

#### Issue 7: Docker Compose Syntax Error

**Error Message**:
```
ERROR: yaml.scanner.ScannerError: mapping values are not allowed here
```

**Cause**: Generated docker-compose.yml has invalid YAML syntax

**Solutions**:

**A. Validate YAML syntax**:
```bash
# Install yamllint
pip install yamllint

# Validate generated file
yamllint /workspace/project/docker-compose.yml

# Or use Python
python3 << EOF
import yaml
with open('/workspace/project/docker-compose.yml') as f:
    yaml.safe_load(f)
print("Valid YAML")
EOF
```

**B. Check for common YAML issues**:
```yaml
# WRONG - missing space after colon
services:
  app:
    environment:
      - KEY:value

# CORRECT - space after colon
services:
  app:
    environment:
      - KEY: value
```

**C. Review template indentation**:
```jinja2
# Ensure consistent indentation (2 spaces)
services:
  app:
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL={{ db_url }}
```

---

### Detection Issues

#### Issue 8: Wrong Project Type Detected

**Problem**: FastAPI project detected as "unknown" or wrong type

**Solutions**:

**A. Verify detection keywords**:
```python
# Check what text is being analyzed
text = f"{masterplan.project_name} {masterplan.description or ''}"
for task in tasks:
    text += f" {task.name} {task.description}"
print(f"Analyzed text: {text}")

# Check if keywords present
print(f"Has 'fastapi': {'fastapi' in text.lower()}")
print(f"Has 'uvicorn': {'uvicorn' in text.lower()}")
```

**B. Add more keywords to detection**:
```python
# In _detect_project_type()
if any(keyword in text for keyword in [
    "fastapi", "uvicorn", "pydantic",
    "fast api", "python api", "rest api python"  # ← Add more
]):
    return "fastapi"
```

**C. Manual override**:
```python
# Add project_type parameter to service
async def generate_infrastructure(
    self,
    masterplan_id: uuid.UUID,
    workspace_path: Path,
    project_type: str = None  # ← Optional override
):
    if not project_type:
        project_type = self._detect_project_type(masterplan, tasks)
```

---

#### Issue 9: Redis Not Detected When Needed

**Problem**: Project needs Redis but docker-compose.yml doesn't include it

**Solutions**:

**A. Verify Redis keywords**:
```python
# Check detection
text = f"{masterplan.project_name} {masterplan.description or ''}"
for task in tasks:
    text += f" {task.name} {task.description}"

needs_redis = any(keyword in text.lower() for keyword in ["redis", "cache", "caching"])
print(f"Needs Redis: {needs_redis}")
print(f"Text analyzed: {text}")
```

**B. Add more Redis keywords**:
```python
redis_keywords = [
    "redis", "cache", "caching",
    "session storage", "rate limiting",  # ← Add more
    "pub/sub", "message queue"
]
needs_redis = any(keyword in text.lower() for keyword in redis_keywords)
```

**C. Manual configuration**:
```python
# Force Redis inclusion
metadata["needs_redis"] = True
```

---

### Runtime Issues

#### Issue 10: Generated Project Won't Start

**Error Message**:
```
ERROR: for app  Cannot start service app: driver failed programming external connectivity
```

**Cause**: Port already in use

**Solutions**:

**A. Check port usage**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port in .env
PORT=8001
```

**B. Stop conflicting containers**:
```bash
# List all containers using port 8000
docker ps --filter publish=8000

# Stop them
docker stop <container_id>
```

**C. Change port in docker-compose.yml**:
```yaml
services:
  app:
    ports:
      - "8001:8000"  # Host port 8001, container port 8000
```

---

#### Issue 11: Database Connection Failed

**Error Message**:
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Cause**: Database service not ready yet

**Solutions**:

**A. Check database health**:
```bash
docker-compose ps
# postgres should show "healthy"

# Check logs
docker-compose logs postgres
```

**B. Wait for database to be ready**:
```python
# Add startup delay in app code
import time
import psycopg2

def wait_for_db(database_url: str, max_retries: int = 30):
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            return
        except psycopg2.OperationalError:
            print(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(1)
    raise Exception("Database not ready")

# Call before starting app
wait_for_db(settings.DATABASE_URL)
```

**C. Verify database credentials**:
```bash
# Test connection manually
docker-compose exec postgres psql -U app_user -d project_db
# Should connect successfully

# Check credentials match
docker-compose exec app env | grep DATABASE_URL
docker-compose exec postgres env | grep POSTGRES_
```

---

#### Issue 12: Health Check Failing

**Error Message**:
```
unhealthy: Health check failed
```

**Solutions**:

**A. Check health endpoint**:
```bash
# Test health endpoint manually
docker-compose exec app curl http://localhost:8000/health
# Should return {"status":"healthy"}

# Check if endpoint exists in code
grep -r "health" src/
```

**B. Verify health check configuration**:
```dockerfile
# In Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Increase start-period if app is slow to start
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**C. Check app logs**:
```bash
docker-compose logs app
# Look for startup errors or exceptions
```

---

### Workflow Issues

#### Issue 13: Infrastructure Generation Skipped

**Problem**: MGE V2 completes but infrastructure files not generated

**Solutions**:

**A. Verify Step 6 is executed**:
```python
# In mge_v2_orchestration_service.py
# Check for Step 6: Infrastructure Generation

# Look for this block
yield {
    "type": "status",
    "phase": "infrastructure_generation",
    "message": "Generating project infrastructure..."
}
```

**B. Check workspace_path is provided**:
```python
# In orchestrate_masterplan_execution()
if workspace_path:  # ← This must be True
    infra_result = await infra_service.generate_infrastructure(...)
else:
    print("WARNING: workspace_path not provided, skipping infrastructure")
```

**C. Verify service import**:
```python
# At top of file
from src.services.infrastructure_generation_service import InfrastructureGenerationService

# If import fails, infrastructure generation won't run
```

---

#### Issue 14: Partial Infrastructure Generated

**Problem**: Some files generated, others missing

**Solutions**:

**A. Check error logs**:
```python
# Infrastructure service returns errors list
infra_result = {
    "success": True/False,
    "files_generated": [...],
    "errors": [...]  # ← Check this
}

# Log errors
for error in infra_result.get("errors", []):
    print(f"ERROR: {error}")
```

**B. Verify all templates exist**:
```bash
ls -la templates/docker/
ls -la templates/config/
ls -la templates/git/

# Should show:
# docker/python_fastapi.dockerfile
# docker/docker-compose.yml.j2
# config/env_fastapi.example.j2
# config/requirements_fastapi.txt.j2
# git/README_fastapi.md.j2
# git/gitignore_python.txt
```

**C. Add error handling for each file**:
```python
# In generate_infrastructure()
for template_name, output_filename in file_mappings:
    try:
        # Generate file
        ...
        files_generated.append(output_filename)
    except Exception as e:
        logger.error(f"Failed to generate {output_filename}: {str(e)}")
        errors.append(f"{output_filename}: {str(e)}")
        # Continue with other files
```

---

## Debugging Techniques

### Enable Debug Logging

```python
# In infrastructure_generation_service.py
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add debug statements
logger.debug(f"Project type detected: {project_type}")
logger.debug(f"Metadata: {metadata}")
logger.debug(f"Template directory: {self.templates_dir}")
```

### Test Template Rendering Manually

```python
# Create test script
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

templates_dir = Path("templates/")
env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Test specific template
template = env.get_template("docker/docker-compose.yml.j2")
output = template.render(
    project_slug="test",
    app_port=8000,
    db_user="test_user",
    db_password="test_pass",
    db_name="test_db",
    needs_redis=True
)

print(output)
```

### Verify Database State

```bash
# Check MasterPlan
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix << EOF
SELECT
  id,
  project_name,
  description,
  status,
  created_at
FROM masterplans
ORDER BY created_at DESC
LIMIT 5;
EOF

# Check Tasks
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix << EOF
SELECT
  id,
  name,
  description,
  task_type
FROM masterplan_tasks
WHERE masterplan_id = '<masterplan_id>'
LIMIT 10;
EOF
```

### Test Infrastructure Generation Directly

```python
# In Python shell
from src.services.infrastructure_generation_service import InfrastructureGenerationService
from src.database import SessionLocal
from pathlib import Path
import uuid

db = SessionLocal()
service = InfrastructureGenerationService(db=db)

masterplan_id = uuid.UUID("...")
workspace_path = Path("/tmp/test-project")
workspace_path.mkdir(exist_ok=True)

result = await service.generate_infrastructure(
    masterplan_id=masterplan_id,
    workspace_path=workspace_path
)

print(result)
```

---

## Performance Issues

### Issue 15: Template Rendering is Slow

**Problem**: Infrastructure generation takes too long

**Solutions**:

**A. Enable template caching** (already enabled by default):
```python
# Jinja2 automatically caches compiled templates
# No action needed
```

**B. Optimize metadata extraction**:
```python
# Use database query optimization
tasks = self.db.query(MasterPlanTask)\
    .filter(MasterPlanTask.masterplan_id == masterplan_id)\
    .options(defer("large_column"))\  # Defer large columns
    .all()
```

**C. Parallelize file writing**:
```python
import asyncio

async def write_files_parallel(self, files: List[Tuple[Path, str]]):
    tasks = [self._write_file_async(path, content) for path, content in files]
    await asyncio.gather(*tasks)
```

---

## Getting Help

### Collect Diagnostic Information

```bash
# System info
docker --version
docker-compose --version
python --version

# Service logs
docker-compose logs app > app.log
docker-compose logs postgres > postgres.log

# Database state
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -c "\d masterplans" > schema.log

# Generated files
ls -laR /workspace/project/ > files.log

# Container state
docker-compose ps > containers.log
docker inspect devmatrix-api > inspect.log
```

### Report Issues

Include in bug reports:
1. Error message (full stack trace)
2. Relevant logs (app.log, postgres.log)
3. MasterPlan ID and project details
4. Expected vs actual behavior
5. Steps to reproduce

### Useful Commands Reference

```bash
# Container management
docker-compose ps                    # List services
docker-compose logs -f app          # Follow app logs
docker-compose exec app bash        # Shell into app
docker-compose restart app          # Restart service
docker-compose down -v              # Stop and remove volumes

# Database debugging
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix
\d masterplans                      # Show schema
\dt                                 # List tables
SELECT * FROM masterplans LIMIT 5;  # Query data

# File inspection
docker exec devmatrix-api ls -la /app/templates/
docker exec devmatrix-api cat /app/src/services/infrastructure_generation_service.py

# Rebuild everything
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

- **[README](./README.md)** - Infrastructure generation overview
- **[Architecture](./architecture.md)** - Technical design details
- **[Templates Guide](./templates-guide.md)** - Template customization
- **[Usage Examples](./usage-examples.md)** - Complete project examples
