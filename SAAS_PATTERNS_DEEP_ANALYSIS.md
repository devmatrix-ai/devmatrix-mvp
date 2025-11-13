# SaaS Patterns - Deep Analysis Across Task Manager, CRM, E-commerce

**Analysis Depth**: Ultrathink - From Public Interface to Internal Architecture
**Focus**: Common patterns that MUST exist in all 3 apps

---

## 1. PUBLIC INTERFACE PATTERNS (What Users See)

### 1.1 Navigation & Information Architecture

**SHARED ACROSS ALL 3:**

```
Layout Pattern:
├── Header
│   ├── Logo + Brand
│   ├── Search/Quick Access
│   ├── User Profile Menu
│   │   ├── Settings
│   │   ├── Preferences
│   │   └── Logout
│   └── Notifications Bell
├── Sidebar (Left Navigation)
│   ├── Main Entities (collection list)
│   ├── Analytics/Dashboard
│   ├── Settings
│   └── Help/Support
└── Main Content Area
    ├── List View / Grid View Toggle
    ├── Filters + Search
    ├── Bulk Actions
    └── Individual Item View

Modal Patterns:
├── Create New Item
├── Edit Item
├── Delete Confirmation
├── Advanced Filters
└── Settings/Preferences
```

**Why**: Users expect consistency. A Task, Contact, or Product look similar in structure.

**Variations**:
- Task Manager: Linear timeline view (today → overdue)
- CRM: Kanban board (pipeline visualization)
- E-commerce: Grid gallery (product images matter)

### 1.2 Data Representation Patterns

**SHARED**: Every app shows tabular data with:
```
Table Row = Entity Instance
├── Unique Identifier (ID, Name, SKU)
├── Primary Status Field
│   ├── Task: status (todo/in_progress/done)
│   ├── CRM: deal_stage (lead/qualified/proposal/won)
│   ├── E-commerce: order_status (pending/confirmed/shipped/delivered)
├── Secondary Metadata
│   ├── Task: assignee, due_date, priority
│   ├── CRM: contact_name, company, value
│   ├── E-commerce: customer_name, total, date
├── Timestamps
│   ├── created_at
│   ├── updated_at
│   └── status_changed_at
├── Quick Actions (Edit, Delete, View)
└── Bulk Select Checkbox
```

**Why**: Standard CRUD pattern - all SaaS apps MUST show entities this way.

### 1.3 Filtering & Search Patterns

**EXACT SAME REQUIREMENTS:**

```
Search/Filter Bar:
├── Full-Text Search
│   ├── Searches: name, description, notes
│   └── Substring match (case-insensitive)
├── Faceted Filters (Left Sidebar)
│   ├── Filter by Status (Dropdown)
│   ├── Filter by Owner/Assignee (Multi-select)
│   ├── Filter by Priority (Checkboxes)
│   ├── Filter by Date Range (Date picker)
│   └── Filter by Custom Tags
├── Saved Filter Sets
│   └── "My Open Tasks", "Won Deals", "Pending Orders"
└── Clear All Filters
```

**Database Requirement**: All entities MUST have:
- `name` (indexed, full-text searchable)
- `status` (indexed, filterable)
- `created_at` (indexed, date-range filterable)
- `owner_id` or `user_id` (indexed)
- `tags` or `categories` (indexed array/relationship)

### 1.4 Bulk Operations Pattern

**IDENTICAL ACROSS ALL 3:**

```
User selects multiple items (checkboxes):
├── Select All / Deselect All buttons
├── Bulk Actions Menu appears:
│   ├── Change Status (Task → done, Deal → won, Order → shipped)
│   ├── Assign To (change owner)
│   ├── Add Tags
│   ├── Move To (folder/category)
│   ├── Export (CSV)
│   ├── Delete (with confirmation)
│   └── Archive (soft delete)
└── Selection count badge
```

**Backend Requirement**:
- All entities need `user_id` (ownership)
- All entities need `status` (state change)
- All entities need `tags` or `categories` (grouping)
- Bulk update endpoint: `PATCH /entities` with `ids: []`

### 1.5 Timeline & History Pattern

**UNIVERSAL REQUIREMENT:**

