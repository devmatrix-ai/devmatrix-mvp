"""
Chat Router

HTTP endpoints for chat conversation management.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel

from src.services.chat_service import ChatService
from src.observability import StructuredLogger
from src.observability.global_metrics import metrics_collector
from src.api.middleware.ownership_middleware import require_resource_ownership
from src.api.middleware.auth_middleware import get_current_user
from src.models.user import User
from src.observability.audit_logger import audit_logger


router = APIRouter()
logger = StructuredLogger("chat_router")

# Create chat service instance
chat_service = ChatService(metrics_collector=metrics_collector)


# ==========================================
# Response Models
# ==========================================

class ConversationSummary(BaseModel):
    """Summary of a conversation for list view."""
    id: str
    created_at: str
    updated_at: str
    message_count: int
    last_message_preview: Optional[str] = None
    workspace_id: Optional[str] = None


class ConversationDetail(BaseModel):
    """Full conversation details."""
    id: str
    created_at: str
    updated_at: str
    workspace_id: Optional[str] = None
    messages: List[dict]
    metadata: dict


# ==========================================
# Endpoints
# ==========================================

@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List all conversations with summaries.

    Args:
        limit: Maximum number of conversations to return
        workspace_id: Optional filter by workspace
        current_user: Authenticated user

    Returns:
        List of conversation summaries
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Build query - filter by user_id for security
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


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
@require_resource_ownership("conversation")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get full conversation details including all messages.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Full conversation details
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Get conversation
        conv_data = db.get_conversation(conversation_id)
        if not conv_data:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        # Get messages
        messages = db.get_conversation_messages(conversation_id)

        return ConversationDetail(
            id=conv_data['id'],
            created_at=conv_data['created_at'].isoformat(),
            updated_at=conv_data['updated_at'].isoformat(),
            workspace_id=conv_data['metadata'].get('workspace_id') if conv_data['metadata'] else None,
            messages=[
                {
                    'id': msg['id'],
                    'role': msg['role'],
                    'content': msg['content'],
                    'created_at': msg['created_at'].isoformat(),
                    'metadata': msg.get('metadata', {})
                }
                for msg in messages
            ],
            metadata=conv_data.get('metadata', {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}")
@require_resource_ownership("conversation")
async def update_conversation(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Update a conversation.

    Args:
        request: FastAPI request object
        conversation_id: Conversation ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Success message
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Check if conversation exists
        conv_data = db.get_conversation(conversation_id)
        if not conv_data:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        # Update conversation (implementation depends on requirements)
        # For now, just acknowledge the update

        # Log modification
        await audit_logger.log_modification(
            user_id=current_user.user_id,
            resource_type="conversation",
            resource_id=conversation_id,
            action="update",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"Updated conversation {conversation_id}")
        return {"message": f"Conversation {conversation_id} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
@require_resource_ownership("conversation")
async def delete_conversation(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages.

    Args:
        request: FastAPI request object
        conversation_id: Conversation ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Success message
    """
    try:
        from src.state.postgres_manager import PostgresManager
        from uuid import UUID

        db = PostgresManager()

        # Check if conversation exists
        conv_data = db.get_conversation(conversation_id)
        if not conv_data:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        # Delete conversation (CASCADE will delete messages)
        query = "DELETE FROM conversations WHERE conversation_id = %s"
        db._execute(query, (conversation_id,), operation=f"delete_conversation:{conversation_id}")

        # Log modification
        await audit_logger.log_modification(
            user_id=current_user.user_id,
            resource_type="conversation",
            resource_id=UUID(conversation_id),
            action="delete",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"Deleted conversation {conversation_id}")
        return {"message": f"Conversation {conversation_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
@require_resource_ownership("conversation")
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all messages in a conversation.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        List of messages
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Get messages
        messages = db.get_conversation_messages(conversation_id)

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    'id': msg['id'],
                    'role': msg['role'],
                    'content': msg['content'],
                    'created_at': msg['created_at'].isoformat(),
                    'metadata': msg.get('metadata', {})
                }
                for msg in messages
            ]
        }

    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
@require_resource_ownership("conversation")
async def create_message(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new message in a conversation.

    Args:
        request: FastAPI request object
        conversation_id: Conversation ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Created message
    """
    try:
        from src.state.postgres_manager import PostgresManager
        from uuid import UUID, uuid4

        db = PostgresManager()

        # Get request body
        body = await request.json()
        role = body.get('role', 'user')
        content = body.get('content', '')

        # Create message
        message_id = str(uuid4())
        query = """
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING id, role, content, created_at
        """
        result = db._execute(
            query,
            (message_id, conversation_id, role, content),
            fetch=True,
            operation="create_message"
        )

        # Log modification
        await audit_logger.log_modification(
            user_id=current_user.user_id,
            resource_type="message",
            resource_id=UUID(message_id),
            action="create",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"conversation_id": conversation_id},
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"Created message {message_id} in conversation {conversation_id}")

        if result:
            row = result[0]
            return {
                "id": row['id'],
                "role": row['role'],
                "content": row['content'],
                "created_at": row['created_at'].isoformat()
            }

        return {"message": "Message created successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}/messages/{message_id}")
@require_resource_ownership("conversation")
async def update_message(
    request: Request,
    conversation_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Update a message in a conversation.

    Args:
        request: FastAPI request object
        conversation_id: Conversation ID
        message_id: Message ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Updated message
    """
    try:
        from src.state.postgres_manager import PostgresManager
        from uuid import UUID

        db = PostgresManager()

        # Get request body
        body = await request.json()
        content = body.get('content', '')

        # Update message
        query = """
            UPDATE messages
            SET content = %s
            WHERE id = %s AND conversation_id = %s
            RETURNING id, role, content, created_at
        """
        result = db._execute(
            query,
            (content, message_id, conversation_id),
            fetch=True,
            operation="update_message"
        )

        if not result:
            raise HTTPException(status_code=404, detail=f"Message {message_id} not found")

        # Log modification
        await audit_logger.log_modification(
            user_id=current_user.user_id,
            resource_type="message",
            resource_id=UUID(message_id),
            action="update",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"conversation_id": conversation_id},
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"Updated message {message_id} in conversation {conversation_id}")

        row = result[0]
        return {
            "id": row['id'],
            "role": row['role'],
            "content": row['content'],
            "created_at": row['created_at'].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}/messages/{message_id}")
@require_resource_ownership("conversation")
async def delete_message(
    request: Request,
    conversation_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a message from a conversation.

    Args:
        request: FastAPI request object
        conversation_id: Conversation ID
        message_id: Message ID
        current_user: Authenticated user (required for ownership check)

    Returns:
        Success message
    """
    try:
        from src.state.postgres_manager import PostgresManager
        from uuid import UUID

        db = PostgresManager()

        # Delete message
        query = "DELETE FROM messages WHERE id = %s AND conversation_id = %s"
        db._execute(query, (message_id, conversation_id), operation="delete_message")

        # Log modification
        await audit_logger.log_modification(
            user_id=current_user.user_id,
            resource_type="message",
            resource_id=UUID(message_id),
            action="delete",
            ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"conversation_id": conversation_id},
            correlation_id=getattr(request.state, 'correlation_id', None)
        )

        logger.info(f"Deleted message {message_id} from conversation {conversation_id}")
        return {"message": f"Message {message_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
