"""
Discovery Service - Generate Discovery Documents from User Requests

Extracts structured DDD (Domain-Driven Design) discovery information from
natural language user requests using LLM.

Generates:
- Domain identification
- Bounded contexts
- Aggregates and entities
- Value objects
- Domain events
- Services

Author: DevMatrix Team
Date: 2025-11-10
"""

import uuid
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.masterplan import DiscoveryDocument
from src.llm import EnhancedAnthropicClient
from src.observability import StructuredLogger


logger = StructuredLogger("discovery_service", output_json=True)


# Discovery System Prompt
DISCOVERY_SYSTEM_PROMPT = """You are an expert software architect and domain-driven design (DDD) specialist.

Your task is to analyze user requests and extract structured domain information for software development.

You must identify:
1. **Domain**: The main problem domain (e.g., "E-commerce", "Healthcare", "Finance")
2. **Bounded Contexts**: Logical boundaries within the domain (3-7 contexts typical)
3. **Aggregates**: Core business entities and their relationships
4. **Value Objects**: Immutable objects defined by their attributes
5. **Domain Events**: Important business events that occur
6. **Services**: Business logic that doesn't fit in entities

Return ONLY valid JSON with this exact structure:
{
  "domain": "string",
  "bounded_contexts": [
    {
      "name": "string",
      "description": "string",
      "responsibilities": ["string"]
    }
  ],
  "aggregates": [
    {
      "name": "string",
      "context": "string",
      "root_entity": "string",
      "entities": ["string"],
      "description": "string"
    }
  ],
  "value_objects": [
    {
      "name": "string",
      "context": "string",
      "attributes": ["string"],
      "description": "string"
    }
  ],
  "domain_events": [
    {
      "name": "string",
      "context": "string",
      "triggers": "string",
      "data": ["string"]
    }
  ],
  "services": [
    {
      "name": "string",
      "context": "string",
      "type": "domain|application|infrastructure",
      "responsibilities": ["string"]
    }
  ],
  "assumptions": ["string"],
  "clarifications_needed": ["string"],
  "risk_factors": ["string"]
}

Be practical and pragmatic:
- Focus on MVP scope (not enterprise-scale)
- 3-5 bounded contexts maximum
- 5-10 aggregates typical
- Keep it implementable
- Identify real risks and unknowns"""


