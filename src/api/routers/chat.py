"""
Chat Router

HTTP endpoints for chat conversation management.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.chat_service import ChatService
from src.observability import StructuredLogger
from src.observability.global_metrics import metrics_collector


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
):
    """
    List all conversations with summaries.

    Args:
        limit: Maximum number of conversations to return
        workspace_id: Optional filter by workspace

    Returns:
        List of conversation summaries
    """
    try:
        from src.state.postgres_manager import PostgresManager

        db = PostgresManager()

        # Build query
        if workspace_id:
            query = """
                SELECT
                    c.id,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COUNT(m.id) as message_count,
                    (
                        SELECT content
                        FROM messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) as last_message
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.metadata->>'workspace_id' = %s
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %s
            """
            params = (workspace_id, limit)
        else:
            query = """
                SELECT
                    c.id,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COUNT(m.id) as message_count,
                    (
                        SELECT content
                        FROM messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) as last_message
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %s
            """
            params = (limit,)

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
                id=row['id'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat(),
                message_count=row['message_count'],
                last_message_preview=preview,
                workspace_id=row['metadata'].get('workspace_id') if row['metadata'] else None
            ))

        logger.info(f"Listed {len(conversations)} conversations")
        return conversations

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """
    Get full conversation details including all messages.

    Args:
        conversation_id: Conversation ID

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


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation ID

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

        # Delete conversation (CASCADE will delete messages)
        query = "DELETE FROM conversations WHERE id = %s"
        db._execute(query, (conversation_id,), operation=f"delete_conversation:{conversation_id}")

        logger.info(f"Deleted conversation {conversation_id}")
        return {"message": f"Conversation {conversation_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
