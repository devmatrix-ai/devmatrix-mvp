# Performance Benchmark Report

**Date**: 2025-11-15 14:37:30

**Duration**: 4.25s

## Results by Component


### CPIE

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Average inference time | 0.036s | 5.0s | ✅ PASS |
| Max inference time | 0.311s | 5.0s | ✅ PASS |
| Min inference time | 0.004s | 5.0s | ✅ PASS |

### PatternBank

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Average search time | 0.001ms | 100.0ms | ✅ PASS |
| Max search time | 0.021ms | 100.0ms | ✅ PASS |
| P95 search time | 0.001ms | 100.0ms | ✅ PASS |

### Neo4j

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| DAG build time | 0.872s | 10.0s | ✅ PASS |
| Cycle detection time | 0.068s | 1.0s | ✅ PASS |
| Topological sort time | 0.13s | 1.0s | ✅ PASS |

### Memory

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Memory used | 406.75MB | 2048.0MB | ✅ PASS |
| Peak memory | 0.453MB | 2048.0MB | ✅ PASS |

### Cache

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Cache hit rate | 80.0% | 50.0% | ✅ PASS |

## Summary

- **Total Tests**: 12
- **Passed**: 12
- **Failed**: 0
- **Pass Rate**: 100.0%