"""
Semantic Task Signatures (STS)

Core component for capturing the essence of atomic code generation tasks.
Enables pattern matching, reuse, and deterministic code generation.

Spec Reference: Section 3.1 - Semantic Task Signatures
Target Coverage: >90% (TDD approach)
"""

import hashlib
import inspect
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


class SemanticTaskSignature(BaseModel):
    """
    Semantic Task Signature - Essence of an atomic code generation task.

    Captures task purpose, inputs, outputs, constraints, and domain classification
    to enable semantic pattern matching and intelligent code reuse.

    **Design Principles**:
    - Deterministic hashing for consistent pattern lookup
    - Rich semantic metadata for accurate matching
    - Validation to ensure data quality
    - Auto-classification support for domain inference

    **Example Usage**:
    ```python
    # Create a signature for email validation task
    signature = SemanticTaskSignature(
        purpose="Validate user email format",
        intent="validate",
        inputs={"email": "str"},
        outputs={"is_valid": "bool", "error_message": "Optional[str]"},
        domain="authentication",
        constraints=["RFC 5322 compliant", "Max length 254 chars"],
        security_level="medium",
        performance_tier="fast",
        idempotency=True,
    )

    # Compute semantic hash
    sig_hash = compute_semantic_hash(signature)

    # Compare with another signature
    similarity = similarity_score(signature, other_signature)
    ```

    **Specification Compliance**:
    - Hash algorithm: SHA256 (deterministic, collision-resistant)
    - Similarity scoring: Multi-factor weighted (purpose 40%, I/O 30%, domain 20%, constraints 10%)
    - Auto-classification: Keyword-based domain inference
    """

    purpose: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Clear description of what the task accomplishes (1-500 chars)",
    )

    intent: str = Field(
        ...,
        description=(
            "Primary action/operation type. "
            "Values: create, read, update, delete, validate, transform, calculate, query, execute"
        ),
    )

    inputs: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Input parameters with types. "
            "Format: {'param_name': 'type_annotation'} "
            "Example: {'user_id': 'UUID', 'email': 'str'}"
        ),
    )

    outputs: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Output values with types. "
            "Format: {'output_name': 'type_annotation'} "
            "Example: {'is_valid': 'bool', 'user_data': 'dict'}"
        ),
    )

    domain: str = Field(
        ...,
        description=(
            "Task domain classification. "
            "Values: authentication, authorization, data_processing, api, database, "
            "ui, testing, infrastructure, financial, general, or 'auto' for auto-classification"
        ),
    )

    constraints: List[str] = Field(
        default_factory=list,
        description=(
            "Technical constraints, requirements, or rules. "
            "Example: ['Thread-safe', 'Max execution time 5s', 'RFC 5322 compliant']"
        ),
    )

    security_level: str = Field(
        default="low",
        description=(
            "Security sensitivity level. "
            "Values: low (public data), medium (user data), high (sensitive data), critical (PII/financial)"
        ),
    )

    performance_tier: str = Field(
        default="standard",
        description=(
            "Performance requirements. "
            "Values: fast (<100ms), standard (<1s), slow (>1s), batch (async ok)"
        ),
    )

    idempotency: bool = Field(
        default=False,
        description=(
            "Whether repeated executions with same inputs produce same results. "
            "True for pure functions, False for side effects"
        ),
    )

    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Reject unknown fields
        validate_assignment = True  # Validate on attribute assignment

    @validator("purpose")
    def purpose_not_empty(cls, v):
        """Validate purpose is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("purpose cannot be empty or whitespace-only")
        return v.strip()

    @validator("intent")
    def intent_valid_action(cls, v):
        """Validate intent is a recognized action verb."""
        valid_intents = [
            "create", "read", "update", "delete",  # CRUD
            "validate", "transform", "calculate",  # Processing
            "query", "execute", "retrieve",  # Operations
        ]
        if v.lower() not in valid_intents:
            # Allow but warn - don't be too strict
            pass
        return v.lower()

    @validator("domain")
    def domain_auto_classify(cls, v, values):
        """Auto-classify domain if set to 'auto'."""
        if v == "auto":
            # Auto-classify based on purpose keywords
            purpose = values.get("purpose", "").lower()

            # Domain classification keywords
            domain_keywords = {
                "authentication": ["login", "auth", "password", "credential", "verify"],
                "authorization": ["permission", "role", "access", "grant", "deny"],
                "database": ["query", "table", "record", "database", "sql", "orm"],
                "api": ["request", "response", "endpoint", "http", "rest", "graphql"],
                "ui": ["component", "render", "view", "template", "display"],
                "data_processing": ["transform", "parse", "convert", "process", "format"],
                "financial": ["payment", "transaction", "price", "cost", "invoice"],
                "testing": ["test", "assert", "mock", "verify", "validate"],
                "infrastructure": ["deploy", "container", "server", "network", "config"],
            }

            # Find matching domain
            for domain_name, keywords in domain_keywords.items():
                if any(keyword in purpose for keyword in keywords):
                    return domain_name

            return "general"  # Default fallback

        return v

    @validator("security_level")
    def security_level_valid(cls, v):
        """Validate security level is recognized."""
        valid_levels = ["low", "medium", "high", "critical"]
        if v not in valid_levels:
            raise ValueError(f"security_level must be one of {valid_levels}, got: {v}")
        return v

    @validator("performance_tier")
    def performance_tier_valid(cls, v):
        """Validate performance tier is recognized."""
        valid_tiers = ["fast", "standard", "slow", "batch"]
        if v not in valid_tiers:
            raise ValueError(f"performance_tier must be one of {valid_tiers}, got: {v}")
        return v


def compute_semantic_hash(signature: SemanticTaskSignature) -> str:
    """
    Compute deterministic SHA256 hash of semantic signature.

    Hash is based on sorted combination of core semantic fields:
    - purpose (primary semantic meaning)
    - inputs (parameter types and names)
    - outputs (return types and names)
    - security_level (affects implementation)
    - performance_tier (affects approach)

    **Properties**:
    - Deterministic: Same signature → same hash
    - Collision-resistant: Different signatures → different hashes (high probability)
    - Stable: Hash doesn't change across runs or platforms

    **Args**:
        signature: SemanticTaskSignature instance

    **Returns**:
        64-character hexadecimal SHA256 hash string

    **Example**:
    ```python
    sig = SemanticTaskSignature(
        purpose="Validate email",
        intent="validate",
        inputs={"email": "str"},
        outputs={"is_valid": "bool"},
        domain="auth",
    )
    hash_value = compute_semantic_hash(sig)  # e.g., "3f4a2c..."
    ```
    """
    # Sort inputs and outputs for determinism
    sorted_inputs = sorted(signature.inputs.items())
    sorted_outputs = sorted(signature.outputs.items())

    # Create hash input string with sorted fields
    hash_input = "|".join([
        signature.purpose,
        signature.intent,
        str(sorted_inputs),
        str(sorted_outputs),
        signature.security_level,
        signature.performance_tier,
    ])

    # Compute SHA256 hash
    hash_object = hashlib.sha256(hash_input.encode('utf-8'))
    return hash_object.hexdigest()


def similarity_score(sig1: SemanticTaskSignature, sig2: SemanticTaskSignature) -> float:
    """
    Compute semantic similarity score between two signatures.

    **Scoring Algorithm**:
    - Purpose similarity: 40% weight (Jaccard text similarity)
    - I/O similarity: 30% weight (key overlap ratio)
    - Domain similarity: 20% weight (exact match = 1.0, different = 0.5)
    - Constraints similarity: 10% weight (common / total)

    **Args**:
        sig1: First SemanticTaskSignature
        sig2: Second SemanticTaskSignature

    **Returns**:
        Similarity score in range [0.0, 1.0]
        - 1.0 = identical signatures
        - 0.7-0.9 = very similar (likely reusable)
        - 0.5-0.7 = moderately similar
        - 0.0-0.5 = different signatures

    **Example**:
    ```python
    score = similarity_score(email_validation_sig, phone_validation_sig)
    if score >= 0.85:  # Threshold from settings
        print("Patterns likely reusable")
    ```
    """
    # 1. Purpose similarity (40% weight) - Jaccard text similarity
    purpose1_words = set(sig1.purpose.lower().split())
    purpose2_words = set(sig2.purpose.lower().split())

    if purpose1_words or purpose2_words:
        purpose_similarity = len(purpose1_words & purpose2_words) / len(purpose1_words | purpose2_words)
    else:
        purpose_similarity = 1.0  # Both empty

    # 2. I/O similarity (30% weight) - Key overlap ratio
    input1_keys = set(sig1.inputs.keys())
    input2_keys = set(sig2.inputs.keys())
    output1_keys = set(sig1.outputs.keys())
    output2_keys = set(sig2.outputs.keys())

    all_keys1 = input1_keys | output1_keys
    all_keys2 = input2_keys | output2_keys

    if all_keys1 or all_keys2:
        io_similarity = len(all_keys1 & all_keys2) / len(all_keys1 | all_keys2)
    else:
        io_similarity = 1.0  # Both empty

    # 3. Domain similarity (20% weight) - Exact match or partial
    if sig1.domain == sig2.domain:
        domain_similarity = 1.0
    else:
        domain_similarity = 0.5  # Different domains still have some baseline similarity

    # 4. Constraints similarity (10% weight) - Common constraints / total constraints
    constraints1 = set(sig1.constraints)
    constraints2 = set(sig2.constraints)

    if constraints1 or constraints2:
        constraints_similarity = len(constraints1 & constraints2) / len(constraints1 | constraints2)
    else:
        constraints_similarity = 1.0  # Both empty

    # Weighted sum
    total_similarity = (
        purpose_similarity * 0.40 +
        io_similarity * 0.30 +
        domain_similarity * 0.20 +
        constraints_similarity * 0.10
    )

    return round(total_similarity, 3)


def extract_io_types_from_function(func: Callable) -> tuple[Dict[str, str], Dict[str, str]]:
    """
    Extract input and output type annotations from Python function.

    Uses introspection to parse function signature and return type.

    **Args**:
        func: Python function or method

    **Returns**:
        Tuple of (inputs_dict, outputs_dict)
        - inputs_dict: {param_name: type_string}
        - outputs_dict: {return: type_string} or {}

    **Example**:
    ```python
    def validate_email(email: str, strict: bool = False) -> bool:
        return "@" in email

    inputs, outputs = extract_io_types_from_function(validate_email)
    # inputs = {"email": "str", "strict": "bool"}
    # outputs = {"return": "bool"}
    ```
    """
    # Get function signature
    sig = inspect.signature(func)

    # Extract input parameters and types
    inputs = {}
    for param_name, param in sig.parameters.items():
        if param_name == "self" or param_name == "cls":
            continue  # Skip class/instance parameters

        if param.annotation != inspect.Parameter.empty:
            # Get type annotation as string
            type_str = (
                param.annotation.__name__
                if hasattr(param.annotation, "__name__")
                else str(param.annotation)
            )
            inputs[param_name] = type_str
        else:
            inputs[param_name] = "Any"  # No annotation

    # Extract return type
    outputs = {}
    if sig.return_annotation != inspect.Signature.empty:
        return_type_str = (
            sig.return_annotation.__name__
            if hasattr(sig.return_annotation, "__name__")
            else str(sig.return_annotation)
        )
        outputs["return"] = return_type_str

    return inputs, outputs


def from_atomic_unit(atomic_unit: Any) -> SemanticTaskSignature:
    """
    Extract SemanticTaskSignature from AtomicUnit database object.

    Performs intelligent extraction and inference:
    - Purpose from description
    - Intent from action verbs (create, validate, transform, etc.)
    - Inputs/outputs from code_snippet (if available)
    - Domain from keyword matching

    **Args**:
        atomic_unit: AtomicUnit object from masterplan_subtasks table
            Required fields: description
            Optional fields: code_snippet

    **Returns**:
        SemanticTaskSignature instance

    **Example**:
    ```python
    atomic_unit = session.query(AtomicUnit).first()
    signature = from_atomic_unit(atomic_unit)
    ```
    """
    # Extract purpose from description
    purpose = atomic_unit.description.strip()

    # Infer intent from action verbs in description
    intent_verbs = {
        "create": "create",
        "build": "create",
        "generate": "create",
        "validate": "validate",
        "verify": "validate",
        "check": "validate",
        "transform": "transform",
        "convert": "transform",
        "parse": "transform",
        "delete": "delete",
        "remove": "delete",
        "update": "update",
        "modify": "update",
        "retrieve": "retrieve",
        "fetch": "retrieve",
        "get": "retrieve",
        "calculate": "calculate",
        "compute": "calculate",
    }

    intent = "execute"  # Default fallback
    purpose_lower = purpose.lower()
    for verb, intent_type in intent_verbs.items():
        if purpose_lower.startswith(verb):
            intent = intent_type
            break

    # Extract inputs/outputs from code if available
    inputs = {}
    outputs = {}

    if hasattr(atomic_unit, 'code_snippet') and atomic_unit.code_snippet:
        try:
            # Try to parse code as function definition
            code_lines = atomic_unit.code_snippet.strip().split('\n')
            if code_lines and 'def ' in code_lines[0]:
                # Extract function signature line
                func_line = code_lines[0]

                # Simple regex-like parsing for common cases
                # Example: "def func(email: str, age: int) -> bool:"
                if '(' in func_line and ')' in func_line:
                    params_str = func_line.split('(')[1].split(')')[0]

                    # Parse parameters
                    for param in params_str.split(','):
                        param = param.strip()
                        if ':' in param:
                            name, type_hint = param.split(':', 1)
                            inputs[name.strip()] = type_hint.strip()

                # Parse return type
                if '->' in func_line:
                    return_type = func_line.split('->')[1].split(':')[0].strip()
                    outputs['return'] = return_type

        except Exception:
            # Parsing failed, leave inputs/outputs empty
            pass

    # Auto-classify domain (will use validator)
    domain = "auto"

    # Create signature
    signature = SemanticTaskSignature(
        purpose=purpose,
        intent=intent,
        inputs=inputs,
        outputs=outputs,
        domain=domain,
        constraints=[],
        security_level="low",
        performance_tier="standard",
        idempotency=False,
    )

    return signature
