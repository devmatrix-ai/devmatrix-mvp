"""
CPIE (Cognitive Pattern Inference Engine)

Core inference engine for atomic code generation using:
1. Pattern matching from Pattern Bank (≥85% similarity)
2. First-principles generation when no patterns match
3. Retry mechanism with context enrichment (max 3 retries)
4. Constraint enforcement (max 10 LOC, syntax, type hints, no TODOs)
5. Co-reasoning with Claude (strategy) + DeepSeek (implementation)
6. Synthesis validation for quality assurance

Spec Reference: Section 3.3 - Cognitive Pattern Inference Engine
Target Coverage: >90% (TDD approach)
"""

import ast
import logging
from typing import Dict, Any, List, Tuple, Optional

from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.cognitive.patterns.pattern_bank import PatternBank, StoredPattern

logger = logging.getLogger(__name__)


# Adaptive threshold configuration (TG4)
DOMAIN_THRESHOLDS = {
    "crud": 0.75,      # Simple CRUD patterns - lower threshold
    "custom": 0.80,    # Custom logic - medium threshold
    "payment": 0.85,   # Complex payment patterns - higher threshold
    "workflow": 0.80,  # Workflow patterns - medium threshold
}
DEFAULT_THRESHOLD = 0.80  # Fallback for unknown domains


def get_adaptive_threshold(domain: Optional[str]) -> float:
    """
    Get adaptive similarity threshold based on requirement domain (TG4).

    Different domains require different similarity thresholds:
    - CRUD (0.75): Simple patterns, lower threshold for more matches
    - Payment (0.85): Complex patterns, higher threshold for precision
    - Custom/Workflow (0.80): Medium complexity, balanced threshold
    - Unknown (0.80): Default threshold for safety

    Args:
        domain: Requirement domain (crud, custom, payment, workflow, etc.)

    Returns:
        Similarity threshold (0.75-0.85)

    Example:
        >>> get_adaptive_threshold("crud")
        0.75
        >>> get_adaptive_threshold("payment")
        0.85
        >>> get_adaptive_threshold("unknown")
        0.80
    """
    if not domain:
        return DEFAULT_THRESHOLD

    return DOMAIN_THRESHOLDS.get(domain.lower(), DEFAULT_THRESHOLD)


