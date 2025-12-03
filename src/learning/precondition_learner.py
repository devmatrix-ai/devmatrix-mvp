"""
PreconditionLearner - Learns preconditions from 404 errors for Auto-Seed.

This module closes the learning loop for 404 errors:
1. Detects 404 patterns (missing entities/relationships)
2. Persists learned preconditions in Neo4j
3. Feeds Auto-Seed with learned data

Created: 2025-12-03
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md Phase 2
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LearnedPrecondition:
    """A precondition learned from 404 errors."""
    entity_name: str
    field_name: str
    required_value: Optional[str] = None
    related_entity: Optional[str] = None  # For FK relationships
    endpoint_pattern: Optional[str] = None  # e.g., "/carts/{id}/checkout"
    flow_name: Optional[str] = None
    confidence: float = 0.5  # Increases with each validation
    occurrences: int = 1
    last_seen: datetime = field(default_factory=datetime.now)


class PreconditionLearner:
    """
    Learns preconditions from 404 errors and feeds Auto-Seed.
    
    Phase 2 Learning Integration:
    - Persists to Neo4j for reuse between runs
    - Uses merge defensivo: IR manda, learned rellena
    - Applies only in context of endpoint/flow
    """
    
    def __init__(self):
        self._learned: Dict[str, LearnedPrecondition] = {}  # key -> precondition
        self._neo4j_enabled = False
        self._initialize_neo4j()
    
    def _initialize_neo4j(self) -> None:
        """Try to connect to Neo4j for persistence."""
        try:
            from src.knowledge_graph.neo4j_manager import Neo4jManager
            self._neo4j = Neo4jManager()
            self._neo4j_enabled = True
            self._load_from_neo4j()
            logger.info("📚 PreconditionLearner: Neo4j persistence enabled")
        except Exception as e:
            self._neo4j = None
            logger.warning(f"📚 PreconditionLearner: Neo4j unavailable, using memory: {e}")
    
    def _load_from_neo4j(self) -> None:
        """Load previously learned preconditions from Neo4j."""
        if not self._neo4j_enabled:
            return
        
        try:
            # Query learned preconditions
            query = """
            MATCH (p:LearnedPrecondition)
            RETURN p.key as key, p.entity_name as entity, p.field_name as field,
                   p.required_value as value, p.related_entity as related,
                   p.confidence as confidence, p.occurrences as occurrences
            """
            result = self._neo4j.execute_query(query)
            for record in result:
                precond = LearnedPrecondition(
                    entity_name=record["entity"],
                    field_name=record["field"],
                    required_value=record.get("value"),
                    related_entity=record.get("related"),
                    confidence=record.get("confidence", 0.5),
                    occurrences=record.get("occurrences", 1),
                )
                self._learned[record["key"]] = precond
            
            logger.info(f"📚 Loaded {len(self._learned)} learned preconditions from Neo4j")
        except Exception as e:
            logger.warning(f"Could not load from Neo4j: {e}")
    
    def learn_from_404(
        self,
        endpoint: str,
        error_message: str,
        entity_name: Optional[str] = None,
        flow_name: Optional[str] = None
    ) -> Optional[LearnedPrecondition]:
        """
        Learn from a 404 error - extract missing entity/relationship.
        
        Args:
            endpoint: The endpoint that returned 404
            error_message: The error message
            entity_name: Optional entity name if known
            flow_name: Optional flow name for context
            
        Returns:
            LearnedPrecondition if something was learned
        """
        # Extract entity from endpoint if not provided
        if not entity_name:
            entity_name = self._extract_entity_from_endpoint(endpoint)
        
        if not entity_name:
            logger.debug(f"Could not extract entity from 404: {endpoint}")
            return None
        
        # Analyze error message for relationship hints
        related_entity = self._extract_related_entity(error_message)
        
        # Create precondition key
        key = f"{entity_name.lower()}:exists"
        if related_entity:
            key = f"{entity_name.lower()}:needs:{related_entity.lower()}"
        
        # Update or create precondition
        if key in self._learned:
            precond = self._learned[key]
            precond.occurrences += 1
            precond.confidence = min(0.95, precond.confidence + 0.1)
            precond.last_seen = datetime.now()
        else:
            precond = LearnedPrecondition(
                entity_name=entity_name,
                field_name="id",  # 404 = entity doesn't exist
                related_entity=related_entity,
                endpoint_pattern=self._normalize_endpoint(endpoint),
                flow_name=flow_name,
            )
            self._learned[key] = precond
        
        logger.info(f"📚 Learned precondition: {key} (confidence={precond.confidence:.2f})")
        
        # Persist to Neo4j
        self._persist_to_neo4j(key, precond)
        
        return precond
    
    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # Pattern: /entities/{id}... -> Entity
        match = re.search(r'/(\w+)/\{[^}]+\}', endpoint)
        if match:
            entity_plural = match.group(1)
            # Simple depluralize
            if entity_plural.endswith('ies'):
                return entity_plural[:-3] + 'y'
            elif entity_plural.endswith('s'):
                return entity_plural[:-1]
            return entity_plural
        return None

