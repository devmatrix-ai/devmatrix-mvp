# Exit Docs Consolidadas (Nov 2025)

## Resumen Ejecutivo
- Compendio único de `DOCS/mvp/exit` sin modificar originales. Incluye estado, propósito y ubicación de cada artefacto.
- Foco en IR unificado, pipeline E2E, enforcement, smoke/repair, learning, LLM/infra, Neo4j y QA.
- Estados clave: la mayoría de fases 2-4 y arquitectura estratificada están completas; enforcement real de 6 validaciones sigue en progreso; instrumentación LLM y refactors de pipeline son post-MVP.

## Fases, IR y Normalización
- `PHASE_2_UNIFIED_CONSTRAINT_EXTRACTOR.md` + `PHASE_2_EXECUTIVE_SUMMARY.md`: diseño e implementación completa de SemanticNormalizer + UnifiedConstraintExtractor (57/57 tests, impacto +18-20% compliance).
- `CONSTRAINT_EQUIVALENCE_MAPPING_REFERENCE.md`: mapa canónico de entidades, campos, tipos de constraint y enforcement para Phase 2.
- `PHASE2_REAL_ENFORCEMENT_PLAN.md`: trabajo pendiente para convertir 6 validaciones descriptivas en enforcement real.
- `PHASE_3_IR_AWARE_SEMANTIC_MATCHING.md` (diseño) y `PHASE_3.5_GROUND_TRUTH_NORMALIZATION.md` (implementación core lista) apuntan a matching IR y ground truth determinista.
- `SEMANTIC_VALIDATION_ARCHITECTURE.md`: ApplicationIR como fuente única; fases 1-4 marcadas completas.
- `COMPLIANCE_VALIDATOR_DEFENSIVE_HELPERS.md`: helpers para compatibilidad ApplicationIR vs SpecRequirements.
- `IR_COMPLIANCE_IN_MEMORY_VALIDATION.md`: validación IR en memoria sin depender de archivos físicos.
- `IR_MATCHING_IMPROVEMENT_PLAN.md`: estrategia STRICT/RELAXED con mejoras ya aplicadas (0%→100% en entidades/flows/constraints).

## Pipeline E2E y Estratificado
- `PHASES.md`, `PIPELINE_E2E_PHASES.md`, `pipeline/phases.md`: orden y uso de IR en cada fase; referencia de comandos E2E.
- `PIPELINE_IMPROVEMENT_PLAN.md` (raíz) y `pipeline/PIPELINE_IMPROVEMENT_PLAN.md`: eliminación de métricas hardcodeadas, renumeración de fases, timeout de extracción.
- `IMPROVEMENT_ROADMAP.md`: dashboard de objetivos post-MVP y progresos recientes.
- `E2E_IR_CENTRIC_INTEGRATION.md` y `E2E_STRATIFIED_INTEGRATION_SUMMARY.md`: integración IR + arquitectura estratificada en el E2E test.
- `E2E_TEST_ANALYSIS_PHASE6.5.md`: análisis/fix del bloqueo en Phase 6.5 (IRSemanticMatcher en batch).
- `STRATIFIED_GENERATION_ARCHITECTURE.md` + `STRATIFIED_ENHANCEMENTS_PLAN.md`: arquitectura a 4 estratos y plan completo ya integrado.
- `DEVMATRIX_TECHNICAL_OVERVIEW.md`: visión técnica general del sistema.
- `specsToApp.md`: diagrama mermaid del flujo SPEC→IR→CODE→VALIDATION→APP.

## Enforcement, Reproducibilidad y Fase 4
- `PHASE4_HIERARCHICAL_EXTRACTION_PLAN.md`: extracción jerárquica completada.
- `PHASE4.1_ENFORCEMENT_STRATEGY_PLAN.md`, `PHASE4.2_IRBUILDER_ENFORCEMENT_PLAN.md`, `PHASE4.3_NEO4J_PERSISTENCE_PLAN.md`, `PHASE4.4_REPRODUCIBILITY_E2E_PLAN.md`: suite de enforcement y persistencia en Neo4j, todas completadas.
- `PHASE2_REAL_ENFORCEMENT_PLAN.md` enlaza con estos para cerrar los 6 casos pendientes.

## Smoke Tests, Repair y Runtime
- `SMOKE_TEST_IMPROVEMENT_PLAN.md`: generador LLM de planes de smoke tests, orquestador y agentes listos.
- `SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md`: conexión smoke→repair para ciclo continuo.
- `FIXES_2025-11-30_RUNTIME_AND_LEARNING.md`: fallbacks de health check/runtime y ajustes al learner.
- `smoke_tests/TESTS_IR_PLAN.md`: TestsModelIR y generación determinista de pruebas IR.

## Aprendizaje y Retroalimentación
- `learning/`:
  - `LEARNING_SYSTEM_ARCHITECTURE.md`, `LEARNING_SYSTEM_OVERVIEW.md`: mapa y estado actual vs objetivo.
  - `LEARNING_GAPS_IMPLEMENTATION_PLAN.md`: 7/7 gaps implementados.
  - `LEARNING_SYSTEM_REDESIGN.md`: rediseño v2 parcialmente implementado.
  - `GENERATION_FEEDBACK_LOOP.md`, `SMOKE_REPAIR_LEARNING_PLAN.md`, `SESSION_2025-11-29_IMPLEMENTATION.md`: cierre del loop generación→smoke→repair→learning y pendientes de reutilización.
  - `LEARNING_ARCHITECTURE_GAPS_2025-11-30.md`: cuatro gaps críticos identificados (aplicación de aprendizaje solo a ~6% del código).

