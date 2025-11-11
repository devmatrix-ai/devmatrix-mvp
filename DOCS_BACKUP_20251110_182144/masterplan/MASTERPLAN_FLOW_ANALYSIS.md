# MasterPlan Generation Flow Analysis

**Date**: November 4, 2025
**Purpose**: Complete root-cause analysis of why MasterPlan generation doesn't persist discovery documents or masterplans to database
**Status**: Flow appears correctly implemented in code but confirmed broken in practice

---

## Executive Summary

**THE PROBLEM**: MasterPlan generation appears to have all the necessary code for:
- ✅ Discovery document generation and persistence
- ✅ MasterPlan JSON generation from LLM
- ✅ Database schema and models
- ✅ Error handling and logging

**BUT**: In practice, discovery documents and masterplans are NOT being persisted to the database when the `/masterplan` chat command is executed.

**ROOT CAUSE**: Unknown - requires testing/debugging to identify actual failure point

---

## Complete Flow Analysis

### 1. INITIATION: Chat Command `/masterplan`

**File**: `src/services/chat_service.py:842`

```python
async def _execute_masterplan_generation(
    self,
    conversation: Conversation,
    request: str,
) -> AsyncIterator[Dict[str, Any]]:
```

**REQUIREMENTS FOR SUCCESS**:
- ✅ `conversation.user_id` must be set (from authenticated WebSocket)
- ✅ `request` parameter must be non-empty user project description
- ✅ `conversation.metadata` should contain 'sid' (socket.io session ID)

**POTENTIAL ISSUE 1**: User not authenticated properly
- If `conversation.user_id` is None/empty, line 861 will raise ValueError
- This would result in error message to user, but might not be handled properly in WebSocket context

---

### 2. PHASE 1: Discovery Generation & Persistence

#### 2.1 Discovery Generation Call

**File**: `src/services/discovery_agent.py:146`

```python
discovery_id = await discovery_agent.conduct_discovery(
    user_request=request,
    session_id=session_id,  # From conversation.metadata['sid']
    user_id=user_id  # From conversation.user_id
)
```

**Flow**:
1. Create DiscoveryAgent with WebSocket manager
2. Call `conduct_discovery()` with user_request, session_id, user_id
3. Inside conduct_discovery:
   - Generate discovery with LLM (lines 202)
   - Parse discovery JSON (line 205)
   - **SAVE TO DATABASE** (line 237) via `_save_discovery()`
   - Return discovery_id

#### 2.2 Discovery Save Implementation

**File**: `src/services/discovery_agent.py:454`

```python
def _save_discovery(self, user_request, session_id, user_id, discovery_data, llm_model, llm_cost) -> UUID:
    with get_db_context() as db:
        # Create DiscoveryDocument with required fields
        discovery = DiscoveryDocument(
            session_id=session_id,
            user_id=user_id,
            user_request=user_request,
            domain=discovery_data["domain"],
            bounded_contexts=discovery_data["bounded_contexts"],
            aggregates=discovery_data["aggregates"],
            value_objects=discovery_data["value_objects"],
            domain_events=discovery_data["domain_events"],
            services=discovery_data["services"],
            # ... additional fields
        )

        db.add(discovery)
        db.commit()
        db.refresh(discovery)
        return discovery.discovery_id
```

**Database Operation**:
- Uses `get_db_context()` context manager (lines 144-161 in `src/config/database.py`)
- Context manager automatically calls `db.commit()` on exit (line 156)
- Redundant `db.commit()` called again at line 497 (double commit - safe but inefficient)
- Returns discovery_id UUID

**REQUIRED FIELDS VALIDATION**:
- `discovery_data` must have: `domain`, `bounded_contexts`, `aggregates`, `value_objects`, `domain_events`, `services`
- Checked in `_parse_discovery()` at lines 430-443

**POTENTIAL ISSUE 2**: DATABASE CONNECTION FAILURE
- If `get_db_context()` can't connect to PostgreSQL database, db.commit() will fail
- Exception should be caught and logged (line 157-159), but might not be
- **CHECK**: Is `DATABASE_URL` environment variable set correctly in production?

**POTENTIAL ISSUE 3**: LLM Generation Failure
- If LLM generation fails (API key, token limits, etc.), discover_data will be None/invalid
- This would fail at parse step (line 205)
- Exception at line 428 would be raised

---

### 3. PHASE 2: Retrieve Saved Discovery & Verify

**File**: `src/services/chat_service.py:883`

```python
discovery = discovery_agent.get_discovery(discovery_id)
```

**Implementation**: `src/services/discovery_agent.py:508`

```python
def get_discovery(self, discovery_id: UUID) -> Optional[DiscoveryDocument]:
    with get_db_context() as db:
        discovery = db.query(DiscoveryDocument).filter(
            DiscoveryDocument.discovery_id == discovery_id
        ).first()
        return discovery
```

