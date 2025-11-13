"""Permission checking and authorization logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.user import User


def check_organization_access(user: User, organization_id: str) -> None:
    """Check if user has access to organization."""
    if user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization",
        )


def check_resource_access(
    user: User,
    resource_organization_id: str,
    resource_owner_id: str = None,
) -> None:
    """Check if user has access to a resource."""
    check_organization_access(user, resource_organization_id)

    if resource_owner_id and not user.is_superuser:
        if user.id != resource_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resource",
            )
