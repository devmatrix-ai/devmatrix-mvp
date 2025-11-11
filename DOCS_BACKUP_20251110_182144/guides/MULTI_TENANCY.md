# Multi-Tenancy Implementation Guide

This guide explains the multi-tenancy (data isolation) implementation in Devmatrix MVP.

## Overview

Devmatrix implements **user-level multi-tenancy** where each user's data is completely isolated from other users. The system ensures that:

- Users can only access their own data
- All database queries are automatically scoped to the current user
- Unauthorized access attempts are logged and blocked
- Foreign key relationships enforce data integrity

## Architecture

### User-Level Isolation

Every resource in the system belongs to a specific user via `user_id` foreign key:

- **Conversations**: Scoped by `user_id`
- **Messages**: Scoped by conversation (which is scoped by `user_id`)
- **MasterPlans**: Scoped by `user_id`
- **Discovery Documents**: Scoped by `user_id`
- **User Quotas**: One-to-one with `user_id`
- **User Usage**: Scoped by `user_id` and month

### Foreign Key Cascade

All foreign keys use `ON DELETE CASCADE` to ensure data cleanup:

```python
user_id = Column(
    UUID(as_uuid=True),
    ForeignKey("users.user_id", ondelete="CASCADE"),
    nullable=False,
    index=True
)
```

When a user is deleted, all their associated data is automatically removed.

## Using the Tenancy Service

### Basic Usage

```python
from src.services.tenancy_service import TenancyService
from src.api.middleware.auth_middleware import get_current_user

@router.get("/conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    """List user's conversations (automatically scoped)"""
    tenancy = TenancyService(current_user.user_id)
    conversations = tenancy.get_user_conversations(limit=50)

    return {
        "conversations": [c.to_dict() for c in conversations]
    }
```

### Verifying Ownership

Before allowing access to a specific resource, verify ownership:

```python
@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get specific conversation (with ownership check)"""
    tenancy = TenancyService(current_user.user_id)

    # Option 1: Get with authorization (raises ValueError if not owned)
    try:
        conversation = tenancy.authorize_conversation_access(conversation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation.to_dict()
```

Alternatively, check ownership first:

```python
@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete conversation (with ownership check)"""
    tenancy = TenancyService(current_user.user_id)

    # Option 2: Check ownership first
    if not tenancy.user_owns_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Proceed with deletion
    with get_db_context() as db:
        conversation = tenancy.get_user_conversation(conversation_id)
        db.delete(conversation)
        db.commit()

    return {"message": "Conversation deleted"}
```

### Custom Scoped Queries

For complex queries, use the scoped query builders:

```python
@router.get("/conversations/recent")
async def get_recent_conversations(current_user: User = Depends(get_current_user)):
    """Get recent conversations with custom filtering"""
    tenancy = TenancyService(current_user.user_id)

    with get_db_context() as db:
        # Get scoped query (automatically filters by user_id)
        query = tenancy.scope_conversation_query(db)

        # Add custom filtering
        recent_conversations = (
            query
            .filter(Conversation.created_at >= datetime.utcnow() - timedelta(days=7))
            .order_by(Conversation.created_at.desc())
            .limit(20)
            .all()
        )

    return {
        "conversations": [c.to_dict() for c in recent_conversations]
    }
```

### MasterPlan Scoping

Same patterns apply to masterplans:

```python
@router.get("/masterplans")
async def list_masterplans(current_user: User = Depends(get_current_user)):
    """List user's masterplans"""
    tenancy = TenancyService(current_user.user_id)
    masterplans = tenancy.get_user_masterplans()

    return {
        "masterplans": [mp.to_dict() for mp in masterplans]
    }

@router.get("/masterplans/{masterplan_id}")
async def get_masterplan(
    masterplan_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get specific masterplan (with ownership check)"""
    tenancy = TenancyService(current_user.user_id)

    try:
        masterplan = tenancy.authorize_masterplan_access(masterplan_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="MasterPlan not found")

    return masterplan.to_dict()
```

### Quota and Usage

Get user's quota and usage data:

```python
@router.get("/me/quota")
async def get_my_quota(current_user: User = Depends(get_current_user)):
    """Get current user's quota"""
    tenancy = TenancyService(current_user.user_id)
    quota = tenancy.get_user_quota()

    if not quota:
        return {"error": "No quota configured"}

    return quota.to_dict()

@router.get("/me/usage")
async def get_my_usage(current_user: User = Depends(get_current_user)):
    """Get current user's usage for current month"""
    tenancy = TenancyService(current_user.user_id)
    usage = tenancy.get_user_usage()

    if not usage:
        return {"tokens_used": 0, "cost": 0.0}

    return usage.to_dict()
```

## Security Best Practices

### 1. Always Use TenancyService for Data Access

**❌ BAD - Direct query without scoping:**

```python
# DANGEROUS: Can access any user's data!
with get_db_context() as db:
    conversation = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()
```

**✅ GOOD - Scoped query via TenancyService:**

```python
# SAFE: Only returns conversation if user owns it
tenancy = TenancyService(current_user.user_id)
conversation = tenancy.get_user_conversation(conversation_id)
```

### 2. Never Trust Client-Provided User IDs

**❌ BAD - Using user_id from request:**

```python
# DANGEROUS: Attacker could pass any user_id
@router.get("/users/{user_id}/conversations")
async def get_user_conversations(user_id: UUID):
    # This allows accessing ANY user's data!
    with get_db_context() as db:
        return db.query(Conversation).filter(Conversation.user_id == user_id).all()
```

