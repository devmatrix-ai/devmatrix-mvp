---
name: Testing Test Writing
description: Write strategic, minimal tests focusing on core user flows and critical paths, deferring edge cases and implementation details until dedicated testing phases. Use this skill when adding test files for features after implementation is complete, when writing unit tests for critical business logic, or when creating integration tests for primary user workflows. Use this skill when working with test files in tests/, __tests__/, specs/, or similar test directories. Use this skill when using testing frameworks like Jest, pytest, RSpec, or Vitest, when mocking external dependencies, or when deciding test coverage priorities. Use this skill when writing tests that focus on behavior rather than implementation details, keeping tests fast and maintainable.
---

# Testing Test Writing

This Skill provides Claude Code with specific guidance on how to adhere to coding standards as they relate to how it should handle testing test writing.

## When to use this skill:

- When creating or editing test files (e.g., `*.test.js`, `*.spec.ts`, `test_*.py`, `*_test.rb`)
- When writing minimal tests after completing feature implementation (not during intermediate steps)
- When testing core user flows and critical business paths exclusively
- When deciding which tests to write and which to defer to dedicated testing phases
- When mocking external dependencies like databases, APIs, or file systems
- When writing tests that focus on behavior and outcomes rather than implementation
- When using testing frameworks (Jest, pytest, RSpec, Vitest, Mocha, etc.)
- When ensuring tests run fast (milliseconds for unit tests) for frequent execution
- When using clear, descriptive test names that explain expected behavior
- When avoiding tests for non-critical utilities and edge cases during feature development

## Instructions

For details, refer to the information provided in this file:
[testing test writing](../../../agent-os/standards/testing/test-writing.md)
