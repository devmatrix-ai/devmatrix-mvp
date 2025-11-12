# 📋 Plan de Implementación RAG: De 38% a 98% de Precisión

**Documento**: Plan de Acción Detallado
**Fecha Inicio**: 2025-11-12
**Fecha Target**: 2025-12-10 (4 semanas)
**Owner**: Ariel (DevMatrix Team)
**Estado**: EN PROGRESO 🔄

---

## 🎯 Objetivo Principal

Elevar la precisión del sistema DevMatrix del **38% actual al 98%** mediante la correcta configuración y población del sistema RAG.

---

## 📊 Métricas Baseline (Estado Actual)

```yaml
current_metrics:
  precision_e2e: 0.38
  vector_store_population:
    devmatrix_curated: 0
    devmatrix_standards: 0
    devmatrix_project_code: 233
    devmatrix_code_examples: 2073
  retrieval_success_rate: 0.00  # 0/30 queries exitosas
  similarity_threshold: 0.70
  rag_enabled_agents: 5/5
  effective_rag_usage: 0%  # Retorna [] siempre
```

---

## 🗓️ SEMANA 1: Población y Configuración Base (38% → 65%)

### Día 1: Martes 12/11 - Población Inicial Urgente

#### ⏰ 9:00 - 10:00: Setup y Verificación
```bash
# 1. Verificar ChromaDB está corriendo
docker ps | grep chromadb
# Si no está corriendo:
docker-compose up -d chromadb

# 2. Backup actual (por seguridad)
cd /home/kwar/code/agentic-ai
mkdir -p backups/rag/2025-11-12
cp -r .cache/rag backups/rag/2025-11-12/
cp -r data/chromadb backups/rag/2025-11-12/

# 3. Verificar estado inicial
python scripts/verify_rag_quality.py > reports/rag_baseline_2025-11-12.txt
```

#### ⏰ 10:00 - 12:00: Población Masiva
```bash
# 4. Ejecutar población completa
python scripts/orchestrate_rag_population.py --source /home/kwar/code/agentic-ai/src

# 5. Seed de patrones curados (CRÍTICO)
python scripts/seed_enhanced_patterns.py \
    --collection devmatrix_curated \
    --count 1000 \
    --priority high

# 6. Seed de estándares
python scripts/seed_project_standards.py \
    --collection devmatrix_standards \
    --count 500
```

**Checkpoint 1**: Vector stores deben tener >500 ejemplos cada uno

#### ⏰ 14:00 - 16:00: Ajuste de Thresholds
```python
# 7. Modificar src/rag/retriever.py
# Línea ~45
DEFAULT_MIN_SIMILARITY = 0.5  # Cambiar de 0.7 a 0.5

# 8. Modificar src/rag/multi_collection_manager.py
# Líneas ~67-85
COLLECTION_CONFIGS = {
    "devmatrix_curated": {
        "threshold": 0.55,    # Reducir de 0.75
        "weight": 1.2,
        "min_results": 2
    },
    "devmatrix_project_code": {
        "threshold": 0.45,    # Reducir de 0.65
        "weight": 1.0,
        "min_results": 3
    },
    "devmatrix_standards": {
        "threshold": 0.50,    # Reducir de 0.70
        "weight": 1.1,
        "min_results": 2
    }
}
```

#### ⏰ 16:00 - 17:00: Validación Día 1
```bash
# 9. Verificar mejora
python scripts/verify_rag_quality.py > reports/rag_day1_results.txt

# 10. Test específico de retrieval
python -c "
from src.rag import create_retriever, create_vector_store, create_embedding_model
import asyncio

async def test():
    embedding_model = create_embedding_model()
    vector_store = create_vector_store(embedding_model)
    retriever = create_retriever(vector_store)

    queries = [
        'FastAPI authentication middleware',
        'React component with hooks',
        'TypeScript validation'
    ]

    for query in queries:
        results = await retriever.retrieve(query)
        print(f'{query}: {len(results)} results')
        if results:
            print(f'  Top similarity: {results[0].similarity:.3f}')

asyncio.run(test())
"
```

**🎯 Target Día 1**:
- Retrieval success rate > 50%
- Al menos 1000 ejemplos en curated
- Precisión: ~45%