```
Every entity has Activity/History Tab:
├── Created: "John created this" (timestamp)
├── Status Changes
│   ├── "Task moved to In Progress" (who, when)
│   ├── "Deal progressed to Proposal stage" (who, when)
│   └── "Order shipped to address" (who, when)
├── Owner/Assignee Changes
│   └── "Reassigned to Jane" (who, when)
├── Field Changes
│   └── "Priority changed from Low to High" (who, when)
├── Comments/Notes
│   ├── User avatar + name
│   ├── Timestamp (relative: "2 hours ago")
│   ├── Comment text
│   └── Edit/Delete options (own comments only)
├── Attachments/Files
│   └── Document added, link added, screenshot added
└── Mentions/Notifications
    ├── @mention someone
    └── Notify them of activity
```

**Backend Requirements**:
- `activity_logs` table (user_id, entity_type, entity_id, action, before, after, timestamp)
- `comments` table (entity_type, entity_id, user_id, text, mentions, timestamp)
- `attachments` table (entity_type, entity_id, file_url, uploaded_by, timestamp)

---

## 2. INFORMATION ARCHITECTURE PATTERNS (Data Relationships)

### 2.1 Ownership & Multi-tenancy

**REQUIRED IN ALL 3:**

```
Data Hierarchy:
┌─ Organization/Team (workspace)
│  ├─ User (team member) - can have multiple roles
│  │  ├─ Role: Admin, Editor, Viewer
│  │  └── Permissions: create, edit, delete, export, admin
│  │
│  └─ Entity Collection
│     ├─ Task (owned by user, in project)
│     ├─ Contact (owned by user, in company)
│     └─ Order (belongs to customer account)
│
└─ Each entity is scoped to organization
   └── Enforce: WHERE organization_id = current_user.organization_id
```

**Database Reality**:
```sql
-- All entities have these columns:
- id (UUID)
- organization_id (who owns the data - CRITICAL)
- workspace_id (optional - for teams)
- user_id (who created/owns it)
- created_at
- updated_at
- is_deleted (soft delete)

-- All queries include:
SELECT * FROM tasks
WHERE organization_id = ?
  AND is_deleted = false
```

### 2.2 Entity Relationships Pattern

**Task Manager**:
```
User (1) ──→ (N) Task
     ↓
   (1)
     ├─────→ Project (1) ──→ (N) Task
     ├─────→ Team (N) ──→ (N) User
     └─────→ Label (N)
```

**CRM**:
```
User (1) ──→ (N) Contact
     ↓
   (1)
     ├─────→ Company (1) ──→ (N) Contact
     ├─────→ Deal (N) ──→ Contact (N)
     ├─────→ Activity (N) ──→ Contact
     └─────→ Pipeline (defines deal stages)
```

**E-commerce**:
```
User (Customer) ──→ (N) Order
                  ↓
              Product (N) ──→ (N) Order (via OrderItem)
                  ↓
              Category (1) ──→ (N) Product
                  ↓
              Inventory (1) ──→ (1) Product
```

**COMMON PATTERN**: Tree/Graph Structure
- Every entity connects to Users
- Every entity has parent/container (Project/Company/Category)
- Every entity can link to multiple other entities (Tags/Labels)

---

## 3. STATE & WORKFLOW PATTERNS

### 3.1 Status/State Machine

**Task Manager**:
```
┌─────────────────────────────────────┐
│         TASK LIFECYCLE              │
├─────────────────────────────────────┤
│ todo ──→ in_progress ──→ done      │
│   ↑                         ↓        │
│   └─────────────────────────┘       │
│         (can revert)                │
│ + cancelled (terminal)              │
└─────────────────────────────────────┘
```

**CRM**:
```
┌──────────────────────────────────┐
│      DEAL PIPELINE               │
├──────────────────────────────────┤
│ lead ──→ qualified ──→ proposal ──→ won
│  ↓           ↓           ↓          ↓
│  └─────────────────────────→ lost   │
│     (won/lost are terminal)        │
└──────────────────────────────────┘
```

**E-commerce**:
```
┌────────────────────────────────────┐
│      ORDER LIFECYCLE               │
├────────────────────────────────────┤
│ pending ──→ confirmed ──→ shipped ──→ delivered
│   ↓           ↓           ↓            ↓
│   └───────────────→ cancelled (terminal)
└────────────────────────────────────┘
```

**COMMON PATTERN**:
- Linear state machine (A → B → C)
- Some states can revert, some can't
- Terminal states (done, lost, cancelled, delivered)
- State change triggered by user action
- State change creates activity log entry
- State transitions may trigger notifications