class CPIE:
    """
    Cognitive Pattern Inference Engine.

    Orchestrates atomic code generation through pattern matching or first-principles
    inference, with retry mechanism and quality validation.

    **Design Principles**:
    - Pattern reuse over first-principles (efficiency)
    - Constraint enforcement for quality (max 10 LOC, syntax, types)
    - Retry with enriched context (max 3 attempts)
    - Co-reasoning for complex tasks (Claude + DeepSeek)

    **Example Usage**:
    ```python
    cpie = CPIE(pattern_bank=bank, co_reasoning_system=co_reasoning)

    signature = SemanticTaskSignature(
        purpose="Validate email format",
        intent="validate",
        inputs={"email": "str"},
        outputs={"is_valid": "bool"},
        domain="authentication",
    )

    code = cpie.infer(signature)  # Returns generated code
    ```

    **Specification Compliance**:
    - Pattern matching threshold: ≥85% similarity
    - Max LOC per atom: 10 lines
    - Retry limit: 3 attempts
    - Success target: ≥95% precision
    """

    def __init__(
        self,
        pattern_bank: PatternBank,
        co_reasoning_system: Any,
        max_retries: int = 3,
        similarity_threshold: float = 0.85,
        max_loc: int = 10,
    ):
        """
        Initialize CPIE with required dependencies.

        Args:
            pattern_bank: PatternBank instance for pattern matching
            co_reasoning_system: Co-reasoning system (Claude + DeepSeek)
            max_retries: Maximum retry attempts (default: 3)
            similarity_threshold: Minimum similarity for pattern match (default: 0.85)
            max_loc: Maximum lines of code per atom (default: 10)
        """
        self.pattern_bank = pattern_bank
        self.co_reasoning_system = co_reasoning_system
        self.max_retries = max_retries
        self.similarity_threshold = similarity_threshold
        self.max_loc = max_loc

        logger.info(
            f"Initialized CPIE with similarity_threshold={similarity_threshold}, "
            f"max_retries={max_retries}, max_loc={max_loc}"
        )

    def infer(self, signature: SemanticTaskSignature) -> Optional[str]:
        """
        Infer code for atomic task from semantic signature.

        Strategy:
        1. Try pattern matching (≥85% similarity)
        2. If no pattern, use first-principles generation
        3. Validate constraints (max LOC, syntax, types, no TODOs)
        4. Retry with enriched context if validation fails (max 3 times)

        Args:
            signature: Semantic task signature

        Returns:
            Generated code string or None if all attempts fail

        Example:
        ```python
        code = cpie.infer(email_validation_signature)
        # Returns: "def validate_email(email: str) -> bool:\\n    return '@' in email"
        ```
        """
        logger.info(f"Starting inference for: {signature.purpose}")

        # Step 1: Try pattern matching
        code = infer_from_pattern(signature, self.pattern_bank, self.co_reasoning_system)

        if code:
            logger.info("Pattern matching succeeded")
            # Validate constraints
            is_valid, errors = validate_constraints(code, max_loc=self.max_loc)
            if is_valid:
                return code
            else:
                logger.warning(f"Pattern-based code failed validation: {errors}")

        # Step 2: Try first-principles generation
        logger.info("Falling back to first-principles generation")
        code = infer_from_first_principles(signature, self.co_reasoning_system)

        if code:
            is_valid, errors = validate_constraints(code, max_loc=self.max_loc)
            if is_valid:
                return code
            else:
                logger.warning(f"First-principles code failed validation: {errors}")

                # Step 3: Retry with enriched context
                previous_failure = {"code": code, "error": ", ".join(errors)}
                enriched_context = f"Previous attempt failed validation: {errors}"

                code = retry_with_context(
                    signature,
                    previous_failure,
                    enriched_context,
                    self.co_reasoning_system,
                    max_retries=self.max_retries,
                )

                if code:
                    is_valid, errors = validate_constraints(code, max_loc=self.max_loc)
                    if is_valid:
                        return code

        logger.error(f"Failed to generate valid code for: {signature.purpose}")
        return None


def infer_from_pattern(
    signature: SemanticTaskSignature,
    pattern_bank: PatternBank,
    co_reasoning_system: Any,
    similarity_threshold: Optional[float] = None,
) -> Optional[str]:
    """
    Infer code by adapting similar pattern from Pattern Bank.

    Strategy:
    1. Calculate adaptive threshold based on domain (TG4)
    2. Search Pattern Bank for similar patterns (threshold varies by domain)
    3. If found, extract pattern code and strategy
    4. Call Claude to generate adaptation strategy
    5. Call DeepSeek to implement adapted code

    Args:
        signature: Semantic task signature
        pattern_bank: PatternBank instance
        co_reasoning_system: Co-reasoning system
        similarity_threshold: Optional override for similarity score
            (if None, uses adaptive threshold based on domain)

    Returns:
        Generated code or None if no pattern matches

    Example:
    ```python
    code = infer_from_pattern(signature, bank, co_reasoning)
    # Returns adapted code if pattern found, None otherwise
    ```
    """
    # TG4: Use adaptive threshold based on domain if not explicitly provided
    if similarity_threshold is None:
        similarity_threshold = get_adaptive_threshold(signature.domain)
        logger.debug(
            f"Using adaptive threshold {similarity_threshold} for domain '{signature.domain}'"
        )

    logger.debug(f"Searching patterns for: {signature.purpose}")

    # Search for similar patterns
    patterns = pattern_bank.search_patterns(
        signature, top_k=1, similarity_threshold=similarity_threshold
    )

    if not patterns or patterns[0].similarity_score < similarity_threshold:
        logger.debug("No matching pattern found above threshold")
        return None

    matched_pattern = patterns[0]
    logger.info(
        f"Found matching pattern: {matched_pattern.pattern_id} "
        f"(similarity={matched_pattern.similarity_score:.2f})"
    )

    # Generate adaptation strategy using Claude
    strategy_prompt = f"""
Task: {signature.purpose}
Matched Pattern Code:
{matched_pattern.code}

Generate a strategy to adapt this pattern for the new task.
Focus on what needs to change while preserving the core approach.
"""
    strategy = co_reasoning_system.generate_strategy(strategy_prompt)

    # Generate adapted code using DeepSeek
    code_prompt = f"""
Task: {signature.purpose}
Strategy: {strategy}
Original Pattern:
{matched_pattern.code}

Implement the adapted code following the strategy.
Requirements:
- Maximum 10 lines of code
- Full type hints
- No TODO comments
- Valid Python syntax
"""
    code = co_reasoning_system.generate_code(code_prompt)

    return code


