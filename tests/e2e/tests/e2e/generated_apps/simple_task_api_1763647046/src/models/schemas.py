"""
Pydantic Schemas

Request/response models for API endpoints.
"""
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
{% for entity in entities %}

# {{ entity.name }} Schemas
class {{ entity.name }}Base(BaseModel):
    """Base schema for {{ entity.name }}."""
    {% for field in entity.fields %}
    {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
    {{ field.name }}: {% if not field.required %}Optional[{{ field.type }}]{% else %}{{ field.type }}{% endif %} = Field(
        {% if not field.required %}None{% elif field.default %}{{ field.default }}{% else %}...{% endif %}
        {% if field.constraints %}
        {% for constraint_name, constraint_value in field.constraints.items() %}
        , {{ constraint_name }}={{ constraint_value }}
        {% endfor %}
        {% endif %}
    )
    {% endif %}
    {% endfor %}


class {{ entity.name }}Create({{ entity.name }}Base):
    """Schema for creating {{ entity.name }}."""
    model_config = ConfigDict(strict=True)  # Enable strict validation


class {{ entity.name }}Update(BaseModel):
    """Schema for updating {{ entity.name }} (all fields optional)."""
    model_config = ConfigDict(strict=True)

    {% for field in entity.fields %}
    {% if not field.primary_key and field.name not in ['created_at', 'updated_at'] %}
    {{ field.name }}: Optional[{{ field.type }}] = Field(
        None
        {% if field.constraints %}
        {% for constraint_name, constraint_value in field.constraints.items() %}
        , {{ constraint_name }}={{ constraint_value }}
        {% endfor %}
        {% endif %}
    )
    {% endif %}
    {% endfor %}


class {{ entity.name }}({{ entity.name }}Base):
    """Schema for {{ entity.name }} response."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # Allow ORM models


class {{ entity.name }}List(BaseModel):
    """Paginated {{ entity.name }} list response."""
    items: list[{{ entity.name }}]
    total: int
    page: int
    size: int
    pages: int
{% endfor %}