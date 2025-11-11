# DevMatrix: Sistema de Atomización Profunda AST-Based

## 🎯 Objetivo

Construir el sistema de atomización más avanzado que:
- **Descompone recursivamente**: Cualquier código → unidades atómicas (expresión-level)
- **100% autocontenidas**: Context injection completo
- **Paralelización real**: 100+ unidades ejecutables simultáneamente
- **Validación estricta**: 10 criterios de atomicidad
- **Multi-lenguaje**: Python, TypeScript, JavaScript, SQL, etc.

**Timeline**: 6-9 meses de desarrollo
**Impacto esperado**: Base para alcanzar 99% de precisión

---

## 🏗️ Arquitectura del Sistema

### Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                  DEVMATRIX ATOMIZATION ENGINE                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Project Spec    │  (Figma, Requirements, Architecture)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Semantic Analyzer│  (GPT-4 / Claude Opus)
│  • Domain model  │
│  • Entities      │
│  • Relations     │
│  • Flows         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Cognitive Graph │  (Neo4j)
│  • Nodes = Units │
│  • Edges = Deps  │
│  • Props = Meta  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Recursive        │
│ Decomposer       │
│  • AST parsing   │
│  • Cut points    │
│  • Atomization   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Atomic Units     │  (1000+ units)
│  • Function      │
│  • Expression    │
│  • Statement     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Context Injector │
│  • Schemas       │
│  • Types         │
│  • Dependencies  │
│  • Examples      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Atomicity        │
│ Validator        │
│  • 10 criteria   │
│  • Auto-fix      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Parallel Executor│  (100+ agents)
│  • DeepSeek      │
│  • Independent   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Final Code      │
└──────────────────┘
```

---

## 🧬 Componentes Clave

### 1. Multi-Language AST Parser

```python
# src/atomization/parsers/multi_parser.py

import ast
import tree_sitter
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    GO = "go"
    RUST = "rust"

class MultiLanguageParser:
    """
    Parser universal para múltiples lenguajes usando tree-sitter.
    """
    
    def __init__(self):
        # Inicializar tree-sitter parsers
        self.parsers = self._init_parsers()
    
    def _init_parsers(self) -> Dict[Language, tree_sitter.Parser]:
        """
        Inicializa parsers para cada lenguaje.
        """
        parsers = {}
        
        # Python
        python_lang = tree_sitter.Language('build/my-languages.so', 'python')
        python_parser = tree_sitter.Parser()
        python_parser.set_language(python_lang)
        parsers[Language.PYTHON] = python_parser
        
        # JavaScript
        js_lang = tree_sitter.Language('build/my-languages.so', 'javascript')
        js_parser = tree_sitter.Parser()
        js_parser.set_language(js_lang)
        parsers[Language.JAVASCRIPT] = js_parser
        
        # TypeScript
        ts_lang = tree_sitter.Language('build/my-languages.so', 'typescript')
        ts_parser = tree_sitter.Parser()
        ts_parser.set_language(ts_lang)
        parsers[Language.TYPESCRIPT] = ts_parser
        
        # SQL
        sql_lang = tree_sitter.Language('build/my-languages.so', 'sql')
        sql_parser = tree_sitter.Parser()
        sql_parser.set_language(sql_lang)
        parsers[Language.SQL] = sql_parser
        
        return parsers
    
    def parse(self, code: str, language: Language) -> tree_sitter.Tree:
        """
        Parsea código a AST.
        """
        if language not in self.parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        parser = self.parsers[language]
        tree = parser.parse(bytes(code, "utf8"))
        
        return tree
    
    def get_root_node(self, tree: tree_sitter.Tree) -> tree_sitter.Node:
        """
        Obtiene nodo raíz del AST.
        """
        return tree.root_node
    
    def traverse(
        self,
        node: tree_sitter.Node,
        visitor_fn,
        depth: int = 0
    ):
        """
        Recorre AST con visitor pattern.
        """
        # Visit current node
        visitor_fn(node, depth)
        
        # Visit children recursively
        for child in node.children:
            self.traverse(child, visitor_fn, depth + 1)
    
    def extract_code_snippet(
        self,
        source_code: str,
        node: tree_sitter.Node
    ) -> str:
        """
        Extrae código de un nodo específico.
        """
        start_byte = node.start_byte
        end_byte = node.end_byte
        
        return source_code[start_byte:end_byte]
    
    def find_nodes_by_type(
        self,
        root: tree_sitter.Node,
        node_type: str
    ) -> list:
        """
        Encuentra todos los nodos de un tipo específico.
        """
        results = []
        
        def visitor(node, depth):
            if node.type == node_type:
                results.append(node)
        
        self.traverse(root, visitor)
        
        return results

