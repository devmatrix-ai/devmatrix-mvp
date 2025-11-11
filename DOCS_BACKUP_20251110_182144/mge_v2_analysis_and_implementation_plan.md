# MGE V2: Análisis Completo y Plan de Implementación

**Fecha:** 2025-11-10
**Versión:** 1.0
**Estado:** Ready for Implementation

---

## 📋 TABLA DE CONTENIDOS

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis del Flujo Completo](#análisis-del-flujo-completo)
3. [Gaps e Issues Críticos](#gaps-e-issues-críticos)
4. [Plan de Implementación](#plan-de-implementación)
5. [Arquitectura de Servicios](#arquitectura-de-servicios)
6. [Especificaciones Técnicas](#especificaciones-técnicas)
7. [Testing y Validación](#testing-y-validación)
8. [Métricas y Performance](#métricas-y-performance)

---

## 🎯 RESUMEN EJECUTIVO

### Estado Actual
MGE V2 tiene **85% de implementación completa** con 7 fases operacionales:
- ✅ Discovery (DDD Analysis)
- ✅ MasterPlan Generation (120 tasks)
- ✅ Code Generation (LLM-based)
- ❌ **Atomization (CRÍTICO - vacío)**
- ⚠️ Wave Execution (simplista)
- ✅ File Writing (funcional)
- ✅ Infrastructure Generation (funcional)

### Gaps Críticos Identificados
1. **AtomService.decompose_task()** - No implementado (bloquea pipeline)
2. **Dependency Graph** - Execution no respeta dependencies
3. **Code Validation** - No hay validation antes de escribir archivos
4. **File Path Resolution** - Lógica débil genera paths incorrectos
5. **Templates Infrastructure** - Hardcoded en lugar de Jinja2
6. **Cost Tracking** - No se agrega correctamente al MasterPlan

### Tiempo de Implementación Estimado
- **Alta Prioridad (crítico):** 3-4 días
- **Media Prioridad (calidad):** 2-3 días
- **Baja Prioridad (optimizaciones):** 2 días

**Total:** ~7-9 días para MGE V2 100% funcional

---

## 🔄 ANÁLISIS DEL FLUJO COMPLETO

### 1. User Interaction → Backend

**Frontend:** `src/ui/src/components/chat/ChatInterface.tsx`
```typescript
// User envía mensaje via Socket.IO
wsService.send('send_message', {
  conversation_id: currentConversationId,
  content: userMessage,
  metadata: { sid: socket.id }
})
```

**Backend Router:** `src/api/routers/websocket.py:240-322`
```python
@sio.event
async def send_message(sid, data):
    """
    Detecta keywords de implementación:
    - Direct: "crear", "implementar", "generar"
    - Ready: "si a todo", "vamos", "dale"
    - Detailed: >30 words + tech keywords
    """
    if is_direct_implementation:
        async for chunk in chat_service.send_message(...):
            await sio.emit('message', chunk, room=f"chat_{conversation_id}")
```

### 2. Chat Service Decision Tree

**File:** `src/services/chat_service.py:559-611`

```
Message
  ├─ is_direct_implementation? (keyword detection)
  │  ├─ YES → _execute_orchestration() [MGE V2]
  │  └─ NO  → _handle_conversational() [LLM chat]
  │
  └─ MGE_V2_ENABLED env var check
     ├─ TRUE  → _execute_mge_v2()
     └─ FALSE → _execute_legacy_orchestration() [V1]
```

### 3. MGE V2 Pipeline (7 Fases)

**Orchestration Service:** `src/services/mge_v2_orchestration_service.py`

```python
async def orchestrate_from_request(user_request, workspace_id, session_id, user_id):
    """
    FASE 1: Discovery (DDD Analysis)
    ================================
    - Analiza request con LLM
    - Extrae: domain, bounded contexts, aggregates, entities
    - WebSocket: discovery_generation_start, discovery_tokens_progress
    - Output: DiscoveryDocument (DB)
    - Tiempo: ~30s, Costo: ~$0.09
    """
    discovery_service = DiscoveryService(db, llm_client)
    discovery_id = await discovery_service.generate_discovery(user_request, session_id, user_id)

    """
    FASE 2: MasterPlan Generation (120 tasks)
    ==========================================
    - Genera plan jerárquico desde Discovery
    - Estructura: Phases (5-7) → Milestones (15-20) → Tasks (120)
    - WebSocket: masterplan_generation_start, masterplan_tokens_progress
    - Output: MasterPlan + MasterPlanTask[] (DB)
    - Tiempo: ~90s, Costo: ~$0.30
    """
    masterplan_generator = MasterPlanGenerator(llm_client, use_rag=True)
    masterplan_id = await masterplan_generator.generate_masterplan(discovery_id, session_id, user_id)
    tasks = db.query(MasterPlanTask).filter(MasterPlanTask.masterplan_id == masterplan_id).all()

    """
    FASE 3: Code Generation (LLM)
    ==============================
    - Genera código Python/TS para cada task
    - Prompts: task description + tech stack + best practices
    - Parallel: 5 tasks concurrently (batching)
    - Output: task.llm_response (código en DB)
    - Tiempo: ~300s (120 tasks × 2.5s), Costo: ~$6.00
    """
    code_gen_service = CodeGenerationService(db, llm_client)
    for batch in chunks(tasks, batch_size=5):
        results = await asyncio.gather(*[
            code_gen_service.generate_code_for_task(task.task_id)
            for task in batch
        ])

    """
    FASE 4: Atomization (code → atoms)
    ===================================
    ❌ CRÍTICO: NO IMPLEMENTADO
    - Parser de código generado en chunks de 10 LOC
    - Dependency analysis entre atoms
    - Output: AtomicUnit[] (DB)
    - Tiempo estimado: ~60s
    """
    for task in tasks:
        atoms = atom_service.decompose_task(task.task_id)  # ❌ VACÍO

    """
    FASE 5: Wave Execution (parallel atoms)
    ========================================
    ⚠️ SIMPLISTA: No respeta dependencies
    - Agrupa atoms en waves de 10
    - Ejecuta waves secuencialmente
    - Output: ExecutionResult (DB)
    - Tiempo: ~180s (8 waves × 22.5s)
    """
    execution_plan = create_waves(all_atoms, wave_size=10)  # ⚠️ No usa dependency graph
    execution_id = await execution_service.start_execution(masterplan_id, execution_plan)

    """
    FASE 6: File Writing (atoms → workspace)
    =========================================
    - Agrupa atoms por file path
    - Merge atoms en archivos completos
    - Escribe a /tmp/mge_v2_workspace/{masterplan_id}/{project_name}/
    - Output: Proyecto en filesystem
    - Tiempo: ~5s
    """
    file_writer = FileWriterService(db)
    write_result = await file_writer.write_atoms_to_files(masterplan_id)

    """
    FASE 7: Infrastructure Generation
    ==================================
    - Detecta project type (FastAPI, Express, React)
    - Genera configs: Dockerfile, docker-compose, .env, requirements.txt, README
    - Templates: Jinja2 (o hardcoded fallback)
    - Output: Proyecto ejecutable completo
    - Tiempo: ~2s
    """
    infra_service = InfrastructureGenerationService(db)
    infra_result = await infra_service.generate_infrastructure(masterplan_id, workspace_path)
```

### 4. Frontend Progress Tracking

**Hook:** `src/ui/src/hooks/useMasterPlanProgress.ts`

```typescript
export function useMasterPlanProgress(sessionId?: string) {
  const { events } = useWebSocketContext()

  // Filter events by session_id (discovery y masterplan usan mismo session_id)
  const sessionEvents = events.filter(e =>
    e.sessionId === sessionId || e.data?.session_id === sessionId
  )

  // Process events chronologically (catch-up mechanism)
  sessionEvents.sort((a, b) => a.timestamp - b.timestamp).forEach(event => {
    switch(event.type) {
      case 'discovery_generation_start':
        updatePhaseStatus('discovery', 'in_progress')
        setProgressState({ currentPhase: 'Generating', percentage: 0 })
        break

      case 'discovery_tokens_progress':
        const percentage = (event.data.tokens_received / event.data.estimated_total) * 100
        setProgressState({ tokensReceived, percentage })
        break

      case 'discovery_entity_discovered':
        // Incrementa: boundedContexts, aggregates, entities
        break

      case 'masterplan_generation_start':
        setProgressState({ percentage: 30 }) // Discovery = 30%
        break

      case 'masterplan_tokens_progress':
        // Continúa progreso desde 30%
        break

      case 'masterplan_entity_discovered':
        // Incrementa: phases, milestones, tasks
        break

      case 'masterplan_generation_complete':
        setProgressState({ percentage: 100, isComplete: true })
        break
    }
  })
}
```

**Modal:** `src/ui/src/components/chat/MasterPlanProgressModal.tsx`

```typescript
<MasterPlanProgressModal open={modalOpen} sessionId={sessionId}>
  {/* Timeline visual con 9 fases */}
  <ProgressTimeline
    phases={[
      { name: 'discovery', status: 'completed', icon: '📡' },
      { name: 'parsing', status: 'in_progress', icon: '📝' },
      { name: 'validation', status: 'pending', icon: '✓' },
      // ... 6 more phases
    ]}
    currentPhase={progressState.currentPhase}
  />

  {/* Métricas en tiempo real */}
  <ProgressMetrics
    tokensUsed={progressState.tokensReceived}
    cost={progressState.cost}
    duration={progressState.elapsedSeconds}
    entities={{
      boundedContexts: 3,
      aggregates: 12,
      tasks: 120
    }}
  />

  {/* Summary final */}
  {isComplete && (
    <FinalSummary
      stats={progressState}
      onViewDetails={() => navigate(`/masterplans/${masterplanId}`)}
      onStartExecution={() => navigate(`/execution/${masterplanId}`)}
    />
  )}
</MasterPlanProgressModal>
```

---

## 🚨 GAPS E ISSUES CRÍTICOS

### 1. ❌ AtomService.decompose_task() NO IMPLEMENTADO

**Severidad:** 🔴 CRÍTICA (bloquea pipeline completo)

**Ubicación:** `src/services/atom_service.py` (service exists but method is stub)

**Problema:**
```python
class AtomService:
    def decompose_task(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        ❌ TODO: Implement atomization logic
        - Parse task.llm_response (generated code)
        - Split into 10 LOC chunks (atoms)
        - Analyze dependencies between atoms
        - Create AtomicUnit records in DB
        """
        pass  # ❌ NOT IMPLEMENTED!
```

**Impacto:**
- Code generation funciona ✅
- Pero atomization retorna 0 atoms ❌
- Pipeline detecta 0 atoms y skippea execution ❌
- Archivos NO se generan ❌

**Causa Raíz:**
Service creado como stub, nunca se implementó la lógica de parsing y chunking.

---

### 2. ⚠️ Wave Execution Sin Dependency Graph

**Severidad:** 🟡 MEDIA (funciona pero incorrectamente)

**Ubicación:** `src/services/mge_v2_orchestration_service.py:282-306`

**Problema:**
```python
# ⚠️ Execution plan simplista (NO usa dependency graph)
execution_plan = []
wave_size = 10
for i in range(0, len(all_atoms), wave_size):
    wave_atoms = all_atoms[i:i + wave_size]
    execution_plan.append({
        "wave_number": len(execution_plan) + 1,
        "atom_ids": [str(atom.atom_id) for atom in wave_atoms]
    })
```

**Impacto:**
- Atoms se ejecutan sin respetar dependencies
- Atom B puede ejecutarse antes que Atom A (del cual depende)
- Runtime errors por imports/funciones faltantes
- Baja precisión en ejecución

**Solución Necesaria:**
Usar NetworkX para topological sort y wave assignment respetando dependencies.

---

### 3. ⚠️ Code Validation Ausente

**Severidad:** 🟡 MEDIA (calidad del código)

**Ubicación:** `src/services/mge_v2_orchestration_service.py` (validation step missing)

**Problema:**
```python
# Code generation → File writing (sin validation intermedia)
code_gen_service.generate_code_for_task(task.task_id)
# ⚠️ NO VALIDATION HERE
file_writer.write_atoms_to_files(masterplan_id)
```

**Impacto:**
- Código con syntax errors se escribe a archivos
- Imports incorrectos no se detectan
- Type errors no se validan
- Baja calidad del código generado

**Solución Necesaria:**
Agregar validation step usando AST parsing, import checking, y type validation.

---

### 4. ⚠️ File Path Resolution Débil

**Severidad:** 🟡 MEDIA (organización del código)

**Ubicación:** `src/services/file_writer_service.py:217-260`

**Problema:**
```python
def _get_atom_file_path(self, atom: AtomicUnit) -> str:
    # Fallback simplista basado en keywords
    if 'model' in task_name:
        return f"src/models/{filename}"
    elif 'service' in task_name:
        return f"src/services/{filename}"
    else:
        return f"src/atom_{atom.atom_number}.py"  # ❌ Path genérico horrible
```

**Impacto:**
- Archivos en paths incorrectos
- Nombres como "atom_123.py" sin significado
- Estructura de proyecto desorganizada
- Dificulta navegación del código

**Solución Necesaria:**
Parse imports y class definitions del código generado para inferir paths correctos.

---

### 5. ⚠️ Templates Infrastructure Hardcoded

**Severidad:** 🟢 BAJA (funcional pero no flexible)

**Ubicación:** `src/services/infrastructure_generation_service.py:360-482`

**Problema:**
```python
def _generate_dockerfile(self, project_type, metadata):
    template_name = f"docker/python_{project_type}.dockerfile"
    try:
        template = self.jinja_env.get_template(template_name)
        return template.render(**metadata)
    except Exception:
        # ⚠️ Fallback a template hardcoded
        return f"""FROM python:3.11-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        EXPOSE {metadata['app_port']}
        CMD ["uvicorn", "src.main:app"]
        """
```

**Impacto:**
- Templates no existen en `templates/` directory
- Usa fallback hardcoded (menos flexible)
- Difícil personalizar para diferentes project types

**Solución Necesaria:**
Crear `templates/` directory con templates Jinja2 reales.

---

### 6. ⚠️ Cost Tracking Incompleto

**Severidad:** 🟢 BAJA (métrica, no funcional)

**Ubicación:** `src/services/mge_v2_orchestration_service.py:179-219`

**Problema:**
```python
# Code generation calcula cost por task ✅
code_gen_service.generate_code_for_task(task.task_id)
# → task.llm_cost_usd = 0.05

# ❌ PERO cost total NO se agrega al MasterPlan
masterplan.generation_cost_usd = ???  # No se actualiza
```

**Impacto:**
- Cost individual por task registrado ✅
- Pero cost total del MasterPlan no se calcula ❌
- Métricas de costo incompletas

**Solución Necesaria:**
Sumar costs de tasks y actualizar MasterPlan.generation_cost_usd.

---

## 🛠️ PLAN DE IMPLEMENTACIÓN

### Fase 1: Fixes Críticos (Alta Prioridad - 3-4 días)

#### Task 1.1: Implementar AtomService.decompose_task()
**Prioridad:** 🔴 CRÍTICA
**Tiempo:** 2 días
**Archivo:** `src/services/atom_service.py`

**Implementación:**
```python
import ast
import re
from typing import List, Dict, Any

class AtomService:
    def decompose_task(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        Descompone código generado en atomic units de ~10 LOC.

        Steps:
        1. Load task.llm_response (generated code)
        2. Parse code with AST
        3. Split into logical chunks (functions, classes, blocks)
        4. Create AtomicUnit records with dependencies
        5. Return atomization result
        """
        # Load task
        task = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.task_id == task_id
        ).first()

        if not task or not task.llm_response:
            return {"success": False, "error": "No code to atomize"}

        code = task.llm_response

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}

        # Extract chunks (functions, classes, imports)
        chunks = self._extract_chunks(tree, code)

        # Create atoms (target 10 LOC per atom)
        atoms = []
        atom_number = 1

        for chunk in chunks:
            # Split large chunks into smaller atoms
            if chunk['lines'] > 15:
                sub_atoms = self._split_chunk(chunk, target_loc=10)
                for sub_atom in sub_atoms:
                    atom = self._create_atom(
                        task_id=task_id,
                        masterplan_id=task.masterplan_id,
                        atom_number=atom_number,
                        code=sub_atom['code'],
                        chunk_type=sub_atom['type'],
                        dependencies=sub_atom['dependencies']
                    )
                    atoms.append(atom)
                    atom_number += 1
            else:
                atom = self._create_atom(
                    task_id=task_id,
                    masterplan_id=task.masterplan_id,
                    atom_number=atom_number,
                    code=chunk['code'],
                    chunk_type=chunk['type'],
                    dependencies=chunk['dependencies']
                )
                atoms.append(atom)
                atom_number += 1

        self.db.commit()

        return {
            "success": True,
            "atoms": [str(a.atom_id) for a in atoms],
            "total_atoms": len(atoms),
            "average_loc": sum(a.code_to_generate.count('\n') for a in atoms) / len(atoms)
        }

    def _extract_chunks(self, tree: ast.AST, code: str) -> List[Dict]:
        """
        Extrae chunks lógicos del AST.

        Returns:
            List of chunks with: type, code, lines, dependencies
        """
        chunks = []

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                chunk_code = ast.get_source_segment(code, node)
                chunks.append({
                    'type': 'import',
                    'code': chunk_code,
                    'lines': chunk_code.count('\n') + 1,
                    'dependencies': [],
                    'node': node
                })

        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                chunk_code = ast.get_source_segment(code, node)
                chunks.append({
                    'type': 'function',
                    'code': chunk_code,
                    'lines': chunk_code.count('\n') + 1,
                    'dependencies': self._extract_dependencies(node),
                    'node': node
                })

        # Extract classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                chunk_code = ast.get_source_segment(code, node)
                chunks.append({
                    'type': 'class',
                    'code': chunk_code,
                    'lines': chunk_code.count('\n') + 1,
                    'dependencies': self._extract_dependencies(node),
                    'node': node
                })

        return chunks

    def _extract_dependencies(self, node: ast.AST) -> List[str]:
        """
        Extrae dependencies de un nodo AST.

        Returns:
            List of function/class names referenced
        """
        dependencies = set()

        for child in ast.walk(node):
            # Function calls
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    dependencies.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    dependencies.add(child.func.attr)

            # Variable references
            elif isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Load):
                    dependencies.add(child.id)

        return list(dependencies)

    def _split_chunk(self, chunk: Dict, target_loc: int = 10) -> List[Dict]:
        """
        Split large chunk into smaller atoms (~10 LOC each).
        """
        lines = chunk['code'].split('\n')
        sub_atoms = []

        for i in range(0, len(lines), target_loc):
            sub_code = '\n'.join(lines[i:i+target_loc])
            sub_atoms.append({
                'type': chunk['type'],
                'code': sub_code,
                'lines': len(sub_code.split('\n')),
                'dependencies': chunk['dependencies']
            })

        return sub_atoms

    def _create_atom(
        self,
        task_id: uuid.UUID,
        masterplan_id: uuid.UUID,
        atom_number: int,
        code: str,
        chunk_type: str,
        dependencies: List[str]
    ) -> AtomicUnit:
        """Create AtomicUnit record in DB."""
        from src.models import AtomicUnit, AtomType

        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            task_id=task_id,
            masterplan_id=masterplan_id,
            atom_number=atom_number,
            code_to_generate=code,
            atom_type=AtomType.FUNCTION if chunk_type == 'function' else AtomType.CLASS,
            estimated_loc=code.count('\n') + 1,
            dependencies_raw=dependencies,
            metadata={
                'chunk_type': chunk_type,
                'has_dependencies': len(dependencies) > 0
            }
        )

        self.db.add(atom)
        return atom
```

**Testing:**
```python
# tests/test_atom_service.py
def test_decompose_simple_function():
    code = '''
def hello_world():
    """Simple function."""
    print("Hello, world!")
    return True
'''
    task = create_task_with_code(code)
    result = atom_service.decompose_task(task.task_id)

    assert result['success'] == True
    assert result['total_atoms'] >= 1
    assert result['average_loc'] <= 15

def test_decompose_complex_class():
    code = '''
class UserService:
    def __init__(self, db):
        self.db = db

    def create_user(self, email, password):
        user = User(email=email, password_hash=hash(password))
        self.db.add(user)
        return user

    def get_user(self, user_id):
        return self.db.query(User).filter(User.id == user_id).first()
'''
    task = create_task_with_code(code)
    result = atom_service.decompose_task(task.task_id)

    assert result['success'] == True
    assert result['total_atoms'] >= 3  # __init__, create_user, get_user
```

---

#### Task 1.2: Implementar Dependency Graph para Wave Execution
**Prioridad:** 🔴 CRÍTICA
**Tiempo:** 1.5 días
**Archivo:** `src/services/mge_v2_orchestration_service.py`

**Implementación:**
```python
import networkx as nx
from typing import List, Dict, Any

class MGE_V2_OrchestrationService:
    def _build_dependency_graph(self, atoms: List[AtomicUnit]) -> nx.DiGraph:
        """
        Build directed graph of atom dependencies using NetworkX.

        Returns:
            NetworkX DiGraph where edges represent dependencies
        """
        G = nx.DiGraph()

        # Add all atoms as nodes
        for atom in atoms:
            G.add_node(str(atom.atom_id), atom=atom)

        # Add edges for dependencies
        for atom in atoms:
            if not atom.dependencies_raw:
                continue

            # Find atoms that define the dependencies
            for dep_name in atom.dependencies_raw:
                for other_atom in atoms:
                    # Check if other_atom defines dep_name
                    if self._atom_defines(other_atom, dep_name):
                        # other_atom must execute before atom
                        G.add_edge(str(other_atom.atom_id), str(atom.atom_id))

        return G

    def _atom_defines(self, atom: AtomicUnit, name: str) -> bool:
        """Check if atom defines a function/class with given name."""
        code = atom.code_to_generate

        # Simple regex check (could be improved with AST)
        patterns = [
            rf'def\s+{name}\s*\(',  # Function definition
            rf'class\s+{name}\s*[:\(]',  # Class definition
            rf'{name}\s*=',  # Variable assignment
        ]

        for pattern in patterns:
            if re.search(pattern, code):
                return True

        return False

    def _create_execution_waves(
        self,
        atoms: List[AtomicUnit],
        max_wave_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Create execution waves using topological sort on dependency graph.

        Atoms in same wave have no dependencies on each other.

        Returns:
            List of waves: [{"wave_number": 1, "atom_ids": [...]}, ...]
        """
        # Build dependency graph
        G = self._build_dependency_graph(atoms)

        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            logger.warning(f"Circular dependencies detected: {cycles}")
            # Break cycles by removing weakest edges
            G = self._break_cycles(G, cycles)

        # Topological sort with level assignment
        waves = []
        wave_number = 1

        # Get atoms with no dependencies (level 0)
        current_wave_ids = [
            node for node in G.nodes()
            if G.in_degree(node) == 0
        ]

        while current_wave_ids:
            # Limit wave size
            if len(current_wave_ids) > max_wave_size:
                # Split into multiple waves
                for i in range(0, len(current_wave_ids), max_wave_size):
                    wave_batch = current_wave_ids[i:i+max_wave_size]
                    waves.append({
                        "wave_number": wave_number,
                        "atom_ids": wave_batch
                    })
                    wave_number += 1
            else:
                waves.append({
                    "wave_number": wave_number,
                    "atom_ids": current_wave_ids
                })
                wave_number += 1

            # Remove current wave nodes from graph
            G.remove_nodes_from(current_wave_ids)

            # Get next wave (atoms with no remaining dependencies)
            current_wave_ids = [
                node for node in G.nodes()
                if G.in_degree(node) == 0
            ]

        logger.info(
            f"Created {len(waves)} execution waves",
            extra={
                "total_atoms": len(atoms),
                "waves": len(waves),
                "avg_wave_size": sum(len(w['atom_ids']) for w in waves) / len(waves)
            }
        )

        return waves

    def _break_cycles(self, G: nx.DiGraph, cycles: List[List[str]]) -> nx.DiGraph:
        """
        Break circular dependencies by removing weakest edges.

        Heuristic: Remove edge with lowest atom complexity score.
        """
        for cycle in cycles:
            # Find weakest edge in cycle
            min_weight = float('inf')
            weakest_edge = None

            for i in range(len(cycle)):
                src = cycle[i]
                dst = cycle[(i + 1) % len(cycle)]

                if G.has_edge(src, dst):
                    # Calculate edge weight (complexity of dependency)
                    src_atom = G.nodes[src]['atom']
                    weight = src_atom.estimated_loc

                    if weight < min_weight:
                        min_weight = weight
                        weakest_edge = (src, dst)

            # Remove weakest edge
            if weakest_edge:
                logger.warning(f"Breaking cycle by removing edge: {weakest_edge}")
                G.remove_edge(*weakest_edge)

        return G
```

**Update orchestrate_from_discovery():**
```python
# Replace lines 282-306 with:
yield {
    "type": "status",
    "phase": "execution_planning",
    "message": f"Analyzing dependencies for {total_atoms} atoms...",
    "timestamp": datetime.utcnow().isoformat()
}

# Create execution plan with dependency graph
execution_plan = self._create_execution_waves(all_atoms, max_wave_size=100)

yield {
    "type": "status",
    "phase": "execution_planning",
    "message": f"Created {len(execution_plan)} execution waves (avg {sum(len(w['atom_ids']) for w in execution_plan) / len(execution_plan):.0f} atoms/wave)",
    "timestamp": datetime.utcnow().isoformat()
}
```

**Testing:**
```python
# tests/test_dependency_graph.py
def test_simple_dependency_chain():
    """Test A → B → C creates 3 waves."""
    atoms = [
        create_atom("A", code="x = 1"),
        create_atom("B", code="y = x + 1", dependencies=["x"]),
        create_atom("C", code="z = y + 1", dependencies=["y"])
    ]

    waves = service._create_execution_waves(atoms)

    assert len(waves) == 3
    assert waves[0]['atom_ids'] == [atom_A.id]
    assert waves[1]['atom_ids'] == [atom_B.id]
    assert waves[2]['atom_ids'] == [atom_C.id]

def test_parallel_independent_atoms():
    """Test A, B, C (no dependencies) creates 1 wave."""
    atoms = [
        create_atom("A", code="x = 1"),
        create_atom("B", code="y = 2"),
        create_atom("C", code="z = 3")
    ]

    waves = service._create_execution_waves(atoms)

    assert len(waves) == 1
    assert len(waves[0]['atom_ids']) == 3

def test_circular_dependency_breaks():
    """Test A → B → C → A breaks cycle."""
    atoms = [
        create_atom("A", code="def a(): return b()"),
        create_atom("B", code="def b(): return c()", dependencies=["a"]),
        create_atom("C", code="def c(): return a()", dependencies=["b"])
    ]

    waves = service._create_execution_waves(atoms)

    # Cycle should be broken, allowing execution
    assert len(waves) >= 2
```

---

### Fase 2: Mejoras de Calidad (Media Prioridad - 2-3 días)

#### Task 2.1: Agregar Code Validation
**Prioridad:** 🟡 MEDIA
**Tiempo:** 1 día
**Archivo:** Crear `src/services/code_validator_service.py`

**Implementación:**
```python
import ast
import subprocess
from typing import Dict, Any, List
from pathlib import Path

class CodeValidatorService:
    """
    Validates generated code for syntax, imports, and type correctness.

    Validation levels:
    1. Syntax validation (AST parse)
    2. Import validation (check imports exist)
    3. Type validation (mypy/typescript)
    """

    def __init__(self, db: Session):
        self.db = db

    def validate_task_code(self, task_id: uuid.UUID) -> Dict[str, Any]:
        """
        Validate generated code for a task.

        Returns:
            {
                "is_valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "validation_steps": {
                    "syntax": bool,
                    "imports": bool,
                    "types": bool
                }
            }
        """
        task = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.task_id == task_id
        ).first()

        if not task or not task.llm_response:
            return {"is_valid": False, "errors": ["No code to validate"]}

        code = task.llm_response
        language = self._detect_language(task)

        errors = []
        warnings = []
        validation_steps = {}

        # Step 1: Syntax validation
        syntax_valid, syntax_errors = self._validate_syntax(code, language)
        validation_steps['syntax'] = syntax_valid
        if not syntax_valid:
            errors.extend(syntax_errors)
            # Stop if syntax invalid
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "validation_steps": validation_steps
            }

        # Step 2: Import validation
        imports_valid, import_errors, import_warnings = self._validate_imports(code, language)
        validation_steps['imports'] = imports_valid
        errors.extend(import_errors)
        warnings.extend(import_warnings)

        # Step 3: Type validation (optional, can be slow)
        if language == 'python':
            types_valid, type_errors = self._validate_types_python(code)
            validation_steps['types'] = types_valid
            if type_errors:
                warnings.extend(type_errors)  # Types are warnings, not errors

        is_valid = syntax_valid and imports_valid

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "validation_steps": validation_steps
        }

    def _validate_syntax(self, code: str, language: str) -> tuple[bool, List[str]]:
        """Validate syntax using AST parsing."""
        errors = []

        if language == 'python':
            try:
                ast.parse(code)
                return True, []
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
                return False, errors

        elif language in ['javascript', 'typescript']:
            # Use esprima or similar for JS/TS
            # For now, basic check
            return True, []

        return True, []

    def _validate_imports(self, code: str, language: str) -> tuple[bool, List[str], List[str]]:
        """Validate imports exist."""
        errors = []
        warnings = []

        if language == 'python':
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if not self._check_python_import(alias.name):
                                warnings.append(f"Import '{alias.name}' may not exist")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and not self._check_python_import(node.module):
                            warnings.append(f"Import from '{node.module}' may not exist")
            except Exception as e:
                errors.append(f"Import validation failed: {e}")
                return False, errors, warnings

        return True, errors, warnings

    def _check_python_import(self, module_name: str) -> bool:
        """Check if Python module exists."""
        try:
            __import__(module_name.split('.')[0])
            return True
        except ImportError:
            return False

    def _validate_types_python(self, code: str) -> tuple[bool, List[str]]:
        """Validate types using mypy (optional, can be slow)."""
        errors = []

        try:
            # Write code to temp file
            temp_file = Path("/tmp") / f"validate_{uuid.uuid4()}.py"
            temp_file.write_text(code)

            # Run mypy
            result = subprocess.run(
                ['mypy', '--no-error-summary', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                errors.append(f"Type errors: {result.stdout}")

            # Clean up
            temp_file.unlink()

            return result.returncode == 0, errors

        except Exception as e:
            # mypy not available or failed, skip
            return True, []

    def _detect_language(self, task: MasterPlanTask) -> str:
        """Detect language from task metadata."""
        if task.target_files:
            ext = Path(task.target_files[0]).suffix
            if ext == '.py':
                return 'python'
            elif ext in ['.js', '.jsx']:
                return 'javascript'
            elif ext in ['.ts', '.tsx']:
                return 'typescript'
        return 'python'
```

**Integration into orchestration:**
```python
# In orchestrate_from_discovery(), after code generation:
yield {
    "type": "status",
    "phase": "code_validation",
    "message": "Validating generated code...",
    "timestamp": datetime.utcnow().isoformat()
}

validator = CodeValidatorService(db=self.db)
validation_errors = []

for task in tasks:
    result = validator.validate_task_code(task.task_id)

    if not result['is_valid']:
        validation_errors.append({
            "task_id": str(task.task_id),
            "task_name": task.name,
            "errors": result['errors']
        })

        # Retry generation with stricter prompt
        logger.warning(f"Code validation failed for task {task.task_id}, retrying...")
        # TODO: Implement retry logic

if validation_errors:
    yield {
        "type": "warning",
        "phase": "code_validation",
        "message": f"Validation failed for {len(validation_errors)} tasks",
        "errors": validation_errors,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

#### Task 2.2: Mejorar File Path Resolution
**Prioridad:** 🟡 MEDIA
**Tiempo:** 1 día
**Archivo:** `src/services/file_writer_service.py`

**Implementación:**
```python
def _get_atom_file_path(self, atom: AtomicUnit) -> str:
    """
    Determine file path using intelligent strategies.

    Priority:
    1. Atom metadata (explicitly set)
    2. Parse from code (imports, class names)
    3. Task target_files
    4. Infer from task name/description
    5. Fallback to generic path
    """
    # Strategy 1: Explicit metadata
    if atom.metadata and 'file_path' in atom.metadata:
        return atom.metadata['file_path']

    # Strategy 2: Parse from code
    if atom.code_to_generate:
        inferred_path = self._infer_path_from_code(atom.code_to_generate)
        if inferred_path:
            return inferred_path

    # Strategy 3: Task target_files
    if atom.task and atom.task.target_files:
        return atom.task.target_files[0]

    # Strategy 4: Infer from task name
    if atom.task:
        inferred_path = self._infer_path_from_task(atom.task)
        if inferred_path:
            return inferred_path

    # Strategy 5: Fallback
    logger.warning(f"Could not infer path for atom {atom.atom_id}, using fallback")
    return f"src/generated/atom_{atom.atom_number}.py"

def _infer_path_from_code(self, code: str) -> Optional[str]:
    """
    Infer file path from code content.

    Strategies:
    - Check for class definitions → src/models/{class_name}.py
    - Check for FastAPI router → src/api/routers/{router_name}.py
    - Check for service class → src/services/{service_name}.py
    - Check for schema class → src/schemas/{schema_name}.py
    """
    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for model indicators
                if any(base.id in ['BaseModel', 'Base', 'Model'] for base in node.bases if isinstance(base, ast.Name)):
                    return f"src/models/{class_name}.py"

                # Check for service indicators
                if 'service' in class_name:
                    return f"src/services/{class_name}.py"

                # Check for schema indicators
                if any(keyword in class_name for keyword in ['schema', 'request', 'response']):
                    return f"src/schemas/{class_name}.py"

                # Default class location
                return f"src/models/{class_name}.py"

            elif isinstance(node, ast.FunctionDef):
                func_name = node.name.lower()

                # Check for route decorators (FastAPI)
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['get', 'post', 'put', 'delete']:
                                return f"src/api/routers/{func_name}_router.py"

    except Exception as e:
        logger.debug(f"Failed to infer path from code: {e}")

    return None

def _infer_path_from_task(self, task: MasterPlanTask) -> Optional[str]:
    """
    Infer file path from task name and description.

    More intelligent than current keyword matching.
    """
    text = f"{task.name} {task.description}".lower()

    # Model patterns
    model_patterns = [
        (r'create (\w+) model', r'src/models/\1.py'),
        (r'(\w+) database model', r'src/models/\1.py'),
        (r'define (\w+) entity', r'src/models/\1.py'),
    ]

    # Service patterns
    service_patterns = [
        (r'create (\w+) service', r'src/services/\1_service.py'),
        (r'(\w+) business logic', r'src/services/\1_service.py'),
    ]

    # API patterns
    api_patterns = [
        (r'create (\w+) api', r'src/api/routers/\1.py'),
        (r'(\w+) endpoints', r'src/api/routers/\1.py'),
        (r'(\w+) routes', r'src/api/routers/\1.py'),
    ]

    # Schema patterns
    schema_patterns = [
        (r'create (\w+) schema', r'src/schemas/\1_schemas.py'),
        (r'(\w+) validation', r'src/schemas/\1_schemas.py'),
    ]

    # Try all patterns
    for patterns, template in [
        (model_patterns, None),
        (service_patterns, None),
        (api_patterns, None),
        (schema_patterns, None)
    ]:
        for pattern, path_template in patterns:
            match = re.search(pattern, text)
            if match:
                return re.sub(pattern, path_template, text)

    return None
```

---

### Fase 3: Optimizaciones (Baja Prioridad - 2 días)

#### Task 3.1: Crear Templates Jinja2
**Prioridad:** 🟢 BAJA
**Tiempo:** 1 día
**Directorio:** Crear `templates/`

**Estructura:**
```
templates/
├── docker/
│   ├── python_fastapi.dockerfile
│   ├── python_django.dockerfile
│   ├── node_express.dockerfile
│   └── docker-compose.yml.j2
├── config/
│   ├── env_fastapi.example.j2
│   ├── env_express.example.j2
│   ├── requirements_fastapi.txt.j2
│   └── package_express.json.j2
└── git/
    ├── README_fastapi.md.j2
    ├── README_express.md.j2
    └── gitignore_python.txt
```

**Ejemplo - FastAPI Dockerfile:**
```dockerfile
# templates/docker/python_fastapi.dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE {{ app_port }}

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:{{ app_port }}/health || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "{{ app_port }}"]
```

**Ejemplo - docker-compose.yml:**
```yaml
# templates/docker/docker-compose.yml.j2
version: '3.8'

services:
  app:
    build: .
    container_name: {{ project_slug }}-app
    ports:
      - "{{ app_port }}:{{ app_port }}"
    environment:
      - DATABASE_URL=postgresql://{{ db_user }}:{{ db_password }}@db:5432/{{ db_name }}
      {% if needs_redis %}
      - REDIS_URL=redis://redis:6379/0
      {% endif %}
    depends_on:
      - db
      {% if needs_redis %}
      - redis
      {% endif %}
    volumes:
      - .:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port {{ app_port }} --reload

  db:
    image: postgres:15-alpine
    container_name: {{ project_slug }}-db
    environment:
      - POSTGRES_USER={{ db_user }}
      - POSTGRES_PASSWORD={{ db_password }}
      - POSTGRES_DB={{ db_name }}
    ports:
      - "{{ db_port }}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  {% if needs_redis %}
  redis:
    image: redis:7-alpine
    container_name: {{ project_slug }}-redis
    ports:
      - "{{ redis_port }}:6379"
    volumes:
      - redis_data:/data
  {% endif %}

volumes:
  postgres_data:
  {% if needs_redis %}
  redis_data:
  {% endif %}
```

**Ejemplo - README.md:**
```markdown
# templates/git/README_fastapi.md.j2
# {{ project_name }}

{{ project_description }}

## Tech Stack

- **Backend:** FastAPI {{ tech_stack.backend_version | default('0.104.0') }}
- **Database:** PostgreSQL {{ tech_stack.database_version | default('15') }}
{% if needs_redis %}
- **Cache:** Redis {{ tech_stack.redis_version | default('7') }}
{% endif %}
- **Python:** 3.11+

## API Endpoints

{% for endpoint_group in api_endpoints %}
### {{ endpoint_group.category }}

{% for route in endpoint_group.routes %}
- `{{ route.method }} {{ route.path }}` - {{ route.description }}
{% endfor %}
{% endfor %}

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### Setup

1. Clone the repository:
```bash
git clone <repository_url>
cd {{ project_slug }}
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start services:
```bash
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose exec app alembic upgrade head
```

5. Access the application:
- API: http://localhost:{{ app_port }}
- Docs: http://localhost:{{ app_port }}/docs

## Development

### Run tests:
```bash
docker-compose exec app pytest
```

### Create migration:
```bash
docker-compose exec app alembic revision --autogenerate -m "description"
```

### Access database:
```bash
docker-compose exec db psql -U {{ db_user }} -d {{ db_name }}
```

## Project Structure

```
{{ project_slug }}/
├── src/
│   ├── api/          # API routes and endpoints
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   ├── schemas/      # Pydantic schemas
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── alembic/          # Database migrations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

MIT
```

---

#### Task 3.2: Fix Cost Tracking
**Prioridad:** 🟢 BAJA
**Tiempo:** 0.5 días
**Archivo:** `src/services/mge_v2_orchestration_service.py`

**Implementación:**
```python
# After code generation phase (line ~219), add:
yield {
    "type": "status",
    "phase": "cost_calculation",
    "message": "Calculating total generation cost...",
    "timestamp": datetime.utcnow().isoformat()
}

# Calculate total cost from tasks
total_code_gen_cost = sum(
    task.llm_cost_usd for task in tasks
    if task.llm_cost_usd is not None
)

# Add discovery cost if available
discovery = self.db.query(DiscoveryDocument).filter(
    DiscoveryDocument.discovery_id == discovery_id
).first()

total_cost = total_code_gen_cost
if discovery and discovery.llm_cost_usd:
    total_cost += discovery.llm_cost_usd

# Update MasterPlan
masterplan.generation_cost_usd = total_cost
masterplan.llm_tokens_total = sum(
    (task.llm_tokens_input or 0) + (task.llm_tokens_output or 0)
    for task in tasks
)
self.db.commit()

yield {
    "type": "status",
    "phase": "cost_calculation",
    "message": f"Total generation cost: ${total_cost:.2f} ({masterplan.llm_tokens_total:,} tokens)",
    "total_cost_usd": total_cost,
    "total_tokens": masterplan.llm_tokens_total,
    "timestamp": datetime.utcnow().isoformat()
}
```

---

## 🏗️ ARQUITECTURA DE SERVICIOS

### Diagrama de Dependencias

```
WebSocket (Frontend)
    ↓
ChatService
    ↓
MGE_V2_OrchestrationService
    ↓
    ├─→ DiscoveryService (DDD analysis)
    ├─→ MasterPlanGenerator (120 tasks)
    ├─→ CodeGenerationService (LLM) ← NEW
    ├─→ CodeValidatorService (validation) ← NEW
    ├─→ AtomService (atomization) ← TO IMPLEMENT
    ├─→ ExecutionServiceV2 (wave execution)
    │   └─→ WaveExecutor
    │       └─→ RetryOrchestrator
    │           └─→ AtomicValidator
    ├─→ FileWriterService (write files)
    └─→ InfrastructureGenerationService (configs)
```

### Service Responsibilities

| Service | Responsibility | Dependencies | Status |
|---------|---------------|--------------|--------|
| **DiscoveryService** | DDD analysis, domain modeling | LLM, DB | ✅ Complete |
| **MasterPlanGenerator** | Task hierarchy generation | Discovery, LLM, RAG | ✅ Complete |
| **CodeGenerationService** | Code from task descriptions | LLM, DB | ✅ Complete |
| **CodeValidatorService** | Syntax, imports, types validation | AST, mypy | ⏳ To Create |
| **AtomService** | Code → 10 LOC atoms | AST parser, DB | ❌ Stub Only |
| **ExecutionServiceV2** | Wave orchestration | WaveExecutor | ✅ Complete |
| **FileWriterService** | Atoms → files | DB, filesystem | ✅ Complete |
| **InfrastructureGenerationService** | Docker, configs, docs | Jinja2, DB | ✅ Complete |

---

## 📐 ESPECIFICACIONES TÉCNICAS

### Database Schema (MGE V2)

```sql
-- Discovery
CREATE TABLE discovery_documents (
    discovery_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id VARCHAR(255),
    domain VARCHAR(255) NOT NULL,
    bounded_contexts JSONB,
    aggregates JSONB,
    entities JSONB,
    llm_cost_usd DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- MasterPlan
CREATE TABLE masterplans (
    masterplan_id UUID PRIMARY KEY,
    discovery_id UUID REFERENCES discovery_documents(discovery_id),
    user_id UUID NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    total_phases INT,
    total_milestones INT,
    total_tasks INT,
    generation_cost_usd DECIMAL(10, 4),  -- ← FIX: Agregar aquí
    llm_tokens_total INT,  -- ← FIX: Agregar aquí
    created_at TIMESTAMP DEFAULT NOW()
);

-- MasterPlan Tasks
CREATE TABLE masterplan_tasks (
    task_id UUID PRIMARY KEY,
    masterplan_id UUID REFERENCES masterplans(masterplan_id),
    task_number INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    complexity VARCHAR(50),
    target_files TEXT[],
    llm_prompt TEXT,  -- ← Prompt usado para code generation
    llm_response TEXT,  -- ← Código generado
    llm_model VARCHAR(100),
    llm_tokens_input INT,
    llm_tokens_output INT,
    llm_cached_tokens INT,
    llm_cost_usd DECIMAL(10, 4),
    last_error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Atomic Units
CREATE TABLE atomic_units (
    atom_id UUID PRIMARY KEY,
    task_id UUID REFERENCES masterplan_tasks(task_id),
    masterplan_id UUID REFERENCES masterplans(masterplan_id),
    atom_number INT NOT NULL,
    atom_type VARCHAR(50),  -- function, class, import, etc.
    code_to_generate TEXT NOT NULL,
    estimated_loc INT,
    dependencies_raw TEXT[],  -- ← Dependencies extracted from AST
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Execution Results
CREATE TABLE execution_results (
    execution_id UUID PRIMARY KEY,
    masterplan_id UUID REFERENCES masterplans(masterplan_id),
    wave_number INT,
    atom_id UUID REFERENCES atomic_units(atom_id),
    status VARCHAR(50),
    output TEXT,
    error TEXT,
    execution_time_seconds DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### WebSocket Events (MGE V2)

```typescript
// Discovery Events
{
  type: 'discovery_generation_start',
  data: {
    session_id: string,
    estimated_tokens: number,
    estimated_duration_seconds: number,
    estimated_cost_usd: number
  }
}

{
  type: 'discovery_tokens_progress',
  data: {
    session_id: string,
    tokens_received: number,
    estimated_total: number
  }
}

{
  type: 'discovery_entity_discovered',
  data: {
    session_id: string,
    entity_type: 'domain' | 'bounded_context' | 'aggregate' | 'entity',
    name: string,
    count: number
  }
}

{
  type: 'discovery_generation_complete',
  data: {
    session_id: string,
    discovery_id: string,
    total_bounded_contexts: number,
    total_aggregates: number,
    total_entities: number
  }
}

// MasterPlan Events
{
  type: 'masterplan_generation_start',
  data: {
    session_id: string,
    discovery_id: string,
    estimated_tokens: number,
    estimated_cost_usd: number
  }
}

{
  type: 'masterplan_tokens_progress',
  data: {
    session_id: string,
    tokens_received: number,
    estimated_total: number
  }
}

{
  type: 'masterplan_entity_discovered',
  data: {
    session_id: string,
    entity_type: 'phase' | 'milestone' | 'task',
    count: number
  }
}

{
  type: 'masterplan_generation_complete',
  data: {
    session_id: string,
    masterplan_id: string,
    total_phases: number,
    total_milestones: number,
    total_tasks: number,
    generation_cost_usd: number
  }
}

// Code Generation Events (NEW)
{
  type: 'code_generation_progress',
  data: {
    masterplan_id: string,
    task_number: number,
    task_title: string,
    progress: string,  // "45/120"
    code_length: number,
    success: boolean
  }
}

// Validation Events (NEW)
{
  type: 'code_validation_complete',
  data: {
    masterplan_id: string,
    total_tasks: number,
    validation_errors: number,
    warnings: number
  }
}

// Atomization Events
{
  type: 'atomization_progress',
  data: {
    masterplan_id: string,
    task_number: number,
    atoms_created: number,
    progress: string  // "45/120"
  }
}

// Execution Events
{
  type: 'execution_wave_start',
  data: {
    masterplan_id: string,
    execution_id: string,
    wave_number: number,
    total_waves: number,
    atoms_in_wave: number
  }
}

{
  type: 'execution_wave_complete',
  data: {
    masterplan_id: string,
    wave_number: number,
    atoms_succeeded: number,
    atoms_failed: number,
    duration_seconds: number
  }
}

// File Writing Events
{
  type: 'file_writing_progress',
  data: {
    masterplan_id: string,
    files_written: number,
    workspace_path: string
  }
}

// Infrastructure Events
{
  type: 'infrastructure_generation_complete',
  data: {
    masterplan_id: string,
    files_generated: number,
    project_type: string
  }
}

// Completion Event
{
  type: 'complete',
  data: {
    masterplan_id: string,
    execution_id: string,
    total_tasks: number,
    total_atoms: number,
    total_waves: number,
    precision: number,
    execution_time: number,
    workspace_path: string
  }
}
```

---

## 🧪 TESTING Y VALIDACIÓN

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| AtomService | 90% | 🔴 Critical |
| Dependency Graph | 95% | 🔴 Critical |
| Code Validator | 85% | 🟡 High |
| File Path Resolution | 80% | 🟡 High |
| Templates | 75% | 🟢 Medium |

### Integration Tests

```python
# tests/integration/test_mge_v2_e2e.py

@pytest.mark.asyncio
async def test_full_mge_v2_pipeline():
    """
    End-to-end test: User request → Generated code
    """
    # Setup
    user_request = "Create a FastAPI REST API for task management with users, tasks, and comments"

    # Execute pipeline
    service = MGE_V2_OrchestrationService(db=db_session)

    events = []
    async for event in service.orchestrate_from_request(
        user_request=user_request,
        workspace_id="test-workspace",
        session_id="test-session",
        user_id="test-user"
    ):
        events.append(event)

    # Assertions
    assert any(e['type'] == 'discovery_generation_complete' for e in events)
    assert any(e['type'] == 'masterplan_generation_complete' for e in events)
    assert any(e['type'] == 'code_generation_complete' for e in events)  # NEW
    assert any(e['type'] == 'atomization_complete' for e in events)
    assert any(e['type'] == 'execution_complete' for e in events)
    assert any(e['type'] == 'complete' for e in events)

    # Verify output
    final_event = next(e for e in events if e['type'] == 'complete')

    assert final_event['data']['total_tasks'] > 0
    assert final_event['data']['total_atoms'] > 0
    assert final_event['data']['workspace_path'] is not None

    # Verify files exist
    workspace_path = Path(final_event['data']['workspace_path'])
    assert workspace_path.exists()
    assert (workspace_path / 'Dockerfile').exists()
    assert (workspace_path / 'docker-compose.yml').exists()
    assert (workspace_path / 'requirements.txt').exists()
    assert (workspace_path / 'src').exists()


@pytest.mark.asyncio
async def test_atomization_with_dependencies():
    """
    Test atomization creates correct dependency graph.
    """
    code = """
from typing import List

def get_users() -> List[User]:
    return db.query(User).all()

def get_user_tasks(user_id: int) -> List[Task]:
    user = get_users()[0]  # Depends on get_users
    return user.tasks
"""

    task = create_test_task(code=code)

    # Atomize
    result = atom_service.decompose_task(task.task_id)

    assert result['success'] == True
    assert result['total_atoms'] >= 2

    # Verify dependency
    atoms = db.query(AtomicUnit).filter(AtomicUnit.task_id == task.task_id).all()

    get_users_atom = next(a for a in atoms if 'get_users' in a.code_to_generate)
    get_user_tasks_atom = next(a for a in atoms if 'get_user_tasks' in a.code_to_generate)

    assert 'get_users' in get_user_tasks_atom.dependencies_raw


@pytest.mark.asyncio
async def test_wave_execution_respects_dependencies():
    """
    Test wave execution creates topological order.
    """
    # Create atoms with dependencies: A → B → C
    atom_a = create_atom(code="def func_a(): return 1")
    atom_b = create_atom(code="def func_b(): return func_a() + 1", dependencies=["func_a"])
    atom_c = create_atom(code="def func_c(): return func_b() + 1", dependencies=["func_b"])

    # Create waves
    waves = service._create_execution_waves([atom_a, atom_b, atom_c])

    # Verify topological order
    assert len(waves) == 3
    assert str(atom_a.atom_id) in waves[0]['atom_ids']
    assert str(atom_b.atom_id) in waves[1]['atom_ids']
    assert str(atom_c.atom_id) in waves[2]['atom_ids']
```

---

## 📊 MÉTRICAS Y PERFORMANCE

### Performance Benchmarks

| Fase | Tiempo Actual | Tiempo Objetivo | Status |
|------|--------------|-----------------|--------|
| Discovery | ~30s | <30s | ✅ |
| MasterPlan Gen | ~90s | <90s | ✅ |
| Code Generation | ~300s | <240s | ⚠️ Optimize batching |
| Atomization | N/A | <60s | ⏳ To implement |
| Wave Execution | N/A | <180s | ⏳ To implement |
| File Writing | ~5s | <10s | ✅ |
| Infrastructure | ~2s | <5s | ✅ |
| **Total** | **~12 min** | **<10 min** | ⚠️ |

### Cost Benchmarks

| Component | Cost/Project | Optimization Potential |
|-----------|--------------|----------------------|
| Discovery | $0.09 | ✅ Already optimal |
| MasterPlan | $0.30 | ✅ RAG caching helps |
| Code Gen (120 tasks) | $6.00 | ⚠️ Use prompt caching |
| Retries (10%) | $0.60 | ✅ Validation reduces |
| **Total** | **~$7.00** | **Target: <$5.00** |

### Optimization Opportunities

1. **Code Generation Batching:**
   - Current: 5 tasks parallel
   - Optimize: 10 tasks parallel
   - Savings: ~50s (300s → 250s)

2. **LLM Prompt Caching:**
   - Cache system prompts across tasks
   - Potential savings: ~$1.50/project

3. **Atomization Performance:**
   - Target: <1s per task
   - Use compiled regex patterns
   - Parallel atomization where possible

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Crítico (3-4 días)
- [ ] Implementar `AtomService.decompose_task()`
  - [ ] AST parsing y chunking
  - [ ] Dependency extraction
  - [ ] AtomicUnit creation
  - [ ] Unit tests (90% coverage)
- [ ] Implementar dependency graph
  - [ ] NetworkX integration
  - [ ] Topological sort
  - [ ] Cycle detection y breaking
  - [ ] Integration tests
- [ ] Update orchestration service
  - [ ] Replace simple waves with graph-based
  - [ ] Add atomization events
  - [ ] Update progress tracking

### Fase 2: Mejoras (2-3 días)
- [ ] Crear `CodeValidatorService`
  - [ ] Syntax validation (AST)
  - [ ] Import checking
  - [ ] Type validation (optional)
  - [ ] Integration con pipeline
- [ ] Mejorar file path resolution
  - [ ] Code parsing strategy
  - [ ] Intelligent inference
  - [ ] Better fallbacks
  - [ ] Tests para edge cases

### Fase 3: Optimizaciones (2 días)
- [ ] Crear templates Jinja2
  - [ ] Dockerfile templates (FastAPI, Express)
  - [ ] docker-compose template
  - [ ] .env templates
  - [ ] README templates
- [ ] Fix cost tracking
  - [ ] Sumar costs de tasks
  - [ ] Actualizar MasterPlan
  - [ ] Add cost events
- [ ] Performance optimizations
  - [ ] Increase batching (5 → 10)
  - [ ] Add prompt caching
  - [ ] Parallel atomization

### Testing & Validation
- [ ] E2E test completo
- [ ] Performance benchmarks
- [ ] Cost validation
- [ ] Documentation updates

---

## 🚀 DEPLOYMENT PLAN

### Phase 1: Development (Week 1)
- Implement critical fixes
- Unit tests
- Integration tests

### Phase 2: Staging (Week 2)
- Deploy to staging
- E2E validation
- Performance testing
- Bug fixes

### Phase 3: Production (Week 3)
- Production deployment
- Monitoring setup
- Gradual rollout
- User feedback collection

---

## 📚 REFERENCIAS

- **MGE V2 Docs:** `DOCS/MGE_V2/`
- **Original Implementation:** `src/services/mge_v2_orchestration_service.py`
- **Frontend Progress:** `src/ui/src/hooks/useMasterPlanProgress.ts`
- **Database Schema:** `alembic/versions/`
- **Testing Guide:** `tests/README.md`

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Next Review:** After Phase 1 completion
