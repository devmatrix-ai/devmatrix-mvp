# DevMatrix Console Tool - User Guide

A powerful command-line interface for real-time pipeline management, progress visualization, and development task orchestration.

## Quick Start

### Installation

```bash
# The console tool is part of the agentic-ai package
cd /path/to/agentic-ai

# Install dependencies (if not already done)
pip install rich pydantic python-socketio

# Verify installation
python -c "from src.console.cli import DevMatrixConsole; print('✅ Console tool ready')"
```

### Starting the Console

```bash
# Start the interactive console
python -m src.console

# Or programmatically
from src.console.cli import DevMatrixConsole
from src.console.config import Config

config = Config()
console = DevMatrixConsole(config)
console.run()
```

---

## Core Features

### 1. **Command Dispatcher** 📋
Execute commands through a complete workflow: Spec → Plan → Execute → Validate

**Core Workflow Commands:**

| Command | Usage | Description |
|---------|-------|-------------|
| `spec` | `spec <description>` | Generate specification from requirement |
| `plan` | `plan show\|generate\|review` | Show, generate, or review masterplan |
| `execute` | `execute [options]` | Execute the masterplan with 120 tasks |
| `validate` | `validate [options]` | Validate execution results |

**Utility Commands:**

| Command | Usage | Description |
|---------|-------|-------------|
| `test` | `test <suite>` | Run test suite |
| `show` | `show <resource>` | Display resource info (pipeline, artifacts, logs) |
| `logs` | `logs [filter]` | View logs with optional filtering |
| `cancel` | `cancel [task_id]` | Cancel current execution |
| `retry` | `retry [task_id]` | Retry failed task |
| `session` | `session [action]` | Manage sessions |
| `config` | `config [key] [value]` | View/modify configuration |
| `help` | `help [command]` | Show help |
| `exit` / `q` | Exit console |

**The Complete Workflow Example:**

```bash
# Phase 1: Generate Specification
> spec build a REST API with JWT authentication --focus security

# Phase 2: View and Review Masterplan
> plan show                           # Overview (default)
> plan show --view timeline           # Timeline of 5 phases
> plan show --view tasks              # Table of 120 tasks
> plan show --view stats              # Statistics
> plan show --view dependencies       # Dependency graph
> plan show --view full               # Everything combined
> plan review                         # Review before executing

# Phase 3: Execute the Plan
> execute                             # Simple execution
> execute --parallel --max-workers 8  # Parallel execution
> execute --dry-run                   # Simulate without changes

# Phase 4: Validate Results
> validate                            # Complete validation
> validate --strict                   # Strict mode (fail on warnings)
> validate --check tests              # Check specific aspect
> validate --check syntax
> validate --check coverage
> validate --check performance
```

**Command Aliases:**
- `p` → `plan`
- `s` → `show`
- `q` → `exit`
- `h` → `help`
- `?` → `help`

### 2. **Plan Visualization** 🎨 NEW
Beautiful visualization of MasterPlans with multiple views.

**Available Views:**

| View | Purpose | Shows |
|------|---------|-------|
| `overview` | Quick status | Stats, progress %, completion |
| `timeline` | Phase progress | 5 phases with completion bars |
| `tasks` | Detailed list | All 120 tasks with status |
| `stats` | Metrics | Tokens, duration, completion by phase |
| `dependencies` | Task graph | Dependency tree with ASCII art |
| `full` | Complete | All views combined |

**Visual Features:**
- 📊 Rich tables with colored output
- 🎯 Progress bars with percentage
- 🌳 Dependency graphs (ASCII art)
- 💬 Motivational messages (0%, 25%, 50%, 75%, 100%)
- 📈 Phase breakdown with emojis
- 🎪 Funny phase-specific messages

**Example Output:**
```
📋 MASTERPLAN: exec_20251116_abc123

Quick Stats
┌───────────────────────────┐
│ 📌 Total Tasks    120     │
│ ⏱️  Est. Duration  10.1m   │
│ 🔌 Est. Tokens    67,450  │
│ 📈 Progress       25.0%   │
└───────────────────────────┘

🚀 You're on fire!
```

---

### 3. **Pipeline Visualization** 📊
Real-time visual representation of execution progress with rich terminal UI.

**Features:**
- Task tree with status indicators
- Progress bars with percentage
- Collapsible task groups
- Status panels (progress, artifacts, tokens)
- Color-coded output

**Status Indicators:**
- ✅ Completed
- 🔄 In Progress
- ⏳ Pending
- ❌ Failed
- ⚠️ Warning

### 4. **Session Management** 💾
Persistent session tracking with auto-save capabilities.

