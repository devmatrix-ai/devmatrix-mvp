"""
Spec Translator Service - Pre-pipeline spec translation to English.

Translates specs from any language to English BEFORE pipeline ingestion.
This ensures consistent handling of:
- YAML parsing (no special character issues)
- Code generation (English-based templates)
- LLM prompts (consistent language)

Usage:
    translator = SpecTranslator()
    english_spec = await translator.translate_if_needed(spec_content, spec_path)
"""

import logging
import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from anthropic import Anthropic

logger = logging.getLogger(__name__)


# Language detection patterns
SPANISH_PATTERNS = [
    r'\b(qué|cómo|dónde|cuándo|cuál|quién)\b',  # Question words
    r'\b(el|la|los|las|un|una|unos|unas)\b',     # Articles
    r'\b(para|desde|hasta|sobre|entre)\b',       # Prepositions
    r'\b(está|están|tiene|tienen|puede|pueden)\b', # Common verbs
    r'[áéíóúüñ¿¡]',                              # Spanish characters
]

NON_ENGLISH_INDICATORS = [
    # Spanish
    (r'\b(especificación|entidades|endpoints|cliente|producto|carrito|orden)\b', 'spanish'),
    (r'\b(obligatorio|opcional|único|activo|automático)\b', 'spanish'),
    # Portuguese
    (r'\b(especificação|entidades|obrigatório|opcional)\b', 'portuguese'),
    # French
    (r'\b(spécification|entités|obligatoire|optionnel)\b', 'french'),
    # German
    (r'\b(Spezifikation|Entitäten|erforderlich|optional)\b', 'german'),
]


TRANSLATION_PROMPT = """You are a technical translator specializing in API specifications.

Translate the following API specification to English. Preserve:
1. All technical terms (API, REST, CRUD, UUID, etc.)
2. The exact structure and formatting (markdown, YAML, etc.)
3. All code examples unchanged
4. All field names and identifiers unchanged

Only translate the descriptive text, comments, and documentation.

IMPORTANT:
- Keep the same file format (markdown stays markdown, YAML stays YAML)
- Preserve all code blocks exactly
- Keep all technical identifiers (field names, endpoint paths, etc.)
- Translate descriptions, comments, and explanations to clear, professional English

---
ORIGINAL SPEC:
{spec_content}
---

Respond ONLY with the translated specification. No explanations or additional text."""


