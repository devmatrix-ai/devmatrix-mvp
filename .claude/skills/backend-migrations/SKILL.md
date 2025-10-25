---
name: Backend Migrations
description: Create and manage database schema migrations following best practices for versioning, reversibility, and zero-downtime deployments. Use this skill when creating or modifying database migration files, Alembic migrations, Django migrations, Rails migrations, or any schema change scripts. Use this skill when working with database schema evolution, implementing rollback strategies, managing indexes on large tables, or separating schema changes from data migrations. Use this skill when working with files in migrations/, db/migrate/, alembic/versions/, or similar migration directories. Use this skill when creating new tables, modifying columns, adding indexes, establishing foreign key relationships, or managing database versioning in development and production environments.
---

# Backend Migrations

This Skill provides Claude Code with specific guidance on how to adhere to coding standards as they relate to how it should handle backend migrations.

## When to use this skill:

- When creating or editing database migration files (e.g., `alembic/versions/*.py`, `db/migrate/*.rb`, `migrations/*.js`)
- When implementing schema changes such as creating tables, adding/modifying columns, or altering data types
- When adding or removing database indexes, foreign keys, or constraints
- When writing reversible migration scripts with proper up/down or upgrade/downgrade methods
- When separating schema migrations from data migrations for better rollback safety
- When managing migration dependencies and ordering in version control
- When implementing zero-downtime deployment strategies for database changes
- When working with Alembic, Django migrations, Rails migrations, Flyway, or similar migration tools

## Instructions

For details, refer to the information provided in this file:
[backend migrations](../../../agent-os/standards/backend/migrations.md)
