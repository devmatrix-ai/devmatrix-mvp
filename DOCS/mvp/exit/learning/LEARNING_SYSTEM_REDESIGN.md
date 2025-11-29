# Learning System Redesign v2.0

**Fecha:** 2025-11-29
**Objetivo:** Rediseño completo del sistema de learning para maximizar precisión
**Estado:** Design Document

---

## 1. Arquitectura Actual (AS-IS)

### 1.1 Infraestructura Existente

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASES DISPONIBLES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Neo4j (46,636 nodos)                 Qdrant (31,230 vectors)               │
│  ├── Pattern (31,811)                 ├── devmatrix_patterns (30,126)       │
│  ├── ApplicationIR (278)              ├── semantic_patterns (48)            │
│  │   ├── DomainModelIR (280)          └── code_generation_feedback (1,056)  │
│  │   │   ├── Entity (1,084)                                                  │
│  │   │   └── Attribute (5,204)                                               │
│  │   ├── APIModelIR (280)                                                    │
│  │   │   ├── Endpoint (4,022)                                                │
│  │   │   └── APIParameter (668)                                              │
│  │   ├── BehaviorModel (280)                                                 │
│  │   ├── ValidationModel (280)                                               │
│  │   └── InfrastructureModel (280)                                           │
│  ├── SuccessfulCode (850)                                                    │
│  ├── CodeGenerationError (523)                                               │
│  └── AtomicTask (100) + DEPENDS_ON                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Problemas Actuales

| Problema | Causa Raíz | Impacto |
|----------|-----------|---------|
| Pattern promotion = 0% | Sin feedback de smoke tests | Patterns nunca maduran |
| Smoke tests 47.7% | No se correlaciona con patterns | No se identifica qué patterns fallan |
| Learning aislado | Neo4j y Qdrant no conectados | Datos duplicados, sin insights |
| Sin lineage | No tracked: Pattern → Code → Test | No causalidad |
| Classification 41.2% | Sin retraining loop | Nunca mejora |

### 1.3 Flujo Actual (Roto)

```
Spec → IR → Code Generation → Tests → (void)
              ↓
         Patterns usados
              ↓
         (no feedback)
              ↓
         Score = 0.00
              ↓
         No promotion
```

---

## 2. Arquitectura Propuesta (TO-BE)

### 2.1 Nuevo Modelo de Datos Neo4j

```cypher
// ============================================================
// NUEVOS NODOS PARA LEARNING
// ============================================================

// Generation: Representa una ejecución completa del pipeline
CREATE CONSTRAINT generation_id IF NOT EXISTS
FOR (g:Generation) REQUIRE g.generation_id IS UNIQUE;

// GeneratedFile: Cada archivo generado con su pattern source
CREATE CONSTRAINT file_id IF NOT EXISTS
FOR (f:GeneratedFile) REQUIRE f.file_id IS UNIQUE;

// SmokeTestResult: Resultado de smoke test por endpoint
CREATE CONSTRAINT smoke_id IF NOT EXISTS
FOR (s:SmokeTestResult) REQUIRE s.smoke_id IS UNIQUE;

// LearningEvent: Eventos de feedback (positivo/negativo)
CREATE CONSTRAINT event_id IF NOT EXISTS
FOR (e:LearningEvent) REQUIRE e.event_id IS UNIQUE;

// PatternScore: Score acumulativo de un pattern
CREATE CONSTRAINT score_id IF NOT EXISTS
FOR (ps:PatternScore) REQUIRE ps.pattern_id IS UNIQUE;
```

### 2.2 Nuevas Relaciones (Lineage Tracking)

```cypher
// ============================================================
// LINEAGE: IR → Pattern → Code → Test
// ============================================================

// Pattern genera archivo
(p:Pattern)-[:GENERATED {
    generation_id: string,
    timestamp: datetime,
    stratum: string  // TEMPLATE, AST, LLM
}]->(f:GeneratedFile)

// Archivo pertenece a generation
(f:GeneratedFile)-[:PART_OF]->(g:Generation)

// Generation usa ApplicationIR
(g:Generation)-[:FROM_IR]->(app:ApplicationIR)

// Smoke test sobre endpoint
(s:SmokeTestResult)-[:TESTS]->(ep:Endpoint)

// Smoke test sobre generation
(s:SmokeTestResult)-[:IN_GENERATION]->(g:Generation)

// Learning event sobre pattern
(e:LearningEvent)-[:AFFECTS]->(p:Pattern)

// Learning event desde test
(e:LearningEvent)-[:FROM_TEST]->(s:SmokeTestResult)
```

### 2.3 Schema Completo de Nodos

```yaml
Generation:
  generation_id: uuid
  app_name: string
  spec_path: string
  timestamp: datetime
  total_files: int
  smoke_pass_rate: float
  semantic_compliance: float
  ir_compliance_strict: float
  ir_compliance_relaxed: float
  patterns_used: int
  stratum_distribution: json  # {TEMPLATE: 31, AST: 59, LLM: 6}
  duration_ms: int
  status: string  # success, partial, failed

GeneratedFile:
  file_id: uuid
  path: string  # src/services/product_service.py
  stratum: string  # TEMPLATE, AST, LLM
  pattern_id: string  # Pattern que lo generó
  size_bytes: int
  loc: int
  syntax_valid: boolean
  entity_name: string  # Si aplica
  endpoint_path: string  # Si aplica

SmokeTestResult:
  smoke_id: uuid
  endpoint_path: string
  method: string  # GET, POST, etc
  scenario_name: string
  expected_status: int
  actual_status: int
  passed: boolean
  error_type: string  # null, "500", "404", "422"
  error_message: string
  response_time_ms: int
  timestamp: datetime

LearningEvent:
  event_id: uuid
  event_type: string  # positive, negative
  source: string  # smoke_test, validation, repair, manual
  pattern_id: string
  weight: float  # 1.0 for smoke, 0.5 for validation
  reason: string
  timestamp: datetime
  metadata: json

PatternScore:
  pattern_id: string
  current_score: float  # 0.0 - 1.0
  positive_events: int
  negative_events: int
  total_usages: int
  success_rate: float
  last_updated: datetime
  promotion_eligible: boolean
  stratum: string  # current stratum
```

