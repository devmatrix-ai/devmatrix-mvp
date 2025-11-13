# Plan de Refactorización hacia Arquitectura Cognitiva
**DevMatrix MVP - Migración de Wave-Based a Inferencia Cognitiva Pura**

**Autor**: Ariel E. Ghysels
**Fecha**: 2025-11-13
**Estado**: PLAN DEFINITIVO
**Base**: ARBOL_ATOMICO_ZERO_TEMPLATE.md
**Objetivo**: 40% → 92% precisión (MVP) → 99% (con LRM)

---

## Resumen Ejecutivo

### Estado Actual del Sistema
- **Arquitectura**: Wave-based sequential (post-hoc atomization)
- **Precisión actual**: ~40%
- **Problema principal**: Atomización DESPUÉS de generar código de 500+ LOC
- **Cascada de errores**: Error en átomo 1 contamina átomos 2-800
- **Matemática del fracaso**: P(éxito) = 0.95^800 ≈ 0%

### Arquitectura Objetivo
- **100% cognitiva**: Inferencia semántica pura, sin código predefinido
- **Atomización ANTES**: DAG completo ANTES de generar código
- **Precisión MVP**: 92% (4 semanas)
- **Precisión Final**: 99% (6 semanas con LRM)
- **Mantenimiento**: 0% - sistema auto-evolutivo

---

## Análisis de la Implementación Actual

### 1. Componentes Existentes (Reutilizables)

#### 1.1 Base de Datos (✅ Excelente - 95% reutilizable)
```
src/models/
├── atomic_unit.py          ✅ Reutilizar con modificaciones menores
├── masterplan.py           ✅ Reutilizar estructura de fases/milestones
├── conversation.py         ✅ Sin cambios
├── user.py                 ✅ Sin cambios
└── dependency_graph.py     🔄 REFACTORIZAR para Neo4j
```

**Acción**:
- Mantener `AtomicUnit` pero agregar campos:
  - `semantic_signature_hash` (String 64) - Hash de firma semántica
  - `pattern_similarity_score` (Float) - Score de similitud con pattern bank
  - `inference_strategy` (String) - "from_principles" | "adapted_pattern"
- Agregar índice: `idx_semantic_signature_hash`

#### 1.2 LLM Clients (✅ Excelente - 90% reutilizable)
```
src/llm/
├── enhanced_anthropic_client.py    ✅ Base para Claude Opus
├── anthropic_client.py             ✅ Base sólida
├── model_selector.py               🔄 Extender para DeepSeek + o1
└── prompt_cache_manager.py         ✅ Critical - mantener
```

**Acción**:
- Crear `src/llm/deepseek_client.py` (nuevo)
- Crear `src/llm/lrm_client.py` para o1/DeepSeek-R1 (Fase 2)
- Extender `model_selector.py` con `SmartTaskRouter`

#### 1.3 RAG y Vector Store (✅ Perfecto - 100% reutilizable)
```
src/rag/
├── vector_store.py                 ✅ Base perfecta para Pattern Bank
├── embeddings.py                   ✅ Sentence Transformers ready
├── retriever.py                    ✅ Hybrid retrieval listo
├── cross_encoder_reranker.py       ✅ Para reranking de patterns
└── hybrid_retriever.py             ✅ Excelente para Pattern Bank
```

**Acción**:
- **Mantener 100%** - es exactamente lo que necesitamos
- Crear colección nueva: `cognitive_patterns` en Qdrant
- Usar `embeddings.py` para generar embeddings de STS
- `retriever.py` será base para `PatternBankMVP.find_similar()`

#### 1.4 Observability y Tracing (✅ Excelente - 100% reutilizable)
```
src/observability/
├── metrics_collector.py            ✅ MLflow integration
├── structured_logger.py            ✅ Logging estructurado
└── tracer.py                       ✅ Distributed tracing
```

**Acción**: Mantener sin cambios, agregar métricas nuevas:
- `pattern_reuse_rate`
- `semantic_similarity_avg`
- `cognitive_inference_time`

#### 1.5 API y WebSocket (✅ 100% reutilizable)
```
src/api/                            ✅ Mantener endpoints actuales
src/websocket/                      ✅ Real-time updates funcionan
```

**Acción**: Mantener sin cambios, solo agregar nuevos eventos de progreso.

---

### 2. Componentes a ELIMINAR (❌ Sistema Viejo)

#### 2.1 Wave Executor (❌ ELIMINAR)
```
src/execution/wave_executor.py     ❌ Lógica wave-based obsoleta
```
**Por qué**: Ejecuta átomos en waves POST generación. Arquitectura cognitiva ejecuta nivel por nivel en DAG ANTES.

#### 2.2 Atomization Post-Hoc (❌ ELIMINAR)
```
src/atomization/                    ❌ Atomiza DESPUÉS de generar
```
**Por qué**: Atomización debe ser ANTES, parte del Multi-Pass Planning.

#### 2.3 Masterplan Generator Actual (🔄 REEMPLAZAR COMPLETO)
```
src/services/masterplan_generator.py   🔄 Monolítico, sin multi-pass
```
**Por qué**: Genera 120 tasks en 1 llamada. Nueva arquitectura: 6 pasadas + DAG.

---

### 3. Componentes a REFACTORIZAR (🔄)

#### 3.1 Orchestrator Agent (🔄 REFACTORIZAR PROFUNDO)
**Archivo**: `src/agents/orchestrator_agent.py`

**Problemas actuales**:
- LangGraph state machine (innecesario para MVP)
- Task decomposition simple (sin multi-pass)
- No tiene concepto de semantic signatures
- No usa co-reasoning Claude+DeepSeek

**Refactorización**:
```python
# ANTES (LangGraph)
class OrchestratorAgent:
    def __init__(self):
        self.graph = StateGraph(OrchestratorState)
        # ... complejo

# DESPUÉS (Simple async orchestration)
class OrchestratorMVP:
    def __init__(self):
        self.planner = MultiPassPlanningMVP()
        self.cpie = CognitivePatternInferenceEngine()
        self.pattern_bank = PatternBankMVP()
        self.validator = EnsembleValidator()
        self.co_reasoning = CoReasoningSystem()
```

**Migración**:
- Mantener interfaz externa (API calls)
- Reemplazar internals completamente
- Migrar gradualmente: agregar `orchestrate_cognitive()` nuevo método

---

## Plan de Implementación Detallado

### FASE 0: Preparación (3 días)

#### Día 1: Setup y Branch
```bash
# 1. Crear branch
git checkout -b feature/cognitive-architecture-mvp

# 2. Crear estructura de directorios
mkdir -p src/cognitive/{signatures,inference,patterns,planning,validation,co_reasoning}

# 3. Instalar dependencias nuevas
pip install faiss-cpu sentence-transformers neo4j
```

**Deliverables**:
- ✅ Branch creado
- ✅ Directorios creados
- ✅ Dependencies instaladas

#### Día 2: Database Migrations
```bash
# Crear migrations para nuevos campos
alembic revision -m "Add cognitive architecture fields to atomic_unit"
alembic upgrade head
```

**Cambios en DB**:
```python
# alembic/versions/XXX_add_cognitive_fields.py
def upgrade():
    op.add_column('atomic_units', sa.Column('semantic_signature_hash', sa.String(64)))
    op.add_column('atomic_units', sa.Column('pattern_similarity_score', sa.Float))
    op.add_column('atomic_units', sa.Column('inference_strategy', sa.String(50)))
    op.create_index('idx_semantic_signature_hash', 'atomic_units', ['semantic_signature_hash'])
```

**Deliverables**:
- ✅ Migration creada y aplicada
- ✅ DB schema actualizado

#### Día 3: Neo4j Setup
```yaml
# docker-compose.yml - Agregar Neo4j
services:
  neo4j:
    image: neo4j:5.13
    ports:
      - "7474:7474"  # Web UI
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/devmatrix2024
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

**Deliverables**:
- ✅ Neo4j running en Docker
- ✅ Conexión verificada
- ✅ Primera query de prueba ejecutada

---

### FASE 1: Core Components MVP (Semana 1)

#### Día 1-2: Semantic Task Signatures

**Archivo**: `src/cognitive/signatures/semantic_signature.py`

```python
"""
Semantic Task Signature - Captura ESENCIA de tareas atómicas
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import hashlib
import json

@dataclass
class SemanticTaskSignature:
    """
    Firma semántica de una tarea atómica
    Define QUÉ hacer sin especificar CÓMO
    """
    # Identificación
    purpose: str  # Propósito normalizado
    intent: str   # Intención extraída

    # I/O normalizado
    inputs: Dict[str, str]  # {param_name: type}
    outputs: Dict[str, str]  # {return_name: type}

    # Contexto
    domain: str  # "auth", "crud", "api", etc.
    constraints: List[str]  # ["max_10_loc", "async", etc.]

    # Calidad
    security_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    performance_tier: str  # "LOW", "MEDIUM", "HIGH"
    idempotency: bool  # ¿Es idempotente?

    # Hash único
    semantic_hash: str = ""

    def __post_init__(self):
        if not self.semantic_hash:
            self.semantic_hash = self.compute_semantic_hash()

    def compute_semantic_hash(self) -> str:
        """Hash único basado en propiedades semánticas"""
        data = {
            'purpose': self.purpose,
            'inputs': sorted(self.inputs.items()),
            'outputs': sorted(self.outputs.items()),
            'security': self.security_level,
            'performance': self.performance_tier
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def similarity_score(self, other: 'SemanticTaskSignature') -> float:
        """
        Calcula similitud semántica con otra firma
        Returns: 0.0 a 1.0
        """
        scores = []

        # Similitud de propósito (40% peso)
        purpose_sim = self._text_similarity(self.purpose, other.purpose)
        scores.append(purpose_sim * 0.4)

        # Similitud de I/O (30% peso)
        io_sim = self._io_similarity(other)
        scores.append(io_sim * 0.3)

        # Similitud de dominio (20% peso)
        domain_sim = 1.0 if self.domain == other.domain else 0.5
        scores.append(domain_sim * 0.2)

        # Similitud de constraints (10% peso)
        constraint_sim = self._constraint_similarity(other)
        scores.append(constraint_sim * 0.1)

        return sum(scores)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple Jaccard similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _io_similarity(self, other: 'SemanticTaskSignature') -> float:
        """Similitud de inputs/outputs"""
        input_keys_sim = len(set(self.inputs.keys()) & set(other.inputs.keys())) / max(len(self.inputs), len(other.inputs), 1)
        output_keys_sim = len(set(self.outputs.keys()) & set(other.outputs.keys())) / max(len(self.outputs), len(other.outputs), 1)
        return (input_keys_sim + output_keys_sim) / 2

    def _constraint_similarity(self, other: 'SemanticTaskSignature') -> float:
        """Similitud de constraints"""
        if not self.constraints or not other.constraints:
            return 0.5
        common = len(set(self.constraints) & set(other.constraints))
        total = len(set(self.constraints) | set(other.constraints))
        return common / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        """Serialización para DB"""
        return asdict(self)

    @classmethod
    def from_atomic_task(cls, atom: 'AtomicUnit') -> 'SemanticTaskSignature':
        """
        Crea STS desde AtomicUnit del sistema actual
        """
        return cls(
            purpose=cls._normalize_purpose(atom.description),
            intent=cls._extract_intent(atom.name),
            inputs=cls._parse_inputs(atom.description),
            outputs=cls._parse_outputs(atom.description),
            domain=cls._infer_domain(atom),
            constraints=cls._extract_constraints(atom),
            security_level=cls._infer_security(atom),
            performance_tier=cls._infer_performance(atom),
            idempotency=cls._check_idempotency(atom)
        )

    @staticmethod
    def _normalize_purpose(description: str) -> str:
        """Normaliza descripción a propósito claro"""
        # Eliminar ruido, estandarizar verbos, etc.
        return description.strip().lower()

    @staticmethod
    def _extract_intent(name: str) -> str:
        """Extrae intención de nombre de tarea"""
        # "Create User model" -> "create"
        # "Validate email" -> "validate"
        verbs = ["create", "update", "delete", "validate", "authenticate", "generate"]
        name_lower = name.lower()
        for verb in verbs:
            if verb in name_lower:
                return verb
        return "process"

    # ... más métodos estáticos para inferencia
```

**Tests**:
```python
# tests/cognitive/test_semantic_signature.py
def test_semantic_signature_hash_consistency():
    atom = AtomicUnit(...)
    sts1 = SemanticTaskSignature.from_atomic_task(atom)
    sts2 = SemanticTaskSignature.from_atomic_task(atom)
    assert sts1.semantic_hash == sts2.semantic_hash

def test_similarity_score_identical():
    sts = SemanticTaskSignature(...)
    assert sts.similarity_score(sts) == 1.0

def test_similarity_score_different_domain():
    sts1 = SemanticTaskSignature(domain="auth", ...)
    sts2 = SemanticTaskSignature(domain="crud", ...)
    assert sts1.similarity_score(sts2) < 0.7
```

**Deliverables**:
- ✅ `semantic_signature.py` implementado
- ✅ 15+ unit tests passing
- ✅ Coverage > 90%

---

#### Día 3-4: Pattern Bank MVP

**Archivo**: `src/cognitive/patterns/pattern_bank.py`

```python
"""
Pattern Bank MVP - Almacena y recupera patrones cognitivos exitosos
"""
from typing import List, Dict, Optional
from uuid import uuid4
from sentence_transformers import SentenceTransformer

from src.rag import create_vector_store, create_embedding_model
from src.cognitive.signatures import SemanticTaskSignature
from src.observability import get_logger

logger = get_logger("pattern_bank")


class PatternBankMVP:
    """
    Banco de patrones auto-evolutivo
    - Almacena patrones exitosos (precision >= 0.95)
    - Búsqueda por similitud semántica
    - Tracking de usage y success rate
    """

    def __init__(
        self,
        vector_store=None,
        embedder=None,
        collection_name: str = "cognitive_patterns",
        success_threshold: float = 0.95
    ):
        """
        Initialize Pattern Bank

        Args:
            vector_store: Qdrant vector store (if None, creates default)
            embedder: Sentence transformer (if None, creates default)
            collection_name: Qdrant collection name
            success_threshold: Minimum precision to store pattern
        """
        self.vector_store = vector_store or create_vector_store()
        self.embedder = embedder or create_embedding_model()
        self.collection_name = collection_name
        self.success_threshold = success_threshold

        # In-memory cache (UUID -> pattern metadata)
        self.patterns: Dict[str, Dict] = {}

        # Ensure collection exists
        self._initialize_collection()

    def _initialize_collection(self):
        """Create Qdrant collection if not exists"""
        # Use existing RAG infrastructure
        self.vector_store.create_collection_if_not_exists(
            collection_name=self.collection_name,
            vector_size=768  # Sentence-transformers dimension
        )

    async def store_success(
        self,
        signature: SemanticTaskSignature,
        code: str,
        metrics: Dict
    ) -> Optional[str]:
        """
        Almacena patrón exitoso en Pattern Bank

        Args:
            signature: Firma semántica del átomo
            code: Código generado exitosamente
            metrics: Métricas de validación {precision, execution_time, ...}

        Returns:
            pattern_id si se almacenó, None si no cumple threshold
        """
        precision = metrics.get('precision', 0.0)

        if precision < self.success_threshold:
            logger.debug(
                f"Pattern not stored (precision {precision:.2f} < {self.success_threshold})",
                extra={'signature_hash': signature.semantic_hash}
            )
            return None

        # Crear embedding semántico
        text = f"{signature.purpose}\n{code}"
        embedding = self.embedder.encode(text).tolist()

        # Generar pattern_id
        pattern_id = str(uuid4())

        # Metadata para búsqueda y tracking
        metadata = {
            'pattern_id': pattern_id,
            'signature': signature.to_dict(),
            'code': code,
            'metrics': metrics,
            'usage_count': 0,
            'success_rate': 1.0,
            'domain': signature.domain,
            'security_level': signature.security_level,
            'created_at': metrics.get('timestamp', 'unknown')
        }

        # Almacenar en Qdrant
        self.vector_store.upsert(
            collection_name=self.collection_name,
            points=[{
                'id': pattern_id,
                'vector': embedding,
                'payload': metadata
            }]
        )

        # Cache en memoria
        self.patterns[pattern_id] = metadata

        logger.info(
            f"Pattern stored successfully",
            extra={
                'pattern_id': pattern_id,
                'precision': precision,
                'domain': signature.domain
            }
        )

        return pattern_id

    async def find_similar(
        self,
        signature: SemanticTaskSignature,
        threshold: float = 0.85,
        limit: int = 5
    ) -> List[Dict]:
        """
        Busca patrones similares semánticamente

        Args:
            signature: Firma semántica a buscar
            threshold: Similitud mínima (0-1)
            limit: Número máximo de resultados

        Returns:
            Lista de patrones ordenados por similitud
        """
        # Query embedding
        query_text = signature.purpose
        query_embedding = self.embedder.encode(query_text).tolist()

        # Search en Qdrant
        results = self.vector_store.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit * 2,  # Traer más para filtrar por threshold
            score_threshold=threshold
        )

        # Filtrar y enriquecer con similarity score
        similar_patterns = []
        for result in results:
            pattern = result.payload
            pattern['similarity_score'] = result.score

            # Calcular también similitud estructural (STS-based)
            stored_sts = SemanticTaskSignature(**pattern['signature'])
            structural_sim = signature.similarity_score(stored_sts)
            pattern['structural_similarity'] = structural_sim

            # Combinar scores (70% vector, 30% structural)
            combined_score = (result.score * 0.7) + (structural_sim * 0.3)
            pattern['combined_score'] = combined_score

            if combined_score >= threshold:
                similar_patterns.append(pattern)

        # Ordenar por combined_score
        similar_patterns.sort(key=lambda x: x['combined_score'], reverse=True)

        logger.info(
            f"Found {len(similar_patterns)} similar patterns",
            extra={
                'threshold': threshold,
                'query_domain': signature.domain,
                'top_score': similar_patterns[0]['combined_score'] if similar_patterns else 0
            }
        )

        return similar_patterns[:limit]

    async def update_usage(self, pattern_id: str, success: bool):
        """
        Actualiza estadísticas de uso de un patrón

        Args:
            pattern_id: UUID del patrón
            success: Si el uso fue exitoso
        """
        if pattern_id not in self.patterns:
            # Cargar de Qdrant si no está en cache
            pattern = self.vector_store.retrieve(
                collection_name=self.collection_name,
                ids=[pattern_id]
            )[0]
            self.patterns[pattern_id] = pattern.payload

        pattern = self.patterns[pattern_id]
        pattern['usage_count'] += 1

        # Actualizar success_rate con moving average
        current_rate = pattern['success_rate']
        new_rate = (current_rate * (pattern['usage_count'] - 1) + (1.0 if success else 0.0)) / pattern['usage_count']
        pattern['success_rate'] = new_rate

        # Persist en Qdrant
        self.vector_store.upsert(
            collection_name=self.collection_name,
            points=[{
                'id': pattern_id,
                'vector': pattern['vector'],  # No cambia
                'payload': pattern
            }]
        )

    def get_stats(self) -> Dict:
        """Estadísticas del Pattern Bank"""
        return {
            'total_patterns': len(self.patterns),
            'avg_success_rate': sum(p['success_rate'] for p in self.patterns.values()) / len(self.patterns) if self.patterns else 0,
            'total_usage': sum(p['usage_count'] for p in self.patterns.values()),
            'domains': list(set(p['domain'] for p in self.patterns.values()))
        }
```

**Tests**:
```python
# tests/cognitive/test_pattern_bank.py
@pytest.mark.asyncio
async def test_store_high_precision_pattern():
    bank = PatternBankMVP()
    signature = SemanticTaskSignature(...)
    code = "def foo(): pass"
    metrics = {'precision': 0.98}

    pattern_id = await bank.store_success(signature, code, metrics)
    assert pattern_id is not None

@pytest.mark.asyncio
async def test_dont_store_low_precision():
    bank = PatternBankMVP()
    metrics = {'precision': 0.85}

    pattern_id = await bank.store_success(signature, code, metrics)
    assert pattern_id is None

@pytest.mark.asyncio
async def test_find_similar_returns_ordered():
    bank = PatternBankMVP()
    # Store 3 patterns
    # ...

    results = await bank.find_similar(query_signature, threshold=0.8)
    assert len(results) > 0
    assert results[0]['combined_score'] >= results[-1]['combined_score']
```

**Deliverables**:
- ✅ `pattern_bank.py` implementado
- ✅ Integración con Qdrant funcionando
- ✅ 12+ tests passing
- ✅ Métricas de stats verificadas

---

#### Día 5: Cognitive Pattern Inference Engine (CPIE)

**Archivo**: `src/cognitive/inference/cpie.py`

```python
"""
Cognitive Pattern Inference Engine (CPIE)
Motor de inferencia cognitiva que razona sobre implementaciones
"""
from typing import Dict, Optional

from src.llm import EnhancedAnthropicClient
from src.cognitive.signatures import SemanticTaskSignature
from src.cognitive.patterns import PatternBankMVP
from src.observability import get_logger

logger = get_logger("cpie")


class CognitivePatternInferenceEngine:
    """
    Motor de inferencia cognitiva
    - NO usa templates
    - Razona desde primeros principios
    - Adapta patrones mediante razonamiento
    """

    def __init__(
        self,
        pattern_bank: PatternBankMVP,
        claude_client: Optional[EnhancedAnthropicClient] = None,
        deepseek_client=None  # TODO: Fase 1
    ):
        self.pattern_bank = pattern_bank
        self.claude = claude_client or EnhancedAnthropicClient()
        self.deepseek = deepseek_client  # MVP usa solo Claude

    async def infer_implementation(
        self,
        signature: SemanticTaskSignature,
        context: Dict
    ) -> str:
        """
        Infiere implementación óptima para firma semántica

        Args:
            signature: Firma semántica del átomo
            context: Contexto enriquecido {dependencies, stack, patterns, ...}

        Returns:
            Código generado (max 10 LOC)
        """
        logger.info(
            "Starting cognitive inference",
            extra={
                'purpose': signature.purpose[:50],
                'domain': signature.domain
            }
        )

        # 1. Buscar patrones similares
        similar_patterns = await self.pattern_bank.find_similar(
            signature,
            threshold=0.85
        )

        if similar_patterns:
            # Adaptar patrón existente mediante razonamiento
            logger.info(
                "Adapting existing pattern",
                extra={'pattern_similarity': similar_patterns[0]['combined_score']}
            )
            code = await self._adapt_via_reasoning(
                similar_patterns[0],
                signature,
                context
            )
        else:
            # Generar desde primeros principios
            logger.info("Generating from first principles")
            code = await self._generate_from_principles(
                signature,
                context
            )

        return code

    async def _adapt_via_reasoning(
        self,
        pattern: Dict,
        signature: SemanticTaskSignature,
        context: Dict
    ) -> str:
        """
        Adapta patrón existente mediante razonamiento cognitivo
        """
        prompt = f"""Tienes un patrón exitoso previo que es similar a esta nueva tarea.

