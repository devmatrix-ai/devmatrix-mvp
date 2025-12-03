"""
Knowledge Graph Module - Neo4j integration for Learning System.

Provides centralized Neo4j connection management for:
- PreconditionLearner (learned preconditions from 404s)
- ServiceGuardStore (successful SERVICE repairs)
- EffectivenessTracker (repair metrics)

Created: 2025-12-03 (Bug #205)
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md
"""

from .neo4j_manager import Neo4jManager, get_neo4j_manager

__all__ = ["Neo4jManager", "get_neo4j_manager"]