### 2.4 Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LEARNING CYCLE v2.0                                     │
└─────────────────────────────────────────────────────────────────────────────┘

                                 ┌──────────────┐
                                 │     Spec     │
                                 └──────┬───────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │    Phase 1: Spec Ingestion    │
                         │    → ApplicationIR (Neo4j)    │
                         └──────────────┬───────────────┘
                                        │
    ┌───────────────────────────────────┼───────────────────────────────────┐
    │                                   │                                    │
    ▼                                   ▼                                    ▼
┌─────────┐                      ┌─────────────┐                      ┌─────────────┐
│ Domain  │                      │    API      │                      │  Behavior   │
│ Model   │                      │   Model     │                      │   Model     │
│(Entity) │                      │ (Endpoint)  │                      │  (Flow)     │
└────┬────┘                      └──────┬──────┘                      └──────┬──────┘
     │                                  │                                    │
     └──────────────────────────────────┼────────────────────────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   Phase 6: Code Generation    │
                         │   PatternBank.search() →      │
                         │   Patterns (Qdrant + Neo4j)   │
                         └──────────────┬───────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
            ┌───────────────┐                       ┌───────────────┐
            │ Pattern Match │                       │  LLM Generate │
            │   (reuse)     │                       │   (new code)  │
            └───────┬───────┘                       └───────┬───────┘
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     CREATE GeneratedFile      │
                         │     [:GENERATED] from Pattern │
                         │     [:PART_OF] → Generation   │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   Phase 8.5: Smoke Tests      │
                         │   For each endpoint:          │
                         │   → Execute HTTP request      │
                         │   → CREATE SmokeTestResult    │
                         └──────────────┬───────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
            ┌───────────────┐                       ┌───────────────┐
            │    PASSED     │                       │    FAILED     │
            │  status=200   │                       │  status=500   │
            └───────┬───────┘                       └───────┬───────┘
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │  CREATE LearningEvent │               │  CREATE LearningEvent │
        │  type: positive       │               │  type: negative       │
        │  weight: 1.0          │               │  weight: 1.0          │
        │  [:AFFECTS]→Pattern   │               │  [:AFFECTS]→Pattern   │
        │  [:FROM_TEST]→Smoke   │               │  [:FROM_TEST]→Smoke   │
        └───────────┬───────────┘               └───────────┬───────────┘
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     UPDATE PatternScore       │
                         │     score = weighted_avg      │
                         │     (positive - negative)     │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   Phase 10: Pattern Promotion │
                         │   IF score > 0.7:             │
                         │     promote(LLM → AST)        │
                         │     promote(AST → TEMPLATE)   │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     Qdrant: Update Vector     │
                         │     success_rate, usage_count │
                         └──────────────────────────────┘
```

---

## 3. Implementación Detallada

### 3.1 Migration Script: New Learning Schema

```python
# scripts/migrations/neo4j/005_learning_schema.cypher

// Create constraints
CREATE CONSTRAINT generation_id IF NOT EXISTS
FOR (g:Generation) REQUIRE g.generation_id IS UNIQUE;

CREATE CONSTRAINT file_id IF NOT EXISTS
FOR (f:GeneratedFile) REQUIRE f.file_id IS UNIQUE;

CREATE CONSTRAINT smoke_id IF NOT EXISTS
FOR (s:SmokeTestResult) REQUIRE s.smoke_id IS UNIQUE;

CREATE CONSTRAINT event_id IF NOT EXISTS
FOR (e:LearningEvent) REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT score_pattern_id IF NOT EXISTS
FOR (ps:PatternScore) REQUIRE ps.pattern_id IS UNIQUE;

// Create indexes for queries
CREATE INDEX generation_timestamp IF NOT EXISTS
FOR (g:Generation) ON (g.timestamp);

CREATE INDEX generation_status IF NOT EXISTS
FOR (g:Generation) ON (g.status);

CREATE INDEX smoke_passed IF NOT EXISTS
FOR (s:SmokeTestResult) ON (s.passed);

CREATE INDEX event_type IF NOT EXISTS
FOR (e:LearningEvent) ON (e.event_type);

CREATE INDEX score_eligible IF NOT EXISTS
FOR (ps:PatternScore) ON (ps.promotion_eligible);
```

### 3.2 Learning Repository

```python
# src/cognitive/services/learning_repository.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

@dataclass
class GenerationRecord:
    generation_id: str
    app_name: str
    spec_path: str
    smoke_pass_rate: float
    semantic_compliance: float
    patterns_used: List[str]
    stratum_distribution: Dict[str, int]

@dataclass
class SmokeTestRecord:
    endpoint_path: str
    method: str
    scenario_name: str
    passed: bool
    expected_status: int
    actual_status: int
    error_type: Optional[str]

@dataclass
class LearningEventRecord:
    event_type: str  # positive, negative
    source: str
    pattern_id: str
    weight: float
    reason: str


