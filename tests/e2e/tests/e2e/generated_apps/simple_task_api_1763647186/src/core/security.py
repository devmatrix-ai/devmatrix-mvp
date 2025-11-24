"""
Security Utilities

HTML sanitization and security helpers.
"""
import bleach

# Allowed HTML tags for user-generated content
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a']
ALLOWED_ATTRS = {'a': ['href', 'title']}


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML to prevent XSS attacks.

    Args:
        text: Raw HTML content

    Returns:
        Sanitized HTML with only allowed tags
    """
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True
    )