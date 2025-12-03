"""
Smoke Feedback Classifier - Maps smoke test errors to IR context.

Classifies smoke test failures and creates GenerationAntiPattern objects
by extracting entity, endpoint, and field context from the error and IR.

Reference: DOCS/mvp/exit/learning/GENERATION_FEEDBACK_LOOP.md
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    create_anti_pattern,
    generate_pattern_id,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class IRContext:
    """Extracted IR context from error analysis."""
    entity_name: str = "*"
    endpoint_pattern: str = "*"
    field_name: str = "*"
    constraint_type: str = "*"
    relationship_type: str = "*"
    confidence: float = 0.0


@dataclass
class ErrorClassification:
    """Classification result for a smoke error."""
    error_type: str           # "database", "validation", "import", "attribute", "type"
    exception_class: str      # "IntegrityError", "ValidationError", etc.
    error_message_pattern: str  # Key part of error message
    ir_context: IRContext     # Extracted IR context
    suggested_fix: str        # Suggested correct code pattern
    classifiable: bool = True # Whether this error could be classified


# =============================================================================
# Error Patterns Database
# =============================================================================


class ErrorPatterns:
    """
    Known error patterns and their classification rules.

    Maps exception classes to:
    - Error type category
    - Sub-patterns for more specific classification
    - Suggested fixes
    """

    # Database errors → entity/field patterns
    DATABASE_ERRORS = {
        "IntegrityError": {
            "NOT NULL constraint": {
                "pattern": r"NOT NULL constraint failed: (\w+)\.(\w+)",
                "fix": "Add Optional[] type hint or default value",
                "field_type": "nullable_missing",
            },
            "FOREIGN KEY constraint": {
                "pattern": r"FOREIGN KEY constraint failed|foreign key constraint",
                "fix": "Verify FK relationship exists or use Optional[int] for FK",
                "field_type": "fk_relationship",
            },
            "UNIQUE constraint": {
                "pattern": r"UNIQUE constraint failed: (\w+)\.(\w+)",
                "fix": "Add unique check before insert or handle duplicate",
                "field_type": "unique_constraint",
            },
            "duplicate key": {
                "pattern": r"duplicate key|already exists",
                "fix": "Use get_or_create pattern or handle conflict",
                "field_type": "duplicate_key",
            },
        },
        "OperationalError": {
            "no such table": {
                "pattern": r"no such table: (\w+)",
                "fix": "Ensure model is imported and table created",
                "field_type": "table_missing",
            },
            "no such column": {
                "pattern": r"no such column: (\w+)\.(\w+)",
                "fix": "Add missing column to model or remove from query",
                "field_type": "column_missing",
            },
        },
    }

    # Validation errors → schema patterns
    VALIDATION_ERRORS = {
        "ValidationError": {
            "field required": {
                "pattern": r"field required|missing.*required",
                "fix": "Add default value or make field Optional",
                "field_type": "required_field",
            },
            "value is not valid": {
                "pattern": r"value is not a valid (\w+)",
                "fix": "Fix type annotation or add validator",
                "field_type": "type_mismatch",
            },
            "extra fields not permitted": {
                "pattern": r"extra fields not permitted|Extra inputs are not permitted",
                "fix": "Use model_config with extra='ignore' or fix schema",
                "field_type": "extra_field",
            },
            "invalid literal": {
                "pattern": r"invalid literal for (\w+)",
                "fix": "Add proper type conversion or validation",
                "field_type": "invalid_literal",
            },
        },
        "RequestValidationError": {
            "body validation": {
                "pattern": r"body.*validation|request body",
                "fix": "Fix request schema to match endpoint expectations",
                "field_type": "body_validation",
            },
        },
    }

    # Import errors → module patterns
    IMPORT_ERRORS = {
        "ImportError": {
            "no module named": {
                "pattern": r"No module named '([\w\.]+)'",
                "fix": "Add missing import or fix import path",
                "field_type": "missing_module",
            },
            "cannot import name": {
                "pattern": r"cannot import name '(\w+)' from '([\w\.]+)'",
                "fix": "Fix import path or ensure symbol is exported",
                "field_type": "wrong_import",
            },
        },
        "ModuleNotFoundError": {
            "no module named": {
                "pattern": r"No module named '([\w\.]+)'",
                "fix": "Add missing import or fix module path",
                "field_type": "module_not_found",
            },
        },
    }

    # Attribute errors → code patterns
    ATTRIBUTE_ERRORS = {
        "AttributeError": {
            "has no attribute": {
                "pattern": r"'(\w+)' object has no attribute '(\w+)'",
                "fix": "Add missing attribute or fix attribute access",
                "field_type": "missing_attribute",
            },
            "NoneType": {
                "pattern": r"'NoneType' object has no attribute",
                "fix": "Add null check before attribute access",
                "field_type": "null_reference",
            },
        },
    }

    # Type errors
    TYPE_ERRORS = {
        "TypeError": {
            "missing argument": {
                "pattern": r"missing \d+ required.*argument",
                "fix": "Add missing argument to function call",
                "field_type": "missing_argument",
            },
            "unexpected argument": {
                "pattern": r"got an unexpected keyword argument '(\w+)'",
                "fix": "Remove unexpected argument or fix function signature",
                "field_type": "unexpected_argument",
            },
            "subscriptable": {
                "pattern": r"not subscriptable|object is not iterable",
                "fix": "Add proper type check or fix return type",
                "field_type": "type_error",
            },
        },
    }

    # Name errors
    NAME_ERRORS = {
        "NameError": {
            "not defined": {
                "pattern": r"name '(\w+)' is not defined",
                "fix": "Add import or define variable before use",
                "field_type": "undefined_name",
            },
        },
    }

    # HTTP errors (when Python exception wasn't extracted)
    HTTP_ERRORS = {
        "HTTP_500": {
            "internal_server_error": {
                "pattern": r"Internal Server Error|500",
                "fix": "Check server logs for actual exception - likely database or logic error",
                "field_type": "server_error",
            },
            "database_related": {
                "pattern": r"database|constraint|integrity|duplicate|foreign key",
                "fix": "Check database constraints and relationships",
                "field_type": "database_error",
            },
            "model_validation": {
                "pattern": r"model_dump|pydantic|validation",
                "fix": "Fix Pydantic model conversion - likely double model_dump()",
                "field_type": "model_error",
            },
        },
        "HTTP_404": {
            "not_found": {
                "pattern": r"Not Found|404|detail.*not found",
                "fix": "Add missing route or check endpoint path",
                "field_type": "missing_route",
            },
            "resource_not_found": {
                "pattern": r"not found|does not exist|no .* with",
                "fix": "Ensure resource exists before access or return proper 404",
                "field_type": "resource_not_found",
            },
        },
        "HTTP_422": {
            "validation_error": {
                "pattern": r"Unprocessable Entity|422|validation error",
                "fix": "Fix request schema to match endpoint expectations",
                "field_type": "request_validation",
            },
            "missing_field": {
                "pattern": r"field required|missing|required",
                "fix": "Add required field to request body or make optional",
                "field_type": "missing_required",
            },
            "type_error": {
                "pattern": r"type.*expected|invalid.*type|not a valid",
                "fix": "Fix field type in request schema",
                "field_type": "type_mismatch",
            },
        },
        "HTTPDetail": {
            "generic_detail": {
                "pattern": r"detail|message",
                "fix": "Check HTTP response detail for specific error",
                "field_type": "http_detail",
            },
        },
        "ConnectionError": {
            "connection_refused": {
                "pattern": r"connection refused|connect|ECONNREFUSED",
                "fix": "Ensure server is running and port is correct",
                "field_type": "connection_error",
            },
        },
        "TimeoutError": {
            "request_timeout": {
                "pattern": r"timeout|timed out",
                "fix": "Increase timeout or optimize endpoint performance",
                "field_type": "timeout_error",
            },
        },
    }

    @classmethod
    def get_all_patterns(cls) -> Dict[str, Dict]:
        """Get all error patterns combined."""
        return {
            **cls.DATABASE_ERRORS,
            **cls.VALIDATION_ERRORS,
            **cls.IMPORT_ERRORS,
            **cls.ATTRIBUTE_ERRORS,
            **cls.TYPE_ERRORS,
            **cls.NAME_ERRORS,
            **cls.HTTP_ERRORS,
        }


# =============================================================================
# Smoke Feedback Classifier
# =============================================================================


class SmokeFeedbackClassifier:
    """
    Classifies smoke test failures and maps them to IR context.

    Flow:
        Smoke Error → (entity, endpoint, field, constraint) → GenerationAntiPattern

    Used by FeedbackCollector to create anti-patterns from smoke failures.
    """

    ERROR_TYPE_MAP = {
        # Database errors
        "IntegrityError": "database",
        "OperationalError": "database",
        "ProgrammingError": "database",
        # Validation errors
        "ValidationError": "validation",
        "RequestValidationError": "validation",
        # Import errors
        "ImportError": "import",
        "ModuleNotFoundError": "import",
        # Standard Python errors
        "AttributeError": "attribute",
        "TypeError": "type",
        "NameError": "name",
        "KeyError": "key",
        "ValueError": "value",
        "RuntimeError": "runtime",
        "SyntaxError": "syntax",
        "IndentationError": "syntax",
        # HTTP errors (status codes mapped to types)
        "HTTP_500": "http_500",
        "HTTP_404": "http_404",
        "HTTP_422": "http_422",
        "HTTPException": "http",
        "HTTPDetail": "http_detail",
        # Network errors
        "ConnectionError": "connection",
        "TimeoutError": "timeout",
    }

    def __init__(self, min_confidence: float = 0.3):
        """
        Initialize classifier.

        Args:
            min_confidence: Minimum confidence to create anti-pattern
        """
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(f"{__name__}.SmokeFeedbackClassifier")
        self._patterns = ErrorPatterns.get_all_patterns()

    def classify_for_generation(
        self,
        violation: Dict[str, Any],
        stack_trace: str,
        application_ir: Any,
    ) -> Optional[GenerationAntiPattern]:
        """
        Create anti-pattern from smoke failure.

        Args:
            violation: Dict with error info from RuntimeSmokeValidator
            stack_trace: Full stack trace from server logs
            application_ir: ApplicationIR with entities/endpoints

        Returns:
            GenerationAntiPattern if classifiable, None otherwise
        """
        # 1. Classify the error
        classification = self._classify_error(violation, stack_trace)

        if not classification.classifiable:
            self.logger.debug(f"Error not classifiable: {violation.get('error_type')}")
            return None

        # Bug #204: Enrich IR context BEFORE confidence check
        # The violation has endpoint info that can boost confidence
        ir_context = self._enrich_ir_context(
            classification.ir_context,
            violation,
            application_ir
        )

        # Now check confidence after enrichment
        if ir_context.confidence < self.min_confidence:
            self.logger.debug(
                f"Low confidence ({ir_context.confidence:.2f}): "
                f"{violation.get('error_type')}"
            )
            return None

        # 3. Create anti-pattern
        pattern = create_anti_pattern(
            error_type=classification.error_type,
            exception_class=classification.exception_class,
            entity_pattern=ir_context.entity_name,
            endpoint_pattern=ir_context.endpoint_pattern,
            field_pattern=ir_context.field_name,
            error_message_pattern=classification.error_message_pattern,
            bad_code_snippet=self._extract_bad_code(violation, stack_trace),
            correct_code_snippet=classification.suggested_fix,
        )

        self.logger.info(
            f"Created anti-pattern: {pattern.pattern_id} "
            f"({classification.exception_class} on {ir_context.entity_name})"
        )

        return pattern

    def _classify_error(
        self,
        violation: Dict[str, Any],
        stack_trace: str
    ) -> ErrorClassification:
        """Classify error type and extract patterns."""
        error_type_raw = violation.get("error_type")

        # If no error_type, infer from actual_status (HTTP code)
        if not error_type_raw:
            actual_status = violation.get("actual_status")
            if actual_status:
                # Convert HTTP status to error type: 500 → "HTTP_500"
                error_type_raw = f"HTTP_{actual_status}"
            else:
                error_type_raw = "Unknown"

        error_message = violation.get("error_message", "") or ""

        # Normalize exception class
        exception_class = self._normalize_exception_class(error_type_raw, error_message)

        # Get error type category
        error_type = self.ERROR_TYPE_MAP.get(exception_class, "unknown")

        # Try to match sub-patterns
        sub_pattern_info = self._match_sub_pattern(exception_class, error_message)

        # Extract IR context from error
        ir_context = self._extract_ir_context_from_error(
            exception_class,
            error_message,
            stack_trace,
            sub_pattern_info
        )

        # Generate suggested fix
        suggested_fix = sub_pattern_info.get("fix", "Review and fix the error")

        return ErrorClassification(
            error_type=error_type,
            exception_class=exception_class,
            error_message_pattern=self._extract_message_pattern(error_message),
            ir_context=ir_context,
            suggested_fix=suggested_fix,
            classifiable=error_type != "unknown",
        )

    def _normalize_exception_class(
        self,
        error_type: str,
        error_message: str
    ) -> str:
        """Normalize exception class name."""
        # Sometimes error_type is the full class path
        if "." in error_type:
            error_type = error_type.split(".")[-1]

        # Handle common variations
        if error_type in ["runtime_error", "RuntimeError"]:
            # Try to extract actual exception from message
            match = re.search(r"(\w+Error|\w+Exception):", error_message)
            if match:
                return match.group(1)

        if error_type in self._patterns:
            return error_type

        # Try to find in message
        for known_exc in self._patterns.keys():
            if known_exc.lower() in error_message.lower():
                return known_exc

        return error_type

    def _match_sub_pattern(
        self,
        exception_class: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Match error message against known sub-patterns."""
        if exception_class not in self._patterns:
            return {}

        sub_patterns = self._patterns[exception_class]

        for sub_name, sub_info in sub_patterns.items():
            pattern = sub_info.get("pattern", "")
            if re.search(pattern, error_message, re.IGNORECASE):
                return sub_info

        return {}

    def _extract_ir_context_from_error(
        self,
        exception_class: str,
        error_message: str,
        stack_trace: str,
        sub_pattern_info: Dict[str, Any]
    ) -> IRContext:
        """Extract IR context (entity, field, etc.) from error details."""
        context = IRContext()

        # Bug #204: HTTP errors get base confidence - endpoint always provides context
        # 404 and 422 are more valuable (actionable) than 500
        if exception_class.startswith("HTTP_"):
            if exception_class in ("HTTP_404", "HTTP_422"):
                context.confidence = 0.2  # Will be boosted by endpoint in _enrich_ir_context
            else:
                context.confidence = 0.15  # 500s need more evidence
        elif exception_class in ("ConnectionError", "TimeoutError", "HTTPDetail"):
            context.confidence = 0.25

        # Try to extract entity from error message
        entity_patterns = [
            r"table[:\s]+['\"]?(\w+)['\"]?",
            r"model[:\s]+['\"]?(\w+)['\"]?",
            r"constraint failed: (\w+)\.",
            r"'(\w+)' object",
        ]

        for pattern in entity_patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                context.entity_name = self._normalize_entity_name(match.group(1))
                context.confidence += 0.3
                break

        # Try to extract field from error message
        field_patterns = [
            r"\.(\w+)\s*$",  # table.field at end
            r"column[:\s]+['\"]?(\w+)['\"]?",
            r"field[:\s]+['\"]?(\w+)['\"]?",
            r"attribute '(\w+)'",
            r"argument '(\w+)'",
        ]

        for pattern in field_patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                context.field_name = match.group(1)
                context.confidence += 0.2
                break

        # Extract constraint type from sub_pattern_info
        if sub_pattern_info.get("field_type"):
            context.constraint_type = sub_pattern_info["field_type"]
            context.confidence += 0.2

        # Try to extract endpoint from stack trace
        endpoint_patterns = [
            r"routes/(\w+)\.py",
            r"/api/[^/]+/(\w+)",
            r"@router\.\w+\(['\"]([^'\"]+)['\"]",
        ]

        for pattern in endpoint_patterns:
            match = re.search(pattern, stack_trace)
            if match:
                resource = match.group(1)
                context.endpoint_pattern = f"/{resource}"
                context.confidence += 0.2
                break

        # Normalize confidence
        context.confidence = min(context.confidence, 1.0)

        return context

    def _enrich_ir_context(
        self,
        context: IRContext,
        violation: Dict[str, Any],
        application_ir: Any
    ) -> IRContext:
        """Enrich IR context with information from ApplicationIR and violation."""
        # Always extract endpoint from violation (even without IR)
        endpoint_str = violation.get("endpoint", "")
        if endpoint_str:
            parts = endpoint_str.split(" ", 1)
            if len(parts) == 2:
                method, path = parts
                context.endpoint_pattern = f"{method} {path}"
                context.confidence += 0.1  # Endpoint gives context

        # Extract entity from endpoint if not already set
        if context.entity_name == "*" and endpoint_str:
            entity_name = self._extract_entity_from_endpoint(endpoint_str)
            if entity_name:
                context.entity_name = entity_name
                context.confidence += 0.1  # Entity inferred from endpoint

        # Early return if no IR to enrich further
        if application_ir is None:
            context.confidence = min(context.confidence, 1.0)
            return context

        # Try to verify entity exists in IR (more confidence if verified)
        if context.entity_name != "*":
            try:
                entities = application_ir.get_entities()
                for entity in entities:
                    if hasattr(entity, 'name') and entity.name.lower() == context.entity_name.lower():
                        context.entity_name = entity.name  # Use canonical name
                        context.confidence += 0.1  # Entity verified in IR
                        break
            except Exception:
                pass

        # Normalize confidence
        context.confidence = min(context.confidence, 1.0)

        return context

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # "POST /products" → "Product"
        # "PUT /users/{id}" → "User"

        # Remove method
        path = endpoint.split(" ")[-1]

        # Get first path segment
        parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]

        if parts:
            resource = parts[0]
            # Singularize and capitalize
            if resource.endswith("s"):
                resource = resource[:-1]
            return resource.title()

        return None

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name (singular, title case)."""
        # Remove common prefixes/suffixes
        name = re.sub(r'^tbl_?', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_table$', '', name, flags=re.IGNORECASE)

        # Singularize simple cases
        if name.lower().endswith("ies"):
            name = name[:-3] + "y"
        elif name.lower().endswith("es") and not name.lower().endswith("ses"):
            name = name[:-2]
        elif name.lower().endswith("s") and not name.lower().endswith("ss"):
            name = name[:-1]

        return name.title()

    def _extract_message_pattern(self, message: str) -> str:
        """Extract key pattern from error message (for matching)."""
        # Truncate to key part
        if len(message) > 200:
            message = message[:200]

        # Remove specific IDs/values but keep structure
        message = re.sub(r'\d{4,}', 'N', message)
        message = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'UUID',
            message,
            flags=re.IGNORECASE
        )

        return message.strip()

    def _extract_bad_code(
        self,
        violation: Dict[str, Any],
        stack_trace: str
    ) -> str:
        """Extract example of bad code from stack trace."""
        # Try to find the relevant line from stack trace
        lines = stack_trace.split("\n")

        for i, line in enumerate(lines):
            # Look for the actual code line (usually after "File" line)
            if "File" in line and ".py" in line:
                # Next line might be the code
                if i + 1 < len(lines):
                    code_line = lines[i + 1].strip()
                    if code_line and not code_line.startswith("File"):
                        return code_line[:200]

        # Fallback: use fix_hint from violation
        return violation.get("fix_hint", "")[:200]

    # =========================================================================
    # Batch Processing
    # =========================================================================

    def classify_violations(
        self,
        violations: List[Dict[str, Any]],
        stack_traces: List[Dict[str, Any]],
        application_ir: Any
    ) -> List[GenerationAntiPattern]:
        """
        Classify multiple violations into anti-patterns.

        Args:
            violations: List of violation dicts from RuntimeSmokeValidator
            stack_traces: List of stack trace dicts
            application_ir: ApplicationIR

        Returns:
            List of GenerationAntiPattern objects
        """
        patterns = []
        stack_trace_map = self._build_stack_trace_map(stack_traces)

        for violation in violations:
            endpoint = violation.get("endpoint", "")
            stack_trace = stack_trace_map.get(endpoint, "")

            pattern = self.classify_for_generation(
                violation=violation,
                stack_trace=stack_trace,
                application_ir=application_ir,
            )

            if pattern:
                patterns.append(pattern)

        self.logger.info(
            f"Classified {len(violations)} violations → "
            f"{len(patterns)} anti-patterns"
        )

        return patterns

    def _build_stack_trace_map(
        self,
        stack_traces: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Build endpoint → stack_trace mapping."""
        trace_map = {}

        for st in stack_traces:
            endpoint = st.get("endpoint", "")
            trace = st.get("trace", st.get("stack_trace", ""))

            if endpoint:
                trace_map[endpoint] = trace

        return trace_map


# =============================================================================
# Singleton Instance
# =============================================================================

_smoke_feedback_classifier: Optional[SmokeFeedbackClassifier] = None


def get_smoke_feedback_classifier() -> SmokeFeedbackClassifier:
    """Get singleton instance of SmokeFeedbackClassifier."""
    global _smoke_feedback_classifier
    if _smoke_feedback_classifier is None:
        _smoke_feedback_classifier = SmokeFeedbackClassifier()
    return _smoke_feedback_classifier
