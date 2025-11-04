"""
Query Expansion for RAG System

Expands queries with synonyms and language variants to improve retrieval.
Increases coverage by searching for multiple formulations of the same concept.
"""

from typing import List, Dict, Set
import re
from src.observability import get_logger


class QueryExpander:
    """Expands queries into variants for better retrieval coverage."""

    # Framework variants and synonyms
    FRAMEWORK_SYNONYMS = {
        "express": ["express", "express.js", "expressjs", "middleware", "routing", "server"],
        "react": ["react", "react.js", "reactjs", "hooks", "components", "jsx"],
        "typescript": ["typescript", "ts", "typescripts", "types", "interfaces", "type annotations"],
        "javascript": ["javascript", "js", "node.js", "nodejs", "async/await", "node"],
        "fastapi": ["fastapi", "fast api", "pydantic", "async python"],
        "django": ["django", "djangorest", "django rest", "django orm"],
        "vue": ["vue", "vue.js", "vuejs", "composition api"],
        "angular": ["angular", "angularjs", "typescript framework"],
    }

    # Language variants
    LANGUAGE_SYNONYMS = {
        "python": ["python", "py", "pyhton"],
        "javascript": ["javascript", "js", "node", "node.js"],
        "typescript": ["typescript", "ts", "typescripts"],
        "java": ["java", "jvm"],
        "csharp": ["csharp", "c#", ".net"],
    }

    # Common code pattern synonyms
    PATTERN_SYNONYMS = {
        "async": ["async", "asynchronous", "concurrent", "parallel", "promise", "await"],
        "error": ["error", "exception", "handling", "try/catch", "error handling"],
        "test": ["test", "testing", "unit test", "jest", "pytest", "mocha"],
        "api": ["api", "endpoint", "rest", "http", "request", "response"],
        "database": ["database", "db", "query", "sql", "orm", "mongo"],
        "authentication": ["auth", "authentication", "login", "jwt", "token", "password"],
        "validation": ["validation", "validate", "check", "verify", "schema"],
    }

    def __init__(self):
        self.logger = get_logger("rag.query_expander")

    def expand_query(self, query: str, max_variants: int = 5) -> List[str]:
        """
        Expand query into multiple variants.

        Args:
            query: Original query text
            max_variants: Maximum number of variants to generate (including original)

        Returns:
            List of query variants, starting with original
        """
        variants = [query]  # Always include original

        # Create semantic variants by extracting key concepts
        semantic_variants = self._create_semantic_variants(query)
        variants.extend(semantic_variants)

        # Find and add domain-specific keyword variants
        keyword_variants = self._add_domain_keywords(query)
        variants.extend(keyword_variants)

        # Remove duplicates and awkward variants while preserving order
        seen: Set[str] = set()
        unique_variants = []
        for variant in variants:
            variant_lower = variant.lower().strip()

            # Skip empty variants
            if not variant_lower:
                continue

            # Skip variants that are too similar (substring duplicates)
            is_duplicate = False
            for existing in seen:
                if variant_lower == existing:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen.add(variant_lower)
                unique_variants.append(variant)

        # Return up to max_variants, prioritizing original
        result = [unique_variants[0]] + unique_variants[1:max_variants]

        self.logger.debug(
            f"Query expansion: {len(result)} variants from '{query}'",
            variants_count=len(result)
        )

        return result

    def _create_semantic_variants(self, query: str) -> List[str]:
        """
        Create semantic variants by rephrasing the query.

        Instead of just replacing keywords, create meaningful paraphrases
        that preserve the core meaning while varying the wording.
        """
        variants = []
        query_lower = query.lower()

        # Variant 1: Extract core framework if present and use alternative name
        for framework, synonyms in self.FRAMEWORK_SYNONYMS.items():
            for syn in synonyms:
                if syn.lower() in query_lower:
                    # Use different synonym
                    for alt_syn in synonyms:
                        if alt_syn != syn and alt_syn not in query_lower:
                            variant = query_lower.replace(syn.lower(), alt_syn)
                            if variant != query_lower and len(variant) > 5:
                                variants.append(variant)
                            break
                    break

        # Variant 2: Focus on specific keywords from the query
        # Extract significant words (skip common words)
        common_words = {"with", "and", "the", "for", "of", "in", "to", "a", "how"}
        words = [w for w in query_lower.split() if w not in common_words and len(w) > 3]

        # Create focused variant with first few significant words
        if len(words) >= 2:
            focused_variant = " ".join(words[:3])
            if focused_variant != query_lower and len(focused_variant) > 5:
                variants.append(focused_variant)

        # Variant 3: Add pattern-specific keywords if applicable
        for pattern, keywords in self.PATTERN_SYNONYMS.items():
            if any(kw.lower() in query_lower for kw in keywords):
                # Add alternative keyword
                alt_keyword = keywords[1] if len(keywords) > 1 else keywords[0]
                if alt_keyword.lower() not in query_lower:
                    variant = f"{query_lower} {alt_keyword}"
                    if len(variant) > len(query_lower):
                        variants.append(variant)
                    break

        return variants

    def _add_domain_keywords(self, query: str) -> List[str]:
        """Add domain-specific keywords to broaden search coverage."""
        variants = []
        query_lower = query.lower()

        # Identify what type of query this is and add related keywords
        if any(fw in query_lower for fw in ["express", "flask", "django", "fastapi"]):
            variants.append(f"{query_lower} api endpoint")
            variants.append(f"{query_lower} http handler")

        if any(lib in query_lower for lib in ["react", "vue", "angular"]):
            variants.append(f"{query_lower} component")
            variants.append(f"{query_lower} ui frontend")

        if any(lang in query_lower for lang in ["typescript", "python", "javascript"]):
            variants.append(f"{query_lower} code example")

        if "async" in query_lower or "await" in query_lower:
            variants.append(f"{query_lower} promise concurrency")

        if "error" in query_lower or "exception" in query_lower:
            variants.append(f"{query_lower} exception handling")

        return variants

    def combine_results(self, results_by_query: Dict[str, List]) -> List:
        """
        Combine results from multiple query variants intelligently.

        Deduplicates by document ID and ranks by occurrence frequency.

        Args:
            results_by_query: Dict mapping query variant to its results

        Returns:
            Combined and ranked results
        """
        # Track results by ID with occurrence count and best score
        result_tracker: Dict[str, Dict] = {}

        for query, results in results_by_query.items():
            for result in results:
                result_id = result.get("id") if isinstance(result, dict) else result.id

                if result_id not in result_tracker:
                    result_tracker[result_id] = {
                        "result": result,
                        "count": 0,
                        "max_score": 0.0,
                    }

                result_tracker[result_id]["count"] += 1

                # Track best similarity score
                score = result.get("similarity") if isinstance(result, dict) else result.similarity
                if score:
                    result_tracker[result_id]["max_score"] = max(
                        result_tracker[result_id]["max_score"],
                        score
                    )

        # Sort by occurrence count (results appearing in multiple queries ranked higher)
        sorted_results = sorted(
            result_tracker.values(),
            key=lambda x: (x["count"], x["max_score"]),
            reverse=True
        )

        # Extract just the result objects
        combined = [r["result"] for r in sorted_results]

        self.logger.debug(
            f"Combined {len(result_tracker)} unique results from {len(results_by_query)} queries",
            unique_count=len(result_tracker),
            query_count=len(results_by_query)
        )

        return combined


def create_query_expander() -> QueryExpander:
    """Factory function to create query expander instance."""
    return QueryExpander()