### 3.2 Priority/Importance Levels

**ALL THREE NEED IT:**

```
Task: priority (Low, Medium, High, Urgent)
Deal: probability (0%, 25%, 50%, 75%, 100%)
Order: priority_level (Standard, Express, Overnight)

Common Implementation:
├── Affects sorting/filtering
├── Visual indicator (color coding)
├── Notification urgency
└── SLA tracking (how long to complete based on priority)
```

---

## 4. CRUD OPERATIONS PATTERN (Every app needs identical endpoints)

### 4.1 List Operations

```
GET /entities?
  page=1
  limit=20
  sort=created_at:desc
  filter[status]=active
  filter[owner_id]=user-123
  search=keyword

Response:
{
  data: [Entity, Entity, ...],
  total: 150,
  page: 1,
  pages: 8,
  hasNext: true,
  hasPrev: false
}
```

### 4.2 Create Operation

```
POST /entities
Body: {
  name: "...",
  description: "...",
  status: "default_value",
  owner_id: "current_user",
  parent_id: "project_id",
  tags: ["tag1", "tag2"],
  custom_fields: {...}
}

Validations:
├── Name: required, min 3 chars, max 255
├── Status: must be valid enum value
├── Owner: must be current_user or someone in org
├── Parent: must exist in org
└── Custom fields: type validation

Side Effects:
├── Create activity log entry
├── Send notification if assigned to someone
└── Update org's entity count
```

### 4.3 Update Operation

```
PUT/PATCH /entities/:id
Body: {...same as create...}

Validations:
├── Entity exists
├── User has edit permission (owner or admin)
└── Status transition is valid (not skip states)

Side Effects:
├── Track what changed (before/after)
├── Create activity log entry ("Changed status from X to Y")
├── Send notifications ("You were assigned to...")
└── Update related counts
```

### 4.4 Delete Operation

```
DELETE /entities/:id

Real Behavior:
├── Update is_deleted = true (soft delete)
├── Set deleted_at timestamp
├── Log the deletion
├── Don't cascade delete (keep history)
├── Remove from search index

Hard Delete (rare):
└── Only for data privacy (GDPR right to be forgotten)
```

---

## 5. AUTHENTICATION & AUTHORIZATION PATTERN

### 5.1 Authentication Layer

**ALL THREE NEED**:

```
Login Flow:
├── Email + Password
├── Validate credentials
├── Issue JWT token (access + refresh)
├── Store refresh token in secure cookie
├── Return user profile

Protected Routes:
├── Verify JWT in Authorization header
├── Decode token → get user_id
├── Verify token not expired
├── Load user + organization
└── Attach to request context

Refresh Token:
├── POST /auth/refresh
├── Validate refresh token cookie
├── Issue new access token
└── Keep user logged in seamlessly
```

### 5.2 Authorization Layer

**Row-Level Security (Critical for SaaS)**:

```
Every query must include:
WHERE organization_id = current_user.org_id

Permission Matrix:
┌──────────────────────────────────────┐
│ Role    │ Create │ Edit │ Delete │   │
├──────────────────────────────────────┤
│ Owner   │   ✓    │  ✓   │   ✓    │   │
│ Admin   │   ✓    │  ✓   │   ✓    │   │
│ Editor  │   ✓    │  ✓*  │   ✗    │*own only
│ Viewer  │   ✗    │  ✗   │   ✗    │   │
└──────────────────────────────────────┘

Ownership Rules:
├── Can edit own items always
├── Can edit others' items if Editor+ role
└── Can delete only if Owner/Admin role
```

---

## 6. REAL-TIME PATTERNS

### 6.1 Updates Notification

**ALL THREE NEED**:

```
When someone updates entity:
├── WebSocket broadcast to org channel
├── Subscribed clients receive:
│   ├── Entity updated
│   ├── Who updated it
│   ├── What changed
│   └── Timestamp
├── Client updates local state
├── UI refreshes optimistically
└── Conflict resolution if simultaneous edits

Typing Indicators:
├── "Jane is editing this task"
├── Prevents conflicts
└── Real-time presence

Collaboration:
├── Multiple users in same item
├── See each other's cursors (optional)
├── Lock entity if someone's editing (optional)
```

---

## 7. DATA VALIDATION PATTERNS

### 7.1 Client-Side Validation

