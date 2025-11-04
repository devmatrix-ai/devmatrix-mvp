"""
Code Metadata Extractor for RAG

Auto-detects programming language, framework, and code patterns from source code.
Enriches document metadata for better filtering and retrieval.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class CodeMetadata:
    """Detected code metadata."""
    language: str  # python, javascript, typescript, etc.
    framework: str  # express, react, fastapi, django, etc.
    patterns: List[str]  # List of detected patterns
    confidence: float  # 0.0-1.0 confidence score


class MetadataExtractor:
    """Extracts metadata from code snippets."""

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": [
            r"\bdef\s+\w+",
            r"\bimport\s+\w+",
            r"\bfrom\s+\w+\s+import",
            r":\s*$",  # Colon at end of line
            r"\b(async\s+def|await|yield|@property|@staticmethod)",
            r"\bif\s+__name__\s*==\s*['\"]__main__['\"]",
        ],
        "javascript": [
            r"\bfunction\s+\w+",
            r"\brequire\(['\"]",
            r"\bmodule\.exports",
            r"\.then\(",
            r"=>",  # Arrow function
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
        ],
        "typescript": [
            r":\s+(string|number|boolean|any|void|interface|type)",
            r"\binterface\s+\w+",
            r"\btype\s+\w+\s*=",
            r"\b(private|protected|public)\s+\w+",
            r"<.*>",  # Generic syntax
        ],
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "express": [
            r"require\(['\"]express",
            r"import.*express",
            r"app\.get\(",
            r"app\.post\(",
            r"app\.use\(",
            r"Router\(\)",
            r"middleware",
            r"res\.send|res\.json",
        ],
        "react": [
            r"import\s+.*React",
            r"from\s+['\"]react['\"]",
            r"useState|useEffect|useContext",
            r"function\s+\w+.*\(\).*{",  # Functional component
            r"export\s+(default\s+)?function",
            r"<.*>.*</.*>",  # JSX
            r"className=",
            r"jsx|tsx",
        ],
        "fastapi": [
            r"from\s+fastapi\s+import",
            r"@app\.get|@app\.post|@app\.put|@app\.delete",
            r"FastAPI\(\)",
            r"Depends\(",
            r"Path\(|Query\(|Body\(",
        ],
        "django": [
            r"from\s+django",
            r"from\s+django\..*\s+import",
            r"@login_required|@csrf_exempt",
            r"models\.Model",
            r"def\s+\w+\(request",
        ],
        "typescript": [
            r":\s+(string|number|boolean|interface|type)",
            r"\binterface\s+\w+",
            r"\btype\s+\w+",
        ],
    }

    # Pattern categories
    PATTERN_CATEGORIES = {
        "async_await": [r"\basync\s+def|\basync\s+function|await\s+", r"\.then\("],
        "error_handling": [r"try:|except:|catch\(|finally", r"throw new|raise\s+"],
        "typing": [r":\s+\w+", r"<.*>", r"\btype\b"],
        "testing": [r"@pytest\.mark|@test|describe\(|it\(|test\("],
        "security": [r"password|token|auth|secret|encryption"],
    }

    @classmethod
    def extract(cls, code: str) -> CodeMetadata:
        """
        Extract metadata from code snippet.

        Args:
            code: Source code snippet

        Returns:
            CodeMetadata object with detected language, framework, patterns
        """
        code = code.strip()

        # Detect language
        language, lang_score = cls._detect_language(code)

        # Detect framework
        framework, fw_score = cls._detect_framework(code, language)

        # Detect patterns
        patterns = cls._detect_patterns(code)

        # Calculate confidence
        confidence = (lang_score + fw_score) / 2

        return CodeMetadata(
            language=language,
            framework=framework,
            patterns=patterns,
            confidence=confidence
        )

    @classmethod
    def _detect_language(cls, code: str) -> Tuple[str, float]:
        """Detect programming language with confidence score."""
        scores = {}

        for lang, patterns in cls.LANGUAGE_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE):
                    matches += 1
            scores[lang] = matches / len(patterns) if patterns else 0

        # Heuristics for language detection
        if "def " in code and "import " in code:
            scores["python"] = min(1.0, scores.get("python", 0) + 0.3)

        if "const " in code or "function " in code:
            scores["javascript"] = min(1.0, scores.get("javascript", 0) + 0.2)

        if "interface " in code or "type " in code:
            scores["typescript"] = min(1.0, scores.get("typescript", 0) + 0.3)

        if scores:
            best_lang = max(scores.items(), key=lambda x: x[1])
            return best_lang[0], best_lang[1]

        return "unknown", 0.0

    @classmethod
    def _detect_framework(cls, code: str, language: str) -> Tuple[str, float]:
        """Detect framework with confidence score."""
        scores = {}

        for framework, patterns in cls.FRAMEWORK_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                    matches += 1
            scores[framework] = matches / len(patterns) if patterns else 0

        # Language-specific framework boosts
        if language == "python":
            scores.pop("express", None)
            scores.pop("react", None)
            scores["django"] = min(1.0, scores.get("django", 0) + 0.2)
            scores["fastapi"] = min(1.0, scores.get("fastapi", 0) + 0.2)

        if language in ("javascript", "typescript"):
            scores.pop("fastapi", None)
            scores.pop("django", None)
            scores["express"] = min(1.0, scores.get("express", 0) + 0.2)
            scores["react"] = min(1.0, scores.get("react", 0) + 0.2)

        if scores:
            best_fw = max(scores.items(), key=lambda x: x[1])
            # Only return if confidence > 0.2
            if best_fw[1] > 0.2:
                return best_fw[0], best_fw[1]

        return "unknown", 0.0

    @classmethod
    def _detect_patterns(cls, code: str) -> List[str]:
        """Detect code patterns and best practices."""
        detected = []

        for category, patterns in cls.PATTERN_CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                    detected.append(category)
                    break

        return detected

    @classmethod
    def enrich_metadata(
        cls,
        metadata: Dict[str, Any],
        code: str
    ) -> Dict[str, Any]:
        """
        Enrich existing metadata with auto-detected values.

        Preserves manual metadata but fills in missing fields.

        NOTE: ChromaDB only supports str, int, float, bool, None in metadata.
        Patterns are stored as comma-separated string.

        Args:
            metadata: Existing metadata dict
            code: Source code snippet

        Returns:
            Enriched metadata dict
        """
        extracted = cls.extract(code)

        # Create enriched copy
        enriched = dict(metadata)

        # Fill missing language
        if not enriched.get("language") or enriched.get("language") == "unknown":
            enriched["language"] = extracted.language

        # Fill missing framework
        if not enriched.get("framework") or enriched.get("framework") == "unknown":
            enriched["framework"] = extracted.framework

        # Add patterns as comma-separated string (ChromaDB doesn't support lists)
        if extracted.patterns:
            enriched["patterns"] = ",".join(extracted.patterns)
        else:
            enriched["patterns"] = ""

        # Add confidence as float
        enriched["metadata_confidence"] = round(extracted.confidence, 2)

        return enriched