class DiscoveryService:
    """
    Service for generating Discovery Documents from natural language requests.

    Usage:
        service = DiscoveryService(db=db_session)
        discovery_id = await service.generate_discovery(
            user_request="Create a REST API for task management",
            session_id="session_123",
            user_id="user_456"
        )
    """

    def __init__(
        self,
        db: Session,
        llm_client: Optional[EnhancedAnthropicClient] = None
    ):
        """
        Initialize Discovery Service.

        Args:
            db: SQLAlchemy database session
            llm_client: Enhanced Anthropic client (creates new if not provided)
        """
        self.db = db
        self.llm_client = llm_client or EnhancedAnthropicClient()

    async def generate_discovery(
        self,
        user_request: str,
        session_id: str,
        user_id: str
    ) -> uuid.UUID:
        """
        Generate Discovery Document from user request.

        Args:
            user_request: Natural language description of what to build
            session_id: Session identifier
            user_id: User identifier

        Returns:
            discovery_id: UUID of created DiscoveryDocument

        Raises:
            ValueError: If request is invalid or generation fails
            RuntimeError: If LLM generation fails
        """
        if not user_request or len(user_request.strip()) < 10:
            raise ValueError("User request must be at least 10 characters")

        logger.info(
            "Starting discovery generation",
            extra={
                "session_id": session_id,
                "user_id": user_id,
                "request_length": len(user_request)
            }
        )

        try:
            # Generate discovery document with LLM
            discovery_data = await self._generate_with_llm(user_request)

            # Validate discovery data
            self._validate_discovery_data(discovery_data)

            # Create DiscoveryDocument
            discovery_doc = DiscoveryDocument(
                discovery_id=uuid.uuid4(),
                session_id=session_id,
                user_id=user_id,
                user_request=user_request,
                domain=discovery_data["domain"],
                bounded_contexts=discovery_data["bounded_contexts"],
                aggregates=discovery_data["aggregates"],
                value_objects=discovery_data["value_objects"],
                domain_events=discovery_data["domain_events"],
                services=discovery_data["services"],
                assumptions=discovery_data.get("assumptions", []),
                clarifications_needed=discovery_data.get("clarifications_needed", []),
                risk_factors=discovery_data.get("risk_factors", []),
                llm_model=discovery_data.get("model", "claude-sonnet-4-5"),
                llm_cost_usd=discovery_data.get("cost_usd", 0.0),
                created_at=datetime.utcnow()
            )

            # Save to database
            self.db.add(discovery_doc)
            self.db.commit()
            self.db.refresh(discovery_doc)

            logger.info(
                "Discovery document created successfully",
                extra={
                    "discovery_id": str(discovery_doc.discovery_id),
                    "domain": discovery_data["domain"],
                    "bounded_contexts_count": len(discovery_data["bounded_contexts"]),
                    "aggregates_count": len(discovery_data["aggregates"])
                }
            )

            return discovery_doc.discovery_id

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Discovery generation failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise RuntimeError(f"Discovery generation failed: {str(e)}")

    async def _generate_with_llm(self, user_request: str) -> Dict[str, Any]:
        """
        Generate discovery document using LLM.

        Args:
            user_request: User's natural language request

        Returns:
            Dictionary with discovery data

        Raises:
            RuntimeError: If LLM generation fails
        """
        user_prompt = f"""Analyze this software project request and extract DDD domain information:

**User Request:**
{user_request}

Extract domain information following DDD principles. Focus on MVP scope.
Return ONLY the JSON structure specified in the system prompt."""

        try:
            # Generate with LLM
            response = await self.llm_client.generate_with_caching(
                task_type="discovery_analysis",
                complexity="medium",
                cacheable_context={
                    "system_prompt": DISCOVERY_SYSTEM_PROMPT
                },
                variable_prompt=user_prompt,
                temperature=0.7,
                max_tokens=4096
            )

            # Extract content
            content = response.get("content", "")

            # Parse JSON
            discovery_data = self._extract_json_from_response(content)

            # Add metadata
            discovery_data["model"] = response.get("model", "claude-sonnet-4-5")
            discovery_data["cost_usd"] = self._calculate_cost(response)

            return discovery_data

        except Exception as e:
            logger.error(
                "LLM generation failed",
                extra={"error": str(e)},
                exc_info=True
            )
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response (handles markdown code blocks).

        Args:
            content: LLM response content

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON parsing fails
        """
        # Remove markdown code blocks if present
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from LLM response",
                extra={
                    "error": str(e),
                    "content_preview": content[:200]
                }
            )
            raise ValueError(f"Failed to parse JSON: {str(e)}")

    def _validate_discovery_data(self, data: Dict[str, Any]) -> None:
        """
        Validate discovery data structure.

        Args:
            data: Discovery data dictionary

        Raises:
            ValueError: If data is invalid
        """
        required_fields = [
            "domain",
            "bounded_contexts",
            "aggregates",
            "value_objects",
            "domain_events",
            "services"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate domain is a string
        if not isinstance(data["domain"], str) or not data["domain"].strip():
            raise ValueError("Domain must be a non-empty string")

        # Validate lists
        for field in ["bounded_contexts", "aggregates", "value_objects", "domain_events", "services"]:
            if not isinstance(data[field], list):
                raise ValueError(f"{field} must be a list")

        # Validate at least one bounded context
        if len(data["bounded_contexts"]) == 0:
            raise ValueError("Must have at least one bounded context")

        # Validate at least one aggregate
        if len(data["aggregates"]) == 0:
            raise ValueError("Must have at least one aggregate")

    def _calculate_cost(self, response: Dict[str, Any]) -> float:
        """
        Calculate LLM API cost from response.

        Args:
            response: LLM response with usage data

        Returns:
            Cost in USD
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Sonnet 4.5 pricing (as of 2025)
        # Input: $3 per 1M tokens
        # Output: $15 per 1M tokens
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0

        return round(input_cost + output_cost, 4)

    def get_discovery(self, discovery_id: uuid.UUID) -> Optional[DiscoveryDocument]:
        """
        Get discovery document by ID.

        Args:
            discovery_id: UUID of discovery document

        Returns:
            DiscoveryDocument or None if not found
        """
        return self.db.query(DiscoveryDocument).filter(
            DiscoveryDocument.discovery_id == discovery_id
        ).first()

    def list_discoveries(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> list[DiscoveryDocument]:
        """
        List discovery documents with optional filtering.

        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            limit: Maximum number of results

        Returns:
            List of DiscoveryDocuments
        """
        query = self.db.query(DiscoveryDocument)

        if user_id:
            query = query.filter(DiscoveryDocument.user_id == user_id)

        if session_id:
            query = query.filter(DiscoveryDocument.session_id == session_id)

        return query.order_by(
            DiscoveryDocument.created_at.desc()
        ).limit(limit).all()
