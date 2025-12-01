"""
Anti-Pattern Advisor - Bug #168: Use stored anti-patterns to prevent code generation errors.

Queries NegativePatternStore before code generation and provides recommendations
to avoid known failure patterns.

Reference: DOCS/mvp/exit/RUNTIME_TUNING_PLAN.md Task 3
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    NegativePatternStore,
    get_negative_pattern_store,
)

logger = logging.getLogger(__name__)


@dataclass
class AntiPatternAdvice:
    """Advice based on stored anti-patterns."""
    
    entity_name: str
    endpoint_pattern: Optional[str] = None
    
    # Recommendations
    avoid_patterns: List[str] = field(default_factory=list)
    use_patterns: List[str] = field(default_factory=list)
    
    # Raw patterns for detailed analysis
    matched_patterns: List[GenerationAntiPattern] = field(default_factory=list)
    
    # Metrics
    high_risk_count: int = 0
    medium_risk_count: int = 0
    
    def has_advice(self) -> bool:
        """Check if there's any advice to provide."""
        return len(self.avoid_patterns) > 0 or len(self.use_patterns) > 0
    
    def to_prompt_injection(self) -> str:
        """Format advice for LLM prompt injection."""
        if not self.has_advice():
            return ""
        
        lines = [f"\n⚠️ KNOWN ISSUES FOR {self.entity_name}:"]
        
        if self.avoid_patterns:
            lines.append("\nAVOID these patterns (caused errors before):")
            for i, pattern in enumerate(self.avoid_patterns[:5], 1):
                lines.append(f"  {i}. {pattern}")
        
        if self.use_patterns:
            lines.append("\nUSE these patterns instead:")
            for i, pattern in enumerate(self.use_patterns[:5], 1):
                lines.append(f"  {i}. {pattern}")
        
        return "\n".join(lines)


