"""
ServiceGuardStore - Stores and retrieves successful SERVICE guards for reuse.

Phase 3 Learning Integration: Enables fix reuse without LLM regeneration.
Guards are stored with signatures for matching and confidence for ranking.

Created: 2025-12-03
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md Phase 3
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StoredGuard:
    """A successful guard stored for reuse."""
    signature: str  # constraint_type:entity:method
    constraint_type: str
    entity_name: str
    method_name: str
    guard_code: str
    confidence: float = 0.5  # Increases with successful reuse
    success_count: int = 1
    failure_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of this guard."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


class ServiceGuardStore:
    """
    Stores and retrieves successful SERVICE guards for reuse.
    
    Phase 3 Learning Integration:
    - Stores guards with normalized signatures
    - Retrieves guards by signature matching
    - Tracks success/failure for confidence scoring
    - Supports Neo4j persistence (optional)
    """
    
    MIN_CONFIDENCE_FOR_REUSE = 0.6  # Minimum confidence to auto-apply
    
    def __init__(self):
        self._guards: Dict[str, StoredGuard] = {}  # signature -> guard
        self._neo4j_enabled = False
        self._initialize_neo4j()
    
    def _initialize_neo4j(self) -> None:
        """Try to connect to Neo4j for persistence."""
        try:
            from src.knowledge_graph.neo4j_manager import Neo4jManager
            self._neo4j = Neo4jManager()
            self._neo4j_enabled = True
            self._load_from_neo4j()
            logger.info("🛡️ ServiceGuardStore: Neo4j persistence enabled")
        except Exception as e:
            self._neo4j = None
            logger.debug(f"🛡️ ServiceGuardStore: Neo4j unavailable, using memory: {e}")
    
    def _load_from_neo4j(self) -> None:
        """Load stored guards from Neo4j."""
        if not self._neo4j_enabled:
            return
        
        try:
            query = """
            MATCH (g:ServiceGuard)
            RETURN g.signature as signature, g.constraint_type as constraint,
                   g.entity_name as entity, g.method_name as method,
                   g.guard_code as code, g.confidence as confidence,
                   g.success_count as success, g.failure_count as failure
            """
            result = self._neo4j.execute_query(query)
            for record in result:
                guard = StoredGuard(
                    signature=record["signature"],
                    constraint_type=record["constraint"],
                    entity_name=record["entity"],
                    method_name=record["method"],
                    guard_code=record["code"],
                    confidence=record.get("confidence", 0.5),
                    success_count=record.get("success", 1),
                    failure_count=record.get("failure", 0),
                )
                self._guards[guard.signature] = guard
            
            logger.info(f"🛡️ Loaded {len(self._guards)} guards from Neo4j")
        except Exception as e:
            logger.warning(f"Could not load guards from Neo4j: {e}")
    
    def store_guard(
        self,
        signature: str,
        constraint_type: str,
        entity_name: str,
        method_name: str,
        guard_code: str,
        validated: bool = False
    ) -> StoredGuard:
        """
        Store a successful guard for future reuse.
        
        Args:
            signature: Normalized signature (constraint:entity:method)
            constraint_type: Type of constraint
            entity_name: Entity name
            method_name: Method name
            guard_code: The guard code
            validated: Whether guard was validated by smoke test
            
        Returns:
            The stored guard
        """
        if signature in self._guards:
            # Update existing
            guard = self._guards[signature]
            guard.success_count += 1
            guard.confidence = min(0.95, guard.confidence + 0.1)
            guard.last_used = datetime.now()
            if validated:
                guard.confidence = min(0.98, guard.confidence + 0.1)
        else:
            # Create new
            guard = StoredGuard(
                signature=signature,
                constraint_type=constraint_type,
                entity_name=entity_name,
                method_name=method_name,
                guard_code=guard_code,
                confidence=0.7 if validated else 0.5,
            )
            self._guards[signature] = guard
        
        logger.info(f"🛡️ Stored guard: {signature} (confidence={guard.confidence:.2f})")

        # Persist to Neo4j
        self._persist_to_neo4j(guard)

        return guard

    def get_guard(
        self,
        signature: str,
        min_confidence: float = None
    ) -> Optional[StoredGuard]:
        """
        Get a stored guard by signature.

        Args:
            signature: The guard signature to look up
            min_confidence: Minimum confidence threshold

        Returns:
            StoredGuard if found and meets confidence threshold
        """
        min_conf = min_confidence or self.MIN_CONFIDENCE_FOR_REUSE
        guard = self._guards.get(signature)

        if guard and guard.confidence >= min_conf:
            return guard
        return None

    def get_guard_for_constraint(
        self,
        constraint_type: str,
        entity_name: str,
        method_name: str,
        min_confidence: float = None
    ) -> Optional[StoredGuard]:
        """
        Get a guard by constraint/entity/method.

        This is the main lookup method for fix reuse.

        Args:
            constraint_type: Type of constraint
            entity_name: Entity name
            method_name: Method name
            min_confidence: Minimum confidence threshold

        Returns:
            StoredGuard if found
        """
        signature = f"{constraint_type}:{entity_name.lower()}:{method_name.lower()}"
        return self.get_guard(signature, min_confidence)

    def record_success(self, signature: str) -> None:
        """Record successful reuse of a guard."""
        if signature in self._guards:
            guard = self._guards[signature]
            guard.success_count += 1
            guard.confidence = min(0.98, guard.confidence + 0.05)
            guard.last_used = datetime.now()
            self._persist_to_neo4j(guard)
            logger.debug(f"📈 Guard success: {signature} → {guard.confidence:.2f}")

    def record_failure(self, signature: str) -> None:
        """Record failed reuse of a guard."""
        if signature in self._guards:
            guard = self._guards[signature]
            guard.failure_count += 1
            guard.confidence = max(0.1, guard.confidence - 0.15)
            self._persist_to_neo4j(guard)
            logger.debug(f"📉 Guard failure: {signature} → {guard.confidence:.2f}")

    def get_all_guards(self, min_confidence: float = 0.0) -> List[StoredGuard]:
        """Get all guards above confidence threshold."""
        return [
            g for g in self._guards.values()
            if g.confidence >= min_confidence
        ]

    def _persist_to_neo4j(self, guard: StoredGuard) -> None:
        """Persist guard to Neo4j."""
        if not self._neo4j_enabled:
            return

        try:
            query = """
            MERGE (g:ServiceGuard {signature: $signature})
            SET g.constraint_type = $constraint,
                g.entity_name = $entity,
                g.method_name = $method,
                g.guard_code = $code,
                g.confidence = $confidence,
                g.success_count = $success,
                g.failure_count = $failure,
                g.last_used = datetime()
            """
            self._neo4j.execute_query(query, {
                "signature": guard.signature,
                "constraint": guard.constraint_type,
                "entity": guard.entity_name,
                "method": guard.method_name,
                "code": guard.guard_code,
                "confidence": guard.confidence,
                "success": guard.success_count,
                "failure": guard.failure_count,
            })
        except Exception as e:
            logger.warning(f"Could not persist guard to Neo4j: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        guards = list(self._guards.values())
        return {
            "total_guards": len(guards),
            "high_confidence": sum(1 for g in guards if g.confidence >= 0.8),
            "avg_confidence": sum(g.confidence for g in guards) / len(guards) if guards else 0,
            "total_reuses": sum(g.success_count for g in guards),
            "by_constraint": self._group_by_constraint(guards),
        }

    def _group_by_constraint(self, guards: List[StoredGuard]) -> Dict[str, int]:
        """Group guards by constraint type."""
        result = {}
        for g in guards:
            result[g.constraint_type] = result.get(g.constraint_type, 0) + 1
        return result

    def clear(self) -> None:
        """Clear all guards (for testing)."""
        self._guards.clear()


# Singleton instance
_store_instance: Optional[ServiceGuardStore] = None


def get_service_guard_store() -> ServiceGuardStore:
    """Get singleton ServiceGuardStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ServiceGuardStore()
    return _store_instance

