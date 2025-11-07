"""
Conversations Router - Sharing & Collaboration

API endpoints for conversation sharing functionality.
Task Group 10 - Phase 2: Resource Sharing & Collaboration

Endpoints:
- GET /api/v1/conversations - List all conversations for current user
- POST /api/v1/conversations/{conversation_id}/share - Share conversation
- GET /api/v1/conversations/{conversation_id}/shares - List shares for conversation
- PATCH /api/v1/conversations/{conversation_id}/shares/{share_id} - Update share permission
- DELETE /api/v1/conversations/{conversation_id}/shares/{share_id} - Revoke share
- GET /api/v1/conversations/shared-with-me - List conversations shared with current user
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, EmailStr

from src.services.sharing_service import SharingService
from src.api.middleware.auth_middleware import get_current_user
from src.models.user import User
from src.observability import get_logger

router = APIRouter()
logger = get_logger("conversations_router")


# ==========================================
# Request/Response Models
# ==========================================

class ShareConversationRequest(BaseModel):
    """Request to share conversation."""
    user_email: EmailStr
    permission_level: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_email": "alice@example.com",
                "permission_level": "view"
            }
        }


class UpdateSharePermissionRequest(BaseModel):
    """Request to update share permission."""
    permission_level: str

    class Config:
        json_schema_extra = {
            "example": {
                "permission_level": "edit"
            }
        }


class ShareResponse(BaseModel):
    """Response for share operations."""
    share_id: str
    conversation_id: str
    shared_with_user_id: str
    shared_with_email: str
    permission_level: str
    shared_at: str


class ConversationShareListItem(BaseModel):
    """List item for conversation shares."""
    share_id: str
    shared_with_user_id: str
    shared_with_email: str
    shared_with_username: str
    permission_level: str
    shared_at: str


class SharedWithMeItem(BaseModel):
    """List item for conversations shared with me."""
    conversation_id: str
    title: str
    owner_username: str
    permission_level: str
    shared_at: str
    shared_by_user_id: str


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    id: str
    created_at: str
    updated_at: str
    message_count: int
    last_message_preview: Optional[str]
    workspace_id: Optional[str]


# ==========================================
# API Endpoints
# ==========================================

@router.get(
    "/",
    response_model=List[ConversationSummary],
    summary="List conversations",
    description="List all conversations for the current user with summaries."
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    List all conversations with summaries.

    Returns conversations owned by the user, ordered by most recent.
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Build query - filter by user_id for security
        # Note: conversations table does not have metadata or workspace_id columns
        query = """
            SELECT
                c.conversation_id,
                c.created_at,
                c.updated_at,
                COUNT(m.message_id) as message_count,
                (
                    SELECT content
                    FROM messages
                    WHERE conversation_id = c.conversation_id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) as last_message
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.conversation_id
            WHERE c.user_id = %s
            GROUP BY c.conversation_id
            ORDER BY c.updated_at DESC
            LIMIT %s
        """
        params = (str(current_user.user_id), limit)

        results = db._execute(query, params, fetch=True, operation="list_conversations")

        # Format results
        conversations = []
        for row in results:
            # Get preview (first 100 chars of last message)
            preview = None
            if row['last_message']:
                preview = row['last_message'][:100]
                if len(row['last_message']) > 100:
                    preview += "..."

            conversations.append(ConversationSummary(
                id=row['conversation_id'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat(),
                message_count=row['message_count'],
                last_message_preview=preview,
                workspace_id=None
            ))

        logger.info(f"Listed {len(conversations)} conversations for user {current_user.user_id}")
        return conversations

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/{conversation_id}/share",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share conversation with user",
    description="Share a conversation with another user. Only the conversation owner can share."
)
async def share_conversation(
    conversation_id: uuid.UUID,
    request: ShareConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Share conversation with another user.

    Permission levels:
    - view: Read-only access
    - comment: Read + write messages
    - edit: Full access except delete/re-share

    Only conversation owner can share.
    Cannot share same conversation twice to same user.
    Email notification sent to recipient.
    """
    try:
        sharing_service = SharingService()

        share = sharing_service.share_conversation(
            conversation_id=conversation_id,
            shared_with_email=request.user_email,
            permission_level=request.permission_level,
            shared_by_user_id=current_user.user_id
        )

        # Get recipient user details for response
        from src.models.user import User as UserModel
        from src.config.database import get_db_context

        with get_db_context() as db:
            recipient = db.query(UserModel).filter(
                UserModel.user_id == share.shared_with
            ).first()

        logger.info(
            f"Conversation {conversation_id} shared with {request.user_email} "
            f"by user {current_user.user_id}"
        )

        return ShareResponse(
            share_id=str(share.share_id),
            conversation_id=str(share.conversation_id),
            shared_with_user_id=str(share.shared_with),
            shared_with_email=recipient.email if recipient else request.user_email,
            permission_level=share.permission_level,
            shared_at=share.shared_at.isoformat()
        )

    except ValueError as e:
        logger.warning(f"Invalid share request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(
            f"User {current_user.user_id} attempted to share conversation "
            f"{conversation_id} without permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sharing conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while sharing conversation"
        )