### Día 2: Miércoles 13/11 - Población Adicional y Fine-tuning

#### ⏰ 9:00 - 11:00: Población de Documentación Oficial
```bash
# 1. Seed documentación oficial
python scripts/seed_official_docs.py \
    --frameworks "fastapi,react,typescript,nextjs" \
    --collection devmatrix_curated \
    --max-examples 500

# 2. Seed ejemplos JWT/Auth específicos
python scripts/seed_jwt_fastapi_examples.py \
    --collection devmatrix_curated \
    --focus authentication
```

#### ⏰ 11:00 - 14:00: Indexación de Repositorios GitHub
```bash
# 3. Clonar y indexar repos de alta calidad
python scripts/seed_github_repos.py \
    --repos "
        tiangolo/fastapi
        microsoft/TypeScript
        facebook/react
        vercel/next.js
    " \
    --collection devmatrix_project_code \
    --max-files-per-repo 200 \
    --file-patterns "*.py,*.ts,*.tsx,*.js,*.jsx"
```

#### ⏰ 14:00 - 16:00: Optimización de Query Expansion
```python
# 4. Modificar src/rag/query_expander.py
# Añadir más sinónimos específicos del dominio
DOMAIN_SYNONYMS = {
    "auth": ["authentication", "authorization", "JWT", "token", "login"],
    "middleware": ["interceptor", "handler", "processor", "filter"],
    "async": ["asynchronous", "await", "promise", "concurrent"],
    "component": ["widget", "module", "element", "control"],
    # ... añadir más
}
```

**🎯 Target Día 2**:
- 2000+ ejemplos en curated
- 5000+ en project_code
- Precisión: ~52%

### Día 3: Jueves 14/11 - Testing y Ajustes

#### ⏰ 9:00 - 12:00: Benchmark Completo
```bash
# 1. Ejecutar benchmark exhaustivo
python scripts/analyze_rag_quality.py \
    --test-queries 100 \
    --categories "all" \
    --output reports/rag_benchmark_day3.json

# 2. Analizar gaps
python scripts/analyze_phase4_coverage.py \
    --identify-gaps \
    --suggest-queries
```

#### ⏰ 14:00 - 17:00: Ajustes Basados en Métricas
```python
# 3. Ajustar pesos de re-ranking basado en resultados
# src/rag/retriever.py
RERANKING_WEIGHTS = {
    "similarity": 0.4,      # Ajustar según benchmark
    "recency": 0.1,
    "quality": 0.3,
    "relevance": 0.2
}

# 4. Optimizar MMR lambda
MMR_LAMBDA = 0.4  # Ajustar para balance diversity/relevance
```

**🎯 Target Día 3**:
- Retrieval success rate > 70%
- Precisión: ~58%

### Día 4: Viernes 15/11 - RAG en Planning Agent

#### ⏰ 9:00 - 14:00: Implementar RAG en Planning
```python
# 5. Modificar src/agents/planning_agent.py
# Línea ~61, cambiar constructor:
def __init__(self, api_key: str = None, enable_rag: bool = True):
    super().__init__(api_key)

    if enable_rag:
        from src.rag import create_retriever, create_vector_store, create_embedding_model
        from src.rag.context_builder import create_context_builder

        # Initialize RAG components
        self.embedding_model = create_embedding_model()
        self.vector_store = create_vector_store(self.embedding_model)
        self.retriever = create_retriever(
            self.vector_store,
            strategy="mmr",
            top_k=5,
            min_similarity=0.5
        )
        self.context_builder = create_context_builder(
            template="structured",
            max_length=4000
        )

    self.enable_rag = enable_rag

# Añadir método para usar RAG:
async def _get_planning_context(self, requirements: str) -> str:
    """Get relevant planning examples from RAG."""
    if not self.enable_rag:
        return ""

    # Search for similar masterplans
    query = f"masterplan planning: {requirements[:200]}"
    examples = await self.retriever.retrieve(query)

    if not examples:
        return ""

    # Build context
    context = self.context_builder.build_context(
        query=requirements,
        retrieved_items=examples,
        metadata={"task_type": "masterplan"}
    )

    return f"\n\n## Similar Planning Examples:\n{context}\n"

# Modificar método generate_masterplan para usar contexto:
async def generate_masterplan(self, discovery_doc: str) -> MasterPlan:
    # Get RAG context
    rag_context = await self._get_planning_context(discovery_doc)

    # Add context to prompt
    enhanced_prompt = f"{rag_context}\n\n{discovery_doc}"

    # Continue with generation...
```

