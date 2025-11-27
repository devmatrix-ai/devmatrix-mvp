"""
Skeleton Generator Service - Phase 6: Skeleton + Holes Architecture

Generates structural code with designated LLM_SLOT markers where the LLM
can fill in business logic. This constrains the LLM to only modify specific
sections, preventing it from breaking imports, signatures, or architecture.

LLM_SLOT Marker Syntax:
    [LLM_SLOT:start:slot_name]
    ... LLM fills content here ...
    [LLM_SLOT:end:slot_name]

Benefits:
    - LLM cannot break imports or change signatures
    - LLM cannot add unauthorized dependencies
    - Clear separation of structural vs business logic
    - Deterministic skeleton generation (no LLM variability)
    - Easier validation and testing
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SlotType(str, Enum):
    """Types of LLM slots for different code sections."""

    BUSINESS_LOGIC = "business_logic"
    VALIDATION = "validation"
    QUERY = "query"
    TRANSFORMATION = "transformation"
    ERROR_HANDLING = "error_handling"
    DOCSTRING = "docstring"
    COMMENT = "comment"


class SlotConstraint(str, Enum):
    """Constraints on what LLM can do within a slot."""

    NO_IMPORTS = "no_imports"
    NO_CLASS_DEF = "no_class_def"
    NO_FUNCTION_DEF = "no_function_def"
    SINGLE_EXPRESSION = "single_expression"
    RETURN_REQUIRED = "return_required"
    NO_SIDE_EFFECTS = "no_side_effects"
    MAX_LINES = "max_lines"


@dataclass
class LLMSlot:
    """Definition of an LLM-fillable slot within skeleton code."""

    name: str
    slot_type: SlotType
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: List[SlotConstraint] = field(default_factory=list)
    max_lines: int = 50
    required: bool = True
    default_content: str = "pass  # LLM: implement this"

    # Validation patterns
    forbidden_patterns: List[str] = field(default_factory=list)
    required_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set default forbidden patterns based on constraints."""
        if SlotConstraint.NO_IMPORTS in self.constraints:
            self.forbidden_patterns.extend([
                r"^import\s+",
                r"^from\s+\w+\s+import",
            ])
        if SlotConstraint.NO_CLASS_DEF in self.constraints:
            self.forbidden_patterns.append(r"^\s*class\s+\w+")
        if SlotConstraint.NO_FUNCTION_DEF in self.constraints:
            self.forbidden_patterns.append(r"^\s*(?:async\s+)?def\s+\w+")


@dataclass
class SlotValidationResult:
    """Result of validating LLM-filled content for a slot."""

    slot_name: str
    is_valid: bool
    content: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class SkeletonTemplate:
    """A skeleton code template with LLM slots."""

    name: str
    template_type: str  # entity, service, router, schema
    content: str
    slots: List[LLMSlot] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def get_slot(self, name: str) -> Optional[LLMSlot]:
        """Get a slot by name."""
        for slot in self.slots:
            if slot.name == name:
                return slot
        return None

    def list_slot_names(self) -> List[str]:
        """List all slot names in this template."""
        return [slot.name for slot in self.slots]


class SkeletonGenerator:
    """
    Generates skeleton code with LLM_SLOT markers.

    The skeleton contains all structural elements (imports, class definitions,
    method signatures) while leaving designated slots for LLM to fill with
    business logic.
    """

    # Marker patterns
    SLOT_START_PATTERN = r"\[LLM_SLOT:start:(\w+)\]"
    SLOT_END_PATTERN = r"\[LLM_SLOT:end:(\w+)\]"
    SLOT_START_TEMPLATE = "[LLM_SLOT:start:{name}]"
    SLOT_END_TEMPLATE = "[LLM_SLOT:end:{name}]"

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the skeleton generator.

        Args:
            strict_mode: If True, validation is stricter and errors are raised.
        """
        self.strict_mode = strict_mode
        self._templates: Dict[str, SkeletonTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """Register default skeleton templates."""
        # Entity template
        self._templates["entity"] = self._create_entity_template()
        self._templates["service"] = self._create_service_template()
        self._templates["router"] = self._create_router_template()
        self._templates["schema"] = self._create_schema_template()
        self._templates["repository"] = self._create_repository_template()

    def _create_entity_template(self) -> SkeletonTemplate:
        """Create the SQLAlchemy entity skeleton template."""
        content = '''"""
{entity_name} Entity - Auto-generated skeleton
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.models.base import Base