# Example usage for Python
class PythonASTAnalyzer:
    """
    Analizador especializado para Python usando AST nativo.
    """
    
    def __init__(self):
        pass
    
    def parse_python(self, code: str) -> ast.Module:
        """
        Parsea código Python a AST.
        """
        try:
            tree = ast.parse(code)
            return tree
        except SyntaxError as e:
            logger.error(f"Syntax error in Python code: {e}")
            raise
    
    def extract_functions(self, tree: ast.Module) -> list:
        """
        Extrae todas las definiciones de función.
        """
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'decorators': [ast.unparse(d) for d in node.decorator_list],
                    'docstring': ast.get_docstring(node),
                    'lineno': node.lineno,
                    'body': node.body
                })
        
        return functions
    
    def extract_classes(self, tree: ast.Module) -> list:
        """
        Extrae todas las definiciones de clase.
        """
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'bases': [ast.unparse(base) for base in node.bases],
                    'decorators': [ast.unparse(d) for d in node.decorator_list],
                    'methods': self._extract_class_methods(node),
                    'lineno': node.lineno
                })
        
        return classes
    
    def _extract_class_methods(self, class_node: ast.ClassDef) -> list:
        """
        Extrae métodos de una clase.
        """
        methods = []
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append({
                    'name': item.name,
                    'args': [arg.arg for arg in item.args.args],
                    'is_property': any(
                        isinstance(d, ast.Name) and d.id == 'property'
                        for d in item.decorator_list
                    )
                })
        
        return methods
    
    def calculate_complexity(self, node: ast.AST) -> int:
        """
        Calcula complejidad ciclomática.
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Control flow increases complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
```

---

### 2. Recursive Decomposer

```python
# src/atomization/decomposer.py

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from src.atomization.parsers.multi_parser import MultiLanguageParser, Language
import tree_sitter
import logging

logger = logging.getLogger(__name__)

@dataclass
class CutPoint:
    """
    Punto donde cortar para atomizar.
    """
    location: tuple  # (start_byte, end_byte)
    node_type: str
    priority: int  # 1 = highest priority
    reason: str
    context_needed: Dict

@dataclass
class AtomicUnit:
    """
    Unidad atómica de código.
    """
    id: str
    purpose: str
    code: str
    language: Language
    parent_id: Optional[str]
    
    # Inputs/Outputs
    inputs: Dict[str, str]  # {name: type}
    outputs: Dict[str, str]
    
    # Context (TODO lo necesario para ejecutar independientemente)
    context: Dict
    
    # Metadata
    level: int  # Nivel de atomización (0 = module, 5 = expression)
    node_type: str
    dependencies: List[str]  # IDs de otras unidades
    
    # Metrics
    complexity: float
    is_pure: bool
    is_deterministic: bool
    estimated_loc: int

class RecursiveDecomposer:
    """
    Descompone código recursivamente hasta unidades atómicas.
    """
    
    def __init__(self):
        self.parser = MultiLanguageParser()
        self.max_depth = 10  # Prevenir recursión infinita
    
    def decompose(
        self,
        code: str,
        language: Language,
        max_complexity: float = 3.0,
        max_loc: int = 10
    ) -> List[AtomicUnit]:
        """
        Descompone código en unidades atómicas.
        
        Args:
            code: Código fuente
            language: Lenguaje de programación
            max_complexity: Complejidad máxima permitida por átomo
            max_loc: Líneas de código máximas por átomo
        
        Returns:
            Lista de unidades atómicas
        """
        logger.info(f"Starting decomposition of {len(code)} chars")
        
        # Parse to AST
        tree = self.parser.parse(code, language)
        root = self.parser.get_root_node(tree)
        
        # Recursive decomposition
        atoms = []
        self._decompose_recursive(
            code=code,
            node=root,
            language=language,
            parent_id=None,
            depth=0,
            atoms=atoms,
            max_complexity=max_complexity,
            max_loc=max_loc
        )
        
        logger.info(f"✅ Decomposed into {len(atoms)} atomic units")
        
        return atoms
    
    def _decompose_recursive(
        self,
        code: str,
        node: tree_sitter.Node,
        language: Language,
        parent_id: Optional[str],
        depth: int,
        atoms: List[AtomicUnit],
        max_complexity: float,
        max_loc: int
    ):
        """
        Descomposición recursiva.
        """
        if depth > self.max_depth:
            logger.warning(f"Max depth reached at node {node.type}")
            return
        
        # Extract code for this node
        node_code = self.parser.extract_code_snippet(code, node)
        
        # Check if already atomic
        if self._is_atomic(node, node_code, max_complexity, max_loc):
            # Create atomic unit
            atom = self._create_atomic_unit(
                code=node_code,
                node=node,
                language=language,
                parent_id=parent_id,
                depth=depth
            )
            atoms.append(atom)
            return
        
        # Not atomic, find cut points
        cut_points = self._find_cut_points(node, node_code)
        
        if not cut_points:
            # Can't decompose further, force atomize
            atom = self._create_atomic_unit(
                code=node_code,
                node=node,
                language=language,
                parent_id=parent_id,
                depth=depth
            )
            atoms.append(atom)
            logger.warning(f"Forced atomization at depth {depth}")
            return
        
        # Decompose at cut points
        for cut_point in cut_points:
            # Get child node at cut point
            child_nodes = self._get_nodes_at_cut_point(node, cut_point)
            
            for child_node in child_nodes:
                self._decompose_recursive(
                    code=code,
                    node=child_node,
                    language=language,
                    parent_id=parent_id,
                    depth=depth + 1,
                    atoms=atoms,
                    max_complexity=max_complexity,
                    max_loc=max_loc
                )
    
    def _is_atomic(
        self,
        node: tree_sitter.Node,
        code: str,
        max_complexity: float,
        max_loc: int
    ) -> bool:
        """
        Determina si un nodo ya es atómico.
        """
        # Criterios de atomicidad
        checks = {
            'single_responsibility': self._has_single_responsibility(node),
            'no_branching': not self._has_branching(node),
            'low_complexity': self._calculate_node_complexity(node) <= max_complexity,
            'minimal_loc': code.count('\n') <= max_loc,
            'no_loops': not self._has_loops(node),
            'pure_or_simple': self._is_pure_or_simple(node)
        }
        
        # Debe cumplir al menos 80% de criterios
        passed = sum(1 for v in checks.values() if v)
        threshold = len(checks) * 0.8
        
        is_atomic = passed >= threshold
        
        if is_atomic:
            logger.debug(f"Node {node.type} is atomic: {checks}")
        
        return is_atomic
    
    def _find_cut_points(
        self,
        node: tree_sitter.Node,
        code: str
    ) -> List[CutPoint]:
        """
        Identifica puntos de corte naturales.
        """
        cut_points = []
        
        # Estrategias de corte por tipo de nodo
        if node.type in ['function_definition', 'method_definition']:
            cut_points.extend(self._cut_function(node))
        
        elif node.type in ['if_statement', 'conditional_expression']:
            cut_points.extend(self._cut_conditional(node))
        
        elif node.type in ['for_statement', 'while_statement']:
            cut_points.extend(self._cut_loop(node))
        
        elif node.type == 'assignment':
            cut_points.extend(self._cut_assignment(node))
        
        elif node.type == 'call_expression':
            cut_points.extend(self._cut_function_call(node))
        
        # Ordenar por prioridad
        cut_points.sort(key=lambda cp: cp.priority)
        
        return cut_points
    
    def _cut_function(self, node: tree_sitter.Node) -> List[CutPoint]:
        """
        Corta una función en sus componentes.
        """
        cut_points = []
        
        # 1. Separar validaciones de entrada
        # 2. Separar cálculos/transformaciones
        # 3. Separar side effects
        # 4. Separar return statement
        
        # TODO: Implementar lógica de corte específica
        
        return cut_points
    
    def _cut_conditional(self, node: tree_sitter.Node) -> List[CutPoint]:
        """
        Corta un condicional en sus ramas.
        """
        cut_points = []
        
        # Cada rama del if/else es un cut point
        for child in node.children:
            if child.type in ['if_clause', 'elif_clause', 'else_clause']:
                cut_points.append(CutPoint(
                    location=(child.start_byte, child.end_byte),
                    node_type=child.type,
                    priority=2,
                    reason='conditional_branch',
                    context_needed={
                        'condition': 'TODO: extract condition',
                        'branch_type': child.type
                    }
                ))
        
        return cut_points
    
    def _cut_loop(self, node: tree_sitter.Node) -> List[CutPoint]:
        """
        Corta un loop en sus componentes.
        """
        cut_points = []
        
        # 1. Inicialización
        # 2. Condición
        # 3. Cuerpo
        # 4. Incremento
        
        # TODO: Implementar
        
        return cut_points
    
    def _create_atomic_unit(
        self,
        code: str,
        node: tree_sitter.Node,
        language: Language,
        parent_id: Optional[str],
        depth: int
    ) -> AtomicUnit:
        """
        Crea unidad atómica.
        """
        # Generate unique ID
        import hashlib
        atom_id = hashlib.md5(
            f"{parent_id}_{node.type}_{node.start_byte}".encode()
        ).hexdigest()[:16]
        
        # Analyze code
        inputs, outputs = self._analyze_io(node, code)
        is_pure = self._is_pure_function(node)
        is_deterministic = self._is_deterministic(node)
        complexity = self._calculate_node_complexity(node)
        
        # Create unit
        return AtomicUnit(
            id=atom_id,
            purpose=f"Atomic {node.type}",  # TODO: Better description
            code=code,
            language=language,
            parent_id=parent_id,
            inputs=inputs,
            outputs=outputs,
            context={},  # TODO: Context injection
            level=depth,
            node_type=node.type,
            dependencies=[],  # TODO: Extract dependencies
            complexity=complexity,
            is_pure=is_pure,
            is_deterministic=is_deterministic,
            estimated_loc=code.count('\n')
        )
    
    def _has_single_responsibility(self, node: tree_sitter.Node) -> bool:
        """
        Verifica responsabilidad única.
        """
        # Contar diferentes tipos de operaciones
        operation_types = set()
        
        for child in node.children:
            if child.type in ['assignment', 'augmented_assignment']:
                operation_types.add('mutation')
            elif child.type in ['call_expression']:
                operation_types.add('function_call')
            elif child.type in ['if_statement', 'while_statement', 'for_statement']:
                operation_types.add('control_flow')
            elif child.type in ['return_statement']:
                operation_types.add('return')
        
        # Single responsibility = max 2 tipos de operaciones
        return len(operation_types) <= 2
    
    def _has_branching(self, node: tree_sitter.Node) -> bool:
        """
        Verifica si tiene branching.
        """
        branching_types = ['if_statement', 'conditional_expression', 'switch_statement']
        
        for child in node.children:
            if child.type in branching_types:
                return True
        
        return False
    
    def _has_loops(self, node: tree_sitter.Node) -> bool:
        """
        Verifica si tiene loops.
        """
        loop_types = ['for_statement', 'while_statement', 'do_statement']
        
        for child in node.children:
            if child.type in loop_types:
                return True
        
        return False
    
    def _is_pure_or_simple(self, node: tree_sitter.Node) -> bool:
        """
        Verifica si es función pura o simple.
        """
        # TODO: Implementar detección de:
        # - No side effects
        # - No state mutations
        # - Deterministic
        return True  # Placeholder
    
    def _calculate_node_complexity(self, node: tree_sitter.Node) -> float:
        """
        Calcula complejidad del nodo.
        """
        complexity = 1.0
        
        # Count control flow
        for child in node.children:
            if child.type in ['if_statement', 'for_statement', 'while_statement']:
                complexity += 1
        
        return complexity
    
    def _analyze_io(
        self,
        node: tree_sitter.Node,
        code: str
    ) -> tuple:
        """
        Analiza inputs y outputs.
        """
        # TODO: Implementar análisis real
        inputs = {}
        outputs = {}
        
        return inputs, outputs
    
    def _is_pure_function(self, node: tree_sitter.Node) -> bool:
        """
        Determina si es función pura.
        """
        # TODO: Implementar
        return False
    
    def _is_deterministic(self, node: tree_sitter.Node) -> bool:
        """
        Determina si es determinista.
        """
        # TODO: Buscar:
        # - random()
        # - Date.now()
        # - External state access
        return True
    
    def _get_nodes_at_cut_point(
        self,
        node: tree_sitter.Node,
        cut_point: CutPoint
    ) -> List[tree_sitter.Node]:
        """
        Obtiene nodos en un cut point.
        """
        # TODO: Implementar
        return list(node.children)
```

---

### 3. Context Injector

```python
# src/atomization/context_injector.py

from typing import Dict, List, Optional
from src.atomization.decomposer import AtomicUnit
from src.atomization.schema_registry import SchemaRegistry
import logging

logger = logging.getLogger(__name__)

class ContextInjector:
    """
    Inyecta TODO el contexto necesario en unidades atómicas
    para que sean 100% autocontenidas.
    """
    
    def __init__(self):
        self.schema_registry = SchemaRegistry()
    
    def inject_context(
        self,
        atom: AtomicUnit,
        project_context: Dict
    ) -> AtomicUnit:
        """
        Inyecta contexto completo en unidad atómica.
        """
        logger.debug(f"Injecting context for atom {atom.id}")
        
        enriched_context = {}
        
        # 1. Data context (schemas, types, constants)
        enriched_context['data'] = self._inject_data_context(atom, project_context)
        
        # 2. Behavior context (preconditions, postconditions, invariants)
        enriched_context['behavior'] = self._inject_behavior_context(atom)
        
        # 3. Implementation context (patterns, algorithms, best practices)
        enriched_context['implementation'] = self._inject_implementation_context(atom)
        
        # 4. Environment context (language, dependencies, conventions)
        enriched_context['environment'] = self._inject_environment_context(atom, project_context)
        
        # 5. Testing context (test cases, assertions, mocks)
        enriched_context['testing'] = self._inject_testing_context(atom)
        
        # 6. Documentation context (descriptions, examples, see-also)
        enriched_context['documentation'] = self._inject_documentation_context(atom)
        
        # Update atom
        atom.context = enriched_context
        
        # Validate completeness
        is_complete, missing = self._validate_context_completeness(atom)
        if not is_complete:
            logger.warning(f"Context incomplete for atom {atom.id}: {missing}")
        
        return atom
    
    def _inject_data_context(
        self,
        atom: AtomicUnit,
        project_context: Dict
    ) -> Dict:
        """
        Inyecta contexto de datos.
        """
        data_context = {}
        
        # Schemas necesarios
        referenced_schemas = self._extract_referenced_schemas(atom)
        for schema_name in referenced_schemas:
            schema = self.schema_registry.get(schema_name)
            if schema:
                data_context['schemas'] = data_context.get('schemas', {})
                data_context['schemas'][schema_name] = schema
        
        # Types
        data_context['types'] = self._extract_required_types(atom)
        
        # Constants
        data_context['constants'] = self._extract_required_constants(atom, project_context)
        
        # Examples
        data_context['examples'] = self._generate_example_data(atom)
        
        return data_context
    
    def _inject_behavior_context(self, atom: AtomicUnit) -> Dict:
        """
        Inyecta contexto de comportamiento.
        """
        return {
            'preconditions': self._extract_preconditions(atom),
            'postconditions': self._extract_postconditions(atom),
            'invariants': self._extract_invariants(atom),
            'error_cases': self._identify_error_scenarios(atom),
            'edge_cases': self._identify_edge_cases(atom)
        }
    
    def _inject_implementation_context(self, atom: AtomicUnit) -> Dict:
        """
        Inyecta contexto de implementación.
        """
        return {
            'patterns': [],  # TODO: Find applicable patterns from RAG
            'algorithms': [],  # TODO: Suggest algorithms
            'optimizations': [],  # TODO: Identify optimizations
            'anti_patterns': [],  # TODO: Warn about anti-patterns
            'best_practices': []  # TODO: Get best practices for this type
        }
    
    def _inject_environment_context(
        self,
        atom: AtomicUnit,
        project_context: Dict
    ) -> Dict:
        """
        Inyecta contexto de entorno.
        """
        return {
            'language': atom.language.value,
            'version': project_context.get('language_version', 'latest'),
            'runtime': self._get_runtime_requirements(atom),
            'dependencies': self._resolve_dependencies(atom),
            'imports': self._generate_imports(atom),
            'conventions': project_context.get('conventions', {}),
            'constraints': project_context.get('constraints', {})
        }
    
    def _inject_testing_context(self, atom: AtomicUnit) -> Dict:
        """
        Inyecta contexto de testing.
        """
        return {
            'test_cases': self._generate_test_cases(atom),
            'assertions': self._generate_assertions(atom),
            'mocks': self._identify_required_mocks(atom),
            'fixtures': self._generate_fixtures(atom),
            'coverage_target': 0.90,
            'performance_benchmarks': self._get_performance_targets(atom)
        }
    
    def _inject_documentation_context(self, atom: AtomicUnit) -> Dict:
        """
        Inyecta contexto de documentación.
        """
        return {
            'description': self._generate_description(atom),
            'parameters': self._document_parameters(atom),
            'returns': self._document_returns(atom),
            'throws': self._document_exceptions(atom),
            'examples': self._generate_usage_examples(atom),
            'see_also': []  # TODO: Find related atoms
        }
    
    def _validate_context_completeness(
        self,
        atom: AtomicUnit
    ) -> tuple:
        """
        Valida que el contexto esté completo.
        """
        required_keys = [
            ('data', 'schemas'),
            ('data', 'types'),
            ('behavior', 'preconditions'),
            ('environment', 'language'),
            ('environment', 'imports')
        ]
        
        missing = []
        
        for section, key in required_keys:
            if section not in atom.context:
                missing.append(f"{section}")
            elif key not in atom.context[section]:
                missing.append(f"{section}.{key}")
        
        is_complete = len(missing) == 0
        
        return is_complete, missing
    
    # Helper methods (placeholders - TODO: implementar)
    
    def _extract_referenced_schemas(self, atom: AtomicUnit) -> List[str]:
        """Extrae schemas referenciados en el código."""
        # TODO: Parse code y extraer referencias a modelos/schemas
        return []
    
    def _extract_required_types(self, atom: AtomicUnit) -> Dict:
        """Extrae tipos necesarios."""
        return {}
    
    def _extract_required_constants(self, atom: AtomicUnit, project_context: Dict) -> Dict:
        """Extrae constantes necesarias."""
        return {}
    
    def _generate_example_data(self, atom: AtomicUnit) -> List[Dict]:
        """Genera datos de ejemplo."""
        return []
    
    def _extract_preconditions(self, atom: AtomicUnit) -> List[str]:
        """Extrae precondiciones."""
        return []
    
    def _extract_postconditions(self, atom: AtomicUnit) -> List[str]:
        """Extrae postcondiciones."""
        return []
    
    def _extract_invariants(self, atom: AtomicUnit) -> List[str]:
        """Extrae invariantes."""
        return []
    
    def _identify_error_scenarios(self, atom: AtomicUnit) -> List[Dict]:
        """Identifica escenarios de error."""
        return []
    
    def _identify_edge_cases(self, atom: AtomicUnit) -> List[Dict]:
        """Identifica edge cases."""
        return []
    
    def _get_runtime_requirements(self, atom: AtomicUnit) -> Dict:
        """Obtiene requerimientos de runtime."""
        return {}
    
    def _resolve_dependencies(self, atom: AtomicUnit) -> List[str]:
        """Resuelve dependencias."""
        return []
    
    def _generate_imports(self, atom: AtomicUnit) -> List[str]:
        """Genera imports necesarios."""
        return []
    
    def _generate_test_cases(self, atom: AtomicUnit) -> List[Dict]:
        """Genera casos de prueba."""
        return []
    
    def _generate_assertions(self, atom: AtomicUnit) -> List[str]:
        """Genera assertions."""
        return []
    
    def _identify_required_mocks(self, atom: AtomicUnit) -> List[Dict]:
        """Identifica mocks necesarios."""
        return []
    
    def _generate_fixtures(self, atom: AtomicUnit) -> List[Dict]:
        """Genera fixtures."""
        return []
    
    def _get_performance_targets(self, atom: AtomicUnit) -> Dict:
        """Obtiene targets de performance."""
        return {}
    
    def _generate_description(self, atom: AtomicUnit) -> str:
        """Genera descripción."""
        return f"Atomic unit for {atom.node_type}"
    
    def _document_parameters(self, atom: AtomicUnit) -> List[Dict]:
        """Documenta parámetros."""
        return []
    
    def _document_returns(self, atom: AtomicUnit) -> Dict:
        """Documenta retorno."""
        return {}
    
    def _document_exceptions(self, atom: AtomicUnit) -> List[str]:
        """Documenta excepciones."""
        return []
    
    def _generate_usage_examples(self, atom: AtomicUnit) -> List[str]:
        """Genera ejemplos de uso."""
        return []
```

---

### 4. Atomicity Validator

```python
# src/atomization/validator.py

from typing import Dict, List, Tuple
from src.atomization.decomposer import AtomicUnit
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationIssue:
    """
    Issue encontrado en validación.
    """
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'independence', 'determinism', etc.
    message: str
    details: Dict
    fix_suggestion: Optional[str]

@dataclass
class ValidationResult:
    """
    Resultado de validación de atomicidad.
    """
    unit_id: str
    is_atomic: bool
    atomicity_score: float  # 0.0 - 1.0
    issues: List[ValidationIssue]
    passed_criteria: Dict[str, bool]
    can_be_parallelized: bool
    estimated_complexity: float

class AtomicityValidator:
    """
    Valida que las unidades sean VERDADERAMENTE atómicas.
    """
    
    def __init__(self):
        self.min_atomicity_score = 0.95  # 95% threshold
    
    def validate(self, unit: AtomicUnit) -> ValidationResult:
        """
        Validación exhaustiva de atomicidad.
        """
        logger.debug(f"Validating atomicity for unit {unit.id}")
        
        issues = []
        criteria = {}
        
        # 1. Independence (no external dependencies)
        independence_result = self._validate_independence(unit)
        criteria['independence'] = independence_result['passed']
        issues.extend(independence_result['issues'])
        
        # 2. Determinism (same input → same output)
        determinism_result = self._validate_determinism(unit)
        criteria['determinism'] = determinism_result['passed']
        issues.extend(determinism_result['issues'])
        
        # 3. Single Purpose
        single_purpose_result = self._validate_single_purpose(unit)
        criteria['single_purpose'] = single_purpose_result['passed']
        issues.extend(single_purpose_result['issues'])
        
        # 4. Context Completeness
        completeness_result = self._validate_completeness(unit)
        criteria['completeness'] = completeness_result['passed']
        issues.extend(completeness_result['issues'])
        
        # 5. Idempotency
        idempotency_result = self._validate_idempotency(unit)
        criteria['idempotency'] = idempotency_result['passed']
        issues.extend(idempotency_result['issues'])
        
        # 6. Minimal Granularity
        granularity_result = self._validate_granularity(unit)
        criteria['granularity'] = granularity_result['passed']
        issues.extend(granularity_result['issues'])
        
        # Calculate atomicity score
        atomicity_score = self._calculate_atomicity_score(criteria)
        
        # Determine if can be parallelized
        can_parallelize = self._check_parallelization_safety(criteria, unit)
        
        # Final verdict
        is_atomic = atomicity_score >= self.min_atomicity_score
        
        return ValidationResult(
            unit_id=unit.id,
            is_atomic=is_atomic,
            atomicity_score=atomicity_score,
            issues=issues,
            passed_criteria=criteria,
            can_be_parallelized=can_parallelize,
            estimated_complexity=unit.complexity
        )
    
    def _validate_independence(self, unit: AtomicUnit) -> Dict:
        """
        Valida que no haya dependencias ocultas.
        """
        issues = []
        
        # Check for external references not in context
        external_refs = self._scan_external_references(unit)
        
        for ref in external_refs:
            if not self._is_in_context(ref, unit.context):
                issues.append(ValidationIssue(
                    severity='critical',
                    category='independence',
                    message=f"External reference '{ref}' not in context",
                    details={'reference': ref},
                    fix_suggestion="Add reference to context"
                ))
        
        # Check for global state access
        if self._accesses_global_state(unit):
            issues.append(ValidationIssue(
                severity='critical',
                category='independence',
                message="Accesses global state",
                details={},
                fix_suggestion="Pass state as parameter"
            ))
        
        passed = len(issues) == 0
        
        return {'passed': passed, 'issues': issues}
    
    def _validate_determinism(self, unit: AtomicUnit) -> Dict:
        """
        Valida determinismo.
        """
        issues = []
        
        # Check for non-deterministic operations
        non_deterministic = [
            'random', 'uuid', 'Date.now', 'time.time',
            'Math.random', 'datetime.now'
        ]
        
        for pattern in non_deterministic:
            if pattern in unit.code:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='determinism',
                    message=f"Uses non-deterministic operation: {pattern}",
                    details={'pattern': pattern},
                    fix_suggestion="Accept value as parameter instead"
                ))
        
        passed = len(issues) == 0
        
        return {'passed': passed, 'issues': issues}
    
    def _validate_single_purpose(self, unit: AtomicUnit) -> Dict:
        """
        Valida responsabilidad única.
        """
        issues = []
        
        # Check complexity
        if unit.complexity > 3.0:
            issues.append(ValidationIssue(
                severity='warning',
                category='single_purpose',
                message=f"Complexity too high: {unit.complexity}",
                details={'complexity': unit.complexity},
                fix_suggestion="Further decompose into simpler units"
            ))
        
        # Check lines of code
        if unit.estimated_loc > 10:
            issues.append(ValidationIssue(
                severity='warning',
                category='single_purpose',
                message=f"Too many lines: {unit.estimated_loc}",
                details={'loc': unit.estimated_loc},
                fix_suggestion="Split into multiple atomic units"
            ))
        
        passed = unit.complexity <= 3.0 and unit.estimated_loc <= 10
        
        return {'passed': passed, 'issues': issues}
    
    def _validate_completeness(self, unit: AtomicUnit) -> Dict:
        """
        Valida que el contexto esté completo.
        """
        issues = []
        
        required_sections = ['data', 'behavior', 'environment', 'testing']
        
        for section in required_sections:
            if section not in unit.context:
                issues.append(ValidationIssue(
                    severity='critical',
                    category='completeness',
                    message=f"Missing context section: {section}",
                    details={'section': section},
                    fix_suggestion=f"Add {section} context"
                ))
        
        passed = len(issues) == 0
        
        return {'passed': passed, 'issues': issues}
    
    def _validate_idempotency(self, unit: AtomicUnit) -> Dict:
        """
        Valida idempotencia.
        """
        issues = []
        
        # Check if unit mutates external state
        if self._mutates_external_state(unit):
            issues.append(ValidationIssue(
                severity='warning',
                category='idempotency',
                message="Mutates external state",
                details={},
                fix_suggestion="Make pure or document side effects"
            ))
        
        passed = len(issues) == 0
        
        return {'passed': passed, 'issues': issues}
    
    def _validate_granularity(self, unit: AtomicUnit) -> Dict:
        """
        Valida granularidad mínima.
        """
        issues = []
        
        # Check if can be further decomposed
        if self._can_decompose_further(unit):
            issues.append(ValidationIssue(
                severity='info',
                category='granularity',
                message="Can be further decomposed",
                details={},
                fix_suggestion="Consider further atomization"
            ))
        
        passed = True  # Granularity is not a hard requirement
        
        return {'passed': passed, 'issues': issues}
    
    def _calculate_atomicity_score(self, criteria: Dict[str, bool]) -> float:
        """
        Calcula score de atomicidad.
        """
        # Pesos por criterio
        weights = {
            'independence': 0.25,
            'determinism': 0.20,
            'single_purpose': 0.20,
            'completeness': 0.15,
            'idempotency': 0.10,
            'granularity': 0.10
        }
        
        score = 0.0
        for criterion, passed in criteria.items():
            if passed:
                score += weights.get(criterion, 0.0)
        
        return round(score, 3)
    
    def _check_parallelization_safety(
        self,
        criteria: Dict[str, bool],
        unit: AtomicUnit
    ) -> bool:
        """
        Verifica si puede ejecutarse en paralelo.
        """
        # Debe ser independiente y determinista
        safe = (
            criteria.get('independence', False) and
            criteria.get('determinism', False) and
            not self._has_shared_state(unit)
        )
        
        return safe
    
    # Helper methods (placeholders)
    
    def _scan_external_references(self, unit: AtomicUnit) -> List[str]:
        """Escanea referencias externas."""
        # TODO: Parse código y extraer referencias
        return []
    
    def _is_in_context(self, ref: str, context: Dict) -> bool:
        """Verifica si referencia está en contexto."""
        # TODO: Buscar en todas las secciones del contexto
        return True
    
    def _accesses_global_state(self, unit: AtomicUnit) -> bool:
        """Verifica acceso a estado global."""
        global_patterns = ['global ', 'window.', 'document.', 'process.']
        return any(p in unit.code for p in global_patterns)
    
    def _mutates_external_state(self, unit: AtomicUnit) -> bool:
        """Verifica mutación de estado externo."""
        # TODO: Analizar AST para detectar mutaciones
        return False
    
    def _can_decompose_further(self, unit: AtomicUnit) -> bool:
        """Verifica si puede descomponerse más."""
        return unit.complexity > 1.0 or unit.estimated_loc > 5
    
    def _has_shared_state(self, unit: AtomicUnit) -> bool:
        """Verifica si tiene estado compartido."""
        # TODO: Detectar variables compartidas
        return False
```

---

## 🎯 Integration con Neo4j

```python
# src/atomization/graph_builder.py

from neo4j import GraphDatabase
from typing import List, Dict
from src.atomization.decomposer import AtomicUnit
import logging

logger = logging.getLogger(__name__)

class CognitiveGraphBuilder:
    """
    Construye grafo cognitivo en Neo4j.
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def build_graph(
        self,
        atoms: List[AtomicUnit],
        project_id: str
    ):
        """
        Construye grafo de unidades atómicas.
        """
        with self.driver.session() as session:
            # Create project node
            session.write_transaction(
                self._create_project_node,
                project_id
            )
            
            # Create atomic unit nodes
            for atom in atoms:
                session.write_transaction(
                    self._create_atomic_unit_node,
                    project_id,
                    atom
                )
            
            # Create dependency edges
            for atom in atoms:
                for dep_id in atom.dependencies:
                    session.write_transaction(
                        self._create_dependency_edge,
                        atom.id,
                        dep_id
                    )
            
            logger.info(f"✅ Graph built with {len(atoms)} nodes")
    
    @staticmethod
    def _create_project_node(tx, project_id: str):
        """
        Crea nodo de proyecto.
        """
        query = """
        CREATE (p:Project {id: $project_id, created_at: datetime()})
        RETURN p
        """
        result = tx.run(query, project_id=project_id)
        return result.single()
    
    @staticmethod
    def _create_atomic_unit_node(tx, project_id: str, atom: AtomicUnit):
        """
        Crea nodo de unidad atómica.
        """
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (a:AtomicUnit {
            id: $atom_id,
            purpose: $purpose,
            code: $code,
            language: $language,
            level: $level,
            node_type: $node_type,
            complexity: $complexity,
            is_pure: $is_pure,
            is_deterministic: $is_deterministic,
            estimated_loc: $estimated_loc
        })
        CREATE (p)-[:CONTAINS]->(a)
        RETURN a
        """
        result = tx.run(
            query,
            project_id=project_id,
            atom_id=atom.id,
            purpose=atom.purpose,
            code=atom.code,
            language=atom.language.value,
            level=atom.level,
            node_type=atom.node_type,
            complexity=atom.complexity,
            is_pure=atom.is_pure,
            is_deterministic=atom.is_deterministic,
            estimated_loc=atom.estimated_loc
        )
        return result.single()
    
    @staticmethod
    def _create_dependency_edge(tx, from_id: str, to_id: str):
        """
        Crea arista de dependencia.
        """
        query = """
        MATCH (a1:AtomicUnit {id: $from_id})
        MATCH (a2:AtomicUnit {id: $to_id})
        CREATE (a1)-[:DEPENDS_ON]->(a2)
        RETURN a1, a2
        """
        result = tx.run(query, from_id=from_id, to_id=to_id)
        return result.single()
    
    def query_execution_order(self, project_id: str) -> List[str]:
        """
        Obtiene orden de ejecución usando topological sort.
        """
        with self.driver.session() as session:
            result = session.read_transaction(
                self._topological_sort,
                project_id
            )
            return result
    
    @staticmethod
    def _topological_sort(tx, project_id: str):
        """
        Topological sort del grafo.
        """
        query = """
        MATCH (p:Project {id: $project_id})-[:CONTAINS]->(a:AtomicUnit)
        WITH a
        MATCH path = (a)-[:DEPENDS_ON*0..]->(dep)
        WITH a, length(path) as depth
        ORDER BY depth DESC
        RETURN a.id as atom_id
        """
        result = tx.run(query, project_id=project_id)
        return [record['atom_id'] for record in result]
    
    def close(self):
        """
        Cierra conexión.
        """
        self.driver.close()
```

---

## 📅 Timeline de Implementación

### Fase 1: Parsers y AST (Meses 1-2)
- **Mes 1**: Setup y Python parser
  - [ ] tree-sitter setup
  - [ ] Python AST parser
  - [ ] Basic node traversal
  - [ ] Testing suite

- **Mes 2**: Multi-language support
  - [ ] JavaScript/TypeScript parser
  - [ ] SQL parser
  - [ ] Unified interface
  - [ ] Comprehensive tests

### Fase 2: Decomposer (Meses 3-4)
- **Mes 3**: Recursive decomposition
  - [ ] Cut point detection
  - [ ] Recursive algorithm
  - [ ] Atomicity heuristics
  - [ ] Unit tests

- **Mes 4**: Advanced decomposition
  - [ ] Function decomposition
  - [ ] Conditional decomposition
  - [ ] Loop decomposition
  - [ ] Integration tests

### Fase 3: Context Injection (Meses 5-6)
- **Mes 5**: Context builder
  - [ ] Schema registry
  - [ ] Type extraction
  - [ ] Dependency resolution
  - [ ] Testing framework

- **Mes 6**: Complete injection
  - [ ] All context sections
  - [ ] Validation
  - [ ] Documentation
  - [ ] E2E tests

### Fase 4: Validation & Graph (Meses 7-8)
- **Mes 7**: Atomicity validator
  - [ ] 10 validation criteria
  - [ ] Auto-fix suggestions
  - [ ] Scoring system
  - [ ] Tests

- **Mes 8**: Neo4j integration
  - [ ] Graph builder
  - [ ] Query interface
  - [ ] Visualization
  - [ ] Performance optimization

### Fase 5: Production (Mes 9)
- **Mes 9**: Integration y deployment
  - [ ] Integration con orchestrator
  - [ ] Parallel execution
  - [ ] Monitoring
  - [ ] Documentation completa

---

## 🎯 Métricas de Éxito

### Atomización
```
Average atoms per 100 LOC: 50-100
Atomicity score average: >0.95
Context completeness: 100%
Parallelizable atoms: >90%
```

### Performance
```
Parsing time: <1s per 1000 LOC
Decomposition time: <5s per 1000 LOC
Context injection: <2s per atom
Validation: <1s per atom
```

### Quality
```
False atomics: <5%
Context errors: <1%
Dependency errors: <2%
Validation accuracy: >95%
```

---

## 🚀 Conclusión

La atomización profunda con AST es el **núcleo técnico diferenciador** de DevMatrix. Permite:

✅ **Paralelización real**: 100+ agentes ejecutando simultáneamente
✅ **Precisión extrema**: 99% objetivo alcanzable
✅ **Autocontención total**: Unidades 100% independientes
✅ **Validación rigurosa**: 10 criterios de atomicidad
✅ **Escalabilidad**: Millones de átomos en grafo

**Investment**: 6-9 meses dev time
**ROI**: Base para el verdadero DevMatrix del plan original

¿Listo para empezar con el Parser multi-lenguaje? 🚀