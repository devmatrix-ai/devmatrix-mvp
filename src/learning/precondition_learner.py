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
        # Pattern 1: /entities/{id}... -> Entity (template format)
        # Pattern 2: /entities/UUID... -> Entity (actual UUID)
        # Pattern 3: /entities/123... -> Entity (numeric ID)
        patterns = [
            r'/(\w+)/\{[^}]+\}',  # Template: /carts/{id}
            r'/(\w+)/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',  # UUID
            r'/(\w+)/\d+',  # Numeric ID
        ]

        for pattern in patterns:
            match = re.search(pattern, endpoint, re.IGNORECASE)
            if match:
                entity_plural = match.group(1)
                # Simple depluralize
                if entity_plural.endswith('ies'):
                    return entity_plural[:-3].capitalize() + 'y'
                elif entity_plural.endswith('s') and len(entity_plural) > 1:
                    return entity_plural[:-1].capitalize()
                return entity_plural.capitalize()
        return None

    def _extract_related_entity(self, error_message: str) -> Optional[str]:
        """Extract related entity from error message."""
        # Pattern: "Cart not found" -> Cart needs to exist
        # Pattern: "Product with id X not found" -> Product
        patterns = [
            r'(\w+)\s+not\s+found',
            r'(\w+)\s+with\s+id',
            r'foreign\s+key.*?(\w+)',
            r'references\s+(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint to pattern (replace IDs with {id})."""
        # Replace UUIDs and numeric IDs with {id}
        normalized = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            endpoint
        )
        normalized = re.sub(r'/\d+', '/{id}', normalized)
        return normalized

    def _persist_to_neo4j(self, key: str, precond: LearnedPrecondition) -> None:
        """Persist precondition to Neo4j."""
        if not self._neo4j_enabled:
            return

        try:
            query = """
            MERGE (p:LearnedPrecondition {key: $key})
            SET p.entity_name = $entity,
                p.field_name = $field,
                p.required_value = $value,
                p.related_entity = $related,
                p.endpoint_pattern = $endpoint,
                p.flow_name = $flow,
                p.confidence = $confidence,
                p.occurrences = $occurrences,
                p.last_seen = datetime()
            """
            self._neo4j.execute_query(query, {
                "key": key,
                "entity": precond.entity_name,
                "field": precond.field_name,
                "value": precond.required_value,
                "related": precond.related_entity,
                "endpoint": precond.endpoint_pattern,
                "flow": precond.flow_name,
                "confidence": precond.confidence,
                "occurrences": precond.occurrences,
            })
        except Exception as e:
            logger.warning(f"Could not persist to Neo4j: {e}")

    def get_preconditions_for_entity(self, entity_name: str) -> List[LearnedPrecondition]:
        """Get all learned preconditions for an entity."""
        entity_lower = entity_name.lower()
        return [
            p for p in self._learned.values()
            if p.entity_name.lower() == entity_lower
        ]

    def get_all_learned(self) -> Dict[str, LearnedPrecondition]:
        """Get all learned preconditions."""
        return dict(self._learned)

    def get_seed_hints(self, ir_hints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge learned preconditions with IR hints (DEFENSIVO).

        IR manda, learned rellena:
        - IR hints take priority
        - Learned hints fill gaps only

        Args:
            ir_hints: Hints extracted from ApplicationIR

        Returns:
            Merged hints dict
        """
        merged = dict(ir_hints)  # IR manda

        # Add learned hints where IR doesn't specify
        for key, precond in self._learned.items():
            # Only add if confidence is high enough
            if precond.confidence < 0.6:
                continue

            hint_key = f"{precond.entity_name.lower()}.{precond.field_name}"

            if hint_key not in merged:
                if precond.required_value:
                    merged[hint_key] = precond.required_value
                    logger.debug(f"📚 Added learned hint: {hint_key}={precond.required_value}")

        return merged

    def get_relationship_hints(self) -> List[tuple]:
        """
        Get learned entity relationships for seed ordering.

        Returns list of (child_entity, parent_entity) tuples.
        """
        relationships = []
        for precond in self._learned.values():
            if precond.related_entity and precond.confidence >= 0.6:
                relationships.append((precond.entity_name, precond.related_entity))
        return relationships

    def clear(self) -> None:
        """Clear learned preconditions (for testing)."""
        self._learned.clear()


# Singleton instance
_learner_instance: Optional[PreconditionLearner] = None


def get_precondition_learner() -> PreconditionLearner:
    """Get singleton PreconditionLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = PreconditionLearner()
    return _learner_instance

