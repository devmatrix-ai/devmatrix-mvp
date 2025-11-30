"""
Cognitive Code Generation Service.

Wrapper service that integrates IR-Centric Cognitive Enhancement
into the code generation pipeline.

Features:
- Feature flag for enabling/disabling cognitive pass
- Baseline comparison mode for A/B testing
- Metrics collection for prevention rate tracking
- Graceful degradation on cognitive pass failures

Part of Bug #143-160 IR-Centric Cognitive Code Generation.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging
import os

# Local imports
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.cache.cognitive_cache import CognitiveCache
from src.cognitive.passes.ir_centric_cognitive_pass import (
    IRCentricCognitivePass,
    EnhancementResult,
)
from src.learning.negative_pattern_store import NegativePatternStore

logger = logging.getLogger(__name__)


@dataclass
class CognitiveGenerationMetrics:
    """
    Metrics for cognitive code generation.
    """
    # Counts
    total_files_processed: int = 0
    files_enhanced: int = 0
    files_unchanged: int = 0
    files_failed: int = 0

    # Enhancement metrics
    total_functions_processed: int = 0
    functions_enhanced: int = 0
    functions_rolled_back: int = 0

    # IR validation
    ir_validations_passed: int = 0
    ir_validations_failed: int = 0

    # Performance
    total_time_ms: float = 0.0
    total_tokens_used: int = 0
    cache_hits: int = 0

    # Baseline comparison (A/B testing)
    baseline_issues_detected: int = 0
    cognitive_issues_prevented: int = 0

    def get_prevention_rate(self) -> float:
        """Calculate the issue prevention rate."""
        total_potential = self.baseline_issues_detected + self.cognitive_issues_prevented
        if total_potential == 0:
            return 0.0
        return self.cognitive_issues_prevented / total_potential

    def get_enhancement_rate(self) -> float:
        """Calculate the enhancement success rate."""
        if self.total_functions_processed == 0:
            return 0.0
        return self.functions_enhanced / self.total_functions_processed

    def get_rollback_rate(self) -> float:
        """Calculate the rollback rate (lower is better)."""
        total_attempts = self.functions_enhanced + self.functions_rolled_back
        if total_attempts == 0:
            return 0.0
        return self.functions_rolled_back / total_attempts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files_processed": self.total_files_processed,
            "files_enhanced": self.files_enhanced,
            "files_unchanged": self.files_unchanged,
            "files_failed": self.files_failed,
            "total_functions_processed": self.total_functions_processed,
            "functions_enhanced": self.functions_enhanced,
            "functions_rolled_back": self.functions_rolled_back,
            "ir_validations_passed": self.ir_validations_passed,
            "ir_validations_failed": self.ir_validations_failed,
            "total_time_ms": self.total_time_ms,
            "total_tokens_used": self.total_tokens_used,
            "cache_hits": self.cache_hits,
            "baseline_issues_detected": self.baseline_issues_detected,
            "cognitive_issues_prevented": self.cognitive_issues_prevented,
            "prevention_rate": self.get_prevention_rate(),
            "enhancement_rate": self.get_enhancement_rate(),
            "rollback_rate": self.get_rollback_rate(),
        }


class CognitiveCodeGenerationService:
    """
    Service for cognitive code generation.

    This service wraps the IRCentricCognitivePass and provides:
    1. Feature flag control (ENABLE_COGNITIVE_PASS env var)
    2. Baseline comparison mode for A/B testing
    3. Metrics collection for monitoring
    4. Graceful degradation when cognitive pass fails

    Usage:
        service = CognitiveCodeGenerationService(ir, pattern_store)

        # Process single file
        result = await service.process_file(
            file_path="src/services/cart_service.py",
            content="...",
        )

        # Process multiple files
        results = await service.process_files(files)

        # Get metrics
        metrics = service.get_metrics()

    Configuration (environment variables):
        ENABLE_COGNITIVE_PASS: "true" to enable, "false" to disable (default: true)
        COGNITIVE_BASELINE_MODE: "true" for A/B testing (default: false)
        COGNITIVE_CACHE_TTL_HOURS: Cache TTL in hours (default: 24)
        COGNITIVE_MAX_PATTERNS: Max anti-patterns per flow (default: 5)
    """

    # Environment variable names
    ENV_ENABLE_COGNITIVE = "ENABLE_COGNITIVE_PASS"
    ENV_BASELINE_MODE = "COGNITIVE_BASELINE_MODE"
    ENV_CACHE_TTL = "COGNITIVE_CACHE_TTL_HOURS"
    ENV_MAX_PATTERNS = "COGNITIVE_MAX_PATTERNS"

    def __init__(
        self,
        ir: ApplicationIR,
        pattern_store: NegativePatternStore,
        llm_client: Optional[Any] = None,
        ir_validator: Optional[Any] = None,
        cache_storage_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the cognitive code generation service.

        Args:
            ir: Application IR with flows and contracts
            pattern_store: Store for anti-patterns
            llm_client: Optional LLM client for enhancement
            ir_validator: Optional IR compliance validator
            cache_storage_path: Path for persistent cache
            config: Additional configuration
        """
        self._ir = ir
        self._pattern_store = pattern_store
        self._llm_client = llm_client
        self._ir_validator = ir_validator
        self._config = config or {}

        # Load configuration from environment
        self._enabled = self._get_env_bool(self.ENV_ENABLE_COGNITIVE, True)
        self._baseline_mode = self._get_env_bool(self.ENV_BASELINE_MODE, False)
        self._cache_ttl = int(os.getenv(self.ENV_CACHE_TTL, "24"))
        self._max_patterns = int(os.getenv(self.ENV_MAX_PATTERNS, "5"))

        # Initialize cache
        self._cache = CognitiveCache(
            storage_path=cache_storage_path,
            ttl_hours=self._cache_ttl,
            cognitive_pass_version=IRCentricCognitivePass.VERSION,
        )

        # Initialize cognitive pass
        self._cognitive_pass = IRCentricCognitivePass(
            ir=ir,
            pattern_store=pattern_store,
            cache=self._cache,
            llm_client=llm_client,
            ir_validator=ir_validator,
            config={
                "max_patterns_per_flow": self._max_patterns,
                "enable_cache": True,
                **self._config,
            },
        )

        # Metrics
        self._metrics = CognitiveGenerationMetrics()
        self._file_results: List[EnhancementResult] = []

        logger.info(
            f"CognitiveCodeGenerationService initialized: "
            f"enabled={self._enabled}, baseline_mode={self._baseline_mode}"
        )

    @staticmethod
    def _get_env_bool(name: str, default: bool) -> bool:
        """Get boolean from environment variable."""
        value = os.getenv(name, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")

    def is_enabled(self) -> bool:
        """Check if cognitive pass is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable cognitive pass."""
        self._enabled = True
        logger.info("Cognitive pass enabled")

    def disable(self) -> None:
        """Disable cognitive pass."""
        self._enabled = False
        logger.info("Cognitive pass disabled")

    def set_baseline_mode(self, enabled: bool) -> None:
        """
        Enable/disable baseline comparison mode.

        In baseline mode, both cognitive and non-cognitive paths
        are evaluated for A/B testing.
        """
        self._baseline_mode = enabled
        logger.info(f"Baseline mode {'enabled' if enabled else 'disabled'}")

    async def process_file(
        self,
        file_path: str,
        content: str,
    ) -> EnhancementResult:
        """
        Process a single file through cognitive enhancement.

        Args:
            file_path: Path to the file
            content: Current content

        Returns:
            EnhancementResult with enhanced content
        """
        import time
        start_time = time.time()

        # If disabled, return unchanged
        if not self._enabled:
            return EnhancementResult(
                file_path=file_path,
                original_content=content,
                enhanced_content=content,
                success=True,
            )

        try:
            # Run cognitive pass
            result = await self._cognitive_pass.enhance_file(
                file_path=file_path,
                content=content,
            )

            # Update metrics
            self._update_metrics(result)
            self._file_results.append(result)

            # Baseline mode: compare with non-enhanced for A/B testing
            if self._baseline_mode:
                await self._compare_baseline(result)

            return result

        except Exception as e:
            logger.error(f"Cognitive processing failed for {file_path}: {e}")

            # Graceful degradation: return original
            return EnhancementResult(
                file_path=file_path,
                original_content=content,
                enhanced_content=content,
                success=False,
                errors=[str(e)],
            )

    async def process_files(
        self,
        files: List[Dict[str, str]],
    ) -> List[EnhancementResult]:
        """
        Process multiple files through cognitive enhancement.

        Args:
            files: List of dicts with 'path' and 'content'

        Returns:
            List of EnhancementResults
        """
        results = []
        for file_info in files:
            result = await self.process_file(
                file_path=file_info["path"],
                content=file_info["content"],
            )
            results.append(result)
        return results

    def _update_metrics(self, result: EnhancementResult) -> None:
        """Update metrics from enhancement result."""
        self._metrics.total_files_processed += 1

        if result.success:
            if result.fully_enhanced or result.partial_enhancement:
                self._metrics.files_enhanced += 1
            else:
                self._metrics.files_unchanged += 1
        else:
            self._metrics.files_failed += 1

        # Function metrics
        self._metrics.total_functions_processed += len(result.function_enhancements)
        for func in result.function_enhancements:
            if func.enhanced_code != func.original_code and not func.rolled_back:
                self._metrics.functions_enhanced += 1
            if func.rolled_back:
                self._metrics.functions_rolled_back += 1

        # IR validation metrics
        self._metrics.ir_validations_passed += result.ir_validations_passed
        self._metrics.ir_validations_failed += result.ir_validations_failed

        # Performance metrics
        self._metrics.total_time_ms += result.total_time_ms
        self._metrics.total_tokens_used += result.total_tokens_used
        self._metrics.cache_hits += result.cache_hits

    async def _compare_baseline(self, cognitive_result: EnhancementResult) -> None:
        """
        Compare cognitive result with baseline for A/B testing.

        This simulates what would have happened without cognitive enhancement.
        """
        # In baseline mode, we track:
        # - Issues that cognitive pass prevented
        # - Issues that baseline would have missed

        # For now, estimate based on anti-patterns applied
        for func in cognitive_result.function_enhancements:
            if func.anti_patterns_applied:
                # Each anti-pattern application is a potential issue prevented
                if func.validation_passed and not func.rolled_back:
                    self._metrics.cognitive_issues_prevented += len(
                        func.anti_patterns_applied
                    )
                else:
                    # Rolled back or failed = baseline would have had this issue
                    self._metrics.baseline_issues_detected += 1

    def get_metrics(self) -> CognitiveGenerationMetrics:
        """Get current metrics."""
        return self._metrics

    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary."""
        return self._metrics.to_dict()

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_statistics()

    def get_pass_statistics(self) -> Dict[str, Any]:
        """Get cognitive pass statistics."""
        return self._cognitive_pass.get_statistics()

    def get_file_results(self) -> List[EnhancementResult]:
        """Get all file results."""
        return self._file_results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of cognitive generation.
        """
        return {
            "enabled": self._enabled,
            "baseline_mode": self._baseline_mode,
            "metrics": self.get_metrics_dict(),
            "cache": self.get_cache_statistics(),
            "pass": self.get_pass_statistics(),
            "version": IRCentricCognitivePass.VERSION,
            "timestamp": datetime.now().isoformat(),
        }

    def reset_metrics(self) -> None:
        """Reset metrics for new run."""
        self._metrics = CognitiveGenerationMetrics()
        self._file_results.clear()
        logger.info("Cognitive metrics reset")

    def clear_cache(self) -> int:
        """Clear cognitive cache."""
        count = self._cache.clear()
        logger.info(f"Cleared {count} entries from cognitive cache")
        return count


# Factory function for easy creation
def create_cognitive_service(
    ir: ApplicationIR,
    pattern_store: Optional[NegativePatternStore] = None,
    llm_client: Optional[Any] = None,
    cache_path: Optional[str] = None,
) -> CognitiveCodeGenerationService:
    """
    Factory function to create CognitiveCodeGenerationService.

    Args:
        ir: Application IR
        pattern_store: Optional pattern store (creates default if None)
        llm_client: Optional LLM client
        cache_path: Optional cache storage path

    Returns:
        Configured CognitiveCodeGenerationService
    """
    if pattern_store is None:
        pattern_store = NegativePatternStore()

    cache_storage = Path(cache_path) if cache_path else None

    return CognitiveCodeGenerationService(
        ir=ir,
        pattern_store=pattern_store,
        llm_client=llm_client,
        cache_storage_path=cache_storage,
    )
