# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_identifier_quoting.py
"""
Tests for MariaDBDialect identifier quoting.

Verifies that format_identifier correctly applies backtick quoting,
escapes internal backticks, respects need_quote, and warns about
reserved words used without quoting.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning


class TestMariaDBIdentifierQuoting:
    """Test MariaDBDialect format_identifier and reserved words."""

    def test_format_identifier_default_backtick_quotes(self):
        d = MariaDBDialect()
        assert d.format_identifier("users") == "`users`"

    def test_format_identifier_need_quote_false(self):
        d = MariaDBDialect()
        assert d.format_identifier("users", need_quote=False) == "users"

    def test_format_identifier_escapes_internal_backticks(self):
        d = MariaDBDialect()
        assert d.format_identifier("my`table") == "`my``table`"

    def test_format_identifier_need_quote_false_no_escaping(self):
        d = MariaDBDialect()
        assert d.format_identifier("my`table", need_quote=False) == "my`table"

    def test_reserved_words_is_frozenset(self):
        d = MariaDBDialect()
        assert isinstance(d.reserved_words, frozenset)

    def test_is_reserved_word_case_insensitive(self):
        d = MariaDBDialect()
        assert d.is_reserved_word("SELECT") is True
        assert d.is_reserved_word("select") is True

    def test_is_reserved_word_non_reserved(self):
        d = MariaDBDialect()
        assert d.is_reserved_word("users") is False

    def test_reserved_word_warning_emitted(self):
        d = MariaDBDialect()
        with pytest.warns(IdentifierQuotingWarning, match="select"):
            d.format_identifier("select", need_quote=False)

    def test_balanced_quotes_security(self):
        d = MariaDBDialect()
        for ident in ["users", "my`table", "a``b"]:
            result = d.format_identifier(ident)
            assert result.count("`") % 2 == 0, f"Unbalanced backticks: {result}"