class LearningRepository:
    """Repository for learning-related data in Neo4j."""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    # ============================================================
    # GENERATION TRACKING
    # ============================================================

    def create_generation(self, record: GenerationRecord) -> str:
        """Create a new generation record."""
        with self.driver.session() as session:
            result = session.run("""
                CREATE (g:Generation {
                    generation_id: $generation_id,
                    app_name: $app_name,
                    spec_path: $spec_path,
                    timestamp: datetime(),
                    smoke_pass_rate: $smoke_pass_rate,
                    semantic_compliance: $semantic_compliance,
                    patterns_used: $patterns_used,
                    stratum_distribution: $stratum_distribution
                })
                RETURN g.generation_id
            """, **record.__dict__)
            return result.single()[0]

    def link_generation_to_ir(self, generation_id: str, app_id: str):
        """Link generation to its source ApplicationIR."""
        with self.driver.session() as session:
            session.run("""
                MATCH (g:Generation {generation_id: $generation_id})
                MATCH (app:ApplicationIR {app_id: $app_id})
                MERGE (g)-[:FROM_IR]->(app)
            """, generation_id=generation_id, app_id=app_id)

    # ============================================================
    # FILE TRACKING
    # ============================================================

    def record_generated_file(
        self,
        generation_id: str,
        file_path: str,
        pattern_id: str,
        stratum: str,
        entity_name: Optional[str] = None,
        endpoint_path: Optional[str] = None
    ):
        """Record a generated file and link to pattern."""
        file_id = str(uuid4())

        with self.driver.session() as session:
            # Create file node
            session.run("""
                CREATE (f:GeneratedFile {
                    file_id: $file_id,
                    path: $file_path,
                    stratum: $stratum,
                    pattern_id: $pattern_id,
                    entity_name: $entity_name,
                    endpoint_path: $endpoint_path,
                    timestamp: datetime()
                })
            """, file_id=file_id, file_path=file_path, stratum=stratum,
                pattern_id=pattern_id, entity_name=entity_name,
                endpoint_path=endpoint_path)

            # Link to generation
            session.run("""
                MATCH (f:GeneratedFile {file_id: $file_id})
                MATCH (g:Generation {generation_id: $generation_id})
                MERGE (f)-[:PART_OF]->(g)
            """, file_id=file_id, generation_id=generation_id)

            # Link to pattern (if exists)
            if pattern_id:
                session.run("""
                    MATCH (f:GeneratedFile {file_id: $file_id})
                    MATCH (p:Pattern {pattern_id: $pattern_id})
                    MERGE (p)-[:GENERATED {
                        generation_id: $generation_id,
                        stratum: $stratum
                    }]->(f)
                """, file_id=file_id, pattern_id=pattern_id,
                    generation_id=generation_id, stratum=stratum)

        return file_id

    # ============================================================
    # SMOKE TEST TRACKING
    # ============================================================

    def record_smoke_test(
        self,
        generation_id: str,
        record: SmokeTestRecord
    ) -> str:
        """Record smoke test result."""
        smoke_id = str(uuid4())

        with self.driver.session() as session:
            # Create smoke test result
            session.run("""
                CREATE (s:SmokeTestResult {
                    smoke_id: $smoke_id,
                    endpoint_path: $endpoint_path,
                    method: $method,
                    scenario_name: $scenario_name,
                    passed: $passed,
                    expected_status: $expected_status,
                    actual_status: $actual_status,
                    error_type: $error_type,
                    timestamp: datetime()
                })
            """, smoke_id=smoke_id, **record.__dict__)

            # Link to generation
            session.run("""
                MATCH (s:SmokeTestResult {smoke_id: $smoke_id})
                MATCH (g:Generation {generation_id: $generation_id})
                MERGE (s)-[:IN_GENERATION]->(g)
            """, smoke_id=smoke_id, generation_id=generation_id)

            # Link to endpoint (if exists)
            session.run("""
                MATCH (s:SmokeTestResult {smoke_id: $smoke_id})
                MATCH (ep:Endpoint)
                WHERE ep.path = $endpoint_path AND ep.method = $method
                MERGE (s)-[:TESTS]->(ep)
            """, smoke_id=smoke_id,
                endpoint_path=record.endpoint_path,
                method=record.method)

        return smoke_id

    # ============================================================
    # LEARNING EVENTS
    # ============================================================

    def record_learning_event(
        self,
        smoke_id: str,
        record: LearningEventRecord
    ):
        """Record a learning event (positive or negative feedback)."""
        event_id = str(uuid4())

        with self.driver.session() as session:
            # Create event
            session.run("""
                CREATE (e:LearningEvent {
                    event_id: $event_id,
                    event_type: $event_type,
                    source: $source,
                    pattern_id: $pattern_id,
                    weight: $weight,
                    reason: $reason,
                    timestamp: datetime()
                })
            """, event_id=event_id, **record.__dict__)

            # Link to pattern
            session.run("""
                MATCH (e:LearningEvent {event_id: $event_id})
                MATCH (p:Pattern {pattern_id: $pattern_id})
                MERGE (e)-[:AFFECTS]->(p)
            """, event_id=event_id, pattern_id=record.pattern_id)

            # Link to smoke test
            session.run("""
                MATCH (e:LearningEvent {event_id: $event_id})
                MATCH (s:SmokeTestResult {smoke_id: $smoke_id})
                MERGE (e)-[:FROM_TEST]->(s)
            """, event_id=event_id, smoke_id=smoke_id)

            # Update pattern score
            self._update_pattern_score(record.pattern_id, record)

        return event_id

    def _update_pattern_score(self, pattern_id: str, event: LearningEventRecord):
        """Update cumulative pattern score."""
        with self.driver.session() as session:
            # Upsert PatternScore
            if event.event_type == "positive":
                session.run("""
                    MERGE (ps:PatternScore {pattern_id: $pattern_id})
                    ON CREATE SET
                        ps.current_score = $weight,
                        ps.positive_events = 1,
                        ps.negative_events = 0,
                        ps.total_usages = 1,
                        ps.last_updated = datetime()
                    ON MATCH SET
                        ps.positive_events = ps.positive_events + 1,
                        ps.total_usages = ps.total_usages + 1,
                        ps.current_score = toFloat(ps.positive_events) /
                            (ps.positive_events + ps.negative_events),
                        ps.last_updated = datetime()
                """, pattern_id=pattern_id, weight=event.weight)
            else:
                session.run("""
                    MERGE (ps:PatternScore {pattern_id: $pattern_id})
                    ON CREATE SET
                        ps.current_score = 0.0,
                        ps.positive_events = 0,
                        ps.negative_events = 1,
                        ps.total_usages = 1,
                        ps.last_updated = datetime()
                    ON MATCH SET
                        ps.negative_events = ps.negative_events + 1,
                        ps.total_usages = ps.total_usages + 1,
                        ps.current_score = toFloat(ps.positive_events) /
                            (ps.positive_events + ps.negative_events),
                        ps.last_updated = datetime()
                """, pattern_id=pattern_id)

            # Check promotion eligibility
            session.run("""
                MATCH (ps:PatternScore {pattern_id: $pattern_id})
                SET ps.promotion_eligible = (
                    ps.current_score >= 0.7 AND
                    ps.total_usages >= 3
                ),
                ps.success_rate = toFloat(ps.positive_events) /
                    CASE WHEN ps.total_usages > 0
                         THEN ps.total_usages
                         ELSE 1 END
            """, pattern_id=pattern_id)

    # ============================================================
    # QUERIES FOR LEARNING INSIGHTS
    # ============================================================

    def get_patterns_ready_for_promotion(self) -> List[Dict]:
        """Get patterns eligible for promotion."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ps:PatternScore)
                WHERE ps.promotion_eligible = true
                MATCH (p:Pattern {pattern_id: ps.pattern_id})
                RETURN p.pattern_id as pattern_id,
                       p.name as name,
                       p.stratum as current_stratum,
                       ps.current_score as score,
                       ps.success_rate as success_rate,
                       ps.total_usages as usages
                ORDER BY ps.current_score DESC
            """)
            return [dict(r) for r in result]

    def get_failing_patterns(self, min_failures: int = 3) -> List[Dict]:
        """Get patterns with high failure rates."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ps:PatternScore)
                WHERE ps.negative_events >= $min_failures
                  AND ps.success_rate < 0.5
                MATCH (p:Pattern {pattern_id: ps.pattern_id})
                RETURN p.pattern_id as pattern_id,
                       p.name as name,
                       ps.negative_events as failures,
                       ps.success_rate as success_rate,
                       ps.total_usages as usages
                ORDER BY ps.negative_events DESC
            """, min_failures=min_failures)
            return [dict(r) for r in result]

    def get_endpoint_failure_analysis(self) -> List[Dict]:
        """Analyze which endpoints fail most often."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:SmokeTestResult)
                WHERE s.passed = false
                WITH s.endpoint_path as endpoint,
                     s.method as method,
                     s.error_type as error_type,
                     count(*) as failure_count
                RETURN endpoint, method, error_type, failure_count
                ORDER BY failure_count DESC
                LIMIT 20
            """)
            return [dict(r) for r in result]

    def get_pattern_to_failure_correlation(self) -> List[Dict]:
        """Correlate patterns with specific failure types."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Pattern)-[:GENERATED]->(f:GeneratedFile)
                      -[:PART_OF]->(g:Generation)
                      <-[:IN_GENERATION]-(s:SmokeTestResult {passed: false})
                WITH p.pattern_id as pattern_id,
                     p.name as pattern_name,
                     s.error_type as error_type,
                     count(*) as occurrences
                WHERE occurrences >= 2
                RETURN pattern_id, pattern_name, error_type, occurrences
                ORDER BY occurrences DESC
            """)
            return [dict(r) for r in result]

    def get_learning_summary(self) -> Dict:
        """Get overall learning system summary."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ps:PatternScore)
                WITH count(*) as total_patterns,
                     sum(CASE WHEN ps.promotion_eligible THEN 1 ELSE 0 END) as eligible,
                     avg(ps.success_rate) as avg_success_rate,
                     sum(ps.positive_events) as total_positive,
                     sum(ps.negative_events) as total_negative

                MATCH (g:Generation)
                WITH total_patterns, eligible, avg_success_rate,
                     total_positive, total_negative,
                     count(g) as total_generations,
                     avg(g.smoke_pass_rate) as avg_smoke_pass

                RETURN {
                    total_patterns: total_patterns,
                    promotion_eligible: eligible,
                    avg_success_rate: avg_success_rate,
                    total_positive_events: total_positive,
                    total_negative_events: total_negative,
                    total_generations: total_generations,
                    avg_smoke_pass_rate: avg_smoke_pass
                } as summary
            """)
            return dict(result.single()["summary"])
