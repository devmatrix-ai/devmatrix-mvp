# Gap Analysis: Implementation vs. Experimental Docs

This document compares the current implementation of the Learning Layer (Milestone 4) against the experimental documentation (`DOCS/experimental`).

## 1. Summary of Findings

| Component | Experimental Doc Status | Current Implementation Status | Gap Severity |
| :--- | :--- | :--- | :--- |
| **Pattern Promotion** | Fully defined (Pipeline, Dual Val, Auto-Promo) | ✅ **Fully Implemented** | None |
| **Error Pattern Loop** | Defined (Store, Analyzer, Feedback) | ✅ **Fully Implemented** | None |
| **Unified RAG** | Defined (Neo4j + Qdrant) | ✅ **Fully Implemented** | None |
| **ApplicationIR** | Core "Source of Truth" Model | ❌ **Not Implemented** | **High** |
| **RAG Feedback Loop** | `FeedbackService` for snippets | ⚠️ **Partial/Missing** | Medium |
| **DAG Sync** | Sync to Neo4j TaskGraph | ⚠️ **Mocked/Partial** | Low |

## 2. Detailed Gaps

### 2.1. ApplicationIR (The "Brain" Gap)
*   **Doc Reference**: `ApplicationIR_Complete_Design.md`
*   **Concept**: A unified, immutable Pydantic model (`ApplicationIR`) that acts as the single source of truth for the entire pipeline. It should drive generation, validation, and repair.
*   **Current State**: The system still relies on `SpecRequirements` and passing loose dictionaries/objects between phases. There is no central `ApplicationIR` object being transformed by "Phase Updaters".
*   **Impact**: While the Learning Layer works, it lacks the deep context that ApplicationIR would provide (e.g., linking an error not just to a "task" but to a specific "BehaviorModelIR" requirement).

### 2.2. RAG Feedback Learning Loop
*   **Doc Reference**: `07_Learning_Layer_and_Promotion.md` (Section 5)
*   **Concept**: A specific loop that indexes *snippets* of successful code (not just full patterns) into a `FeedbackService` for granular reuse.
*   **Current State**: We have `PatternFeedbackIntegration` for *patterns*, but we don't have a dedicated `FeedbackService` that extracts and indexes smaller snippets from every successful generation.
*   **Impact**: We miss out on learning from small, successful code fragments that aren't full patterns.

### 2.3. DAG Synchronization
*   **Doc Reference**: `07_Learning_Layer_and_Promotion.md` (Section 3.3, Step 5)
*   **Concept**: Updating the Neo4j `TaskGraph` with new pattern relationships after promotion.
*   **Current State**: The `sync_to_dag` method in `PatternFeedbackIntegration` exists but contains mock logic or TODOs for the actual Neo4j graph updates.
*   **Impact**: The Knowledge Graph doesn't immediately reflect newly promoted patterns, requiring a manual or scheduled re-indexing.

## 3. Recommendations

1.  **Prioritize ApplicationIR**: This is the most significant architectural gap. Implementing `ApplicationIR` will require a major refactor of the core pipeline (Phases 1-7) to use this model as the data backbone.
2.  **Implement FeedbackService**: Create the `rag/feedback_service.py` module to handle granular snippet learning, separate from the "Pattern Promotion" pipeline.
3.  **Flesh out DAG Sync**: Implement the actual Cypher queries in `sync_to_dag` to update Neo4j in real-time.
