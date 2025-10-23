# Alembic Migrations - DevMatrix MVP

## Overview

This directory contains Alembic database migrations for the DevMatrix MVP project. Alembic is used to manage database schema changes in a version-controlled, reproducible manner.

## Migration Order

The migrations must be applied in the following order (handled automatically by Alembic):

1. **20251020_1548_bcacf97a17b8** - Add masterplan schema with discovery documents
2. **20251022_1003_93ad2d77767b** - Add users table for authentication
3. **20251022_1346_extend_users_table** - Extend users table with email verification and password reset
4. **20251022_1347_create_user_quotas** - Create user_quotas table
5. **20251022_1348_create_user_usage** - Create user_usage table
6. **20251022_1349_create_conversations_messages** - Create conversations and messages tables
7. **20251022_1350_masterplans_user_id_fk** - Modify masterplans.user_id to UUID FK
8. **20251022_1351_discovery_documents_user_id_fk** - Modify discovery_documents.user_id to UUID FK

## Running Migrations

### Apply All Pending Migrations

To upgrade your database to the latest version:

```bash
alembic upgrade head
```

### Apply Migrations One at a Time

To apply migrations incrementally:

```bash
# Apply next migration
alembic upgrade +1

# Apply specific migration
alembic upgrade <revision_id>
```

### Check Current Migration Status

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

## Rollback Procedures

### Rollback Last Migration

To rollback the most recent migration:

```bash
alembic downgrade -1
```

### Rollback to Specific Version

```bash
alembic downgrade <revision_id>
```

### Rollback All Migrations

To completely reset the database:

```bash
alembic downgrade base
```

**WARNING:** This will drop all tables and data!

## Creating New Migrations

### Auto-generate Migration from Model Changes

When you modify SQLAlchemy models, generate a migration automatically:

```bash
alembic revision --autogenerate -m "descriptive message"
```

**Important:** Always review auto-generated migrations before applying them!

### Create Empty Migration

To create a custom migration manually:

```bash
alembic revision -m "descriptive message"
```

## Migration Documentation

### Phase 6: Authentication & Multi-tenancy Migrations (Task Group 1.2)

#### Migration 1: Extend Users Table (20251022_1346)

**Purpose:** Add email verification and password reset functionality to users table

**Changes:**
- Add `is_verified` (Boolean, default true)
- Add `verification_token` (UUID, nullable)
- Add `verification_token_created_at` (DateTime, nullable)
- Add `password_reset_token` (UUID, nullable)
- Add `password_reset_expires` (DateTime, nullable)
- Create indexes: `idx_verification_token`, `idx_password_reset_token`

**Rollback:** Removes all added columns and indexes

---

#### Migration 2: Create User Quotas Table (20251022_1347)

**Purpose:** Store per-user quota limits for LLM tokens, masterplans, storage, and API calls

**Changes:**
- Create `user_quotas` table with columns:
  - `quota_id` (UUID PK)
  - `user_id` (UUID FK to users, unique)
  - `llm_tokens_monthly_limit` (Integer, nullable)
  - `masterplans_limit` (Integer, nullable)
  - `storage_bytes_limit` (BigInteger, nullable)
  - `api_calls_per_minute` (Integer, default 30)
- Add FK constraint: `user_id` → `users.user_id` (ON DELETE CASCADE)
- Add unique constraint: `uq_user_quotas_user_id`
- Create index: `ix_user_quotas_user_id`

**Rollback:** Drops the entire `user_quotas` table

---

#### Migration 3: Create User Usage Table (20251022_1348)

**Purpose:** Track monthly usage metrics per user for billing and quota enforcement

**Changes:**
- Create `user_usage` table with columns:
  - `usage_id` (UUID PK)
  - `user_id` (UUID FK to users)
  - `month` (Date - first day of month)
  - `llm_tokens_used` (Integer, default 0)
  - `llm_cost_usd` (Numeric(10,4), default 0.0)
  - `masterplans_created` (Integer, default 0)
  - `storage_bytes` (BigInteger, default 0)
  - `api_calls` (Integer, default 0)
- Add FK constraint: `user_id` → `users.user_id` (ON DELETE CASCADE)
- Add unique constraint: `uq_user_usage_user_month` on (user_id, month)
- Create compound index: `idx_user_usage_user_month` on (user_id, month)

**Rollback:** Drops the entire `user_usage` table

---

#### Migration 4: Create Conversations & Messages Tables (20251022_1349)

**Purpose:** Store user chat conversations and messages for multi-tenancy support

**Changes:**
- Create `conversations` table:
  - `conversation_id` (UUID PK)
  - `user_id` (UUID FK to users)
  - `title` (String(300), nullable)
  - `created_at` (DateTime, default now())
  - `updated_at` (DateTime, default now())
  - FK: `user_id` → `users.user_id` (ON DELETE CASCADE)
  - Indexes: `idx_conversations_user_id`, `idx_conversations_created_at`

- Create `messages` table:
  - `message_id` (UUID PK)
  - `conversation_id` (UUID FK to conversations)
  - `role` (String(20) - user/assistant/system)
  - `content` (Text)
  - `created_at` (DateTime, default now())
  - FK: `conversation_id` → `conversations.conversation_id` (ON DELETE CASCADE)
  - Index: `idx_messages_conversation_id`