#### ⏰ 14:00 - 17:00: Seed Ejemplos de MasterPlans
```bash
# 6. Crear ejemplos de masterplans de alta calidad
python -c "
import json
from pathlib import Path

# Crear ejemplos de masterplans bien estructurados
masterplan_examples = [
    {
        'id': 'mp_auth_001',
        'description': 'JWT Authentication System',
        'tasks': [
            {'name': 'Create user model', 'loc': 10, 'atomic': True},
            {'name': 'Setup JWT utilities', 'loc': 8, 'atomic': True},
            {'name': 'Create auth endpoints', 'loc': 12, 'atomic': True},
            # ... más tareas atómicas
        ],
        'quality_score': 0.95
    },
    # ... más ejemplos
]

# Guardar para seeding
Path('data/masterplan_examples.json').write_text(
    json.dumps(masterplan_examples, indent=2)
)
"

# Indexar los ejemplos
python scripts/seed_rag_examples.py \
    --input data/masterplan_examples.json \
    --collection devmatrix_curated \
    --metadata '{"task_type": "masterplan", "quality": "high"}'
```

**🎯 Target Día 4**:
- Planning con RAG funcional
- Precisión: ~62%

### Día 5: Sábado 16/11 - Validación Semana 1

#### ⏰ 10:00 - 14:00: Test End-to-End
```bash
# 1. Test completo del pipeline
python tests/e2e/test_mge_v2_with_rag.py \
    --discovery-samples 5 \
    --measure-precision \
    --output reports/week1_e2e_results.json

# 2. Comparar con baseline
python scripts/compare_metrics.py \
    --baseline reports/rag_baseline_2025-11-12.txt \
    --current reports/week1_e2e_results.json
```

**🎯 Target Semana 1 Completado**:
- Precisión: 65% ✅
- Vector stores poblados ✅
- RAG en Planning ✅

---

## 🗓️ SEMANA 2: RAG en Atomización (65% → 75%)

### Día 6-7: Lunes-Martes 18-19/11 - Context-Aware Atomization