```

### 3.3 Smoke Test Integration

```python
# src/validation/smoke_test_learning.py

class SmokeTestLearning:
    """Integrates smoke test results with learning system."""

    def __init__(
        self,
        learning_repo: LearningRepository,
        generation_manifest: dict
    ):
        self.repo = learning_repo
        self.manifest = generation_manifest
        self.pattern_map = self._build_pattern_map()

    def _build_pattern_map(self) -> Dict[str, str]:
        """Map file paths to pattern IDs from manifest."""
        pattern_map = {}
        for file_info in self.manifest.get("files", []):
            path = file_info.get("path")
            pattern_id = file_info.get("pattern_id")
            if path and pattern_id:
                pattern_map[path] = pattern_id
        return pattern_map

    def _find_pattern_for_endpoint(self, endpoint_path: str, method: str) -> Optional[str]:
        """Find the pattern that generated code for an endpoint."""
        # Derive service file from endpoint
        # e.g., /products → src/services/product_service.py
        entity = endpoint_path.split("/")[1] if "/" in endpoint_path else ""
        if entity.endswith("s"):
            entity = entity[:-1]

        possible_files = [
            f"src/services/{entity}_service.py",
            f"src/api/routes/{entity}_routes.py",
            f"src/api/routes/{entity}s_routes.py"
        ]

        for file_path in possible_files:
            if file_path in self.pattern_map:
                return self.pattern_map[file_path]

        return None

    async def process_smoke_results(
        self,
        generation_id: str,
        smoke_results: List[Dict]
    ):
        """Process all smoke test results and create learning events."""
        for result in smoke_results:
            # Record the smoke test
            smoke_record = SmokeTestRecord(
                endpoint_path=result["endpoint"],
                method=result["method"],
                scenario_name=result["scenario"],
                passed=result["passed"],
                expected_status=result["expected_status"],
                actual_status=result["actual_status"],
                error_type=result.get("error_type")
            )

            smoke_id = self.repo.record_smoke_test(generation_id, smoke_record)

            # Find pattern and create learning event
            pattern_id = self._find_pattern_for_endpoint(
                result["endpoint"],
                result["method"]
            )

            if pattern_id:
                event_record = LearningEventRecord(
                    event_type="positive" if result["passed"] else "negative",
                    source="smoke_test",
                    pattern_id=pattern_id,
                    weight=1.0,
                    reason=f"Smoke test {'passed' if result['passed'] else 'failed'}: "
                           f"{result['method']} {result['endpoint']}"
                )

                self.repo.record_learning_event(smoke_id, event_record)

        # Log summary
        passed = sum(1 for r in smoke_results if r["passed"])
        failed = len(smoke_results) - passed
        print(f"    📊 Learning events recorded: {passed} positive, {failed} negative")