**Patrón Previo** (similitud: {pattern['combined_score']:.2f}):
```python
{pattern['code']}
```

**Nueva Tarea**:
- Propósito: {signature.purpose}
- Inputs: {signature.inputs}
- Outputs: {signature.outputs}
- Constraints: {signature.constraints}
- Security: {signature.security_level}

**Contexto Disponible**:
- Stack: {context.get('stack', 'Python')}
- Dependencias: {context.get('dependencies', [])}

**Instrucciones**:
1. Analiza las diferencias entre el patrón previo y la nueva tarea
2. Razona sobre qué adaptaciones son necesarias
3. Genera código adaptado que:
   - Cumpla EXACTAMENTE el nuevo propósito
   - Máximo 10 líneas de código
   - Mantenga la calidad del patrón original
   - Sea sintácticamente perfecto

Retorna SOLO el código Python, sin explicaciones."""

        response = await self.claude.generate(
            prompt=prompt,
            temperature=0.1,  # Baja variabilidad en adaptación
            max_tokens=800
        )

        return self._extract_code(response)

    async def _generate_from_principles(
        self,
        signature: SemanticTaskSignature,
        context: Dict
    ) -> str:
        """
        Genera código razonando desde primeros principios
        """
        prompt = f"""Genera código Python para esta tarea desde primeros principios.

**Tarea**:
- Propósito: {signature.purpose}
- Inputs: {signature.inputs}
- Outputs: {signature.outputs}
- Domain: {signature.domain}
- Constraints: {signature.constraints}
- Security Level: {signature.security_level}
- Performance Tier: {signature.performance_tier}

**Contexto**:
- Stack: {context.get('stack', 'Python + FastAPI')}
- Dependencias disponibles: {context.get('dependencies', [])}
- Patrones del proyecto: {context.get('project_patterns', [])}

**Requisitos**:
1. Máximo 10 líneas de código
2. Una sola responsabilidad
3. Sin efectos secundarios globales
4. Imports al inicio
5. Type hints completos
6. Sintácticamente perfecto

**Razonamiento**:
1. Analiza el propósito exacto
2. Diseña el algoritmo óptimo
3. Implementa con clean code
4. Considera edge cases

Retorna SOLO el código Python, sin explicaciones."""

        response = await self.claude.generate(
            prompt=prompt,
            temperature=0.2,  # Un poco más de creatividad
            max_tokens=800
        )

        return self._extract_code(response)

    def _extract_code(self, response: str) -> str:
        """Extrae código de respuesta LLM"""
        import re

        # Buscar código entre ```python ``` o ``` ```
        patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Si no hay bloques de código, asumir que todo es código
        return response.strip()
```

**Tests**:
```python
# tests/cognitive/test_cpie.py
@pytest.mark.asyncio
async def test_infer_from_principles():
    cpie = CognitivePatternInferenceEngine(pattern_bank=mock_bank)
    signature = SemanticTaskSignature(
        purpose="validate email format",
        inputs={'email': 'str'},
        outputs={'is_valid': 'bool'},
        ...
    )
    context = {'stack': 'Python'}

    code = await cpie.infer_implementation(signature, context)
    assert len(code.split('\n')) <= 10
    assert 'def ' in code or 'class ' in code

@pytest.mark.asyncio
async def test_adapt_existing_pattern():
    # Mock pattern_bank to return similar pattern
    mock_bank.find_similar = AsyncMock(return_value=[{
        'code': 'def validate_email(email): ...',
        'combined_score': 0.92
    }])

    cpie = CognitivePatternInferenceEngine(pattern_bank=mock_bank)
    code = await cpie.infer_implementation(signature, context)

    assert 'validate' in code.lower()
```

**Deliverables**:
- ✅ `cpie.py` implementado
- ✅ Integración con Pattern Bank
- ✅ 10+ tests passing
- ✅ Generación verificada < 10 LOC

---

---

### FASE 1: Semana 2 - Multi-Pass Planning + DAG Builder

#### Día 6-7: Multi-Pass Planning MVP

**Archivo**: `src/cognitive/planning/multi_pass_planner.py`

```python
"""
Multi-Pass Planning MVP
Sistema de planning con 6 pasadas de refinamiento progresivo
"""
from typing import Dict, List
from dataclasses import dataclass

from src.llm import EnhancedAnthropicClient
from src.cognitive.signatures import SemanticTaskSignature
from src.observability import get_logger

logger = get_logger("multi_pass_planner")


@dataclass
class AtomicTask:
    """Tarea atómica para ejecución"""
    id: str
    name: str
    purpose: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    dependencies: List[str]
    estimated_loc: int = 10
    complexity: float = 0.5


class MultiPassPlanningMVP:
    """
    Sistema de planning con 6 pasadas:
    1. Requirements Analysis
    2. Architecture Design
    3. Contract Definition
    4. Integration Points
    5. Atomic Task Breakdown
    6. Validation & Optimization
    """

    def __init__(self, claude_client=None):
        self.claude = claude_client or EnhancedAnthropicClient()

    async def generate_masterplan(self, requirements: str) -> 'DAG':
        """
        Genera masterplan completo mediante 6 pasadas

        Args:
            requirements: User requirements (natural language)

        Returns:
            DAG con tareas atómicas listas para ejecutar
        """
        logger.info("Starting multi-pass planning", extra={'req_length': len(requirements)})

        # Pass 1: Requirements Analysis
        print("🔍 Pass 1: Analyzing requirements...")
        analyzed_reqs = await self._pass1_requirements_analysis(requirements)

        # Pass 2: Architecture Design
        print("🏗️ Pass 2: Designing architecture...")
        architecture = await self._pass2_architecture_design(analyzed_reqs)

        # Pass 3: Contract Definition
        print("📝 Pass 3: Defining contracts...")
        contracts = await self._pass3_contract_definition(architecture)

        # Pass 4: Integration Points
        print("🔗 Pass 4: Identifying integrations...")
        integrations = await self._pass4_integration_points(contracts)

        # Pass 5: Atomic Task Breakdown
        print("⚛️ Pass 5: Breaking down to atomic tasks...")
        atomic_tasks = await self._pass5_atomic_breakdown(integrations)

        # Pass 6: Validation & Optimization
        print("✅ Pass 6: Validating and optimizing...")
        validated_tasks = await self._pass6_validation(atomic_tasks)

        # Construir DAG (próximo paso)
        from src.cognitive.planning import DAGBuilder
        dag_builder = DAGBuilder()
        dag = await dag_builder.build_dag(validated_tasks)

        logger.info(f"Masterplan generated: {len(dag.nodes)} atomic tasks")
        return dag

    async def _pass1_requirements_analysis(self, requirements: str) -> Dict:
        """Pass 1: Extrae y estructura requerimientos"""
        prompt = f"""Analiza estos requerimientos y extrae información estructurada.

Requerimientos:
{requirements}

Extrae:
1. **Entidades principales**: Modelos de dominio clave
2. **Casos de uso críticos**: Flujos principales
3. **Requisitos no funcionales**: Performance, seguridad, etc.
4. **Restricciones técnicas**: Stack obligatorio, integraciones
5. **Criterios de éxito**: ¿Qué define "hecho"?

Retorna JSON estructurado:
```json
{{
  "entities": ["User", "Product", ...],
  "use_cases": ["User registration", "Product search", ...],
  "non_functional": {{"performance": "...", "security": "..."}},
  "technical_constraints": ["Python 3.12", "PostgreSQL", ...],
  "success_criteria": ["All CRUD working", "< 200ms response", ...]
}}
```
"""
        response = await self.claude.generate(prompt, temperature=0.1, max_tokens=2000)
        return self._parse_json_response(response)

    async def _pass2_architecture_design(self, analyzed_reqs: Dict) -> Dict:
        """Pass 2: Diseña arquitectura de alto nivel"""
        prompt = f"""Diseña arquitectura de alto nivel basada en estos requerimientos.

Requerimientos Analizados:
{analyzed_reqs}

Diseña:
1. **Módulos principales**: Separación lógica
2. **Patrones arquitectónicos**: MVC, DDD, CQRS, etc.
3. **Separación de responsabilidades**: Capas y boundaries
4. **Flujo de datos**: Cómo fluye información entre módulos
5. **Interfaces entre módulos**: Contratos entre componentes

Retorna JSON:
```json
{{
  "modules": [
    {{"name": "auth", "responsibility": "Authentication & Authorization"}},
    ...
  ],
  "patterns": ["Repository Pattern", "Service Layer", ...],
  "layers": ["API", "Service", "Repository", "Model"],
  "data_flow": "Request → API → Service → Repository → DB",
  "interfaces": [
    {{"from": "api", "to": "service", "contract": "UserService"}}
  ]
}}
```
"""
        response = await self.claude.generate(prompt, temperature=0.1, max_tokens=2500)
        return self._parse_json_response(response)

    async def _pass3_contract_definition(self, architecture: Dict) -> Dict:
        """Pass 3: Define contratos precisos e interfaces"""
        prompt = f"""Define contratos precisos para esta arquitectura.

Arquitectura:
{architecture}

Define para cada módulo:
1. **APIs y endpoints**: Rutas, métodos HTTP, auth
2. **Modelos de datos**: Schemas con tipos exactos
3. **Esquemas de validación**: Pydantic, etc.
4. **Formatos de mensajes**: Request/Response shapes
5. **Protocolos de comunicación**: REST, WebSocket, etc.

Retorna JSON con especificación completa:
```json
{{
  "endpoints": [
    {{
      "path": "/api/v1/users",
      "method": "POST",
      "request_schema": {{"email": "str", "password": "str"}},
      "response_schema": {{"id": "UUID", "email": "str", "created_at": "datetime"}},
      "auth_required": true
    }}
  ],
  "models": [
    {{
      "name": "User",
      "fields": {{"id": "UUID", "email": "str", "password_hash": "str"}},
      "relationships": []
    }}
  ],
  "validation_rules": [...]
}}
```
"""
        response = await self.claude.generate(prompt, temperature=0.0, max_tokens=3000)
        return self._parse_json_response(response)

    async def _pass4_integration_points(self, contracts: Dict) -> Dict:
        """Pass 4: Identifica puntos de integración y dependencias"""
        prompt = f"""Analiza puntos de integración entre módulos.

Contratos Definidos:
{contracts}

Identifica:
1. **Puntos de integración**: Dónde se conectan módulos
2. **Dependencias de datos**: Qué necesita qué
3. **Orden de ejecución**: Qué debe crearse primero
4. **Cuellos de botella**: Dependencias que bloquean
5. **Paralelización**: Qué puede ejecutarse en paralelo