#### Crear nuevo módulo de atomización con RAG
```python
# Crear src/mge/v2/atomization/context_aware_atomizer.py
"""
Context-Aware Atomizer usando RAG para guiar la atomización.
"""
from typing import List, Dict, Any
from src.rag import create_retriever, create_vector_store, create_embedding_model
from src.models.atom import Atom

class ContextAwareAtomizer:
    def __init__(self, enable_rag: bool = True):
        self.enable_rag = enable_rag

        if enable_rag:
            self.embedding_model = create_embedding_model()
            self.vector_store = create_vector_store(self.embedding_model)
            self.retriever = create_retriever(
                self.vector_store,
                strategy="similarity",  # Queremos ejemplos más similares
                top_k=10,
                min_similarity=0.6
            )

    async def atomize_with_examples(self, code: str, task_description: str) -> List[Atom]:
        """Atomiza código usando ejemplos del RAG."""

        if not self.enable_rag:
            return self._default_atomization(code)

        # Buscar ejemplos de atomización exitosa
        query = f"atomize code 10 LOC: {task_description[:100]}"
        examples = await self.retriever.retrieve(
            query,
            filters={
                "metadata.atom_size": {"$lte": 15},
                "metadata.atom_quality": {"$gte": 0.9}
            }
        )

        # Analizar patrones de atomización en ejemplos
        patterns = self._extract_atomization_patterns(examples)

        # Aplicar patrones al código actual
        atoms = self._apply_patterns(code, patterns)

        # Validar cada átomo
        validated_atoms = self._validate_atoms(atoms, examples)

        return validated_atoms

    def _extract_atomization_patterns(self, examples) -> Dict[str, Any]:
        """Extrae patrones comunes de atomización."""
        patterns = {
            "avg_lines": 0,
            "max_lines": 15,
            "min_lines": 5,
            "split_points": [],  # Donde típicamente se divide
            "atomic_indicators": []  # Qué hace algo atómico
        }

        for example in examples:
            # Analizar estructura del ejemplo
            lines = example.code.split('\n')
            patterns["avg_lines"] += len(lines)

            # Identificar puntos de división comunes
            if "class " in example.code:
                patterns["split_points"].append("class_definition")
            if "def " in example.code:
                patterns["split_points"].append("function_definition")
            if "if __name__" in example.code:
                patterns["split_points"].append("main_block")

        patterns["avg_lines"] /= len(examples) if examples else 10
        return patterns

    def _apply_patterns(self, code: str, patterns: Dict) -> List[Atom]:
        """Aplica patrones de atomización al código."""
        atoms = []
        lines = code.split('\n')
        current_atom_lines = []

        for i, line in enumerate(lines):
            current_atom_lines.append(line)

            # Verificar si debemos crear un átomo
            should_split = (
                len(current_atom_lines) >= patterns["avg_lines"] or
                self._is_natural_boundary(line, patterns["split_points"])
            )

            if should_split and current_atom_lines:
                atom = Atom(
                    code='\n'.join(current_atom_lines),
                    line_count=len(current_atom_lines),
                    confidence=0.0  # Se calculará en validación
                )
                atoms.append(atom)
                current_atom_lines = []

        # Añadir último átomo si queda código
        if current_atom_lines:
            atoms.append(Atom(
                code='\n'.join(current_atom_lines),
                line_count=len(current_atom_lines)
            ))

        return atoms

    def _validate_atoms(self, atoms: List[Atom], examples) -> List[Atom]:
        """Valida y ajusta la confianza de cada átomo."""
        for atom in atoms:
            # Calcular confianza basada en similitud con ejemplos
            atom.confidence = self._calculate_confidence(atom, examples)

            # Rechazar átomos de baja calidad
            if atom.confidence < 0.6:
                # Intentar re-atomizar
                sub_atoms = self._re_atomize(atom)
                atoms.extend(sub_atoms)
                atoms.remove(atom)

        return atoms
```

#### Integrar con el pipeline existente
```python
# Modificar src/mge/v2/services/atomization_service.py
# Línea ~50
from src.mge.v2.atomization.context_aware_atomizer import ContextAwareAtomizer

class AtomizationService:
    def __init__(self):
        # Añadir context-aware atomizer
        self.context_atomizer = ContextAwareAtomizer(enable_rag=True)

    async def atomize_code(self, code: str, task_description: str) -> List[Atom]:
        # Usar el nuevo atomizer con RAG
        atoms = await self.context_atomizer.atomize_with_examples(
            code,
            task_description
        )
        return atoms
```

**🎯 Target Día 6-7**:
- Context-aware atomization implementado
- Precisión: ~70%

### Día 8-10: Miércoles-Viernes 20-22/11 - Optimización y Testing

#### Seed de ejemplos atómicos perfectos
```bash
# Crear dataset de átomos ideales
python scripts/create_atomic_examples.py \
    --source "src/" \
    --output data/atomic_examples.json \
    --max-lines 15 \
    --min-lines 5 \
    --quality-threshold 0.9

# Indexar en RAG
python scripts/seed_rag_examples.py \
    --input data/atomic_examples.json \
    --collection devmatrix_curated \
    --metadata '{"task_type": "atomization", "atom_quality": "high"}'
```

**🎯 Target Semana 2 Completado**:
- Atomización con RAG ✅
- Precisión: 75% ✅

---

## 🗓️ SEMANA 3: Validación Proactiva con RAG (75% → 85%)

### Día 11-13: Lunes-Miércoles 25-27/11 - RAG Validator