class {entity_name}(Base):
    """
    {entity_name} database entity.

    [LLM_SLOT:start:entity_docstring]
    # LLM: Add detailed docstring describing the entity
    [LLM_SLOT:end:entity_docstring]
    """

    __tablename__ = "{table_name}"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc)
    )

    [LLM_SLOT:start:entity_columns]
    # LLM: Add entity-specific columns here
    # Example: name: Mapped[str] = mapped_column(String(255), nullable=False)
    pass
    [LLM_SLOT:end:entity_columns]

    # Relationships
    [LLM_SLOT:start:entity_relationships]
    # LLM: Add relationships here
    # Example: items: Mapped[List["OrderItem"]] = relationship(back_populates="order")
    pass
    [LLM_SLOT:end:entity_relationships]

    def __repr__(self) -> str:
        return f"<{entity_name}(id={{self.id}})>"

    [LLM_SLOT:start:entity_methods]
    # LLM: Add entity-specific methods here
    pass
    [LLM_SLOT:end:entity_methods]
'''

        slots = [
            LLMSlot(
                name="entity_docstring",
                slot_type=SlotType.DOCSTRING,
                description="Detailed entity docstring",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="entity_columns",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Entity-specific column definitions",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=30,
                context={"allowed": "SQLAlchemy column definitions"},
            ),
            LLMSlot(
                name="entity_relationships",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Entity relationships",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
                required=False,
            ),
            LLMSlot(
                name="entity_methods",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Entity-specific methods",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=50,
                required=False,
            ),
        ]

        return SkeletonTemplate(
            name="entity",
            template_type="entity",
            content=content,
            slots=slots,
            imports=[
                "datetime",
                "typing",
                "uuid",
                "sqlalchemy",
                "src.models.base",
            ],
        )

    def _create_service_template(self) -> SkeletonTemplate:
        """Create the service layer skeleton template."""
        content = '''"""
{service_name} Service - Auto-generated skeleton
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from src.models.entities import {entity_name}
from src.models.schemas import {schema_prefix}Create, {schema_prefix}Update, {schema_prefix}Response


class {service_name}Service:
    """
    Service layer for {entity_name} operations.

    Handles business logic and data access for {entity_name} entities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: {schema_prefix}Create) -> {entity_name}:
        """
        Create a new {entity_name}.

        Args:
            data: Creation data from request

        Returns:
            Created {entity_name} entity
        """
        [LLM_SLOT:start:service_create_validation]
        # LLM: Add pre-creation validation logic
        pass
        [LLM_SLOT:end:service_create_validation]

        entity = {entity_name}(
            [LLM_SLOT:start:service_create_mapping]
            # LLM: Map data fields to entity
            # Example: name=data.name,
            [LLM_SLOT:end:service_create_mapping]
        )

        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)

        return entity

    async def get_by_id(self, entity_id: str) -> Optional[{entity_name}]:
        """
        Get {entity_name} by ID.

        Args:
            entity_id: UUID of the entity

        Returns:
            {entity_name} if found, None otherwise
        """
        query = select({entity_name}).where({entity_name}.id == entity_id)

        [LLM_SLOT:start:service_get_eager_loading]
        # LLM: Add eager loading options if needed
        # Example: query = query.options(selectinload({entity_name}.items))
        [LLM_SLOT:end:service_get_eager_loading]

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        [LLM_SLOT:start:service_list_params]
        # LLM: Add additional filter parameters
        [LLM_SLOT:end:service_list_params]
    ) -> List[{entity_name}]:
        """
        Get all {entity_name} entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of {entity_name} entities
        """
        query = select({entity_name})

        [LLM_SLOT:start:service_list_filters]
        # LLM: Add filter conditions
        # Example: if status: query = query.where({entity_name}.status == status)
        [LLM_SLOT:end:service_list_filters]

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        entity_id: str,
        data: {schema_prefix}Update
    ) -> Optional[{entity_name}]:
        """
        Update an existing {entity_name}.

        Args:
            entity_id: UUID of the entity to update
            data: Update data from request

        Returns:
            Updated {entity_name} if found, None otherwise
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        [LLM_SLOT:start:service_update_logic]
        # LLM: Add update logic
        # Example: if data.name is not None: entity.name = data.name
        [LLM_SLOT:end:service_update_logic]

        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_id: str) -> bool:
        """
        Delete a {entity_name}.

        Args:
            entity_id: UUID of the entity to delete

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False

        [LLM_SLOT:start:service_delete_validation]
        # LLM: Add pre-deletion validation (e.g., check dependencies)
        [LLM_SLOT:end:service_delete_validation]

        await self.session.delete(entity)
        await self.session.commit()
        return True

    [LLM_SLOT:start:service_custom_methods]
    # LLM: Add custom service methods
    # Example: async def get_by_email(self, email: str) -> Optional[{entity_name}]:
    [LLM_SLOT:end:service_custom_methods]
