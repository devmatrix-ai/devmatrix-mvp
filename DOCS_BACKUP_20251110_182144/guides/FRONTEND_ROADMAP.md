# DevMatrix - Frontend & System Complete Roadmap

**Version**: 1.0
**Created**: 2025-10-16
**Owner**: Ariel + Dany
**Status**: Phase 4 Planning

---

## 📋 Table of Contents

1. [Current State](#current-state)
2. [Phase 4: Task Execution (CRITICAL)](#phase-4-task-execution-critical)
3. [Phase 5: Chat UI Enhancements](#phase-5-chat-ui-enhancements)
4. [Phase 6: Advanced Features](#phase-6-advanced-features)
5. [Phase 7: Production Polish](#phase-7-production-polish)
6. [Estimation Summary](#estimation-summary)

---

## 🎯 Current State

### ✅ What's Working

**Backend (Complete)**:
- ✅ Multi-agent orchestration system (Orchestrator + 5 specialized agents)
- ✅ LangGraph workflows with state management
- ✅ Redis + PostgreSQL persistence
- ✅ Performance monitoring + caching
- ✅ Error recovery (retry + circuit breaker)
- ✅ REST API with OpenAPI docs
- ✅ Plugin system for extensibility
- ✅ 511 tests passing, 89% coverage

**Frontend (Functional but Basic)**:
- ✅ React 18 + TypeScript + Vite
- ✅ Real-time chat via Socket.IO
- ✅ Markdown rendering + syntax highlighting
- ✅ Basic message UI (user/assistant/system)
- ✅ Connection status indicator
- ✅ "Nuevo Proyecto" button
- ✅ Auto-scroll + auto-focus
- ✅ Intent detection (conversational vs orchestration)

### 🔴 Critical Gap

**⚠️ BLOCKER**: Sistema solo **planea** pero no **ejecuta**
- OrchestratorAgent genera plan de tareas
- Agentes especializados existen pero nunca se invocan
- Usuario ve plan pero nunca ve código generado
- **Sin esto, DevMatrix no es funcional**

---

## 🚨 PHASE 4: Task Execution (CRITICAL)

**Priority**: 🔴 HIGHEST
**Estimated Time**: 12-16 hours (3-4 días)
**Blocker**: Without this, the system is incomplete

### 🎯 Objective

Hacer que el OrchestratorAgent **realmente ejecute** las tareas que planea, invocando agentes especializados y generando código.

---

### Day 1-2: Execute Tasks Node (8-10 hours)

**Goal**: Add task execution to orchestrator workflow

#### Backend Changes

**File**: `src/agents/orchestrator_agent.py`

1. **Add `execute_tasks` node to workflow**:
```python
# In _build_graph()
workflow.add_node("execute_tasks", self._execute_tasks)

# Update edges
workflow.add_edge("display_plan", "execute_tasks")  # NEW
workflow.add_edge("execute_tasks", "finalize")
```

2. **Implement `_execute_tasks` method**:
```python
def _execute_tasks(self, state: OrchestratorState) -> OrchestratorState:
    """
    Execute tasks respecting dependencies.

    Uses topological sort to ensure tasks execute in correct order,
    with parallel execution for independent tasks.
    """
    tasks = state["tasks"]
    dependency_graph = state["dependency_graph"]
    workspace_id = state["workspace_id"]

    # Topological sort for execution order
    execution_order = self._topological_sort(tasks, dependency_graph)

    # Create shared scratchpad for inter-agent communication
    scratchpad = SharedScratchpad(workspace_id=workspace_id)

    # Track completed/failed tasks
    completed_tasks = []
    failed_tasks = []

    # Execute tasks in order
    for task in execution_order:
        task_id = task["id"]
        task_type = task["task_type"]
        assigned_agent = task["assigned_agent"]

        # Check dependencies are met
        dependencies_met = all(
            dep_id in completed_tasks
            for dep_id in task["dependencies"]
        )

        if not dependencies_met:
            failed_tasks.append(task_id)
            continue

        # Get agent instance
        agent = self.registry.get_agent(assigned_agent)

        # Execute task
        try:
            result = agent.execute(task, {
                "workspace_id": workspace_id,
                "scratchpad": scratchpad
            })

            if result["success"]:
                completed_tasks.append(task_id)
                task["status"] = "completed"
                task["output"] = result["output"]
            else:
                failed_tasks.append(task_id)
                task["status"] = "failed"
        except Exception as e:
            failed_tasks.append(task_id)
            task["status"] = "failed"

    state["completed_tasks"] = completed_tasks
    state["failed_tasks"] = failed_tasks

    return state
```

3. **Add topological sort helper**:
```python
def _topological_sort(
    self,
    tasks: List[Task],
    dependency_graph: Dict[str, List[str]]
) -> List[Task]:
    """
    Topological sort of tasks based on dependencies.

    Returns tasks in execution order, or empty list if circular dependency.
    """
    # Build in-degree map
    in_degree = {task["id"]: 0 for task in tasks}
    for task_id, deps in dependency_graph.items():
        in_degree[task_id] = len(deps)

    # Find tasks with no dependencies
    queue = [task for task in tasks if in_degree[task["id"]] == 0]
    result = []

    while queue:
        # Take task with no dependencies
        current_task = queue.pop(0)
        result.append(current_task)
        current_id = current_task["id"]

        # Find tasks that depend on current task
        for task in tasks:
            if current_id in dependency_graph.get(task["id"], []):
                in_degree[task["id"]] -= 1
                if in_degree[task["id"]] == 0:
                    queue.append(task)

    # If not all tasks processed, there's a cycle
    if len(result) != len(tasks):
        return []

    return result
```

#### Testing

**File**: `tests/test_orchestrator_execution.py` (NEW)

```python
import pytest
from src.agents.orchestrator_agent import OrchestratorAgent

@pytest.mark.asyncio
async def test_execute_simple_task():
    """Test executing a single task"""
    orchestrator = OrchestratorAgent()

    result = orchestrator.orchestrate(
        user_request="Create a simple calculator with add and subtract",
        workspace_id="test-calc"
    )

    # Verify execution happened
    assert result["success"] == True
    assert len(result["completed_tasks"]) > 0
    assert len(result["failed_tasks"]) == 0

    # Verify files were created
    # ... file system checks

@pytest.mark.asyncio
async def test_execute_with_dependencies():
    """Test task execution respects dependencies"""
    # Implementation task → Testing task
    # Verify testing task executes AFTER implementation

@pytest.mark.asyncio
async def test_execute_parallel_tasks():
    """Test independent tasks execute in parallel"""
    # Multiple independent implementation tasks
    # Verify they all execute
```

**Deliverables**:
- ✅ `execute_tasks` node implemented
- ✅ Topological sort working
- ✅ Task execution happens
- ✅ Tests passing

---

### Day 3: Progress Streaming (4-6 hours)

**Goal**: Real-time progress updates during task execution

#### Backend Changes

**File**: `src/agents/orchestrator_agent.py`

1. **Add progress callback support**:
```python
def __init__(self, api_key: str = None, progress_callback=None):
    self.progress_callback = progress_callback
    # ...

def _emit_progress(self, event_type: str, data: dict):
    """Emit progress event via callback if available"""
    if self.progress_callback:
        self.progress_callback(event_type, data)
```

2. **Emit events during execution**:
```python
def _execute_tasks(self, state):
    # ...

    # Emit start
    self._emit_progress('execution_start', {
        'total_tasks': len(tasks),
        'workspace_id': workspace_id
    })

    for idx, task in enumerate(execution_order):
        # Emit task start
        self._emit_progress('task_start', {
            'task_id': task_id,
            'task_type': task_type,
            'progress': f"{idx + 1}/{len(execution_order)}"
        })

        # Execute...

        if result["success"]:
            # Emit task complete
            self._emit_progress('task_complete', {
                'task_id': task_id,
                'output_files': result.get("file_paths", [])
            })
        else:
            # Emit task failed
            self._emit_progress('task_failed', {
                'task_id': task_id,
                'error': result.get("error")
            })

    # Emit execution complete
    self._emit_progress('execution_complete', {
        'total_tasks': len(tasks),
        'completed': len(completed_tasks),
        'failed': len(failed_tasks)
    })
```

**File**: `src/services/chat_service.py`

3. **Wire progress callback to WebSocket**:
```python
async def _execute_orchestration(self, conversation, request):
    # Create orchestrator with progress callback
    orchestrator = OrchestratorAgent(
        api_key=self.api_key,
        agent_registry=self.registry,
        progress_callback=lambda event, data: self._emit_ws_progress(event, data)
    )

    # Execute in background thread
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        orchestrator.orchestrate,
        request,
        conversation.workspace_id
    )

    # Yield final result
    yield {"type": "message", "content": format_result(result)}

def _emit_ws_progress(self, event_type: str, data: dict):
    """Emit progress via WebSocket"""
    # This will be called from orchestrator
    # Need to emit via socketio
    socketio.emit('message', {
        'type': 'progress',
        'event': event_type,
        'data': data
    })
```

#### Frontend Changes

**File**: `src/ui/src/hooks/useChat.ts`

4. **Add progress state**:
```typescript
interface ProgressEvent {
  event: string
  data: Record<string, any>
}

const [progress, setProgress] = useState<ProgressEvent | null>(null)

// In message handler
} else if (data.type === 'progress') {
  // Progress events during orchestration
  const progressEvent: ProgressEvent = {
    event: data.event,
    data: data.data
  }
  setProgress(progressEvent)
  if (options.onProgress) {
    options.onProgress(progressEvent)
  }
}

// Clear progress when message completes
if (data.done) {
  setProgress(null)
}

return {
  // ...
  progress,
  // ...
}
```

**File**: `src/ui/src/components/chat/ProgressIndicator.tsx` (NEW)

5. **Create progress indicator component**:
```typescript
import React from 'react'
import { ProgressEvent } from '../../hooks/useChat'

interface ProgressIndicatorProps {
  progress: ProgressEvent | null
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ progress }) => {
  if (!progress) return null

  const getProgressMessage = (event: string, data: Record<string, any>): string => {
    switch (event) {
      case 'execution_start':
        return `🚀 Ejecutando ${data.total_tasks} tareas...`
      case 'task_start':
        return `${data.progress} - ${data.description}`
      case 'task_complete':
        return `✓ ${data.task_id} completada`
      case 'task_failed':
        return `✗ ${data.task_id} falló: ${data.error}`
      case 'execution_complete':
        return `✓ Completado: ${data.completed}/${data.total_tasks} exitosas`
      default:
        return `${event}: ${JSON.stringify(data)}`
    }
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
      <span className="text-blue-600 dark:text-blue-400 text-sm font-medium">
        {getProgressMessage(progress.event, progress.data)}
      </span>
    </div>
  )
}
```

**File**: `src/ui/src/components/chat/ChatWindow.tsx`

6. **Integrate progress indicator**:
```typescript
import { ProgressIndicator } from './ProgressIndicator'

const { progress, ...rest } = useChat({ workspaceId })

return (
  <div>
    <MessageList messages={messages} />

    {/* Progress Indicator */}
    {progress && (
      <div className="mt-4">
        <ProgressIndicator progress={progress} />
      </div>
    )}

    <ChatInput ... />
  </div>
)
```

**Deliverables**:
- ✅ Progress events emitted from backend
- ✅ WebSocket streaming working
- ✅ UI shows real-time progress
- ✅ User sees task execution status

---

### Day 4: Model Configuration (2-4 hours)

**Goal**: Use different Claude models for different purposes

#### Backend Changes

**File**: `src/agents/orchestrator_agent.py`

```python
def __init__(self, api_key: str = None, ...):
    # Use Claude Opus 4.1 for complex orchestration reasoning
    self.llm = AnthropicClient(
        api_key=api_key,
        model="claude-opus-4-1-20250805"
    )
```

**File**: `src/agents/implementation_agent.py`, `testing_agent.py`, `documentation_agent.py`

```python
def __init__(self, api_key: str = None):
    # Use Claude Sonnet 4.5 for faster execution
    self.llm = AnthropicClient(
        api_key=api_key,
        model="claude-sonnet-4-5-20250929"
    )
```

**Rationale**:
- **Opus 4.1**: Complex reasoning para task decomposition y planning
- **Sonnet 4.5**: Ejecución rápida de tareas (código, tests, docs)
- **Cost optimization**: Sonnet es más barato para tareas repetitivas

**Deliverables**:
- ✅ Opus 4.1 para orchestration
- ✅ Sonnet 4.5 para agents
- ✅ Optimized cost/performance balance

---

### ✅ Phase 4 Complete Checklist

- [ ] `execute_tasks` node implemented
- [ ] Topological sort working correctly
- [ ] Agent execution happens (ImplementationAgent, TestingAgent, DocumentationAgent)
- [ ] Tasks respect dependencies
- [ ] Progress streaming via WebSocket
- [ ] UI shows real-time progress
- [ ] Model configuration optimized (Opus 4.1 + Sonnet 4.5)
- [ ] Tests passing (execution + progress + models)
- [ ] E2E test: User request → Plan → Execute → Code generated

**Success Criteria**:
- User sends "crear una calculadora simple"
- Orchestrator genera plan de 3 tareas
- Tareas se ejecutan automáticamente
- Usuario ve progreso en tiempo real
- Código Python se genera en workspace
- Tests se ejecutan y pasan
- Documentación se genera

---

## 🎨 PHASE 5: Chat UI Enhancements

**Priority**: 🟡 HIGH (after Phase 4)
**Estimated Time**: 20-24 hours (5-6 días)

---

### Sprint 1: Core Improvements (8-10 hours)

#### 1.1: Markdown Rendering (3-4 hours)

**Already Done**: Basic markdown rendering with `react-markdown`

**Enhancements Needed**:

**File**: `src/ui/src/components/chat/MessageList.tsx`

```typescript
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeRaw from 'rehype-raw'

// Add copy button to code blocks
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || '')
  const code = String(children).replace(/\n$/, '')

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    // Show toast notification
  }

  return !inline && match ? (
    <div className="relative group">
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded text-xs"
      >
        Copy
      </button>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  ) : (
    <code className={className} {...props}>
      {children}
    </code>
  )
}

<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeHighlight, rehypeRaw]}
  components={{
    code: CodeBlock
  }}
>
  {message.content}
</ReactMarkdown>
```

**Features**:
- ✅ GitHub-flavored markdown (tables, task lists, strikethrough)
- ✅ Syntax highlighting for code blocks
- ✅ Copy button on hover
- ✅ Language detection
- ✅ Inline code styling

**Deliverables**:
- Enhanced markdown rendering
- Copy-to-clipboard functionality
- Better code block styling

---

#### 1.2: Message Timestamps (1-2 hours)

**File**: `src/ui/src/components/chat/MessageList.tsx`

```typescript
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()

  // Today: show time only
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('es-AR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // This week: show day + time
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays < 7) {
    return date.toLocaleDateString('es-AR', {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Older: show full date
  return date.toLocaleDateString('es-AR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

<div className="flex items-baseline gap-2">
  <span className="font-semibold">{message.role}</span>
  <span className="text-xs text-gray-500 dark:text-gray-400">
    {formatTimestamp(message.timestamp)}
  </span>
</div>
```

**Deliverables**:
- Relative timestamps (today, yesterday, etc.)
- Localized formatting (Spanish Argentina)
- Hover to show full timestamp

---

#### 1.3: Typing Indicator (2-3 hours)

**File**: `src/ui/src/components/chat/TypingIndicator.tsx` (NEW)

```typescript
export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 px-4 py-2">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm text-gray-500 dark:text-gray-400">
        DevMatrix está pensando...
      </span>
    </div>
  )
}
```

**File**: `src/ui/src/components/chat/MessageList.tsx`

```typescript
import { TypingIndicator } from './TypingIndicator'

{isLoading && <TypingIndicator />}
```

**Deliverables**:
- Animated typing indicator
- Shows while agent is processing
- Better user feedback

---

#### 1.4: Message Actions (2-3 hours)

**File**: `src/ui/src/components/chat/MessageActions.tsx` (NEW)

```typescript
interface MessageActionsProps {
  message: ChatMessage
  onCopy: () => void
  onRegenerate?: () => void
  onDelete?: () => void
}

export const MessageActions: React.FC<MessageActionsProps> = ({
  message,
  onCopy,
  onRegenerate,
  onDelete
}) => {
  return (
    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        onClick={onCopy}
        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
        title="Copiar mensaje"
      >
        <FiCopy size={14} />
      </button>

      {message.role === 'assistant' && onRegenerate && (
        <button
          onClick={onRegenerate}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          title="Regenerar respuesta"
        >
          <FiRotateCw size={14} />
        </button>
      )}

      {onDelete && (
        <button
          onClick={onDelete}
          className="p-1 hover:bg-red-200 dark:hover:bg-red-900 rounded"
          title="Eliminar mensaje"
        >
          <FiTrash2 size={14} />
        </button>
      )}
    </div>
  )
}
```

**Deliverables**:
- Copy message to clipboard
- Regenerate assistant responses
- Delete messages
- Hover-based UI

---

### Sprint 2: Productivity Features (6-8 hours)

#### 2.1: Command Autocomplete (3-4 hours)

**File**: `src/ui/src/components/chat/CommandPalette.tsx` (NEW)

```typescript
const COMMANDS = [
  { name: '/help', description: 'Mostrar comandos disponibles' },
  { name: '/orchestrate', description: 'Iniciar orquestación multi-agente' },
  { name: '/analyze', description: 'Analizar código o proyecto' },
  { name: '/test', description: 'Ejecutar tests' },
  { name: '/clear', description: 'Limpiar historial' },
  { name: '/workspace', description: 'Ver info del workspace' }
]

interface CommandPaletteProps {
  query: string
  onSelect: (command: string) => void
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ query, onSelect }) => {
  const filtered = COMMANDS.filter(cmd =>
    cmd.name.toLowerCase().includes(query.toLowerCase())
  )

  if (filtered.length === 0) return null

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
      {filtered.map((cmd, idx) => (
        <button
          key={cmd.name}
          onClick={() => onSelect(cmd.name)}
          className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <div className="font-mono text-sm text-blue-600 dark:text-blue-400">
            {cmd.name}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {cmd.description}
          </div>
        </button>
      ))}
    </div>
  )
}
```

**File**: `src/ui/src/components/chat/ChatInput.tsx`

```typescript
const [showCommands, setShowCommands] = useState(false)

const handleInputChange = (e) => {
  const value = e.target.value
  setValue(value)

  // Show command palette if starts with /
  setShowCommands(value.startsWith('/') && value.length > 1)
}

const handleCommandSelect = (command: string) => {
  setValue(command + ' ')
  setShowCommands(false)
  inputRef.current?.focus()
}

<div className="relative">
  <textarea ... onChange={handleInputChange} />

  {showCommands && (
    <CommandPalette
      query={value.slice(1)}
      onSelect={handleCommandSelect}
    />
  )}
</div>
```

**Deliverables**:
- Command autocomplete UI
- Keyboard navigation (arrows + enter)
- Fuzzy search
- Command descriptions

---

#### 2.2: Keyboard Shortcuts (2-3 hours)

**File**: `src/ui/src/hooks/useKeyboardShortcuts.ts` (NEW)

```typescript
interface Shortcuts {
  [key: string]: () => void
}

export const useKeyboardShortcuts = (shortcuts: Shortcuts) => {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const key = [
        e.ctrlKey && 'Ctrl',
        e.shiftKey && 'Shift',
        e.altKey && 'Alt',
        e.key
      ].filter(Boolean).join('+')

      const action = shortcuts[key]
      if (action) {
        e.preventDefault()
        action()
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts])
}
```

**File**: `src/ui/src/components/chat/ChatWindow.tsx`

```typescript
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'

useKeyboardShortcuts({
  'Ctrl+k': clearMessages,
  'Ctrl+n': handleNewProject,
  'Ctrl+/': () => sendMessage('/help'),
  'ArrowUp': () => {
    // Navigate to previous message in history
  },
  'ArrowDown': () => {
    // Navigate to next message in history
  }
})
```

**Deliverables**:
- Global keyboard shortcuts
- Customizable shortcuts
- Shortcuts help modal (?)

---

#### 2.3: Export Chat (1-2 hours)

**File**: `src/ui/src/utils/exportChat.ts` (NEW)

```typescript
export const exportToMarkdown = (messages: ChatMessage[]): string => {
  const lines = [
    '# DevMatrix Chat Export',
    `**Exported**: ${new Date().toISOString()}`,
    '',
    '---',
    ''
  ]

  messages.forEach(msg => {
    lines.push(`## ${msg.role} (${msg.timestamp})`)
    lines.push('')
    lines.push(msg.content)
    lines.push('')
    lines.push('---')
    lines.push('')
  })

  return lines.join('\n')
}

export const exportToJSON = (messages: ChatMessage[]): string => {
  return JSON.stringify({
    exported_at: new Date().toISOString(),
    messages: messages
  }, null, 2)
}

export const downloadFile = (content: string, filename: string) => {
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

**File**: `src/ui/src/components/chat/ChatWindow.tsx`

```typescript
import { exportToMarkdown, downloadFile } from '../../utils/exportChat'

const handleExportMarkdown = () => {
  const md = exportToMarkdown(messages)
  downloadFile(md, `devmatrix-chat-${Date.now()}.md`)
}

<button onClick={handleExportMarkdown}>
  <FiDownload /> Exportar
</button>
```

**Deliverables**:
- Export to Markdown
- Export to JSON
- Download functionality

---

### Sprint 3: Advanced Features (6-8 hours)

#### 3.1: Conversation History (4-5 hours)

**Backend**: `src/services/chat_service.py`

```python
def list_conversations(self, workspace_id: Optional[str] = None) -> List[Dict]:
    """List all conversations, optionally filtered by workspace"""
    conversations = self.conversations.values()

    if workspace_id:
        conversations = [c for c in conversations if c.workspace_id == workspace_id]

    return [
        {
            "conversation_id": c.conversation_id,
            "workspace_id": c.workspace_id,
            "message_count": len(c.messages),
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "preview": c.messages[0].content[:100] if c.messages else ""
        }
        for c in conversations
    ]
```

**Frontend**: `src/ui/src/components/chat/ConversationSidebar.tsx` (NEW)

```typescript
interface Conversation {
  conversation_id: string
  workspace_id: string
  message_count: number
  created_at: string
  updated_at: string
  preview: string
}

export const ConversationSidebar: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    // Fetch conversations from API
    fetch('/api/conversations')
      .then(res => res.json())
      .then(setConversations)
  }, [])

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <button onClick={() => setIsOpen(!isOpen)}>
        <FiMenu />
      </button>

      {isOpen && (
        <div className="conversation-list">
          <h3>Conversaciones</h3>
          {conversations.map(conv => (
            <div key={conv.conversation_id} className="conversation-item">
              <div className="preview">{conv.preview}</div>
              <div className="meta">
                {conv.message_count} mensajes • {formatDate(conv.updated_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

**Deliverables**:
- Conversation list sidebar
- Load previous conversations
- Search conversations
- Delete conversations

---

#### 3.2: File Browser (2-3 hours)

**File**: `src/ui/src/components/chat/FileBrowser.tsx` (NEW)

```typescript
interface FileNode {
  name: string
  type: 'file' | 'directory'
  path: string
  children?: FileNode[]
}

export const FileBrowser: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [files, setFiles] = useState<FileNode[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')

  useEffect(() => {
    // Fetch workspace files
    fetch(`/api/workspaces/${workspaceId}/files`)
      .then(res => res.json())
      .then(setFiles)
  }, [workspaceId])

  const handleFileClick = async (path: string) => {
    setSelectedFile(path)
    const content = await fetch(`/api/workspaces/${workspaceId}/files/${path}`)
      .then(res => res.text())
    setFileContent(content)
  }

  return (
    <div className="flex h-full">
      {/* File tree */}
      <div className="w-64 border-r">
        <FileTree nodes={files} onFileClick={handleFileClick} />
      </div>

      {/* File preview */}
      <div className="flex-1 p-4">
        {selectedFile && (
          <CodePreview
            filename={selectedFile}
            content={fileContent}
          />
        )}
      </div>
    </div>
  )
}
```

**Deliverables**:
- File tree navigation
- File preview
- Syntax highlighting for previews
- Download files

---

### ✅ Phase 5 Complete Checklist

**Sprint 1 (Core Improvements)**:
- [ ] Enhanced markdown rendering with copy buttons
- [ ] Message timestamps (relative + absolute)
- [ ] Typing indicator animation
- [ ] Message actions (copy, regenerate, delete)

**Sprint 2 (Productivity)**:
- [ ] Command autocomplete palette
- [ ] Keyboard shortcuts system
- [ ] Export chat (Markdown + JSON)

**Sprint 3 (Advanced)**:
- [ ] Conversation history sidebar
- [ ] File browser with preview

---

## 🚀 PHASE 6: Advanced Features

**Priority**: 🟢 MEDIUM
**Estimated Time**: 16-20 hours (4-5 días)

---

### 6.1: Streaming Responses (4-5 hours)

**Goal**: Token-by-token streaming instead of waiting for complete response

**Backend**: `src/llm/anthropic_client.py`

```python
def generate_stream(
    self,
    messages: List[Dict[str, str]],
    **kwargs
) -> Iterator[str]:
    """Stream tokens as they're generated"""
    with self.client.messages.stream(
        model=self.model,
        messages=messages,
        **kwargs
    ) as stream:
        for text in stream.text_stream:
            yield text
```

**Backend**: `src/services/chat_service.py`

```python
async def _handle_conversational(self, conversation, message):
    # Stream LLM response
    async for token in self.llm.generate_stream(...):
        yield {
            "type": "token",
            "content": token,
            "done": False
        }

    # Final message
    yield {
        "type": "message",
        "content": full_response,
        "done": True
    }
```

**Frontend**: `src/ui/src/hooks/useChat.ts`

```typescript
const [streamingContent, setStreamingContent] = useState<string>('')

// In message handler
if (data.type === 'token') {
  setStreamingContent(prev => prev + data.content)
} else if (data.type === 'message' && data.done) {
  // Complete message, clear streaming
  setStreamingContent('')
  setMessages(prev => [...prev, {
    role: 'assistant',
    content: data.content,
    timestamp: new Date().toISOString()
  }])
}
```

**Deliverables**:
- Token-by-token streaming
- Progressive rendering in UI
- Cancellation support

---

### 6.2: File Upload & Attachments (4-5 hours)

**Backend**: `src/api/routes/files.py` (NEW)

```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: str = None
):
    # Save file to workspace
    workspace = WorkspaceManager(workspace_id)
    file_path = workspace.write_file(
        file.filename,
        await file.read()
    )

    return {
        "filename": file.filename,
        "path": str(file_path),
        "size": file.size
    }
```

**Frontend**: `src/ui/src/components/chat/FileUpload.tsx` (NEW)

```typescript
export const FileUpload: React.FC<{ onUpload: (file: File) => void }> = ({ onUpload }) => {
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    files.forEach(onUpload)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-gray-300 rounded-lg p-4"
    >
      <input
        type="file"
        onChange={(e) => e.target.files && onUpload(e.target.files[0])}
        className="hidden"
        id="file-upload"
      />
      <label htmlFor="file-upload" className="cursor-pointer">
        Arrastrá archivos o hacé click para subir
      </label>
    </div>
  )
}
```

**Deliverables**:
- File upload UI (drag & drop + click)
- Multiple file support
- File size limits
- Preview attachments in messages

---

### 6.3: Dark/Light Mode Toggle (2-3 hours)

**File**: `src/ui/src/hooks/useTheme.ts` (NEW)

```typescript
type Theme = 'light' | 'dark' | 'system'

export const useTheme = () => {
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem('theme') as Theme) || 'system'
  })

  useEffect(() => {
    const root = document.documentElement

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      root.classList.toggle('dark', systemTheme === 'dark')
    } else {
      root.classList.toggle('dark', theme === 'dark')
    }

    localStorage.setItem('theme', theme)
  }, [theme])

  return { theme, setTheme }
}
```

**File**: `src/ui/src/components/chat/ThemeToggle.tsx` (NEW)

```typescript
export const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useTheme()

  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      {theme === 'light' ? <FiMoon /> : <FiSun />}
    </button>
  )
}
```

**Deliverables**:
- Theme toggle button
- System preference detection
- Persisted preference
- Smooth transitions

---

### 6.4: Search in Conversation (3-4 hours)

**File**: `src/ui/src/components/chat/SearchBar.tsx` (NEW)

```typescript
export const SearchBar: React.FC<{ messages: ChatMessage[] }> = ({ messages }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<number[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)

  const handleSearch = (q: string) => {
    setQuery(q)

    const matches = messages
      .map((msg, idx) => ({ msg, idx }))
      .filter(({ msg }) =>
        msg.content.toLowerCase().includes(q.toLowerCase())
      )
      .map(({ idx }) => idx)

    setResults(matches)
    setCurrentIndex(0)
  }

  const scrollToResult = (index: number) => {
    const messageElement = document.querySelector(`[data-message-index="${results[index]}"]`)
    messageElement?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <div className="search-bar">
      <input
        type="search"
        value={query}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Buscar en conversación..."
      />

      {results.length > 0 && (
        <div className="search-nav">
          <span>{currentIndex + 1} / {results.length}</span>
          <button onClick={() => {
            const prev = (currentIndex - 1 + results.length) % results.length
            setCurrentIndex(prev)
            scrollToResult(prev)
          }}>
            <FiChevronUp />
          </button>
          <button onClick={() => {
            const next = (currentIndex + 1) % results.length
            setCurrentIndex(next)
            scrollToResult(next)
          }}>
            <FiChevronDown />
          </button>
        </div>
      )}
    </div>
  )
}
```

**Deliverables**:
- Search bar UI
- Highlight matches
- Navigate results
- Clear search

---

### 6.5: Message Reactions & Feedback (2-3 hours)

**File**: `src/ui/src/components/chat/MessageReactions.tsx` (NEW)

```typescript
type Reaction = '👍' | '👎' | '❤️' | '🎯'