#### Implementar validador proactivo
```python
# Crear src/mge/v2/validation/rag_validator.py
"""
Validador proactivo que usa RAG para prevenir errores.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.rag import create_retriever

@dataclass
class ValidationIssue:
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: Optional[str] = None
    confidence: float = 0.0

@dataclass
class ValidationResult:
    passed: bool
    issues: List[ValidationIssue]
    suggestions: List[str]
    confidence: float

class RAGValidator:
    def __init__(self, enable_rag: bool = True):
        self.enable_rag = enable_rag

        if enable_rag:
            from src.rag import create_retriever, create_vector_store, create_embedding_model

            self.embedding_model = create_embedding_model()
            self.vector_store = create_vector_store(self.embedding_model)
            self.retriever = create_retriever(
                self.vector_store,
                strategy="mmr",
                top_k=10,
                min_similarity=0.6
            )

    async def validate_before_generation(
        self,
        spec: str,
        code: Optional[str] = None
    ) -> ValidationResult:
        """Valida proactivamente antes de generar código."""

        if not self.enable_rag:
            return ValidationResult(
                passed=True,
                issues=[],
                suggestions=[],
                confidence=0.5
            )

        # Buscar especificaciones similares que tuvieron problemas
        problem_examples = await self.retriever.retrieve(
            f"validation failed: {spec[:200]}",
            filters={"metadata.validation_passed": False}
        )

        # Buscar especificaciones similares exitosas
        success_examples = await self.retriever.retrieve(
            f"validation passed: {spec[:200]}",
            filters={"metadata.validation_passed": True}
        )

        # Analizar patrones de fallo
        issues = self._identify_potential_issues(spec, problem_examples)

        # Generar sugerencias basadas en éxitos
        suggestions = self._generate_suggestions(spec, success_examples)

        # Calcular confianza
        confidence = self._calculate_validation_confidence(
            spec,
            problem_examples,
            success_examples
        )

        passed = len([i for i in issues if i.severity == "error"]) == 0

        return ValidationResult(
            passed=passed,
            issues=issues,
            suggestions=suggestions,
            confidence=confidence
        )

    def _identify_potential_issues(
        self,
        spec: str,
        problem_examples
    ) -> List[ValidationIssue]:
        """Identifica problemas potenciales basado en ejemplos."""
        issues = []

        # Patrones comunes de problemas
        problem_patterns = {
            "missing_error_handling": {
                "indicator": "try/except" not in spec and "error" in spec.lower(),
                "message": "Specification lacks error handling details",
                "severity": "warning",
                "suggestion": "Add error handling requirements"
            },
            "ambiguous_requirements": {
                "indicator": any(word in spec.lower() for word in ["maybe", "possibly", "might"]),
                "message": "Requirements contain ambiguous language",
                "severity": "warning",
                "suggestion": "Clarify ambiguous requirements"
            },
            "missing_validation": {
                "indicator": "validation" not in spec.lower() and "input" in spec.lower(),
                "message": "Input validation not specified",
                "severity": "warning",
                "suggestion": "Add input validation requirements"
            },
            "no_tests_specified": {
                "indicator": "test" not in spec.lower(),
                "message": "No test requirements specified",
                "severity": "info",
                "suggestion": "Consider adding test requirements"
            }
        }

        for pattern_name, pattern_config in problem_patterns.items():
            if pattern_config["indicator"]:
                issues.append(ValidationIssue(
                    severity=pattern_config["severity"],
                    message=pattern_config["message"],
                    suggestion=pattern_config["suggestion"],
                    confidence=0.7
                ))

        # Analizar ejemplos problemáticos similares
        for example in problem_examples[:3]:
            if hasattr(example, 'metadata') and 'failure_reason' in example.metadata:
                issues.append(ValidationIssue(
                    severity="warning",
                    message=f"Similar spec failed with: {example.metadata['failure_reason']}",
                    suggestion="Review and address similar issue",
                    confidence=example.similarity
                ))

        return issues

    def _generate_suggestions(self, spec: str, success_examples) -> List[str]:
        """Genera sugerencias basadas en ejemplos exitosos."""
        suggestions = []

        # Extraer patrones de éxito
        success_patterns = set()
        for example in success_examples[:5]:
            if hasattr(example, 'metadata'):
                if 'success_factors' in example.metadata:
                    success_patterns.update(example.metadata['success_factors'])

        # Convertir patrones en sugerencias
        pattern_suggestions = {
            "clear_interfaces": "Define clear interfaces between components",
            "error_handling": "Include comprehensive error handling",
            "input_validation": "Validate all inputs at entry points",
            "test_coverage": "Specify test coverage requirements",
            "performance_metrics": "Define performance metrics and thresholds",
            "security_considerations": "Address security requirements",
            "documentation": "Include documentation requirements"
        }

        for pattern in success_patterns:
            if pattern in pattern_suggestions:
                suggestions.append(pattern_suggestions[pattern])

        # Añadir sugerencias específicas basadas en el spec
        if "api" in spec.lower():
            suggestions.append("Include API versioning strategy")
            suggestions.append("Define rate limiting requirements")

        if "database" in spec.lower():
            suggestions.append("Specify transaction handling")
            suggestions.append("Define data consistency requirements")

        return suggestions[:5]  # Limitar a 5 sugerencias más relevantes

    async def validate_after_generation(
        self,
        code: str,
        spec: str
    ) -> ValidationResult:
        """Valida código generado contra especificación."""

        # Buscar código similar validado
        validated_code = await self.retriever.retrieve(
            f"validated code: {code[:200]}",
            filters={"metadata.validation_passed": True}
        )

        issues = []

        # Verificaciones básicas
        if len(code.split('\n')) > 500:
            issues.append(ValidationIssue(
                severity="warning",
                message="Code exceeds 500 lines, consider splitting",
                suggestion="Break into smaller components"
            ))

        # Comparar con ejemplos validados
        if not validated_code:
            issues.append(ValidationIssue(
                severity="info",
                message="No similar validated code found",
                suggestion="Manual review recommended"
            ))

        return ValidationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            suggestions=[],
            confidence=0.7
        )
```

