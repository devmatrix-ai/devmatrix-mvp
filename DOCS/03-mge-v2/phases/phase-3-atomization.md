# Phase 3: AST Atomization

**Document**: 05 of 15
**Purpose**: Detailed implementation of AST parsing and recursive decomposition

---

## Overview

**Phase 3 is the HEART of MGE v2** - it breaks tasks into atomic units using Abstract Syntax Tree (AST) parsing.

**Goal**: Transform 25 LOC subtasks → ~10 LOC atomic units with 95% context completeness

---

## Architecture

```
Task (80 LOC)
└─> Subtasks (25 LOC each)
    └─> AST Parser (tree-sitter)
        └─> Recursive Decomposer
            └─> AtomicUnits (~10 LOC each)
                └─> Context Injector (95%)
                    └─> Validation
                        └─> Store in PostgreSQL
```

---

## Component 1: AST Parser

### Technology: tree-sitter

**Why tree-sitter?**
- Multi-language support (40+ languages)
- Fast (written in C)
- Incremental parsing
- Error-tolerant
- Battle-tested (VS Code, GitHub use it)

### Installation

```bash
pip install tree-sitter==0.20.4
pip install tree-sitter-python==0.20.4
pip install tree-sitter-typescript==0.20.4
pip install tree-sitter-javascript==0.20.4
```

### Basic Usage

```python
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

# Build language
PY_LANGUAGE = Language(tspython.language(), "python")

# Create parser
parser = Parser()
parser.set_language(PY_LANGUAGE)

# Parse code
code = b"""
def calculate_total(price: float, tax: float) -> float:
    return price * (1 + tax)
"""

tree = parser.parse(code)
root_node = tree.root_node

print(root_node.sexp())
```

**Output (S-expression)**:
```
(module
  (function_definition
    name: (identifier)
    parameters: (parameters
      (typed_parameter (identifier) (type (identifier)))
      (typed_parameter (identifier) (type (identifier))))
    return_type: (type (identifier))
    body: (block
      (return_statement
        (binary_operator
          (identifier)
          (parenthesized_expression
            (binary_operator (integer) (identifier))))))))
```

### Multi-Language Parser Factory

```python
from pathlib import Path
from typing import Optional
import tree_sitter_python as tspython
import tree_sitter_typescript as tstype
import tree_sitter_javascript as tsjs

class MultiLanguageParser:
    """
    Factory for creating language-specific parsers.
    """

    LANGUAGE_MAP = {
        '.py': ('python', tspython.language()),
        '.ts': ('typescript', tstype.language_typescript()),
        '.tsx': ('tsx', tstype.language_tsx()),
        '.js': ('javascript', tsjs.language()),
        '.jsx': ('jsx', tsjs.language()),
    }

    def __init__(self):
        self.parsers = {}
        self._initialize_parsers()

    def _initialize_parsers(self):
        """Initialize parsers for all supported languages."""
        for ext, (lang_name, lang_func) in self.LANGUAGE_MAP.items():
            language = Language(lang_func, lang_name)
            parser = Parser()
            parser.set_language(language)
            self.parsers[ext] = parser

    def parse_file(self, file_path: str) -> Optional[tuple]:
        """
        Parse a file and return (tree, language).

        Returns:
            tuple: (tree, language_name) or None if unsupported
        """
        path = Path(file_path)
        ext = path.suffix

        if ext not in self.parsers:
            raise ValueError(f"Unsupported file type: {ext}")

        # Read file
        with open(file_path, 'rb') as f:
            code = f.read()

        # Parse
        parser = self.parsers[ext]
        tree = parser.parse(code)
        lang_name = self.LANGUAGE_MAP[ext][0]

        return tree, lang_name

    def parse_code(self, code: str, language: str) -> Any:
        """
        Parse code string with specified language.

        Args:
            code: Source code string
            language: 'python', 'typescript', 'javascript'

        Returns:
            Parsed tree
        """
        # Find extension for language
        ext = None
        for e, (lang, _) in self.LANGUAGE_MAP.items():
            if lang == language:
                ext = e
                break

        if not ext:
            raise ValueError(f"Unsupported language: {language}")

        parser = self.parsers[ext]
        return parser.parse(code.encode('utf-8'))
```

---

## Component 2: Recursive Decomposer

### Decomposition Strategy

**Goal**: Break code into atomic units where each unit is:
1. **Single responsibility** (one function/class/method)
2. **~10 LOC** (5-15 acceptable)
3. **Self-contained** (minimal external dependencies)
4. **Testable** (can be validated independently)

### Node Type Classification

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class NodeClassification:
    """Classification of AST node for decomposition."""
    is_atomic: bool
    estimated_loc: int
    complexity: float
    node_type: str
    can_decompose: bool

