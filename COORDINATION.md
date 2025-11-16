# Coordination Document - DevMatrix Console Tool vs Pipeline Optimization

**Date**: 2025-11-16
**Status**: Active parallel development
**Claude A (Pipeline)**: Optimizing RAG + Orchestration
**Claude B (Console)**: Building Console Tool

---

## 📋 Work Division

### Claude A - Pipeline Optimization
**Branch**: `feature/cognitive-architecture-mvp`
**Current Task**: Optimize Unified RAG for Qdrant + Neo4j
**Files Modified**:
- `src/rag/unified_retriever.py`
- `src/services/masterplan_generator.py`
- `src/services/mge_v2_orchestration_service.py`
- `tests/precision/e2e/precision_pipeline_mge_v2.py`

**Expected Timeline**: 2-3 days
**Status**: In progress (4 recent commits, local changes pending)

---

### Claude B - Console Tool
**Branch**: `feature/console-tool` (NEW - will be created)
**New Folder**: `src/console/` (ISOLATED)
**Features**:
- Interactive CLI with Rich UI
- Pipeline tree visualization
- Real-time WebSocket streaming
- Session persistence (SQLite)
- Command palette system
- Error recovery UI

**Files to Create** (NO CONFLICTS):
- `src/console/__init__.py`
- `src/console/cli.py`
- `src/console/session_manager.py`
- `src/console/websocket_client.py`
- `src/console/pipeline_visualizer.py`
- `src/console/command_dispatcher.py`
- `src/console/config.py`
- `tests/console/*.py`

**Expected Timeline**: 1-2 weeks (MVP + Phase 2)
**Status**: Starting now

---

## 🛡️ Conflict Prevention Strategy

### What Claude B Will NOT Touch
- ❌ `src/api/` (Pipeline APIs)
- ❌ `src/services/` (Orchestration, RAG)
- ❌ `src/rag/` (RAG implementation)
- ❌ `src/cli/main.py` (Will read only)
- ❌ `src/config/settings.py` (Will read only)

### What Claude B WILL Create
- ✅ New `src/console/` folder (isolated)
- ✅ New `~/.devmatrix/` config (user home, local)
- ✅ New `~/.devmatrix/sessions/` storage (local)
- ✅ New tests in `tests/console/` (isolated)
- ✅ New spec in `agent-os/specs/` (documentation)

### Integration Points (Read-Only)
Claude B will **consume** but **not modify**:
- FastAPI WebSocket endpoints (from Claude A's pipeline)
- Logging infrastructure
- Workspace manager
- Configuration system

---

## 📡 Communication Protocol

### If Issues Arise
1. **Conflict detected**: Add comment to `CONFLICTS.md`
2. **Need to change API**: Discuss in `API_CHANGES.md`
3. **Blocking issue**: Tag in `BLOCKERS.md`

### Git Strategy
- **Claude A**: Commit to `feature/cognitive-architecture-mvp`
- **Claude B**: Commit to `feature/console-tool` (new branch)
- **Merge**: Each to `main` independently (zero conflicts)

### Daily Sync (if working simultaneously)
```bash
# Claude A
git push origin feature/cognitive-architecture-mvp

# Claude B
git push origin feature/console-tool

# No conflicts - different folders, different branches
```

---

## ✅ Safety Checklist

- [x] Claude B isolated to `src/console/` (new folder)
- [x] Claude A controls `src/rag/`, `src/services/`, `src/api/`
- [x] No shared database modifications
- [x] No shared file modifications
- [x] WebSocket: Claude A creates endpoints, Claude B consumes
- [x] Config: Claude B reads global, creates local
- [x] Tests: Separate test folders
- [x] Git: Separate branches

---

## 🎯 Success Criteria

**For Both Claudes**:
- ✅ No git merge conflicts
- ✅ No data corruption in shared DBs
- ✅ API contracts honored
- ✅ Code reviews clean
- ✅ Tests pass independently

**For Claude A (Pipeline)**:
- ✅ RAG optimization complete
- ✅ Performance metrics improved
- ✅ All tests green

**For Claude B (Console)**:
- ✅ MVP console tool working
- ✅ Pipeline integration tested
- ✅ Session persistence functional
- ✅ Phase 2 features queued

---

## 📝 Next Steps

1. **Claude A**: Continue RAG optimization (no changes needed)
2. **Claude B**: Create `feature/console-tool` branch and start coding
3. **Both**: Push to separate branches, merge to main independently

---

**Contact**: If confusion, create issue in repo with `@coordination` tag