#### Integrar validador en el pipeline
```python
# Modificar src/mge/v2/services/validation_service.py
from src.mge.v2.validation.rag_validator import RAGValidator

class ValidationService:
    def __init__(self):
        self.rag_validator = RAGValidator(enable_rag=True)

    async def validate_before_generation(self, spec: str):
        # Validación proactiva con RAG
        result = await self.rag_validator.validate_before_generation(spec)

        if not result.passed:
            # Log issues
            for issue in result.issues:
                logger.warning(f"Validation issue: {issue.message}")

            # Aplicar sugerencias automáticamente si es posible
            if result.suggestions:
                spec = self._apply_suggestions(spec, result.suggestions)

        return spec, result
```

**🎯 Target Semana 3 Completado**:
- Validación proactiva con RAG ✅
- Precisión: 85% ✅

---

## 🗓️ SEMANA 4: Optimización Final (85% → 98%)

### Día 14-16: Lunes-Miércoles 2-4/12 - Fine-tuning

#### Hyperparameter Optimization
```bash
# 1. Ejecutar optimización automática de hiperparámetros
python scripts/tune_rag_hyperparameters.py \
    --target-precision 0.98 \
    --max-iterations 100 \
    --parameters "
        similarity_threshold: [0.4, 0.5, 0.6, 0.7]
        mmr_lambda: [0.3, 0.35, 0.4, 0.45, 0.5]
        top_k: [3, 5, 7, 10]
        reranking_weights: optimize
        query_expansion_count: [3, 5, 7]
    " \
    --output config/optimal_rag_params.json

# 2. Aplicar parámetros óptimos
python scripts/apply_rag_config.py \
    --config config/optimal_rag_params.json \
    --restart-services
```

#### Test-Driven RAG Enhancement
```python
# Crear src/agents/testing_agent_enhanced.py
# Añadir RAG para generación de tests

async def generate_tests_with_rag(self, code: str, spec: str):
    """Genera tests usando ejemplos del RAG."""

    # Buscar tests similares exitosos
    test_examples = await self.retriever.retrieve(
        f"test for: {spec[:200]}",
        filters={
            "metadata.test_type": "unit",
            "metadata.test_quality": {"$gte": 0.9}
        }
    )

    # Generar tests basados en ejemplos
    tests = self._generate_from_examples(code, test_examples)

    return tests
```

### Día 17-18: Jueves-Viernes 5-6/12 - Testing Intensivo

#### Ejecutar batería completa de tests
```bash
# 1. Test E2E con métricas detalladas
python tests/e2e/test_full_mge_v2_pipeline.py \
    --with-rag \
    --measure-all-metrics \
    --iterations 10 \
    --output reports/final_precision_test.json

# 2. Benchmark contra diferentes tipos de proyectos
python scripts/benchmark_project_types.py \
    --types "api,frontend,fullstack,cli,library" \
    --complexity "simple,medium,complex" \
    --measure-precision
```

