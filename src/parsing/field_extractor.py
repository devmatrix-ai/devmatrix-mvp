"""
Field Extraction using Regex Patterns

Pass 2: Extracts entity fields from context windows deterministically using regex.
Identifies field names, types, constraints, and enforcement types.
"""

import re
from typing import List, Dict, Optional, Tuple
from src.parsing.hierarchical_models import Field


# Enforcement type keywords
COMPUTED_KEYWORDS = [
    "calculated", "computed", "sum of", "derived from", "aggregated",
    "total", "subtotal", "quantity ×", "unit_price", "amount"
]

IMMUTABLE_KEYWORDS = [
    "immutable", "cannot change", "snapshot at", "captured at", "at time of",
    "never changes", "permanent", "fixed", "created", "original"
]

VALIDATOR_KEYWORDS = [
    "validate", "validation", "must", "requires", "ensure", "verify",
    "check", "sufficient", "unique", "format", "pattern", "constraint"
]


def extract_field_patterns(context_window: str) -> List[Dict[str, any]]:
    """
    Extract field definitions using regex patterns.

    Supports patterns:
    - **field_name** (type) - description
    - **field_name** (type): description
    - **field_name** (type)
    - - **field_name** (type)
    - field_name: type - description

    Args:
        context_window: Text window around entity definition

    Returns:
        List of field definitions as dicts
    """
    fields = []

    # Pattern 1: **field_name** (type) with optional - or : and description
    # Supports all variations of format: with/without description, with - or :
    pattern1 = r"\*\*([a-zA-Z_]\w*)\*\*\s*\(([^)]+)\)(?:\s*[-:]?\s*(.+?))?(?=\n\s*[-•]|\n\s{0,3}[A-Z]|\n\*\*|$)"
    matches1 = re.finditer(pattern1, context_window, re.DOTALL | re.MULTILINE)

    for match in matches1:
        field_name = match.group(1)
        field_type = match.group(2).strip()
        description = (match.group(3).strip() if match.group(3) else "").replace("\n", " ").strip()

        if description:  # Only add if we have meaningful data
            fields.append({
                "name": field_name,
                "type": field_type,
                "description": description,
                "raw_match": match.group(0)
            })

    # Pattern 2: - **field_name** (type) [with bullet point]
    pattern2 = r"^-\s+\*\*([a-zA-Z_]\w*)\*\*\s*\(([^)]+)\)(?:\s*[-:]?\s*(.+?))?(?=\n|$)"
    matches2 = re.finditer(pattern2, context_window, re.DOTALL | re.MULTILINE)

    for match in matches2:
        field_name = match.group(1)
        field_type = match.group(2).strip()
        description = (match.group(3).strip() if match.group(3) else "").replace("\n", " ").strip()

        # Skip if already found
        if not any(f["name"] == field_name for f in fields):
            if field_type:  # Only add if we have type
                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "description": description,
                    "raw_match": match.group(0)
                })

    # Pattern 3: field_name: type - description (colon format)
    pattern3 = r"^-\s+([a-zA-Z_]\w*)\s*\(([^)]+)\)(?:\s*-\s*(.+?))?(?=\n|$)"
    matches3 = re.finditer(pattern3, context_window, re.DOTALL | re.MULTILINE)

    for match in matches3:
        field_name = match.group(1)
        field_type = match.group(2).strip()
        description = (match.group(3).strip() if match.group(3) else "").replace("\n", " ").strip()

        # Skip if already found
        if not any(f["name"] == field_name for f in fields):
            if field_type:  # Only add if we have type
                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "description": description,
                    "raw_match": match.group(0)
                })

    return fields


def infer_field_type(type_str: str, description: str) -> str:
    """
    Infer field type from type string and description.
    Normalizes types to: string, integer, decimal, boolean, datetime, uuid
    """
    type_lower = type_str.lower()
    desc_lower = description.lower()

    # Integer types
    if any(x in type_lower for x in ["int", "integer", "count", "quantity", "number"]):
        return "integer"

    # Decimal/Float types
    if any(x in type_lower for x in ["decimal", "float", "price", "amount", "total", "money"]):
        return "decimal"

    # Boolean types
    if any(x in type_lower for x in ["bool", "boolean", "flag", "active"]):
        return "boolean"

    # Datetime types
    if any(x in type_lower for x in ["datetime", "timestamp", "date", "time", "created", "updated"]):
        return "datetime"

    # UUID types
    if any(x in type_lower for x in ["uuid", "id"]) and len(type_lower) < 10:
        return "uuid"

    # Default to string
    return "string"


