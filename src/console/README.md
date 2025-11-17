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
Execute powerful commands with options and arguments.

**Available Commands:**

| Command | Usage | Description |
|---------|-------|-------------|
| `run` | `run <task_name>` | Execute a named task |
| `plan` | `plan <type>` | Generate a plan (feature, refactor, analysis) |
| `test` | `test <suite>` | Run test suite |
| `show` | `show <resource>` | Display resource info (pipeline, artifacts, logs) |
| `logs` | `logs [filter]` | View logs with optional filtering |
| `cancel` | `cancel <task_id>` | Cancel running task |
| `retry` | `retry <task_id>` | Retry failed task |
| `session` | `session [action]` | Manage sessions |
| `config` | `config [key] [value]` | View/modify configuration |
| `help` | `help [command]` | Show help |
| `exit` / `q` | Exit console |

**Examples:**

```bash
# Run a task
> run authentication_feature

# Generate a feature plan
> plan feature --focus security

# Run tests
> test unit --depth comprehensive

# Show pipeline status
> show pipeline

# View error logs
> logs --level ERROR

# Get help
> help run
> help
```

### 2. **Pipeline Visualization** 📊
Real-time visual representation of task progress with rich terminal UI.

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

### 3. **Session Management** 💾
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

### 4. **Token Tracking** 🎯
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

### 5. **Artifact Previewer** 🎨
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

### 6. **Command Autocomplete** ⚡
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

### 7. **Advanced Logging** 📝
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

### Expected Backend Events

```python
# Pipeline Update
{
    "type": "progress_update",
    "data": {
        "current_task": "Running tests",
        "progress": 65,
        "total_tasks": 10,
        "completed_tasks": 6
    }
}

# Artifact Created
{
    "type": "artifact_created",
    "data": {
        "path": "/workspace/auth.py",
        "size": 1024,
        "type": "file"
    }
}

# Error Notification
{
    "type": "error",
    "data": {
        "message": "Task execution failed",
        "error_type": "AssertionError",
        "recoverable": true
    }
}
```

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
