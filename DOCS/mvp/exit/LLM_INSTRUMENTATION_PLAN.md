# LLM Instrumentation Plan

**Created**: 2025-11-27
**Related Bug**: #66 (LLM Latency = 0.0ms)
**Status**: Planning
**Priority**: LOW (post-MVP optimization)

---

## Problem Statement

El pipeline reporta `LLM Latency = 0.0ms` porque la mayoría de services usan `anthropic.Anthropic()` directamente en lugar de `EnhancedAnthropicClient` que tiene instrumentación.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA ACTUAL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EnhancedAnthropicClient (instrumentado ✅)                     │
│  ├── Trackea latency con time.time()                           │
│  ├── Acumula en _global_total_latency_ms                       │
│  └── Reporta avg_latency_ms correctamente                      │
│                                                                 │
│  VS                                                             │
│                                                                 │
│  anthropic.Anthropic() directo (NO instrumentado ❌)           │
│  ├── semantic_matcher.py                                       │
│  ├── validation_code_generator.py                              │
│  ├── business_logic_extractor.py                               │
│  ├── llm_spec_normalizer.py                                    │
│  └── llm_validation_extractor.py                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Current State

### Instrumented (✅)
| File | Client | Latency Tracked |
|------|--------|-----------------|
| `src/llm/enhanced_anthropic_client.py` | EnhancedAnthropicClient | ✅ Yes |
| `src/mge/v2/agents/code_repair_agent.py` | Uses EnhancedAnthropicClient | ✅ Yes |

### Not Instrumented (❌)
| File | Line | Current Usage | Phase Used |
|------|------|---------------|------------|
| `src/services/semantic_matcher.py` | ~169 | `anthropic.Anthropic()` | Phase 2 |
| `src/services/validation_code_generator.py` | ~45 | `anthropic.Anthropic()` | Phase 6 |
| `src/services/business_logic_extractor.py` | ~52 | `anthropic.Anthropic()` | Phase 1.5 |
| `src/services/llm_spec_normalizer.py` | ~38 | `anthropic.Anthropic()` | Phase 1.5 |
| `src/services/llm_validation_extractor.py` | ~41 | `anthropic.Anthropic()` | Phase 1.5 |

---

## Solution Options

| Option | Effort | Impact | Recommendation |
|--------|--------|--------|----------------|
| **A: Centralized Client** | 8-16h | Full instrumentation | ✅ Best long-term |
| **B: Wrapper per Service** | 4-8h | Per-service timing | ⚠️ Duplication |
| **C: Decorator Pattern** | 2-4h | Non-invasive | ✅ Good balance |
| **D: Hide Metric** | 5min | No instrumentation | ✅ Current (MVP) |

---

## Recommended Approach: Option A (Centralized Client)

### Phase 1: Create LLM Client Factory (2h)

```python
# src/llm/client_factory.py

from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

class LLMClientFactory:
    """Centralized factory for instrumented LLM clients."""

    _instance: Optional[EnhancedAnthropicClient] = None

    @classmethod
    def get_client(cls) -> EnhancedAnthropicClient:
        """Get singleton instrumented client."""
        if cls._instance is None:
            cls._instance = EnhancedAnthropicClient(
                use_opus=False,
                cost_optimization=True
            )
        return cls._instance

    @classmethod
    def get_metrics(cls) -> dict:
        """Get aggregated metrics from all LLM calls."""
        if cls._instance is None:
            return {"total_calls": 0, "avg_latency_ms": 0.0}
        return {
            "total_calls": cls._instance._global_api_calls,
            "total_latency_ms": cls._instance._global_total_latency_ms,
            "avg_latency_ms": cls._instance.avg_latency_ms,
            "total_tokens": cls._instance._global_total_tokens,
        }
```

### Phase 2: Migrate Services (4-8h)

#### 2.1 semantic_matcher.py
```python
# BEFORE
self.client = anthropic.Anthropic()

# AFTER
from src.llm.client_factory import LLMClientFactory
self.client = LLMClientFactory.get_client()
```

#### 2.2 llm_spec_normalizer.py
```python
# BEFORE
self.client = anthropic.Anthropic()

# AFTER
from src.llm.client_factory import LLMClientFactory
self.client = LLMClientFactory.get_client()
```

#### 2.3 business_logic_extractor.py
```python
# BEFORE
self.client = anthropic.Anthropic()

# AFTER
from src.llm.client_factory import LLMClientFactory
self.client = LLMClientFactory.get_client()
```

