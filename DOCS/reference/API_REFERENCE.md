# API & CLI Reference

Complete reference for Devmatrix CLI commands and Python API.

---

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Python API](#python-api)
3. [Configuration](#configuration)
4. [Examples](#examples)

---

## CLI Commands

### Global Options

All commands support these global options:

```bash
devmatrix [COMMAND] --help        # Show command help
devmatrix --version               # Show version
```

---

### `devmatrix generate`

Generate Python code with AI assistance and human approval.

**Syntax**:
```bash
devmatrix generate REQUEST [OPTIONS]
```

**Arguments**:
- `REQUEST` (required): Natural language description of what to generate

**Options**:
- `--workspace, -w TEXT`: Workspace ID (auto-generated if not provided)
- `--context TEXT`: Additional context as JSON string
- `--git / --no-git`: Enable/disable auto-commit to Git (default: enabled)

**Examples**:
```bash
# Basic usage
devmatrix generate "Create a function to validate email addresses"

# With custom workspace
devmatrix generate "Create a Calculator class" --workspace my-calc

# Disable Git
devmatrix generate "Create hello world" --no-git

# With context
devmatrix generate "Create API client" --context '{"base_url": "https://api.example.com"}'
```

**Output**:
```
╭───────────────────────╮
│ Generated Code        │
│ Filename: email.py    │
│ Quality Score: 8.5/10 │
╰───────────────────────╯

  1 def validate_email(email: str) -> bool:
  2     """Validate email address format."""
  3     import re
  4     pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  5     return bool(re.match(pattern, email))

AI Review:
Score: 8.5/10
Feedback: Clean implementation with proper regex validation.

Action [approve/reject/modify]:
```

**Interactive Prompts**:
1. **approve**: Write file and commit to Git
2. **reject**: Discard code (no file written)
3. **modify**: Request changes and regenerate

**Exit Codes**:
- `0`: Success (code approved and written)
- `1`: Error (API failure, invalid input, etc.)
- `2`: Rejected by user

---

### `devmatrix plan`

Create implementation plan without generating code.

**Syntax**:
```bash
devmatrix plan REQUEST [OPTIONS]
```

**Arguments**:
- `REQUEST` (required): What you want to plan

**Options**:
- `--save PATH`: Save plan to file

**Examples**:
```bash
# Basic planning
devmatrix plan "Design a caching system with Redis"

# Save to file
devmatrix plan "Build REST API" --save plan.json
```

**Output**:
```json
{
  "description": "Implementation plan for...",
  "tasks": [
    {"id": 1, "name": "...", "dependencies": []},
    {"id": 2, "name": "...", "dependencies": [1]}
  ]
}
```

---

### `devmatrix workspace`

Manage isolated workspace environments.

#### `workspace create`

Create a new workspace.

**Syntax**:
```bash
devmatrix workspace create [WORKSPACE_ID]
```

**Arguments**:
- `WORKSPACE_ID` (optional): Custom workspace ID (auto-generated if not provided)

**Example**:
```bash
devmatrix workspace create my-project
# Created workspace: /workspace/my-project
```

#### `workspace list`

List all existing workspaces.

**Syntax**:
```bash
devmatrix workspace list
```

**Output**:
```
Available workspaces:
  • my-project (12.5 KB)
  • test-workspace (3.2 KB)
  • codegen-abc123 (1.8 KB)
```

#### `workspace clean`

Clean up workspaces.

**Syntax**:
```bash
devmatrix workspace clean [WORKSPACE_ID] [OPTIONS]
```

**Options**:
- `--all`: Clean all workspaces (requires confirmation)

**Examples**:
```bash
# Clean specific workspace
devmatrix workspace clean my-project

# Clean all
devmatrix workspace clean --all
```

---

### `devmatrix files`

File operations within workspaces.

#### `files list`

List files in a workspace.

**Syntax**:
```bash
devmatrix files list WORKSPACE_ID [OPTIONS]
```

**Arguments**:
- `WORKSPACE_ID` (required): Workspace to list

**Options**:
- `--pattern TEXT`: Filter files by pattern (e.g., "*.py")

**Examples**:
```bash
# List all files
devmatrix files list my-project

# List Python files only
devmatrix files list my-project --pattern "*.py"
```

**Output**:
```
Files in my-project:
  📄 calculator.py (1.2 KB)
  📄 utils.py (856 B)
  📁 tests/
    📄 test_calculator.py (2.1 KB)
```

#### `files read`

Read and display a file.

**Syntax**:
```bash
devmatrix files read WORKSPACE_ID FILE_PATH [OPTIONS]
```

**Arguments**:
- `WORKSPACE_ID` (required): Workspace containing the file
- `FILE_PATH` (required): Path to file (relative to workspace)

**Options**:
- `--syntax / --no-syntax`: Enable/disable syntax highlighting (default: enabled)

**Example**:
```bash
devmatrix files read my-project calculator.py
```

---

### `devmatrix git`

Git operations for workspaces.

#### `git status`

Show Git status for a workspace.

**Syntax**:
```bash
devmatrix git status [WORKSPACE_ID]
```

**Arguments**:
- `WORKSPACE_ID` (optional): Workspace to check (default: current directory)

**Example**:
```bash
devmatrix git status my-project
```

**Output**:
```
Git Status for my-project:
  Branch: main
  Status: Clean working directory
  Staged: 0 files
  Modified: 0 files
  Untracked: 0 files
```

---

### `devmatrix init`

Initialize a new Devmatrix project.

**Syntax**:
```bash
devmatrix init [PROJECT_NAME]
```

**Arguments**:
- `PROJECT_NAME` (optional): Project name (default: current directory name)

**Example**:
```bash
devmatrix init my-ai-project
```

**Creates**:
- Project structure in PostgreSQL
- Initial workspace
- Configuration files

---

### `devmatrix info`

Display system information and health status.

**Syntax**:
```bash
devmatrix info
```

**Output**:
```
Devmatrix v0.1.0

System Status:
  ✓ PostgreSQL: Connected
  ✓ Redis: Connected
  ✓ API Key: Configured
  ✓ Workspace: /workspace (writable)

Configuration:
  • Anthropic Model: claude-sonnet-4.5
  • Default Workspace: /workspace
  • Git Auto-commit: Enabled
```

---

## Python API

### CodeGenerationAgent

Main agent for code generation workflows.

```python
from src.agents.code_generation_agent import CodeGenerationAgent

# Initialize agent
agent = CodeGenerationAgent(api_key="your_key")  # Optional, uses env var

# Generate code
result = agent.generate(
    user_request="Create a function to calculate fibonacci",
    workspace_id="my-project",  # Optional, auto-generated if not provided
    context={"language": "python"},  # Optional
    git_enabled=True  # Optional, default: True
)

# Access results
print(result["generated_code"])
print(result["quality_score"])
print(result["git_commit_hash"])
```

**Parameters**:
- `user_request` (str, required): Natural language description
- `workspace_id` (str, optional): Workspace identifier
- `context` (dict, optional): Additional context
- `git_enabled` (bool, optional): Enable Git integration (default: True)

**Returns** (dict):
```python
{
    "generated_code": str,        # The generated Python code
    "target_filename": str,        # Suggested filename
    "approval_status": str,        # "approved", "rejected", or "needs_modification"
    "file_written": bool,          # Whether file was written
    "file_path": str,              # Path to written file
    "quality_score": float,        # 0-10 quality score
    "workspace_id": str,           # Workspace used
    "git_committed": bool,         # Whether code was committed
    "git_commit_hash": str,        # Short commit hash (8 chars)
    "git_commit_message": str,     # Commit message
    "messages": list[dict]         # Full conversation history
}
```

---

### PlanningAgent

Agent for creating implementation plans.

```python
from src.agents.planning_agent import PlanningAgent

agent = PlanningAgent(api_key="your_key")

plan = agent.plan(
    request="Build a REST API with FastAPI"
)

print(plan["description"])
for task in plan["tasks"]:
    print(f"- {task['name']}")
```

**Returns** (dict):
```python
{
    "description": str,           # Plan description
    "tasks": list[dict],          # List of tasks
    "dependencies": dict,         # Task dependencies
    "estimated_time": str         # Time estimate (if available)
}
```

---

### WorkspaceManager

Manage isolated workspace environments.

```python
from src.tools.workspace_manager import WorkspaceManager

# Create workspace
ws = WorkspaceManager(workspace_id="my-project", auto_cleanup=False)
ws.create()

# Write file
file_path = ws.write_file("code.py", "print('Hello, World!')")

# Read file
content = ws.read_file("code.py")

# Check existence
if ws.file_exists("code.py"):
    print("File exists")

# List files
files = ws.list_files()
dirs = ws.list_dirs()

# Get workspace info
size = ws.get_size()
path = ws.get_path()

# Clean up
ws.cleanup()

# Context manager (auto-cleanup)
with WorkspaceManager("temp-project") as ws:
    ws.write_file("temp.py", "# Temporary")
    # Auto-cleaned on exit
```

---

### FileOperations

Low-level file operations.

```python
from src.tools.file_operations import FileOperations
from pathlib import Path

file_ops = FileOperations(base_path=Path("/workspace/my-project"))

# Write
file_ops.write_file("test.py", "print('test')")

# Read
content = file_ops.read_file("test.py")

# Append
file_ops.append_file("test.py", "\nprint('more')")

# Delete
file_ops.delete_file("test.py")

# Directory operations
file_ops.create_dir("subdir")
files = file_ops.list_files()
dirs = file_ops.list_dirs()

# File info
info = file_ops.get_file_info("test.py")
print(info["size"], info["modified"])

# Tree view
tree = file_ops.get_tree(max_depth=3)
```

---

### GitOperations

Git repository management.

```python
from src.tools.git_operations import GitOperations

git = GitOperations(repo_path="/workspace/my-project")

# Get status
status = git.get_status()
print(status["branch"])
print(status["staged"])
print(status["modified"])

# Add files
git.add_files(["file1.py", "file2.py"])
git.add_all()

# Commit
commit_info = git.commit(
    message="feat: add new feature",
    author="Name <email@example.com>"  # Optional
)
print(commit_info["hash"])

# Get changes
diff = git.get_diff(staged=True)
changed_files = git.get_changed_files()

# History
last_commit = git.get_last_commit()
history = git.get_file_history("file.py", max_count=10)
```

---

### AnthropicClient

LLM integration client.

```python
from src.llm.anthropic_client import AnthropicClient

client = AnthropicClient(api_key="your_key", model="claude-sonnet-4.5")

# Generate response
response = client.generate(
    messages=[
        {"role": "user", "content": "Write a hello world function"}
    ],
    system="You are a Python expert",  # Optional
    temperature=0.7,                    # Optional
    max_tokens=2048                     # Optional
)

print(response["content"])
print(response["usage"]["input_tokens"])
print(response["usage"]["output_tokens"])

# Token counting
tokens = client.count_tokens("Sample text to count")

# Cost calculation
cost = client.calculate_cost(
    input_tokens=1000,
    output_tokens=500
)
print(f"Cost: ${cost:.4f}")
```

---

### PostgresManager

Database persistence layer.

```python
from src.state.postgres_manager import PostgresManager

db = PostgresManager()

# Create project
project_id = db.create_project(
    name="My AI Project",
    description="An AI-powered application"
)

# Create task
task_id = db.create_task(
    project_id=project_id,
    agent_name="CodeGenerationAgent",
    task_type="code_generation",
    input_data="Create fibonacci function",
    output_data='{"code": "def fib(n): ..."}',
    status="running"
)

# Update task
db.update_task_status(
    task_id=task_id,
    status="completed",
    output_data='{"code": "...", "quality": 8.5}'
)

# Track costs
db.track_cost(
    task_id=task_id,
    model="claude-sonnet-4.5",
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.012
)

# Log decision
decision_id = db.log_decision(
    task_id=task_id,
    decision_point="human_approval",
    options=["approve", "reject", "modify"],
    selected_option="approve",
    rationale="Code quality is good"
)

# Query data
tasks = db.get_project_tasks(project_id)
costs = db.get_project_costs(project_id)
monthly = db.get_monthly_costs(year=2025, month=10)
```

---

### RedisManager

Caching and state management.

```python
from src.state.redis_manager import RedisManager

redis = RedisManager()

# Save workflow state
redis.save_workflow_state(
    workflow_id="wf-123",
    state={
        "step": "generate_code",
        "data": {"request": "..."}
    },
    ttl=3600  # 1 hour
)

# Get workflow state
state = redis.get_workflow_state("wf-123")

# Cache LLM response
redis.cache_llm_response(
    prompt="Write hello world",
    response={"content": "def hello(): ..."},
    ttl=3600
)

# Get cached response
cached = redis.get_cached_llm_response("Write hello world")

# Delete state
redis.delete_workflow_state("wf-123")

# Get stats
stats = redis.get_stats()
print(stats["used_memory_human"])
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional - PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=devmatrix
POSTGRES_PASSWORD=devmatrix
POSTGRES_DB=devmatrix

# Optional - Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Optional - Workspace
WORKSPACE_PATH=/workspace

# Optional - Logging
LOG_LEVEL=INFO
```

### Docker Services

Start with Docker Compose:

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Stop services
docker-compose down
```

---

## Examples

### Example 1: Simple Function Generation

```python
from src.agents.code_generation_agent import CodeGenerationAgent

agent = CodeGenerationAgent()

result = agent.generate(
    user_request="Create a function to validate phone numbers",
    workspace_id="phone-validator"
)

if result["approval_status"] == "approved":
    print(f"✓ File written: {result['file_path']}")
    print(f"✓ Quality score: {result['quality_score']}/10")
    print(f"✓ Git commit: {result['git_commit_hash']}")
```

### Example 2: Class Generation with Context

```python
agent = CodeGenerationAgent()

result = agent.generate(
    user_request="Create a DatabaseConnection class",
    workspace_id="db-utils",
    context={
        "database": "PostgreSQL",
        "features": ["connection pooling", "retry logic"]
    }
)
```

### Example 3: Workspace Management

```python
from src.tools.workspace_manager import WorkspaceManager

# Create and use workspace
with WorkspaceManager("api-client") as ws:
    # Write multiple files
    ws.write_file("client.py", api_code)
    ws.write_file("auth.py", auth_code)
    ws.write_file("README.md", docs)

    # List created files
    files = ws.list_files()
    print(f"Created {len(files)} files")

# Workspace auto-cleaned after context exit
```

### Example 4: Git Workflow

```python
from src.tools.git_operations import GitOperations

git = GitOperations("/workspace/my-project")

# Stage changes
git.add_files(["feature.py", "tests/test_feature.py"])

# Commit
commit = git.commit(
    message="feat: add new feature with tests",
    author="Developer <dev@example.com>"
)

print(f"Committed: {commit['hash']}")
```

### Example 5: Cost Tracking

```python
from src.state.postgres_manager import PostgresManager

db = PostgresManager()

# Get monthly costs
costs = db.get_monthly_costs(year=2025, month=10)
total = sum(c["cost_usd"] for c in costs)

print(f"Total cost for October 2025: ${total:.2f}")

# Get per-project costs
project_costs = db.get_project_costs(project_id=1)
for cost in project_costs:
    print(f"{cost['model']}: ${cost['cost_usd']:.4f}")
```

---

**Last Updated**: 2025-10-11
**Version**: 0.1.0 (MVP)