```

### 3.4 Qdrant Sync

```python
# src/cognitive/services/learning_qdrant_sync.py

class LearningQdrantSync:
    """Syncs learning data from Neo4j to Qdrant."""

    def __init__(self, neo4j_driver, qdrant_client):
        self.neo4j = neo4j_driver
        self.qdrant = qdrant_client

    def sync_pattern_scores(self):
        """Sync pattern scores to Qdrant payload."""
        with self.neo4j.session() as session:
            result = session.run("""
                MATCH (ps:PatternScore)
                RETURN ps.pattern_id as pattern_id,
                       ps.success_rate as success_rate,
                       ps.total_usages as usage_count,
                       ps.promotion_eligible as production_ready
            """)

            updates = []
            for r in result:
                updates.append({
                    "id": r["pattern_id"],
                    "payload": {
                        "success_rate": r["success_rate"],
                        "usage_count": r["usage_count"],
                        "production_ready": r["production_ready"]
                    }
                })

            # Batch update Qdrant
            if updates:
                self.qdrant.batch_update_payload(
                    collection_name="devmatrix_patterns",
                    updates=updates
                )
                print(f"    🔄 Synced {len(updates)} pattern scores to Qdrant")
```

---

## 4. Pipeline Integration

### 4.1 Cambios en real_e2e_full_pipeline.py

```python
# En _initialize_services():
from src.cognitive.services.learning_repository import LearningRepository
from src.validation.smoke_test_learning import SmokeTestLearning

self.learning_repo = LearningRepository(self.neo4j_driver)

# En _phase_6_code_generation() - después de generar código:
self.generation_id = self.learning_repo.create_generation(
    GenerationRecord(
        generation_id=str(uuid4()),
        app_name=self.spec_name,
        spec_path=self.spec_path,
        smoke_pass_rate=0.0,  # Updated later
        semantic_compliance=0.0,  # Updated later
        patterns_used=[...],  # From manifest
        stratum_distribution=self.stratum_metrics
    )
)

# Link to ApplicationIR
self.learning_repo.link_generation_to_ir(
    self.generation_id,
    str(self.application_ir.app_id)
)

# Record each generated file
for file_path, file_info in self.generation_manifest["files"].items():
    self.learning_repo.record_generated_file(
        generation_id=self.generation_id,
        file_path=file_path,
        pattern_id=file_info.get("pattern_id"),
        stratum=file_info.get("stratum"),
        entity_name=file_info.get("entity"),
        endpoint_path=file_info.get("endpoint")
    )

# En _phase_85_runtime_smoke_test() - después de ejecutar tests:
smoke_learning = SmokeTestLearning(
    learning_repo=self.learning_repo,
    generation_manifest=self.generation_manifest
)

await smoke_learning.process_smoke_results(
    generation_id=self.generation_id,
    smoke_results=smoke_result.all_results
)

# En _phase_11_learning() - usar nueva data:
# Get patterns ready for promotion
ready_patterns = self.learning_repo.get_patterns_ready_for_promotion()
print(f"    📊 Patterns ready for promotion: {len(ready_patterns)}")

for pattern in ready_patterns:
    print(f"       ✅ {pattern['name']}: score={pattern['score']:.2f}, "
          f"usages={pattern['usages']}")

# Get failing patterns for analysis
failing = self.learning_repo.get_failing_patterns()
if failing:
    print(f"    ⚠️ Failing patterns detected: {len(failing)}")
    for p in failing[:5]:
        print(f"       ❌ {p['name']}: failures={p['failures']}, "
              f"rate={p['success_rate']:.2%}")

# Summary
summary = self.learning_repo.get_learning_summary()
print(f"\n    📈 Learning Summary:")
print(f"       Total patterns tracked: {summary['total_patterns']}")
print(f"       Promotion eligible: {summary['promotion_eligible']}")
print(f"       Avg success rate: {summary['avg_success_rate']:.2%}")
print(f"       Total events: +{summary['total_positive_events']} / "
      f"-{summary['total_negative_events']}")
