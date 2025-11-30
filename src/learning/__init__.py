"""
Learning Module - Generation Feedback Loop System.

Closes the gap between smoke test failures and code generation improvement.
Instead of just learning to repair, the system learns to PREVENT errors.

Components:
- NegativePatternStore: Persists anti-patterns to Neo4j
- SmokeFeedbackClassifier: Maps smoke errors to IR context
- PromptEnhancer: Injects anti-patterns into generation prompts
- FeedbackCollector: Orchestrates the feedback loop

Reference: DOCS/mvp/exit/learning/GENERATION_FEEDBACK_LOOP.md

Usage:
    # Process smoke failures
    from src.learning import process_smoke_feedback

    result = await process_smoke_feedback(
        smoke_result=validator.result,
        application_ir=application_ir
    )

    # Enhance generation prompts
    from src.learning import enhance_prompt

    enhanced = enhance_prompt(
        base_prompt="Generate endpoint",
        entity_name="Product"
    )
"""

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    NegativePatternStore,
    get_negative_pattern_store,
    create_anti_pattern,
)

from src.learning.smoke_feedback_classifier import (
    SmokeFeedbackClassifier,
    get_smoke_feedback_classifier,
    ErrorClassification,
    IRContext,
)

from src.learning.prompt_enhancer import (
    GenerationPromptEnhancer,
    get_prompt_enhancer,
    enhance_prompt,
)

from src.learning.feedback_collector import (
    GenerationFeedbackCollector,
    get_feedback_collector,
    FeedbackProcessingResult,
    FeedbackSessionStats,
    process_smoke_feedback,
    process_smoke_feedback_sync,
)

# Bug #161 Fix: Bridge from ErrorKnowledge to GenerationAntiPattern
from src.learning.error_knowledge_bridge import (
    ErrorKnowledgeBridge,
    BridgeResult,
    get_error_knowledge_bridge,
    bridge_smoke_error_to_pattern,
)

__all__ = [
    # Pattern Store
    "GenerationAntiPattern",
    "NegativePatternStore",
    "get_negative_pattern_store",
    "create_anti_pattern",
    # Classifier
    "SmokeFeedbackClassifier",
    "get_smoke_feedback_classifier",
    "ErrorClassification",
    "IRContext",
    # Prompt Enhancer
    "GenerationPromptEnhancer",
    "get_prompt_enhancer",
    "enhance_prompt",
    # Feedback Collector
    "GenerationFeedbackCollector",
    "get_feedback_collector",
    "FeedbackProcessingResult",
    "FeedbackSessionStats",
    "process_smoke_feedback",
    "process_smoke_feedback_sync",
    # Error Knowledge Bridge (Bug #161)
    "ErrorKnowledgeBridge",
    "BridgeResult",
    "get_error_knowledge_bridge",
    "bridge_smoke_error_to_pattern",
]
