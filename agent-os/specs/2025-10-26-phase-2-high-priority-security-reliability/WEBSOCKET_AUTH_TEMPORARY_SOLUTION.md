# WebSocket Authentication - Temporary Solution

**Status:** ⚠️ TEMPORARY - For Development/Demo Only
**Created:** 2025-10-28
**Phase:** Pre-Phase 2
**Priority:** P1 (Must be fixed in Phase 2)

## Problem

The WebSocket chat system (`/socket.io`) currently does not authenticate users. When a client connects and creates a conversation, the system needs to associate the conversation with a `user_id` (required by the database schema), but the WebSocket handler has no authentication mechanism to obtain the user's identity.

### Database Constraint
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id),  -- ❌ Required but not provided
    session_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Error Before Fix
```
null value in column "user_id" of relation "conversations" violates not-null constraint
```

## Temporary Solution (Current Implementation)

To unblock development and demo of the masterplan generation feature, we implemented a temporary fallback:

### Implementation

**File:** `src/state/postgres_manager.py:541`

```python
def create_conversation(
    self,
    conversation_id: str,
    session_id: str,
    metadata: dict = None,
    user_id: str = None,  # Optional
) -> str:
    # TEMPORARY: Use demo user as fallback
    if user_id is None:
        user_id = "7b10ae4c-2158-46be-be91-18dec7d02767"  # demo@devmatrix.com

    query = """
        INSERT INTO conversations (id, user_id, session_id, metadata)
        VALUES (%s, %s, %s, %s)
        ...
    """
```

**Demo User:**
- Email: `demo@devmatrix.com`
- Username: `demo`
- Password: `Demo123!`
- UUID: `7b10ae4c-2158-46be-be91-18dec7d02767`

### Behavior

1. **Unauthenticated WebSocket connections** → All conversations assigned to demo user
2. **No user isolation** → All anonymous users share the same `user_id`
3. **Works for single-user demo** → Allows testing masterplan generation immediately

## Why This Is NOT Production-Ready

### Security Issues

1. **No Authentication**
   - Anyone can connect to WebSocket without credentials
   - No way to verify user identity

2. **No Authorization**
   - All users share conversations
   - No data isolation between users

3. **Privacy Violation**
   - User A can see conversations from User B
   - Violates multi-tenancy principles

4. **Audit Trail Broken**
   - Cannot track which real user performed actions
   - All actions attributed to demo user

### Business Impact

- **Cannot support multiple users**
- **Cannot charge per user**
- **Cannot enforce quotas per user**
- **Security compliance failures (SOC2, GDPR)**

## Proper Solution (Phase 2 Implementation)

### Task: P1-04 - Implement WebSocket Authentication

**Objective:** Authenticate WebSocket connections using JWT tokens

### Implementation Steps

#### 1. **Frontend: Send JWT Token in WebSocket Connection**

```typescript
// src/ui/src/lib/websocket.ts
const token = localStorage.getItem('auth_token');

const socket = io('http://localhost:8000', {
  auth: {
    token: token  // Send JWT token
  },
  extraHeaders: {
    'Authorization': `Bearer ${token}`  // Alternative: HTTP header
  }
});
```

#### 2. **Backend: Extract and Validate Token in WebSocket Handler**

```python
# src/api/routers/websocket.py

@sio.event
async def connect(sid, environ, auth):
    """Authenticate WebSocket connection."""
    try:
        # Extract token from auth or headers
        token = auth.get('token') if auth else None

        if not token:
            # Check HTTP headers as fallback
            headers = environ.get('HTTP_AUTHORIZATION', '')
            if headers.startswith('Bearer '):
                token = headers[7:]

        if not token:
            logger.warning(f"WebSocket connection {sid} rejected: No token")
            return False  # Reject connection

        # Validate JWT token
        from src.services.auth_service import AuthService
        auth_service = AuthService()
        user = auth_service.verify_access_token(token)

        if not user:
            logger.warning(f"WebSocket connection {sid} rejected: Invalid token")
            return False  # Reject connection

        # Store user_id in session
        async with sio.session(sid) as session:
            session['user_id'] = str(user.user_id)
            session['user_email'] = user.email

        logger.info(f"WebSocket connection {sid} authenticated as {user.email}")

    except Exception as e:
        logger.error(f"Authentication failed for {sid}: {e}")
        return False  # Reject connection
```

