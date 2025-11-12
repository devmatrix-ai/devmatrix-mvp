"""
Centralized LLM Configuration for Deterministic Behavior

This module provides centralized configuration for all LLM interactions
to ensure deterministic and reproducible behavior across the entire system.

DETERMINISTIC MODE REQUIREMENTS:
- temperature = 0.0 (zero randomness)
- seed = 42 (reproducible outputs)
- top_p = 1.0 (no nucleus sampling)
- frequency_penalty = 0 (no frequency bias)
- presence_penalty = 0 (no presence bias)

These settings maximize determinism and precision in LLM responses,
critical for achieving >95% accuracy in masterplan generation.

Usage:
    from src.config.llm_config import LLMConfig

    # Get deterministic parameters
    params = LLMConfig.get_deterministic_params()

    # Use with any LLM call
    response = await llm.generate(**params)
"""

from typing import Dict, Any


class LLMConfig:
    """Centralized LLM configuration for deterministic behavior."""

    # Core deterministic settings
    DEFAULT_SEED = 42
    DEFAULT_TEMPERATURE = 0.0
    DETERMINISTIC_MODE = True

    # Sampling parameters
    DEFAULT_TOP_P = 1.0
    DEFAULT_FREQUENCY_PENALTY = 0
    DEFAULT_PRESENCE_PENALTY = 0

    # Max tokens defaults (can be overridden)
    DEFAULT_MAX_TOKENS = 4096
    MAX_TOKENS_LARGE = 8192

    @staticmethod
    def get_deterministic_params() -> Dict[str, Any]:
        """
        Get standard deterministic parameters for LLM calls.

        Returns:
            Dict with temperature, seed, and sampling parameters
        """
        return {
            "temperature": LLMConfig.DEFAULT_TEMPERATURE,
            "seed": LLMConfig.DEFAULT_SEED,
            "top_p": LLMConfig.DEFAULT_TOP_P,
            "frequency_penalty": LLMConfig.DEFAULT_FREQUENCY_PENALTY,
            "presence_penalty": LLMConfig.DEFAULT_PRESENCE_PENALTY
        }

    @staticmethod
    def get_params_with_max_tokens(max_tokens: int = None) -> Dict[str, Any]:
        """
        Get deterministic parameters with custom max_tokens.

        Args:
            max_tokens: Maximum tokens for response (default: DEFAULT_MAX_TOKENS)

        Returns:
            Dict with temperature, seed, sampling params, and max_tokens
        """
        params = LLMConfig.get_deterministic_params()
        params["max_tokens"] = max_tokens or LLMConfig.DEFAULT_MAX_TOKENS
        return params

    @staticmethod
    def validate_determinism(params: Dict[str, Any]) -> bool:
        """
        Validate that parameters meet deterministic requirements.

        Args:
            params: Dictionary of LLM parameters to validate

        Returns:
            True if deterministic, False otherwise
        """
        if params.get("temperature", 1.0) != 0.0:
            return False
        if params.get("seed") is None:
            return False
        if params.get("top_p", 1.0) != 1.0:
            return False
        return True

    @staticmethod
    def enforce_determinism(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Force deterministic settings on any parameter dict.

        Args:
            params: Original parameters

        Returns:
            Parameters with deterministic settings enforced
        """
        deterministic = LLMConfig.get_deterministic_params()
        return {**params, **deterministic}


# Backwards compatibility aliases
TEMPERATURE_DEFAULT = LLMConfig.DEFAULT_TEMPERATURE
SEED_DEFAULT = LLMConfig.DEFAULT_SEED
