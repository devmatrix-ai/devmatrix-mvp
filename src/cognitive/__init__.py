"""
Cognitive Architecture MVP - Core Package

This package implements the semantic-driven inference engine for DevMatrix,
replacing wave-based code generation with pre-atomization and pattern matching.

Core Components:
- signatures: Semantic Task Signatures (STS) for task essence capture
- patterns: Pattern Bank with Qdrant integration for similarity search
- inference: Cognitive Pattern Inference Engine (CPIE)
- planning: Multi-Pass Planning (6 refinement passes)
- validation: E2E Production Validator (4-layer validation)
- co_reasoning: Co-Reasoning System (Claude + DeepSeek)
- infrastructure: Neo4j and Qdrant client wrappers
- lrm: Large Reasoning Model integration (o1/DeepSeek-R1)

Target Precision:
- MVP (4 weeks): 88% E2E, 92% Atomic
- Final (6 weeks): 92% E2E, 95% Atomic
"""

__version__ = "0.1.0"
__author__ = "DevMatrix Team"

# Package-level imports will be added as components are implemented
