"""
{{ entity.name }} Service

Business logic layer for {{ entity.table_name }}.
"""
from uuid import UUID
from typing import Optional
from src.repositories.{{ entity.snake_name }}_repository import {{ entity.name }}Repository
from src.models.schemas import {{ entity.name }}Create, {{ entity.name }}Update, {{ entity.name }}, {{ entity.name }}List
from src.models.entities import {{ entity.name }}Entity
from src.core.security import sanitize_html
import structlog

logger = structlog.get_logger(__name__)


class {{ entity.name }}Service:
    """Business logic for {{ entity.table_name }}."""

    def __init__(self, repository: {{ entity.name }}Repository):
        self.repo = repository

    async def create_{{ entity.snake_name }}(self, {{ entity.snake_name }}_data: {{ entity.name }}Create) -> {{ entity.name }}:
        """
        Create new {{ entity.snake_name }} with business validation.

        Args:
            {{ entity.snake_name }}_data: {{ entity.name }} creation data

        Returns:
            Created {{ entity.snake_name }} schema
        """
        # Sanitize HTML in text fields to prevent XSS
        {% for field in entity.fields %}
        {% if field.type == "str" and field.name not in ['id', 'email'] and not field.primary_key %}
        if {{ entity.snake_name }}_data.{{ field.name }}:
            {{ entity.snake_name }}_data.{{ field.name }} = sanitize_html({{ entity.snake_name }}_data.{{ field.name }})
        {% endif %}
        {% endfor %}

        # Create in database
        {{ entity.snake_name }}_entity = await self.repo.create({{ entity.snake_name }}_data)
        return {{ entity.name }}.model_validate({{ entity.snake_name }}_entity)

    async def get_{{ entity.snake_name }}(self, {{ entity.snake_name }}_id: UUID) -> Optional[{{ entity.name }}]:
        """
        Get {{ entity.snake_name }} by ID.

        Args:
            {{ entity.snake_name }}_id: {{ entity.name }} UUID

        Returns:
            {{ entity.name }} schema or None if not found
        """
        {{ entity.snake_name }}_entity = await self.repo.get({{ entity.snake_name }}_id)
        if not {{ entity.snake_name }}_entity:
            return None
        return {{ entity.name }}.model_validate({{ entity.snake_name }}_entity)

    async def list_{{ entity.table_name }}(self, page: int = 1, size: int = 10) -> {{ entity.name }}List:
        """
        List {{ entity.table_name }} with pagination.

        Args:
            page: Page number (1-indexed)
            size: Items per page

        Returns:
            Paginated {{ entity.snake_name }} list
        """
        skip = (page - 1) * size

        {{ entity.table_name }} = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return {{ entity.name }}List(
            items=[{{ entity.name }}.model_validate(t) for t in {{ entity.table_name }}],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )

    async def update_{{ entity.snake_name }}(
        self, {{ entity.snake_name }}_id: UUID, {{ entity.snake_name }}_data: {{ entity.name }}Update
    ) -> Optional[{{ entity.name }}]:
        """
        Update {{ entity.snake_name }}.

        Args:
            {{ entity.snake_name }}_id: {{ entity.name }} UUID
            {{ entity.snake_name }}_data: Update data

        Returns:
            Updated {{ entity.snake_name }} schema or None if not found
        """
        # Sanitize HTML in text fields
        {% for field in entity.fields %}
        {% if field.type == "str" and field.name not in ['id', 'email'] and not field.primary_key %}
        if {{ entity.snake_name }}_data.{{ field.name }}:
            {{ entity.snake_name }}_data.{{ field.name }} = sanitize_html({{ entity.snake_name }}_data.{{ field.name }})
        {% endif %}
        {% endfor %}

        {{ entity.snake_name }}_entity = await self.repo.update({{ entity.snake_name }}_id, {{ entity.snake_name }}_data)
        if not {{ entity.snake_name }}_entity:
            return None
        return {{ entity.name }}.model_validate({{ entity.snake_name }}_entity)

    async def delete_{{ entity.snake_name }}(self, {{ entity.snake_name }}_id: UUID) -> bool:
        """
        Delete {{ entity.snake_name }}.

        Args:
            {{ entity.snake_name }}_id: {{ entity.name }} UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.repo.delete({{ entity.snake_name }}_id)