**✅ GOOD - Using authenticated user:**

```python
# SAFE: Can only access own data
@router.get("/me/conversations")
async def get_my_conversations(current_user: User = Depends(get_current_user)):
    tenancy = TenancyService(current_user.user_id)
    return tenancy.get_user_conversations()
```

### 3. Return 404 (Not 403) for Unauthorized Access

To prevent information disclosure, return 404 instead of 403 when a resource doesn't exist OR isn't owned by the user:

**❌ BAD - Reveals resource existence:**

```python
if not tenancy.user_owns_conversation(conversation_id):
    raise HTTPException(status_code=403, detail="Access denied")  # Reveals it exists!
```

**✅ GOOD - Hides resource existence:**

```python
if not tenancy.user_owns_conversation(conversation_id):
    raise HTTPException(status_code=404, detail="Conversation not found")
```

### 4. Log Unauthorized Access Attempts

The TenancyService automatically logs unauthorized access attempts:

```python
# Automatically logged when user tries to access another user's data
conversation = tenancy.get_user_conversation(conversation_id)
# Logs: "User <uuid> attempted to access unauthorized conversation <uuid>"
```

Monitor these logs for potential security issues.

## Database Schema Patterns

### Adding New Multi-Tenant Tables

When creating new tables that should be user-scoped:

```python
class NewResource(Base):
    __tablename__ = "new_resources"

    # Primary key
    resource_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Multi-tenancy: Add user_id FK with CASCADE delete
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Important for query performance!
    )

    # Other fields...
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Add index on user_id for performance
    __table_args__ = (
        Index('idx_new_resources_user', 'user_id'),
    )
```

### Migration for Multi-Tenant Tables

```python
def upgrade():
    op.create_table(
        'new_resources',
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        # Foreign key with CASCADE delete
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.user_id'],
            ondelete='CASCADE'
        ),
    )

    # Create index for performance
    op.create_index('idx_new_resources_user', 'new_resources', ['user_id'])
```

## Testing Multi-Tenancy

### Unit Test Example

```python
def test_user_cannot_access_other_users_data():
    """Test that users cannot access other users' conversations"""
    # Create two users
    user1 = create_test_user("user1@example.com")
    user2 = create_test_user("user2@example.com")

    # User 1 creates conversation
    with get_db_context() as db:
        conversation = Conversation(user_id=user1.user_id, title="User 1 Chat")
        db.add(conversation)
        db.commit()
        conversation_id = conversation.conversation_id

    # User 2 tries to access User 1's conversation
    tenancy_user2 = TenancyService(user2.user_id)
    result = tenancy_user2.get_user_conversation(conversation_id)

    # Should return None (not found)
    assert result is None

    # User 1 can access their own conversation
    tenancy_user1 = TenancyService(user1.user_id)
    result = tenancy_user1.get_user_conversation(conversation_id)

    # Should return the conversation
    assert result is not None
    assert result.conversation_id == conversation_id
```

### Integration Test Example

```python
def test_api_conversation_isolation(test_client):
    """Test API endpoint enforces conversation isolation"""
    # Create two users with tokens
    user1_token = create_user_and_get_token("user1@example.com")
    user2_token = create_user_and_get_token("user2@example.com")

    # User 1 creates conversation
    response = test_client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={"title": "User 1 Chat"}
    )
    assert response.status_code == 201
    conversation_id = response.json()["conversation_id"]

    # User 2 tries to access User 1's conversation
    response = test_client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {user2_token}"}
    )

    # Should return 404 (not 403, to hide existence)
    assert response.status_code == 404

    # User 1 can access their own conversation
    response = test_client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {user1_token}"}
    )

    # Should return 200
    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id
```

## Performance Considerations

### Always Index user_id Columns

Every table with a `user_id` column should have an index:

```python
Index('idx_tablename_user_id', 'user_id')
```

This ensures fast filtering when querying user-specific data.

### Use Compound Indexes When Appropriate

If you frequently filter by user_id and another field:

```python
# Example: Querying user's conversations by date
Index('idx_conversations_user_created', 'user_id', 'created_at')
```

### Avoid N+1 Queries

When loading related data, use eager loading:

```python
# BAD: N+1 queries
conversations = tenancy.get_user_conversations()
for conv in conversations:
    messages = conv.messages  # Triggers separate query for each conversation!

# GOOD: Eager loading with joinedload
from sqlalchemy.orm import joinedload

with get_db_context() as db:
    conversations = (
        tenancy.scope_conversation_query(db)
        .options(joinedload(Conversation.messages))  # Load messages in single query
        .all()
    )
```

## Future Enhancements

### Workspace/Organization Multi-Tenancy

For true multi-user workspaces, the schema would need to be extended:

1. Add `Workspace` model
2. Add `WorkspaceMember` model (many-to-many)
3. Add `workspace_id` to all resources
4. Update TenancyService to support workspace context
5. Add workspace invitation and role management

This is beyond the scope of the current MVP but can be added later.

## Summary

- **Always use TenancyService** for accessing user data
- **Never trust client-provided user IDs** - use authenticated user
- **Return 404 for unauthorized access** to prevent information disclosure
- **Index all user_id columns** for performance
- **Use CASCADE delete** on foreign keys for data cleanup
- **Test isolation thoroughly** with unit and integration tests

By following these patterns, you ensure that users' data remains completely isolated and secure.