class SpecTranslator:
    """
    Translates specs to English before pipeline ingestion.

    This service:
    1. Detects if spec is in non-English language
    2. Translates to English using Claude
    3. Caches translations to avoid re-processing
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize translator.

        Args:
            cache_dir: Directory for translation cache (default: .devmatrix/translations)
            model: Claude model to use (default: Sonnet for cost efficiency)
        """
        self.model = model
        self.cache_dir = Path(cache_dir or ".devmatrix/translations")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[Anthropic] = None
        self.logger = logging.getLogger(f"{__name__}.SpecTranslator")

    @property
    def client(self) -> Anthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            self._client = Anthropic()
        return self._client

    def detect_language(self, content: str) -> Tuple[str, float]:
        """
        Detect the language of the spec content.

        Args:
            content: Spec content to analyze

        Returns:
            Tuple of (language_code, confidence)
        """
        # Check for non-English indicators
        content_lower = content.lower()

        language_scores = {"english": 0, "spanish": 0, "portuguese": 0, "french": 0, "german": 0}

        # Check specific language patterns
        for pattern, lang in NON_ENGLISH_INDICATORS:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            language_scores[lang] += matches * 2

        # Check Spanish patterns specifically (most common non-English for this codebase)
        for pattern in SPANISH_PATTERNS:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            language_scores["spanish"] += matches

        # Determine language
        max_lang = max(language_scores, key=language_scores.get)
        max_score = language_scores[max_lang]

        if max_score == 0:
            return ("english", 0.9)

        # If Spanish score is significant, mark as Spanish
        if language_scores["spanish"] > 5:
            confidence = min(0.95, 0.5 + (language_scores["spanish"] / 50))
            return ("spanish", confidence)

        if max_score > 3:
            confidence = min(0.95, 0.5 + (max_score / 30))
            return (max_lang, confidence)

        return ("english", 0.7)

    def _get_cache_key(self, content: str) -> str:
        """Generate cache key from content hash."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached_translation(self, content: str) -> Optional[str]:
        """Get cached translation if available."""
        cache_key = self._get_cache_key(content)
        cache_file = self.cache_dir / f"{cache_key}.txt"

        if cache_file.exists():
            self.logger.info(f"Using cached translation: {cache_key}")
            return cache_file.read_text(encoding="utf-8")
        return None

    def _cache_translation(self, original: str, translated: str):
        """Cache a translation."""
        cache_key = self._get_cache_key(original)
        cache_file = self.cache_dir / f"{cache_key}.txt"
        cache_file.write_text(translated, encoding="utf-8")
        self.logger.info(f"Cached translation: {cache_key}")

    async def translate(self, content: str) -> str:
        """
        Translate spec content to English.

        Args:
            content: Spec content to translate

        Returns:
            Translated content in English
        """
        # Check cache first
        cached = self._get_cached_translation(content)
        if cached:
            return cached

        self.logger.info("Translating spec to English...")

        prompt = TRANSLATION_PROMPT.format(spec_content=content)

        try:
            # Use synchronous call (simpler, no streaming needed for translation)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.1,  # Low temperature for consistent translation
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            translated = response.content[0].text

            # Cache the translation
            self._cache_translation(content, translated)

            # Log token usage
            self.logger.info(
                f"Translation complete: {response.usage.input_tokens} in, "
                f"{response.usage.output_tokens} out"
            )

            return translated

        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            # Return original on failure
            return content

    def translate_sync(self, content: str) -> str:
        """
        Synchronous version of translate.

        Args:
            content: Spec content to translate

        Returns:
            Translated content in English
        """
        import asyncio

        # Check cache first
        cached = self._get_cached_translation(content)
        if cached:
            return cached

        self.logger.info("Translating spec to English (sync)...")

        prompt = TRANSLATION_PROMPT.format(spec_content=content)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            translated = response.content[0].text
            self._cache_translation(content, translated)

            self.logger.info(
                f"Translation complete: {response.usage.input_tokens} in, "
                f"{response.usage.output_tokens} out"
            )

            return translated

        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return content

    async def translate_if_needed(
        self,
        content: str,
        spec_path: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Translate spec to English only if needed.

        Args:
            content: Spec content
            spec_path: Optional path for logging

        Returns:
            Tuple of (content, was_translated)
        """
        language, confidence = self.detect_language(content)

        if language == "english" and confidence > 0.7:
            self.logger.info(
                f"Spec appears to be in English (confidence: {confidence:.0%}), "
                "skipping translation"
            )
            return (content, False)

        self.logger.info(
            f"Detected {language} (confidence: {confidence:.0%}), translating to English"
        )

        translated = await self.translate(content)
        return (translated, True)

    def translate_if_needed_sync(
        self,
        content: str,
        spec_path: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Synchronous version of translate_if_needed.

        Args:
            content: Spec content
            spec_path: Optional path for logging

        Returns:
            Tuple of (content, was_translated)
        """
        language, confidence = self.detect_language(content)

        if language == "english" and confidence > 0.7:
            self.logger.info(
                f"Spec appears to be in English (confidence: {confidence:.0%}), "
                "skipping translation"
            )
            return (content, False)

        self.logger.info(
            f"Detected {language} (confidence: {confidence:.0%}), translating to English"
        )

        translated = self.translate_sync(content)
        return (translated, True)


# =============================================================================
# Singleton Instance
# =============================================================================

_spec_translator: Optional[SpecTranslator] = None


def get_spec_translator() -> SpecTranslator:
    """Get singleton instance of SpecTranslator."""
    global _spec_translator
    if _spec_translator is None:
        _spec_translator = SpecTranslator()
    return _spec_translator


def translate_spec_if_needed(content: str, spec_path: Optional[str] = None) -> Tuple[str, bool]:
    """
    Convenience function for synchronous spec translation.

    Args:
        content: Spec content
        spec_path: Optional path for logging

    Returns:
        Tuple of (content, was_translated)
    """
    translator = get_spec_translator()
    return translator.translate_if_needed_sync(content, spec_path)