**POTENTIAL ISSUE 4**: DETACHED OBJECT AFTER CONTEXT MANAGER EXIT
- After `get_db_context()` exits (line 523), the SQLAlchemy session closes
- The returned `discovery` object is detached from session
- Accessing `discovery` attributes might fail due to lazy loading
- **Solution**: Load discovery data while session is open, or use `expire_on_commit=False` (ALREADY DONE at line 84 in database.py)

---

### 4. PHASE 3: MasterPlan Generation & Persistence

#### 4.1 MasterPlan Generation Call

**File**: `src/services/chat_service.py:914`

```python
masterplan_id = await masterplan_generator.generate_masterplan(
    discovery_id=discovery_id,
    session_id=session_id,
    user_id=user_id
)
```

#### 4.2 MasterPlan Generation Process

**File**: `src/services/masterplan_generator.py:268`

```python
async def generate_masterplan(
    self, discovery_id: UUID, session_id: str, user_id: str
) -> UUID:
    # 1. Load discovery (line 308)
    discovery = self._load_discovery(discovery_id)
    if not discovery:
        raise ValueError(f"Discovery not found: {discovery_id}")

    # 2. Emit WebSocket progress event (line 316)
    if self.ws_manager:
        await self.ws_manager.emit_masterplan_generation_start(...)

    # 3. Retrieve RAG examples (line 326)
    rag_examples = await self._retrieve_rag_examples(discovery)

    # 4. Generate MasterPlan with LLM (line 329)
    masterplan_json = await self._generate_masterplan_llm_with_progress(...)

    # 5. Parse MasterPlan JSON (line 336)
    masterplan_data = self._parse_masterplan(masterplan_json)

    # 6. Validate MasterPlan (line 355)
    self._validate_masterplan(masterplan_data)

    # 7. **SAVE TO DATABASE** (line 369)
    masterplan_id = self._save_masterplan(
        discovery_id=discovery_id,
        session_id=session_id,
        user_id=user_id,
        masterplan_data=masterplan_data,
        llm_model=masterplan_json.get("model"),
        llm_cost=masterplan_json.get("cost_usd")
    )

    return masterplan_id
```

#### 4.3 MasterPlan Save Implementation

**File**: `src/services/masterplan_generator.py:739`

```python
def _save_masterplan(self, discovery_id, session_id, user_id, masterplan_data, llm_model, llm_cost) -> UUID:
    with get_db_context() as db:
        # Create MasterPlan object
        masterplan = MasterPlan(
            discovery_id=discovery_id,
            session_id=session_id,
            user_id=user_id,
            project_name=masterplan_data["project_name"],
            description=masterplan_data.get("description"),
            status=MasterPlanStatus.DRAFT,
            tech_stack=masterplan_data["tech_stack"],
            architecture_style=masterplan_data.get("architecture_style"),
            total_tasks=masterplan_data["total_tasks"],
            llm_model=llm_model,
            generation_cost_usd=llm_cost,
            estimated_cost_usd=masterplan_data.get("estimated_cost_usd"),
            estimated_duration_minutes=masterplan_data.get("estimated_duration_minutes")
        )

        db.add(masterplan)
        db.flush()  # Get masterplan_id without committing

        # Create Phases, Milestones, Tasks
        task_number_to_uuid = {}

        for phase_data in masterplan_data["phases"]:
            phase = self._create_phase(db, masterplan, phase_data, task_number_to_uuid)
            db.add(phase)

        # Update task dependencies
        self._update_task_dependencies(db, task_number_to_uuid, masterplan_data)

        # Update counts
        masterplan.total_phases = len(masterplan_data["phases"])
        masterplan.total_milestones = sum(...)

        # Calculate estimated cost
        estimated_cost = self._calculate_estimated_cost(masterplan_data)
        masterplan.estimated_cost_usd = estimated_cost

        db.commit()  # Commit all phases, milestones, tasks
        db.refresh(masterplan)

        logger.info("MasterPlan saved to database", masterplan_id=str(masterplan.masterplan_id))

        return masterplan.masterplan_id
```

**Database Operations**:
- Creates MasterPlan object and phases, milestones, tasks
- Uses db.flush() to get masterplan_id before final commit
- Commits all objects at line 804
- Returns masterplan_id

**REQUIRED FIELDS VALIDATION**:
- `masterplan_data` must have: `project_name`, `tech_stack`, `phases`, `total_tasks`
- Validated in `_validate_masterplan()` at line 705

**POTENTIAL ISSUE 5**: MISSING REQUIRED FIELDS IN MASTERPLAN_DATA
- If LLM generates incomplete JSON, parsing/validation might pass but save might fail
- **CHECK**: Does LLM actually generate valid JSON with all required fields?

