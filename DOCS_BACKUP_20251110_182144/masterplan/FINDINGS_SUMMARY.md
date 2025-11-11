# MasterPlan Generation - Root Cause Analysis Summary

**Status**: 🔴 **CRITICAL** - Discovery and MasterPlan documents are not persisting to database

**Analysis Date**: November 4, 2025

---

## Executive Summary

After comprehensive code analysis of the MasterPlan generation flow (`chat /masterplan command → database persistence`), **the code structure appears correct**, but **something is breaking in production**. The persistence code exists but masterplans and discovery documents are not being saved.

### Key Findings:

| Aspect | Status | Details |
|--------|--------|---------|
| **Persistence Code** | ✅ Present | `db.add()`, `db.commit()` calls exist in both discovery and masterplan save methods |
| **Database Schema** | ✅ Defined | All required tables and models properly defined in SQLAlchemy |
| **Error Handling** | ✅ Implemented | Exceptions are caught and logged with full stack traces |
| **Flow Implementation** | ✅ Complete | All steps from chat command to database save are implemented |
| **⚠️ Actual Persistence** | ❌ **BROKEN** | Discovery documents and masterplans NOT found in database after generation |

---

## Three Most Likely Root Causes

### 🔴 CAUSE 1: DATABASE NOT INITIALIZED / ENVIRONMENT NOT SET
**Likelihood**: 60%

**What's Happening**:
- PostgreSQL database not running or not accessible
- `DATABASE_URL` environment variable not set correctly
- Tables exist but are empty (no auto-commit happening)

**Evidence**:
- No verification code in chat_service.py that confirms persistence actually happened
- No diagnostic logs showing database operations

**Test Command**:
```bash
# Check if DATABASE_URL is set
echo $DATABASE_URL

# Test database connectivity
docker exec devmatrix-postgres psql -U devmatrix -d devmatrix -c "\dt discovery_documents"

# Check if tables are empty
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -c "SELECT COUNT(*) FROM discovery_documents;"
```

---

### 🔴 CAUSE 2: USER NOT AUTHENTICATED (user_id IS NULL)
**Likelihood**: 30%

**What's Happening**:
- WebSocket connection not properly authenticated
- `conversation.user_id` is None when `/masterplan` command is called
- Line 861 in chat_service.py raises ValueError but it's caught and sent to user without stopping flow

**Evidence**:
- Line 860-861 in chat_service.py checks if user_id is set, but error might be swallowed
- No verification that user_id is actually passed to database save

**Test Code** (add to chat_service.py line 857):
```python
logger.info(f"🔍 DEBUG: user_id = {user_id}, type = {type(user_id)}")
if not user_id or user_id.strip() == "":
    logger.error(f"❌ CRITICAL: user_id is empty or None!")
```

---

### 🔴 CAUSE 3: LLM GENERATION FAILING (INVALID JSON)
**Likelihood**: 10%

**What's Happening**:
- Claude API not responding or returning invalid JSON
- JSON parsing fails silently
- Discovery/MasterPlan data is incomplete

**Evidence**:
- No explicit verification that LLM response is valid before saving
- Token limits might be exceeded (120 tasks might exceed output tokens)

**Test Code** (add to masterplan_generator.py line 636):
```python
logger.info(f"🔍 LLM Response Stats:")
logger.info(f"  - Content length: {len(response['content'])} chars")
logger.info(f"  - Output tokens: {response['usage']['output_tokens']}")
logger.info(f"  - Cache hit: {response['usage'].get('cache_read_input_tokens', 0)}")
```

---

## Critical Code Paths to Test

### Path 1: Discovery Persistence
```
chat_service.py:877 conduct_discovery()
  ├─ discovery_agent.py:202 _generate_discovery()
  ├─ discovery_agent.py:205 _parse_discovery()
  ├─ discovery_agent.py:237 _save_discovery() [DB WRITE]
  │  ├─ database.py:144 get_db_context()
  │  ├─ discovery_agent.py:496 db.add(discovery)
  │  └─ discovery_agent.py:497 db.commit()
  └─ discovery_agent.py:508 get_discovery() [DB READ]
```

### Path 2: MasterPlan Persistence
```
chat_service.py:914 generate_masterplan()
  ├─ masterplan_generator.py:308 _load_discovery()
  ├─ masterplan_generator.py:329 _generate_masterplan_llm()
  ├─ masterplan_generator.py:336 _parse_masterplan()
  ├─ masterplan_generator.py:369 _save_masterplan() [DB WRITE]
  │  ├─ database.py:144 get_db_context()
  │  ├─ masterplan_generator.py:780 db.add(masterplan)
  │  ├─ masterplan_generator.py:787-788 db.add(phases)
  │  └─ masterplan_generator.py:804 db.commit()
  └─ masterplan_generator.py:1003 get_masterplan() [DB READ]
```