**What Gets Saved:**
- Command history
- Pipeline states
- Artifacts created
- Execution metrics
- Error logs

**Session Features:**
```bash
# Create new session
> session create

# List sessions
> session list

# Load previous session
> session load <session_id>

# Get session stats
> session stats
```

### 5. **Token Tracking** 🎯
Monitor API token usage with budget alerts and cost tracking.

**Features:**
- Real-time token counting
- Budget management
- Cost breakdown by model
- Alert thresholds (75%, 90%)
- Usage history

**Configuration:**
```python
# In config.yaml
token_budget: 100000          # Total token budget
cost_limit: 10.0              # Maximum spend in USD
cost_warning_threshold: 0.75  # Alert at 75% spent
```

**Commands:**
```bash
# Show token status
> show tokens

# View cost breakdown
> config token_budget
```

### 6. **Artifact Previewer** 🎨
Smart preview and tracking of generated files with syntax highlighting.

**Features:**
- Language-aware syntax highlighting
- File size formatting (B/KB/MB/GB)
- Artifact statistics
- Direct file preview
- Metadata tracking

**Supported Languages:**
Python, JavaScript, TypeScript, Java, C++, Go, Rust, SQL, YAML, JSON, Markdown, HTML, CSS, and more.

**Commands:**
```bash
# Show artifacts
> show artifacts

# Get artifact stats
> show artifacts --stats

# Preview specific file
> show artifact <file_path>
```

### 7. **Command Autocomplete** ⚡
Intelligent autocomplete with command history search.

**Features:**
- Smart command suggestions
- History search
- Argument completion
- Option completion
- Quick recall

**Usage:**
```
Type command start + TAB for suggestions
Example: "run au" + TAB → suggests "run authentication"

Use CTRL+R to search history
```

### 8. **Advanced Logging** 📝
Powerful log aggregation and filtering system.

**Features:**
- Multiple log levels (DEBUG, INFO, WARN, ERROR)
- Source filtering
- Text search
- Log statistics
- Error summaries

**Commands:**
```bash
# Show logs
> logs

# Filter by level
> logs --level ERROR
> logs --level WARN

# Filter by source
> logs --source websocket

# Search logs
> logs --query "connection"

# Show stats
> logs --stats
```

---

## Configuration

### Configuration Files

**Global Config** (applies to all projects):
```bash
~/.devmatrix/config.yaml
```

**Project Config** (overrides global):
```bash
.devmatrix/config.yaml
```

### Configuration Options

```yaml
# Console Display
theme: "dark"                 # dark, light, auto
verbosity: "normal"           # quiet, normal, verbose, debug
animation_speed: "normal"     # slow, normal, fast
colors_enabled: true

# Pipeline
pipeline_update_interval: 500  # ms
progress_bar_style: "filled"  # filled, minimal, detailed

# Tokens
token_budget: 100000
cost_limit: 10.0
cost_warning_threshold: 0.75
token_warning_threshold: 0.90

# Session
session_auto_save_interval: 30000  # ms
session_retention_days: 30
max_session_history: 1000

# WebSocket
websocket_url: "ws://localhost:8000/socket.io/"
api_base_url: "http://localhost:8000"
websocket_timeout: 30000  # ms
reconnect_interval: 5000   # ms
max_reconnect_attempts: 10

# Logging
log_level: "INFO"
log_sources: ["cli", "websocket", "api", "task"]
max_log_entries: 10000
```

### Modify Configuration at Runtime

```bash
# View current config
> config

# Change setting
> config token_budget 50000

# View specific setting
> config websocket_url
```

---

## WebSocket Integration

The console connects to a backend server for real-time updates.

### Expected Backend Events (Opción 2 - Granular)

**Total Events per Execution**: ~180-200 events
- 1× `execution_started` - At pipeline start
- 120× `progress_update` - One per task completed (main event)
- ~45× `artifact_created` - When files are generated
- 8-10× `wave_completed` - Per parallel execution wave
- 0-20× `error` - Only on failures (with retry info)
- 1× `execution_completed` - At pipeline end

#### 1. execution_started
Emitted once at the start of execution with phase structure.

```json
{
    "type": "execution_started",
    "timestamp": "2025-11-16T14:32:15.123Z",
    "data": {
        "execution_id": "mp_abc123",
        "total_tasks": 120,
        "phases": [
            {"phase": 0, "name": "Discovery", "task_count": 5, "status": "pending"},
            {"phase": 1, "name": "Analysis", "task_count": 10, "status": "pending"},
            {"phase": 2, "name": "Planning", "task_count": 15, "status": "pending"},
            {"phase": 3, "name": "Execution", "task_count": 85, "status": "pending"},
            {"phase": 4, "name": "Validation", "task_count": 5, "status": "pending"}
        ]
    }
}
```

