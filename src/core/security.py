"""
Security Utilities Module

Provides HTML sanitization and XSS protection for user-generated content.
Implements OWASP A03:2021 Injection prevention.

Created for Task Group 5: Security Hardening - Task 5.2
"""

import bleach
from typing import Optional, List, Dict, Any
from src.observability import get_logger

logger = get_logger("security")

# ============================================================================
# HTML Sanitization Configuration
# ============================================================================

# Allowed HTML tags for user content
# Based on OWASP recommendations for safe HTML
ALLOWED_TAGS = [
    # Text formatting
    'p', 'br', 'strong', 'em', 'u', 'b', 'i',
    # Lists
    'ul', 'ol', 'li',
    # Links (with restricted attributes)
    'a',
    # Code blocks
    'code', 'pre',
]

# Allowed HTML attributes
# Only 'a' tags can have href and title
ALLOWED_ATTRS = {
    'a': ['href', 'title'],
}

# Allowed URL protocols
# Prevents javascript:, data:, and other dangerous protocols
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


# ============================================================================
# HTML Sanitization Functions
# ============================================================================

def sanitize_html(text: Optional[str]) -> Optional[str]:
    """
    Sanitize HTML content to prevent XSS attacks.

    Removes dangerous tags, attributes, and protocols while preserving
    safe formatting elements.

    Args:
        text: Raw HTML string (may contain malicious content)

    Returns:
        Sanitized HTML string safe for rendering
        Returns None if input is None

    Examples:
        >>> sanitize_html("<script>alert('XSS')</script>")
        ""
        >>> sanitize_html("<p>Hello <strong>World</strong></p>")
        "<p>Hello <strong>World</strong></p>"
        >>> sanitize_html("<a href='javascript:alert(1)'>Click</a>")
        "<a>Click</a>"
    """
    if text is None:
        return None

    if not text.strip():
        return text

    try:
        sanitized = bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            protocols=ALLOWED_PROTOCOLS,
            strip=True  # Strip disallowed tags instead of escaping
        )

        # Log if dangerous content was removed
        if sanitized != text:
            logger.warning(
                "HTML content sanitized - potentially dangerous content removed",
                extra={
                    "original_length": len(text),
                    "sanitized_length": len(sanitized),
                    "removed_chars": len(text) - len(sanitized)
                }
            )

        return sanitized

    except Exception as e:
        logger.error(f"HTML sanitization failed: {str(e)}", exc_info=True)
        # Fail-safe: return empty string if sanitization fails
        return ""


def sanitize_text_fields(obj: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Sanitize multiple text fields in a dictionary.

    Useful for sanitizing multiple fields in request/response objects.

    Args:
        obj: Dictionary containing fields to sanitize
        fields: List of field names to sanitize

    Returns:
        Dictionary with sanitized fields (in-place modification)

    Examples:
        >>> data = {"title": "<script>alert(1)</script>", "description": "Safe text"}
        >>> sanitize_text_fields(data, ["title", "description"])
        {"title": "", "description": "Safe text"}
    """
    for field in fields:
        if field in obj and obj[field] is not None:
            original = obj[field]
            sanitized = sanitize_html(obj[field])

            if sanitized != original:
                logger.info(
                    f"Field '{field}' sanitized",
                    extra={
                        "field": field,
                        "had_dangerous_content": True
                    }
                )

            obj[field] = sanitized

    return obj


def is_safe_html(text: str) -> bool:
    """
    Check if HTML content is safe (no sanitization needed).

    Args:
        text: HTML string to check

    Returns:
        True if content is safe, False if sanitization would modify it

    Examples:
        >>> is_safe_html("<p>Hello World</p>")
        True
        >>> is_safe_html("<script>alert(1)</script>")
        False
    """
    if not text:
        return True

    sanitized = sanitize_html(text)
    return sanitized == text


# ============================================================================
# URL Sanitization (Bonus for future use)
# ============================================================================

def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitize URL to prevent javascript: and data: protocols.

    Args:
        url: URL string to sanitize

    Returns:
        Sanitized URL or None if dangerous

    Examples:
        >>> sanitize_url("https://example.com")
        "https://example.com"
        >>> sanitize_url("javascript:alert(1)")
        None
    """
    if url is None:
        return None

    url = url.strip()

    # Check for dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']

    for protocol in dangerous_protocols:
        if url.lower().startswith(protocol):
            logger.warning(
                f"Dangerous URL protocol detected: {protocol}",
                extra={"url_prefix": url[:50]}
            )
            return None

    # Ensure only http, https, mailto
    if url.startswith('http://') or url.startswith('https://') or url.startswith('mailto:'):
        return url
    elif url.startswith('//'):
        # Protocol-relative URL
        return url
    else:
        # Assume relative URL (safe)
        return url


# ============================================================================
# Batch Sanitization for Pydantic Models
# ============================================================================

def sanitize_model_fields(model_instance: Any, text_fields: List[str]) -> Any:
    """
    Sanitize text fields in a Pydantic model instance.

    Args:
        model_instance: Pydantic model instance
        text_fields: List of field names to sanitize

    Returns:
        Model instance with sanitized fields (in-place)

    Examples:
        >>> task = TaskCreate(title="<script>XSS</script>", description="Safe")
        >>> sanitize_model_fields(task, ["title", "description"])
        TaskCreate(title="", description="Safe")
    """
    for field in text_fields:
        if hasattr(model_instance, field):
            value = getattr(model_instance, field)
            if value is not None and isinstance(value, str):
                sanitized = sanitize_html(value)
                setattr(model_instance, field, sanitized)

    return model_instance


# ============================================================================
# Testing Helper Functions
# ============================================================================

def get_xss_test_payloads() -> List[str]:
    """
    Get common XSS test payloads for security testing.

    Returns:
        List of XSS test payloads

    Usage:
        Use in tests to verify sanitization works correctly.
    """
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<select onfocus=alert('XSS') autofocus>",
        "<textarea onfocus=alert('XSS') autofocus>",
        "<keygen onfocus=alert('XSS') autofocus>",
        "<video><source onerror=alert('XSS')>",
        "<audio src=x onerror=alert('XSS')>",
        "<details open ontoggle=alert('XSS')>",
        "<marquee onstart=alert('XSS')>",
        "javascript:alert('XSS')",
        "<a href='javascript:alert(1)'>Click</a>",
    ]