'''

        slots = [
            LLMSlot(
                name="service_create_validation",
                slot_type=SlotType.VALIDATION,
                description="Pre-creation validation logic",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
                required=False,
            ),
            LLMSlot(
                name="service_create_mapping",
                slot_type=SlotType.TRANSFORMATION,
                description="Map request data to entity fields",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_FUNCTION_DEF],
                max_lines=20,
            ),
            LLMSlot(
                name="service_get_eager_loading",
                slot_type=SlotType.QUERY,
                description="Eager loading options for relationships",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="service_list_params",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Additional filter parameters",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="service_list_filters",
                slot_type=SlotType.QUERY,
                description="Filter conditions for list query",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
                required=False,
            ),
            LLMSlot(
                name="service_update_logic",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Update field mapping logic",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=30,
            ),
            LLMSlot(
                name="service_delete_validation",
                slot_type=SlotType.VALIDATION,
                description="Pre-deletion validation",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=15,
                required=False,
            ),
            LLMSlot(
                name="service_custom_methods",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Custom service methods",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=100,
                required=False,
            ),
        ]

        return SkeletonTemplate(
            name="service",
            template_type="service",
            content=content,
            slots=slots,
            imports=[
                "typing",
                "uuid",
                "sqlalchemy",
                "src.models.entities",
                "src.models.schemas",
            ],
        )

    def _create_router_template(self) -> SkeletonTemplate:
        """Create the FastAPI router skeleton template."""
        content = '''"""
{router_name} Router - Auto-generated skeleton
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models.schemas import {schema_prefix}Create, {schema_prefix}Update, {schema_prefix}Response
from src.services.{service_module} import {service_name}Service


router = APIRouter(
    prefix="/{route_prefix}",
    tags=["{tag_name}"],
)


def get_service(session: AsyncSession = Depends(get_session)) -> {service_name}Service:
    """Dependency to get service instance."""
    return {service_name}Service(session)


@router.post(
    "/",
    response_model={schema_prefix}Response,
    status_code=status.HTTP_201_CREATED,
    summary="Create {entity_name}",
)
async def create_{entity_name_lower}(
    data: {schema_prefix}Create,
    service: {service_name}Service = Depends(get_service),
) -> {schema_prefix}Response:
    """
    Create a new {entity_name}.

    [LLM_SLOT:start:router_create_docstring]
    # LLM: Add detailed endpoint documentation
    [LLM_SLOT:end:router_create_docstring]
    """
    [LLM_SLOT:start:router_create_validation]
    # LLM: Add request validation logic
    [LLM_SLOT:end:router_create_validation]

    entity = await service.create(data)
    return {schema_prefix}Response.model_validate(entity)


@router.get(
    "/{{entity_id}}",
    response_model={schema_prefix}Response,
    summary="Get {entity_name}",
)
async def get_{entity_name_lower}(
    entity_id: str,
    service: {service_name}Service = Depends(get_service),
) -> {schema_prefix}Response:
    """Get {entity_name} by ID."""
    entity = await service.get_by_id(entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )
    return {schema_prefix}Response.model_validate(entity)


@router.get(
    "/",
    response_model=List[{schema_prefix}Response],
    summary="List {entity_name}s",
)
async def list_{entity_name_lower}s(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    [LLM_SLOT:start:router_list_params]
    # LLM: Add filter query parameters
    # Example: status: Optional[str] = Query(None),
    [LLM_SLOT:end:router_list_params]
    service: {service_name}Service = Depends(get_service),
) -> List[{schema_prefix}Response]:
    """List all {entity_name}s with pagination."""
    entities = await service.get_all(
        skip=skip,
        limit=limit,
        [LLM_SLOT:start:router_list_args]
        # LLM: Pass filter arguments to service
        [LLM_SLOT:end:router_list_args]
    )
    return [
        {schema_prefix}Response.model_validate(entity)
        for entity in entities
    ]


@router.put(
    "/{{entity_id}}",
    response_model={schema_prefix}Response,
    summary="Update {entity_name}",
)
async def update_{entity_name_lower}(
    entity_id: str,
    data: {schema_prefix}Update,
    service: {service_name}Service = Depends(get_service),
) -> {schema_prefix}Response:
    """Update an existing {entity_name}."""
    [LLM_SLOT:start:router_update_validation]
    # LLM: Add update validation logic
    [LLM_SLOT:end:router_update_validation]

    entity = await service.update(entity_id, data)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )
    return {schema_prefix}Response.model_validate(entity)


@router.delete(
    "/{{entity_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete {entity_name}",
)
async def delete_{entity_name_lower}(
    entity_id: str,
    service: {service_name}Service = Depends(get_service),
) -> None:
    """Delete a {entity_name}."""
    [LLM_SLOT:start:router_delete_validation]
    # LLM: Add delete validation logic
    [LLM_SLOT:end:router_delete_validation]

    deleted = await service.delete(entity_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )


[LLM_SLOT:start:router_custom_endpoints]
# LLM: Add custom endpoints
# Example: @router.post("/{entity_id}/activate", ...)
[LLM_SLOT:end:router_custom_endpoints]
'''

        slots = [
            LLMSlot(
                name="router_create_docstring",
                slot_type=SlotType.DOCSTRING,
                description="Detailed create endpoint documentation",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="router_create_validation",
                slot_type=SlotType.VALIDATION,
                description="Request validation for create",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=15,
                required=False,
            ),
            LLMSlot(
                name="router_list_params",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Filter query parameters",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_FUNCTION_DEF],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="router_list_args",
                slot_type=SlotType.TRANSFORMATION,
                description="Arguments to pass to service",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="router_update_validation",
                slot_type=SlotType.VALIDATION,
                description="Request validation for update",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=15,
                required=False,
            ),
            LLMSlot(
                name="router_delete_validation",
                slot_type=SlotType.VALIDATION,
                description="Validation before delete",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=15,
                required=False,
            ),
            LLMSlot(
                name="router_custom_endpoints",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Custom endpoint definitions",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=150,
                required=False,
            ),
        ]

        return SkeletonTemplate(
            name="router",
            template_type="router",
            content=content,
            slots=slots,
            imports=[
                "typing",
                "uuid",
                "fastapi",
                "sqlalchemy",
                "src.database",
                "src.models.schemas",
            ],
        )

    def _create_schema_template(self) -> SkeletonTemplate:
        """Create the Pydantic schema skeleton template."""
        content = '''"""
{schema_name} Schemas - Auto-generated skeleton
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class {schema_prefix}Base(BaseModel):
    """Base schema for {entity_name}."""

    [LLM_SLOT:start:schema_base_fields]
    # LLM: Add base fields shared across Create/Update/Response
    # Example: name: str = Field(..., min_length=1, max_length=255)
    pass
    [LLM_SLOT:end:schema_base_fields]