```
Same for all 3:
├── Required fields
├── String length (min/max)
├── Email format
├── Date is valid
├── Enum is valid value
├── File upload (size, type)
└── Custom business rules
```

### 7.2 Server-Side Validation (Critical)

```
ALWAYS on server:
├── Validate all inputs again
├── Check organization_id matches
├── Verify user has permission
├── Check data constraints
├── Validate state transitions
├── Prevent double-submit
└── Rate limiting
```

---

## 8. ERROR HANDLING PATTERN

**IDENTICAL ACROSS ALL 3:**

```
Error Response Format:
{
  error: {
    code: "VALIDATION_ERROR",
    message: "User-friendly message",
    details: {
      field: "name",
      error: "Name must be at least 3 characters"
    }
  },
  timestamp: "2025-11-12T...",
  request_id: "req-123"
}

Status Codes:
├── 400: Validation error
├── 401: Not authenticated
├── 403: Not authorized
├── 404: Not found
├── 409: Conflict (state transition invalid)
├── 429: Rate limited
└── 500: Server error
```

---

## 9. PERFORMANCE PATTERNS

### 9.1 Pagination

```
ALL apps must support:
├── Limit (10, 20, 50, 100)
├── Offset
├── Cursor-based (for infinite scroll)
├── Total count
└── Has_next, has_prev flags
```

### 9.2 Caching

```
Frontend:
├── Cache list views (invalidate on create/update/delete)
├── Cache entity detail
├── Stale-while-revalidate (5 min)

Backend:
├── Cache user permissions (5 min)
├── Cache organization settings (10 min)
├── Cache select lists (categories, tags)
└── Invalidate on changes
```

### 9.3 Indexing (Database)

```
CRITICAL indexes (ALL 3 apps need):
├── (organization_id, is_deleted)
├── (organization_id, status)
├── (organization_id, user_id)
├── (organization_id, created_at)
├── (organization_id, updated_at)
├── Full-text index on (name, description)
└── (organization_id, parent_id) for hierarchies
```

---

## 10. NOTIFICATIONS PATTERN

### 10.1 In-App Notifications

```
Types:
├── Assignment: "You were assigned to Task X"
├── Mention: "@John mentioned you"
├── Update: "Task X status changed to Done"
├── Reminder: "Task due tomorrow"
└── System: "Organization limit reached"

Delivery:
├── Real-time (WebSocket)
├── Unread count badge
├── Notification center/inbox
├── Mark as read/unread
└── Delete notification
```

### 10.2 Email Notifications

```
Same triggers for all 3:
├── Assignment
├── Mention
├── High-priority updates
├── Daily digest (optional)
└── Weekly summary

User Preference:
├── Enable/disable by type
├── Email frequency (immediate, daily, weekly, off)
└── Quiet hours
```

---

## 11. EXPORT/REPORTING PATTERNS

### 11.1 CSV Export

```
ALL THREE NEED:
├── Export filtered/sorted view
├── Select columns
├── Encoding (UTF-8)
├── Proper formatting
│   ├── Dates: ISO-8601
│   ├── Booleans: true/false
│   ├── JSON fields: flattened
│   └── Related entities: ID or name
├── Large export (async job, email download link)
└── Rate limiting (max 10K rows per request)
```

### 11.2 Analytics Dashboard

```
Common Metrics:
├── Count of items by status
├── Trend over time (7d, 30d, 90d)
├── Items per user (who's most active)
├── Average time in each status
├── Items created/closed per period
└── Activity heatmap (when most active)
```

---

## CONCLUSION: WHAT ALL 3 APPS REALLY SHARE

### Core Infrastructure (100% Identical)

```
┌─────────────────────────────────────────┐
│        SHARED INFRASTRUCTURE            │
├─────────────────────────────────────────┤
│ 1. Authentication & Authorization       │
│ 2. Multi-tenancy (organization_id)      │
│ 3. CRUD Operations (list/create/...)    │
│ 4. Pagination & Filtering               │
│ 5. Full-text Search                     │
│ 6. Activity Logging & History           │
│ 7. Comments/Notes                       │
│ 8. File Attachments                     │
│ 9. Bulk Operations                      │
│ 10. User Permissions                    │
│ 11. Real-time Updates (WebSocket)       │
│ 12. Notifications (in-app + email)      │
│ 13. Error Handling                      │
│ 14. Validation (client + server)        │
│ 15. Caching Strategy                    │
│ 16. CSV Export                          │
│ 17. Soft Delete (is_deleted flag)       │
│ 18. Timestamps (created/updated/deleted)│
│ 19. Rate Limiting                       │
│ 20. Request Logging                     │
└─────────────────────────────────────────┘
```