interface MessageReactionsProps {
  messageId: string
  reactions: Record<Reaction, number>
  onReact: (reaction: Reaction) => void
}

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions,
  onReact
}) => {
  return (
    <div className="flex gap-1 mt-2">
      {(['👍', '👎', '❤️', '🎯'] as Reaction[]).map(emoji => (
        <button
          key={emoji}
          onClick={() => onReact(emoji)}
          className="px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
        >
          {emoji} {reactions[emoji] || 0}
        </button>
      ))}
    </div>
  )
}
```

**Backend**: Store reactions in PostgreSQL

```sql
CREATE TABLE message_reactions (
  id SERIAL PRIMARY KEY,
  conversation_id VARCHAR(255),
  message_id VARCHAR(255),
  reaction VARCHAR(10),
  user_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Deliverables**:
- Reaction buttons (👍👎❤️🎯)
- Reaction counts
- User feedback collection

---

### ✅ Phase 6 Complete Checklist

- [ ] Streaming responses (token-by-token)
- [ ] File upload & attachments
- [ ] Dark/Light mode toggle
- [ ] Search in conversation
- [ ] Message reactions & feedback

---

## 🎯 PHASE 7: Production Polish

**Priority**: 🟢 LOW
**Estimated Time**: 12-16 hours (3-4 días)

---

### 7.1: Error Boundaries & Fallbacks (3-4 hours)

**File**: `src/ui/src/components/ErrorBoundary.tsx` (NEW)

```typescript
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error Boundary:', error, errorInfo)
    // Log to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Algo salió mal</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Recargar página
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
```

**Deliverables**:
- Error boundaries for all major components
- User-friendly error messages
- Automatic error reporting

---

### 7.2: Loading States & Skeletons (2-3 hours)

**File**: `src/ui/src/components/Skeleton.tsx` (NEW)

```typescript
export const MessageSkeleton: React.FC = () => {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2" />
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
    </div>
  )
}

export const ConversationListSkeleton: React.FC = () => {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="animate-pulse">
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      ))}
    </div>
  )
}
```

**Deliverables**:
- Loading skeletons for all async content
- Smooth transitions
- Better perceived performance

---

### 7.3: Accessibility (WCAG 2.1) (3-4 hours)

**Improvements**:

```typescript
// Keyboard navigation
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick()
    }
  }}
  aria-label="Send message"
  role="button"
  tabIndex={0}
>
  Send
</button>

// Screen reader announcements
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {isLoading ? 'Processing message...' : 'Message sent'}
</div>

// Focus management
useEffect(() => {
  if (modalOpen) {
    modalRef.current?.focus()
  }
}, [modalOpen])

// Color contrast
// Ensure all text has minimum 4.5:1 contrast ratio
```

**Deliverables**:
- ARIA labels and roles
- Keyboard navigation
- Focus management
- Screen reader support
- Color contrast compliance

---

### 7.4: Performance Optimization (2-3 hours)

**Optimizations**:

```typescript
// Virtual scrolling for long message lists
import { FixedSizeList } from 'react-window'

const VirtualMessageList = ({ messages }) => {
  return (
    <FixedSizeList
      height={600}
      itemCount={messages.length}
      itemSize={100}
    >
      {({ index, style }) => (
        <div style={style}>
          <Message message={messages[index]} />
        </div>
      )}
    </FixedSizeList>
  )
}

// Memoization
const MemoizedMessage = React.memo(Message, (prev, next) => {
  return prev.message.id === next.message.id
})

// Code splitting
const FileBrowser = React.lazy(() => import('./FileBrowser'))

<Suspense fallback={<Skeleton />}>
  <FileBrowser />
</Suspense>

// Debounced search
import { useDebouncedValue } from '@/hooks/useDebounce'

const [query, setQuery] = useState('')
const debouncedQuery = useDebouncedValue(query, 300)

useEffect(() => {
  // Search with debounced query
}, [debouncedQuery])
```

**Deliverables**:
- Virtual scrolling for messages
- Component memoization
- Code splitting
- Debounced inputs

---

### 7.5: Mobile Responsiveness (2-3 hours)

**Improvements**:

```typescript
// Responsive layout
<div className="
  flex flex-col h-screen
  md:flex-row
">
  {/* Sidebar - hidden on mobile, slide-in menu */}
  <div className="
    hidden md:block md:w-64
    absolute md:relative
    inset-y-0 left-0
    transform -translate-x-full md:translate-x-0
    transition-transform
  ">
    <ConversationSidebar />
  </div>

  {/* Main chat */}
  <div className="flex-1">
    <ChatWindow />
  </div>
</div>

// Mobile-friendly input
<textarea
  className="
    w-full p-3
    text-base md:text-sm
    min-h-[60px] md:min-h-[40px]
  "
  placeholder={isMobile ? "Mensaje..." : "Escribí un mensaje..."}
/>

// Touch-friendly buttons
<button className="
  px-4 py-3 md:px-3 md:py-2
  text-base md:text-sm
  min-h-[44px] md:min-h-auto
">
  Send
</button>
```

**Deliverables**:
- Mobile-first design
- Touch-friendly UI elements
- Responsive typography
- Mobile menu/drawer

---

### ✅ Phase 7 Complete Checklist

- [ ] Error boundaries implemented
- [ ] Loading skeletons for all async content
- [ ] WCAG 2.1 accessibility compliance
- [ ] Performance optimizations (virtual scroll, memoization, code splitting)
- [ ] Mobile responsive design

---

## 📊 Estimation Summary

| Phase | Focus | Estimated Time | Priority |
|-------|-------|----------------|----------|
| **Phase 4** | Task Execution (CRITICAL) | 12-16 hours (3-4 days) | 🔴 HIGHEST |
| **Phase 5** | Chat UI Enhancements | 20-24 hours (5-6 days) | 🟡 HIGH |
| **Phase 6** | Advanced Features | 16-20 hours (4-5 days) | 🟢 MEDIUM |
| **Phase 7** | Production Polish | 12-16 hours (3-4 days) | 🟢 LOW |
| **TOTAL** | **Complete System** | **60-76 hours (15-19 days)** | - |

---

## 🎯 Recommended Execution Order

### Week 1: Critical Path
- **Day 1-4**: Phase 4 - Task Execution (BLOCKER)
  - Without this, system doesn't work end-to-end
  - Highest ROI

### Week 2-3: High-Value Features
- **Day 5-10**: Phase 5 - Chat UI Enhancements
  - Markdown + Copy buttons (Day 5)
  - Timestamps + Typing indicator (Day 6)
  - Message actions (Day 7)
  - Command autocomplete (Day 8)
  - Keyboard shortcuts (Day 9)
  - Export + Conversation history (Day 10)

### Week 3-4: Nice-to-Haves
- **Day 11-15**: Phase 6 - Advanced Features
  - Streaming responses (Day 11-12)
  - File upload (Day 13)
  - Theme toggle (Day 14)
  - Search + Reactions (Day 15)

### Week 4: Polish
- **Day 16-19**: Phase 7 - Production Polish
  - Error boundaries (Day 16)
  - Loading states (Day 17)
  - Accessibility (Day 18)
  - Performance + Mobile (Day 19)

---

## 📝 Notes & Considerations

### Technical Debt
- **Testing**: Frontend tests pendientes (Vitest + React Testing Library)
- **Type Safety**: Mejorar types en algunos hooks
- **Performance**: Profiling con React DevTools
- **Bundle Size**: Code splitting más agresivo

### Future Enhancements (Post-MVP)
- Multi-user authentication & workspaces
- Voice input (Web Speech API)
- Code diff viewer
- Collaborative editing
- Agent customization UI
- Workflow builder (visual)
- Analytics dashboard

### Dependencies to Add

**Phase 5**:
```json
{
  "react-syntax-highlighter": "^15.5.0",
  "remark-gfm": "^4.0.0",
  "rehype-highlight": "^7.0.0",
  "rehype-raw": "^7.0.0"
}
```

**Phase 6**:
```json
{
  "react-dropzone": "^14.2.3"
}
```

**Phase 7**:
```json
{
  "react-window": "^1.8.10",
  "@testing-library/react": "^14.1.2",
  "vitest": "^1.0.4"
}
```

---

**Last Updated**: 2025-10-16
**Next Review**: After Phase 4 completion
**Document Owner**: Dany
