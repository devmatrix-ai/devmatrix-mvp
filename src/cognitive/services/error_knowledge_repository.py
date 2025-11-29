"""
Error Knowledge Repository

Repository for storing and querying learned error knowledge from code generation failures.
Implements Active Learning for error avoidance in subsequent generations.

Design reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_REDESIGN.md Section 7
"""
import hashlib
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ErrorKnowledge:
    """Represents learned knowledge about an error pattern."""

    knowledge_id: str
    error_type: str  # "500", "422", "ImportError", "AttributeError", etc.
    pattern_category: str  # "service", "route", "repository", "entity", "schema"
    entity_type: Optional[str]  # "product", "customer", etc.
    endpoint_pattern: Optional[str]  # "POST /{entity}", "PUT /{entity}/{id}"
    error_signature: str  # Hash for dedup
    description: str  # Human readable error description
    avoidance_hint: str  # "Always call db.commit() after create"
    code_example_bad: Optional[str] = None  # Code that caused the error
    code_example_good: Optional[str] = None  # Corrected code (from fix)
    occurrence_count: int = 1
    confidence: float = 0.5  # 0.0-1.0 based on occurrences
    last_seen: Optional[datetime] = None

    @classmethod
    def from_neo4j(cls, record: Dict[str, Any]) -> "ErrorKnowledge":
        """Create ErrorKnowledge from Neo4j record."""
        return cls(
            knowledge_id=record.get("knowledge_id", ""),
            error_type=record.get("error_type", ""),
            pattern_category=record.get("pattern_category", ""),
            entity_type=record.get("entity_type"),
            endpoint_pattern=record.get("endpoint_pattern"),
            error_signature=record.get("error_signature", ""),
            description=record.get("description", ""),
            avoidance_hint=record.get("avoidance_hint", ""),
            code_example_bad=record.get("code_example_bad"),
            code_example_good=record.get("code_example_good"),
            occurrence_count=record.get("occurrence_count", 1),
            confidence=record.get("confidence", 0.5),
            last_seen=record.get("last_seen"),
        )