class {schema_prefix}Create({schema_prefix}Base):
    """Schema for creating a new {entity_name}."""

    [LLM_SLOT:start:schema_create_fields]
    # LLM: Add create-specific fields
    pass
    [LLM_SLOT:end:schema_create_fields]

    [LLM_SLOT:start:schema_create_validators]
    # LLM: Add create-specific validators
    # Example: @field_validator("email")
    #          @classmethod
    #          def validate_email(cls, v): ...
    [LLM_SLOT:end:schema_create_validators]


class {schema_prefix}Update(BaseModel):
    """Schema for updating an existing {entity_name}."""

    [LLM_SLOT:start:schema_update_fields]
    # LLM: Add update fields (all Optional)
    # Example: name: Optional[str] = Field(None, min_length=1, max_length=255)
    pass
    [LLM_SLOT:end:schema_update_fields]

    [LLM_SLOT:start:schema_update_validators]
    # LLM: Add update-specific validators
    [LLM_SLOT:end:schema_update_validators]


class {schema_prefix}Response({schema_prefix}Base):
    """Schema for {entity_name} responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    [LLM_SLOT:start:schema_response_fields]
    # LLM: Add response-specific fields
    pass
    [LLM_SLOT:end:schema_response_fields]


[LLM_SLOT:start:schema_custom_classes]
# LLM: Add custom schema classes (e.g., nested schemas, list responses)
[LLM_SLOT:end:schema_custom_classes]
'''

        slots = [
            LLMSlot(
                name="schema_base_fields",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Base fields shared across schemas",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=30,
            ),
            LLMSlot(
                name="schema_create_fields",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Create-specific fields",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
                required=False,
            ),
            LLMSlot(
                name="schema_create_validators",
                slot_type=SlotType.VALIDATION,
                description="Create schema validators",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=30,
                required=False,
            ),
            LLMSlot(
                name="schema_update_fields",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Update fields (all Optional)",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
            ),
            LLMSlot(
                name="schema_update_validators",
                slot_type=SlotType.VALIDATION,
                description="Update schema validators",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=30,
                required=False,
            ),
            LLMSlot(
                name="schema_response_fields",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Response-specific fields",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=20,
                required=False,
            ),
            LLMSlot(
                name="schema_custom_classes",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Custom schema classes",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=100,
                required=False,
            ),
        ]

        return SkeletonTemplate(
            name="schema",
            template_type="schema",
            content=content,
            slots=slots,
            imports=[
                "datetime",
                "typing",
                "uuid",
                "pydantic",
            ],
        )

    def _create_repository_template(self) -> SkeletonTemplate:
        """Create the repository pattern skeleton template."""
        content = '''"""
{repository_name} Repository - Auto-generated skeleton
"""
from typing import List, Optional, Dict, Any, TypeVar, Generic
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from src.models.entities import {entity_name}


T = TypeVar("T")


class {repository_name}Repository:
    """
    Repository for {entity_name} data access.

    Provides a clean abstraction over database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model = {entity_name}

    async def create(self, **kwargs) -> {entity_name}:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get_by_id(
        self,
        entity_id: str,
        [LLM_SLOT:start:repo_get_options]
        # LLM: Add additional get options
        # Example: with_relations: bool = False
        [LLM_SLOT:end:repo_get_options]
    ) -> Optional[{entity_name}]:
        """Get entity by ID."""
        query = select(self.model).where(self.model.id == entity_id)

        [LLM_SLOT:start:repo_get_eager_load]
        # LLM: Add conditional eager loading
        # Example: if with_relations:
        #              query = query.options(selectinload(self.model.items))
        [LLM_SLOT:end:repo_get_eager_load]

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        [LLM_SLOT:start:repo_list_filters]
        # LLM: Add filter parameters
        # Example: filters: Optional[Dict[str, Any]] = None
        [LLM_SLOT:end:repo_list_filters]
    ) -> List[{entity_name}]:
        """Get all entities with pagination."""
        query = select(self.model)

        [LLM_SLOT:start:repo_list_where]
        # LLM: Apply filter conditions
        # Example: if filters:
        #              for key, value in filters.items():
        #                  query = query.where(getattr(self.model, key) == value)
        [LLM_SLOT:end:repo_list_where]

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, entity_id: str, **kwargs) -> Optional[{entity_name}]:
        """Update an entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)

        await self.session.flush()
        return entity

    async def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False

        await self.session.delete(entity)
        await self.session.flush()
        return True

    async def count(
        self,
        [LLM_SLOT:start:repo_count_filters]
        # LLM: Add count filter parameters
        [LLM_SLOT:end:repo_count_filters]
    ) -> int:
        """Count entities."""
        query = select(func.count()).select_from(self.model)

        [LLM_SLOT:start:repo_count_where]
        # LLM: Apply count filter conditions
        [LLM_SLOT:end:repo_count_where]

        result = await self.session.execute(query)
        return result.scalar_one()

    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        query = select(func.count()).select_from(self.model).where(
            self.model.id == entity_id
        )
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    [LLM_SLOT:start:repo_custom_methods]
    # LLM: Add custom repository methods
    # Example: async def find_by_email(self, email: str) -> Optional[{entity_name}]:
    [LLM_SLOT:end:repo_custom_methods]
'''

        slots = [
            LLMSlot(
                name="repo_get_options",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Additional get options",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=5,
                required=False,
            ),
            LLMSlot(
                name="repo_get_eager_load",
                slot_type=SlotType.QUERY,
                description="Conditional eager loading",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="repo_list_filters",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="List filter parameters",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=5,
                required=False,
            ),
            LLMSlot(
                name="repo_list_where",
                slot_type=SlotType.QUERY,
                description="List filter conditions",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=15,
                required=False,
            ),
            LLMSlot(
                name="repo_count_filters",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Count filter parameters",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=5,
                required=False,
            ),
            LLMSlot(
                name="repo_count_where",
                slot_type=SlotType.QUERY,
                description="Count filter conditions",
                constraints=[SlotConstraint.NO_IMPORTS],
                max_lines=10,
                required=False,
            ),
            LLMSlot(
                name="repo_custom_methods",
                slot_type=SlotType.BUSINESS_LOGIC,
                description="Custom repository methods",
                constraints=[SlotConstraint.NO_IMPORTS, SlotConstraint.NO_CLASS_DEF],
                max_lines=100,
                required=False,
            ),
        ]

        return SkeletonTemplate(
            name="repository",
            template_type="repository",
            content=content,
            slots=slots,
            imports=[
                "typing",
                "uuid",
                "sqlalchemy",
                "src.models.entities",
            ],
        )

    def generate_skeleton(
        self,
        template_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate skeleton code from a template.

        Args:
            template_type: Type of template (entity, service, router, schema)
            context: Variables to substitute in the template

        Returns:
            Generated skeleton code with LLM_SLOT markers
        """
        if template_type not in self._templates:
            raise ValueError(f"Unknown template type: {template_type}")

        template = self._templates[template_type]
        content = template.content

        # Substitute context variables
        for key, value in context.items():
            placeholder = "{" + key + "}"
            content = content.replace(placeholder, str(value))

        return content

    def get_template(self, template_type: str) -> Optional[SkeletonTemplate]:
        """Get a template by type."""
        return self._templates.get(template_type)

    def register_template(self, template: SkeletonTemplate):
        """Register a custom template."""
        self._templates[template.template_type] = template

    def extract_slots(self, code: str) -> Dict[str, str]:
        """
        Extract slot contents from code with LLM_SLOT markers.

        Args:
            code: Code with LLM_SLOT markers

        Returns:
            Dictionary mapping slot names to their content
        """
        slots = {}

        # Find all slot pairs
        pattern = rf"{self.SLOT_START_PATTERN}(.*?){self.SLOT_END_PATTERN}"
        matches = re.finditer(pattern, code, re.DOTALL)

        for match in matches:
            start_name = match.group(1)
            content = match.group(2)
            end_name = match.group(3)

            if start_name != end_name:
                logger.warning(
                    f"Mismatched slot markers: start={start_name}, end={end_name}"
                )
                continue

            # Clean up content (remove leading/trailing whitespace per line)
            lines = content.split("\n")
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("# LLM:"):
                    cleaned_lines.append(line)

            slots[start_name] = "\n".join(cleaned_lines).strip()

        return slots

    def list_slots(self, code: str) -> List[str]:
        """List all slot names in the code."""
        starts = re.findall(self.SLOT_START_PATTERN, code)
        return list(set(starts))