class ASTClassifier:
    """
    Classify AST nodes for atomicity and decomposability.
    """

    # Atomic node types (cannot decompose further)
    ATOMIC_TYPES = {
        'import_statement',
        'import_from_statement',
        'expression_statement',
        'return_statement',
        'assert_statement',
        'pass_statement',
        'break_statement',
        'continue_statement'
    }

    # Composite node types (can decompose)
    COMPOSITE_TYPES = {
        'function_definition',
        'class_definition',
        'module',
        'if_statement',
        'for_statement',
        'while_statement',
        'try_statement',
        'with_statement'
    }

    def classify_node(self, node) -> NodeClassification:
        """
        Classify a node for decomposition strategy.
        """
        node_type = node.type
        loc = self._estimate_loc(node)
        complexity = self._estimate_complexity(node)

        # Check if atomic
        is_atomic = (
            node_type in self.ATOMIC_TYPES or
            (loc <= 15 and complexity <= 2.0)
        )

        # Check if can decompose
        can_decompose = (
            node_type in self.COMPOSITE_TYPES and
            not is_atomic
        )

        return NodeClassification(
            is_atomic=is_atomic,
            estimated_loc=loc,
            complexity=complexity,
            node_type=node_type,
            can_decompose=can_decompose
        )

    def _estimate_loc(self, node) -> int:
        """Estimate lines of code for node."""
        start_line = node.start_point[0]
        end_line = node.end_point[0]
        return end_line - start_line + 1

    def _estimate_complexity(self, node) -> float:
        """
        Estimate cyclomatic complexity.

        Base complexity + decision points (if, for, while, except, etc.)
        """
        complexity = 1.0

        # Count decision points
        decision_types = {
            'if_statement', 'elif_clause',
            'for_statement', 'while_statement',
            'except_clause', 'and', 'or'
        }

        def count_decisions(n):
            count = 0
            if n.type in decision_types:
                count += 1
            for child in n.children:
                count += count_decisions(child)
            return count

        complexity += count_decisions(node)

        return complexity
```

### Recursive Decomposition Algorithm

```python
from typing import List, Dict, Any
from uuid import uuid4

@dataclass
class AtomicUnit:
    """Represents an atomic code unit."""
    id: str
    task_id: str
    atom_number: int
    name: str
    description: str
    language: str
    code: str
    estimated_loc: int
    complexity: float
    node_type: str
    depends_on: List[str]
    context: Dict[str, Any]