### Día 19-20: Sábado-Domingo 7-8/12 - Documentación y Monitoreo

#### Setup de monitoreo continuo
```python
# Crear scripts/monitor_rag_performance.py
"""
Monitor continuo de performance del RAG.
"""
import time
import json
from datetime import datetime
from pathlib import Path

class RAGMonitor:
    def __init__(self):
        self.metrics_file = Path("metrics/rag_performance.json")

    def collect_metrics(self):
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "precision": self.measure_precision(),
            "retrieval_success_rate": self.measure_retrieval(),
            "latency_p50": self.measure_latency(0.5),
            "latency_p95": self.measure_latency(0.95),
            "vector_store_size": self.get_vector_store_size(),
            "cache_hit_rate": self.get_cache_hit_rate()
        }

        # Alertas si cae la precisión
        if metrics["precision"] < 0.95:
            self.send_alert(f"Precision dropped to {metrics['precision']:.2%}")

        return metrics

    def run_continuous(self, interval_minutes=30):
        while True:
            metrics = self.collect_metrics()
            self.save_metrics(metrics)
            time.sleep(interval_minutes * 60)

# Ejecutar monitor
monitor = RAGMonitor()
monitor.run_continuous()
```

#### Dashboard de métricas
```bash
# Generar dashboard HTML
python scripts/generate_rag_dashboard.py \
    --input metrics/rag_performance.json \
    --output dashboard/rag_metrics.html \
    --auto-refresh 60
```

### Día 21: Lunes 9/12 - Validación Final

#### Test de aceptación final
```bash
# Ejecutar validación completa
python scripts/final_validation.py \
    --target-precision 0.98 \
    --test-cases 50 \
    --categories "all"
```

**🎯 Target Final Alcanzado**:
- Precisión: 98% ✅
- Sistema monitoreado ✅
- Documentación completa ✅

---

## 📈 Métricas de Seguimiento

### Dashboard de Progreso

| Semana | Fecha | Target | Actual | Estado | Tareas Clave |
|--------|-------|--------|--------|--------|--------------|
| 1 | 12-17/11 | 65% | - | 🔄 | Población + Config |
| 2 | 18-24/11 | 75% | - | ⏳ | RAG Atomización |
| 3 | 25/11-1/12 | 85% | - | ⏳ | Validación Proactiva |
| 4 | 2-10/12 | 98% | - | ⏳ | Optimización Final |

### KPIs Diarios

```yaml
daily_metrics:
  - retrieval_success_rate
  - avg_similarity_score
  - precision_e2e
  - atomization_success_rate
  - validation_accuracy
  - generation_time
  - cost_per_generation
```

---

## 🛠️ Scripts de Automatización

### Script Master de Ejecución Diaria
```bash
#!/bin/bash
# daily_rag_maintenance.sh

echo "🔄 DevMatrix RAG Daily Maintenance"
date

# 1. Verificar servicios
echo "Checking services..."
docker ps | grep chromadb || docker-compose up -d chromadb

# 2. Ejecutar población incremental
echo "Incremental population..."
python scripts/maintain_rag_quality.py --incremental

# 3. Verificar calidad
echo "Quality check..."
python scripts/verify_rag_quality.py --quick

# 4. Generar reporte
echo "Generating report..."
python scripts/generate_daily_report.py

# 5. Backup
echo "Backing up..."
./scripts/backup_rag.sh

echo "✅ Daily maintenance complete"
```