Retorna análisis estructurado:
```json
{{
  "integration_points": [
    {{"from": "UserAPI", "to": "UserService", "type": "sync_call"}},
    ...
  ],
  "data_dependencies": [
    {{"task": "CreateUser", "depends_on": ["UserModel", "Database"]}},
    ...
  ],
  "execution_order": ["Setup DB", "Create Models", "Create Services", ...],
  "bottlenecks": ["Database setup blocks all", ...],
  "parallel_groups": [
    ["CreateUserModel", "CreateProductModel"],
    ...
  ]
}}
```
"""
        response = await self.claude.generate(prompt, temperature=0.1, max_tokens=2500)
        return self._parse_json_response(response)

    async def _pass5_atomic_breakdown(self, integrations: Dict) -> List[AtomicTask]:
        """Pass 5: Descompone en tareas atómicas de máximo 10 LOC"""
        prompt = f"""Descompone en tareas ULTRA-ATÓMICAS.

Integrations & Dependencies:
{integrations}

**CRITICAL**: Cada tarea debe ser:
1. **Máximo 10 líneas de código**
2. **Una sola responsabilidad**
3. **Inputs/outputs claramente definidos**
4. **Dependencias explícitas** (IDs de otras tareas)
5. **Completamente testeable** en aislamiento

**Formato de cada tarea**:
```json
{{
  "id": "task_001",
  "name": "Create User SQLAlchemy model",
  "purpose": "Define User model in src/models/user.py with id, email, password_hash fields",
  "inputs": {{}},
  "outputs": {{"model_class": "User"}},
  "dependencies": [],
  "estimated_loc": 8,
  "complexity": 0.3,
  "file_path": "src/models/user.py"
}}
```

Retorna array de 50-120 tareas atómicas.
"""
        response = await self.claude.generate(prompt, temperature=0.0, max_tokens=8000)
        tasks_data = self._parse_json_response(response)

        # Convertir a objetos AtomicTask
        atomic_tasks = []
        for task_data in tasks_data:
            atomic_tasks.append(AtomicTask(**task_data))

        logger.info(f"Generated {len(atomic_tasks)} atomic tasks")
        return atomic_tasks

    async def _pass6_validation(self, atomic_tasks: List[AtomicTask]) -> List[AtomicTask]:
        """Pass 6: Valida consistencia y optimiza"""
        logger.info("Validating atomic tasks...")

        # 1. Verificar que todas las dependencias existen
        task_ids = {task.id for task in atomic_tasks}
        for task in atomic_tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Dependency not found: {dep} in task {task.id}")

        # 2. Verificar que no hay ciclos (se hará en DAG Builder)

        # 3. Optimizar: eliminar dependencias redundantes transitivas
        for task in atomic_tasks:
            task.dependencies = self._minimize_dependencies(task, atomic_tasks)

        # 4. Verificar que todos los tasks tienen LOC <= 10
        for task in atomic_tasks:
            if task.estimated_loc > 10:
                logger.warning(f"Task {task.id} exceeds 10 LOC: {task.estimated_loc}")

        logger.info(f"Validation complete: {len(atomic_tasks)} tasks validated")
        return atomic_tasks

    def _minimize_dependencies(self, task: AtomicTask, all_tasks: List[AtomicTask]) -> List[str]:
        """Elimina dependencias transitivas redundantes"""
        # TODO: Implementar algoritmo de reducción transitiva
        return task.dependencies

    def _parse_json_response(self, response: str) -> Dict:
        """Parsea respuesta JSON de LLM"""
        import json
        import re

        # Buscar JSON en respuesta
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Asumir que toda la respuesta es JSON
            json_str = response

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}", extra={'response': response[:200]})
            raise
```

**Deliverables Día 6-7**:
- ✅ `multi_pass_planner.py` implementado
- ✅ 6 pasadas funcionando end-to-end
- ✅ Validación de tasks completa
- ✅ Tests de integración passing

---

#### Día 8-9: DAG Builder con Neo4j

**Archivo**: `src/cognitive/planning/dag_builder.py`

```python
"""
DAG Builder con Neo4j
Constructor de grafo de dependencias con detección de ciclos y niveles topológicos
"""
from typing import List, Dict
from neo4j import AsyncGraphDatabase

from src.cognitive.planning import AtomicTask
from src.observability import get_logger

logger = get_logger("dag_builder")


class DAG:
    """
    Directed Acyclic Graph de tareas atómicas
    """

    def __init__(self, nodes: List[AtomicTask], levels: Dict[int, List[str]]):
        self.nodes = {node.id: node for node in nodes}
        self.levels = levels  # {0: [task_ids_level_0], 1: [...], ...}

    def get_topological_levels(self) -> List[List[AtomicTask]]:
        """Retorna tareas agrupadas por nivel para ejecución paralela"""
        result = []
        for level_num in sorted(self.levels.keys()):
            level_tasks = [self.nodes[task_id] for task_id in self.levels[level_num]]
            result.append(level_tasks)
        return result

    def get_dependencies(self, task_id: str) -> List[AtomicTask]:
        """Obtiene dependencias de una tarea"""
        task = self.nodes[task_id]
        return [self.nodes[dep_id] for dep_id in task.dependencies]


class DAGBuilder:
    """
    Constructor de DAG con Neo4j
    - Crea nodos y relaciones
    - Detecta ciclos
    - Calcula niveles topológicos para paralelización
    """

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "devmatrix2024"):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def build_dag(self, atomic_tasks: List[AtomicTask]) -> DAG:
        """
        Construye DAG completo

        Args:
            atomic_tasks: Lista de tareas atómicas con dependencias

        Returns:
            DAG validado y optimizado

        Raises:
            ValueError: Si hay ciclos en el grafo
        """
        logger.info(f"Building DAG with {len(atomic_tasks)} tasks")

        async with self.driver.session() as session:
            # 1. Limpiar grafo anterior
            await session.run("MATCH (n:AtomicTask) DETACH DELETE n")

            # 2. Crear nodos
            for task in atomic_tasks:
                await session.run("""
                    CREATE (t:AtomicTask {
                        id: $id,
                        name: $name,
                        purpose: $purpose,
                        loc: $loc,
                        complexity: $complexity
                    })
                """, {
                    'id': task.id,
                    'name': task.name,
                    'purpose': task.purpose,
                    'loc': task.estimated_loc,
                    'complexity': task.complexity
                })

            # 3. Crear relaciones de dependencia
            for task in atomic_tasks:
                for dep_id in task.dependencies:
                    await session.run("""
                        MATCH (t1:AtomicTask {id: $from_id})
                        MATCH (t2:AtomicTask {id: $to_id})
                        CREATE (t1)-[:DEPENDS_ON]->(t2)
                    """, {
                        'from_id': task.id,
                        'to_id': dep_id
                    })

            # 4. Detectar ciclos
            cycles_result = await session.run("""
                MATCH (t:AtomicTask)-[r:DEPENDS_ON*]->(t)
                RETURN t.id as cycle_node
                LIMIT 1
            """)
            cycle_records = [record async for record in cycles_result]
            if cycle_records:
                cycle_node = cycle_records[0]['cycle_node']
                raise ValueError(f"DAG contains cycles involving task: {cycle_node}")

            # 5. Calcular niveles topológicos
            levels = await self._calculate_topological_levels(session, atomic_tasks)

        logger.info(f"DAG built successfully: {len(levels)} levels")
        return DAG(nodes=atomic_tasks, levels=levels)

    async def _calculate_topological_levels(self, session, tasks: List[AtomicTask]) -> Dict[int, List[str]]:
        """
        Calcula niveles topológicos para ejecución paralela
        Nivel 0: tareas sin dependencias
        Nivel N: tareas cuyas dependencias están en niveles < N
        """
        # Nivel 0: nodos sin dependencias
        result = await session.run("""
            MATCH (t:AtomicTask)
            WHERE NOT (t)-[:DEPENDS_ON]->()
            RETURN t.id as node_id
        """)
        level_0 = [record['node_id'] async for record in result]

        levels = {0: level_0}
        visited = set(level_0)
        current_level = 0

        # Iterar hasta procesar todos los nodos
        while len(visited) < len(tasks):
            current_level += 1

            # Encontrar nodos cuyas dependencias ya fueron procesadas
            result = await session.run("""
                MATCH (t:AtomicTask)-[:DEPENDS_ON]->(dep:AtomicTask)
                WHERE dep.id IN $visited
                WITH t, collect(dep.id) as processed_deps
                MATCH (t)-[:DEPENDS_ON]->(all_deps:AtomicTask)
                WITH t, processed_deps, collect(all_deps.id) as all_dependencies
                WHERE ALL(d IN all_dependencies WHERE d IN $visited)
                AND NOT t.id IN $visited
                RETURN DISTINCT t.id as node_id
            """, {'visited': list(visited)})

            level_nodes = [record['node_id'] async for record in result]

            if not level_nodes:
                # No hay más nodos alcanzables - verificar si quedan nodos
                remaining = len(tasks) - len(visited)
                if remaining > 0:
                    logger.warning(f"{remaining} tasks unreachable - possible orphans")
                break

            levels[current_level] = level_nodes
            visited.update(level_nodes)

        logger.info(f"Topological levels calculated: {len(levels)} levels, {len(visited)} tasks")
        return levels
```

**Deliverables Día 8-9**:
- ✅ `dag_builder.py` implementado
- ✅ Neo4j integration funcionando
- ✅ Cycle detection verificado
- ✅ Topological levels correctos

---

#### Día 10: Orchestrator MVP

**Archivo**: `src/cognitive/orchestrator_mvp.py`

```python
"""
Orchestrator MVP - Coordinador principal del sistema cognitivo
"""
from typing import Dict, List, Tuple
import asyncio

from src.cognitive.planning import MultiPassPlanningMVP, DAG, AtomicTask
from src.cognitive.inference import CognitivePatternInferenceEngine
from src.cognitive.patterns import PatternBankMVP
from src.cognitive.signatures import SemanticTaskSignature
from src.cognitive.validation import EnsembleValidator
from src.observability import get_logger

logger = get_logger("orchestrator_mvp")


class OrchestratorMVP:
    """
    Orquestador principal de arquitectura cognitiva

    Pipeline:
    1. Multi-pass planning → DAG
    2. Procesamiento nivel por nivel (paralelo)
    3. Inferencia cognitiva por átomo
    4. Validación ensemble
    5. Almacenamiento de patterns exitosos
    """

    def __init__(self):
        self.planner = MultiPassPlanningMVP()
        self.cpie = CognitivePatternInferenceEngine(pattern_bank=PatternBankMVP())
        self.pattern_bank = self.cpie.pattern_bank
        self.validator = EnsembleValidator()  # Implementar en Día 11

    async def execute_project(self, requirements: str) -> List[Tuple[AtomicTask, str, Dict]]:
        """
        Pipeline completo de inferencia cognitiva

        Args:
            requirements: User requirements (natural language)

        Returns:
            List of (atom, generated_code, validation_metrics)
        """
        logger.info("Starting cognitive project execution")

        # 1. Multi-pass planning → DAG
        print("📋 Generating cognitive masterplan...")
        dag = await self.planner.generate_masterplan(requirements)
        print(f"✅ DAG created: {len(dag.nodes)} atomic tasks")

        # 2. Procesar por niveles topológicos (paralelo)
        results = []
        levels = dag.get_topological_levels()

        for level_num, atoms in enumerate(levels):
            print(f"\n🔄 Level {level_num}: {len(atoms)} atoms (parallel)")

            # Procesar todos los átomos del nivel en paralelo
            level_tasks = []
            for atom in atoms:
                task = self.process_atom_cognitive(atom, dag)
                level_tasks.append(task)

            level_results = await asyncio.gather(*level_tasks, return_exceptions=True)

            # Filtrar errores y procesar éxitos
            for i, result in enumerate(level_results):
                if isinstance(result, Exception):
                    logger.error(f"Atom failed: {atoms[i].id}", extra={'error': str(result)})
                    continue

                atom, code, validation = result
                results.append((atom, code, validation))

                # Almacenar patrones exitosos para aprendizaje
                if validation['precision'] >= 0.95:
                    signature = SemanticTaskSignature.from_atomic_task(atom)
                    await self.pattern_bank.store_success(
                        signature,
                        code,
                        validation
                    )
                    print(f"✅ Pattern learned: {atom.name[:50]}")

        logger.info(f"Project execution complete: {len(results)} atoms processed")
        return results

    async def process_atom_cognitive(
        self,
        atom: AtomicTask,
        dag: DAG
    ) -> Tuple[AtomicTask, str, Dict]:
        """
        Procesa un átomo usando inferencia cognitiva pura

        Returns:
            (atom, generated_code, validation_metrics)
        """
        # 1. Extraer firma semántica
        signature = SemanticTaskSignature.from_atomic_task(atom)

        # 2. Preparar contexto enriquecido
        context = {
            'dependencies': self._get_dependency_outputs(atom, dag),
            'stack': self._detect_stack(atom),
            'constraints': signature.constraints,
            'security': signature.security_level
        }

        # 3. Inferir implementación mediante CPIE
        code = await self.cpie.infer_implementation(signature, context)

        # 4. Validación ensemble
        validation = await self.validator.validate(code, atom)

        # 5. Retry inteligente si falla (max 3 intentos)
        retry_count = 0
        while not validation['success'] and retry_count < 3:
            retry_count += 1
            logger.warning(f"Retry {retry_count} for {atom.id}")

            # Enriquecer contexto con feedback del error
            context['previous_error'] = validation['errors']
            context['retry_attempt'] = retry_count

            # Re-inferir con contexto mejorado
            code = await self.cpie.infer_implementation(signature, context)
            validation = await self.validator.validate(code, atom)

        return atom, code, validation

    def _get_dependency_outputs(self, atom: AtomicTask, dag: DAG) -> List[Dict]:
        """Obtiene outputs de dependencias del átomo"""
        dependencies = dag.get_dependencies(atom.id)
        return [{'id': dep.id, 'outputs': dep.outputs} for dep in dependencies]

    def _detect_stack(self, atom: AtomicTask) -> str:
        """Detecta stack tecnológico del átomo"""
        # TODO: Implementar detección inteligente
        return "Python + FastAPI"
```

**Deliverables Día 10**:
- ✅ `orchestrator_mvp.py` implementado
- ✅ Pipeline end-to-end funcionando
- ✅ Pattern storage verificado
- ✅ Retry logic implementado

---

### FASE 1: Semana 3 - Validation & Testing

#### Día 11-12: Ensemble Validator

**Archivo**: `src/cognitive/validation/ensemble_validator.py`

```python
"""
Ensemble Validator - Validación mediante votación de múltiples LLMs
"""
import asyncio
from typing import Dict, List

from src.llm import EnhancedAnthropicClient
from src.cognitive.planning import AtomicTask
from src.observability import get_logger

logger = get_logger("ensemble_validator")


class EnsembleValidator:
    """
    Validación mediante ensemble voting
    - Claude Opus
    - (Opcionalmente) GPT-4
    - (Opcionalmente) DeepSeek Coder

    Threshold: 66% (2 de 3 deben aprobar en MVP con 1 validador)
    """

    def __init__(self, voting_threshold: float = 0.66):
        self.validators = {
            'claude': EnhancedAnthropicClient()
        }
        self.voting_threshold = voting_threshold

    async def validate(self, code: str, atom: AtomicTask) -> Dict:
        """
        Valida código mediante ensemble voting

        Args:
            code: Código generado
            atom: Tarea atómica original

        Returns:
            {
                'success': bool,
                'precision': float,
                'approval_rate': float,
                'errors': List[str],
                'details': List[Dict]
            }
        """
        # Validación paralela con todos los LLMs
        validation_tasks = []
        for name, validator in self.validators.items():
            task = self._validate_with_llm(validator, name, code, atom)
            validation_tasks.append(task)

        validations = await asyncio.gather(*validation_tasks)

        # Contar votos
        approvals = sum(1 for v in validations if v['approved'])
        total_validators = len(validations)
        approval_rate = approvals / total_validators

        # Construir resultado
        result = {
            'success': approval_rate >= self.voting_threshold,
            'approval_rate': approval_rate,
            'approvals': approvals,
            'total': total_validators,
            'precision': self._calculate_precision(validations),
            'details': validations,
            'errors': self._extract_errors(validations)
        }

        logger.info(
            "Validation complete",
            extra={
                'approval_rate': approval_rate,
                'precision': result['precision']
            }
        )

        return result

    async def _validate_with_llm(
        self,
        validator: EnhancedAnthropicClient,
        name: str,
        code: str,
        atom: AtomicTask
    ) -> Dict:
        """Valida con un LLM específico"""
        prompt = f"""Valida este código para la tarea atómica.

**Tarea**:
- Propósito: {atom.purpose}
- Inputs: {atom.inputs}
- Outputs: {atom.outputs}
- Max LOC: {atom.estimated_loc}

**Código**:
```python
{code}
```

**Evalúa**:
1. ¿Cumple el propósito EXACTO?
2. ¿Respeta inputs/outputs?
3. ¿Es <= {atom.estimated_loc} líneas?
4. ¿Es sintácticamente correcto?
5. ¿Es seguro y eficiente?