class RecursiveDecomposer:
    """
    Recursively decompose AST into atomic units.
    """

    def __init__(self, classifier: ASTClassifier):
        self.classifier = classifier
        self.atoms = []
        self.atom_counter = 0

    def decompose_task(
        self,
        task_id: str,
        code: str,
        language: str,
        tree: Any
    ) -> List[AtomicUnit]:
        """
        Main entry point: decompose task code into atoms.

        Args:
            task_id: Task UUID
            code: Source code string
            language: 'python', 'typescript', etc.
            tree: Parsed tree-sitter tree

        Returns:
            List of AtomicUnits
        """
        self.atoms = []
        self.atom_counter = 0

        # Start recursive decomposition from root
        root_node = tree.root_node
        self._decompose_node(
            node=root_node,
            task_id=task_id,
            code=code,
            language=language,
            parent_context={}
        )

        return self.atoms

    def _decompose_node(
        self,
        node,
        task_id: str,
        code: str,
        language: str,
        parent_context: Dict[str, Any]
    ):
        """
        Recursively decompose a node.

        Strategy:
        1. Classify node
        2. If atomic → create AtomicUnit
        3. If composite → recurse on children
        """
        classification = self.classifier.classify_node(node)

        if classification.is_atomic:
            # Create atomic unit
            atom = self._create_atomic_unit(
                node=node,
                task_id=task_id,
                code=code,
                language=language,
                classification=classification,
                parent_context=parent_context
            )
            self.atoms.append(atom)

        elif classification.can_decompose:
            # Decompose further
            # Extract context for children
            child_context = self._extract_context(node, code, parent_context)

            # Recurse on children
            for child in node.children:
                if child.type not in ['comment', 'decorator']:
                    self._decompose_node(
                        node=child,
                        task_id=task_id,
                        code=code,
                        language=language,
                        parent_context=child_context
                    )

        else:
            # Leaf node that's not interesting (punctuation, etc.)
            pass

    def _create_atomic_unit(
        self,
        node,
        task_id: str,
        code: str,
        language: str,
        classification: NodeClassification,
        parent_context: Dict[str, Any]
    ) -> AtomicUnit:
        """
        Create an AtomicUnit from a node.
        """
        self.atom_counter += 1

        # Extract code text
        start_byte = node.start_byte
        end_byte = node.end_byte
        node_code = code[start_byte:end_byte]

        # Generate name and description
        name = self._generate_name(node, classification)
        description = self._generate_description(node, node_code)

        # Identify dependencies
        depends_on = self._identify_dependencies(node, parent_context)

        # Build context
        context = self._build_context(node, parent_context, node_code)

        return AtomicUnit(
            id=str(uuid4()),
            task_id=task_id,
            atom_number=self.atom_counter,
            name=name,
            description=description,
            language=language,
            code=node_code,
            estimated_loc=classification.estimated_loc,
            complexity=classification.complexity,
            node_type=classification.node_type,
            depends_on=depends_on,
            context=context
        )

    def _generate_name(self, node, classification: NodeClassification) -> str:
        """Generate human-readable name for atom."""
        if classification.node_type == 'function_definition':
            # Find function name
            for child in node.children:
                if child.type == 'identifier':
                    return f"Function: {child.text.decode('utf-8')}"

        elif classification.node_type == 'class_definition':
            for child in node.children:
                if child.type == 'identifier':
                    return f"Class: {child.text.decode('utf-8')}"

        elif classification.node_type == 'import_statement':
            return "Import dependencies"

        else:
            return f"{classification.node_type.replace('_', ' ').title()}"

    def _generate_description(self, node, code: str) -> str:
        """Generate description using LLM (simplified)."""
        # In real implementation, use Claude to generate description
        # For now, return first line or truncated code
        lines = code.strip().split('\n')
        if len(lines) > 0:
            first_line = lines[0]
            if len(first_line) > 100:
                return first_line[:100] + "..."
            return first_line
        return "Code unit"

    def _identify_dependencies(
        self,
        node,
        parent_context: Dict[str, Any]
    ) -> List[str]:
        """
        Identify which previous atoms this one depends on.

        Dependencies are based on:
        1. Variable references
        2. Function calls
        3. Class inheritance
        4. Import usage
        """
        dependencies = []

        # Get all identifiers in this node
        identifiers = self._extract_identifiers(node)

        # Check if any identifier was defined in previous atoms
        for atom in self.atoms:
            # Check if this atom defined any of the identifiers we use
            atom_defines = self._extract_definitions(atom.code)

            for identifier in identifiers:
                if identifier in atom_defines:
                    dependencies.append(atom.id)
                    break  # Don't add same atom twice

        return dependencies

    def _extract_identifiers(self, node) -> set:
        """Extract all identifier references in node."""
        identifiers = set()

        def traverse(n):
            if n.type == 'identifier':
                identifiers.add(n.text.decode('utf-8'))
            for child in n.children:
                traverse(child)

        traverse(node)
        return identifiers

    def _extract_definitions(self, code: str) -> set:
        """Extract all definitions in code (simplified)."""
        # In real implementation, parse and analyze properly
        # For now, simple regex for function/class/variable names
        import re

        definitions = set()

        # Functions
        func_pattern = r'def\s+(\w+)'
        definitions.update(re.findall(func_pattern, code))

        # Classes
        class_pattern = r'class\s+(\w+)'
        definitions.update(re.findall(class_pattern, code))

        # Variables (first assignment)
        var_pattern = r'^(\w+)\s*='
        definitions.update(re.findall(var_pattern, code, re.MULTILINE))

        return definitions

    def _extract_context(
        self,
        node,
        code: str,
        parent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract context information for children.

        Context includes:
        - Class name (if inside class)
        - Function name (if inside function)
        - Scope variables
        - Imports
        """
        context = parent_context.copy()

        if node.type == 'class_definition':
            # Extract class name
            for child in node.children:
                if child.type == 'identifier':
                    context['class_name'] = child.text.decode('utf-8')

        elif node.type == 'function_definition':
            # Extract function name and parameters
            for child in node.children:
                if child.type == 'identifier':
                    context['function_name'] = child.text.decode('utf-8')
                elif child.type == 'parameters':
                    context['parameters'] = self._extract_parameters(child)

        return context

    def _extract_parameters(self, params_node) -> List[str]:
        """Extract parameter names from parameters node."""
        params = []
        for child in params_node.children:
            if child.type in ['identifier', 'typed_parameter']:
                if child.type == 'identifier':
                    params.append(child.text.decode('utf-8'))
                else:
                    # typed_parameter has identifier as first child
                    for c in child.children:
                        if c.type == 'identifier':
                            params.append(c.text.decode('utf-8'))
                            break
        return params

    def _build_context(
        self,
        node,
        parent_context: Dict[str, Any],
        code: str
    ) -> Dict[str, Any]:
        """
        Build complete context for this atomic unit.

        95% completeness target:
        - File path
        - Module imports
        - Class context (if in class)
        - Function context (if in function)
        - Dependencies
        - Type information
        - Documentation
        """
        context = {
            'parent_context': parent_context,
            'node_type': node.type,
            'start_line': node.start_point[0] + 1,
            'end_line': node.end_point[0] + 1,
        }

        # Add class context if available
        if 'class_name' in parent_context:
            context['class_name'] = parent_context['class_name']

        # Add function context if available
        if 'function_name' in parent_context:
            context['function_name'] = parent_context['function_name']
            context['parameters'] = parent_context.get('parameters', [])

        # Extract type hints (Python-specific)
        type_hints = self._extract_type_hints(node)
        if type_hints:
            context['type_hints'] = type_hints

        # Extract docstring
        docstring = self._extract_docstring(node)
        if docstring:
            context['docstring'] = docstring

        return context

    def _extract_type_hints(self, node) -> Dict[str, str]:
        """Extract type hints from node."""
        type_hints = {}

        # For function definitions, extract return type and parameter types
        if node.type == 'function_definition':
            for child in node.children:
                if child.type == 'type':
                    type_hints['return_type'] = child.text.decode('utf-8')

        return type_hints

    def _extract_docstring(self, node) -> Optional[str]:
        """Extract docstring from function/class."""
        if node.type in ['function_definition', 'class_definition']:
            # Look for string as first statement in body
            for child in node.children:
                if child.type == 'block':
                    for stmt in child.children:
                        if stmt.type == 'expression_statement':
                            for expr_child in stmt.children:
                                if expr_child.type == 'string':
                                    return expr_child.text.decode('utf-8').strip('"\'')

        return None
```

---

## Component 3: Context Injector

### Goal: 95% Context Completeness

**Context includes**:
1. **File-level**: Imports, module docstring, global variables
2. **Class-level**: Class name, inheritance, class variables
3. **Function-level**: Function name, parameters, return type, docstring
4. **Dependency-level**: What other atoms this depends on
5. **Type-level**: Type hints, expected input/output types
6. **Documentation-level**: Comments, docstrings, usage examples

### Implementation

```python
from typing import List, Dict, Any

class ContextInjector:
    """
    Inject comprehensive context into atomic units.

    Target: 95% completeness (vs 70% in MVP)
    """

    def __init__(self, parser: MultiLanguageParser):
        self.parser = parser

    def enrich_atoms(
        self,
        atoms: List[AtomicUnit],
        full_code: str,
        file_path: str,
        tree: Any
    ) -> List[AtomicUnit]:
        """
        Enrich all atoms with comprehensive context.
        """
        # Extract file-level context
        file_context = self._extract_file_context(tree, full_code, file_path)

        # Enrich each atom
        for atom in atoms:
            atom.context = self._enrich_atom_context(
                atom=atom,
                file_context=file_context,
                all_atoms=atoms
            )

        return atoms

    def _extract_file_context(
        self,
        tree: Any,
        code: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Extract file-level context.

        Returns:
            - imports: List of import statements
            - module_docstring: Module-level docstring
            - global_variables: Global variable definitions
            - file_path: Absolute file path
        """
        context = {
            'file_path': file_path,
            'imports': [],
            'module_docstring': None,
            'global_variables': []
        }

        root = tree.root_node

        # Extract imports
        for node in root.children:
            if node.type in ['import_statement', 'import_from_statement']:
                start = node.start_byte
                end = node.end_byte
                context['imports'].append(code[start:end])

        # Extract module docstring (first string in module)
        for node in root.children:
            if node.type == 'expression_statement':
                for child in node.children:
                    if child.type == 'string':
                        context['module_docstring'] = child.text.decode('utf-8')
                        break
                if context['module_docstring']:
                    break

        # Extract global variables
        for node in root.children:
            if node.type == 'expression_statement':
                # Look for assignment
                for child in node.children:
                    if child.type == 'assignment':
                        left = child.children[0]
                        if left.type == 'identifier':
                            var_name = left.text.decode('utf-8')
                            context['global_variables'].append(var_name)

        return context

    def _enrich_atom_context(
        self,
        atom: AtomicUnit,
        file_context: Dict[str, Any],
        all_atoms: List[AtomicUnit]
    ) -> Dict[str, Any]:
        """
        Enrich a single atom's context to 95% completeness.
        """
        enriched = atom.context.copy()

        # 1. File-level context (10% weight)
        enriched['file_context'] = {
            'file_path': file_context['file_path'],
            'imports': file_context['imports'],
            'module_docstring': file_context['module_docstring']
        }

        # 2. Dependency context (25% weight)
        enriched['dependencies'] = self._build_dependency_context(atom, all_atoms)

        # 3. Type context (15% weight)
        enriched['type_context'] = self._build_type_context(atom)

        # 4. Usage context (20% weight)
        enriched['usage_context'] = self._build_usage_context(atom, all_atoms)

        # 5. Documentation context (15% weight)
        enriched['documentation'] = self._build_documentation_context(atom)

        # 6. Validation context (15% weight)
        enriched['validation'] = self._build_validation_context(atom)

        # Calculate completeness score
        enriched['completeness_score'] = self._calculate_completeness(enriched)

        return enriched

    def _build_dependency_context(
        self,
        atom: AtomicUnit,
        all_atoms: List[AtomicUnit]
    ) -> Dict[str, Any]:
        """
        Build detailed dependency context.

        What does this atom depend on?
        - Functions it calls
        - Classes it instantiates
        - Variables it references
        """
        dependency_info = {
            'direct_dependencies': [],
            'dependency_types': {},
            'dependency_code': {}
        }

        for dep_id in atom.depends_on:
            # Find dependency atom
            dep_atom = next((a for a in all_atoms if a.id == dep_id), None)

            if dep_atom:
                dependency_info['direct_dependencies'].append({
                    'id': dep_id,
                    'name': dep_atom.name,
                    'type': dep_atom.node_type
                })

                # Store dependency code for context
                dependency_info['dependency_code'][dep_id] = dep_atom.code

                # Classify dependency type
                if 'function' in dep_atom.node_type.lower():
                    dependency_info['dependency_types'][dep_id] = 'function'
                elif 'class' in dep_atom.node_type.lower():
                    dependency_info['dependency_types'][dep_id] = 'class'
                else:
                    dependency_info['dependency_types'][dep_id] = 'other'

        return dependency_info

    def _build_type_context(self, atom: AtomicUnit) -> Dict[str, Any]:
        """
        Build type information context.

        For functions:
        - Parameter types
        - Return type
        - Type constraints

        For variables:
        - Inferred type
        - Type annotations
        """
        type_info = {
            'has_type_hints': False,
            'parameter_types': {},
            'return_type': None,
            'inferred_types': {}
        }

        # Extract from atom context
        if 'type_hints' in atom.context:
            type_info['has_type_hints'] = True
            type_info.update(atom.context['type_hints'])

        # Extract parameter types from code (Python type hints)
        if atom.node_type == 'function_definition':
            import re
            # Simple regex for type hints (full parser would be better)
            param_pattern = r'(\w+):\s*([^\),=]+)'
            matches = re.findall(param_pattern, atom.code)
            for param_name, param_type in matches:
                type_info['parameter_types'][param_name] = param_type.strip()

            # Return type
            return_pattern = r'->\s*([^:]+):'
            return_match = re.search(return_pattern, atom.code)
            if return_match:
                type_info['return_type'] = return_match.group(1).strip()

        return type_info

    def _build_usage_context(
        self,
        atom: AtomicUnit,
        all_atoms: List[AtomicUnit]
    ) -> Dict[str, Any]:
        """
        Build usage context: how is this atom used?

        - Which atoms depend on this one?
        - How many times is it called?
        - Usage patterns
        """
        usage_info = {
            'used_by': [],
            'usage_count': 0,
            'usage_patterns': []
        }

        # Find atoms that depend on this one
        for other_atom in all_atoms:
            if atom.id in other_atom.depends_on:
                usage_info['used_by'].append({
                    'id': other_atom.id,
                    'name': other_atom.name
                })
                usage_info['usage_count'] += 1

        return usage_info

    def _build_documentation_context(self, atom: AtomicUnit) -> Dict[str, Any]:
        """
        Build documentation context.

        - Docstrings
        - Inline comments
        - Purpose description
        """
        doc_info = {
            'has_docstring': False,
            'docstring': None,
            'inline_comments': [],
            'purpose': None
        }

        # Extract docstring
        if 'docstring' in atom.context:
            doc_info['has_docstring'] = True
            doc_info['docstring'] = atom.context['docstring']

        # Generate purpose description (using LLM in real implementation)
        doc_info['purpose'] = atom.description

        return doc_info

    def _build_validation_context(self, atom: AtomicUnit) -> Dict[str, Any]:
        """
        Build validation context.

        - Expected inputs
        - Expected outputs
        - Constraints
        - Test cases
        """
        validation_info = {
            'expected_inputs': [],
            'expected_outputs': [],
            'constraints': [],
            'test_cases': []
        }

        # For functions, extract parameters as expected inputs
        if atom.node_type == 'function_definition' and 'parameters' in atom.context:
            validation_info['expected_inputs'] = atom.context['parameters']

        # Extract constraints from docstring (if available)
        if 'docstring' in atom.context:
            docstring = atom.context['docstring']
            # Simple pattern matching for constraints
            if 'must' in docstring.lower() or 'should' in docstring.lower():
                validation_info['constraints'].append(docstring)

        return validation_info

    def _calculate_completeness(self, context: Dict[str, Any]) -> float:
        """
        Calculate context completeness score (0.0 - 1.0).

        Target: 0.95 (95%)

        Weights:
        - File context: 10%
        - Dependencies: 25%
        - Types: 15%
        - Usage: 20%
        - Documentation: 15%
        - Validation: 15%
        """
        score = 0.0

        # File context (10%)
        if context.get('file_context', {}).get('imports'):
            score += 0.10

        # Dependencies (25%)
        deps = context.get('dependencies', {})
        if deps.get('direct_dependencies'):
            score += 0.15
        if deps.get('dependency_code'):
            score += 0.10

        # Types (15%)
        types = context.get('type_context', {})
        if types.get('has_type_hints'):
            score += 0.10
        if types.get('parameter_types') or types.get('return_type'):
            score += 0.05

        # Usage (20%)
        usage = context.get('usage_context', {})
        if usage.get('used_by'):
            score += 0.10
        if usage.get('usage_count', 0) > 0:
            score += 0.10

        # Documentation (15%)
        docs = context.get('documentation', {})
        if docs.get('has_docstring'):
            score += 0.10
        if docs.get('purpose'):
            score += 0.05

        # Validation (15%)
        validation = context.get('validation', {})
        if validation.get('expected_inputs'):
            score += 0.08
        if validation.get('constraints'):
            score += 0.07

        return min(score, 1.0)
```

---

## Component 4: Atomicity Validator

### Validation Criteria

An atomic unit must satisfy:
1. **Single Responsibility**: Does one thing only
2. **Size**: 5-15 LOC (target 10)
3. **Complexity**: Cyclomatic complexity ≤ 3
4. **Independence**: Minimal external dependencies
5. **Testability**: Can be unit tested independently
6. **Clarity**: Clear purpose and behavior
7. **Completeness**: Has all necessary context (≥95%)
8. **Correctness**: Syntactically valid
9. **Consistency**: Follows project conventions
10. **Documentation**: Has description or docstring

### Implementation

```python
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of atomicity validation."""
    is_valid: bool
    score: float  # 0.0 - 1.0
    violations: List[str]
    warnings: List[str]

class AtomicityValidator:
    """
    Validate that units are truly atomic.
    """

    def validate_atom(self, atom: AtomicUnit) -> ValidationResult:
        """
        Validate a single atomic unit against 10 criteria.

        Returns:
            ValidationResult with pass/fail and details
        """
        violations = []
        warnings = []
        scores = []

        # 1. Single Responsibility (weight: 0.15)
        sr_score, sr_issues = self._check_single_responsibility(atom)
        scores.append(sr_score * 0.15)
        violations.extend(sr_issues)

        # 2. Size (weight: 0.10)
        size_score, size_issues = self._check_size(atom)
        scores.append(size_score * 0.10)
        if size_issues:
            warnings.extend(size_issues)

        # 3. Complexity (weight: 0.15)
        complexity_score, complexity_issues = self._check_complexity(atom)
        scores.append(complexity_score * 0.15)
        violations.extend(complexity_issues)

        # 4. Independence (weight: 0.10)
        indep_score, indep_issues = self._check_independence(atom)
        scores.append(indep_score * 0.10)
        if indep_issues:
            warnings.extend(indep_issues)

        # 5. Testability (weight: 0.10)
        test_score, test_issues = self._check_testability(atom)
        scores.append(test_score * 0.10)
        violations.extend(test_issues)

        # 6. Clarity (weight: 0.10)
        clarity_score, clarity_issues = self._check_clarity(atom)
        scores.append(clarity_score * 0.10)
        if clarity_issues:
            warnings.extend(clarity_issues)

        # 7. Completeness (weight: 0.10)
        complete_score, complete_issues = self._check_completeness(atom)
        scores.append(complete_score * 0.10)
        violations.extend(complete_issues)

        # 8. Correctness (weight: 0.10)
        correct_score, correct_issues = self._check_correctness(atom)
        scores.append(correct_score * 0.10)
        violations.extend(correct_issues)

        # 9. Consistency (weight: 0.05)
        consist_score, consist_issues = self._check_consistency(atom)
        scores.append(consist_score * 0.05)
        if consist_issues:
            warnings.extend(consist_issues)

        # 10. Documentation (weight: 0.05)
        doc_score, doc_issues = self._check_documentation(atom)
        scores.append(doc_score * 0.05)
        if doc_issues:
            warnings.extend(doc_issues)

        # Calculate total score
        total_score = sum(scores)

        # Pass if score >= 0.80 and no critical violations
        critical_violations = [v for v in violations if 'CRITICAL' in v]
        is_valid = total_score >= 0.80 and len(critical_violations) == 0

        return ValidationResult(
            is_valid=is_valid,
            score=total_score,
            violations=violations,
            warnings=warnings
        )

    def _check_single_responsibility(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check if atom has single responsibility."""
        issues = []
        score = 1.0

        # Heuristics:
        # - Function should do one thing
        # - No "and" in description
        # - Limited number of statements

        if ' and ' in atom.description.lower():
            issues.append("Description contains 'and' - may have multiple responsibilities")
            score -= 0.3

        # Count top-level statements
        statement_count = atom.code.count('\n    ') + 1  # Rough heuristic
        if statement_count > 10:
            issues.append("Too many statements - may have multiple responsibilities")
            score -= 0.4

        return max(score, 0.0), issues

    def _check_size(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check if size is appropriate (5-15 LOC)."""
        issues = []
        loc = atom.estimated_loc

        if loc < 5:
            issues.append(f"Too small ({loc} LOC) - may not be meaningful unit")
            score = 0.7
        elif loc > 15:
            issues.append(f"Too large ({loc} LOC) - should decompose further")
            score = 0.5
        elif 8 <= loc <= 12:
            score = 1.0  # Perfect size
        else:
            score = 0.9  # Acceptable

        return score, issues

    def _check_complexity(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check cyclomatic complexity."""
        issues = []
        complexity = atom.complexity

        if complexity <= 3:
            score = 1.0
        elif complexity <= 5:
            score = 0.8
            issues.append(f"Moderate complexity ({complexity}) - consider simplifying")
        else:
            score = 0.5
            issues.append(f"CRITICAL: High complexity ({complexity}) - must simplify")

        return score, issues

    def _check_independence(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check dependency count."""
        issues = []
        dep_count = len(atom.depends_on)

        if dep_count == 0:
            score = 1.0
        elif dep_count <= 3:
            score = 0.9
        elif dep_count <= 5:
            score = 0.7
            issues.append(f"Many dependencies ({dep_count}) - coupling may be high")
        else:
            score = 0.5
            issues.append(f"Too many dependencies ({dep_count}) - refactor needed")

        return score, issues

    def _check_testability(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check if unit can be tested independently."""
        issues = []
        score = 1.0

        # Check if function has parameters (easy to test)
        if atom.node_type == 'function_definition':
            if 'parameters' in atom.context and atom.context['parameters']:
                score = 1.0
            else:
                # No parameters - may be harder to test
                score = 0.8

        # Check if uses global state
        if 'global' in atom.code.lower():
            issues.append("Uses global state - reduces testability")
            score -= 0.3

        return max(score, 0.0), issues

    def _check_clarity(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check if purpose is clear."""
        issues = []
        score = 1.0

        # Check if has meaningful name
        if atom.name == "Code unit" or len(atom.name) < 5:
            issues.append("Unclear name")
            score -= 0.3

        # Check if has description
        if not atom.description or len(atom.description) < 10:
            issues.append("Insufficient description")
            score -= 0.3

        return max(score, 0.0), issues

    def _check_completeness(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check context completeness (target: 95%)."""
        issues = []

        completeness = atom.context.get('completeness_score', 0.0)

        if completeness < 0.90:
            issues.append(f"CRITICAL: Low context completeness ({completeness:.1%}) - target is 95%")
            score = completeness
        elif completeness < 0.95:
            issues.append(f"Context completeness ({completeness:.1%}) below target (95%)")
            score = completeness
        else:
            score = 1.0

        return score, issues

    def _check_correctness(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check syntactic correctness."""
        issues = []

        try:
            # For Python, try to parse
            if atom.language == 'python':
                import ast
                ast.parse(atom.code)
            score = 1.0
        except SyntaxError as e:
            issues.append(f"CRITICAL: Syntax error - {str(e)}")
            score = 0.0

        return score, issues

    def _check_consistency(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check coding style consistency."""
        issues = []
        score = 1.0

        # Check naming convention
        if atom.language == 'python':
            # Python uses snake_case for functions
            if atom.node_type == 'function_definition':
                func_name_match = re.search(r'def\s+(\w+)', atom.code)
                if func_name_match:
                    func_name = func_name_match.group(1)
                    if not func_name.islower() and '_' not in func_name:
                        issues.append("Function name not snake_case")
                        score -= 0.2

        return score, issues

    def _check_documentation(self, atom: AtomicUnit) -> Tuple[float, List[str]]:
        """Check documentation quality."""
        issues = []
        score = 1.0

        doc = atom.context.get('documentation', {})

        if not doc.get('has_docstring') and atom.node_type in ['function_definition', 'class_definition']:
            issues.append("Missing docstring")
            score -= 0.5

        return max(score, 0.0), issues
```

---

## Complete Workflow

### End-to-End Pipeline

```python
from typing import List

class ASTAtomizationPipeline:
    """
    Complete Phase 3 pipeline.
    """

    def __init__(self):
        self.parser = MultiLanguageParser()
        self.classifier = ASTClassifier()
        self.decomposer = RecursiveDecomposer(self.classifier)
        self.context_injector = ContextInjector(self.parser)
        self.validator = AtomicityValidator()

    def atomize_task(
        self,
        task_id: str,
        task_code: str,
        language: str,
        file_path: str
    ) -> List[AtomicUnit]:
        """
        Main entry point: atomize a task.

        Args:
            task_id: Task UUID
            task_code: Source code for task
            language: 'python', 'typescript', etc.
            file_path: File path for context

        Returns:
            List of validated AtomicUnits
        """
        print(f"📋 Atomizing task {task_id} ({language})...")

        # Step 1: Parse code to AST
        print("  1️⃣ Parsing AST...")
        tree = self.parser.parse_code(task_code, language)

        # Step 2: Recursive decomposition
        print("  2️⃣ Decomposing to atoms...")
        atoms = self.decomposer.decompose_task(
            task_id=task_id,
            code=task_code,
            language=language,
            tree=tree
        )
        print(f"     ✅ Generated {len(atoms)} atoms")

        # Step 3: Context injection
        print("  3️⃣ Injecting context (95% target)...")
        atoms = self.context_injector.enrich_atoms(
            atoms=atoms,
            full_code=task_code,
            file_path=file_path,
            tree=tree
        )

        avg_completeness = sum(a.context.get('completeness_score', 0) for a in atoms) / len(atoms)
        print(f"     ✅ Average context completeness: {avg_completeness:.1%}")

        # Step 4: Validation
        print("  4️⃣ Validating atomicity...")
        validated_atoms = []
        validation_failures = 0

        for atom in atoms:
            result = self.validator.validate_atom(atom)

            if result.is_valid:
                validated_atoms.append(atom)
            else:
                validation_failures += 1
                print(f"     ⚠️ Validation failed for {atom.name}:")
                for violation in result.violations:
                    print(f"        - {violation}")

        print(f"     ✅ {len(validated_atoms)}/{len(atoms)} atoms passed validation")

        if validation_failures > 0:
            print(f"     ⚠️ {validation_failures} atoms need refinement")

        return validated_atoms

    def save_to_database(self, atoms: List[AtomicUnit]):
        """
        Save atoms to PostgreSQL database.
        """
        import psycopg2
        import json

        conn = psycopg2.connect(
            host="localhost",
            database="devmatrix",
            user="devmatrix_user",
            password="password"
        )

        cursor = conn.cursor()

        for atom in atoms:
            cursor.execute("""
                INSERT INTO atomic_units (
                    id, task_id, atom_number, name, description,
                    language, estimated_loc, complexity, node_type,
                    depends_on, code, context_json
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                atom.id, atom.task_id, atom.atom_number, atom.name,
                atom.description, atom.language, atom.estimated_loc,
                atom.complexity, atom.node_type,
                atom.depends_on, atom.code,
                json.dumps(atom.context)
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"💾 Saved {len(atoms)} atoms to database")
```

---

## Testing Strategy

### Unit Tests

```python
import pytest

def test_ast_parser():
    """Test AST parsing."""
    parser = MultiLanguageParser()

    code = """
def add(a: int, b: int) -> int:
    return a + b
"""

    tree = parser.parse_code(code, 'python')
    assert tree is not None
    assert tree.root_node.type == 'module'

def test_decomposition():
    """Test recursive decomposition."""
    classifier = ASTClassifier()
    decomposer = RecursiveDecomposer(classifier)
    parser = MultiLanguageParser()

    code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""

    tree = parser.parse_code(code, 'python')
    atoms = decomposer.decompose_task(
        task_id='test-task',
        code=code,
        language='python',
        tree=tree
    )

    assert len(atoms) >= 1
    assert any('calculate_total' in a.name for a in atoms)

def test_context_injection():
    """Test context injection."""
    # Create test atom
    atom = AtomicUnit(
        id='test-atom',
        task_id='test-task',
        atom_number=1,
        name='Test Function',
        description='A test function',
        language='python',
        code='def test(): pass',
        estimated_loc=1,
        complexity=1.0,
        node_type='function_definition',
        depends_on=[],
        context={}
    )

    parser = MultiLanguageParser()
    injector = ContextInjector(parser)

    # Enrich
    enriched = injector.enrich_atoms(
        atoms=[atom],
        full_code='def test(): pass',
        file_path='test.py',
        tree=parser.parse_code('def test(): pass', 'python')
    )

    assert enriched[0].context.get('completeness_score', 0) > 0.5

def test_validation():
    """Test atomicity validation."""
    validator = AtomicityValidator()

    # Good atom
    good_atom = AtomicUnit(
        id='good',
        task_id='task',
        atom_number=1,
        name='Calculate Sum',
        description='Calculates sum of two numbers',
        language='python',
        code='def add(a: int, b: int) -> int:\n    return a + b',
        estimated_loc=2,
        complexity=1.0,
        node_type='function_definition',
        depends_on=[],
        context={'completeness_score': 0.95}
    )

    result = validator.validate_atom(good_atom)
    assert result.is_valid
    assert result.score > 0.8
```

---

## Performance Metrics

### Target Metrics

| Metric | Target | Why |
|--------|--------|-----|
| **Atoms per task** | 8-10 | 80 LOC task ÷ 10 LOC/atom |
| **Average atom size** | 10 LOC | Balance between granularity and overhead |
| **Context completeness** | ≥95% | Sufficient for accurate generation |
| **Validation pass rate** | ≥90% | Most atoms atomic on first try |
| **Processing time** | <5 sec/task | Fast enough for 150 tasks |

### Actual Results (Expected)

| Metric | Expected Result |
|--------|-----------------|
| Atoms per task | 8-12 |
| Average atom size | 8-11 LOC |
| Context completeness | 93-97% |
| Validation pass rate | 88-92% |
| Processing time | 3-6 sec/task |

---

## Next Phase

**Phase 4: Dependency Graph** → Build Neo4j graph, topological sort, parallel groups

---

**Next Document**: [06_PHASE_4_DEPENDENCY_GRAPH.md](06_PHASE_4_DEPENDENCY_GRAPH.md) - Dependency analysis and topological ordering
