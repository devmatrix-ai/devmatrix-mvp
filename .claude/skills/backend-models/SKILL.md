---
name: Backend Models
description: Define and structure database models with proper data types, relationships, constraints, and validation following ORM best practices. Use this skill when creating or modifying database model classes, ORM entities, schema definitions, or data model files. Use this skill when working with SQLAlchemy models, Django models, ActiveRecord models, Prisma schemas, TypeORM entities, or Sequelize models. Use this skill when defining table schemas, establishing relationships (one-to-many, many-to-many), implementing model validation, adding timestamps and soft deletes, or configuring cascade behaviors. Use this skill when working with files in models/, entities/, schemas/, or orm/ directories that define database table structures and business logic.
---

# Backend Models

This Skill provides Claude Code with specific guidance on how to adhere to coding standards as they relate to how it should handle backend models.

## When to use this skill:

- When creating or editing database model files (e.g., `models/*.py`, `models/*.js`, `entities/*.ts`, `schema.prisma`)
- When defining database table structures with appropriate data types and constraints
- When implementing model relationships (one-to-one, one-to-many, many-to-many) and foreign keys
- When adding validation rules at the model or database level
- When configuring timestamps (created_at, updated_at) and audit fields
- When setting up cascade behaviors for related records on delete or update
- When adding indexes to improve query performance on frequently accessed fields
- When working with SQLAlchemy, Django ORM, Prisma, TypeORM, ActiveRecord, or similar ORMs

## Instructions

For details, refer to the information provided in this file:
[backend models](../../../agent-os/standards/backend/models.md)