#### 2. progress_update (Main Event - 120 total)
Emitted once per task completion with granular progress information.

```json
{
    "type": "progress_update",
    "timestamp": "2025-11-16T14:32:18.456Z",
    "data": {
        "task_id": "task_042",
        "task_name": "Generate authentication module",
        "phase": 3,
        "phase_name": "Execution",
        "status": "completed",
        "progress": 42,
        "progress_percent": 35.0,
        "completed_tasks": 42,
        "total_tasks": 120,
        "current_wave": 3,
        "duration_ms": 2345.67,
        "subtask_status": {}
    }
}
```

**Status values**: `pending`, `in_progress`, `completed`, `failed`

#### 3. artifact_created (~45 events)
Emitted when files/directories are created during execution.

```json
{
    "type": "artifact_created",
    "timestamp": "2025-11-16T14:32:20.789Z",
    "data": {
        "artifact_id": "art_xyz789",
        "artifact_name": "auth.py",
        "artifact_type": "file",
        "file_path": "src/auth.py",
        "size_bytes": 3245,
        "task_id": "task_042",
        "metadata": {
            "language": "python",
            "lines": 98
        }
    }
}
```

**Artifact types**: `file`, `directory`, `config`, `test`, `documentation`

#### 4. wave_completed (8-10 events)
Emitted when a parallel execution wave completes.

```json
{
    "type": "wave_completed",
    "timestamp": "2025-11-16T14:33:45.123Z",
    "data": {
        "wave_number": 3,
        "tasks_in_wave": 15,
        "successful_tasks": 14,
        "failed_tasks": 1,
        "duration_ms": 45678.90,
        "artifacts_created": 12
    }
}
```

#### 5. error (0-20 events, only on failures)
Emitted when task execution fails, includes retry information.

```json
{
    "type": "error",
    "timestamp": "2025-11-16T14:34:12.456Z",
    "data": {
        "error_id": "err_fail123",
        "task_id": "task_067",
        "task_name": "Generate API endpoint",
        "error_type": "validation_error",
        "error_message": "Missing required parameter: auth_token",
        "stack_trace": "Traceback (most recent call last)...",
        "retry_count": 1,
        "max_retries": 3,
        "recoverable": true
    }
}
```

**Error types**: `validation_error`, `generation_error`, `timeout_error`, `dependency_error`

#### 6. execution_completed (1 event)
Emitted once at the end with final execution statistics.

```json
{
    "type": "execution_completed",
    "timestamp": "2025-11-16T14:45:30.789Z",
    "data": {
        "execution_id": "mp_abc123",
        "status": "completed",
        "total_tasks": 120,
        "completed_tasks": 118,
        "failed_tasks": 2,
        "skipped_tasks": 0,
        "total_duration_ms": 789012.34,
        "artifacts_created": 45,
        "final_stats": {
            "precision": 0.98,
            "total_waves": 8,
            "avg_task_duration_ms": 6575.10
        }
    }
}
```

**Final status values**: `completed`, `failed`, `partial_success`

### Backend Implementation
Events are emitted by [WebSocketManager](../../src/websocket/manager.py:883-1195):
- `emit_execution_started()` - Line 883
- `emit_progress_update()` - Line 919
- `emit_artifact_created()` - Line 985
- `emit_wave_completed()` - Line 1037
- `emit_error()` - Line 1082
- `emit_execution_completed()` - Line 1139

Integrated in [MGE V2 Orchestration Service](../../src/services/mge_v2_orchestration_service.py)

---

## Common Workflows

### Workflow 1: Running a Feature Development

```bash
# 1. Start session
> session create

# 2. View project config
> config

# 3. Generate feature plan
> plan feature --focus authentication

# 4. Run the task
> run authentication_feature

# 5. Monitor progress
> show pipeline

# 6. Check artifacts
> show artifacts

# 7. View execution logs
> logs

# 8. Check token usage
> show tokens
```

### Workflow 2: Debugging Failed Task

```bash
# 1. View error logs
> logs --level ERROR

# 2. Get more context
> logs --query "connection" --level WARN

# 3. Load previous session
> session load <session_id>

# 4. Retry failed task
> retry <task_id>

# 5. Monitor retry
> show pipeline

# 6. Review new logs
> logs
```

### Workflow 3: Cost Management

```bash
# 1. Check token budget
> show tokens

# 2. View cost breakdown
> config cost_limit

# 3. Review expensive operations
> logs --source "api"

# 4. Adjust budget if needed
> config token_budget 80000
```