class ErrorKnowledgeRepository:
    """
    Repository for learned error knowledge.

    Implements the Active Learning loop:
    1. Learn from failures (smoke test errors)
    2. Learn from fixes (successful repairs)
    3. Query relevant errors before generation
    4. Apply avoidance context to code generation
    """

    def __init__(self, neo4j_driver):
        """
        Initialize repository with Neo4j driver.

        Args:
            neo4j_driver: Neo4j driver instance (from neo4j Python driver)
        """
        self.driver = neo4j_driver

    def learn_from_failure(
        self,
        pattern_id: Optional[str],
        error_type: str,
        error_message: str,
        endpoint_path: str,
        entity_name: Optional[str],
        failed_code: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Learn from a smoke test failure.

        Creates or updates ErrorKnowledge node and links to Pattern if provided.
        Confidence increases with each occurrence.

        Args:
            pattern_id: Optional ID of pattern that generated the failing code
            error_type: Type of error (HTTP status, exception type)
            error_message: Full error message
            endpoint_path: API endpoint path (e.g., "/products", "/carts/123/items")
            entity_name: Entity name if applicable
            failed_code: Code snippet that caused the error
            file_path: Path to the file that caused the error

        Returns:
            Error signature for future reference
        """
        signature = self._compute_signature(error_type, endpoint_path, entity_name)
        avoidance_hint = self._generate_avoidance_hint(error_type, error_message)
        endpoint_pattern = self._extract_endpoint_pattern(endpoint_path)
        pattern_category = self._infer_category(file_path or endpoint_path)

        with self.driver.session() as session:
            result = session.run("""
                MERGE (ek:ErrorKnowledge {error_signature: $signature})
                ON CREATE SET
                    ek.knowledge_id = $knowledge_id,
                    ek.error_type = $error_type,
                    ek.pattern_category = $pattern_category,
                    ek.entity_type = $entity_name,
                    ek.endpoint_pattern = $endpoint_pattern,
                    ek.description = $error_message,
                    ek.avoidance_hint = $avoidance_hint,
                    ek.code_example_bad = $failed_code,
                    ek.occurrence_count = 1,
                    ek.last_seen = datetime(),
                    ek.confidence = 0.5,
                    ek.created_at = datetime()
                ON MATCH SET
                    ek.occurrence_count = ek.occurrence_count + 1,
                    ek.last_seen = datetime(),
                    ek.confidence = CASE
                        WHEN ek.occurrence_count >= 5 THEN 0.95
                        WHEN ek.occurrence_count >= 3 THEN 0.8
                        ELSE 0.5 + (ek.occurrence_count * 0.1)
                    END,
                    ek.description = CASE
                        WHEN size($error_message) > size(ek.description)
                        THEN $error_message
                        ELSE ek.description
                    END
                RETURN ek.knowledge_id as knowledge_id
            """,
                signature=signature,
                knowledge_id=str(uuid4()),
                error_type=error_type,
                pattern_category=pattern_category,
                entity_name=entity_name,
                endpoint_pattern=endpoint_pattern,
                error_message=error_message[:2000] if error_message else "",
                avoidance_hint=avoidance_hint,
                failed_code=failed_code[:5000] if failed_code else None,
            )

            record = result.single()
            knowledge_id = record["knowledge_id"] if record else None

            # Link to pattern if provided
            if pattern_id:
                session.run("""
                    MATCH (ek:ErrorKnowledge {error_signature: $signature})
                    MATCH (p:Pattern {pattern_id: $pattern_id})
                    MERGE (p)-[r:CAUSED_ERROR]->(ek)
                    ON CREATE SET r.timestamp = datetime(), r.count = 1
                    ON MATCH SET r.timestamp = datetime(), r.count = r.count + 1
                """,
                    signature=signature,
                    pattern_id=pattern_id,
                )

        logger.info(f"Learned from failure: {error_type} at {endpoint_pattern} (sig={signature[:8]}...)")
        return signature

    def learn_from_fix(
        self,
        error_signature: str,
        fix_code: str,
        fix_description: Optional[str] = None,
    ) -> bool:
        """
        Learn from a successful fix.

        Updates ErrorKnowledge with the correct code example.

        Args:
            error_signature: Signature of the error that was fixed
            fix_code: The corrected code
            fix_description: Optional improved avoidance hint

        Returns:
            True if update was successful
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ek:ErrorKnowledge {error_signature: $signature})
                SET ek.code_example_good = $fix_code,
                    ek.avoidance_hint = COALESCE($fix_description, ek.avoidance_hint),
                    ek.fixed_at = datetime()
                RETURN ek.knowledge_id as knowledge_id
            """,
                signature=error_signature,
                fix_code=fix_code[:5000] if fix_code else None,
                fix_description=fix_description,
            )

            record = result.single()
            success = record is not None

        if success:
            logger.info(f"Learned fix for error: {error_signature[:8]}...")
        else:
            logger.warning(f"Could not find error to update: {error_signature[:8]}...")

        return success

    def get_relevant_errors(
        self,
        endpoint_pattern: Optional[str] = None,
        entity_type: Optional[str] = None,
        pattern_category: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[ErrorKnowledge]:
        """
        Get errors relevant to what we're about to generate.

        Queries ErrorKnowledge nodes that match the generation context.
        Results are ordered by confidence and occurrence count.

        Args:
            endpoint_pattern: Pattern like "POST /{entity}" or "GET /{entity}/{id}"
            entity_type: Entity name (lowercase)
            pattern_category: Category like "service", "route", "repository"
            min_confidence: Minimum confidence threshold (default 0.5)
            limit: Maximum number of errors to return

        Returns:
            List of relevant ErrorKnowledge objects
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ek:ErrorKnowledge)
                WHERE ek.confidence >= $min_confidence
                  AND (
                    $endpoint_pattern IS NULL
                    OR ek.endpoint_pattern = $endpoint_pattern
                    OR ek.endpoint_pattern IS NULL
                  )
                  AND (
                    $entity_type IS NULL
                    OR ek.entity_type = $entity_type
                    OR ek.entity_type IS NULL
                  )
                  AND (
                    $pattern_category IS NULL
                    OR ek.pattern_category = $pattern_category
                  )
                RETURN ek {.*} as error
                ORDER BY ek.confidence DESC, ek.occurrence_count DESC
                LIMIT $limit
            """,
                endpoint_pattern=endpoint_pattern,
                entity_type=entity_type.lower() if entity_type else None,
                pattern_category=pattern_category,
                min_confidence=min_confidence,
                limit=limit,
            )

            errors = []
            for record in result:
                try:
                    errors.append(ErrorKnowledge.from_neo4j(record["error"]))
                except Exception as e:
                    logger.warning(f"Failed to parse ErrorKnowledge: {e}")

            return errors

    def get_errors_for_entity(
        self,
        entity_name: str,
        min_confidence: float = 0.5,
    ) -> List[ErrorKnowledge]:
        """
        Get all errors related to a specific entity.

        Args:
            entity_name: Entity name (case-insensitive)
            min_confidence: Minimum confidence threshold

        Returns:
            List of ErrorKnowledge objects for this entity
        """
        return self.get_relevant_errors(
            entity_type=entity_name.lower(),
            min_confidence=min_confidence,
        )

    def get_errors_for_endpoint_type(
        self,
        method: str,
        path_pattern: str,
        min_confidence: float = 0.5,
    ) -> List[ErrorKnowledge]:
        """
        Get errors for a specific endpoint type.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path_pattern: Path pattern like "/{entity}" or "/{entity}/{id}"
            min_confidence: Minimum confidence threshold

        Returns:
            List of ErrorKnowledge objects for this endpoint type
        """
        endpoint_pattern = f"{method.upper()} {path_pattern}"
        return self.get_relevant_errors(
            endpoint_pattern=endpoint_pattern,
            min_confidence=min_confidence,
        )

    def get_high_confidence_errors(
        self,
        min_confidence: float = 0.8,
        limit: int = 20,
    ) -> List[ErrorKnowledge]:
        """
        Get high-confidence errors (well-established patterns).

        Args:
            min_confidence: Minimum confidence (default 0.8)
            limit: Maximum results

        Returns:
            List of high-confidence ErrorKnowledge objects
        """
        return self.get_relevant_errors(
            min_confidence=min_confidence,
            limit=limit,
        )

    def get_error_by_signature(self, signature: str) -> Optional[ErrorKnowledge]:
        """Get a specific error by its signature."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ek:ErrorKnowledge {error_signature: $signature})
                RETURN ek {.*} as error
            """, signature=signature)

            record = result.single()
            if record:
                return ErrorKnowledge.from_neo4j(record["error"])
            return None

    def build_avoidance_context(
        self,
        errors: List[ErrorKnowledge],
        max_errors: int = 5,
    ) -> str:
        """
        Build context string for error avoidance.

        Creates a formatted string that can be injected into generation prompts
        or added as comments in generated code.

        Args:
            errors: List of relevant errors
            max_errors: Maximum number of errors to include

        Returns:
            Formatted avoidance context string
        """
        if not errors:
            return ""

        lines = [
            "",
            "# =============================================================",
            "# ERROR AVOIDANCE (learned from previous failures):",
            "# =============================================================",
        ]

        for error in errors[:max_errors]:
            lines.append(f"# ⚠️ {error.error_type}: {error.avoidance_hint}")
            if error.code_example_good:
                # Include first line of correct code as example
                good_code = error.code_example_good.strip().split('\n')[0]
                lines.append(f"#    ✅ Example: {good_code[:80]}...")

        lines.append("# =============================================================")
        lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about learned errors."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ek:ErrorKnowledge)
                RETURN
                    count(ek) as total_errors,
                    avg(ek.confidence) as avg_confidence,
                    sum(ek.occurrence_count) as total_occurrences,
                    count(CASE WHEN ek.code_example_good IS NOT NULL THEN 1 END) as fixed_errors,
                    collect(DISTINCT ek.error_type)[0..10] as top_error_types,
                    collect(DISTINCT ek.pattern_category)[0..10] as categories
            """)

            record = result.single()
            if record:
                return {
                    "total_errors": record["total_errors"],
                    "avg_confidence": round(record["avg_confidence"] or 0, 2),
                    "total_occurrences": record["total_occurrences"],
                    "fixed_errors": record["fixed_errors"],
                    "fix_rate": round(
                        (record["fixed_errors"] / record["total_errors"] * 100)
                        if record["total_errors"] > 0 else 0, 1
                    ),
                    "top_error_types": record["top_error_types"],
                    "categories": record["categories"],
                }
            return {}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _compute_signature(
        self,
        error_type: str,
        endpoint_path: str,
        entity_name: Optional[str] = None,
    ) -> str:
        """
        Compute unique signature for error deduplication.

        Combines error type, endpoint pattern, and entity to create
        a unique identifier for this class of error.
        """
        endpoint_pattern = self._extract_endpoint_pattern(endpoint_path)
        components = [
            error_type,
            endpoint_pattern,
            entity_name.lower() if entity_name else "",
        ]
        signature_input = "|".join(components)
        return hashlib.sha256(signature_input.encode()).hexdigest()[:16]

    def _generate_avoidance_hint(
        self,
        error_type: str,
        error_message: str,
    ) -> str:
        """Generate human-readable avoidance hint from error."""
        hints = {
            "500": "Ensure proper error handling and database commits",
            "422": "Validate request body matches schema exactly",
            "404": "Verify endpoint path and route registration",
            "405": "Check HTTP method matches route definition",
            "400": "Validate request parameters and body format",
            "IntegrityError": "Check foreign key constraints and unique values",
            "AttributeError": "Verify object attributes exist before access",
            "TypeError": "Check type compatibility in operations",
            "ImportError": "Verify imported module/class exists",
            "KeyError": "Check dictionary key exists before access",
            "ValidationError": "Ensure data matches Pydantic schema",
            "missing db.commit": "Always call db.commit() after create/update",
            "missing db.refresh": "Call db.refresh() after commit to get updated values",
            "model_dump": "Use model.model_dump() not model.dict() for Pydantic v2",
        }

        # Check for specific patterns in error message
        error_lower = (error_type + " " + error_message).lower()

        for key, hint in hints.items():
            if key.lower() in error_lower:
                return hint

        # Default hint from error message
        return f"Avoid: {error_message[:100]}"

    def _extract_endpoint_pattern(self, endpoint_path: str) -> str:
        """
        Extract generic pattern from endpoint path.

        Examples:
            /products/123 → GET /products/{id}
            /carts/456/items → /carts/{id}/items
            /customers → /customers
        """
        if not endpoint_path:
            return ""

        # Remove method prefix if present
        path = endpoint_path
        method = ""
        if " " in endpoint_path:
            parts = endpoint_path.split(" ", 1)
            if parts[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                method = parts[0].upper() + " "
                path = parts[1]

        # Replace UUIDs with {id}
        pattern = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        # Replace numeric IDs with {id}
        pattern = re.sub(r'/\d+', '/{id}', pattern)

        return method + pattern

    def _infer_category(self, path_or_file: str) -> str:
        """Infer pattern category from file path or endpoint."""
        path_lower = path_or_file.lower()

        if "service" in path_lower:
            return "service"
        elif "route" in path_lower or "router" in path_lower or "endpoint" in path_lower:
            return "route"
        elif "repository" in path_lower or "repo" in path_lower:
            return "repository"
        elif "entity" in path_lower or "model" in path_lower:
            return "entity"
        elif "schema" in path_lower:
            return "schema"
        elif "test" in path_lower:
            return "test"
        elif "factory" in path_lower:
            return "factory"
        else:
            return "unknown"


# =========================================================================
# Convenience Functions
# =========================================================================

def create_error_knowledge_repository(neo4j_driver) -> ErrorKnowledgeRepository:
    """Factory function to create ErrorKnowledgeRepository."""
    return ErrorKnowledgeRepository(neo4j_driver)
