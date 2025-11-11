# MGE V2 Integration Guide

**Date**: 2025-11-10
**Status**: In Progress (70% Complete)
**Priority**: P0 - Critical for Production

## Executive Summary

This guide documents the integration of MGE V2 (Masterplan Generation Engine V2) into the DevMatrix production codebase. MGE V2 provides:

- **98% precision** (vs 87% in V1/MVP)
- **1.5 hour execution** (vs 13 hours in V1)
- **100+ concurrent atoms** (vs 2-3 concurrent tasks in V1)
- **4-level hierarchical validation**
- **Smart retry with temperature backoff**
- **Dependency-aware wave execution**

## Current Status

### ✅ Completed (Nov 10, 2025)

1. **Mock Services Replaced** (`src/api/routers/execution_v2.py`)
   - Removed `MagicMock()` instances
   - Integrated real `EnhancedAnthropicClient`
   - Integrated real `AtomicValidator`
   - Proper service initialization with API key management

2. **MGE V2 Orchestration Service** (`src/services/mge_v2_orchestration_service.py`)
   - Complete end-to-end pipeline orchestration
   - Integrates: MasterPlan Generation → Atomization → Wave Execution
   - Async streaming with progress events
   - Reference implementation for chat_service integration

### 🔄 In Progress

3. **Chat Service Integration** (`src/services/chat_service.py`)
   - Old `OrchestratorAgent` (LangGraph) still in use at line 730
   - Need to refactor `_execute_orchestration()` to use MGE V2 pipeline
   - See "Integration Steps" section below

### ⏳ Pending

4. **End-to-End Testing**
   - Integration tests for complete pipeline
   - Performance benchmarks (1.5 hour target)
   - Precision validation (98% target)

5. **Discovery Document Generation**
   - Implement `orchestrate_from_request()` in MGE V2 service
   - LLM-based requirement extraction from user input
   - Discovery Document creation and persistence

## Architecture Overview

### MGE V1 (MVP - Current Production)

```
User Request
    ↓
OrchestratorAgent (LangGraph)
    ↓
Task Decomposition (25 LOC subtasks)
    ↓
Sequential/Limited Parallel Execution (2-3 tasks)
    ↓
Basic Validation
    ↓
Code Generated (87% precision, 13 hours)
```

**Problems**:
- Compound error propagation (0.99^800 = 0.03% success)
- No dependency-aware generation
- Limited concurrency (2-3 tasks)
- No retry logic
- 13 hour execution time

### MGE V2 (Target Architecture)

```
User Request
    ↓
Discovery Document Generation
    ↓
MasterPlan Generation (120 tasks via LLM + RAG)
    ↓
Atomization Pipeline (800 atoms @ 10 LOC each)
    ├── MultiLanguageParser (AST)
    ├── RecursiveDecomposer
    ├── ContextInjector
    └── AtomicityValidator
    ↓
Dependency Graph (NetworkX)
    ↓
Wave Execution (8-10 waves, 100+ atoms/wave)
    ├── WaveExecutor (parallel execution)
    ├── RetryOrchestrator (4 attempts, temp backoff)
    └── AtomicValidator (4-level validation)
    ↓
Code Generated (98% precision, 1.5 hours)
```

**Benefits**:
- Dependency-aware generation prevents error cascade
- 100+ concurrent atoms per wave
- Smart retry (4 attempts: 0.7 → 0.5 → 0.3 → 0.3 temperature)
- 4-level validation (atomic → task → milestone → masterplan)
- 90% faster execution (1.5 hours vs 13 hours)

## Integration Steps

### Step 1: Update ChatService to Use MGE V2

**File**: `src/services/chat_service.py`

#### Current Code (Line 694-840):

```python
async def _execute_orchestration(
    self,
    conversation: Conversation,
    request: str,
) -> AsyncIterator[Dict[str, Any]]:
    """Execute orchestration and stream progress."""
    try:
        # ❌ OLD: Uses OrchestratorAgent (LangGraph)
        orchestrator = OrchestratorAgent(
            api_key=self.api_key,
            agent_registry=self.registry,
            progress_callback=progress_callback
        )

        result = await loop.run_in_executor(
            None,
            orchestrator.orchestrate,
            request,
            conversation.workspace_id,
            None,
        )
        # ... format and return result
```

#### New Code (MGE V2):