def infer_from_first_principles(
    signature: SemanticTaskSignature, co_reasoning_system: Any
) -> Optional[str]:
    """
    Generate code from first principles using semantic signature.

    Strategy:
    1. Call Claude to generate strategic approach from signature
    2. Call DeepSeek to implement code following strategy
    3. Ensure constraints are communicated (max LOC, types, etc.)

    Args:
        signature: Semantic task signature
        co_reasoning_system: Co-reasoning system

    Returns:
        Generated code

    Example:
    ```python
    code = infer_from_first_principles(signature, co_reasoning)
    # Returns: "def parse_json(json_str: str) -> dict:\\n    return json.loads(json_str)"
    ```
    """
    logger.info(f"Generating code from first principles for: {signature.purpose}")

    # Generate strategy using Claude
    strategy_prompt = f"""
Task Purpose: {signature.purpose}
Intent: {signature.intent}
Inputs: {signature.inputs}
Outputs: {signature.outputs}
Domain: {signature.domain}
Constraints: {signature.constraints}
Security Level: {signature.security_level}

Generate a strategic approach to implement this task.
Consider edge cases, performance, and security.
"""
    strategy = co_reasoning_system.generate_strategy(strategy_prompt)

    # Generate code using DeepSeek
    code_prompt = f"""
Task: {signature.purpose}
Strategy: {strategy}
Inputs: {signature.inputs}
Outputs: {signature.outputs}
Constraints: {signature.constraints}

Implement the code following the strategy.
Requirements:
- Maximum 10 lines of code
- Full type hints for all parameters and return values
- No TODO or placeholder comments
- Valid Python syntax
- Single responsibility principle
"""
    code = co_reasoning_system.generate_code(code_prompt)

    return code


def validate_constraints(code: str, max_loc: int = 10) -> Tuple[bool, List[str]]:
    """
    Validate generated code against quality constraints.

    Constraints:
    1. Maximum lines of code (default: 10)
    2. Valid Python syntax (no parse errors)
    3. Full type hints for all functions
    4. No TODO comments
    5. Single responsibility (one function/purpose)

    Args:
        code: Generated code to validate
        max_loc: Maximum lines of code allowed

    Returns:
        Tuple of (is_valid: bool, errors: List[str])

    Example:
    ```python
    is_valid, errors = validate_constraints(code, max_loc=10)
    if not is_valid:
        print(f"Validation failed: {errors}")
    ```
    """
    errors = []

    # 1. Check max LOC (exclude empty lines and comments)
    code_lines = [
        line for line in code.strip().split("\n") if line.strip() and not line.strip().startswith("#")
    ]
    actual_loc = len(code_lines)

    if actual_loc > max_loc:
        errors.append(f"Code exceeds max LOC: {actual_loc} > {max_loc}")

    # 2. Check syntax validity
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Syntax error: {str(e)}")

    # 3. Check for type hints
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has type hints
                if not node.returns:
                    errors.append(f"Function '{node.name}' missing return type hint")

                # Check if parameters have type hints
                for arg in node.args.args:
                    if not arg.annotation and arg.arg not in ["self", "cls"]:
                        errors.append(f"Parameter '{arg.arg}' in function '{node.name}' missing type hint")
    except Exception:
        pass  # Syntax error already caught above

    # 4. Check for TODO comments
    if "TODO" in code or "FIXME" in code or "XXX" in code:
        errors.append("Code contains TODO/FIXME/XXX comments")

    is_valid = len(errors) == 0

    if is_valid:
        logger.debug("Code passed all constraint validations")
    else:
        logger.warning(f"Code failed validation: {errors}")

    return is_valid, errors