```

---

## 5. Métricas de Éxito

### 5.1 KPIs

| Métrica | Antes | Target (Sprint 1) | Target (Sprint 3) |
|---------|-------|-------------------|-------------------|
| Pattern Promotion Rate | 0% | >20% | >50% |
| Pattern Score Coverage | 0% | >80% | 100% |
| Smoke Test Pass Rate | 47.7% | 60% | 80% |
| Lineage Tracking | 0% | 100% | 100% |
| Learning Events/Run | 0 | >50 | >100 |
| Failing Pattern Detection | 0 | >90% | 100% |

### 5.2 Queries de Monitoreo

```cypher
// Health check: Learning system status
MATCH (ps:PatternScore)
RETURN {
    total_tracked: count(ps),
    avg_score: avg(ps.current_score),
    eligible_promotion: sum(CASE WHEN ps.promotion_eligible THEN 1 ELSE 0 END),
    total_events: sum(ps.positive_events) + sum(ps.negative_events)
} as health

// Trend: Learning over time
MATCH (g:Generation)
WHERE g.timestamp > datetime() - duration('P7D')
RETURN date(g.timestamp) as day,
       count(g) as generations,
       avg(g.smoke_pass_rate) as avg_pass_rate
ORDER BY day

// Impact: Patterns that improved
MATCH (ps:PatternScore)
WHERE ps.success_rate > 0.7 AND ps.total_usages >= 5
RETURN ps.pattern_id, ps.success_rate, ps.total_usages
ORDER BY ps.success_rate DESC
LIMIT 10
```

---

## 6. Roadmap de Implementación

### Sprint L1: Foundation (3-4 días)

| Día | Task | Output |
|-----|------|--------|
| 1 | Migration script Neo4j | 005_learning_schema.cypher |
| 1 | LearningRepository base | learning_repository.py |
| 2 | SmokeTestLearning | smoke_test_learning.py |
| 2 | Pipeline integration | real_e2e_full_pipeline.py |
| 3 | Qdrant sync | learning_qdrant_sync.py |
| 3 | Tests + validation | test_learning_*.py |
| 4 | E2E verification | Full pipeline run |

### Sprint L2: Analytics (2-3 días)

| Día | Task | Output |
|-----|------|--------|
| 1 | Learning queries | queries/learning/*.cypher |
| 1 | Pattern analysis API | pattern_analysis.py |
| 2 | CLI dashboard | learning_dashboard.py |
| 2 | Report integration | Metrics in E2E report |
| 3 | Documentation | Updated docs |

### Sprint L3: Optimization (2-3 días)

| Día | Task | Output |
|-----|------|--------|
| 1 | Batch processing | Optimized bulk ops |
| 1 | Caching layer | Redis for hot data |
| 2 | Auto-promotion | Automatic stratum promotion |
| 2 | Alert system | Failing pattern alerts |
| 3 | A/B testing | Pattern comparison |

---

## 7. Active Learning: Error Avoidance in Code Generation

### 7.1 Concepto

El learning no solo debe acumular scores para promoción futura. Debe **aplicarse activamente** en la siguiente generación para evitar errores ya cometidos.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ACTIVE LEARNING LOOP                                      │
└─────────────────────────────────────────────────────────────────────────────┘

    Generation N                          Generation N+1
    ────────────                          ──────────────
    Pattern A genera                      ANTES de generar:
    POST /products                        1. Query: "errores en POST /products"
           ↓                              2. Encontrar: "500 - missing db.commit()"
    Smoke test: 500                       3. Inyectar en contexto:
    Error: db.commit() missing               "EVITAR: olvidar db.commit()"
           ↓                              4. Generar con awareness
    Guardar en Neo4j:                            ↓
    (Pattern A)-[:CAUSED_ERROR]->         Código SIN el error
    (Error {type: "missing_commit"})
```

### 7.2 Nuevo Modelo: ErrorKnowledge

```cypher
// Nodo que representa conocimiento de error aprendido
CREATE CONSTRAINT error_knowledge_id IF NOT EXISTS
FOR (ek:ErrorKnowledge) REQUIRE ek.knowledge_id IS UNIQUE;

ErrorKnowledge:
  knowledge_id: uuid
  error_type: string          # "missing_commit", "wrong_status_code", etc.
  pattern_category: string    # "service", "route", "repository"
  entity_type: string         # "product", "customer", etc.
  endpoint_pattern: string    # "POST /{entity}", "PUT /{entity}/{id}"
  error_signature: string     # Hash del error para dedup
  description: string         # Human readable
  avoidance_hint: string      # "Always call db.commit() after create"
  code_example_bad: string    # Código que causó el error
  code_example_good: string   # Código correcto (del fix)
  occurrence_count: int       # Cuántas veces ocurrió
  last_seen: datetime
  confidence: float           # 0.0-1.0 basado en ocurrencias
```

### 7.3 Relaciones de Error Knowledge

```cypher
// Pattern causó el error
(p:Pattern)-[:CAUSED_ERROR {
    generation_id: string,
    timestamp: datetime
}]->(ek:ErrorKnowledge)

// Error afecta tipo de endpoint
(ek:ErrorKnowledge)-[:AFFECTS_ENDPOINT_TYPE]->(et:EndpointType)

// Error afecta tipo de entidad
(ek:ErrorKnowledge)-[:AFFECTS_ENTITY_TYPE]->(entity_type: string)

// Fix resolvió el error
(fix:FixPattern)-[:RESOLVES]->(ek:ErrorKnowledge)
```

### 7.4 Error Knowledge Repository

