"""
MGE V2 Acceptance Testing Module

Autogenerate and execute acceptance tests from masterplan requirements.

Components:
- AcceptanceTestGenerator: Generate contract, invariant, and case tests
- AcceptanceTestExecutor: Execute tests with MUST/SHOULD gates
"""

from .test_generator import (
    AcceptanceTestGenerator,
    AcceptanceTest,
    TestType,
    TestGenerationResult
)
from .test_executor import (
    AcceptanceTestExecutor,
    TestStatus,
    TestResult,
    ExecutionReport
)

__all__ = [
    "AcceptanceTestGenerator",
    "AcceptanceTest",
    "TestType",
    "TestGenerationResult",
    "AcceptanceTestExecutor",
    "TestStatus",
    "TestResult",
    "ExecutionReport",
]
