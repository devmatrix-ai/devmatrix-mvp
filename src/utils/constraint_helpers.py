"""
Constraint normalization utilities.

Handles the inconsistency between constraints being stored as list or dict
across different parts of the codebase.
"""
from typing import Any, Dict


def normalize_constraints(raw: Any) -> Dict[str, Any]:
    """
    Normalize constraints to dict format.

    The codebase has inconsistent constraint formats:
    - Some places use dict: {"gt": 0, "required": True}
    - Some places use list: ["gt=0", "required"]

    This function normalizes both to dict format for consistent access.

    Args:
        raw: Constraints in any format (None, dict, list of strings)

    Returns:
        Dict with normalized constraints

    Examples:
        >>> normalize_constraints(None)
        {}
        >>> normalize_constraints({"gt": 0})
        {"gt": 0}
        >>> normalize_constraints(["gt=0", "required"])
        {"gt": "0", "required": True}
        >>> normalize_constraints(["min_length=1", "max_length=255"])
        {"min_length": "1", "max_length": "255"}
    """
    if raw is None:
        return {}

    if isinstance(raw, dict):
        return raw

    if isinstance(raw, list):
        result = {}
        for item in raw:
            if isinstance(item, str):
                if "=" in item:
                    # Handle "key=value" format
                    key, val = item.split("=", 1)
                    # Try to convert numeric values
                    try:
                        if "." in val:
                            result[key] = float(val)
                        else:
                            result[key] = int(val)
                    except ValueError:
                        result[key] = val
                else:
                    # Handle bare constraint names like "required", "unique"
                    result[item] = True
            elif isinstance(item, dict):
                # Handle list of dicts (merge them)
                result.update(item)
        return result

    # Fallback for unknown types
    return {}