#### 3. **Pass user_id to Conversation Creation**

```python
# src/api/routers/websocket.py

@sio.event
async def join_chat(sid, data):
    # Get user_id from authenticated session
    async with sio.session(sid) as session:
        user_id = session.get('user_id')

    if not user_id:
        await sio.emit('error', {'message': 'Unauthorized'}, room=sid)
        return

    # Create conversation with authenticated user_id
    conversation_id = chat_service.create_conversation(
        workspace_id=workspace_id,
        metadata={'sid': sid},
        session_id=sid,
        user_id=user_id  # ✅ Now authenticated
    )
```

#### 4. **Update chat_service.py**

```python
# src/services/chat_service.py

def create_conversation(
    self,
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,  # Make this REQUIRED
) -> str:
    # Remove demo user fallback
    if user_id is None:
        raise ValueError("user_id is required for authenticated conversations")

    # ... rest of implementation
```

#### 5. **Remove Demo User Fallback**

```python
# src/state/postgres_manager.py

def create_conversation(
    self,
    conversation_id: str,
    session_id: str,
    user_id: str,  # Make REQUIRED (remove Optional)
    metadata: dict = None,
) -> str:
    # Remove this block:
    # if user_id is None:
    #     user_id = "7b10ae4c-2158-46be-be91-18dec7d02767"

    query = """
        INSERT INTO conversations (id, user_id, session_id, metadata)
        VALUES (%s, %s, %s, %s)
        ...
    """
```

### Testing

```python
# tests/integration/test_websocket_auth.py

async def test_websocket_requires_authentication():
    """Test that WebSocket connections without token are rejected."""
    socket = socketio.AsyncClient()

    # Should fail without token
    with pytest.raises(Exception):
        await socket.connect('http://localhost:8000')

async def test_websocket_with_valid_token():
    """Test that WebSocket connections with valid token succeed."""
    # Login to get token
    response = requests.post('/api/v1/auth/login', json={
        'email': 'test@example.com',
        'password': 'Test123!'
    })
    token = response.json()['access_token']

    # Connect with token
    socket = socketio.AsyncClient()
    await socket.connect('http://localhost:8000', auth={'token': token})

    # Should succeed
    assert socket.connected
```

## Migration Plan

### Phase 1: Implement (This Phase)
- Implement JWT authentication for WebSocket (P1-04)
- Update frontend to send tokens
- Update backend to validate tokens
- Add integration tests

### Phase 2: Migrate Existing Data
```sql
-- Option 1: Delete anonymous conversations (if demo data)
DELETE FROM conversations WHERE user_id = '7b10ae4c-2158-46be-be91-18dec7d02767';

-- Option 2: Keep conversations but mark them (if valuable data)
UPDATE conversations
SET metadata = jsonb_set(metadata, '{migrated_from_demo}', 'true')
WHERE user_id = '7b10ae4c-2158-46be-be91-18dec7d02767';
```

### Phase 3: Enforce Requirement
- Make `user_id` required (remove fallback)
- Add database migration to enforce NOT NULL
- Update monitoring to alert on missing user_id

## References

- **Spec:** `agent-os/specs/2025-10-26-phase-2-high-priority-security-reliability/spec.md`
- **Task:** P1-04 - Implement WebSocket Authentication
- **Related:**
  - P1-03: Session Timeout & Management
  - P1-05: Role-Based Access Control (RBAC)

## Rollback Plan

If issues occur during Phase 2 implementation:

```python
# Temporarily re-enable demo fallback with feature flag
WEBSOCKET_AUTH_ENABLED = os.getenv('WEBSOCKET_AUTH_ENABLED', 'false').lower() == 'true'

if not WEBSOCKET_AUTH_ENABLED:
    # Use demo fallback
    user_id = user_id or "7b10ae4c-2158-46be-be91-18dec7d02767"
```

## Sign-off

- **Implementation:** Ready for Phase 2
- **Documentation:** ✅ Complete
- **Tests:** Pending Phase 2 implementation
- **Stakeholder Approval:** Required before production deployment
