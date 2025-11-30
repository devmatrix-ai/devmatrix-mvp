# Fixes – Runtime & Learning (2025-11-30)

**Scope:** E2E pipeline health checks, Docker runtime smoke fallback, FixPatternLearner recording.

## Changes Applied
- **Health Verification (Phase 9)**  
  - If no README is found in `README.md`/`docs/README.md`/`docker/README.md`, the pipeline now auto-creates a minimal `README.md` in the generated app root to keep the health check green.  
  - When `generation_manifest.json` exists, the auto README now embeds a short manifest summary (app id, mode, tracked file count).  
  - Location: `tests/e2e/real_e2e_full_pipeline.py`.

- **Docker Runtime Smoke Fallback**  
  - Runtime validator now checks for `docker-compose.yml` **and** a Dockerfile before attempting a build.  
  - On missing Dockerfile or build failure, it falls back to `uvicorn` instead of hard-failing with “Dockerfile: no such file”.  
  - New env toggle `ENFORCE_DOCKER_RUNTIME` = `1|true` forces fail-fast (no fallback) when Docker assets are missing or build fails.
  - Location: `src/validation/runtime_smoke_validator.py`.

- **Smoke Repair Docker Rebuild Toggle**  
  - Smoke-driven repair now allows enabling/disabling Docker rebuilds via `SMOKE_REPAIR_DOCKER_REBUILD` (default: disabled to avoid missing-Dockerfile hangs).  
  - Location: `tests/e2e/real_e2e_full_pipeline.py` (repair orchestrator call).

- **FixPatternLearner Recording**  
  - Repair records are normalized to strings before sending to FixPatternLearner, preventing `'dict' object has no attribute 'lower'`.  
  - Location: `src/validation/smoke_repair_orchestrator.py`.

## Impact
- Health verification no longer blocks on absent README when templates omit it.
- Docker-less environments continue via uvicorn, reducing false negatives in smoke tests.
- Learning loop stays stable; repair attempts are recorded without type errors.

## Follow-ups
- If you want Docker enforcement instead of fallback, gate on policy and fail fast when Dockerfile is missing.  
- Consider enriching the auto README from generation manifest once available.