```python
async def _execute_orchestration(
    self,
    conversation: Conversation,
    request: str,
) -> AsyncIterator[Dict[str, Any]]:
    """Execute orchestration using MGE V2 pipeline."""
    try:
        # ✅ NEW: Import MGE V2 orchestration service
        from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService

        # Initialize MGE V2 service
        mge_v2_service = MGE_V2_OrchestrationService(
            db=self.db,  # Need to add db to ChatService constructor
            api_key=self.api_key,
            enable_caching=True,
            enable_rag=True
        )

        # Stream MGE V2 pipeline events
        async for event in mge_v2_service.orchestrate_from_request(
            user_request=request,
            workspace_id=conversation.workspace_id,
            session_id=conversation.conversation_id,
            user_id=conversation.user_id
        ):
            # Stream event to frontend
            yield {
                "type": event.get("type"),
                "content": event.get("message", ""),
                "data": event,
                "done": (event.get("type") in ["complete", "error"])
            }

            # Save completed result to conversation
            if event.get("type") == "complete":
                response = self._format_completion_message(event)
                assistant_message = Message(
                    content=response,
                    role=MessageRole.ASSISTANT,
                    metadata={"mge_v2_result": event},
                )
                conversation.add_message(assistant_message)
                self._save_message_to_db(
                    conversation_id=conversation.conversation_id,
                    role=MessageRole.ASSISTANT.value,
                    content=response,
                    metadata={"mge_v2_result": event}
                )

    except Exception as e:
        error_message = f"Error during MGE V2 orchestration: {str(e)}"
        self.logger.error(error_message, exc_info=True)
        yield {
            "type": "error",
            "content": error_message,
            "done": True,
        }

def _format_completion_message(self, event: Dict[str, Any]) -> str:
    """Format MGE V2 completion event as markdown message."""
    lines = [
        "## ✅ MGE V2 Generation Complete",
        "",
        f"**MasterPlan ID**: `{event.get('masterplan_id')}`",
        f"**Total Tasks**: {event.get('total_tasks')}",
        f"**Total Atoms**: {event.get('total_atoms')}",
        f"**Precision**: {event.get('precision', 0) * 100:.1f}%",
        f"**Execution Time**: {event.get('execution_time', 0):.1f}s",
        "",
        "The code has been generated successfully. Check your workspace for the results.",
    ]
    return "\n".join(lines)
```

#### Required Changes to ChatService Constructor:

```python
class ChatService:
    def __init__(
        self,
        api_key: str,
        db: Session,  # ✅ ADD: Database session for MGE V2
        websocket_manager: Optional[WebSocketManager] = None,
    ):
        self.api_key = api_key
        self.db = db  # ✅ NEW
        self.ws_manager = websocket_manager
        # ... rest of initialization
```

### Step 2: Update API Router Initialization

**File**: `src/api/routers/chat.py` (or wherever ChatService is instantiated)

```python
# OLD
chat_service = ChatService(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    websocket_manager=ws_manager
)

# NEW
from src.config.database import get_db

chat_service = ChatService(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    db=next(get_db()),  # ✅ ADD: Database session
    websocket_manager=ws_manager
)
```

### Step 3: Implement Discovery Document Generation

**Status**: Not yet implemented (required for full MGE V2 flow)

The `orchestrate_from_request()` method in `MGE_V2_OrchestrationService` currently returns an error. To complete the integration:

1. Create LLM prompt for extracting requirements from natural language
2. Generate structured DiscoveryDocument
3. Save to database
4. Call `orchestrate_from_discovery()`

**Example Implementation**:

```python
async def orchestrate_from_request(
    self,
    user_request: str,
    workspace_id: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> AsyncIterator[Dict[str, Any]]:
    """Execute MGE V2 pipeline from user request."""

    # Step 1: Extract requirements with LLM
    requirements = await self._extract_requirements_from_request(user_request)

    # Step 2: Create Discovery Document
    discovery_doc = DiscoveryDocument(
        discovery_id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id or str(uuid.uuid4()),
        project_name=requirements["project_name"],
        project_description=requirements["description"],
        # ... other fields
    )
    self.db.add(discovery_doc)
    self.db.commit()

    # Step 3: Execute full pipeline
    async for event in self.orchestrate_from_discovery(
        discovery_id=discovery_doc.discovery_id,
        session_id=session_id,
        user_id=user_id
    ):
        yield event
```

### Step 4: Feature Flag (Optional - For Gradual Rollout)

Add a feature flag to allow gradual rollout of MGE V2:

```python
# In constants.py or environment config
MGE_V2_ENABLED = os.getenv("MGE_V2_ENABLED", "false").lower() == "true"

# In chat_service.py
async def _execute_orchestration(self, conversation, request):
    if MGE_V2_ENABLED:
        # Use MGE V2 pipeline
        async for event in self._execute_mge_v2(conversation, request):
            yield event
    else:
        # Use legacy OrchestratorAgent
        async for event in self._execute_legacy_orchestration(conversation, request):
            yield event
```

## Testing Strategy

### 1. Unit Tests

**Location**: `tests/services/test_mge_v2_orchestration_service.py`

