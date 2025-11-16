"""
Multi-Language Parser - tree-sitter AST extraction

Parses Python, TypeScript, and JavaScript code using tree-sitter.

Features:
- AST extraction for 3 languages
- Complexity calculation (cyclomatic)
- LOC counting
- Function/class detection
- Syntax validation

Author: DevMatrix Team
Date: 2025-10-23
"""

import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_typescript as tstype
import tree_sitter_javascript as tsjs
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ASTNode:
    """Parsed AST node with metadata"""
    type: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    text: str
    children: List['ASTNode']

    @property
    def loc(self) -> int:
        """Lines of code"""
        return self.end_line - self.start_line + 1


@dataclass
class ParseResult:
    """Result of parsing code"""
    language: str
    ast: Optional[tree_sitter.Node]
    ast_nodes: List[ASTNode]
    functions: List[Dict]
    classes: List[Dict]
    imports: List[str]
    loc: int
    complexity: float
    errors: List[str]
    success: bool


class MultiLanguageParser:
    """
    Multi-language AST parser using tree-sitter

    Supports:
    - Python (.py)
    - TypeScript (.ts, .tsx)
    - JavaScript (.js, .jsx)
    """

    def __init__(self) -> None:
        """Initialize parsers for all supported languages"""
        # tree-sitter 0.25+ API: Language(capsule, name) and Parser(language)
        self.py_language = Language(tspython.language(), name="python")
        self.ts_language = Language(tstype.language_typescript(), name="typescript")
        self.js_language = Language(tsjs.language(), name="javascript")

        # Create parsers and set languages
        self.py_parser = Parser()
        self.py_parser.set_language(self.py_language)

        self.ts_parser = Parser()
        self.ts_parser.set_language(self.ts_language)

        self.js_parser = Parser()
        self.js_parser.set_language(self.js_language)

        logger.info("MultiLanguageParser initialized for Python, TypeScript, JavaScript")

    def parse(self, code: str, language: str) -> ParseResult:
        """
        Parse code in specified language

        Args:
            code: Source code to parse
            language: 'python', 'typescript', 'javascript'

        Returns:
            ParseResult with AST and metadata
        """
        language = language.lower()

        if language == "python":
            return self._parse_python(code)
        elif language in ["typescript", "tsx"]:
            return self._parse_typescript(code)
        elif language in ["javascript", "jsx"]:
            return self._parse_javascript(code)
        else:
            return ParseResult(
                language=language,
                ast=None,
                ast_nodes=[],
                functions=[],
                classes=[],
                imports=[],
                loc=0,
                complexity=0.0,
                errors=[f"Unsupported language: {language}"],
                success=False
            )

    def _parse_python(self, code: str) -> ParseResult:
        """Parse Python code"""
        try:
            # Parse with tree-sitter
            tree = self.py_parser.parse(bytes(code, "utf8"))
            root = tree.root_node

            # Check for syntax errors
            if root.has_error:
                return ParseResult(
                    language="python",
                    ast=root,
                    ast_nodes=[],
                    functions=[],
                    classes=[],
                    imports=[],
                    loc=len(code.split('\n')),
                    complexity=0.0,
                    errors=["Syntax error in Python code"],
                    success=False
                )

            # Extract AST nodes
            ast_nodes = self._extract_nodes(root, code)

            # Extract functions
            functions = self._extract_python_functions(root, code)

            # Extract classes
            classes = self._extract_python_classes(root, code)

            # Extract imports
            imports = self._extract_python_imports(root, code)

            # Calculate LOC
            loc = len([line for line in code.split('\n') if line.strip()])

            # Calculate complexity
            complexity = self._calculate_complexity(root)

            return ParseResult(
                language="python",
                ast=root,
                ast_nodes=ast_nodes,
                functions=functions,
                classes=classes,
                imports=imports,
                loc=loc,
                complexity=complexity,
                errors=[],
                success=True
            )

        except Exception as e:
            logger.error(f"Error parsing Python code: {e}")
            return ParseResult(
                language="python",
                ast=None,
                ast_nodes=[],
                functions=[],
                classes=[],
                imports=[],
                loc=0,
                complexity=0.0,
                errors=[str(e)],
                success=False
            )

    def _parse_typescript(self, code: str) -> ParseResult:
        """Parse TypeScript code"""
        try:
            tree = self.ts_parser.parse(bytes(code, "utf8"))
            root = tree.root_node

            if root.has_error:
                return ParseResult(
                    language="typescript",
                    ast=root,
                    ast_nodes=[],
                    functions=[],
                    classes=[],
                    imports=[],
                    loc=len(code.split('\n')),
                    complexity=0.0,
                    errors=["Syntax error in TypeScript code"],
                    success=False
                )

            ast_nodes = self._extract_nodes(root, code)
            functions = self._extract_ts_functions(root, code)
            classes = self._extract_ts_classes(root, code)
            imports = self._extract_ts_imports(root, code)
            loc = len([line for line in code.split('\n') if line.strip()])
            complexity = self._calculate_complexity(root)

            return ParseResult(
                language="typescript",
                ast=root,
                ast_nodes=ast_nodes,
                functions=functions,
                classes=classes,
                imports=imports,
                loc=loc,
                complexity=complexity,
                errors=[],
                success=True
            )

        except Exception as e:
            logger.error(f"Error parsing TypeScript code: {e}")
            return ParseResult(
                language="typescript",
                ast=None,
                ast_nodes=[],
                functions=[],
                classes=[],
                imports=[],
                loc=0,
                complexity=0.0,
                errors=[str(e)],
                success=False
            )

    def _parse_javascript(self, code: str) -> ParseResult:
        """Parse JavaScript code"""
        try:
            tree = self.js_parser.parse(bytes(code, "utf8"))
            root = tree.root_node

            if root.has_error:
                return ParseResult(
                    language="javascript",
                    ast=root,
                    ast_nodes=[],
                    functions=[],
                    classes=[],
                    imports=[],
                    loc=len(code.split('\n')),
                    complexity=0.0,
                    errors=["Syntax error in JavaScript code"],
                    success=False
                )

            ast_nodes = self._extract_nodes(root, code)
            functions = self._extract_js_functions(root, code)
            classes = self._extract_js_classes(root, code)
            imports = self._extract_js_imports(root, code)
            loc = len([line for line in code.split('\n') if line.strip()])
            complexity = self._calculate_complexity(root)

            return ParseResult(
                language="javascript",
                ast=root,
                ast_nodes=ast_nodes,
                functions=functions,
                classes=classes,
                imports=imports,
                loc=loc,
                complexity=complexity,
                errors=[],
                success=True
            )

        except Exception as e:
            logger.error(f"Error parsing JavaScript code: {e}")
            return ParseResult(
                language="javascript",
                ast=None,
                ast_nodes=[],
                functions=[],
                classes=[],
                imports=[],
                loc=0,
                complexity=0.0,
                errors=[str(e)],
                success=False
            )

    def _extract_nodes(self, root: tree_sitter.Node, code: str) -> List[ASTNode]:
        """Extract all AST nodes recursively"""
        nodes = []

        def traverse(node: tree_sitter.Node) -> Optional[ASTNode]:
            ast_node = ASTNode(
                type=node.type,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                text=code[node.start_byte:node.end_byte],
                children=[]
            )

            for child in node.children:
                child_node = traverse(child)
                if child_node:
                    ast_node.children.append(child_node)

            nodes.append(ast_node)
            return ast_node

        traverse(root)
        return nodes

    def _extract_python_functions(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract function definitions from Python AST"""
        functions = []

        def find_functions(node: tree_sitter.Node) -> None:
            if node.type == "function_definition":
                # Get function name
                name_node = node.child_by_field_name("name")
                name = code[name_node.start_byte:name_node.end_byte] if name_node else "unknown"

                # Get parameters
                params_node = node.child_by_field_name("parameters")
                params = code[params_node.start_byte:params_node.end_byte] if params_node else "()"

                functions.append({
                    "name": name,
                    "params": params,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "loc": node.end_point[0] - node.start_point[0] + 1
                })

            for child in node.children:
                find_functions(child)

        find_functions(root)
        return functions

    def _extract_python_classes(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract class definitions from Python AST"""
        classes = []

        def find_classes(node: tree_sitter.Node) -> None:
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                name = code[name_node.start_byte:name_node.end_byte] if name_node else "unknown"

                classes.append({
                    "name": name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "loc": node.end_point[0] - node.start_point[0] + 1
                })

            for child in node.children:
                find_classes(child)

        find_classes(root)
        return classes

    def _extract_python_imports(self, root: tree_sitter.Node, code: str) -> List[str]:
        """Extract import statements from Python AST"""
        imports = []

        def find_imports(node: tree_sitter.Node) -> None:
            if node.type in ["import_statement", "import_from_statement"]:
                import_text = code[node.start_byte:node.end_byte]
                imports.append(import_text)

            for child in node.children:
                find_imports(child)

        find_imports(root)
        return imports

    def _extract_ts_functions(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract function definitions from TypeScript AST"""
        functions = []

        def find_functions(node: tree_sitter.Node) -> None:
            if node.type in ["function_declaration", "arrow_function", "function_expression"]:
                name = "anonymous"
                if node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        name = code[name_node.start_byte:name_node.end_byte]

                functions.append({
                    "name": name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "loc": node.end_point[0] - node.start_point[0] + 1
                })

            for child in node.children:
                find_functions(child)

        find_functions(root)
        return functions

    def _extract_ts_classes(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract class definitions from TypeScript AST"""
        classes = []

        def find_classes(node: tree_sitter.Node) -> None:
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = code[name_node.start_byte:name_node.end_byte] if name_node else "unknown"

                classes.append({
                    "name": name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "loc": node.end_point[0] - node.start_point[0] + 1
                })

            for child in node.children:
                find_classes(child)

        find_classes(root)
        return classes

    def _extract_ts_imports(self, root: tree_sitter.Node, code: str) -> List[str]:
        """Extract import statements from TypeScript AST"""
        imports = []

        def find_imports(node: tree_sitter.Node) -> None:
            if node.type == "import_statement":
                import_text = code[node.start_byte:node.end_byte]
                imports.append(import_text)

            for child in node.children:
                find_imports(child)

        find_imports(root)
        return imports

    def _extract_js_functions(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract function definitions from JavaScript AST"""
        return self._extract_ts_functions(root, code)  # Same structure

    def _extract_js_classes(self, root: tree_sitter.Node, code: str) -> List[Dict]:
        """Extract class definitions from JavaScript AST"""
        return self._extract_ts_classes(root, code)  # Same structure

    def _extract_js_imports(self, root: tree_sitter.Node, code: str) -> List[str]:
        """Extract import statements from JavaScript AST"""
        return self._extract_ts_imports(root, code)  # Same structure

    def _calculate_complexity(self, root: tree_sitter.Node) -> float:
        """
        Calculate cyclomatic complexity

        Complexity = 1 + number of decision points
        Decision points: if, elif, else, while, for, try, except, and, or
        """
        decision_nodes = [
            "if_statement",
            "elif_clause",
            "else_clause",
            "while_statement",
            "for_statement",
            "try_statement",
            "except_clause",
            "boolean_operator",  # and, or
            "conditional_expression",  # ternary
        ]

        count = 1  # Base complexity

        def count_decisions(node: tree_sitter.Node) -> None:
            nonlocal count
            if node.type in decision_nodes:
                count += 1

            for child in node.children:
                count_decisions(child)

        count_decisions(root)
        return float(count)

    def detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        else:
            return "unknown"