class LLMSlotFiller:
    """
    Fills LLM_SLOT markers with LLM-generated content.

    Validates that LLM content adheres to slot constraints.
    """

    def __init__(
        self,
        generator: SkeletonGenerator,
        strict_mode: bool = True,
    ):
        self.generator = generator
        self.strict_mode = strict_mode

    def fill_slots(
        self,
        skeleton: str,
        slot_contents: Dict[str, str],
        template_type: Optional[str] = None,
    ) -> Tuple[str, List[SlotValidationResult]]:
        """
        Fill slots in skeleton code with provided content.

        Args:
            skeleton: Skeleton code with LLM_SLOT markers
            slot_contents: Dictionary mapping slot names to content
            template_type: Optional template type for slot validation

        Returns:
            Tuple of (filled code, list of validation results)
        """
        filled = skeleton
        validation_results = []

        # Get template for validation if provided
        template = None
        if template_type:
            template = self.generator.get_template(template_type)

        for slot_name, content in slot_contents.items():
            # Validate the content
            slot_def = None
            if template:
                slot_def = template.get_slot(slot_name)

            validation = self._validate_slot_content(
                slot_name, content, slot_def
            )
            validation_results.append(validation)

            if validation.has_errors and self.strict_mode:
                logger.error(
                    f"Slot '{slot_name}' validation failed: {validation.errors}"
                )
                continue

            # Replace the slot with content
            start_marker = self.generator.SLOT_START_TEMPLATE.format(name=slot_name)
            end_marker = self.generator.SLOT_END_TEMPLATE.format(name=slot_name)

            pattern = rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
            replacement = f"{start_marker}\n{content}\n{end_marker}"

            filled = re.sub(pattern, replacement, filled, flags=re.DOTALL)

        return filled, validation_results

    def _validate_slot_content(
        self,
        slot_name: str,
        content: str,
        slot_def: Optional[LLMSlot] = None,
    ) -> SlotValidationResult:
        """
        Validate content for a slot.

        Args:
            slot_name: Name of the slot
            content: Content to validate
            slot_def: Slot definition for constraints

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        # Basic validation
        lines = content.split("\n")

        if slot_def:
            # Check line limit
            if len(lines) > slot_def.max_lines:
                errors.append(
                    f"Content exceeds max lines ({len(lines)} > {slot_def.max_lines})"
                )

            # Check forbidden patterns
            for pattern in slot_def.forbidden_patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        errors.append(
                            f"Line {i} matches forbidden pattern: {pattern}"
                        )

            # Check required patterns
            for pattern in slot_def.required_patterns:
                found = any(re.search(pattern, line) for line in lines)
                if not found:
                    warnings.append(f"Missing required pattern: {pattern}")

            # Check specific constraints
            if SlotConstraint.RETURN_REQUIRED in slot_def.constraints:
                has_return = any("return " in line for line in lines)
                if not has_return:
                    errors.append("Slot requires a return statement")

            if SlotConstraint.SINGLE_EXPRESSION in slot_def.constraints:
                non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
                if len(non_empty) > 1:
                    errors.append("Slot must be a single expression")

        # Universal validations (always apply)
        dangerous_patterns = [
            (r"os\.system\(", "os.system() is forbidden"),
            (r"subprocess\.", "subprocess is forbidden"),
            (r"eval\(", "eval() is forbidden"),
            (r"exec\(", "exec() is forbidden"),
            (r"__import__\(", "__import__() is forbidden"),
        ]

        for pattern, message in dangerous_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    errors.append(f"Line {i}: {message}")

        return SlotValidationResult(
            slot_name=slot_name,
            is_valid=len(errors) == 0,
            content=content,
            errors=errors,
            warnings=warnings,
        )

    def strip_markers(self, code: str) -> str:
        """
        Remove all LLM_SLOT markers from code.

        Args:
            code: Code with LLM_SLOT markers

        Returns:
            Code with markers removed
        """
        # Remove start markers
        code = re.sub(
            rf"\s*{self.generator.SLOT_START_PATTERN}\s*\n?",
            "",
            code
        )
        # Remove end markers
        code = re.sub(
            rf"\s*{self.generator.SLOT_END_PATTERN}\s*\n?",
            "",
            code
        )
        return code

    def has_unfilled_slots(self, code: str) -> bool:
        """Check if code still has unfilled slot markers."""
        slots = self.generator.list_slots(code)
        return len(slots) > 0

    def get_unfilled_slots(self, code: str) -> List[str]:
        """Get list of unfilled slot names."""
        return self.generator.list_slots(code)


def create_skeleton_for_entity(
    entity_name: str,
    table_name: Optional[str] = None,
) -> str:
    """
    Convenience function to create an entity skeleton.

    Args:
        entity_name: Name of the entity class (e.g., "Product")
        table_name: Optional table name (defaults to snake_case of entity_name)

    Returns:
        Entity skeleton code
    """
    generator = SkeletonGenerator()

    if table_name is None:
        # Convert PascalCase to snake_case
        table_name = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower() + "s"

    return generator.generate_skeleton(
        "entity",
        {
            "entity_name": entity_name,
            "table_name": table_name,
        }
    )


def create_skeleton_for_service(
    entity_name: str,
    service_name: Optional[str] = None,
    schema_prefix: Optional[str] = None,
) -> str:
    """
    Convenience function to create a service skeleton.

    Args:
        entity_name: Name of the entity class
        service_name: Optional service name (defaults to entity_name)
        schema_prefix: Optional schema prefix (defaults to entity_name)

    Returns:
        Service skeleton code
    """
    generator = SkeletonGenerator()

    if service_name is None:
        service_name = entity_name
    if schema_prefix is None:
        schema_prefix = entity_name

    return generator.generate_skeleton(
        "service",
        {
            "entity_name": entity_name,
            "service_name": service_name,
            "schema_prefix": schema_prefix,
        }
    )


def create_skeleton_for_router(
    entity_name: str,
    route_prefix: Optional[str] = None,
) -> str:
    """
    Convenience function to create a router skeleton.

    Args:
        entity_name: Name of the entity class
        route_prefix: Optional route prefix (defaults to plural snake_case)

    Returns:
        Router skeleton code
    """
    generator = SkeletonGenerator()

    # Convert PascalCase to snake_case
    entity_name_lower = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()

    if route_prefix is None:
        route_prefix = entity_name_lower + "s"

    return generator.generate_skeleton(
        "router",
        {
            "entity_name": entity_name,
            "entity_name_lower": entity_name_lower,
            "router_name": entity_name,
            "route_prefix": route_prefix,
            "tag_name": entity_name + "s",
            "schema_prefix": entity_name,
            "service_name": entity_name,
            "service_module": entity_name_lower + "_service",
        }
    )


def create_skeleton_for_schema(
    entity_name: str,
    schema_prefix: Optional[str] = None,
) -> str:
    """
    Convenience function to create a schema skeleton.

    Args:
        entity_name: Name of the entity class
        schema_prefix: Optional schema prefix (defaults to entity_name)

    Returns:
        Schema skeleton code
    """
    generator = SkeletonGenerator()

    if schema_prefix is None:
        schema_prefix = entity_name

    return generator.generate_skeleton(
        "schema",
        {
            "entity_name": entity_name,
            "schema_name": entity_name,
            "schema_prefix": schema_prefix,
        }
    )