Retorna JSON:
```json
{{
  "approved": true/false,
  "score": 0.0-1.0,
  "issues": ["issue1", "issue2", ...],
  "suggestions": ["suggestion1", ...]
}}
```
"""
        response = await validator.generate(prompt, temperature=0.0, max_tokens=1000)
        validation = self._parse_json_response(response)
        validation['validator'] = name

        return validation

    def _calculate_precision(self, validations: List[Dict]) -> float:
        """Calcula precisión promedio basada en scores"""
        scores = [v.get('score', 0.5) for v in validations]
        return sum(scores) / len(scores) if scores else 0.0

    def _extract_errors(self, validations: List[Dict]) -> List[str]:
        """Extrae todos los errores únicos"""
        all_errors = []
        for v in validations:
            if 'issues' in v:
                all_errors.extend(v['issues'])
        return list(set(all_errors))

    def _parse_json_response(self, response: str) -> Dict:
        """Parsea JSON de respuesta LLM"""
        import json
        import re
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(response)
```

**Deliverables Día 11-12**:
- ✅ `ensemble_validator.py` implementado
- ✅ Claude validation funcionando
- ✅ Error extraction verificado
- ✅ Tests passing

---

#### Día 13-14: Integration Testing & Metrics

**Tests end-to-end**:
```python
# tests/cognitive/test_integration.py
@pytest.mark.asyncio
async def test_full_cognitive_pipeline():
    """Test pipeline completo: requirements → código validado"""
    orchestrator = OrchestratorMVP()

    requirements = """
    Simple CRUD API for User management:
    - Create user (POST /users)
    - Get user (GET /users/:id)
    - Update user (PUT /users/:id)
    - Delete user (DELETE /users/:id)
    """

    results = await orchestrator.execute_project(requirements)

    # Verificar resultados
    assert len(results) > 0
    successful = sum(1 for _, _, v in results if v['success'])
    precision = successful / len(results)

    # MVP target: >= 92%
    assert precision >= 0.92, f"Precision {precision:.2%} below 92% target"

    # Verificar pattern learning
    stats = orchestrator.pattern_bank.get_stats()
    assert stats['total_patterns'] > 0

@pytest.mark.asyncio
async def test_pattern_reuse():
    """Test que patterns se reusan correctamente"""
    orchestrator = OrchestratorMVP()

    # Ejecutar 2 proyectos similares
    req1 = "Create User CRUD API"
    req2 = "Create Product CRUD API"

    await orchestrator.execute_project(req1)
    results2 = await orchestrator.execute_project(req2)

    # Verificar reuso de patterns
    stats = orchestrator.pattern_bank.get_stats()
    assert stats['total_usage'] > stats['total_patterns'], "No pattern reuse detected"
```

**Métricas de tracking**:
```python
# src/cognitive/metrics/cognitive_metrics.py
class CognitiveMetrics:
    """Métricas específicas de arquitectura cognitiva"""

    @staticmethod
    def track_precision(results: List[Tuple]) -> float:
        """Calcula precisión del proyecto"""
        successful = sum(1 for _, _, v in results if v['success'])
        return successful / len(results) if results else 0.0

    @staticmethod
    def track_pattern_reuse_rate(pattern_bank: PatternBankMVP) -> float:
        """Tasa de reuso de patterns"""
        stats = pattern_bank.get_stats()
        return stats['total_usage'] / stats['total_patterns'] if stats['total_patterns'] > 0 else 0.0

    @staticmethod
    def track_inference_time(start_time: float, end_time: float) -> float:
        """Tiempo promedio por átomo"""
        return end_time - start_time
```

**Deliverables Día 13-14**:
- ✅ Integration tests passing
- ✅ Precision >= 92% verificada
- ✅ Pattern reuse funcionando
- ✅ Métricas implementadas

---

### FASE 1: Semana 4 - Polish & Production Ready

#### Día 15-17: Production Hardening

**Tareas**:
1. Error handling robusto en todos los componentes
2. Logging estructurado completo
3. Retry con exponential backoff
4. Rate limiting para LLM calls
5. Connection pooling (Neo4j, Qdrant)
6. Graceful degradation si un validador falla

**Ejemplo error handling**:
```python
# src/cognitive/error_handling/cognitive_errors.py
class CognitiveError(Exception):
    """Base error para sistema cognitivo"""
    pass

class PlanningError(CognitiveError):
    """Error en multi-pass planning"""
    pass

class InferenceError(CognitiveError):
    """Error en inferencia cognitiva"""
    pass

class ValidationError(CognitiveError):
    """Error en validación ensemble"""
    pass

class DAGCycleError(CognitiveError):
    """Ciclo detectado en DAG"""
    pass
```

---

#### Día 18-20: Documentation & Demo

**Documentation**:
- `DOCS/cognitive/ARCHITECTURE.md` - Arquitectura completa
- `DOCS/cognitive/USAGE.md` - Cómo usar el sistema
- `DOCS/cognitive/METRICS.md` - Métricas y benchmarks
- `DOCS/cognitive/TROUBLESHOOTING.md` - Debugging guide

**Demo script**:
```python
# scripts/demo_cognitive.py
async def main():
    orchestrator = OrchestratorMVP()

    requirements = """
    JWT Authentication System:
    - User registration
    - Login with JWT
    - Refresh tokens
    - Protected endpoints
    """

    print("🚀 Starting cognitive execution...")
    results = await orchestrator.execute_project(requirements)

    # Show results
    print(f"\n✅ Completed: {len(results)} atoms")
    precision = sum(1 for _, _, v in results if v['success']) / len(results)
    print(f"📊 Precision: {precision:.2%}")

    stats = orchestrator.pattern_bank.get_stats()
    print(f"🧠 Patterns learned: {stats['total_patterns']}")
    print(f"♻️ Pattern reuse rate: {stats['total_usage'] / max(stats['total_patterns'], 1):.2%}")
```

**Deliverables Semana 4**:
- ✅ Production ready code
- ✅ Complete documentation
- ✅ Demo funcionando
- ✅ Precision >= 92% en 3+ proyectos reales

---

### FASE 2: Integración LRM Selectiva (Semanas 5-6)

#### Semana 5: LRM Integration

**Objetivo**: Agregar o1/DeepSeek-R1 para tareas complejas → 99% precisión

**Tareas**:
1. Implementar `LRMClient` (o1 + DeepSeek-R1)
2. Crear `SmartTaskRouter` para decidir LRM vs LLM
3. Integrar con `MultiPassPlanningMVP`
4. Calibrar thresholds de complejidad

**SmartTaskRouter**:
```python
# src/cognitive/planning/smart_task_router.py
class SmartTaskRouter:
    """
    Router inteligente que decide LRM vs LLM
    basado en complejidad y criticidad
    """

    LRM_OPTIMAL_TASKS = {
        'masterplan_generation': 0.7,   # Usar LRM si complexity > 0.7
        'architecture_design': 0.6,
        'critical_validation': 0.9,
        'complex_algorithm': 0.8
    }

    def should_use_lrm(self, task_type: str, complexity: float) -> bool:
        """
        Decide si usar LRM para esta tarea

        Args:
            task_type: Tipo de tarea
            complexity: Complejidad 0-1

        Returns:
            True si debe usar LRM
        """
        threshold = self.LRM_OPTIMAL_TASKS.get(task_type, 1.0)
        return complexity >= threshold
```

**Deliverables Semana 5**:
- ✅ LRM integration funcionando
- ✅ SmartTaskRouter implementado
- ✅ Thresholds calibrados
- ✅ A/B testing LRM vs LLM

---

#### Semana 6: Optimization & 99% Target

**Objetivo**: Alcanzar 99% precisión mediante optimización

**Tareas**:
1. Fine-tuning de LRM thresholds
2. Optimización de prompts
3. Mejora de validation ensemble
4. Cost optimization (caching agresivo)
5. Performance tuning (parallelization)

**Validation con LRM**:
- 20% tareas críticas con LRM (98% precision)
- 80% tareas normales con LLM (90% precision)
- Weighted precision: 0.20 × 0.98 + 0.80 × 0.90 = 91.6%
- Cascade improvement (mejor planning): 91.6% × 1.08 = 98.9% ≈ 99%

**Deliverables Semana 6**:
- ✅ Precision >= 99% alcanzada
- ✅ Cost/benefit optimizado
- ✅ Production deployment ready
- ✅ Full documentation updated

---

## Métricas de Éxito del Plan

### MVP (4 semanas)
- ✅ Precisión >= 92%
- ✅ Pattern reuse rate >= 30% (después de 10 proyectos)
- ✅ Tiempo por átomo < 5s
- ✅ Costo por átomo < $0.002
- ✅ Zero mantenimiento manual

### Final (6 semanas con LRM)
- ✅ Precisión >= 99%
- ✅ Pattern reuse rate >= 50%
- ✅ Tiempo por átomo < 3s (con LRM selectivo)
- ✅ Costo por átomo < $0.005

---

## Sistema de Co-Reasoning (Crítico para 92%+)

### Arquitectura del Co-Reasoning System

El sistema de co-reasoning es **fundamental** para alcanzar 92%+ precisión. Coordina múltiples LLMs en dos modos:

1. **Single-LLM Mode** (tasks simples): Claude Opus solo
2. **Dual-LLM Mode** (tasks complejas): Claude Opus (strategy) + DeepSeek 70B (implementation)

### Implementación Completa

```python
# src/cognitive/reasoning/co_reasoning_system.py
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

class ReasoningMode(Enum):
    """Modos de razonamiento"""
    SINGLE_LLM = "single_llm"      # Claude solo
    DUAL_LLM = "dual_llm"          # Claude + DeepSeek
    LRM_CRITICAL = "lrm_critical"  # o1 para tareas críticas

@dataclass
class ReasoningResult:
    """Resultado del proceso de razonamiento"""
    strategy: str
    implementation: str
    reasoning_trace: List[str]
    confidence: float
    mode_used: ReasoningMode
    token_usage: Dict[str, int]

class CoReasoningSystem:
    """
    Sistema de Co-Reasoning que coordina múltiples LLMs
    para generar código de alta precisión
    """

    def __init__(
        self,
        claude_client,
        deepseek_client,
        lrm_client=None
    ):
        self.claude = claude_client
        self.deepseek = deepseek_client
        self.lrm = lrm_client

        # Thresholds para decidir modo
        self.complexity_threshold_dual = 0.6
        self.complexity_threshold_lrm = 0.85

    async def reason_and_implement(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict] = None
    ) -> ReasoningResult:
        """
        Ejecuta co-reasoning para una tarea atómica

        Args:
            signature: Firma semántica de la tarea
            context: Contexto del proyecto (stack, dependencies, etc)
            similar_pattern: Patrón similar del Pattern Bank (si existe)

        Returns:
            ReasoningResult con estrategia e implementación
        """
        complexity = self._estimate_complexity(signature, context)
        mode = self._select_reasoning_mode(complexity, signature)

        if mode == ReasoningMode.SINGLE_LLM:
            return await self._single_llm_reasoning(signature, context, similar_pattern)
        elif mode == ReasoningMode.DUAL_LLM:
            return await self._dual_llm_reasoning(signature, context, similar_pattern)
        else:  # LRM_CRITICAL
            return await self._lrm_reasoning(signature, context, similar_pattern)

    def _estimate_complexity(self, signature: 'SemanticTaskSignature', context: Dict) -> float:
        """
        Estima complejidad de la tarea (0-1)

        Factores:
        - Número de inputs/outputs
        - Security level
        - Domain complexity
        - Stack familiarity
        """
        complexity = 0.0

        # Factor 1: I/O complexity
        io_count = len(signature.inputs) + len(signature.outputs)
        complexity += min(io_count / 10, 0.3)

        # Factor 2: Security level
        security_weight = {
            'LOW': 0.0,
            'MEDIUM': 0.15,
            'HIGH': 0.3,
            'CRITICAL': 0.4
        }
        complexity += security_weight.get(signature.security_level, 0.2)

        # Factor 3: Domain complexity
        complex_domains = ['auth', 'payment', 'crypto', 'ml', 'distributed']
        if any(domain in signature.domain.lower() for domain in complex_domains):
            complexity += 0.2

        # Factor 4: Constraints
        complexity += min(len(signature.constraints) * 0.05, 0.1)

        return min(complexity, 1.0)

    def _select_reasoning_mode(self, complexity: float, signature: 'SemanticTaskSignature') -> ReasoningMode:
        """Selecciona modo de razonamiento basado en complejidad"""
        if self.lrm and complexity >= self.complexity_threshold_lrm:
            return ReasoningMode.LRM_CRITICAL
        elif complexity >= self.complexity_threshold_dual:
            return ReasoningMode.DUAL_LLM
        else:
            return ReasoningMode.SINGLE_LLM

    async def _single_llm_reasoning(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict]
    ) -> ReasoningResult:
        """
        Modo Single-LLM: Claude genera estrategia + implementación
        Usado para tareas simples (complexity < 0.6)
        """
        reasoning_trace = []

        prompt = self._build_single_llm_prompt(signature, context, similar_pattern)
        reasoning_trace.append(f"Single-LLM prompt generated (complexity: {self._estimate_complexity(signature, context):.2f})")

        response = await self.claude.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=2000
        )

        reasoning_trace.append(f"Claude response received ({len(response)} chars)")

        # Parse response (espera formato: STRATEGY:\n...\nIMPLEMENTATION:\n...)
        strategy, implementation = self._parse_single_response(response)

        return ReasoningResult(
            strategy=strategy,
            implementation=implementation,
            reasoning_trace=reasoning_trace,
            confidence=0.92,  # Single-LLM típicamente 92% confianza
            mode_used=ReasoningMode.SINGLE_LLM,
            token_usage={'claude': len(response.split())}
        )

    async def _dual_llm_reasoning(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict]
    ) -> ReasoningResult:
        """
        Modo Dual-LLM: Claude (estrategia) → DeepSeek (implementación)
        Usado para tareas complejas (0.6 <= complexity < 0.85)
        """
        reasoning_trace = []

        # PASO 1: Claude diseña estrategia
        strategy_prompt = self._build_strategy_prompt(signature, context, similar_pattern)
        reasoning_trace.append("Requesting strategy from Claude Opus")

        strategy = await self.claude.generate(
            prompt=strategy_prompt,
            temperature=0.1,
            max_tokens=1500
        )

        reasoning_trace.append(f"Strategy received: {len(strategy)} chars")

        # PASO 2: DeepSeek implementa estrategia
        impl_prompt = self._build_implementation_prompt(signature, strategy, context)
        reasoning_trace.append("Requesting implementation from DeepSeek 70B")

        implementation = await self.deepseek.generate(
            prompt=impl_prompt,
            temperature=0.0,  # Deterministic para código
            max_tokens=2000
        )

        reasoning_trace.append(f"Implementation received: {len(implementation)} chars")

        # PASO 3: Claude valida coherencia strategy-implementation
        validation = await self._validate_coherence(strategy, implementation, signature)
        reasoning_trace.append(f"Coherence validation: {validation['coherent']}")

        if not validation['coherent']:
            # Retry con feedback
            reasoning_trace.append("Retrying implementation with feedback")
            implementation = await self._retry_with_feedback(
                signature, strategy, implementation, validation['issues']
            )

        return ReasoningResult(
            strategy=strategy,
            implementation=implementation,
            reasoning_trace=reasoning_trace,
            confidence=0.96,  # Dual-LLM típicamente 96% confianza
            mode_used=ReasoningMode.DUAL_LLM,
            token_usage={
                'claude': len(strategy.split()),
                'deepseek': len(implementation.split())
            }
        )

    async def _lrm_reasoning(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict]
    ) -> ReasoningResult:
        """
        Modo LRM: o1/DeepSeek-R1 para tareas críticas
        Usado para tareas muy complejas (complexity >= 0.85)
        """
        reasoning_trace = []

        lrm_prompt = self._build_lrm_prompt(signature, context, similar_pattern)
        reasoning_trace.append(f"Requesting LRM reasoning (complexity >= 0.85)")

        response = await self.lrm.generate(
            prompt=lrm_prompt,
            max_tokens=4000  # LRMs necesitan más tokens para reasoning chains
        )

        reasoning_trace.append(f"LRM response received with reasoning chain")

        # LRMs retornan reasoning chain + código
        strategy, implementation = self._parse_lrm_response(response)

        return ReasoningResult(
            strategy=strategy,
            implementation=implementation,
            reasoning_trace=reasoning_trace,
            confidence=0.98,  # LRM típicamente 98% confianza
            mode_used=ReasoningMode.LRM_CRITICAL,
            token_usage={'lrm': len(response.split())}
        )

    def _build_single_llm_prompt(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict]
    ) -> str:
        """Construye prompt para modo single-LLM"""
        base_prompt = f"""
Implementa esta tarea atómica siguiendo EXACTAMENTE las especificaciones:

TAREA:
Purpose: {signature.purpose}
Intent: {signature.intent}
Domain: {signature.domain}

INPUTS:
{self._format_io(signature.inputs)}

OUTPUTS:
{self._format_io(signature.outputs)}

CONSTRAINTS:
{self._format_constraints(signature.constraints)}

STACK:
{self._format_stack(context.get('stack', {}))}

SECURITY: {signature.security_level}
PERFORMANCE: {signature.performance_tier}
IDEMPOTENT: {signature.idempotency}
"""

        if similar_pattern:
            base_prompt += f"""