@router.get(
    "/{conversation_id}/shares",
    response_model=List[ConversationShareListItem],
    summary="List shares for conversation",
    description="List all shares for a conversation. Only the conversation owner can list shares."
)
async def list_conversation_shares(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    """
    List all shares for a conversation.

    Only conversation owner can list shares.
    Returns list of users the conversation is shared with.
    """
    try:
        sharing_service = SharingService()

        shares = sharing_service.list_conversation_shares(
            conversation_id=conversation_id,
            user_id=current_user.user_id
        )

        # Get user details for each share
        from src.models.user import User as UserModel
        from src.config.database import get_db_context

        share_items = []
        with get_db_context() as db:
            for share in shares:
                user = db.query(UserModel).filter(
                    UserModel.user_id == share.shared_with
                ).first()

                if user:
                    share_items.append(
                        ConversationShareListItem(
                            share_id=str(share.share_id),
                            shared_with_user_id=str(share.shared_with),
                            shared_with_email=user.email,
                            shared_with_username=user.username,
                            permission_level=share.permission_level,
                            shared_at=share.shared_at.isoformat()
                        )
                    )

        logger.info(
            f"User {current_user.user_id} listed {len(share_items)} shares "
            f"for conversation {conversation_id}"
        )

        return share_items

    except PermissionError as e:
        logger.warning(
            f"User {current_user.user_id} attempted to list shares for "
            f"conversation {conversation_id} without permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing conversation shares: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing shares"
        )


@router.patch(
    "/{conversation_id}/shares/{share_id}",
    response_model=ShareResponse,
    summary="Update share permission",
    description="Update permission level for an existing share. Only the conversation owner can update."
)
async def update_share_permission(
    conversation_id: uuid.UUID,
    share_id: uuid.UUID,
    request: UpdateSharePermissionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update permission level for existing share.

    Only conversation owner can update permissions.
    """
    try:
        sharing_service = SharingService()

        updated_share = sharing_service.update_share_permission(
            share_id=share_id,
            new_permission_level=request.permission_level,
            user_id=current_user.user_id
        )

        # Get recipient user details for response
        from src.models.user import User as UserModel
        from src.config.database import get_db_context

        with get_db_context() as db:
            recipient = db.query(UserModel).filter(
                UserModel.user_id == updated_share.shared_with
            ).first()

        logger.info(
            f"Share {share_id} permission updated to {request.permission_level} "
            f"by user {current_user.user_id}"
        )

        return ShareResponse(
            share_id=str(updated_share.share_id),
            conversation_id=str(updated_share.conversation_id),
            shared_with_user_id=str(updated_share.shared_with),
            shared_with_email=recipient.email if recipient else "",
            permission_level=updated_share.permission_level,
            shared_at=updated_share.shared_at.isoformat()
        )

    except ValueError as e:
        logger.warning(f"Invalid update share request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(
            f"User {current_user.user_id} attempted to update share {share_id} "
            f"without permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating share permission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating share"
        )


@router.delete(
    "/{conversation_id}/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke share",
    description="Revoke a conversation share. Only the conversation owner can revoke."
)
async def revoke_share(
    conversation_id: uuid.UUID,
    share_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Revoke conversation share.

    Only conversation owner can revoke shares.
    """
    try:
        sharing_service = SharingService()

        sharing_service.revoke_share(
            share_id=share_id,
            user_id=current_user.user_id
        )

        logger.info(
            f"Share {share_id} revoked by user {current_user.user_id}"
        )

        return None  # 204 No Content

    except ValueError as e:
        logger.warning(f"Invalid revoke share request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(
            f"User {current_user.user_id} attempted to revoke share {share_id} "
            f"without permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error revoking share: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while revoking share"
        )


@router.get(
    "/shared-with-me",
    response_model=List[SharedWithMeItem],
    summary="List conversations shared with me",
    description="List all conversations shared with the current user."
)
async def list_shared_with_me(
    current_user: User = Depends(get_current_user)
):
    """
    List all conversations shared with current user.

    Returns conversations with permission level for each.
    """
    try:
        sharing_service = SharingService()

        shared_conversations = sharing_service.list_shared_with_user(
            user_id=current_user.user_id
        )

        # Get owner details for each conversation
        from src.models.user import User as UserModel
        from src.config.database import get_db_context

        shared_items = []
        with get_db_context() as db:
            for item in shared_conversations:
                conversation = item["conversation"]
                owner = db.query(UserModel).filter(
                    UserModel.user_id == conversation.user_id
                ).first()

                shared_items.append(
                    SharedWithMeItem(
                        conversation_id=str(conversation.conversation_id),
                        title=conversation.title or "Untitled Conversation",
                        owner_username=owner.username if owner else "Unknown",
                        permission_level=item["permission_level"],
                        shared_at=item["shared_at"].isoformat(),
                        shared_by_user_id=str(item["shared_by"])
                    )
                )

        logger.info(
            f"User {current_user.user_id} listed {len(shared_items)} "
            f"conversations shared with them"
        )

        return shared_items

    except Exception as e:
        logger.error(f"Error listing shared conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing shared conversations"
        )