```python
# src/cognitive/services/error_knowledge_repository.py

@dataclass
class ErrorKnowledge:
    knowledge_id: str
    error_type: str
    pattern_category: str
    entity_type: Optional[str]
    endpoint_pattern: Optional[str]
    description: str
    avoidance_hint: str
    code_example_bad: Optional[str]
    code_example_good: Optional[str]
    occurrence_count: int
    confidence: float


class ErrorKnowledgeRepository:
    """Repository for learned error knowledge."""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    def learn_from_failure(
        self,
        pattern_id: str,
        error_type: str,
        error_message: str,
        endpoint_path: str,
        entity_name: Optional[str],
        failed_code: str
    ):
        """Learn from a smoke test failure."""
        # Compute error signature for dedup
        signature = self._compute_signature(error_type, endpoint_path)

        # Derive avoidance hint from error
        avoidance_hint = self._generate_avoidance_hint(error_type, error_message)

        # Derive endpoint pattern
        endpoint_pattern = self._extract_endpoint_pattern(endpoint_path)

        with self.driver.session() as session:
            # Upsert ErrorKnowledge
            session.run("""
                MERGE (ek:ErrorKnowledge {error_signature: $signature})
                ON CREATE SET
                    ek.knowledge_id = $knowledge_id,
                    ek.error_type = $error_type,
                    ek.pattern_category = $pattern_category,
                    ek.entity_type = $entity_name,
                    ek.endpoint_pattern = $endpoint_pattern,
                    ek.description = $error_message,
                    ek.avoidance_hint = $avoidance_hint,
                    ek.code_example_bad = $failed_code,
                    ek.occurrence_count = 1,
                    ek.last_seen = datetime(),
                    ek.confidence = 0.5
                ON MATCH SET
                    ek.occurrence_count = ek.occurrence_count + 1,
                    ek.last_seen = datetime(),
                    ek.confidence = CASE
                        WHEN ek.occurrence_count >= 5 THEN 0.95
                        WHEN ek.occurrence_count >= 3 THEN 0.8
                        ELSE 0.5 + (ek.occurrence_count * 0.1)
                    END

                WITH ek
                MATCH (p:Pattern {pattern_id: $pattern_id})
                MERGE (p)-[:CAUSED_ERROR {timestamp: datetime()}]->(ek)
            """,
                signature=signature,
                knowledge_id=str(uuid4()),
                error_type=error_type,
                pattern_category=self._infer_category(endpoint_path),
                entity_name=entity_name,
                endpoint_pattern=endpoint_pattern,
                error_message=error_message,
                avoidance_hint=avoidance_hint,
                failed_code=failed_code,
                pattern_id=pattern_id
            )

    def learn_from_fix(
        self,
        error_signature: str,
        fix_code: str,
        fix_description: str
    ):
        """Learn from a successful fix."""
        with self.driver.session() as session:
            session.run("""
                MATCH (ek:ErrorKnowledge {error_signature: $signature})
                SET ek.code_example_good = $fix_code,
                    ek.avoidance_hint = $fix_description
            """, signature=error_signature, fix_code=fix_code,
                fix_description=fix_description)

    def get_relevant_errors(
        self,
        endpoint_pattern: str,
        entity_type: Optional[str] = None,
        pattern_category: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[ErrorKnowledge]:
        """Get errors relevant to what we're about to generate."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ek:ErrorKnowledge)
                WHERE ek.confidence >= $min_confidence
                  AND (ek.endpoint_pattern = $endpoint_pattern
                       OR ek.endpoint_pattern IS NULL)
                  AND ($entity_type IS NULL
                       OR ek.entity_type = $entity_type
                       OR ek.entity_type IS NULL)
                  AND ($pattern_category IS NULL
                       OR ek.pattern_category = $pattern_category)
                RETURN ek
                ORDER BY ek.confidence DESC, ek.occurrence_count DESC
                LIMIT 10
            """,
                endpoint_pattern=endpoint_pattern,
                entity_type=entity_type,
                pattern_category=pattern_category,
                min_confidence=min_confidence
            )

            return [self._to_error_knowledge(r["ek"]) for r in result]

    def _generate_avoidance_hint(self, error_type: str, error_message: str) -> str:
        """Generate human-readable avoidance hint."""
        hints = {
            "500": "Ensure proper error handling and database commits",
            "422": "Validate request body matches schema exactly",
            "404": "Verify endpoint path and route registration",
            "IntegrityError": "Check foreign key constraints and unique values",
            "AttributeError": "Verify object attributes exist before access",
            "TypeError": "Check type compatibility in operations",
        }

        for key, hint in hints.items():
            if key in error_type or key in error_message:
                return hint

        return f"Avoid: {error_message[:100]}"

    def _extract_endpoint_pattern(self, endpoint_path: str) -> str:
        """Extract generic pattern from endpoint path."""
        # /products/123 → /products/{id}
        # /carts/456/items → /carts/{id}/items
        import re
        pattern = re.sub(r'/[0-9a-f-]{36}', '/{id}', endpoint_path)
        pattern = re.sub(r'/\d+', '/{id}', pattern)
        return pattern
```

### 7.5 Integración en Code Generation