---

## Tips & Tricks

### Speed Up Navigation
- Use aliases: `q` for `exit`, `h` for `help`, `?` for `help`
- Use autocomplete: Tab for command suggestions
- Use history search: Ctrl+R to search previous commands

### Optimize Token Usage
- Check budget regularly: `show tokens`
- Set reasonable limits: `config cost_limit 5.0`
- Monitor expensive operations: `logs --source api`

### Better Logging
- Filter by level: `logs --level ERROR` (only errors)
- Filter by source: `logs --source websocket` (specific component)
- Search logs: `logs --query "timeout"` (find specific issue)
- View stats: `logs --stats` (summary overview)

### Session Management
- Save frequently: Sessions auto-save every 30 seconds
- Review history: `session list` (see all sessions)
- Load old sessions: `session load <id>` (resume work)
- Analyze patterns: `session stats` (understand usage)

---

## Troubleshooting

### Console Won't Start
```bash
# Check dependencies
pip list | grep -E "rich|pydantic|socketio"

# Reinstall if needed
pip install rich pydantic python-socketio
```

### WebSocket Connection Failed
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check config
> config websocket_url

# Reconnect manually
# (Console will auto-reconnect, but manually can help debug)
```

### Token Budget Exceeded
```bash
# Check current usage
> show tokens

# Increase budget
> config token_budget 150000

# Or set stricter limit for next session
> config cost_limit 5.0
```

### Lost Previous Session
```bash
# List available sessions
> session list

# Load specific session
> session load <session_id>

# If still not found, check session directory
ls ~/.devmatrix/sessions/
```

---

## API Reference

### Core Classes

#### DevMatrixConsole
Main console application.

```python
from src.console.cli import DevMatrixConsole
from src.console.config import Config

config = Config(
    websocket_url="ws://localhost:8000/socket.io/",
    token_budget=100000
)

console = DevMatrixConsole(config)
console.run()
```

#### SessionManager
Manage persistent sessions.

```python
from src.console.session_manager import SessionManager
from pathlib import Path

manager = SessionManager(Path("~/.devmatrix"))
session_id = manager.create_session()
manager.save_command("run", {"task": "test"}, "Success", "success", 150.5)
```

#### TokenTracker
Track API token usage.

```python
from src.console.token_tracker import TokenTracker

tracker = TokenTracker(default_model="gpt-3.5-turbo", budget=100000)
tracker.add_tokens(100, 50, model="gpt-3.5-turbo", operation="completion")
status = tracker.get_status()
```

#### LogViewer
Filter and analyze logs.

```python
from src.console.log_viewer import LogViewer, LogLevel

viewer = LogViewer()
viewer.add_log(LogLevel.ERROR, "Connection failed", source="websocket")
errors = viewer.filter_logs(level=LogLevel.ERROR)
stats = viewer.get_stats()
```

---

## Examples

### Example 1: Custom Command
```python
from src.console.cli import DevMatrixConsole
from src.console.config import Config

# Initialize
config = Config(theme="dark", verbosity="verbose")
console = DevMatrixConsole(config)

# In the running console:
# > run my_custom_task
# > show pipeline
# > logs --level ERROR
```

### Example 2: Session Persistence
```bash
# Session 1: Do work
> run feature_development
> show artifacts
# Auto-saves every 30 seconds

# Session 2: Resume work
> session load <previous_session_id>
> show artifacts  # Same artifacts as before
> retry failed_task
```

### Example 3: Token Monitoring
```bash
# Check budget
> show tokens
# Output: Used: 45,000 / Budget: 100,000 (45%)

# Set warning
> config cost_warning_threshold 0.80

# Continue work and monitor
# Console alerts at 80% budget
```

---

## Performance

### Benchmarks
- Command parsing: < 1ms
- Session save: < 100ms
- Log filtering: < 10ms for 10K entries
- WebSocket events: < 50ms latency

### Optimization Tips
- Limit history: `max_session_history: 1000`
- Archive old sessions: `session_retention_days: 30`
- Filter logs by level: `logs --level ERROR` (faster than full scan)

---

## Support & Documentation

- **Main Guide**: This file (README.md)
- **Specification**: `agent-os/specs/2025-11-16-devmatrix-console-tool-evolution/`
- **Tests**: `tests/console/` (see examples of usage)
- **Source Code**: `src/console/` (well-documented with docstrings)

---

## Version

**Console Tool Version**: 2.0.0
**Release Date**: 2025-11-16
**Status**: Production Ready ✅

---

## License

Part of the agentic-ai project.
