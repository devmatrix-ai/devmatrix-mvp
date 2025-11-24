"""
Unit tests for keyword fallback functionality (TG5).

Tests keyword-based pattern matching when embedding search yields insufficient results.
"""

import pytest
from src.cognitive.patterns.pattern_bank import PatternBank


class TestKeywordFallback:
    """Test keyword-based fallback pattern matching."""

    def test_extract_keywords_removes_stopwords(self):
        """Keyword extraction should remove common stopwords."""
        bank = PatternBank()

        text = "Create a new user in the database"
        keywords = bank._extract_keywords(text)

        # Should keep meaningful words
        assert "create" in keywords
        assert "new" in keywords
        assert "user" in keywords
        assert "database" in keywords

        # Should remove stopwords
        assert "a" not in keywords
        assert "in" not in keywords
        assert "the" not in keywords

    def test_extract_keywords_lowercase(self):
        """Keywords should be converted to lowercase."""
        bank = PatternBank()

        text = "Create New User"
        keywords = bank._extract_keywords(text)

        assert "create" in keywords
        assert "new" in keywords
        assert "user" in keywords
        # No uppercase
        assert "Create" not in keywords
        assert "New" not in keywords

    def test_crud_keywords_match_create_pattern(self):
        """Create/add/new keywords should match CRUD create patterns."""
        bank = PatternBank()

        # Test various create-related keywords
        assert bank._keyword_to_pattern_type("create") == "crud_create"
        assert bank._keyword_to_pattern_type("add") == "crud_create"
        assert bank._keyword_to_pattern_type("new") == "crud_create"

    def test_crud_keywords_match_list_pattern(self):
        """List/all/filter keywords should match CRUD list patterns."""
        bank = PatternBank()

        assert bank._keyword_to_pattern_type("list") == "crud_list"
        assert bank._keyword_to_pattern_type("all") == "crud_list"
        assert bank._keyword_to_pattern_type("filter") == "crud_list"

    def test_crud_keywords_match_update_pattern(self):
        """Update/edit/modify keywords should match CRUD update patterns."""
        bank = PatternBank()

        assert bank._keyword_to_pattern_type("update") == "crud_update"
        assert bank._keyword_to_pattern_type("edit") == "crud_update"
        assert bank._keyword_to_pattern_type("modify") == "crud_update"

    def test_crud_keywords_match_delete_pattern(self):
        """Delete/remove keywords should match CRUD delete patterns."""
        bank = PatternBank()

        assert bank._keyword_to_pattern_type("delete") == "crud_delete"
        assert bank._keyword_to_pattern_type("remove") == "crud_delete"

    def test_workflow_keywords_match_patterns(self):
        """Workflow keywords should match corresponding patterns."""
        bank = PatternBank()

        # Payment workflow
        assert bank._keyword_to_pattern_type("checkout") == "payment_workflow"
        assert bank._keyword_to_pattern_type("pay") == "payment_workflow"
        assert bank._keyword_to_pattern_type("order") == "payment_workflow"

        # Cart workflow
        assert bank._keyword_to_pattern_type("cart") == "cart_workflow"
        assert bank._keyword_to_pattern_type("basket") == "cart_workflow"

    def test_unknown_keyword_returns_none(self):
        """Unknown keywords should return None."""
        bank = PatternBank()

        assert bank._keyword_to_pattern_type("unknown_keyword") is None
        assert bank._keyword_to_pattern_type("xyz") is None
