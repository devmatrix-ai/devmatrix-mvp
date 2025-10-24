"""
MGE V2 Atomization Package

Components for decomposing tasks into atomic execution units:
- MultiLanguageParser: AST parsing with tree-sitter
- RecursiveDecomposer: Task → 800 atoms decomposition
- ContextInjector: Complete context extraction
- AtomicityValidator: 10-criteria validation
"""

from .parser import MultiLanguageParser
from .decomposer import RecursiveDecomposer
from .context_injector import ContextInjector
from .validator import AtomicityValidator

__all__ = [
    "MultiLanguageParser",
    "RecursiveDecomposer",
    "ContextInjector",
    "AtomicityValidator",
]
