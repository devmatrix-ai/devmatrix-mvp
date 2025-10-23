"""
LLM Integrations

Clients for various LLM providers with MVP enhancements:
- Multi-model support (Haiku/Sonnet/Opus)
- Anthropic's Prompt Caching (32% cost savings)
- Task-based model selection
"""

from .anthropic_client import AnthropicClient
from .enhanced_anthropic_client import EnhancedAnthropicClient
from .model_selector import ModelSelector, ClaudeModel, TaskType, TaskComplexity
from .prompt_cache_manager import PromptCacheManager, CacheableContext

__all__ = [
    # Primary MVP client
    "EnhancedAnthropicClient",

    # Supporting components
    "ModelSelector",
    "PromptCacheManager",
    "CacheableContext",

    # Enums
    "ClaudeModel",
    "TaskType",
    "TaskComplexity",

    # Legacy (backwards compatibility)
    "AnthropicClient"
]