PATRÓN SIMILAR ENCONTRADO (Similarity: {similar_pattern.get('score', 0):.2f}):
```python
{similar_pattern.get('code', '')}
```

IMPORTANTE: Adapta este patrón a los nuevos requisitos, NO lo copies literalmente.
"""

        base_prompt += """

FORMATO DE RESPUESTA:
STRATEGY:
[Describe tu estrategia de implementación en 2-3 líneas]

IMPLEMENTATION:
```python
[Código Python limpio, máximo 10 líneas]
```

REGLAS:
- Una sola responsabilidad
- Sin efectos secundarios globales
- Sin imports innecesarios
- Código auto-documentado
- Type hints completos
"""
        return base_prompt

    def _build_strategy_prompt(
        self,
        signature: 'SemanticTaskSignature',
        context: Dict,
        similar_pattern: Optional[Dict]
    ) -> str:
        """Construye prompt de estrategia para Claude en modo dual"""
        return f"""
Diseña la estrategia de implementación para esta tarea atómica:

TAREA: {signature.purpose}
DOMAIN: {signature.domain}
INPUTS: {signature.inputs}
OUTPUTS: {signature.outputs}
CONSTRAINTS: {signature.constraints}
SECURITY: {signature.security_level}

STACK: {context.get('stack', {})}

{"PATRÓN SIMILAR:\n" + similar_pattern.get('code', '') if similar_pattern else ''}

Responde SOLO la estrategia (3-5 líneas), SIN código:
- Approach principal
- Manejo de edge cases
- Security considerations
- Performance optimizations
"""

    def _build_implementation_prompt(
        self,
        signature: 'SemanticTaskSignature',
        strategy: str,
        context: Dict
    ) -> str:
        """Construye prompt de implementación para DeepSeek"""
        return f"""
Implementa EXACTAMENTE esta estrategia:

STRATEGY:
{strategy}

SPECIFICATIONS:
Purpose: {signature.purpose}
Inputs: {signature.inputs}
Outputs: {signature.outputs}
Stack: {context.get('stack', {})}

CÓDIGO (máximo 10 líneas):
```python
[Tu implementación aquí]
```

REGLAS ESTRICTAS:
- Sigue la estrategia AL PIE DE LA LETRA
- Máximo 10 líneas
- Type hints completos
- Sin imports innecesarios
- Sin comentarios (código auto-documentado)
"""

    async def _validate_coherence(
        self,
        strategy: str,
        implementation: str,
        signature: 'SemanticTaskSignature'
    ) -> Dict:
        """Valida coherencia entre estrategia e implementación"""
        validation_prompt = f"""
Valida si esta implementación sigue la estrategia:

STRATEGY:
{strategy}

IMPLEMENTATION:
{implementation}

TASK SPEC:
{signature.purpose}
Inputs: {signature.inputs}
Outputs: {signature.outputs}

Responde JSON:
{{
    "coherent": true/false,
    "issues": ["issue1", "issue2"],
    "confidence": 0.95
}}
"""
        response = await self.claude.generate(
            prompt=validation_prompt,
            temperature=0.0,
            max_tokens=500
        )

        import json
        return json.loads(response)

    async def _retry_with_feedback(
        self,
        signature: 'SemanticTaskSignature',
        strategy: str,
        failed_impl: str,
        issues: List[str]
    ) -> str:
        """Retry implementación con feedback de validación"""
        retry_prompt = f"""
La implementación anterior tiene problemas. Corrígela:

STRATEGY:
{strategy}

IMPLEMENTACIÓN FALLIDA:
{failed_impl}

PROBLEMAS DETECTADOS:
{chr(10).join(f"- {issue}" for issue in issues)}

TASK SPEC:
{signature.purpose}