---

## Code Issues That NEED Fixing

### Issue 1: No Persistence Verification
**File**: `src/services/chat_service.py:920`
**Problem**: After retrieving masterplan with `get_masterplan()`, no check is done to verify it actually exists in database

**Fix**: Add verification
```python
masterplan = masterplan_generator.get_masterplan(masterplan_id)
if not masterplan:
    raise RuntimeError(f"❌ MasterPlan generation succeeded but database lookup failed: {masterplan_id}")
logger.info(f"✅ MasterPlan persisted and retrieved: {masterplan.project_name}")
```

### Issue 2: Double db.commit()
**File**: `src/services/discovery_agent.py:497`
**Problem**: Explicit `db.commit()` + automatic `db.commit()` from context manager at exit
**Fix**: Remove line 497, let context manager handle commit

### Issue 3: Atomic MasterPlan Tasks NOT Implemented
**File**: `src/services/masterplan_generator.py`
**Problem**: Generates 120 tasks in one LLM call - tasks are likely NOT atomic (not 200-800 tokens each)
**Fix**: Generate tasks incrementally (50 at a time) to ensure true atomicity

### Issue 4: Debug Logging Left in Production
**File**: `src/services/discovery_agent.py:188, 198`
**Problem**: Debug log statements with emojis
**Fix**: Convert to debug-level logs (DEBUG not INFO)

---

## Environment Checklist

### Prerequisites to Check:
- [ ] PostgreSQL running and accessible
- [ ] DATABASE_URL environment variable set to valid PostgreSQL connection string
- [ ] All tables created (discovery_documents, masterplans, etc.)
- [ ] ANTHROPIC_API_KEY set for Claude Sonnet 4.5
- [ ] OPENAI_API_KEY set for embeddings
- [ ] WebSocket connection properly authenticated with valid user_id

### Database Verification SQL:
```sql
-- Check tables exist
SELECT COUNT(*) as table_count FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('discovery_documents', 'masterplans', 'masterplan_phases', 'masterplan_milestones', 'masterplan_tasks');

-- Check discovery documents
SELECT COUNT(*) as discovery_count FROM discovery_documents;

-- Check masterplans
SELECT COUNT(*) as masterplan_count FROM masterplans;

-- Check recent masterplans with joins
SELECT mp.masterplan_id, mp.project_name, dd.domain, mp.created_at
FROM masterplans mp
LEFT JOIN discovery_documents dd ON mp.discovery_id = dd.discovery_id
ORDER BY mp.created_at DESC
LIMIT 5;
```

---

## Recommended Testing Order

### Test 1: Environment Verification (5 min)
```bash
# Check variables
env | grep -E "DATABASE_URL|ANTHROPIC_API_KEY"

# Test database
docker exec devmatrix-postgres psql -U devmatrix -d devmatrix -c "SELECT version();"

# Test table existence
docker exec -i devmatrix-postgres psql -U devmatrix -d devmatrix -c "\dt discovery_documents"
```

**Expected Result**: All environment variables set, PostgreSQL accessible, tables exist

---

### Test 2: Database Write Test (10 min)
Add temporary test code to chat_service.py:

```python
# After line 881 (before masterplan generation)
logger.info(f"🧪 TEST: Attempting discovery save...")
discovery = discovery_agent.get_discovery(discovery_id)
if discovery:
    logger.info(f"✅ Discovery found in database: {discovery.domain}")
else:
    logger.error(f"❌ Discovery NOT found in database: {discovery_id}")
    logger.error(f"   Expected discovery_id: {discovery_id}")

    # Check if ANY discoveries exist
    with get_db_context() as db:
        all_count = db.query(DiscoveryDocument).count()
        logger.error(f"   Total discoveries in database: {all_count}")
```

**Expected Result**: Discovery persisted and retrievable from database

---

### Test 3: MasterPlan Write Test (10 min)
Add temporary test code to chat_service.py:

```python
# After line 920 (after masterplan_id assigned)
logger.info(f"🧪 TEST: Attempting masterplan save...")
masterplan = masterplan_generator.get_masterplan(masterplan_id)
if masterplan:
    logger.info(f"✅ MasterPlan found in database: {masterplan.project_name}")
    logger.info(f"   Phases: {masterplan.total_phases}")
    logger.info(f"   Tasks: {masterplan.total_tasks}")
else:
    logger.error(f"❌ MasterPlan NOT found in database: {masterplan_id}")
    logger.error(f"   Expected masterplan_id: {masterplan_id}")
```