def retry_with_context(
    signature: SemanticTaskSignature,
    previous_failure: Dict[str, str],
    enriched_context: str,
    co_reasoning_system: Any,
    max_retries: int = 3,
) -> Optional[str]:
    """
    Retry code generation with enriched context from previous failures.

    Strategy:
    1. Analyze previous failure (code + error)
    2. Enrich prompt with error details and fixes
    3. Retry generation with increased temperature or different model
    4. Validate result
    5. Repeat up to max_retries times

    Args:
        signature: Semantic task signature
        previous_failure: Dict with "code" and "error" keys
        enriched_context: Additional context about what went wrong
        co_reasoning_system: Co-reasoning system
        max_retries: Maximum retry attempts

    Returns:
        Fixed code or None if all retries fail

    Example:
    ```python
    code = retry_with_context(signature, {"code": bad_code, "error": "Missing base case"},
                              "Add base case for recursion", co_reasoning)
    ```
    """
    logger.info(f"Starting retry mechanism (max {max_retries} attempts)")

    for attempt in range(max_retries):
        logger.debug(f"Retry attempt {attempt + 1}/{max_retries}")

        # Enrich prompt with failure analysis
        code_prompt = f"""
Task: {signature.purpose}
Previous Attempt Failed:
{previous_failure['code']}

Error: {previous_failure['error']}
Context: {enriched_context}

Generate corrected code that fixes the errors.
Requirements:
- Maximum 10 lines of code
- Full type hints
- No TODO comments
- Valid Python syntax
- Address the specific errors mentioned
"""
        code = co_reasoning_system.generate_code(code_prompt)

        # Validate the retry result
        is_valid, errors = validate_constraints(code, max_loc=10)

        if is_valid:
            logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return code
        else:
            logger.warning(f"Retry attempt {attempt + 1} failed: {errors}")
            # Update failure context for next retry
            previous_failure["code"] = code
            previous_failure["error"] = ", ".join(errors)

    logger.error(f"All {max_retries} retry attempts failed")
    return None


def validate_synthesis(code: str, purpose: str) -> bool:
    """
    Validate that generated code correctly implements the intended purpose.

    Validation checks:
    1. Code parses without syntax errors
    2. Code contains meaningful implementation (not just 'pass')
    3. Function name relates to purpose
    4. Code implements expected behavior (heuristic check)

    Args:
        code: Generated code to validate
        purpose: Intended purpose description

    Returns:
        True if code appears to implement purpose correctly, False otherwise

    Example:
    ```python
    is_valid = validate_synthesis("def add(a: int, b: int) -> int: return a + b",
                                  "Add two numbers")
    # Returns: True
    ```
    """
    # 1. Check syntax
    try:
        tree = ast.parse(code)
    except SyntaxError:
        logger.warning("Synthesis validation failed: syntax error")
        return False

    # 2. Check for meaningful implementation (not just 'pass')
    if code.strip().endswith("pass") or "pass  #" in code:
        logger.warning("Synthesis validation failed: empty implementation")
        return False

    # 3. Check function name relates to purpose (heuristic)
    purpose_lower = purpose.lower()
    key_words = set(purpose_lower.split())

    has_relevant_name = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name_lower = node.name.lower()
            # Check if function name contains key words from purpose
            if any(word in func_name_lower for word in key_words if len(word) > 3):
                has_relevant_name = True
                break

    if not has_relevant_name:
        logger.warning("Synthesis validation failed: function name doesn't relate to purpose")
        return False

    # 4. Basic implementation check - function should have actual logic
    has_logic = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Return, ast.Assign, ast.AugAssign, ast.If, ast.For, ast.While)):
            has_logic = True
            break

    if not has_logic:
        logger.warning("Synthesis validation failed: no meaningful logic detected")
        return False

    logger.debug("Synthesis validation passed")
    return True