Nueva implementación corregida (máximo 10 líneas):
```python
[Código corregido]
```
"""
        return await self.deepseek.generate(
            prompt=retry_prompt,
            temperature=0.0,
            max_tokens=2000
        )

    def _parse_single_response(self, response: str) -> Tuple[str, str]:
        """Parse response de single-LLM"""
        parts = response.split('IMPLEMENTATION:')
        if len(parts) != 2:
            return response[:200], response

        strategy = parts[0].replace('STRATEGY:', '').strip()
        implementation = parts[1].strip()

        # Extract code from markdown block
        if '```python' in implementation:
            implementation = implementation.split('```python')[1].split('```')[0].strip()

        return strategy, implementation

    def _parse_lrm_response(self, response: str) -> Tuple[str, str]:
        """Parse response de LRM (incluye reasoning chain)"""
        # LRMs típicamente usan formato especial
        # Simplificado para MVP
        return self._parse_single_response(response)

    def _format_io(self, io_dict: Dict[str, str]) -> str:
        """Formatea inputs/outputs"""
        return '\n'.join(f"- {k}: {v}" for k, v in io_dict.items())

    def _format_constraints(self, constraints: List[str]) -> str:
        """Formatea constraints"""
        return '\n'.join(f"- {c}" for c in constraints)

    def _format_stack(self, stack: Dict) -> str:
        """Formatea stack"""
        return '\n'.join(f"- {k}: {v}" for k, v in stack.items())
```

### Integración con CPIE

El `CognitivePatternInferenceEngine` usa el `CoReasoningSystem`:

```python
# En src/cognitive/inference/cpie.py (actualizado)
class CognitivePatternInferenceEngine:
    def __init__(self, pattern_bank: PatternBankMVP):
        self.pattern_bank = pattern_bank
        self.co_reasoning = CoReasoningSystem(
            claude_client=ClaudeClient(),
            deepseek_client=DeepSeekClient(),
            lrm_client=None  # MVP sin LRM
        )

    async def infer_implementation(
        self,
        signature: SemanticTaskSignature,
        context: Dict
    ) -> Tuple[str, Dict]:
        # Buscar patrón similar
        similar = await self.pattern_bank.find_similar(signature, threshold=0.92)

        # Co-reasoning
        result = await self.co_reasoning.reason_and_implement(
            signature=signature,
            context=context,
            similar_pattern=similar
        )

        return result.implementation, {
            'strategy': result.strategy,
            'reasoning_trace': result.reasoning_trace,
            'confidence': result.confidence,
            'mode': result.mode_used.value,
            'token_usage': result.token_usage
        }
```

---

## Estrategia de Migración Gradual

### Principio: Coexistencia Sin Romper Producción

**NO hacer Big Bang Rewrite**. La migración es gradual con rollback instantáneo.

### Fase 1: Infraestructura Paralela (Días 1-3)

```python
# src/config/feature_flags.py
class FeatureFlags:
    """Feature flags para migración gradual"""

    USE_COGNITIVE_ARCHITECTURE = os.getenv('USE_COGNITIVE_ARCH', 'false') == 'true'
    COGNITIVE_ROLLOUT_PERCENTAGE = int(os.getenv('COGNITIVE_ROLLOUT_PCT', '0'))
    COGNITIVE_ATOM_TYPES = os.getenv('COGNITIVE_ATOM_TYPES', '').split(',')

    @classmethod
    def should_use_cognitive(cls, atom_type: str = None) -> bool:
        """Decide si usar cognitive architecture para este átomo"""
        if not cls.USE_COGNITIVE_ARCHITECTURE:
            return False

        # Rollout gradual por porcentaje
        import random
        if random.randint(1, 100) > cls.COGNITIVE_ROLLOUT_PERCENTAGE:
            return False

        # Filtro por tipo de átomo (opcional)
        if atom_type and cls.COGNITIVE_ATOM_TYPES:
            return atom_type in cls.COGNITIVE_ATOM_TYPES

        return True
```

### Fase 2: Orchestrator Híbrido (Días 4-10)

```python
# src/agents/orchestrator_agent.py (REFACTORIZADO)
class HybridOrchestrator:
    """
    Orchestrator híbrido que soporta ambos sistemas:
    - Wave-based (legacy)
    - Cognitive (nuevo)
    """

    def __init__(self):
        # Legacy
        self.wave_executor = WaveExecutor()
        self.masterplan_generator = MasterplanGenerator()

        # Cognitive
        self.cognitive_orchestrator = OrchestratorMVP()

        self.feature_flags = FeatureFlags()

    async def execute_project(self, requirements: str) -> Dict:
        """Execute con A/B testing integrado"""
        if self.feature_flags.should_use_cognitive():
            logger.info("Using COGNITIVE architecture")
            try:
                return await self._execute_cognitive(requirements)
            except Exception as e:
                logger.error(f"Cognitive failed, fallback to legacy: {e}")
                return await self._execute_legacy(requirements)
        else:
            logger.info("Using LEGACY wave-based architecture")
            return await self._execute_legacy(requirements)

    async def _execute_cognitive(self, requirements: str) -> Dict:
        """Nueva arquitectura cognitiva"""
        start = time.time()

        results = await self.cognitive_orchestrator.execute_project(requirements)

        metrics = {
            'architecture': 'cognitive',
            'duration': time.time() - start,
            'atoms_generated': len(results),
            'precision': self._calculate_precision(results),
            'pattern_reuse_rate': self._calculate_reuse_rate(results)
        }

        await self._log_metrics(metrics)
        return self._format_results(results, metrics)

    async def _execute_legacy(self, requirements: str) -> Dict:
        """Arquitectura legacy wave-based"""
        start = time.time()

        masterplan = await self.masterplan_generator.generate(requirements)
        results = await self.wave_executor.execute_waves(masterplan)

        metrics = {
            'architecture': 'legacy',
            'duration': time.time() - start,
            'atoms_generated': len(results),
            'precision': self._calculate_precision(results)
        }

        await self._log_metrics(metrics)
        return self._format_results(results, metrics)
```

### Fase 3: Rollout Gradual

#### Semana 1-2 (MVP): 0% → 10%
```bash
# .env
USE_COGNITIVE_ARCH=true
COGNITIVE_ROLLOUT_PCT=10
COGNITIVE_ATOM_TYPES=auth,crud  # Solo auth y CRUD
```

#### Semana 3: 10% → 50%
```bash
COGNITIVE_ROLLOUT_PCT=50
COGNITIVE_ATOM_TYPES=  # Todos los tipos
```

#### Semana 4: 50% → 100%
```bash
COGNITIVE_ROLLOUT_PCT=100  # Full rollout
```

#### Semana 5-6 (LRM): Deprecar legacy
```bash
# Remover código legacy después de 2 semanas sin incidentes
git rm src/execution/wave_executor.py
git rm src/services/masterplan_generator.py (legacy version)
```

### Rollback Instantáneo

En caso de problemas críticos:

```bash
# Rollback a legacy en < 1 minuto
USE_COGNITIVE_ARCH=false

# Restart services
docker-compose restart backend
```

---

## FASE 1.5: Frontend MVP (Semanas 5-6)

**Objetivo**: Implementar sistema de generación de frontends con arquitectura cognitiva, usando Next.js 14 + TypeScript + Shadcn/UI + Tailwind.

**Alcance MVP Frontend**:
- Text-to-UI generation (sin Figma inicialmente)
- ComponentSignature (equivalente frontend de STS)
- Frontend Pattern Bank para componentes Shadcn/UI
- Frontend CPIE adaptado para React/TypeScript
- Integración con Backend vía API contracts
- Precision target: 90-92% (MVP), escalar a 95%+ con LRM

### Arquitectura Frontend: Componentes Clave

#### 1. ComponentSignature (Frontend STS)

```typescript
// src/frontend/cognitive/signatures/component_signature.ts

export interface ComponentSignature {
  // Identificación
  componentId: string;
  semanticHash: string;

  // Propósito semántico
  purpose: string;           // e.g., "Display user profile card with avatar and actions"
  intent: string;            // e.g., "Present user info in compact, scannable format"

  // Especificación UI
  uiType: UIComponentType;   // 'container' | 'layout' | 'widget' | 'form' | 'data-display'
  complexity: UIComplexity;  // 'atomic' | 'molecular' | 'organism' (Atomic Design)

  // Interface Props
  props: {
    [key: string]: {
      type: string;          // 'string' | 'number' | 'User' | 'onClick: () => void'
      required: boolean;
      description: string;
    };
  };

  // Outputs/Events
  events: {
    [key: string]: {
      signature: string;     // e.g., 'onSubmit: (data: FormData) => void'
      description: string;
    };
  };

  // Constraints
  constraints: {
    maxWidth?: string;       // e.g., '768px'
    responsive: boolean;
    accessibility: string[]; // e.g., ['keyboard-nav', 'screen-reader', 'aria-labels']
    performance: {
      maxRenderTime?: number;  // ms
      lazyLoad?: boolean;
    };
  };

  // Stack Específico
  stack: {
    framework: 'react';
    language: 'typescript';
    styling: 'tailwind' | 'css-modules';
    uiLibrary: 'shadcn';
    stateManagement?: 'useState' | 'zustand' | 'redux';
  };

  // Business Logic Integration
  apiIntegration?: {
    endpoints: string[];     // e.g., ['/api/users/{id}', '/api/users/{id}/update']
    methods: string[];       // e.g., ['GET', 'PATCH']
  };

  // Design Tokens
  designTokens?: {
    colors?: string[];       // e.g., ['primary', 'secondary', 'destructive']
    spacing?: string[];      // e.g., ['sm', 'md', 'lg']
    typography?: string[];   // e.g., ['heading-2', 'body-text']
  };
}

export enum UIComponentType {
  CONTAINER = 'container',     // Wrappers, sections
  LAYOUT = 'layout',           // Grid, flex, sidebar
  WIDGET = 'widget',           // Button, Input, Card
  FORM = 'form',               // Form, FormField
  DATA_DISPLAY = 'data-display' // Table, List, Chart
}

export enum UIComplexity {
  ATOMIC = 'atomic',         // Button, Input (no dependencies)
  MOLECULAR = 'molecular',   // FormField = Label + Input + Error
  ORGANISM = 'organism'      // UserProfileCard = Avatar + Name + Actions
}

export class ComponentSignatureBuilder {
  /**
   * Construye ComponentSignature desde spec de chat
   */
  static async fromUserSpec(
    spec: string,
    llmClient: LLMClient
  ): Promise<ComponentSignature> {
    const analysisPrompt = `
Analiza esta especificación de componente UI y extrae:

SPEC:
${spec}

Responde en JSON:
{
  "purpose": "...",
  "intent": "...",
  "uiType": "widget|container|layout|form|data-display",
  "complexity": "atomic|molecular|organism",
  "props": {
    "propName": {"type": "string", "required": true, "description": "..."}
  },
  "events": {
    "onClick": {"signature": "() => void", "description": "..."}
  },
  "constraints": {
    "responsive": true,
    "accessibility": ["keyboard-nav", "screen-reader"]
  },
  "apiIntegration": {
    "endpoints": ["/api/..."],
    "methods": ["GET"]
  }
}
`;

    const response = await llmClient.generate({
      prompt: analysisPrompt,
      temperature: 0.0,
      maxTokens: 1500
    });

    const parsed = JSON.parse(response);

    return {
      componentId: this.generateComponentId(parsed.purpose),
      semanticHash: this.computeSemanticHash(parsed),
      ...parsed,
      stack: {
        framework: 'react',
        language: 'typescript',
        styling: 'tailwind',
        uiLibrary: 'shadcn'
      }
    };
  }

  private static generateComponentId(purpose: string): string {
    const sanitized = purpose
      .replace(/[^a-zA-Z0-9\s]/g, '')
      .split(/\s+/)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join('');
    return sanitized;
  }

  private static computeSemanticHash(data: any): string {
    const crypto = require('crypto');
    const normalized = {
      purpose: data.purpose,
      props: Object.keys(data.props || {}).sort(),
      events: Object.keys(data.events || {}).sort(),
      uiType: data.uiType
    };
    const jsonStr = JSON.stringify(normalized);
    return crypto.createHash('sha256').update(jsonStr).digest('hex');
  }
}
```

#### 2. Frontend Pattern Bank

```typescript
// src/frontend/cognitive/patterns/frontend_pattern_bank.ts

import { ComponentSignature } from '../signatures/component_signature';
import { VectorDB } from '@/lib/vector_db'; // Qdrant/FAISS

export interface StoredComponentPattern {
  signature: ComponentSignature;
  implementation: {
    code: string;               // React component code
    dependencies: string[];     // npm packages
    shadcnComponents: string[]; // e.g., ['button', 'card', 'input']
  };
  metadata: {
    precision: number;          // Validation score
    successRate: number;        // Reuse success %
    averageRenderTime: number;  // Performance
    a11yScore: number;          // Accessibility score
    createdAt: Date;
    lastUsed: Date;
    usageCount: number;
  };
  feedback: {
    userEdits: number;          // How many times edited post-gen
    compilationErrors: number;
    validationPassed: boolean;
  };
}

export class FrontendPatternBank {
  private vectorDB: VectorDB;
  private embeddingModel: EmbeddingModel;
  private storageThreshold: number = 0.88; // Store if precision >= 88%

  constructor(vectorDBUrl: string) {
    this.vectorDB = new VectorDB(vectorDBUrl);
    this.embeddingModel = new EmbeddingModel('sentence-transformers/all-MiniLM-L6-v2');
  }

  /**
   * Busca componentes similares basados en signature
   */
  async searchSimilar(
    signature: ComponentSignature,
    topK: number = 5
  ): Promise<StoredComponentPattern[]> {
    // Crear embedding del componente query
    const queryText = this.signatureToSearchText(signature);
    const embedding = await this.embeddingModel.encode(queryText);

    // Search en vector DB con filtros
    const results = await this.vectorDB.search({
      vector: embedding,
      topK,
      filters: {
        uiType: signature.uiType,
        'stack.framework': signature.stack.framework,
        'metadata.precision': { $gte: 0.85 } // Solo patterns buenos
      }
    });

    return results.map(r => r.payload as StoredComponentPattern);
  }

  /**
   * Almacena pattern exitoso
   */
  async storeSuccess(
    signature: ComponentSignature,
    implementation: { code: string; dependencies: string[]; shadcnComponents: string[] },
    validationScore: number,
    renderTime: number,
    a11yScore: number
  ): Promise<void> {
    if (validationScore < this.storageThreshold) {
      console.log(`Pattern precision ${validationScore} < threshold ${this.storageThreshold}, not storing`);
      return;
    }

    const pattern: StoredComponentPattern = {
      signature,
      implementation,
      metadata: {
        precision: validationScore,
        successRate: 1.0, // Initial
        averageRenderTime: renderTime,
        a11yScore,
        createdAt: new Date(),
        lastUsed: new Date(),
        usageCount: 1
      },
      feedback: {
        userEdits: 0,
        compilationErrors: 0,
        validationPassed: true
      }
    };

    const embedding = await this.embeddingModel.encode(
      this.signatureToSearchText(signature)
    );

    await this.vectorDB.upsert({
      id: signature.semanticHash,
      vector: embedding,
      payload: pattern
    });

    console.log(`✅ Stored component pattern: ${signature.componentId}`);
  }

  /**
   * Actualiza feedback de uso
   */
  async updateFeedback(
    semanticHash: string,
    feedback: { userEdits?: number; compilationErrors?: number }
  ): Promise<void> {
    const pattern = await this.vectorDB.retrieve(semanticHash);
    if (!pattern) return;

    pattern.payload.feedback = {
      ...pattern.payload.feedback,
      ...feedback
    };

    // Recalcular success rate
    const totalUses = pattern.payload.metadata.usageCount;
    const errors = pattern.payload.feedback.compilationErrors;
    pattern.payload.metadata.successRate = (totalUses - errors) / totalUses;

    await this.vectorDB.update(semanticHash, pattern.payload);
  }

  private signatureToSearchText(sig: ComponentSignature): string {
    return [
      sig.purpose,
      sig.intent,
      sig.uiType,
      ...Object.keys(sig.props),
      ...Object.keys(sig.events || {})
    ].join(' ');
  }

  async getStats(): Promise<{
    totalPatterns: number;
    avgPrecision: number;
    avgSuccessRate: number;
    topComponents: string[];
  }> {
    const allPatterns = await this.vectorDB.scroll({ limit: 1000 });

    const precisions = allPatterns.map(p => p.payload.metadata.precision);
    const successRates = allPatterns.map(p => p.payload.metadata.successRate);
    const sorted = allPatterns.sort((a, b) =>
      b.payload.metadata.usageCount - a.payload.metadata.usageCount
    );

    return {
      totalPatterns: allPatterns.length,
      avgPrecision: precisions.reduce((a, b) => a + b, 0) / precisions.length,
      avgSuccessRate: successRates.reduce((a, b) => a + b, 0) / successRates.length,
      topComponents: sorted.slice(0, 10).map(p => p.payload.signature.componentId)
    };
  }
}
```

#### 3. Frontend CPIE (Cognitive Pattern Inference Engine)

```typescript
// src/frontend/cognitive/inference/frontend_cpie.ts

import { ComponentSignature } from '../signatures/component_signature';
import { FrontendPatternBank, StoredComponentPattern } from '../patterns/frontend_pattern_bank';
import { CoReasoningSystem, ReasoningMode } from './co_reasoning';

export interface ComponentGenerationResult {
  code: string;
  dependencies: string[];
  shadcnComponents: string[];
  strategy: string;
  confidence: number;
  renderTime?: number;
  a11yScore?: number;
}

export class FrontendCPIE {
  private patternBank: FrontendPatternBank;
  private coReasoning: CoReasoningSystem;
  private shadcnRegistry: ShadcnRegistry;

  constructor(
    patternBank: FrontendPatternBank,
    claudeClient: LLMClient,
    deepseekClient: LLMClient
  ) {
    this.patternBank = patternBank;
    this.coReasoning = new CoReasoningSystem(claudeClient, deepseekClient);
    this.shadcnRegistry = new ShadcnRegistry();
  }

  /**
   * Genera componente React desde signature
   */
  async inferComponent(
    signature: ComponentSignature,
    context: ComponentContext
  ): Promise<ComponentGenerationResult> {
    console.log(`🧠 Inferring component: ${signature.componentId}`);

    // 1. Search similar patterns
    const similarPatterns = await this.patternBank.searchSimilar(signature, 3);
    const bestMatch = similarPatterns[0];

    // 2. Decide strategy: reuse vs generate
    if (bestMatch && bestMatch.metadata.precision >= 0.92) {
      console.log(`♻️  Reusing pattern with ${bestMatch.metadata.precision} precision`);
      return this.adaptExistingPattern(bestMatch, signature, context);
    }

    // 3. Generate new component with Co-Reasoning
    console.log(`🆕 Generating new component via Co-Reasoning`);
    const result = await this.generateViaCoReasoning(signature, context, similarPatterns);

    // 4. Validate generated code
    const validation = await this.validateComponent(result.code, signature);

    if (!validation.passed) {
      console.log(`⚠️  Validation failed, retrying...`);
      // Retry with feedback
      const retryResult = await this.retryWithFeedback(
        signature,
        result,
        validation.issues
      );
      return retryResult;
    }

    // 5. Store if successful
    await this.patternBank.storeSuccess(
      signature,
      {
        code: result.code,
        dependencies: result.dependencies,
        shadcnComponents: result.shadcnComponents
      },
      validation.score,
      validation.renderTime || 0,
      validation.a11yScore || 0
    );

    return result;
  }

  private async generateViaCoReasoning(
    signature: ComponentSignature,
    context: ComponentContext,
    similarPatterns: StoredComponentPattern[]
  ): Promise<ComponentGenerationResult> {
    // Estimate complexity
    const complexity = this.estimateComplexity(signature);

    // Prepare context for Co-Reasoning
    const enrichedContext = {
      signature,
      projectContext: context,
      similarPatterns: similarPatterns.slice(0, 2).map(p => ({
        code: p.implementation.code,
        purpose: p.signature.purpose
      })),
      shadcnAvailable: await this.shadcnRegistry.listComponents(),
      constraints: signature.constraints
    };

    // Generate via Dual-LLM or Single-LLM based on complexity
    const mode = complexity > 0.6 ? ReasoningMode.DUAL_LLM : ReasoningMode.SINGLE_LLM;

    const reasoningResult = await this.coReasoning.reasonAndImplement(
      signature,
      enrichedContext,
      mode
    );

    // Parse generated code
    const code = this.extractComponentCode(reasoningResult.implementation);
    const dependencies = this.extractDependencies(code);
    const shadcnComponents = this.extractShadcnComponents(code);

    return {
      code,
      dependencies,
      shadcnComponents,
      strategy: reasoningResult.strategy,
      confidence: reasoningResult.confidence
    };
  }

  private async adaptExistingPattern(
    pattern: StoredComponentPattern,
    newSignature: ComponentSignature,
    context: ComponentContext
  ): Promise<ComponentGenerationResult> {
    // Si signature es casi idéntica, retornar directo
    const similarity = this.computeSimilarity(pattern.signature, newSignature);
    if (similarity > 0.95) {
      return {
        code: pattern.implementation.code,
        dependencies: pattern.implementation.dependencies,
        shadcnComponents: pattern.implementation.shadcnComponents,
        strategy: 'exact_reuse',
        confidence: pattern.metadata.precision
      };
    }

    // Si hay diferencias menores, adaptar con LLM ligero
    const adaptationPrompt = `
Adapta este componente existente a la nueva especificación:

COMPONENTE EXISTENTE:
Purpose: ${pattern.signature.purpose}
Props: ${JSON.stringify(pattern.signature.props, null, 2)}

CÓDIGO EXISTENTE:
\`\`\`tsx
${pattern.implementation.code}
\`\`\`

NUEVA ESPECIFICACIÓN:
Purpose: ${newSignature.purpose}
Props: ${JSON.stringify(newSignature.props, null, 2)}
Events: ${JSON.stringify(newSignature.events, null, 2)}

CAMBIOS NECESARIOS:
${this.describeChanges(pattern.signature, newSignature)}

Adapta el código manteniendo la estructura pero ajustando según la nueva spec.
Usa Shadcn/UI components y Tailwind CSS.
Máximo 50 líneas de código.

\`\`\`tsx
[Código adaptado]
\`\`\`
`;

    const adapted = await this.coReasoning.deepseek.generate({
      prompt: adaptationPrompt,
      temperature: 0.1,
      maxTokens: 3000
    });

    const code = this.extractComponentCode(adapted);

    return {
      code,
      dependencies: pattern.implementation.dependencies,
      shadcnComponents: pattern.implementation.shadcnComponents,
      strategy: 'pattern_adaptation',
      confidence: pattern.metadata.precision * 0.95 // Slight confidence reduction
    };
  }

  private async validateComponent(
    code: string,
    signature: ComponentSignature
  ): Promise<{
    passed: boolean;
    score: number;
    issues: string[];
    renderTime?: number;
    a11yScore?: number;
  }> {
    const issues: string[] = [];
    let score = 1.0;

    // 1. TypeScript compilation check
    try {
      await this.compileTypeScript(code);
    } catch (error) {
      issues.push(`TypeScript error: ${error.message}`);
      score -= 0.3;
    }

    // 2. React syntax validation
    if (!code.includes('export default') && !code.includes('export const')) {
      issues.push('Missing export statement');
      score -= 0.2;
    }

    // 3. Props validation
    const declaredProps = this.extractPropsFromCode(code);
    const requiredProps = Object.keys(signature.props).filter(
      k => signature.props[k].required
    );
    const missingProps = requiredProps.filter(p => !declaredProps.includes(p));
    if (missingProps.length > 0) {
      issues.push(`Missing required props: ${missingProps.join(', ')}`);
      score -= 0.2 * missingProps.length;
    }

    // 4. Accessibility basic checks
    let a11yScore = 1.0;
    if (signature.constraints.accessibility?.includes('keyboard-nav')) {
      if (!code.includes('onKeyDown') && !code.includes('onKeyPress')) {
        issues.push('Missing keyboard navigation handlers');
        a11yScore -= 0.3;
      }
    }
    if (signature.constraints.accessibility?.includes('aria-labels')) {
      if (!code.includes('aria-') && !code.includes('role=')) {
        issues.push('Missing ARIA attributes');
        a11yScore -= 0.2;
      }
    }

    // 5. Performance: Check if lazy loading needed
    if (signature.constraints.performance?.lazyLoad) {
      if (!code.includes('React.lazy') && !code.includes('dynamic(')) {
        issues.push('Missing lazy loading implementation');
        score -= 0.1;
      }
    }

    return {
      passed: score >= 0.7 && issues.length < 3,
      score: Math.max(score, 0),
      issues,
      a11yScore
    };
  }

  private async retryWithFeedback(
    signature: ComponentSignature,
    failedResult: ComponentGenerationResult,
    issues: string[]
  ): Promise<ComponentGenerationResult> {
    const retryPrompt = `
El componente generado tiene problemas. Corrígelos:

COMPONENTE FALLIDO:
\`\`\`tsx
${failedResult.code}
\`\`\`

PROBLEMAS DETECTADOS:
${issues.map(i => `- ${i}`).join('\n')}

ESPECIFICACIÓN ORIGINAL:
- Purpose: ${signature.purpose}
- Props: ${JSON.stringify(signature.props, null, 2)}
- Events: ${JSON.stringify(signature.events, null, 2)}
- Constraints: ${JSON.stringify(signature.constraints, null, 2)}

Genera una versión corregida que resuelva TODOS los problemas.
Usa TypeScript + Shadcn/UI + Tailwind CSS.

\`\`\`tsx
[Código corregido]
\`\`\`
`;

    const corrected = await this.coReasoning.deepseek.generate({
      prompt: retryPrompt,
      temperature: 0.0,
      maxTokens: 3000
    });

    const code = this.extractComponentCode(corrected);

    return {
      code,
      dependencies: failedResult.dependencies,
      shadcnComponents: failedResult.shadcnComponents,
      strategy: failedResult.strategy + '_retry',
      confidence: failedResult.confidence * 0.9
    };
  }

  // Helper methods
  private estimateComplexity(signature: ComponentSignature): number {
    let complexity = 0.3; // Base

    // Props complexity
    complexity += Object.keys(signature.props).length * 0.05;

    // Events complexity
    complexity += Object.keys(signature.events || {}).length * 0.08;

    // API integration adds complexity
    if (signature.apiIntegration) {
      complexity += signature.apiIntegration.endpoints.length * 0.15;
    }

    // UI complexity type
    const complexityMap = {
      [UIComplexity.ATOMIC]: 0.0,
      [UIComplexity.MOLECULAR]: 0.15,
      [UIComplexity.ORGANISM]: 0.3
    };
    complexity += complexityMap[signature.complexity] || 0;

    return Math.min(complexity, 1.0);
  }

  private extractComponentCode(response: string): string {
    // Extract from markdown code blocks
    const match = response.match(/```(?:tsx?|jsx?)\n([\s\S]*?)\n```/);
    return match ? match[1].trim() : response.trim();
  }

  private extractDependencies(code: string): string[] {
    const imports = code.match(/import .* from ['"]([^'"]+)['"]/g) || [];
    return imports
      .map(imp => imp.match(/from ['"]([@\w/-]+)['"]/)?.[1])
      .filter(Boolean) as string[];
  }

  private extractShadcnComponents(code: string): string[] {
    const shadcnImports = code.match(/from ['"]@\/components\/ui\/([^'"]+)['"]/g) || [];
    return shadcnImports
      .map(imp => imp.match(/ui\/([^'"]+)['"]/)?.[1])
      .filter(Boolean) as string[];
  }

  private async compileTypeScript(code: string): Promise<void> {
    // Simplified - en producción usar ts.transpileModule
    // o integrar con tsserver
    if (code.includes(': any') && !code.includes('// @ts-ignore')) {
      throw new Error('Avoid using "any" type');
    }
  }

  private extractPropsFromCode(code: string): string[] {
    // Extract from interface or type definition
    const match = code.match(/interface \w+Props \{([^}]+)\}/s);
    if (!match) return [];

    const propsBlock = match[1];
    const propNames = propsBlock
      .split('\n')
      .map(line => line.trim().split(/[?:]/)[0])
      .filter(Boolean);

    return propNames;
  }

  private computeSimilarity(sig1: ComponentSignature, sig2: ComponentSignature): number {
    let score = 0;

    // Purpose similarity (rough heuristic)
    if (sig1.purpose === sig2.purpose) score += 0.4;
    else if (sig1.purpose.includes(sig2.purpose) || sig2.purpose.includes(sig1.purpose)) score += 0.2;

    // Props similarity
    const props1 = Object.keys(sig1.props);
    const props2 = Object.keys(sig2.props);
    const commonProps = props1.filter(p => props2.includes(p));
    const propsSimilarity = commonProps.length / Math.max(props1.length, props2.length);
    score += propsSimilarity * 0.4;

    // UI type match
    if (sig1.uiType === sig2.uiType) score += 0.2;

    return score;
  }

  private describeChanges(oldSig: ComponentSignature, newSig: ComponentSignature): string {
    const changes: string[] = [];

    const oldProps = Object.keys(oldSig.props);
    const newProps = Object.keys(newSig.props);

    const added = newProps.filter(p => !oldProps.includes(p));
    const removed = oldProps.filter(p => !newProps.includes(p));

    if (added.length > 0) changes.push(`Added props: ${added.join(', ')}`);
    if (removed.length > 0) changes.push(`Removed props: ${removed.length > 0) changes.push(`Removed props: ${removed.join(', ')}`);

    if (oldSig.purpose !== newSig.purpose) {
      changes.push(`Purpose changed from "${oldSig.purpose}" to "${newSig.purpose}"`);
    }

    return changes.join('\n');
  }
}

// Helper class for Shadcn registry
class ShadcnRegistry {
  private components = [
    'button', 'card', 'input', 'label', 'select', 'textarea',
    'dialog', 'dropdown-menu', 'popover', 'tooltip',
    'form', 'table', 'tabs', 'accordion', 'alert',
    'avatar', 'badge', 'checkbox', 'radio-group',
    'progress', 'skeleton', 'switch', 'toast'
  ];

  async listComponents(): Promise<string[]> {
    return this.components;
  }

  isAvailable(component: string): boolean {
    return this.components.includes(component);
  }
}
```

#### 4. Frontend Orchestrator

```typescript
// src/frontend/cognitive/orchestration/frontend_orchestrator.ts

import { ComponentSignature, ComponentSignatureBuilder } from '../signatures/component_signature';
import { FrontendCPIE, ComponentGenerationResult } from '../inference/frontend_cpie';
import { FrontendPatternBank } from '../patterns/frontend_pattern_bank';

export interface FrontendProjectSpec {
  description: string;
  pages: PageSpec[];
  apiEndpoints?: string[];     // Backend API base URL
  designSystem?: {
    colors: Record<string, string>;
    typography: Record<string, string>;
  };
}

export interface PageSpec {
  name: string;                // e.g., 'UserProfile'
  route: string;               // e.g., '/users/[id]'
  description: string;
  components: string[];        // Descriptions of components needed
}

export interface FrontendGenerationResult {
  components: GeneratedComponent[];
  pages: GeneratedPage[];
  dependencies: string[];
  shadcnComponents: string[];
  precision: number;
  generationTime: number;
}

export interface GeneratedComponent {
  signature: ComponentSignature;
  code: string;
  filePath: string;            // e.g., 'components/user-profile-card.tsx'
}

export interface GeneratedPage {
  name: string;
  route: string;
  code: string;
  filePath: string;            // e.g., 'app/users/[id]/page.tsx'
  components: string[];        // Component IDs used
}

export class FrontendOrchestrator {
  private cpie: FrontendCPIE;
  private patternBank: FrontendPatternBank;
  private signatureBuilder: typeof ComponentSignatureBuilder;

  constructor(
    cpie: FrontendCPIE,
    patternBank: FrontendPatternBank
  ) {
    this.cpie = cpie;
    this.patternBank = patternBank;
    this.signatureBuilder = ComponentSignatureBuilder;
  }

  /**
   * Genera frontend completo desde spec de chat
   */
  async generateFrontend(
    spec: FrontendProjectSpec,
    claudeClient: LLMClient
  ): Promise<FrontendGenerationResult> {
    console.log(`🚀 Starting frontend generation for: ${spec.description}`);
    const startTime = Date.now();

    // 1. Multi-Pass Planning para UI
    const plan = await this.multiPassUIPlanning(spec, claudeClient);

    // 2. Generar atomic components primero
    const atomicComponents = await this.generateAtomicComponents(
      plan.atomicComponents,
      claudeClient
    );

    // 3. Generar molecular components (dependen de atomic)
    const molecularComponents = await this.generateMolecularComponents(
      plan.molecularComponents,
      atomicComponents,
      claudeClient
    );

    // 4. Generar organism components (dependen de molecular + atomic)
    const organismComponents = await this.generateOrganismComponents(
      plan.organismComponents,
      [...atomicComponents, ...molecularComponents],
      claudeClient
    );

    const allComponents = [
      ...atomicComponents,
      ...molecularComponents,
      ...organismComponents
    ];

    // 5. Generar pages (orquestan organisms)
    const pages = await this.generatePages(
      spec.pages,
      allComponents,
      claudeClient
    );

    // 6. Consolidar dependencies
    const allDependencies = new Set<string>();
    const allShadcnComponents = new Set<string>();

    allComponents.forEach(c => {
      c.result.dependencies.forEach(d => allDependencies.add(d));
      c.result.shadcnComponents.forEach(s => allShadcnComponents.add(s));
    });

    // 7. Calculate precision
    const precisions = allComponents.map(c => c.result.confidence);
    const avgPrecision = precisions.reduce((a, b) => a + b, 0) / precisions.length;

    const generationTime = (Date.now() - startTime) / 1000;

    console.log(`✅ Frontend generated in ${generationTime}s with ${avgPrecision * 100}% precision`);

    return {
      components: allComponents.map(c => ({
        signature: c.signature,
        code: c.result.code,
        filePath: this.generateFilePath(c.signature)
      })),
      pages,
      dependencies: Array.from(allDependencies),
      shadcnComponents: Array.from(allShadcnComponents),
      precision: avgPrecision,
      generationTime
    };
  }

  /**
   * Multi-Pass Planning adaptado para UI
   */
  private async multiPassUIPlanning(
    spec: FrontendProjectSpec,
    claudeClient: LLMClient
  ): Promise<{
    atomicComponents: string[];
    molecularComponents: string[];
    organismComponents: string[];
  }> {
    const planningPrompt = `
Analiza este proyecto frontend y descompón en componentes siguiendo Atomic Design:

SPEC:
${spec.description}

PAGES:
${spec.pages.map(p => `- ${p.name} (${p.route}): ${p.description}`).join('\n')}

COMPONENTS NEEDED:
${spec.pages.flatMap(p => p.components).join('\n')}

Descompón en 3 niveles:
1. **ATOMIC**: Componentes sin dependencias (Button, Input, Label, etc.)
2. **MOLECULAR**: Combinan 2-3 atomic (FormField = Label + Input + ErrorText)
3. **ORGANISM**: Secciones complejas (UserProfileCard, DataTable, etc.)

Responde en JSON:
{
  "atomicComponents": ["Button with primary variant", "Input with validation", ...],
  "molecularComponents": ["FormField with label and error", ...],
  "organismComponents": ["UserProfileCard with avatar and actions", ...]
}
`;

    const response = await claudeClient.generate({
      prompt: planningPrompt,
      temperature: 0.2,
      maxTokens: 2000
    });

    return JSON.parse(response);
  }

  private async generateAtomicComponents(
    specs: string[],
    claudeClient: LLMClient
  ): Promise<Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>> {
    console.log(`🔬 Generating ${specs.length} atomic components...`);

    const results = await Promise.all(
      specs.map(async (spec) => {
        const signature = await this.signatureBuilder.fromUserSpec(spec, claudeClient);
        signature.complexity = UIComplexity.ATOMIC;

        const result = await this.cpie.inferComponent(signature, {
          projectType: 'web-app',
          existingComponents: []
        });

        return { signature, result };
      })
    );

    console.log(`✅ Generated ${results.length} atomic components`);
    return results;
  }

  private async generateMolecularComponents(
    specs: string[],
    atomicComponents: Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>,
    claudeClient: LLMClient
  ): Promise<Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>> {
    console.log(`🧪 Generating ${specs.length} molecular components...`);

    const results = await Promise.all(
      specs.map(async (spec) => {
        const signature = await this.signatureBuilder.fromUserSpec(spec, claudeClient);
        signature.complexity = UIComplexity.MOLECULAR;

        const result = await this.cpie.inferComponent(signature, {
          projectType: 'web-app',
          existingComponents: atomicComponents.map(c => ({
            id: c.signature.componentId,
            code: c.result.code
          }))
        });

        return { signature, result };
      })
    );

    console.log(`✅ Generated ${results.length} molecular components`);
    return results;
  }

  private async generateOrganismComponents(
    specs: string[],
    existingComponents: Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>,
    claudeClient: LLMClient
  ): Promise<Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>> {
    console.log(`🦠 Generating ${specs.length} organism components...`);

    const results = await Promise.all(
      specs.map(async (spec) => {
        const signature = await this.signatureBuilder.fromUserSpec(spec, claudeClient);
        signature.complexity = UIComplexity.ORGANISM;

        const result = await this.cpie.inferComponent(signature, {
          projectType: 'web-app',
          existingComponents: existingComponents.map(c => ({
            id: c.signature.componentId,
            code: c.result.code
          }))
        });

        return { signature, result };
      })
    );

    console.log(`✅ Generated ${results.length} organism components`);
    return results;
  }

  private async generatePages(
    pageSpecs: PageSpec[],
    components: Array<{ signature: ComponentSignature; result: ComponentGenerationResult }>,
    claudeClient: LLMClient
  ): Promise<GeneratedPage[]> {
    console.log(`📄 Generating ${pageSpecs.length} pages...`);

    const pages = await Promise.all(
      pageSpecs.map(async (pageSpec) => {
        const pagePrompt = `
Genera una página Next.js 14 (App Router) usando estos componentes:

PAGE SPEC:
- Name: ${pageSpec.name}
- Route: ${pageSpec.route}
- Description: ${pageSpec.description}

AVAILABLE COMPONENTS:
${components.map(c => `- ${c.signature.componentId}: ${c.signature.purpose}`).join('\n')}

Requirements:
- Use Next.js 14 App Router (async page component)
- Import components from '@/components/...'
- Implement proper TypeScript types
- Handle loading and error states
- Use Suspense where appropriate
- Follow Next.js best practices

\`\`\`tsx
[Page code]
\`\`\`
`;

        const response = await claudeClient.generate({
          prompt: pagePrompt,
          temperature: 0.1,
          maxTokens: 3000
        });

        const code = this.extractCode(response);
        const usedComponents = this.extractUsedComponents(code, components);

        return {
          name: pageSpec.name,
          route: pageSpec.route,
          code,
          filePath: this.routeToFilePath(pageSpec.route),
          components: usedComponents
        };
      })
    );

    console.log(`✅ Generated ${pages.length} pages`);
    return pages;
  }

  private generateFilePath(signature: ComponentSignature): string {
    const fileName = signature.componentId
      .replace(/([A-Z])/g, '-$1')
      .toLowerCase()
      .slice(1);

    return `components/${fileName}.tsx`;
  }

  private routeToFilePath(route: string): string {
    // Convert /users/[id] to app/users/[id]/page.tsx
    const cleanRoute = route.startsWith('/') ? route.slice(1) : route;
    return `app/${cleanRoute}/page.tsx`;
  }

  private extractCode(response: string): string {
    const match = response.match(/```(?:tsx?|jsx?)\n([\s\S]*?)\n```/);
    return match ? match[1].trim() : response.trim();
  }

  private extractUsedComponents(
    code: string,
    availableComponents: Array<{ signature: ComponentSignature }>
  ): string[] {
    return availableComponents
      .filter(c => code.includes(c.signature.componentId))
      .map(c => c.signature.componentId);
  }
}

// Type definitions
interface ComponentContext {
  projectType: string;
  existingComponents: Array<{ id: string; code: string }>;
}

enum UIComplexity {
  ATOMIC = 'atomic',
  MOLECULAR = 'molecular',
  ORGANISM = 'organism'
}
```

### Timeline Detallado: Semanas 5-6

#### **Semana 5: Core Frontend Architecture**

**Día 1: Setup + ComponentSignature**
```bash
# Morning: Project setup
cd devmatrix-frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir
npx shadcn-ui@latest init

# Install dependencies
npm install @radix-ui/react-* class-variance-authority clsx tailwind-merge
npm install -D @types/node typescript

# Afternoon: ComponentSignature
mkdir -p src/frontend/cognitive/signatures
# Implementar component_signature.ts (350 líneas)
# Tests: signature builder, hash computation, props validation
npm run test src/frontend/cognitive/signatures
```

**Deliverable Día 1**:
- ✅ Next.js 14 + TypeScript + Shadcn/UI setup
- ✅ ComponentSignature implementation completa
- ✅ Tests unitarios con 100% coverage

**Día 2: Frontend Pattern Bank**
```bash
# Setup Vector DB (Qdrant local para MVP)
docker run -p 6333:6333 qdrant/qdrant

# Implement Pattern Bank
mkdir -p src/frontend/cognitive/patterns
# Implementar frontend_pattern_bank.ts (400 líneas)

# Tests
npm run test src/frontend/cognitive/patterns
```

**Deliverable Día 2**:
- ✅ FrontendPatternBank con Qdrant integration
- ✅ Search, store, update feedback methods
- ✅ Tests: search similarity, storage threshold, stats

**Día 3: Frontend CPIE (Part 1)**
```bash
# Implement core inference
mkdir -p src/frontend/cognitive/inference
# Implementar frontend_cpie.ts (600 líneas - parte 1)
#   - inferComponent
#   - generateViaCoReasoning
#   - adaptExistingPattern

# Integration tests
npm run test:integration
```

**Deliverable Día 3**:
- ✅ Frontend CPIE core methods
- ✅ Integration con Pattern Bank
- ✅ Precision test: 1 componente generado >= 88%

**Día 4: Frontend CPIE (Part 2) + Validation**
```bash
# Complete CPIE
#   - validateComponent
#   - retryWithFeedback
#   - Helper methods

# Shadcn Registry
# Implementar shadcn_registry.ts

# Tests
npm run test src/frontend/cognitive/inference
```

**Deliverable Día 4**:
- ✅ Frontend CPIE completo con validation
- ✅ TypeScript compilation checks
- ✅ Accessibility validation básica
- ✅ Tests: validation, retry, adaptation

**Día 5: Frontend Orchestrator**
```bash
# Implement orchestrator
mkdir -p src/frontend/cognitive/orchestration
# Implementar frontend_orchestrator.ts (500 líneas)
#   - Multi-Pass UI Planning
#   - Atomic/Molecular/Organism generation
#   - Page generation

# E2E test
npm run test:e2e -- --spec frontend-generation
```

**Deliverable Día 5**:
- ✅ FrontendOrchestrator completo
- ✅ Multi-Pass Planning para UI
- ✅ E2E test: Generar 1 página con 3 componentes
- ✅ Precision >= 90% promedio

---

#### **Semana 6: Integration + Refinement**

**Día 1: Backend API Integration**
```bash
# API client generator
mkdir -p src/frontend/api
# Generar cliente TypeScript desde OpenAPI del backend

# Contract validation
# Implementar api_contract_validator.ts
#   - Valida que endpoints existen
#   - Valida tipos de request/response

# Tests
npm run test src/frontend/api
```

**Deliverable Día 1**:
- ✅ API client auto-generado desde backend OpenAPI
- ✅ Contract validator
- ✅ Tests: endpoint existence, type safety

**Día 2-3: Full Frontend Generation Test**
```bash
# E2E: Generate complete mini app
# Spec: "Mini CRM with contacts list, detail view, and add form"

node scripts/generate_frontend.js --spec "Mini CRM..."

# Expected output:
#   - 8 atomic components (Button, Input, Label, etc.)
#   - 4 molecular (FormField, ContactCard, etc.)
#   - 2 organisms (ContactsList, ContactDetail)
#   - 3 pages (home, contacts/[id], contacts/new)

# Manual QA:
npm run dev
# Verificar en http://localhost:3000
```

**Deliverable Día 2-3**:
- ✅ Generación frontend completo end-to-end
- ✅ 15+ componentes generados
- ✅ 3 páginas funcionales
- ✅ Precision promedio >= 90%
- ✅ Build sin errores TypeScript
- ✅ UI visualmente coherente con Shadcn/UI

**Día 4: Performance + A11y Optimization**
```bash
# Performance audit
npm run build
npx lighthouse http://localhost:3000 --view

# A11y improvements
#   - Add missing ARIA labels
#   - Keyboard navigation verification
#   - Color contrast checks

# Automated a11y tests
npm install -D @axe-core/react
npm run test:a11y
```

**Deliverable Día 4**:
- ✅ Lighthouse score >= 90 (Performance, A11y)
- ✅ All components keyboard navigable
- ✅ Automated a11y tests passing

**Día 5: Pattern Bank Growth + Reuse**
```bash
# Generate 5+ different projects to grow Pattern Bank
# Track reuse rate

python scripts/measure_frontend_reuse.py

# Expected:
#   - Pattern Bank: 30+ components stored
#   - Reuse rate: >= 25% (Week 6 target)
#   - Avg precision: >= 91%
```

**Deliverable Día 5**:
- ✅ Pattern Bank con 30+ patterns
- ✅ Reuse rate >= 25%
- ✅ Precision consistency >= 90% across projects

---

## FASE 2: Integración Full Stack (Semanas 7-8)

**Objetivo**: Unificar backend + frontend en flujo cohesivo, con type safety end-to-end, testing integrado, y deployment ready.

### Semana 7: E2E Integration

**Día 1-2: Unified Project Generator**
```python
# src/orchestration/full_stack_orchestrator.py

class FullStackOrchestrator:
    """
    Orquesta generación backend + frontend en un único flujo
    """

    def __init__(
        self,
        backend_orchestrator: OrchestratorMVP,
        frontend_orchestrator: FrontendOrchestrator,
        contract_validator: ContractValidator
    ):
        self.backend = backend_orchestrator
        self.frontend = frontend_orchestrator
        self.validator = contract_validator

    async def generate_full_stack_project(
        self,
        spec: str,
        workflow: WorkflowType = WorkflowType.FRONTEND_FIRST
    ) -> FullStackResult:
        """
        Genera proyecto completo con backend + frontend

        Workflows:
        - FRONTEND_FIRST: UI → infer API needs → generate backend
        - BACKEND_FIRST: API → generate matching frontend
        - PARALLEL: Both simultaneously (requiere spec más detallada)
        """

        if workflow == WorkflowType.FRONTEND_FIRST:
            return await self._frontend_first_workflow(spec)
        elif workflow == WorkflowType.BACKEND_FIRST:
            return await self._backend_first_workflow(spec)
        else:
            return await self._parallel_workflow(spec)

    async def _frontend_first_workflow(self, spec: str) -> FullStackResult:
        """
        1. Genera frontend desde spec de chat
        2. Infiere API contracts desde componentes
        3. Genera backend matching
        """

        # 1. Parse spec y generar frontend
        frontend_spec = await self._parse_frontend_spec(spec)
        frontend_result = await self.frontend.generateFrontend(frontend_spec)

        # 2. Inferir API needs desde componentes
        api_contracts = await self._infer_api_contracts(frontend_result.components)

        # 3. Generar backend matching
        backend_spec = self._api_contracts_to_backend_spec(api_contracts)
        backend_result = await self.backend.execute_project(backend_spec)

        # 4. Validate contracts match
        validation = await self.validator.validate_e2e(
            backend_result,
            frontend_result,
            api_contracts
        )

        if not validation.passed:
            # Retry con ajustes
            backend_result = await self._adjust_backend(
                backend_result,
                validation.mismatches
            )

        return FullStackResult(
            backend=backend_result,
            frontend=frontend_result,
            contracts=api_contracts,
            validation=validation
        )

    async def _infer_api_contracts(
        self,
        components: List[GeneratedComponent]
    ) -> List[APIContract]:
        """
        Infiere API endpoints necesarios desde componentes frontend
        """
        contracts = []

        for component in components:
            if component.signature.apiIntegration:
                for endpoint, method in zip(
                    component.signature.apiIntegration.endpoints,
                    component.signature.apiIntegration.methods
                ):
                    # Parse endpoint y extraer tipos
                    contract = await self._parse_endpoint_to_contract(
                        endpoint,
                        method,
                        component.code
                    )
                    contracts.append(contract)

        # Deduplicate
        unique_contracts = self._deduplicate_contracts(contracts)
        return unique_contracts

    async def _parse_endpoint_to_contract(
        self,
        endpoint: str,
        method: str,
        component_code: str
    ) -> APIContract:
        """
        Usa LLM para inferir contract desde uso en componente
        """
        prompt = f"""