---

### 5. PHASE 4: Retrieve Saved MasterPlan & Return to User

**File**: `src/services/chat_service.py:920`

```python
masterplan = masterplan_generator.get_masterplan(masterplan_id)
```

**Implementation**: `src/services/masterplan_generator.py:1003`

```python
def get_masterplan(self, masterplan_id: UUID) -> Optional[MasterPlan]:
    with get_db_context() as db:
        masterplan = db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()
        return masterplan
```

---

## Identified Potential Breakpoints

### CRITICAL ISSUES (Must be resolved):

1. **DATABASE CONNECTION FAILURE**
   - **Location**: `get_db_context()` in `src/config/database.py:144`
   - **Symptom**: Discovery/MasterPlan not saved to database
   - **Check**: Is `DATABASE_URL` environment variable set? Can PostgreSQL be reached?
   - **Severity**: 🔴 CRITICAL

2. **USER NOT AUTHENTICATED**
   - **Location**: `_execute_masterplan_generation()` line 861
   - **Symptom**: ValueError raised, no discovery/masterplan generated
   - **Check**: Is WebSocket connection authenticated? Does `conversation.user_id` exist?
   - **Severity**: 🔴 CRITICAL

3. **LLM GENERATION FAILURE**
   - **Location**: `_generate_discovery()` or `_generate_masterplan_llm()`
   - **Symptom**: Discovery/MasterPlan JSON not generated
   - **Check**: Is Claude API key set? Are token limits being hit? Is Sonnet 4.5 available?
   - **Severity**: 🔴 CRITICAL

### MEDIUM ISSUES:

4. **INCOMPLETE DISCOVERY JSON**
   - **Location**: `_parse_discovery()` line 425-452
   - **Symptom**: Discovery parsing fails, validation raises ValueError
   - **Check**: Does LLM output valid JSON? Does it include all required fields?
   - **Severity**: 🟡 MEDIUM

5. **INCOMPLETE MASTERPLAN JSON**
   - **Location**: `_parse_masterplan()` line 657-692
   - **Symptom**: MasterPlan parsing fails
   - **Check**: Does LLM output valid JSON for 120 tasks?
   - **Severity**: 🟡 MEDIUM

6. **ATOMIZATION NOT IMPLEMENTED**
   - **Location**: Tasks are saved but not as "ultra-atomic" units
   - **Symptom**: Generated tasks are too large (not 200-800 tokens each)
   - **Check**: Are tasks actually atomic or are they monolithic?
   - **Severity**: 🟡 MEDIUM

### LOW ISSUES:

7. **WEBSOCKET MANAGER IS NONE**
   - **Location**: Various `if self.ws_manager:` checks
   - **Symptom**: Progress events not emitted (non-blocking)
   - **Check**: Is WebSocket manager properly initialized?
   - **Severity**: 🟢 LOW (non-blocking, but prevents real-time updates)

8. **DETACHED OBJECT LAZY LOADING**
   - **Location**: After `get_db_context()` returns objects
   - **Symptom**: Accessing discovery/masterplan attributes might fail
   - **Check**: Is `expire_on_commit=False` set? (ALREADY DONE)
   - **Severity**: 🟢 LOW

---

## Testing Strategy to Identify Root Cause

### Test 1: DATABASE CONNECTIVITY
```bash
# Check if DATABASE_URL is set
echo $DATABASE_URL

# Try to connect to PostgreSQL
psql $DATABASE_URL -c "SELECT 1"

# Check if tables exist
psql $DATABASE_URL -c "\dt discovery_documents masterplans"
```

### Test 2: USER AUTHENTICATION
```python
# Verify user_id is set when chat command is called
# Add logging in _execute_masterplan_generation:
logger.info(f"Starting masterplan with user_id: {user_id}")
```

### Test 3: DISCOVERY PERSISTENCE
```python
# Add explicit test in chat_service.py after conduct_discovery:
discovery = discovery_agent.get_discovery(discovery_id)
if not discovery:
    logger.error(f"❌ Discovery not found in database: {discovery_id}")
else:
    logger.info(f"✅ Discovery persisted: {discovery.domain}")
```

### Test 4: MASTERPLAN PERSISTENCE
```python
# Add explicit test in chat_service.py after generate_masterplan:
masterplan = masterplan_generator.get_masterplan(masterplan_id)
if not masterplan:
    logger.error(f"❌ MasterPlan not found in database: {masterplan_id}")
else:
    logger.info(f"✅ MasterPlan persisted: {masterplan.project_name}")
```

### Test 5: LLM GENERATION
```python
# Add logging in _generate_discovery and _generate_masterplan_llm:
logger.info(f"LLM Response length: {len(response['content'])} chars")
logger.debug(f"LLM Response content: {response['content'][:500]}")
```

