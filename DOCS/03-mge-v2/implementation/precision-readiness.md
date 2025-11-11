# Precision Readiness Checklist — DevMatrix / MGE v2
**Version:** 1.0 • **Generated:** 2025-10-23

> Objetivo: alcanzar **Precisión ≥ 98%** sostenida (2 semanas consecutivas) en ≥80% de proyectos canario, con coste < $200 y latencia p95 estable.

---

## 🗂️ Proyectos Canario (Gold Set)
- [ ] Definir y congelar set (10–15 proyectos: Python, TS/JS, monorepo, API, UI)
- [ ] Baseline V1 (si existe): tiempo, coste, precisión
- **Owner:** Ariel • **Due:** Week 1 Fri

---

## ✅ Definición de “Precisión” (Contrato)
**Score = 50% Spec Conformance + 30% Integration Pass + 20% Validation Pass (L1–L4)**
- [ ] Métrica compuesta implementada en backend
- [ ] Mapeo requisito → acceptance test(s) (must/should)
- [ ] Publicación de score por proyecto en Prometheus/Grafana
- **Owners:** Dany (backend), Eng1 (QA) • **Due:** Week 1 Fri

---

## 🧪 Acceptance Tests Autogenerados
- [ ] Generación desde masterplan (contratos, invariantes, casos)
- [ ] Ejecución al final de cada wave mayor
- [ ] Gate: 100% **must** y ≥95% **should**
- **Owners:** Eng1, Eng2 • **Due:** Week 2 Wed

---

## 🚀 Ejecución V2 (Closing the loop)
- [ ] WaveExecutor (paralelo por wave, 100+ átomos)
- [ ] RetryOrchestrator (3 intentos, backoff, temp 0.7→0.5→0.3)
- [ ] ExecutionServiceV2 (estado, progreso, endpoints)
- **Owners:** Dany (lead), Eng2 • **Due:** Week 2 Fri

---

## 🔗 Dependencias con "ground truth" - ✅ IMPLEMENTED + TESTED (Gap 5)
- [x] Suite dura: dynamic imports, barrel files, TS path aliases, cycles
- [x] Validación vs tsc/bundler/import maps
- [x] Acierto edges ≥90% (0 FN críticos)
- [x] **25 tests passing, 89% coverage**
- **Owners:** Eng2 (TS/JS), Eng1 (Python) • **Due:** Week 2 Fri • **Status:** ✅ COMPLETED 2025-10-25

---

## 🧩 Atomización con criterios duros - ✅ IMPLEMENTED + TESTED (Gap 6)
- [x] ≤15 LOC • complejidad <3.0 • SRP • context completeness ≥95%
- [x] L1 reports con violaciones + severidad
- [x] **31 API tests passing, 6 REST endpoints validated**
- **Owners:** Eng1 • **Due:** Week 2 Wed • **Status:** ✅ COMPLETED 2025-10-25

---

## ♻️ Cycle-breaking con "semantic guards" - ✅ IMPLEMENTED + TESTED (Gap 7)
- [x] FAS con políticas que no rompan contratos/interfaz pública
- [x] Re-chequeo de integridad tras remover aristas
- [x] **26 tests passing, 90% coverage, handles 1000-atom graphs**
- **Owners:** Dany • **Due:** Week 3 Wed • **Status:** ✅ COMPLETED 2025-10-25

---

## ⚖️ Concurrency Controller Adaptativo - ✅ IMPLEMENTED + TESTED (Gap 8)
- [x] Límites por wave según p95 LLM/DB y presupuesto
- [x] Colas + backpressure; evitar thundering herds
- [x] **22 tests passing, 84% coverage, 65K req/s throughput**
- **Owners:** Eng2 • **Due:** Week 3 Fri • **Status:** ✅ COMPLETED 2025-10-25

---

## 💸 Guardrails de Coste - ✅ IMPLEMENTED + TESTED (Gap 9)
- [x] Soft/Hard caps por masterplan; auto-pause/confirm
- [x] Alertas en Grafana (coste hora, coste total)
- [x] **22 tests passing, 100% coverage, <0.01ms cost checks**
- **Owners:** Dany • **Due:** Week 3 Fri • **Status:** ✅ COMPLETED 2025-10-25

---

## 🧠 Cacheo & Reuso
- [ ] LLM cache (prompt hash), RAG cache, batching
- [ ] Hit-rate combinado ≥60% en canarios
- **Owners:** Eng1 • **Due:** Week 3 Wed

---

## 🔬 Trazabilidad de Causalidad (E2E)
- [ ] Log por átomo: context → L1–L4 → acceptance → retries → coste/tiempo
- [ ] Dashboard con correlaciones (scatter/curvas)
- **Owners:** Dany • **Due:** Week 2 Fri

---

## 🧷 Spec Conformance Gate
- [ ] Gate final: si **must** <100% → **no release**
- [ ] Reporte por requisito con IDs de tests
- **Owners:** Eng1 • **Due:** Week 2 Wed

---

## 👀 Human Review Dirigida
- [ ] ConfidenceScorer (40% validación, 30% retries, 20% complejidad, 10% tests)
- [ ] Cola 15–20% peor score • SLA <24h • tasa corrección >80%
- **Owners:** Ariel (ops), Eng2 (UI) • **Due:** Week 4 Wed

---

## 🐤 Canary Dual-Run (shadow)
- [ ] V2 corre en paralelo en 3 canarios
- [ ] Comparar vs baseline: tiempo/coste/precisión
- **Owners:** Ariel • **Due:** Week 4 Fri

---

## 📈 Reporte Semanal de Precisión
- [ ] Informe automático (cada viernes): score, coste, tiempo, top fallas, acciones
- [ ] Tendencia ≥ +2 pp/semana hasta meta 98%
- **Owners:** Ariel (publish), Dany (data) • **Due:** Recurring

---

### Gates
- **Gate A (promoción):** Score ≥95 por 2 semanas + coste < $200 + p95 estable
- **Gate S (objetivo):** Score ≥**98** por 2 semanas en ≥80% canarios

---

## 📊 Métricas Prometheus esperadas (nombres sugeridos)
- `v2_precision_percent` (Gauge) – por masterplan
- `v2_spec_conformance_percent` (Gauge)
- `v2_integration_pass_percent` (Gauge)
- `v2_validation_pass_percent` (Gauge, L1–L4 etiquetas)
- `v2_execution_time_seconds` (Histogram)
- `v2_cost_per_project_usd` (Summary)
- `v2_cache_hit_rate` (Gauge)
- `v2_retries_total` (Counter)
- `v2_parallel_atoms` (Gauge)
- `llm_request_duration_seconds` (Histogram, etiquetas model/cached)
- `llm_cost_eur_sum` (Counter) • usar conversión a USD si hace falta
- `rag_retrieval_duration_seconds` (Histogram)
- `rag_cache_hits_total`, `rag_cache_misses_total` (Counters)

---

## 👥 Asignación rápida
- **Ariel**: Gold set, canary dual-run, publicación semanal
- **Dany**: Backend métricas, ejecución V2, trazabilidad, costos
- **Eng1 (QA/Backend)**: Acceptance + L1/L2 + cache
- **Eng2 (FE/TS/Infra)**: Dependencias JS/TS, concurrency, UI review