### Script de Validación Rápida
```python
#!/usr/bin/env python3
# quick_validate.py

import asyncio
from src.rag import create_retriever, create_vector_store, create_embedding_model

async def quick_validation():
    """Validación rápida del estado del RAG."""

    # Initialize
    embedding_model = create_embedding_model()
    vector_store = create_vector_store(embedding_model)
    retriever = create_retriever(vector_store)

    # Test queries
    test_queries = [
        "FastAPI middleware",
        "React hooks",
        "TypeScript types",
        "Async Python",
        "JWT authentication"
    ]

    success = 0
    for query in test_queries:
        results = await retriever.retrieve(query)
        if results:
            success += 1
            print(f"✅ {query}: {len(results)} results")
        else:
            print(f"❌ {query}: No results")

    success_rate = success / len(test_queries)
    print(f"\n📊 Success Rate: {success_rate:.1%}")

    if success_rate < 0.8:
        print("⚠️ WARNING: RAG performance degraded!")
        print("Run: python scripts/orchestrate_rag_population.py")

    return success_rate

if __name__ == "__main__":
    rate = asyncio.run(quick_validation())
    exit(0 if rate >= 0.8 else 1)
```

---

## 🚨 Plan de Contingencia

### Si la precisión no mejora:

#### Diagnóstico Nivel 1
```bash
# 1. Verificar vector stores
python -c "
from src.rag import create_vector_store, create_embedding_model
em = create_embedding_model()
vs = create_vector_store(em)
for collection in vs.list_collections():
    print(f'{collection}: {vs.get_collection_size(collection)} items')
"

# 2. Test retrieval directo
python scripts/test_retrieval_direct.py --verbose
```

#### Diagnóstico Nivel 2
```bash
# 3. Analizar calidad de embeddings
python scripts/analyze_embedding_quality.py \
    --sample-size 100 \
    --visualize

# 4. Verificar similitud entre queries y documentos
python scripts/analyze_similarity_distribution.py
```

#### Acciones Correctivas

1. **Si retrieval falla** (< 50% success):
   - Reducir threshold a 0.4
   - Aumentar top_k a 10
   - Re-indexar con diferentes embeddings

2. **Si atomización falla**:
   - Aumentar ejemplos de atomización
   - Ajustar patterns de división
   - Implementar fallback manual

3. **Si validación falla**:
   - Relajar criterios temporalmente
   - Aumentar ejemplos de validación
   - Implementar human-in-the-loop

---

## 📝 Checklist de Implementación

### Semana 1 ✅
- [ ] Backup del estado actual
- [ ] Ejecutar orchestrate_rag_population.py
- [ ] Seed enhanced patterns (1000+)
- [ ] Seed project standards (500+)
- [ ] Reducir thresholds (0.5)
- [ ] Implementar RAG en Planning
- [ ] Validar mejora (>65%)

### Semana 2 ⏳
- [ ] Implementar ContextAwareAtomizer
- [ ] Integrar con AtomizationService
- [ ] Seed atomic examples
- [ ] Test atomización mejorada
- [ ] Validar mejora (>75%)

### Semana 3 ⏳
- [ ] Implementar RAGValidator
- [ ] Validación proactiva
- [ ] Integrar con pipeline
- [ ] Test validación
- [ ] Validar mejora (>85%)

### Semana 4 ⏳
- [ ] Hyperparameter tuning
- [ ] Test-driven RAG
- [ ] Monitoreo continuo
- [ ] Dashboard métricas
- [ ] Validación final (>98%)

---

## 📞 Puntos de Contacto y Escalación

### Responsables
- **Owner Principal**: Ariel (DevMatrix Team)
- **RAG Expert**: [Asignar]
- **QA Lead**: [Asignar]

### Escalación
1. **Nivel 1**: Problemas de configuración → Scripts automatizados
2. **Nivel 2**: Falla de población → Re-ejecutar orchestrate
3. **Nivel 3**: Degradación de precisión → Análisis profundo + rollback

---

## 🎯 Criterios de Éxito Final

```yaml
final_acceptance_criteria:
  precision_e2e: ≥ 0.98
  retrieval_success: ≥ 0.95
  atomization_quality: ≥ 0.95
  validation_accuracy: ≥ 0.90
  latency_p95: ≤ 500ms
  cost_per_generation: ≤ $0.10

  vector_stores:
    devmatrix_curated: ≥ 1000
    devmatrix_standards: ≥ 500
    devmatrix_project_code: ≥ 5000

  monitoring:
    dashboard: active
    alerts: configured
    backup: automated
```

---

**Firma**: Plan aprobado y listo para ejecución
**Fecha**: 2025-11-12
**Próxima Revisión**: 2025-11-17 (fin semana 1)