"""
Context Injector - Complete execution context extraction

Extracts complete context for atomic units to achieve ≥95% context completeness.

Context includes:
- Imports: All required imports
- Type schema: Type definitions and interfaces
- Preconditions: Required state before execution
- Postconditions: Expected state after execution
- Test cases: Generated test cases for validation
- Dependency hints: References to other atoms

Author: DevMatrix Team
Date: 2025-10-23
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import re

from .parser import MultiLanguageParser, ParseResult
from .decomposer import AtomCandidate

logger = logging.getLogger(__name__)


@dataclass
class AtomContext:
    """Complete context for an atomic unit"""
    imports: Dict[str, List[str]]  # {module: [items]}
    type_schema: Dict[str, Any]    # Type definitions
    preconditions: Dict[str, Any]  # Required state before
    postconditions: Dict[str, Any] # Expected state after
    test_cases: List[Dict[str, Any]]  # Generated tests
    dependency_hints: List[str]    # Referenced symbols
    completeness_score: float      # 0.0-1.0
    missing_elements: List[str]    # What's missing


class ContextInjector:
    """
    Context injector for atomic units

    Extracts complete execution context:
    1. Import analysis (required modules)
    2. Type schema extraction (interfaces, types)
    3. Precondition inference (required state)
    4. Postcondition inference (expected results)
    5. Test case generation
    6. Dependency hint extraction

    Target: ≥95% context completeness
    """

    def __init__(self) -> None:
        """Initialize context injector"""
        self.parser = MultiLanguageParser()
        logger.info("ContextInjector initialized")

    def inject_context(
        self,
        atom: AtomCandidate,
        full_code: str,
        language: str,
        all_atoms: Optional[List[AtomCandidate]] = None
    ) -> AtomContext:
        """
        Inject complete context into atomic unit

        Args:
            atom: Atomic unit candidate
            full_code: Full source code (for context)
            language: Programming language
            all_atoms: All atoms in same task (for dependencies)

        Returns:
            AtomContext with complete execution context
        """
        logger.debug(f"Injecting context for atom: {atom.description}")

        # Parse full code for context
        parse_result = self.parser.parse(full_code, language)

        # Extract context elements
        imports = self._extract_imports(atom, full_code, parse_result)
        type_schema = self._extract_type_schema(atom, full_code, parse_result, language)
        preconditions = self._infer_preconditions(atom, language)
        postconditions = self._infer_postconditions(atom, language)
        test_cases = self._generate_test_cases(atom, language)
        dependency_hints = self._extract_dependency_hints(atom, all_atoms)

        # Calculate completeness score
        completeness_score, missing = self._calculate_completeness(
            imports, type_schema, preconditions, postconditions, test_cases
        )

        context = AtomContext(
            imports=imports,
            type_schema=type_schema,
            preconditions=preconditions,
            postconditions=postconditions,
            test_cases=test_cases,
            dependency_hints=dependency_hints,
            completeness_score=completeness_score,
            missing_elements=missing
        )

        logger.debug(f"Context completeness: {completeness_score:.2%}")
        return context

    def _extract_imports(
        self,
        atom: AtomCandidate,
        full_code: str,
        parse_result: ParseResult
    ) -> Dict[str, List[str]]:
        """Extract required imports for atom"""
        imports = {}

        # Get all imports from full code
        for import_stmt in parse_result.imports:
            module, items = self._parse_import_statement(import_stmt)
            if module:
                imports[module] = items

        # Filter to only imports used in atom code
        used_imports = {}
        for module, items in imports.items():
            used_items = [item for item in items if item in atom.code]
            if used_items or module in atom.code:
                used_imports[module] = used_items

        return used_imports

    def _parse_import_statement(self, import_stmt: str) -> tuple:
        """Parse import statement to extract module and items"""
        # Python: import module or from module import item1, item2
        if import_stmt.startswith('import '):
            module = import_stmt.replace('import ', '').strip()
            return module, []

        if import_stmt.startswith('from '):
            match = re.match(r'from\s+(\S+)\s+import\s+(.+)', import_stmt)
            if match:
                module = match.group(1)
                items = [item.strip() for item in match.group(2).split(',')]
                return module, items

        # TypeScript/JavaScript: import { item1, item2 } from 'module'
        if 'from' in import_stmt:
            match = re.match(r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]', import_stmt)
            if match:
                items = [item.strip() for item in match.group(1).split(',')]
                module = match.group(2)
                return module, items

        return None, []

    def _extract_type_schema(
        self,
        atom: AtomCandidate,
        full_code: str,
        parse_result: ParseResult,
        language: str
    ) -> Dict[str, Any]:
        """Extract type definitions and interfaces"""
        type_schema: Dict[str, Any] = {}

        if language == "python":
            # Extract type hints
            type_hints = self._extract_python_type_hints(atom.code)
            type_schema['hints'] = type_hints

        elif language in ["typescript", "javascript"]:
            # Extract interfaces and types
            interfaces = self._extract_ts_interfaces(atom.code)
            types = self._extract_ts_types(atom.code)
            type_schema['interfaces'] = interfaces
            type_schema['types'] = types

        return type_schema

    def _extract_python_type_hints(self, code: str) -> Dict[str, Any]:
        """Extract Python type hints"""
        hints: Dict[str, Any] = {}

        # Function signatures with types: def func(arg: Type) -> ReturnType
        pattern = r'def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*([^:]+))?:'
        matches = re.finditer(pattern, code)

        for match in matches:
            func_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3)

            hints[func_name] = {
                'params': params,
                'return': return_type.strip() if return_type else None
            }

        # Variable annotations: var: Type = value
        var_pattern = r'(\w+)\s*:\s*([^=\n]+)(?:=|$)'
        var_matches = re.finditer(var_pattern, code)

        for match in var_matches:
            var_name = match.group(1)
            var_type = match.group(2).strip()
            hints[var_name] = var_type

        return hints

    def _extract_ts_interfaces(self, code: str) -> List[Dict[str, Any]]:
        """Extract TypeScript interfaces"""
        interfaces: List[Dict[str, Any]] = []

        # interface Name { ... }
        pattern = r'interface\s+(\w+)\s*\{([^}]+)\}'
        matches = re.finditer(pattern, code, re.DOTALL)

        for match in matches:
            name = match.group(1)
            body = match.group(2)
            interfaces.append({'name': name, 'body': body.strip()})

        return interfaces

    def _extract_ts_types(self, code: str) -> List[Dict[str, Any]]:
        """Extract TypeScript type definitions"""
        types: List[Dict[str, Any]] = []

        # type Name = ...
        pattern = r'type\s+(\w+)\s*=\s*([^;\n]+)'
        matches = re.finditer(pattern, code)

        for match in matches:
            name = match.group(1)
            definition = match.group(2).strip()
            types.append({'name': name, 'definition': definition})

        return types

    def _infer_preconditions(self, atom: AtomCandidate, language: str) -> Dict[str, Any]:
        """Infer preconditions (required state before execution)"""
        preconditions: Dict[str, Any] = {
            'variables_required': [],
            'functions_required': [],
            'state_requirements': []
        }

        # Find variable references (not definitions)
        var_pattern = r'\b([a-zA-Z_]\w*)\b'
        variables = re.findall(var_pattern, atom.code)

        # Filter out definitions and keywords
        keywords = {'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'return', 'import', 'from', 'try', 'except'}
        used_vars = [v for v in set(variables) if v not in keywords and not v.startswith('_')]

        preconditions['variables_required'] = used_vars[:10]  # Limit to avoid noise

        # Find function calls
        func_pattern = r'(\w+)\s*\('
        functions = re.findall(func_pattern, atom.code)
        preconditions['functions_required'] = list(set(functions))[:5]

        return preconditions

    def _infer_postconditions(self, atom: AtomCandidate, language: str) -> Dict[str, Any]:
        """Infer postconditions (expected state after execution)"""
        postconditions: Dict[str, Any] = {
            'variables_created': [],
            'functions_defined': [],
            'side_effects': []
        }

        # Find variable definitions
        if language == "python":
            var_def_pattern = r'(\w+)\s*='
            definitions = re.findall(var_def_pattern, atom.code)
            postconditions['variables_created'] = list(set(definitions))

            # Find function definitions
            func_def_pattern = r'def\s+(\w+)'
            functions = re.findall(func_def_pattern, atom.code)
            postconditions['functions_defined'] = functions

        elif language in ["typescript", "javascript"]:
            # const/let/var declarations
            var_def_pattern = r'(?:const|let|var)\s+(\w+)'
            definitions = re.findall(var_def_pattern, atom.code)
            postconditions['variables_created'] = list(set(definitions))

            # Function declarations
            func_def_pattern = r'function\s+(\w+)|const\s+(\w+)\s*=\s*\('
            matches = re.findall(func_def_pattern, atom.code)
            functions = [m[0] or m[1] for m in matches if m[0] or m[1]]
            postconditions['functions_defined'] = functions

        # Detect side effects (I/O operations, mutations)
        side_effects = []
        if 'print(' in atom.code or 'console.log(' in atom.code:
            side_effects.append('stdout')
        if 'input(' in atom.code or 'prompt(' in atom.code:
            side_effects.append('stdin')
        if 'open(' in atom.code or 'fs.' in atom.code:
            side_effects.append('file_io')
        if 'requests.' in atom.code or 'fetch(' in atom.code:
            side_effects.append('network')

        postconditions['side_effects'] = side_effects

        return postconditions

    def _generate_test_cases(self, atom: AtomCandidate, language: str) -> List[Dict[str, Any]]:
        """Generate basic test cases for atom"""
        test_cases: List[Dict[str, Any]] = []

        # Basic test case structure
        test_case = {
            'name': f"test_{atom.description.replace(' ', '_').lower()}",
            'description': f"Test case for {atom.description}",
            'setup': "# Setup required state",
            'execution': "# Execute atom code",
            'assertions': ["# Assert expected results"],
            'generated': True
        }

        test_cases.append(test_case)

        # Add edge case tests
        if 'if' in atom.code:
            test_cases.append({
                'name': f"test_{atom.description.replace(' ', '_').lower()}_edge_cases",
                'description': "Edge case testing",
                'setup': "# Setup edge case conditions",
                'execution': "# Execute with edge cases",
                'assertions': ["# Assert edge case handling"],
                'generated': True
            })

        return test_cases

    def _extract_dependency_hints(
        self,
        atom: AtomCandidate,
        all_atoms: Optional[List[AtomCandidate]]
    ) -> List[str]:
        """Extract hints about dependencies on other atoms"""
        hints: List[str] = []

        if not all_atoms:
            return hints

        # Check if atom references functions/variables from other atoms
        for other_atom in all_atoms:
            if other_atom == atom:
                continue

            # Check for function calls
            for func in re.findall(r'def\s+(\w+)', other_atom.code):
                if f'{func}(' in atom.code:
                    hints.append(f"calls_{func}_from_atom_{other_atom.start_line}")

        return hints

    def _calculate_completeness(
        self,
        imports: Dict[str, List[str]],
        type_schema: Dict[str, Any],
        preconditions: Dict[str, Any],
        postconditions: Dict[str, Any],
        test_cases: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """
        Calculate context completeness score (0.0-1.0)

        Target: ≥0.95

        Scoring:
        - Imports present: 20%
        - Type schema present: 20%
        - Preconditions identified: 20%
        - Postconditions identified: 20%
        - Test cases generated: 20%
        """
        score = 0.0
        missing = []

        # Imports (20%)
        if imports:
            score += 0.20
        else:
            missing.append("imports")

        # Type schema (20%)
        if type_schema and any(type_schema.values()):
            score += 0.20
        else:
            missing.append("type_schema")

        # Preconditions (20%)
        if preconditions and any(preconditions.values()):
            score += 0.20
        else:
            missing.append("preconditions")

        # Postconditions (20%)
        if postconditions and any(postconditions.values()):
            score += 0.20
        else:
            missing.append("postconditions")

        # Test cases (20%)
        if test_cases:
            score += 0.20
        else:
            missing.append("test_cases")

        return score, missing