**Rollback:** Drops both tables (messages first, then conversations)

---

#### Migration 5: Masterplans User ID FK (20251022_1350)

**Purpose:** Enforce referential integrity between masterplans and users

**Changes:**
- Convert `masterplans.user_id` from String(100) to UUID
- Add FK constraint: `user_id` → `users.user_id` (ON DELETE CASCADE)
- Recreate index: `idx_masterplan_user`

**CAUTION:** This is a **BREAKING MIGRATION**
- Uses `CAST` to convert String to UUID (`user_id::uuid`)
- Will fail if existing `user_id` values are not valid UUIDs
- Recommended: Start with fresh database or clean data first

**Rollback:** Reverts column to String(100), drops FK constraint

---

#### Migration 6: Discovery Documents User ID FK (20251022_1351)

**Purpose:** Enforce referential integrity between discovery_documents and users

**Changes:**
- Convert `discovery_documents.user_id` from String(100) to UUID
- Add FK constraint: `user_id` → `users.user_id` (ON DELETE CASCADE)
- Recreate index: `idx_discovery_user`

**CAUTION:** This is a **BREAKING MIGRATION**
- Uses `CAST` to convert String to UUID (`user_id::uuid`)
- Will fail if existing `user_id` values are not valid UUIDs
- Recommended: Start with fresh database or clean data first

**Rollback:** Reverts column to String(100), drops FK constraint

---

## Important Notes

### Breaking Migrations (5 & 6)

Migrations 5 and 6 modify existing columns from String to UUID. These are **breaking changes** if you have existing data with non-UUID `user_id` values.

**Options:**

1. **Fresh Start (Recommended for Development):**
   ```bash
   # Drop all tables
   alembic downgrade base

   # Apply all migrations
   alembic upgrade head
   ```

2. **Data Migration (Production):**
   Before running migrations 5 & 6:
   ```sql
   -- Ensure all user_id values are valid UUIDs
   -- Update or delete rows with invalid user_id values

   -- Example: Delete rows with invalid UUIDs
   DELETE FROM masterplans WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
   DELETE FROM discovery_documents WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
   ```

### Foreign Key Cascades

All foreign key constraints use `ON DELETE CASCADE` to ensure:
- When a user is deleted, all their data is automatically deleted
- Maintains referential integrity
- Prevents orphaned records

**Tables with CASCADE deletes:**
- `user_quotas` → deletes when user deleted
- `user_usage` → deletes when user deleted
- `conversations` → deletes when user deleted
- `messages` → deletes when conversation deleted
- `masterplans` → deletes when user deleted
- `discovery_documents` → deletes when user deleted

### Testing Migrations

Always test migrations on a development/staging database before production:

```bash
# 1. Backup production database
pg_dump devmatrix_prod > backup.sql

# 2. Create test database
createdb devmatrix_test

# 3. Restore backup to test database
psql devmatrix_test < backup.sql

# 4. Test migrations on test database
DATABASE_URL=postgresql://user:pass@localhost/devmatrix_test alembic upgrade head

# 5. Test rollback
DATABASE_URL=postgresql://user:pass@localhost/devmatrix_test alembic downgrade -1
```

## Verifying Migrations

After running migrations, verify the schema:

```bash
# Connect to database
psql devmatrix_mvp

# List all tables
\dt

# Describe users table
\d users

# Describe user_quotas table
\d user_quotas

# Describe user_usage table
\d user_usage

# Check foreign keys
\d+ masterplans
\d+ discovery_documents

# Check indexes
\di
```

## Troubleshooting

### Migration Fails with "column already exists"

This usually happens when:
1. You ran the migration partially before
2. Database is out of sync with Alembic version

**Solution:**
```bash
# Mark migration as applied without running it
alembic stamp <revision_id>
```

### Migration Fails with "invalid UUID"

For migrations 5 & 6, this means existing data has non-UUID `user_id` values.

**Solution:** Clean data before migration (see "Breaking Migrations" section above)

### Cannot Rollback Migration

If a rollback fails, manually fix the database and update Alembic version:

```bash
# Fix database manually using SQL
psql devmatrix_mvp

# Then update Alembic to correct version
alembic stamp <revision_id>
```

## Production Deployment Checklist

Before deploying migrations to production:

- [ ] Backup database (`pg_dump`)
- [ ] Test migrations on staging environment
- [ ] Test rollback on staging environment
- [ ] Verify all foreign keys and indexes created
- [ ] Review migration logs for errors
- [ ] Update application code to match new schema
- [ ] Monitor application after deployment
- [ ] Keep backup for 30 days

## Contact

For migration issues or questions, contact the database engineering team or refer to:
- Alembic Documentation: https://alembic.sqlalchemy.org/
- Phase 6 Spec: `/agent-os/specs/2025-10-22-authentication-multi-tenancy/spec.md`
- Tasks File: `/agent-os/specs/2025-10-22-authentication-multi-tenancy/tasks.md`