class AntiPatternAdvisor:
    """
    Queries stored anti-patterns and provides generation advice.
    
    Integrates with code generation to prevent known failures:
    1. Before generating entity routes -> query entity-specific patterns
    2. Before generating services -> query error type patterns
    3. Inject recommendations into LLM prompts
    
    Flow:
        CodeGenerationService → AntiPatternAdvisor → NegativePatternStore
                             ↓
                      Advice injected into prompts
    """
    
    def __init__(self, store: Optional[NegativePatternStore] = None):
        """Initialize advisor with pattern store."""
        self.store = store or get_negative_pattern_store()
        self._cache: Dict[str, AntiPatternAdvice] = {}
    
    def get_advice_for_entity(
        self,
        entity_name: str,
        endpoint_method: Optional[str] = None,
        min_occurrences: int = 1,
    ) -> AntiPatternAdvice:
        """
        Get advice for generating code for an entity.
        
        Args:
            entity_name: Entity being generated (e.g., "Product", "Order")
            endpoint_method: Optional HTTP method filter (e.g., "POST", "PUT")
            min_occurrences: Minimum error occurrences to consider (default 1)
            
        Returns:
            AntiPatternAdvice with recommendations
        """
        cache_key = f"{entity_name}:{endpoint_method or 'all'}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        advice = AntiPatternAdvice(
            entity_name=entity_name,
            endpoint_pattern=endpoint_method,
        )
        
        try:
            # Query patterns for this entity
            patterns = self.store.get_patterns_for_entity(
                entity_name=entity_name,
                min_occurrences=min_occurrences,
            )
            
            # Filter by endpoint method if specified
            if endpoint_method:
                patterns = [
                    p for p in patterns
                    if endpoint_method.upper() in p.endpoint_pattern.upper()
                ]
            
            advice.matched_patterns = patterns
            
            # Process patterns into recommendations
            for pattern in patterns:
                # Classify risk level
                if pattern.severity_score >= 0.7 or pattern.occurrence_count >= 3:
                    advice.high_risk_count += 1
                else:
                    advice.medium_risk_count += 1
                
                # Extract avoid pattern
                if pattern.bad_code_snippet:
                    avoid_msg = self._format_avoid_pattern(pattern)
                    if avoid_msg and avoid_msg not in advice.avoid_patterns:
                        advice.avoid_patterns.append(avoid_msg)
                
                # Extract use pattern (correct code)
                if pattern.correct_code_snippet:
                    use_msg = self._format_use_pattern(pattern)
                    if use_msg and use_msg not in advice.use_patterns:
                        advice.use_patterns.append(use_msg)
            
            self._cache[cache_key] = advice
            
            if advice.has_advice():
                logger.debug(
                    f"AntiPatternAdvisor: {len(patterns)} patterns for {entity_name}, "
                    f"{advice.high_risk_count} high-risk"
                )
            
        except Exception as e:
            logger.warning(f"AntiPatternAdvisor: Failed to get patterns for {entity_name}: {e}")
        
        return advice
    
    def get_advice_for_error_type(
        self,
        error_type: str,
        min_occurrences: int = 2,
    ) -> AntiPatternAdvice:
        """
        Get advice for a specific error type.
        
        Args:
            error_type: Error type (e.g., "validation", "database", "import")
            min_occurrences: Minimum occurrences to consider
            
        Returns:
            AntiPatternAdvice with recommendations
        """
        cache_key = f"error:{error_type}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        advice = AntiPatternAdvice(
            entity_name="*",
            endpoint_pattern=error_type,
        )
        
        try:
            patterns = self.store.get_patterns_by_error_type(
                error_type=error_type,
                min_occurrences=min_occurrences,
            )
            
            advice.matched_patterns = patterns
            
            for pattern in patterns:
                if pattern.severity_score >= 0.7:
                    advice.high_risk_count += 1
                else:
                    advice.medium_risk_count += 1
                
                if pattern.bad_code_snippet:
                    avoid_msg = self._format_avoid_pattern(pattern)
                    if avoid_msg and avoid_msg not in advice.avoid_patterns:
                        advice.avoid_patterns.append(avoid_msg)
                
                if pattern.correct_code_snippet:
                    use_msg = self._format_use_pattern(pattern)
                    if use_msg and use_msg not in advice.use_patterns:
                        advice.use_patterns.append(use_msg)
            
            self._cache[cache_key] = advice
            
        except Exception as e:
            logger.warning(f"AntiPatternAdvisor: Failed to get patterns for error type {error_type}: {e}")
        
        return advice
    
    def get_route_generation_advice(
        self,
        entity_name: str,
        http_method: str,
        path_pattern: str,
    ) -> AntiPatternAdvice:
        """
        Get specific advice for route generation.
        
        Bug #168: Prevents common route generation errors:
        - 404 vs 422 confusion
        - Missing path parameters
        - Incorrect status codes
        
        Args:
            entity_name: Entity name
            http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path_pattern: Route path (e.g., "/{id}", "/{id}/checkout")
            
        Returns:
            AntiPatternAdvice for route generation
        """
        advice = self.get_advice_for_entity(entity_name, http_method)
        
        # Add route-specific advice based on common patterns
        method_upper = http_method.upper()
        
        # Check for ID-based routes that might have 404 issues
        if '{id}' in path_pattern or '{' in path_pattern:
            if method_upper in ['PUT', 'PATCH', 'DELETE']:
                # Bug #166 pattern - check existence before validation
                existence_advice = (
                    f"For {method_upper} {path_pattern}: "
                    "Check entity existence BEFORE validating request body "
                    "to return 404 instead of 422 for missing resources"
                )
                if existence_advice not in advice.use_patterns:
                    advice.use_patterns.insert(0, existence_advice)
        
        # Check for action endpoints (checkout, activate, etc.)
        action_keywords = ['checkout', 'activate', 'deactivate', 'cancel', 'pay', 'complete']
        for keyword in action_keywords:
            if keyword in path_pattern.lower():
                action_advice = (
                    f"For action endpoint /{keyword}: "
                    "Verify entity state preconditions before executing action"
                )
                if action_advice not in advice.use_patterns:
                    advice.use_patterns.append(action_advice)
                break
        
        return advice
    
    def _format_avoid_pattern(self, pattern: GenerationAntiPattern) -> str:
        """Format anti-pattern as human-readable avoid message."""
        msg_parts = []
        
        if pattern.exception_class:
            msg_parts.append(f"[{pattern.exception_class}]")
        
        if pattern.error_message_pattern:
            # Truncate long messages
            error_msg = pattern.error_message_pattern[:100]
            if len(pattern.error_message_pattern) > 100:
                error_msg += "..."
            msg_parts.append(error_msg)
        
        if pattern.bad_code_snippet:
            # Show first line of bad code
            first_line = pattern.bad_code_snippet.split('\n')[0].strip()
            if first_line:
                msg_parts.append(f"Example: `{first_line[:60]}`")
        
        return " - ".join(msg_parts) if msg_parts else ""
    
    def _format_use_pattern(self, pattern: GenerationAntiPattern) -> str:
        """Format correct pattern as human-readable use message."""
        if not pattern.correct_code_snippet:
            return ""
        
        # Show first meaningful line of correct code
        lines = [l.strip() for l in pattern.correct_code_snippet.split('\n') if l.strip()]
        if lines:
            first_line = lines[0][:80]
            return f"Use: `{first_line}`" + ("..." if len(lines[0]) > 80 else "")
        
        return ""
    
    def clear_cache(self):
        """Clear advice cache (call when patterns are updated)."""
        self._cache.clear()
        logger.debug("AntiPatternAdvisor: Cache cleared")


# Singleton instance
_advisor_instance: Optional[AntiPatternAdvisor] = None


def get_anti_pattern_advisor() -> AntiPatternAdvisor:
    """Get or create singleton AntiPatternAdvisor instance."""
    global _advisor_instance
    if _advisor_instance is None:
        _advisor_instance = AntiPatternAdvisor()
    return _advisor_instance

