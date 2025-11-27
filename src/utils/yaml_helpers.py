"""
YAML Parsing Helpers

Fix #6: Robust YAML parsing with retry and fallback for LLM responses.
"""

import re
import yaml
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def robust_yaml_parse(response: str, max_retries: int = 6) -> Optional[Dict[str, Any]]:
    """
    Robustly parse YAML from LLM response with multiple fallback strategies.

    Handles:
    - Direct YAML parsing
    - Extracting YAML from markdown code blocks
    - Extracting YAML delimited by --- and ...
    - Cleaning common LLM response artifacts
    - Bug #18 Fix: Fixing descriptions with special characters
    - Bug #18 Fix: Pattern-based extraction for validation structures

    Args:
        response: Raw LLM response that should contain YAML
        max_retries: Number of extraction strategies to try (default 6)

    Returns:
        Parsed dict if successful, None if all strategies fail
    """
    if not response or not response.strip():
        return None

    strategies = [
        _try_direct_parse,
        _try_extract_yaml_block,
        _try_extract_code_block,
        _try_clean_and_parse,
        _try_fix_descriptions_and_parse,  # Bug #18 Fix
        _try_extract_validation_structure,  # Bug #18 Fix: Last resort pattern matching
    ]

    for i, strategy in enumerate(strategies[:max_retries]):
        try:
            result = strategy(response)
            if result is not None:
                logger.debug(f"YAML parsed successfully with strategy {i+1}: {strategy.__name__}")
                return result
        except Exception as e:
            logger.debug(f"YAML strategy {i+1} ({strategy.__name__}) failed: {e}")
            continue

    logger.warning(f"All YAML parsing strategies failed for response: {response[:100]}...")
    return None


def _try_direct_parse(response: str) -> Optional[Dict[str, Any]]:
    """Try direct YAML parsing."""
    result = yaml.safe_load(response)
    if isinstance(result, dict):
        return result
    return None


def _try_extract_yaml_block(response: str) -> Optional[Dict[str, Any]]:
    """Extract YAML delimited by --- and ... markers."""
    # Match YAML document format: ---\ncontent\n...
    pattern = r'---\s*\n(.*?)\n\s*\.\.\.|\Z'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        yaml_content = match.group(1).strip()
        result = yaml.safe_load(yaml_content)
        if isinstance(result, dict):
            return result
    return None


def _try_extract_code_block(response: str) -> Optional[Dict[str, Any]]:
    """Extract YAML from markdown code blocks."""
    # Match ```yaml\ncontent\n``` or ```\ncontent\n```
    patterns = [
        r'```ya?ml?\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            yaml_content = match.group(1).strip()
            result = yaml.safe_load(yaml_content)
            if isinstance(result, dict):
                return result
    return None


def _try_clean_and_parse(response: str) -> Optional[Dict[str, Any]]:
    """Clean common LLM artifacts and try parsing."""
    # Remove common prefixes/suffixes
    cleaned = response.strip()

    # Remove "Here's the YAML:" type prefixes
    prefixes_to_remove = [
        r'^[Hh]ere\'?s?\s+(?:the\s+)?(?:YAML|yaml|response|output)[\s:]*\n?',
        r'^[Oo]utput[\s:]*\n?',
        r'^[Rr]esult[\s:]*\n?',
    ]
    for prefix in prefixes_to_remove:
        cleaned = re.sub(prefix, '', cleaned)

    # Remove trailing explanations
    suffixes_to_remove = [
        r'\n+(?:Note|Explanation|This|The above).*$',
    ]
    for suffix in suffixes_to_remove:
        cleaned = re.sub(suffix, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

    cleaned = cleaned.strip()
    if cleaned:
        result = yaml.safe_load(cleaned)
        if isinstance(result, dict):
            return result
    return None


def _try_fix_descriptions_and_parse(response: str) -> Optional[Dict[str, Any]]:
    """
    Bug #18 Fix: Handle YAML with problematic description values.

    LLM often generates descriptions with special characters that break YAML.
    This strategy quotes all description values to make them valid YAML.
    """
    cleaned = response.strip()

    # Fix description lines that may have special characters
    # Pattern: "description: Some text with special chars" -> "description: 'Some text with special chars'"
    lines = cleaned.split('\n')
    fixed_lines = []

    for line in lines:
        # Check if this is a description line (has "description:" followed by unquoted text)
        if 'description:' in line:
            match = re.match(r'^(\s*description:\s*)(.+)$', line)
            if match:
                indent = match.group(1)
                value = match.group(2).strip()
                # Only quote if not already quoted
                if value and not (value.startswith('"') or value.startswith("'")):
                    # Escape single quotes in the value
                    value = value.replace("'", "''")
                    line = f"{indent}'{value}'"
        fixed_lines.append(line)

    fixed = '\n'.join(fixed_lines)

    try:
        result = yaml.safe_load(fixed)
        if isinstance(result, dict):
            logger.debug("YAML parsed successfully after fixing descriptions")
            return result
    except yaml.YAMLError:
        pass

    return None


def _try_extract_validation_structure(response: str) -> Optional[Dict[str, Any]]:
    """
    Bug #18 Fix: Extract validation ground truth structure even when YAML fails.

    When LLM generates validation_count + validations structure but YAML parsing fails,
    try to extract the key data using regex patterns.
    """
    if 'validation_count' not in response or 'validations' not in response:
        return None

    # Try to extract validation_count
    count_match = re.search(r'validation_count:\s*(\d+)', response)
    if not count_match:
        return None

    validation_count = int(count_match.group(1))

    # Try to extract individual validations using pattern matching
    # Pattern: V{id}_{entity}_{field}:\n    entity: {name}\n    field: {field}\n    constraint: {constraint}
    validation_pattern = re.compile(
        r'(V\d+_\w+):\s*\n'
        r'\s+entity:\s*(\w+)\s*\n'
        r'\s+field:\s*(\w+)\s*\n'
        r'\s+constraint:\s*([^\n]+)\s*\n'
        r'(?:\s+description:\s*([^\n]+))?',
        re.MULTILINE
    )

    validations = {}
    for match in validation_pattern.finditer(response):
        key = match.group(1)
        validations[key] = {
            'entity': match.group(2),
            'field': match.group(3),
            'constraint': match.group(4).strip(),
        }
        if match.group(5):
            validations[key]['description'] = match.group(5).strip()

    if validations:
        logger.debug(f"Extracted {len(validations)} validations using pattern matching")
        return {
            'validation_count': validation_count,
            'validations': validations
        }

    return None


def safe_yaml_load(content: str, default: Any = None) -> Any:
    """
    Safe YAML load with default fallback.

    Args:
        content: YAML string to parse
        default: Default value if parsing fails

    Returns:
        Parsed content or default
    """
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.warning(f"YAML parsing error: {e}")
        return default