def extract_constraints(description: str, field_type: str) -> List[str]:
    """
    Extract constraints from description text.

    Examples:
    - "unique email address" → ["unique"]
    - "1-255 characters" → ["length:1-255"]
    - "positive integer" → ["range:>0"]
    """
    constraints = []
    desc_lower = description.lower()

    # Unique constraint
    if "unique" in desc_lower:
        constraints.append("unique")

    # Required/Not null
    if "required" in desc_lower or "must have" in desc_lower:
        constraints.append("required")

    # Email format
    if "email" in desc_lower:
        constraints.append("pattern:email")

    # Length constraints (e.g., "1-255 characters", "max 100 chars")
    length_match = re.search(r"(\d+)\s*-\s*(\d+)\s*(?:char|length)", desc_lower)
    if length_match:
        constraints.append(f"length:{length_match.group(1)}-{length_match.group(2)}")

    max_match = re.search(r"max(?:imum)?\s+(\d+)", desc_lower)
    if max_match:
        constraints.append(f"max_length:{max_match.group(1)}")

    # Numeric ranges
    if "positive" in desc_lower:
        constraints.append("range:>0")

    if "non-negative" in desc_lower or "zero or more" in desc_lower:
        constraints.append("range:>=0")

    # Numeric range (e.g., "0-100")
    range_match = re.search(r"(\d+)\s*-\s*(\d+)(?!.*char)", desc_lower)
    if range_match and "length" not in constraints:
        constraints.append(f"range:{range_match.group(1)}-{range_match.group(2)}")

    return constraints


def detect_enforcement_type(field_name: str, description: str) -> Tuple[str, Optional[str]]:
    """
    Detect enforcement type: normal, computed, immutable, or validator.

    Returns:
        Tuple of (enforcement_type, enforcement_details)
    """
    desc_lower = description.lower()
    name_lower = field_name.lower()

    # Check for computed fields
    computed_score = sum(1 for keyword in COMPUTED_KEYWORDS if keyword in desc_lower)
    if computed_score >= 1:
        return "computed", description

    # Check for immutable fields
    immutable_score = sum(1 for keyword in IMMUTABLE_KEYWORDS if keyword in desc_lower)
    if immutable_score >= 1:
        # Extract what makes it immutable
        immutable_detail = None
        if "snapshot at" in desc_lower or "captured at" in desc_lower:
            immutable_detail = "Captures value at point in time (purchase/order creation)"
        elif "never" in desc_lower or "cannot" in desc_lower:
            immutable_detail = "Permanently fixed after creation"
        return "immutable", immutable_detail or description

    # Check for validator fields
    validator_score = sum(1 for keyword in VALIDATOR_KEYWORDS if keyword in desc_lower)
    if validator_score >= 1:
        return "validator", description

    # Check for timestamps (implicit immutable)
    if "created" in name_lower or "updated" in name_lower or "_at" in name_lower:
        if "created" in name_lower and "updated" not in name_lower:
            return "immutable", "Timestamp set at record creation"

    return "normal", None


def build_field_objects(raw_fields: List[Dict]) -> List[Field]:
    """
    Convert raw field dicts to Field objects with full analysis.
    """
    fields = []

    for raw_field in raw_fields:
        name = raw_field["name"]
        type_str = raw_field["type"]
        description = raw_field["description"]

        # Infer type
        field_type = infer_field_type(type_str, description)

        # Extract constraints
        constraints = extract_constraints(description, field_type)
        required = "required" in constraints

        # Detect enforcement type
        enforcement_type, enforcement_details = detect_enforcement_type(name, description)

        field = Field(
            name=name,
            type=field_type,
            description=description,
            required=required,
            constraints=constraints,
            enforcement_type=enforcement_type,
            enforcement_details=enforcement_details
        )

        fields.append(field)

    return fields


def extract_entity_fields(entity_name: str, context_window: str) -> List[Field]:
    """
    Complete field extraction pipeline using regex patterns.

    Args:
        entity_name: Name of entity being analyzed
        context_window: Text window around entity definition

    Returns:
        List of Field objects with full analysis
    """
    # Extract raw field patterns
    raw_fields = extract_field_patterns(context_window)

    # Build Field objects with full analysis
    fields = build_field_objects(raw_fields)

    return fields
