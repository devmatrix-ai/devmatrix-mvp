---
name: Global Error Handling
description: Implement robust error handling with user-friendly messages, specific exception types, centralized error handling, and graceful degradation strategies across the application. Use this skill when writing error handling logic in any code file, implementing try-catch blocks, raising or throwing exceptions, or designing error response formats. Use this skill when validating input and failing fast with clear messages, implementing retry strategies for transient failures, ensuring proper resource cleanup in finally blocks, or creating centralized error handling middleware. Use this skill when working with API endpoints, service layers, data access code, or any code that could fail and needs proper error handling. Use this skill when designing error responses for users or implementing graceful fallback behaviors.
---

# Global Error Handling

This Skill provides Claude Code with specific guidance on how to adhere to coding standards as they relate to how it should handle global error handling.

## When to use this skill:

- When writing or editing any code that needs error handling (try-catch blocks, error boundaries, etc.)
- When implementing API error responses with user-friendly messages
- When validating input and failing fast with clear, actionable error messages
- When using specific exception types rather than generic errors for better handling
- When implementing centralized error handling at API boundaries or application layers
- When designing graceful degradation for non-critical service failures
- When adding retry strategies with exponential backoff for transient failures
- When ensuring resource cleanup (file handles, database connections) in finally blocks
- When deciding what technical details to hide from users for security

## Instructions

For details, refer to the information provided in this file:
[global error handling](../../../agent-os/standards/global/error-handling.md)
