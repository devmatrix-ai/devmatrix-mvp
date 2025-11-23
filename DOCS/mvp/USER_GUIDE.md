# DevMatrix User Guide: Learning Layer & ApplicationIR

This guide explains how to use the new **Learning Layer** and **ApplicationIR** features in DevMatrix.

## 1. ApplicationIR (The "Brain")

The **ApplicationIR** is the central data model for your application. It is automatically constructed from your requirements.

### How it works
1.  You provide a text prompt or spec file.
2.  DevMatrix parses it into `SpecRequirements`.
3.  The `IRBuilder` converts it into a structured `ApplicationIR` object.
4.  This IR is used to guide the LLM, ensuring all entities and endpoints are generated exactly as defined.

### How to verify
When running a generation, look for this log line:
```
INFO: ApplicationIR constructed: MyAppName (ID: ...)
```
You can also inspect the generated code to see that it matches the structure defined in `DOCS/APPLICATION_IR.md`.

## 2. Learning Layer (The "Memory")

The Learning Layer allows DevMatrix to learn from its mistakes and successes.

### 2.1 Error Recording
-   **What it does**: Automatically records timeouts, syntax errors, and empty responses to Neo4j.
-   **How to use**: No action needed. It runs automatically during generation.
-   **Benefit**: If a generation fails, the system remembers the error pattern and avoids it in future retries.

### 2.2 Pattern Promotion (Auto-Learning)
-   **What it does**: If code is generated successfully and passes validation, it is promoted to the `PatternBank`.
-   **Configuration**:
    -   `enable_auto_promotion=True` (Default: Enabled)
    -   Requires `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` in `.env` for Dual Validation.
-   **Dual Validation**:
    -   Before promotion, code is reviewed by **Claude 3 Sonnet** and **GPT-4 Turbo**.
    -   Both must score it ≥ 0.8/1.0 for it to be promoted.
    -   If keys are missing, it falls back to "Mock Mode" (for testing).

### 2.3 Unified RAG Retrieval
-   **What it does**: Before generating code, it searches Neo4j and Qdrant for similar past examples.
-   **How to use**: Ensure your Qdrant and Neo4j containers are running.
-   **Benefit**: The LLM sees "few-shot" examples of successful code, improving quality and consistency.

## 3. Troubleshooting

### "ApplicationIR construction failed"
-   Check your input spec format. Ensure entities are clearly defined.
-   See `src/parsing/spec_parser.py` for supported formats.

### "Dual Validation failed"
-   Check your `.env` file for valid API keys.
-   Check logs for specific validation errors (e.g., "Security vulnerability detected").

### "Neo4j/Qdrant connection refused"
-   Ensure Docker containers are running:
    ```bash
    docker-compose up -d neo4j qdrant
    ```