Analiza este componente y el endpoint que usa:

ENDPOINT: {method} {endpoint}

COMPONENT CODE:
```tsx
{component_code}
```

Infiere el API contract:
{{
  "endpoint": "{endpoint}",
  "method": "{method}",
  "requestSchema": {{
    "type": "object",
    "properties": {{ ... }}
  }},
  "responseSchema": {{
    "type": "object",
    "properties": {{ ... }}
  }},
  "authentication": "bearer" | "none"
}}
"""

        response = await self.backend.claude.generate(
            prompt=prompt,
            temperature=0.0,
            maxTokens=1000
        )

        return APIContract(**json.loads(response))
```

**Día 3: Type Safety Cross-Stack**
```typescript
// src/types/api_types_generator.ts

/**
 * Genera tipos TypeScript desde Pydantic models del backend
 */
export class APITypesGenerator {
  async generateFromOpenAPI(openAPISpec: OpenAPISpec): Promise<string> {
    // Convert OpenAPI schemas to TypeScript interfaces
    const types: string[] = [];

    for (const [name, schema] of Object.entries(openAPISpec.components.schemas)) {
      const tsInterface = this.schemaToTypeScript(name, schema);
      types.push(tsInterface);
    }

    // Generate API client with typed methods
    const apiClient = this.generateTypedClient(openAPISpec.paths, types);

    return [
      '// Auto-generated from backend OpenAPI spec',
      '// DO NOT EDIT MANUALLY',
      '',
      ...types,
      '',
      apiClient
    ].join('\n');
  }

  private schemaToTypeScript(name: string, schema: any): string {
    const properties = Object.entries(schema.properties || {})
      .map(([key, prop]: [string, any]) => {
        const required = schema.required?.includes(key) ?? false;
        const optional = required ? '' : '?';
        const type = this.openAPITypeToTS(prop.type, prop.format);
        return `  ${key}${optional}: ${type};`;
      })
      .join('\n');

    return `export interface ${name} {\n${properties}\n}`;
  }

  private openAPITypeToTS(type: string, format?: string): string {
    const typeMap: Record<string, string> = {
      'string': 'string',
      'integer': 'number',
      'number': 'number',
      'boolean': 'boolean',
      'array': 'any[]', // Simplificado
      'object': 'Record<string, any>'
    };

    if (format === 'date-time') return 'string'; // ISO string
    if (format === 'uuid') return 'string';

    return typeMap[type] || 'any';
  }

  private generateTypedClient(paths: any, types: string[]): string {
    // Generate fetch wrapper with TypeScript types
    return `
export class APIClient {
  constructor(private baseURL: string, private token?: string) {}

  ${Object.entries(paths).map(([path, methods]: [string, any]) =>
    Object.entries(methods).map(([method, spec]: [string, any]) => {
      const operationId = spec.operationId || `${method}${path.replace(/[^a-zA-Z0-9]/g, '')}`;
      const requestType = spec.requestBody?.content['application/json']?.schema.$ref?.split('/').pop() || 'any';
      const responseType = spec.responses['200']?.content['application/json']?.schema.$ref?.split('/').pop() || 'any';

      return `
  async ${operationId}(data: ${requestType}): Promise<${responseType}> {
    const response = await fetch(\`\${this.baseURL}${path}\`, {
      method: '${method.toUpperCase()}',
      headers: {
        'Content-Type': 'application/json',
        ${spec.security ? `'Authorization': \`Bearer \${this.token}\`,` : ''}
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error(\`API error: \${response.statusText}\`);
    return response.json();
  }`;
    }).join('\n')
  ).join('\n')}
}
`;
  }
}
```

**Día 4-5: E2E Testing Strategy**
```typescript
// tests/e2e/full_stack.spec.ts

import { test, expect } from '@playwright/test';
import { setupTestDB, teardownTestDB } from './helpers/db';
import { startBackend, stopBackend } from './helpers/backend';

test.describe('Full Stack E2E: Mini CRM', () => {
  test.beforeAll(async () => {
    await setupTestDB();
    await startBackend();
  });

  test.afterAll(async () => {
    await stopBackend();
    await teardownTestDB();
  });

  test('User can create, view, and edit contact', async ({ page }) => {
    // 1. Navigate to app
    await page.goto('http://localhost:3000');

    // 2. Create new contact
    await page.click('text=Add Contact');
    await page.fill('[name="name"]', 'John Doe');
    await page.fill('[name="email"]', 'john@example.com');
    await page.click('button:has-text("Save")');

    // 3. Verify contact appears in list
    await expect(page.locator('text=John Doe')).toBeVisible();

    // 4. Click to view details
    await page.click('text=John Doe');
    await expect(page).toHaveURL(/\/contacts\/\d+/);
    await expect(page.locator('text=john@example.com')).toBeVisible();

    // 5. Edit contact
    await page.click('button:has-text("Edit")');
    await page.fill('[name="phone"]', '+1234567890');
    await page.click('button:has-text("Save")');

    // 6. Verify update via API
    const contactId = page.url().match(/\/contacts\/(\d+)/)?.[1];
    const response = await page.request.get(`http://localhost:8000/api/v1/contacts/${contactId}`);
    const contact = await response.json();
    expect(contact.phone).toBe('+1234567890');
  });

  test('API contract matches frontend expectations', async ({ request }) => {
    // Verify all endpoints used by frontend exist and return correct types

    const endpoints = [
      { path: '/api/v1/contacts', method: 'GET' },
      { path: '/api/v1/contacts', method: 'POST' },
      { path: '/api/v1/contacts/1', method: 'GET' },
      { path: '/api/v1/contacts/1', method: 'PATCH' }
    ];

    for (const endpoint of endpoints) {
      const response = await request.fetch(`http://localhost:8000${endpoint.path}`, {
        method: endpoint.method,
        headers: endpoint.method === 'POST' ? { 'Content-Type': 'application/json' } : {}
      });

      expect(response.ok || response.status === 404).toBeTruthy(); // 404 OK for GET /1 if not exists
    }
  });
});
```

### Semana 8: Polish + Production Ready

**Día 1: Performance Optimization**
```bash
# Backend optimization
python scripts/optimize_backend.py
#   - Add DB indexes for common queries
#   - Enable Redis caching for Pattern Bank
#   - Optimize Neo4j queries

# Frontend optimization
npm run analyze # Analyze bundle size
#   - Code splitting per page
#   - Lazy load heavy components
#   - Optimize images (next/image)

# Load testing
artillery run tests/load/full_stack.yml
# Target: 100 req/s, p95 < 500ms
```

**Día 2: Security Hardening**
```bash
# Backend security
python scripts/security_audit.py
#   - SQL injection checks
#   - XSS prevention
#   - Rate limiting per endpoint
#   - JWT expiry validation

# Frontend security
npm audit fix
#   - CSP headers
#   - Sanitize user input
#   - Secure cookies
```

**Día 3: Documentation + Deployment**
```bash
# Generate docs
python scripts/generate_docs.py
#   - API reference (auto from OpenAPI)
#   - Component storybook
#   - Architecture diagrams

# Docker compose for production
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
```

**Día 4-5: Final Integration Tests + Demo**
```bash
# Run full test suite
npm run test:all        # Frontend tests
python -m pytest        # Backend tests
npm run test:e2e        # E2E tests

# Generate 3 different full-stack projects as demo
python scripts/demo_generator.py --projects "Mini CRM,Todo App,Blog Platform"

# Measure final metrics
python scripts/measure_precision.py --full-stack

# Expected metrics:
#   - Backend precision: >= 95%
#   - Frontend precision: >= 92%
#   - E2E tests passing: 100%
#   - Pattern reuse (backend): >= 40%
#   - Pattern reuse (frontend): >= 30%
#   - Avg generation time: < 8 minutes per full project
```

---

## Integration Workflow Comparison

### Frontend-First (Recomendado para MVP)

**Ventajas**:
- UI define contracts naturalmente
- User experience driving backend
- Más intuitivo para specs de chat

**Flujo**:
1. User: "Mini CRM con lista de contactos y formulario"
2. Generate frontend (ComponentSignatures → API needs)
3. Infer API contracts desde componentes
4. Generate backend matching

**Ejemplo**:
```typescript
// Frontend genera esto:
interface ContactsListProps {
  apiEndpoint: '/api/v1/contacts';
  method: 'GET';
  responseType: Contact[];
}

// Backend infiere y genera:
@router.get("/api/v1/contacts", response_model=List[Contact])
async def get_contacts(db: Session = Depends(get_db)):
    return db.query(ContactModel).all()
```

### Backend-First

**Ventajas**:
- Útil cuando lógica de negocio es compleja
- APIs reutilizables por múltiples frontends

**Flujo**:
1. Generate backend con OpenAPI spec
2. Export types a TypeScript
3. Generate frontend consumiendo API client

### Parallel (Avanzado - Post-MVP)

**Requiere**:
- Spec muy detallada
- Contract-first design (OpenAPI manual)
- Validación continua de sync

---

## Checkpoints de Calidad por Semana

---

## Checkpoints de Calidad por Semana

### Semana 1: Core Components
- ✅ **Tests unitarios**: 100% coverage en STS, PatternBank, CPIE
- ✅ **Precision test**: >= 85% en 5 átomos de prueba
- ✅ **Performance**: STS hash < 1ms, Pattern search < 100ms
- ✅ **Code review**: Arquitectura aprobada por lead

### Semana 2: Multi-Pass + DAG
- ✅ **Integration tests**: DAG builder genera graphs válidos
- ✅ **Precision test**: >= 90% en proyecto auth completo
- ✅ **Performance**: Multi-pass < 30s para 20 átomos
- ✅ **Neo4j load test**: 1000+ nodes sin degradación

### Semana 3: Validation + Production Ready
- ✅ **E2E tests**: 3 proyectos reales (auth, CRUD, API)
- ✅ **Precision target**: >= 92% promedio en 3 proyectos
- ✅ **Pattern reuse**: >= 20% después de 10 ejecuciones
- ✅ **Cost analysis**: < $0.002 por átomo
- ✅ **Error handling**: Graceful degradation a legacy

### Semana 4: Hardening
- ✅ **Load test**: 100 átomos paralelos sin fallos
- ✅ **Precision stability**: 92%+ mantenido por 50 ejecuciones
- ✅ **Pattern bank**: >= 50 patrones validados
- ✅ **Documentation**: Arquitectura + APIs + Troubleshooting
- ✅ **Rollback test**: Rollback exitoso en < 2 min

### Semana 5: LRM Integration
- ✅ **LRM tests**: o1/DeepSeek-R1 funcionando
- ✅ **Smart routing**: Complexity detection accuracy > 90%
- ✅ **A/B test**: LRM vs LLM en 20 tareas complejas
- ✅ **Cost optimization**: LRM usado solo en 15-20% de tareas

### Semana 6: 99% Target
- ✅ **Final precision**: >= 99% en 5+ proyectos reales
- ✅ **Pattern reuse**: >= 50%
- ✅ **Production deployment**: Zero downtime migration
- ✅ **Legacy deprecation**: Wave executor eliminado
- ✅ **Team training**: Docs + demo + Q&A

---

## Troubleshooting Guide

### Problema 1: Precision < 92% en MVP

**Síntomas**:
- Código generado no compila
- Tests fallan consistentemente
- Precision promedio < 85%

**Diagnóstico**:
```python
# Analizar fallos por tipo
python scripts/analyze_failures.py --precision-threshold 0.92

# Output esperado:
# Top failure reasons:
# 1. Missing imports (30%)
# 2. Type mismatches (25%)
# 3. Logic errors (20%)
# 4. Edge cases not handled (15%)
```

**Soluciones**:
1. **Missing imports**: Mejorar extracción de dependencies en STS
2. **Type mismatches**: Agregar validation schema estricto
3. **Logic errors**: Aumentar context en prompts (stack, patterns)
4. **Edge cases**: Agregar constraints específicos en STS

### Problema 2: Pattern Bank No Crece

**Síntomas**:
- Pattern reuse rate < 10% después de 20 ejecuciones
- Vector DB vacío o con pocos patterns

**Diagnóstico**:
```python
# Verificar threshold de storage
pattern_bank = PatternBankMVP()
stats = await pattern_bank.get_stats()

print(f"Patterns stored: {stats['total_patterns']}")
print(f"Avg precision: {stats['avg_precision']}")
print(f"Success rate: {stats['success_rate']}")
```

**Soluciones**:
- Reducir `success_threshold` de 0.95 a 0.90 temporalmente
- Verificar que `store_success()` se llama correctamente
- Revisar embeddings (modelo correcto, dimensiones OK)

### Problema 3: Neo4j DAG Lento

**Síntomas**:
- DAG builder tarda > 60s para 50 átomos
- Queries Neo4j timeout

**Diagnóstico**:
```cypher
// Verificar índices
CALL db.indexes()

// Verificar query plan
PROFILE MATCH (a:AtomicTask)-[:DEPENDS_ON]->(b:AtomicTask)
WHERE a.masterplan_id = $id
RETURN a, b
```

**Soluciones**:
- Crear índices faltantes: `CREATE INDEX ON :AtomicTask(masterplan_id)`
- Batch inserts en vez de uno por uno
- Usar `UNWIND` para operaciones bulk

### Problema 4: Co-Reasoning Failures

**Síntomas**:
- Strategy-Implementation mismatch
- Coherence validation falla > 20%

**Diagnóstico**:
```python
# Analizar coherence validation logs
grep "coherent.*false" logs/co_reasoning.log | wc -l
```

**Soluciones**:
- Mejorar prompt de strategy (más específico)
- Agregar examples en implementation prompt
- Aumentar retry attempts de 1 a 2

### Problema 5: Costos Elevados

**Síntomas**:
- Costo por átomo > $0.005
- Budget mensual excedido

**Diagnóstico**:
```python
# Analizar token usage
python scripts/analyze_costs.py --groupby model

# Output:
# claude-opus: $0.003/atom (60% total)
# deepseek-70b: $0.001/atom (25% total)
# embeddings: $0.0002/atom (15% total)
```

**Soluciones**:
- Habilitar prompt caching en Claude (90% reducción)
- Reducir max_tokens en prompts
- Usar Single-LLM mode para tareas simples (threshold 0.7 → 0.5)
- Cachear embeddings de patterns

### Problema 6: Rollback a Legacy Falla

**Síntomas**:
- `USE_COGNITIVE_ARCH=false` no funciona
- Errors en legacy code

**Diagnóstico**:
```bash
# Verificar feature flags
echo $USE_COGNITIVE_ARCH
echo $COGNITIVE_ROLLOUT_PCT

# Verificar logs
tail -f logs/orchestrator.log | grep "architecture"
```

**Soluciones**:
- Verificar que `HybridOrchestrator` está activo
- Asegurar que legacy code NO fue eliminado prematuramente
- Reiniciar services: `docker-compose restart backend`

---

**© 2025 DevMatrix - Ariel E. Ghysels**
*Plan de Refactorización Cognitiva*
*Estado: READY FOR IMPLEMENTATION*