#### 2.4 validation_code_generator.py
```python
# BEFORE
self.client = anthropic.Anthropic()

# AFTER
from src.llm.client_factory import LLMClientFactory
self.client = LLMClientFactory.get_client()
```

#### 2.5 llm_validation_extractor.py
```python
# BEFORE
self.client = anthropic.Anthropic()

# AFTER
from src.llm.client_factory import LLMClientFactory
self.client = LLMClientFactory.get_client()
```

### Phase 3: Update Metrics Collection (2h)

```python
# tests/e2e/real_e2e_full_pipeline.py

# In final metrics collection:
from src.llm.client_factory import LLMClientFactory

llm_metrics = LLMClientFactory.get_metrics()
final_metrics.llm_avg_latency_ms = llm_metrics["avg_latency_ms"]
final_metrics.llm_total_calls = llm_metrics["total_calls"]
```

### Phase 4: Re-enable Metric Display (5min)

```python
# Uncomment in dashboard:
print(f"  Avg Latency:         {metrics.llm_avg_latency_ms:.1f}ms")
```

---

## Implementation Checklist

| # | Task | File | Status |
|---|------|------|--------|
| 1.1 | Create LLMClientFactory | `src/llm/client_factory.py` | ⏳ TODO |
| 1.2 | Add metrics aggregation methods | `client_factory.py` | ⏳ TODO |
| 2.1 | Migrate semantic_matcher.py | `src/services/` | ⏳ TODO |
| 2.2 | Migrate llm_spec_normalizer.py | `src/services/` | ⏳ TODO |
| 2.3 | Migrate business_logic_extractor.py | `src/services/` | ⏳ TODO |
| 2.4 | Migrate validation_code_generator.py | `src/services/` | ⏳ TODO |
| 2.5 | Migrate llm_validation_extractor.py | `src/services/` | ⏳ TODO |
| 3.1 | Update E2E pipeline metrics collection | `real_e2e_full_pipeline.py` | ⏳ TODO |
| 3.2 | Add latency percentiles (p50/p95/p99) | `client_factory.py` | ⏳ TODO |
| 4.1 | Re-enable latency metric in dashboard | `real_e2e_full_pipeline.py` | ⏳ TODO |
| 4.2 | Verify metrics in E2E run | E2E test | ⏳ TODO |

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_llm_client_factory.py

def test_singleton_pattern():
    """Factory returns same client instance."""
    client1 = LLMClientFactory.get_client()
    client2 = LLMClientFactory.get_client()
    assert client1 is client2

def test_metrics_aggregation():
    """Metrics aggregate across all calls."""
    client = LLMClientFactory.get_client()
    # Make test calls...
    metrics = LLMClientFactory.get_metrics()
    assert metrics["total_calls"] > 0
    assert metrics["avg_latency_ms"] > 0
```

### Integration Tests
```bash
# Run E2E and verify latency > 0
PRODUCTION_MODE=true python tests/e2e/real_e2e_full_pipeline.py 2>&1 | grep "Avg Latency"
# Expected: Avg Latency: 150.3ms (not 0.0ms)
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing services | HIGH | Keep backward compatibility, test each migration |
| Singleton issues in tests | MEDIUM | Add reset method for test isolation |
| Memory leaks | LOW | Use weak references if needed |
| Thread safety | MEDIUM | Add locks for concurrent access |

---

## Estimated Timeline

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Factory | 2h | None |
| Phase 2: Migrations | 4-8h | Phase 1 |
| Phase 3: Metrics | 2h | Phase 2 |
| Phase 4: Enable | 5min | Phase 3 |
| **Total** | **8-12h** | - |

---

## Success Criteria

- [ ] All services use LLMClientFactory
- [ ] `Avg Latency` shows real values (not 0.0ms)
- [ ] Latency percentiles available (p50/p95/p99)
- [ ] No regressions in pipeline functionality
- [ ] All E2E tests pass

---

## Related Documentation

- [IMPROVEMENT_ROADMAP.md](./IMPROVEMENT_ROADMAP.md) - Task 8: Latency Benchmarks
- [CRITICAL_BUGS_2025-11-27.md](./debug/CRITICAL_BUGS_2025-11-27.md) - Bug #66

---

## Changelog

| Date | Change |
|------|--------|
| 2025-11-27 | Initial plan created |