**Expected Result**: MasterPlan persisted and retrievable from database

---

### Test 4: User Authentication Test (5 min)
Add logging to chat_service.py:

```python
# At line 857 in _execute_masterplan_generation
logger.info(f"🔐 Authentication Check:")
logger.info(f"   - conversation.user_id: {conversation.user_id}")
logger.info(f"   - user_id (passed): {user_id}")
logger.info(f"   - session_id: {session_id}")
logger.info(f"   - User authenticated: {bool(user_id)}")
```

**Expected Result**: user_id is valid UUID or string, not None/empty

---

### Test 5: LLM Generation Test (15 min)
Add logging to masterplan_generator.py:

```python
# After line 647 (in _generate_masterplan_llm)
logger.info(f"🤖 LLM Generation Stats:")
logger.info(f"   - Model: {response['model']}")
logger.info(f"   - Input tokens: {response['usage']['input_tokens']}")
logger.info(f"   - Output tokens: {response['usage']['output_tokens']}")
logger.info(f"   - Cost: ${response['cost_usd']:.4f}")
logger.info(f"   - Response length: {len(response['content'])} chars")
logger.debug(f"   - First 500 chars: {response['content'][:500]}")
```

**Expected Result**: LLM response is valid JSON with all required fields

---

## Quick Diagnostic Script

Create `/tmp/test_masterplan_flow.py`:

```python
#!/usr/bin/env python3
"""Test MasterPlan generation flow"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code" / "agentic-ai"))

from src.config.database import get_db_context
from src.models.masterplan import DiscoveryDocument, MasterPlan

def test_database_connection():
    print("🧪 Testing database connection...")
    try:
        with get_db_context() as db:
            discovery_count = db.query(DiscoveryDocument).count()
            masterplan_count = db.query(MasterPlan).count()
            print(f"✅ Database connected")
            print(f"   - Discoveries: {discovery_count}")
            print(f"   - MasterPlans: {masterplan_count}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_environment():
    print("\n🧪 Testing environment variables...")
    vars_to_check = ["DATABASE_URL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    all_set = True
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET")
            all_set = False
    return all_set

if __name__ == "__main__":
    env_ok = test_environment()
    db_ok = test_database_connection()

    if env_ok and db_ok:
        print("\n✅ All checks passed - environment is ready")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed - fix before testing masterplan")
        sys.exit(1)
```

---

## Decision Tree for Debugging

```
Does `/masterplan` command execute without error?
├─ NO: Check exception logs → Fix error
├─ YES: Continue...

Is user_id set?
├─ NO: Fix authentication → user_id should be set in conversation.user_id
├─ YES: Continue...

Is DATABASE_URL set and valid?
├─ NO: Set DATABASE_URL environment variable
├─ YES: Continue...

Does discovery document exist in database after generation?
├─ NO: 🔴 CAUSE 1 - Database not persisting (transaction issue)
├─ YES: Continue...

Does masterplan exist in database after generation?
├─ NO: 🔴 CAUSE 3 - LLM generation failing or masterplan save failing
├─ YES: Flow is working! 🎉

Check if masterplan is atomic (each task 200-800 tokens)?
├─ NO: Implement atomic generation (Phase 5)
├─ YES: Complete! ✅
```

---

## Recommended Fix Priority

### Phase 1: Identify Root Cause (TODAY)
1. Add persistence verification logging
2. Run diagnostic tests
3. Check database for records
4. Identify exact failure point

### Phase 2: Fix Persistence (AFTER identifying cause)
1. Fix database connection if needed
2. Fix authentication if needed
3. Add transaction error handling
4. Add retry logic for transient failures

### Phase 3: Implement Atomic MasterPlan (WEEK 2)
1. Generate masterplan incrementally (50 tasks at a time)
2. Ensure each task is truly atomic (200-800 tokens)
3. Add progress tracking
4. Save progressively to database

---

## Summary

**The MasterPlan generation system LOOKS correct but DOESN'T WORK in practice.**

**Most likely culprits** (in order):
1. 60% - Database not initialized or DATABASE_URL not set
2. 30% - User not authenticated (user_id is None)
3. 10% - LLM generation failing (invalid JSON)

**Next step**: Run the diagnostic tests above to identify which one is actually broken, then fix accordingly.

---

**Generated**: November 4, 2025
**Status**: Ready for debugging and testing phase