## LLM, Instrumentación y Streaming
- `LLM_MODEL_STRATEGY.md`: asignación Opus/Sonnet/Haiku por tipo de tarea; bug de modelo Sonnet corregido.
- `LLM_INSTRUMENTATION_PLAN.md`: plan para centralizar clientes instrumentados (latencia 0.0ms es síntoma).
- `STREAMING_IMPLEMENTATION_PLAN.md`: modo streaming para specs >20KB en SpecToApplicationIR.
- `SPEC_TRANSLATOR_ARCHITECTURE.md`: reglas de traducción sin alterar contenido.

## Infra IR y Caché
- `REDIS_IR_CACHE.md`: cache multi-tier Redis→filesystem→LLM con TTL 7 días e invalidación por hash.
- `IR_MIGRATION_PLAN.md`: uso de ApplicationIR en fases 3 y 7 (migración completada).

## Neo4j y Bases de Datos
- Principales: `neo4j/NEO4J_INTEGRATION_PLAN.md`, `neo4j/MIGRATION_PROGRESS.md`, `neo4j/DATA_STRUCTURES_INVENTORY.md`, `neo4j/DATABASE_ARCHITECTURE.md`.
- Políticas/contratos: `neo4j/DUAL_WRITE_RETIREMENT.yml`, `neo4j/GRAPH_SHAPE_CONTRACT.yml`.
- Mejoras: `neo4j/improvements/` (`ACTION_PLAN.md`, `PIPELINE_DB_GAPS.md`, `RISKS.md`, `SPRINT_0-2.md`, `SPRINT_3-5.md`, `SPRINT_6-8.md`, `SPRINT3_EDGE_DESIGN.md`, `SPRINT5_REDESIGN.md`, `SUMMARY.md`, `VISION_2.0.md`) con sprints y riesgos mitigados.

## QA y Métricas
- `qa/QA_COMPREHENSIVE_REPORT_2025-11-28.md`: auditoría completa del sistema.
- Reports por ejecución: `qa/QA_REPORT_ecommerce_1764321087.md`, `qa/QA_REPORT_ecommerce_1764323550.md`, `qa/ecommerce-api-spec-human_1764082377_qa_report.md`.
- `CODE_GENERATION_BUG_FIXES.md`: fixes aplicados tras QA.

## Debug y Planes de Fix
- `debug/` incluye: `CODE_GENERATION_FIX_PLAN.md`, `CRITICAL_BUGS_2025-11-27.md`, `FIX_PLAN_REALISTIC.md`, `FIX_PLAN_V2.md`, `HARDCODING_ELIMINATION_PLAN.md`, `HONEST_BUG_STATUS.md`, `REMOVE_HARDCODED_PRODUCTION_MODE.md`, `SMOKE_REPAIR_DISCONNECT.md`, `SMOKE_TEST_FAILURES_INVESTIGATION.md`, `VALIDATION_LOSS_ROOT_CAUSE_PLAN.md`, `VALIDATION_LOSS_ROOT_CAUSE_PLAN_V2.md`. Cubren eliminación de hardcoding, bugs críticos, desconexión smoke→repair y pérdida de validación.

## Anti / Run Analyses
- `anti/COGNITIVE_CODE_GENERATION_PROPOSAL.md`: propuesta IR-céntrica de generación cognitiva.
- `anti/PRO_DASHBOARD_IMPLEMENTATION_PLAN.md`: dashboard unificado de ejecución/learning.
- `anti/SMOKE_REPAIR_HARDENING_PLAN.md`: endurecer repair ante fallas smoke.
- `anti/analysis_and_action_plan.md`, `anti/run_analysis_047.md`, `anti/root_causes_047.md`, `anti/errors_incongruences_047.md`, `anti/report_verification_047.md`, `anti/code_verification_047.md`, `anti/errors_047.txt`: análisis exhaustivo del run 047 con hallazgos, verificaciones y métricas.

## Nicetohave y Refactors
- `nicetohave/PIPELINE_REFACTORING_PLAN.md` + `PIPELINE_REFACTORING_PLAN_FULL.md`: mover el monolito E2E a `/src/pipeline/*`.
- `nicetohave/TEMPLATE_ELIMINATION_PLAN.md` + `nicetohave/nicestpan.md`: migrar a PatternBank y formalizar Quality Gate estrato 4.

## Misceláneos
- `SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md` ya cubierto en smoke/repair.
- `STREAMING_IMPLEMENTATION_PLAN.md` ya cubierto en LLM/streaming.
- `STRATIFIED_ENHANCEMENTS_PLAN.md` y `STRATIFIED_GENERATION_ARCHITECTURE.md` ya cubiertos en pipeline/estratos.
- `Fases del pipeline` duplicadas en `PHASES.md` y `PIPELINE_E2E_PHASES.md` para referencia rápida.