```python
# src/services/code_generation_service.py

class CodeGenerationService:

    def __init__(self, ..., error_knowledge_repo: ErrorKnowledgeRepository = None):
        ...
        self.error_knowledge = error_knowledge_repo

    async def generate_service_code(
        self,
        entity: Entity,
        endpoints: List[Endpoint],
        ...
    ) -> str:
        """Generate service code with error awareness."""

        # 1. Query learned errors for this entity/endpoint type
        relevant_errors = []
        if self.error_knowledge:
            for endpoint in endpoints:
                errors = self.error_knowledge.get_relevant_errors(
                    endpoint_pattern=self._to_pattern(endpoint.path),
                    entity_type=entity.name.lower(),
                    pattern_category="service"
                )
                relevant_errors.extend(errors)

        # 2. Build error avoidance context
        avoidance_context = self._build_avoidance_context(relevant_errors)

        # 3. Include in generation prompt/context
        generation_context = {
            "entity": entity,
            "endpoints": endpoints,
            "patterns": matched_patterns,
            # NEW: Error avoidance
            "error_avoidance": avoidance_context,
        }

        # 4. Generate with awareness
        if self._should_use_llm(entity, endpoints):
            prompt = self._build_prompt_with_avoidance(generation_context)
            code = await self.llm_client.generate(prompt)
        else:
            code = self._generate_from_template(generation_context)

        return code

    def _build_avoidance_context(self, errors: List[ErrorKnowledge]) -> str:
        """Build context string for error avoidance."""
        if not errors:
            return ""

        lines = ["\n# ERROR AVOIDANCE (learned from previous failures):"]
        for error in errors[:5]:  # Top 5 most relevant
            lines.append(f"# - {error.avoidance_hint}")
            if error.code_example_good:
                lines.append(f"#   CORRECT: {error.code_example_good[:100]}...")

        return "\n".join(lines)

    def _build_prompt_with_avoidance(self, context: dict) -> str:
        """Build LLM prompt that includes error avoidance."""
        base_prompt = self._build_base_prompt(context)

        if context.get("error_avoidance"):
            avoidance_section = f"""
## IMPORTANT: Error Avoidance

The following errors have occurred in similar code before. AVOID them:

{context['error_avoidance']}

Make sure your generated code does NOT have these issues.
"""
            return base_prompt + avoidance_section

        return base_prompt
```

### 7.6 Template Enhancement

Para generación AST/TEMPLATE, agregar validaciones automáticas:

```python
# En _generate_from_template():

def _generate_from_template(self, context: dict) -> str:
    """Generate code from template with error guards."""
    code = self.template_engine.render(context)

    # Apply learned error guards
    if context.get("error_avoidance"):
        code = self._apply_error_guards(code, context["error_avoidance"])

    return code

def _apply_error_guards(self, code: str, errors: List[ErrorKnowledge]) -> str:
    """Apply automatic fixes for known error patterns."""

    for error in errors:
        if error.error_type == "missing_commit":
            # Ensure db.commit() after create/update
            code = self._ensure_db_commit(code)

        elif error.error_type == "missing_refresh":
            # Ensure db.refresh() after commit
            code = self._ensure_db_refresh(code)

        elif error.error_type == "wrong_status_code":
            # Verify status codes match spec
            code = self._fix_status_codes(code)

    return code
```

### 7.7 Flujo Completo de Active Learning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ACTIVE LEARNING FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

GENERATION N:
1. Generate code for POST /products
2. Run smoke test → FAIL (500)
3. Analyze error: "db.commit() missing"
4. Store in ErrorKnowledge:
   - endpoint_pattern: "POST /{entity}"
   - error_type: "missing_commit"
   - avoidance_hint: "Always call db.commit() after create"
   - confidence: 0.5 (first occurrence)

GENERATION N+1:
1. About to generate POST /customers (similar pattern)
2. Query ErrorKnowledge:
   - endpoint_pattern: "POST /{entity}"
   - pattern_category: "service"
3. Found: "missing_commit" error
4. Inject avoidance context:
   "# AVOID: Missing db.commit() after create operations"
5. Generate code WITH commit
6. Run smoke test → PASS
7. Update ErrorKnowledge confidence: 0.8 (fix worked)

GENERATION N+2:
1. About to generate POST /orders
2. Query ErrorKnowledge → same error
3. Confidence now 0.8 → higher priority
4. Generate with automatic db.commit()
5. Smoke test → PASS
6. Pattern promoted based on consistent success
```

### 7.8 Métricas de Active Learning

| Métrica | Descripción | Target |
|---------|-------------|--------|
| Error Recurrence Rate | Mismo error en gen N+1 | <10% |
| Fix Application Rate | Fixes aplicados automáticamente | >80% |
| Knowledge Confidence Avg | Confianza promedio de errores | >0.7 |
| Generation Improvement | Mejora en pass rate gen N→N+1 | >15% |

### 7.9 Queries de Monitoreo

```cypher
// Errores más frecuentes (para priorizar fixes)
MATCH (ek:ErrorKnowledge)
RETURN ek.error_type, ek.endpoint_pattern,
       ek.occurrence_count, ek.confidence
ORDER BY ek.occurrence_count DESC
LIMIT 10;

// Efectividad del active learning
MATCH (ek:ErrorKnowledge)
WHERE ek.code_example_good IS NOT NULL
MATCH (p:Pattern)-[:CAUSED_ERROR]->(ek)
MATCH (g:Generation)<-[:PART_OF]-(f:GeneratedFile)<-[:GENERATED]-(p)
WITH ek, g ORDER BY g.timestamp DESC
WITH ek, collect(g)[0..5] as recent_gens
RETURN ek.error_type,
       ek.confidence,
       [g IN recent_gens | g.smoke_pass_rate] as recent_pass_rates;

// Errores que ya no ocurren (learning exitoso)
MATCH (ek:ErrorKnowledge)
WHERE ek.last_seen < datetime() - duration('P7D')
  AND ek.occurrence_count >= 3
RETURN ek.error_type, ek.avoidance_hint, ek.last_seen
ORDER BY ek.last_seen ASC;
```

---

## 8. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Neo4j performance | Media | Indexes, batch ops |
| Data inconsistency | Baja | Transactions, validation |
| Over-fitting | Media | Min usage threshold |
| Complexity creep | Alta | Feature flags, phased rollout |

---

**Documento creado:** 2025-11-29
**Última actualización:** 2025-11-29
**Autor:** DevMatrix AI Pipeline Team