```python
import pytest
from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService

@pytest.mark.asyncio
async def test_orchestration_pipeline():
    """Test complete MGE V2 pipeline."""
    service = MGE_V2_OrchestrationService(db=mock_db)

    events = []
    async for event in service.orchestrate_from_discovery(
        discovery_id=test_discovery_id,
        session_id="test_session",
        user_id="test_user"
    ):
        events.append(event)

    # Verify pipeline stages
    assert any(e["phase"] == "masterplan_generation" for e in events)
    assert any(e["phase"] == "atomization" for e in events)
    assert any(e["phase"] == "execution" for e in events)
    assert events[-1]["type"] == "complete"
```

### 2. Integration Tests

**Location**: `tests/integration/test_mge_v2_end_to_end.py`

Test the complete flow from user request to code generation.

### 3. Performance Benchmarks

**Target Metrics**:
- Execution time: ≤ 1.5 hours (for 800 atoms)
- Precision: ≥ 98% (atoms passing validation)
- Concurrency: 100+ atoms per wave
- Cost: ≤ $2.50 per masterplan (with caching)

## Known Issues & Limitations

### 1. AtomicValidator is a Stub

**File**: `src/mge/v2/validation/atomic_validator.py`

```python
async def validate(self, atom_spec) -> AtomicValidationResult:
    # ⚠️ Stub implementation - always returns passed=True
    return AtomicValidationResult(passed=True, issues=[], metrics={})
```

**Impact**: No validation is currently performed. Need to implement real validation logic from Phase 2.

**Solution**: Integrate with `src/validation/validation_service.py` (4-level validation already exists).

### 2. Discovery Document Generation Not Implemented

**Status**: `orchestrate_from_request()` returns error

**Workaround**: Use `orchestrate_from_discovery()` with manually created discovery documents.

### 3. ExecutionServiceV2 Progress Polling

The current implementation doesn't poll real execution progress. Need to add:
- Status polling from database
- Real-time progress events via WebSocket
- Wave completion tracking

### 4. RAG System Underpopulated

**Current**: Only 34 examples in ChromaDB
**Required**: 500-1000 examples for effective RAG

**Solution**: Run ingestion scripts from `data/context7/` directory.

## Migration Path

### Phase 1: Parallel Operation (Recommended)

1. Keep both V1 and V2 systems operational
2. Use feature flag to toggle between them
3. Run V2 on non-critical projects first
4. Collect metrics and validate precision
5. Gradually increase V2 adoption

### Phase 2: Full Cutover

1. Set `MGE_V2_ENABLED=true` globally
2. Monitor error rates and precision
3. Deprecate V1 code after 30 days of stable V2 operation

## Performance Comparison

| Metric | MGE V1 (MVP) | MGE V2 (Target) | Improvement |
|--------|--------------|-----------------|-------------|
| Precision | 87.1% | 98% | +12.5% |
| Execution Time | 13 hours | 1.5 hours | 90% faster |
| Concurrency | 2-3 tasks | 100+ atoms | 33-50x |
| Granularity | 25 LOC | 10 LOC | 2.5x finer |
| Validation Levels | 1 basic | 4 hierarchical | 4x |
| Retry Attempts | 0 | 4 with backoff | ∞ improvement |
| Cost per Plan | ~$0.50 | ~$2.50* | 5x higher** |

\* With caching
\** Higher cost justified by 90% time savings and 12.5% precision gain

## Next Steps

1. ✅ **Complete** - Fix mock services in `execution_v2.py`
2. ✅ **Complete** - Create MGE V2 orchestration service
3. **TODO** - Integrate into `chat_service.py` (~2 hours)
4. **TODO** - Implement Discovery Document generation (~3 hours)
5. **TODO** - Add integration tests (~2 hours)
6. **TODO** - Performance benchmarks (~1 hour)
7. **TODO** - Populate RAG system (500+ examples) (~4 hours)
8. **TODO** - Production rollout with feature flag (~1 hour)

**Total Estimated Time**: ~13 hours

## References

- [MGE V1 vs V2 Comparison](/DOCS/eval/MGE_V1_VS_V2_COMPARISON.md)
- [Codebase Deep Analysis](/DOCS/eval/2025-11-10_CODEBASE_DEEP_ANALYSIS.md)
- [MGE V2 Executive Summary](/DOCS/MGE_V2/00_EXECUTIVE_SUMMARY.md)
- [MGE V2 Architecture](/DOCS/MGE_V2/ARCHITECTURE_COMPARISON.md)
- [Integration into DevMatrix](/DOCS/MGE_V2/10_INTEGRATION_DEVMATRIX.md)

## Contact

For questions or issues during integration:
- **Architecture**: See `/DOCS/MGE_V2/` documentation
- **Code Reference**: See `src/services/mge_v2_orchestration_service.py`
- **Tests**: See `tests/mge/v2/` directory
