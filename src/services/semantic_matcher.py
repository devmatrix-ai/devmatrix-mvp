"""
Semantic Matcher: Hybrid Embeddings + LLM approach for constraint matching.

Uses sentence-transformers for fast embedding-based matching (~1ms),
falling back to LLM (Claude Haiku) for uncertain cases (~500ms).

Paper inspiration: ReMatch (arXiv:2403.01567)
"""

from dataclasses import dataclass
from typing import Optional
import json
import logging

try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a semantic match operation."""
    match: bool
    confidence: float
    method: str  # "embedding" | "llm" | "fallback"
    spec_constraint: str
    code_constraint: str
    reason: Optional[str] = None


class SemanticMatcher:
    """
    Hybrid semantic matcher: Embeddings first, LLM for uncertain cases.

    Architecture:
        1. Compute embedding similarity (cosine)
        2. If sim >= HIGH_THRESHOLD → MATCH
        3. If sim < LOW_THRESHOLD → NO MATCH
        4. Otherwise → LLM validation

    This eliminates the need for manual equivalence mappings.
    """

    HIGH_THRESHOLD = 0.8   # Above this = definite match
    LOW_THRESHOLD = 0.5    # Below this = definite no match
    # Between LOW and HIGH = uncertain, use LLM

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        use_llm_fallback: bool = True,
        llm_model: str = "claude-3-haiku-20240307"
    ):
        """
        Initialize the semantic matcher.

        Args:
            model_name: Sentence transformer model to use
            use_llm_fallback: Whether to use LLM for uncertain cases
            llm_model: Claude model for LLM validation
        """
        self.use_llm_fallback = use_llm_fallback
        self.llm_model = llm_model
        self._cache: dict[str, any] = {}

        # Initialize sentence transformer
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer(model_name)
                logger.info(f"Loaded sentence transformer: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")
                self.encoder = None
        else:
            logger.warning("sentence-transformers not installed, using fallback")
            self.encoder = None

        # Initialize Anthropic client
        if ANTHROPIC_AVAILABLE and use_llm_fallback:
            try:
                self.client = Anthropic()
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            self.client = None

    def match(self, spec: str, code: str) -> MatchResult:
        """
        Match a spec constraint to a code constraint.

        Args:
            spec: Specification constraint text
            code: Code constraint text

        Returns:
            MatchResult with match status, confidence, and method used
        """
        # Fallback if no encoder available
        if self.encoder is None:
            return self._fallback_match(spec, code)

        # Step 1: Embedding similarity
        sim = self._embedding_similarity(spec, code)

        # High confidence match
        if sim >= self.HIGH_THRESHOLD:
            return MatchResult(
                match=True,
                confidence=float(sim),
                method="embedding",
                spec_constraint=spec,
                code_constraint=code,
                reason=f"High embedding similarity: {sim:.3f}"
            )

        # High confidence no-match
        if sim < self.LOW_THRESHOLD:
            return MatchResult(
                match=False,
                confidence=float(1 - sim),
                method="embedding",
                spec_constraint=spec,
                code_constraint=code,
                reason=f"Low embedding similarity: {sim:.3f}"
            )

        # Uncertain case: use LLM if available
        if self.use_llm_fallback and self.client is not None:
            return self._llm_validate(spec, code, sim)

        # No LLM available, use embedding result with lower confidence
        return MatchResult(
            match=sim >= 0.65,  # Slightly above middle
            confidence=float(sim),
            method="embedding",
            spec_constraint=spec,
            code_constraint=code,
            reason=f"Uncertain (no LLM), similarity: {sim:.3f}"
        )

    def _embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)
        return float(util.cos_sim(emb1, emb2)[0][0])

    def _get_embedding(self, text: str):
        """Get embedding with caching."""
        if text not in self._cache:
            self._cache[text] = self.encoder.encode(text, convert_to_tensor=True)
        return self._cache[text]

    def _llm_validate(self, spec: str, code: str, embed_sim: float) -> MatchResult:
        """Use LLM to validate uncertain matches."""
        try:
            response = self.client.messages.create(
                model=self.llm_model,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""Determine if this code implements this specification constraint.

Specification constraint: "{spec}"
Code constraint: "{code}"

Consider semantic equivalence, not just literal text matching.
For example, "EmailStr" implements "must be valid email".

Respond ONLY with valid JSON:
{{"match": true or false, "confidence": 0.0 to 1.0, "reason": "brief explanation"}}"""
                }]
            )

            result_text = response.content[0].text.strip()

            # Try to extract JSON from response
            if result_text.startswith("{"):
                result = json.loads(result_text)
            else:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")

            return MatchResult(
                match=result.get("match", False),
                confidence=float(result.get("confidence", 0.5)),
                method="llm",
                spec_constraint=spec,
                code_constraint=code,
                reason=result.get("reason", "LLM validation")
            )

        except Exception as e:
            logger.warning(f"LLM validation failed: {e}")
            # Fall back to embedding result
            return MatchResult(
                match=embed_sim >= 0.65,
                confidence=float(embed_sim),
                method="embedding",
                spec_constraint=spec,
                code_constraint=code,
                reason=f"LLM failed, using embedding: {embed_sim:.3f}"
            )

    def _fallback_match(self, spec: str, code: str) -> MatchResult:
        """Fallback matching when no ML models available."""
        # Simple heuristic: normalized string containment
        spec_lower = spec.lower()
        code_lower = code.lower()

        # Extract key terms
        spec_terms = set(spec_lower.split())
        code_terms = set(code_lower.split())

        # Calculate overlap
        overlap = len(spec_terms & code_terms)
        total = len(spec_terms | code_terms)
        similarity = overlap / total if total > 0 else 0

        return MatchResult(
            match=similarity >= 0.3,
            confidence=similarity,
            method="fallback",
            spec_constraint=spec,
            code_constraint=code,
            reason=f"Fallback word overlap: {similarity:.3f}"
        )

    def match_batch(
        self,
        specs: list[str],
        codes: list[str],
        return_all: bool = False
    ) -> list[MatchResult]:
        """
        Match multiple spec constraints to code constraints.

        For each spec, finds the best matching code constraint.

        Args:
            specs: List of specification constraints
            codes: List of code constraints
            return_all: If True, return all matches including non-matches

        Returns:
            List of MatchResult for each spec that found a match
        """
        results = []

        for spec in specs:
            best_match: Optional[MatchResult] = None
            best_score = 0.0

            for code in codes:
                result = self.match(spec, code)

                if result.match and result.confidence > best_score:
                    best_match = result
                    best_score = result.confidence

            if best_match:
                results.append(best_match)
            elif return_all:
                # No match found, add a non-match result
                results.append(MatchResult(
                    match=False,
                    confidence=0.0,
                    method="none",
                    spec_constraint=spec,
                    code_constraint="",
                    reason="No matching code constraint found"
                ))

        return results

    def get_stats(self) -> dict:
        """Get matcher statistics."""
        return {
            "cache_size": len(self._cache),
            "encoder_available": self.encoder is not None,
            "llm_available": self.client is not None,
            "high_threshold": self.HIGH_THRESHOLD,
            "low_threshold": self.LOW_THRESHOLD,
        }

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()

    # ═══════════════════════════════════════════════════════════════════════════════
    # ApplicationIR Integration (OPTIONAL - does not break existing functionality)
    # ═══════════════════════════════════════════════════════════════════════════════

    def match_from_validation_model(
        self,
        validation_model,  # ValidationModelIR - not typed to avoid import
        found_constraints: list[str]
    ) -> tuple[float, list[MatchResult]]:
        """
        Match found code constraints against ValidationModelIR rules.

        Uses the structured IR for more precise matching:
        - entity + attribute gives us exact field targeting
        - condition gives us the expected constraint
        - enforcement_type tells us if it's real enforcement

        Args:
            validation_model: ValidationModelIR instance with rules
            found_constraints: List of code constraints in "Entity.field: constraint" format

        Returns:
            Tuple of (compliance_score, list of MatchResult)
        """
        if not validation_model or not hasattr(validation_model, 'rules'):
            logger.warning("Invalid validation_model, falling back to standard matching")
            return 0.0, []

        results = []
        matched_count = 0
        total_rules = len(validation_model.rules)

        if total_rules == 0:
            return 1.0, []  # No rules = 100% compliance

        # Build found constraints map: "Entity.field" -> [constraints]
        found_map = {}
        for constraint in found_constraints:
            if ": " in constraint:
                key, value = constraint.split(": ", 1)
                if key not in found_map:
                    found_map[key] = []
                found_map[key].append(value.lower())

        for rule in validation_model.rules:
            # Build expected constraint string from IR
            entity_field = f"{rule.entity}.{rule.attribute}"
            expected_constraint = rule.condition or str(rule.type.value)

            # Check if we have any constraints for this field
            if entity_field not in found_map:
                results.append(MatchResult(
                    match=False,
                    confidence=0.0,
                    method="ir_lookup",
                    spec_constraint=f"{entity_field}: {expected_constraint}",
                    code_constraint="",
                    reason=f"No constraints found for {entity_field}"
                ))
                continue

            # Try to match against found constraints
            best_match = None
            best_confidence = 0.0

            for found_constraint in found_map[entity_field]:
                result = self.match(expected_constraint, found_constraint)

                if result.confidence > best_confidence:
                    best_match = MatchResult(
                        match=result.match,
                        confidence=result.confidence,
                        method=f"ir_{result.method}",
                        spec_constraint=f"{entity_field}: {expected_constraint}",
                        code_constraint=f"{entity_field}: {found_constraint}",
                        reason=result.reason
                    )
                    best_confidence = result.confidence

            if best_match and best_match.match:
                matched_count += 1
                results.append(best_match)
            else:
                # Add best non-match for debugging
                results.append(best_match or MatchResult(
                    match=False,
                    confidence=0.0,
                    method="ir_lookup",
                    spec_constraint=f"{entity_field}: {expected_constraint}",
                    code_constraint=f"{entity_field}: {found_map[entity_field][0]}",
                    reason="No semantic match found"
                ))

        compliance = matched_count / total_rules if total_rules > 0 else 1.0
        logger.info(f"🧠 IR-based matching: {matched_count}/{total_rules} = {compliance:.1%}")

        return compliance, results
