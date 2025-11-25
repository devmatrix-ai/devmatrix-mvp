"""
Entity Location and Context Window Extraction

Utilities for finding entity definitions in specifications and extracting
context windows around them for hierarchical LLM extraction.
"""
import re
from typing import Dict, List


def find_entity_locations(spec: str, entity_names: List[str]) -> Dict[str, int]:
    """
    Find character positions of entity definitions in spec.

    Searches for entity definition patterns:
    - Markdown headers: ### Entity Name, ## Entity Name
    - Bold text: **Entity Name**
    - Entity labels: Entity Name:, Entity: Name
    - Table headers: | Entity Name |

    Args:
        spec: Full specification text
        entity_names: List of entity names to locate

    Returns:
        Dictionary mapping entity name to character position in spec.
        Position is start of the entity definition section.
    """
    locations = {}

    for entity_name in entity_names:
        # Escape special regex characters in entity name
        escaped_name = re.escape(entity_name)

        # Pattern 1: Markdown header (### Entity, ## Entity)
        pattern_header = rf"^#{1,6}\s+{escaped_name}\b"

        # Pattern 2: Numbered header with Spanish/English (### 1. Producto (Product))
        pattern_numbered = rf"^#{1,6}\s+\d+\.\s+[^\(]*\(\s*{escaped_name}\s*\)"

        # Pattern 3: Bold text (**Entity**)
        pattern_bold = rf"\*\*{escaped_name}\*\*"

        # Pattern 4: Entity label (Entity:, Entity Name:)
        pattern_label = rf"^{escaped_name}\s*:"

        # Pattern 5: Prefixed label (Entity: Name)
        pattern_prefixed = rf"^Entity:\s*{escaped_name}\b"

        # Pattern 6: Table header (| Entity |)
        pattern_table = rf"\|\s*{escaped_name}\s*\|"

        # Combine all patterns
        combined_pattern = "|".join([
            pattern_header,
            pattern_numbered,  # Added numbered pattern
            pattern_bold,
            pattern_label,
            pattern_prefixed,
            pattern_table
        ])

        # Search for entity definition (case-insensitive, multiline)
        match = re.search(combined_pattern, spec, re.IGNORECASE | re.MULTILINE)

        if match:
            locations[entity_name] = match.start()

    return locations


def extract_context_window(spec: str, location: int, window: int = 2000) -> str:
    """
    Extract text window around entity definition.

    Extracts ±window characters around the entity location, ensuring
    the extracted context includes:
    - Entity definition and description
    - Field definitions
    - Related entities mentioned nearby
    - Business logic constraints

    Args:
        spec: Full specification text
        location: Character position of entity definition
        window: Number of characters to extract before/after location (default: 2000)

    Returns:
        Text window around entity definition, trimmed to complete sentences.
    """
    spec_len = len(spec)

    # Calculate window boundaries
    start = max(0, location - window)
    end = min(spec_len, location + window)

    # Extract raw window
    raw_window = spec[start:end]

    # Trim to complete sentences at boundaries
    # Start: Find first newline or sentence boundary
    if start > 0:
        # Find first double newline (paragraph boundary) or single newline
        first_newline = raw_window.find("\n")
        if first_newline != -1 and first_newline < 200:  # Only trim if within 200 chars
            raw_window = raw_window[first_newline + 1:]

    # End: Find last complete sentence or paragraph
    if end < spec_len:
        # Find last double newline (paragraph boundary)
        last_double_newline = raw_window.rfind("\n\n")
        if last_double_newline != -1 and last_double_newline > len(raw_window) - 200:
            raw_window = raw_window[:last_double_newline]
        else:
            # Find last single newline
            last_newline = raw_window.rfind("\n")
            if last_newline != -1 and last_newline > len(raw_window) - 200:
                raw_window = raw_window[:last_newline]

    return raw_window.strip()


def extract_entity_context_windows(
    spec: str,
    global_context,  # GlobalContext from hierarchical_models
    window: int = 2000
) -> Dict[str, str]:
    """
    Extract context windows for all entities using global context.

    Args:
        spec: Full specification text
        global_context: GlobalContext object from Pass 1
        window: Context window size (default: 2000 chars)

    Returns:
        Dictionary mapping entity name to context window text
    """
    entity_windows = {}

    for entity_summary in global_context.entities:
        location = entity_summary.location
        entity_windows[entity_summary.name] = extract_context_window(
            spec, location, window
        )

    return entity_windows
