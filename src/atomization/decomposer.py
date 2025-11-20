"""
Recursive Decomposer - Task → Atomic Units

Decomposes tasks into atomic execution units (~10 LOC each).

Strategy:
- Top-down recursive splitting
- Target: 10 LOC per atom
- Atomicity criteria: complexity <3.0, single responsibility
- Boundary detection: function/class boundaries
- Split strategies: by function, by class, by logical blocks

Author: DevMatrix Team
Date: 2025-10-23
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging

from .parser import MultiLanguageParser, ParseResult, ASTNode

logger = logging.getLogger(__name__)


@dataclass
class AtomCandidate:
    """Candidate atomic unit from decomposition"""
    code: str
    start_line: int
    end_line: int
    loc: int
    complexity: float
    description: str
    boundary_type: str  # 'function', 'class', 'block', 'statement'
    parent_context: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class DecompositionResult:
    """Result of task decomposition"""
    atoms: List[AtomCandidate]
    total_atoms: int
    avg_loc: float
    avg_complexity: float
    strategy_used: str
    errors: List[str]
    success: bool


class RecursiveDecomposer:
    """
    Recursive task decomposer

    Decomposes tasks into atomic units using:
    1. AST parsing (MultiLanguageParser)
    2. Recursive splitting algorithm
    3. Boundary detection (functions, classes, blocks)
    4. Atomicity validation

    Target: ~10 LOC per atom, complexity <3.0
    """

    def __init__(self, target_loc: int = 10, max_loc: int = 15, max_complexity: float = 3.0, max_loc_for_classes: int = 100) -> None:
        """
        Initialize decomposer

        Args:
            target_loc: Target lines of code per atom (default: 10)
            max_loc: Maximum lines of code per atom (default: 15)
            max_complexity: Maximum cyclomatic complexity (default: 3.0)
            max_loc_for_classes: Maximum LOC for classes before splitting (default: 100)
        """
        self.target_loc = target_loc
        self.max_loc = max_loc
        self.max_complexity = max_complexity
        self.max_loc_for_classes = max_loc_for_classes
        self.parser = MultiLanguageParser()

        logger.info(f"RecursiveDecomposer initialized (target_loc={target_loc}, max_loc={max_loc}, max_complexity={max_complexity}, max_loc_for_classes={max_loc_for_classes})")

    def decompose(self, code: str, language: str, description: str = "") -> DecompositionResult:
        """
        Decompose code into atomic units

        Args:
            code: Source code to decompose
            language: Programming language
            description: Task description

        Returns:
            DecompositionResult with atomic unit candidates
        """
        logger.info(f"Starting decomposition: {len(code)} chars, language={language}")

        # Parse code
        parse_result = self.parser.parse(code, language)
        if not parse_result.success:
            return DecompositionResult(
                atoms=[],
                total_atoms=0,
                avg_loc=0.0,
                avg_complexity=0.0,
                strategy_used="failed",
                errors=parse_result.errors,
                success=False
            )

        # Choose decomposition strategy based on code structure
        strategy = self._choose_strategy(parse_result)
        logger.info(f"Using strategy: {strategy}")

        # Apply strategy
        if strategy == "by_function":
            atoms = self._decompose_by_functions(code, parse_result, description)
        elif strategy == "by_class":
            atoms = self._decompose_by_classes(code, parse_result, description)
        elif strategy == "by_block":
            atoms = self._decompose_by_blocks(code, parse_result, description)
        else:  # single_atom
            atoms = self._create_single_atom(code, parse_result, description)

        # Calculate statistics
        total_atoms = len(atoms)
        avg_loc = sum(a.loc for a in atoms) / total_atoms if total_atoms > 0 else 0
        avg_complexity = sum(a.complexity for a in atoms) / total_atoms if total_atoms > 0 else 0

        logger.info(f"Decomposition complete: {total_atoms} atoms, avg_loc={avg_loc:.1f}, avg_complexity={avg_complexity:.1f}")

        return DecompositionResult(
            atoms=atoms,
            total_atoms=total_atoms,
            avg_loc=avg_loc,
            avg_complexity=avg_complexity,
            strategy_used=strategy,
            errors=[],
            success=True
        )

    def _choose_strategy(self, parse_result: ParseResult) -> str:
        """
        Choose decomposition strategy based on code structure

        Strategies:
        - by_function: Multiple functions detected
        - by_class: Multiple classes detected
        - by_block: Single large function/class
        - single_atom: Already atomic (<15 LOC)
        """
        loc = parse_result.loc

        # Already atomic
        if loc <= self.max_loc:
            return "single_atom"

        # Multiple functions
        if len(parse_result.functions) >= 2:
            return "by_function"

        # Multiple classes
        if len(parse_result.classes) >= 2:
            return "by_class"

        # Single large function/class - split into blocks
        if len(parse_result.functions) == 1 or len(parse_result.classes) == 1:
            return "by_block"

        # Default: block-based splitting
        return "by_block"

    def _decompose_by_functions(self, code: str, parse_result: ParseResult, description: str) -> List[AtomCandidate]:
        """Decompose code by splitting functions"""
        atoms = []
        lines = code.split('\n')

        for func in parse_result.functions:
            func_code = '\n'.join(lines[func['start_line']-1:func['end_line']])
            func_loc = func['end_line'] - func['start_line'] + 1

            # Function is already atomic
            if func_loc <= self.max_loc:
                atoms.append(AtomCandidate(
                    code=func_code,
                    start_line=func['start_line'],
                    end_line=func['end_line'],
                    loc=func_loc,
                    complexity=self._estimate_complexity(func_code, parse_result.language),
                    description=f"{description} - Function: {func['name']}",
                    boundary_type='function',
                    parent_context=description
                ))
            else:
                # Function too large - recursively decompose
                sub_atoms = self._split_large_function(func_code, func, description, parse_result.language)
                atoms.extend(sub_atoms)

        return atoms

    def _decompose_by_classes(self, code: str, parse_result: ParseResult, description: str) -> List[AtomCandidate]:
        """Decompose code by splitting classes"""
        atoms = []
        lines = code.split('\n')

        for cls in parse_result.classes:
            cls_code = '\n'.join(lines[cls['start_line']-1:cls['end_line']])
            cls_loc = cls['end_line'] - cls['start_line'] + 1

            # Class is already atomic
            if cls_loc <= self.max_loc_for_classes:
                atoms.append(AtomCandidate(
                    code=cls_code,
                    start_line=cls['start_line'],
                    end_line=cls['end_line'],
                    loc=cls_loc,
                    complexity=self._estimate_complexity(cls_code, parse_result.language),
                    description=f"{description} - Class: {cls['name']}",
                    boundary_type='class',
                    parent_context=description
                ))
            else:
                # Class too large - split by methods
                sub_atoms = self._split_large_class(cls_code, cls, description, parse_result.language)
                atoms.extend(sub_atoms)

        return atoms

    def _decompose_by_blocks(self, code: str, parse_result: ParseResult, description: str) -> List[AtomCandidate]:
        """Decompose code by logical blocks"""
        atoms: List[AtomCandidate] = []
        lines = code.split('\n')
        current_start = 0
        current_lines = []

        for i, line in enumerate(lines):
            current_lines.append(line)

            # Check if we've reached target LOC
            if len(current_lines) >= self.target_loc:
                # Find a good boundary (empty line, comment, function end)
                if self._is_good_boundary(line, lines, i):
                    block_code = '\n'.join(current_lines)
                    atoms.append(AtomCandidate(
                        code=block_code,
                        start_line=current_start + 1,
                        end_line=i + 1,
                        loc=len(current_lines),
                        complexity=self._estimate_complexity(block_code, parse_result.language),
                        description=f"{description} - Block {len(atoms) + 1}",
                        boundary_type='block',
                        parent_context=description
                    ))

                    current_start = i + 1
                    current_lines = []

        # Add remaining lines as final atom
        if current_lines:
            block_code = '\n'.join(current_lines)
            atoms.append(AtomCandidate(
                code=block_code,
                start_line=current_start + 1,
                end_line=len(lines),
                loc=len(current_lines),
                complexity=self._estimate_complexity(block_code, parse_result.language),
                description=f"{description} - Block {len(atoms) + 1}",
                boundary_type='block',
                parent_context=description
            ))

        return atoms

    def _create_single_atom(self, code: str, parse_result: ParseResult, description: str) -> List[AtomCandidate]:
        """Create single atom (code is already atomic)"""
        return [AtomCandidate(
            code=code,
            start_line=1,
            end_line=parse_result.loc,
            loc=parse_result.loc,
            complexity=parse_result.complexity,
            description=description,
            boundary_type='complete',
            parent_context=None
        )]

    def _split_large_function(self, func_code: str, func: Dict, description: str, language: str) -> List[AtomCandidate]:
        """Split a large function into smaller atoms"""
        atoms: List[AtomCandidate] = []
        lines = func_code.split('\n')

        # Simple strategy: split by ~10 LOC blocks at good boundaries
        current_start = 0
        current_lines = []

        for i, line in enumerate(lines):
            current_lines.append(line)

            if len(current_lines) >= self.target_loc and self._is_good_boundary(line, lines, i):
                block_code = '\n'.join(current_lines)
                atoms.append(AtomCandidate(
                    code=block_code,
                    start_line=func['start_line'] + current_start,
                    end_line=func['start_line'] + i,
                    loc=len(current_lines),
                    complexity=self._estimate_complexity(block_code, language),
                    description=f"{description} - {func['name']} (part {len(atoms) + 1})",
                    boundary_type='function_part',
                    parent_context=func['name']
                ))

                current_start = i + 1
                current_lines = []

        # Add remaining
        if current_lines:
            block_code = '\n'.join(current_lines)
            atoms.append(AtomCandidate(
                code=block_code,
                start_line=func['start_line'] + current_start,
                end_line=func['end_line'],
                loc=len(current_lines),
                complexity=self._estimate_complexity(block_code, language),
                description=f"{description} - {func['name']} (part {len(atoms) + 1})",
                boundary_type='function_part',
                parent_context=func['name']
            ))

        return atoms

    def _split_large_class(self, cls_code: str, cls: Dict, description: str, language: str) -> List[AtomCandidate]:
        """Split a large class into smaller atoms (by methods)"""
        # Parse class to find methods
        parse_result = self.parser.parse(cls_code, language)

        if parse_result.functions:
            # Split by methods
            return self._decompose_by_functions(cls_code, parse_result, f"{description} - {cls['name']}")
        else:
            # No methods, split by blocks
            return self._decompose_by_blocks(cls_code, parse_result, f"{description} - {cls['name']}")

    def _is_good_boundary(self, line: str, all_lines: List[str], index: int) -> bool:
        """Check if this is a good place to split atoms"""
        line = line.strip()

        # Empty line
        if not line:
            return True

        # Comment line
        if line.startswith('#') or line.startswith('//'):
            return True

        # End of function/class
        if line in [')', '}', 'pass', 'return']:
            return True

        # Last line
        if index == len(all_lines) - 1:
            return True

        # Next line is empty or comment
        if index + 1 < len(all_lines):
            next_line = all_lines[index + 1].strip()
            if not next_line or next_line.startswith('#') or next_line.startswith('//'):
                return True

        return False

    def _estimate_complexity(self, code: str, language: str) -> float:
        """Estimate complexity for a code block"""
        # Quick heuristic: count decision points
        decision_keywords = ['if', 'elif', 'else', 'while', 'for', 'try', 'except', 'and', 'or', '?']
        count = 1  # Base complexity

        for keyword in decision_keywords:
            count += code.count(keyword)

        return float(count)