### Core Data Model (Same Structure)

```
┌─────────────────────────────────────────┐
│        EVERY ENTITY HAS:                │
├─────────────────────────────────────────┤
│ id (UUID, primary key)                  │
│ name (string, indexed, searchable)      │
│ description (text, optional)            │
│ status (enum, indexed, state machine)   │
│ priority/importance (enum)              │
│ owner_id (UUID, foreign key to User)    │
│ organization_id (UUID, row-level sec)   │
│ parent_id (UUID, for hierarchy)         │
│ tags (array/relationship, indexed)      │
│ created_at (timestamp, indexed)         │
│ updated_at (timestamp)                  │
│ is_deleted (boolean, soft delete)       │
│ custom_fields (JSON, flexible)          │
└─────────────────────────────────────────┘
```

### What VARIES Between Apps

```
Task Manager:
  └─ Linear workflow (todo → in_progress → done)
  └─ Time-based (due dates, schedules)
  └─ Project/Sprint organization

CRM:
  └─ Pipeline workflow (kanban view)
  └─ Multi-step sales process
  └─ Relationship tracking (contact ↔ company ↔ deal)

E-commerce:
  └─ Transactional workflow (order fulfillment)
  └─ Inventory management
  └─ Payment processing
```

---

## THE REAL BOILERPLATE COMPONENTS

**These are what should be in the graph:**

### Universal Components (Used by ALL 3)

```
1. Authentication Module
   ├── JWT token management
   ├── Login/logout/refresh
   ├── Password hashing (bcrypt)
   └── Email verification (optional)

2. Authorization Module
   ├── Role-based access control
   ├── Organization scoping (WHERE org_id = ?)
   ├── Permission checks
   └── Row-level security

3. Entity Base Service
   ├── CRUD operations (create, read, update, delete)
   ├── List with pagination
   ├── Search and filter
   ├── Bulk operations
   └── Soft delete handling

4. Activity Logging
   ├── Log all changes (before/after)
   ├── Track who changed what when
   ├── Timeline view
   └── Queryable history

5. Comments/Notes System
   ├── Add comments to any entity
   ├── Mentions (@user)
   ├── Edit/delete own comments
   └── Real-time updates

6. File Attachments
   ├── Upload to entity
   ├── Store metadata (uploaded_by, timestamp)
   ├── Delete files
   └── File integrity checks

7. Notifications Engine
   ├── In-app notifications
   ├── Email notifications
   ├── Notification preferences
   ├── Real-time delivery (WebSocket)
   └── Notification history

8. Real-time Updates
   ├── WebSocket connection management
   ├── Broadcast entity changes
   ├── Presence indicators
   └── Conflict resolution

9. Validation Framework
   ├── Input validation schemas
   ├── Custom validators
   ├── Error message formatting
   └── Client + server validation

10. Error Handling
    ├── Exception types
    ├── Error response formatting
    ├── Logging
    └── Error tracking (Sentry integration optional)

11. Caching Layer
    ├── Redis cache
    ├── Cache invalidation
    ├── TTL management
    └── Stale-while-revalidate

12. Bulk Operations Handler
    ├── Bulk update
    ├── Bulk delete
    ├── Bulk status change
    └── Transactional safety

13. Search & Filtering
    ├── Full-text search
    ├── Faceted filtering
    ├── Saved filter sets
    └── Search indexing

14. Export System
    ├── CSV generation
    ├── Large file handling (async jobs)
    ├── Column selection
    └── Format handling
```

### App-Specific Components

```
Task Manager:
  ├── Task State Machine (todo → in_progress → done)
  ├── Priority Levels
  ├── Due Date Management
  ├── Assignee Assignment
  └── Project/Sprint Grouping

CRM:
  ├── Deal Pipeline Management
  ├── Contact Management
  ├── Company Hierarchy
  ├── Lead Scoring
  └── Activity Tracking (calls, emails)

E-commerce:
  ├── Product Catalog
  ├── Shopping Cart
  ├── Order Management
  ├── Inventory Tracking
  ├── Payment Processing (Stripe integration)
  └── Shipping Integration
```

---

**This is what should go in the Neo4j graph.**