---

## Database Schema Verification

### Required Tables:
1. **discovery_documents** - Must exist and have all columns
   - discovery_id (UUID primary key)
   - session_id, user_id, user_request
   - domain, bounded_contexts, aggregates, value_objects, domain_events, services
   - llm_model, llm_cost_usd, created_at, updated_at

2. **masterplans** - Must exist with all columns
   - masterplan_id (UUID primary key)
   - discovery_id (foreign key to discovery_documents)
   - session_id, user_id, project_name, description
   - tech_stack, architecture_style, total_tasks, total_phases, total_milestones
   - status, llm_model, generation_cost_usd, estimated_cost_usd, estimated_duration_minutes

3. **masterplan_phases, masterplan_milestones, masterplan_tasks** - Dependent tables

### Verification Command:
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('discovery_documents', 'masterplans', 'masterplan_phases');

-- Check column constraints
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'discovery_documents'
ORDER BY ordinal_position;
```

---

## Environment Configuration Verification

### Required Environment Variables:
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@localhost/devmatrix`)
- `OPENAI_API_KEY` - For embeddings and data generation
- `ANTHROPIC_API_KEY` - For LLM generation (Claude Sonnet 4.5)

### Verification:
```bash
# Check if variables are set
env | grep -E "DATABASE_URL|ANTHROPIC_API_KEY|OPENAI_API_KEY"

# Check if PostgreSQL is running
docker ps | grep postgres

# Check if API keys are valid
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## Code Quality Issues Found (Non-blocking):

1. **Double db.commit()** (Line 497 in discovery_agent.py + automatic in get_db_context)
   - `db.commit()` called explicitly at line 497
   - `get_db_context()` context manager also calls `db.commit()` at exit
   - Safe but inefficient - should remove explicit call

2. **Debug Logging Left in Code** (Lines 188, 198 in discovery_agent.py)
   - ```python
     logger.info(f"🔍 [DEBUG] About to check ws_manager: {self.ws_manager is not None}")
     logger.info(f"⚠️  [DEBUG] ws_manager is None! Cannot emit discovery_generation_start")
     ```
   - These suggest someone was debugging websocket manager issues

3. **Monolithic MasterPlan Generation** (Not atomic)
   - Generates 120 tasks in single LLM call
   - Tasks are not "ultra-atomic" (should be 200-800 tokens each)
   - Violates the "atomic masterplan" requirement

---

## Recommendations for Investigation

### Immediate Actions:
1. **Enable DEBUG logging** for database operations
   - Set `echo=True` in SQLAlchemy engine creation (line 51 in database.py)
   - Enable verbose logging for `src.services.discovery_agent` and `src.services.masterplan_generator`

2. **Add persistence verification** in chat_service.py
   - After conduct_discovery(), query and verify discovery exists in DB
   - After generate_masterplan(), query and verify masterplan exists in DB
   - Log results explicitly

3. **Test database connectivity**
   - Verify PostgreSQL is running and accessible
   - Verify all tables are created
   - Run manual inserts to confirm database works

4. **Test LLM generation**
   - Check if Claude API is responding
   - Verify JSON response format
   - Check token limits

### Architecture Improvements:
1. **Implement proper atomic masterplan generation**
   - Generate masterplan incrementally (50 tasks at a time)
   - Ensure each task is truly atomic (200-800 tokens)
   - Save progressively to database

2. **Add transaction logging**
   - Log every db.add(), db.commit(), db.flush() operation
   - Track transaction lifecycle

3. **Implement retry logic**
   - Retry database operations on transient failures
   - Retry LLM generation on API errors

4. **Improve error reporting**
   - Ensure all exceptions are properly logged with full context
   - Add structured logging for better debugging

---

## Next Steps

1. **Run diagnostics** to identify actual failure point
2. **Fix database connectivity** if issue is DATABASE_URL
3. **Fix authentication** if issue is missing user_id
4. **Debug LLM generation** if issue is invalid JSON
5. **Implement atomic masterplan generation** to properly fulfill "ultra-atomic" requirement
6. **Add comprehensive testing** to prevent regression

---

**Status**: 🔴 ROOT CAUSE NOT YET IDENTIFIED - requires testing/debugging

**Files to Review**:
- `/home/kwar/code/agentic-ai/src/services/chat_service.py` (lines 842-977)
- `/home/kwar/code/agentic-ai/src/services/discovery_agent.py` (lines 146-506)
- `/home/kwar/code/agentic-ai/src/services/masterplan_generator.py` (lines 268-815)
- `/home/kwar/code/agentic-ai/src/config/database.py` (lines 144-161)
- `/home/kwar/code/agentic-ai/src/models/masterplan.py` (lines 71-365)

