# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_fulltext_index.py
"""
MariaDB FULLTEXT index support tests.

This module tests MariaDB-specific FULLTEXT index functionality including:
- Protocol support detection
- MATCH ... AGAINST expression formatting
- CREATE FULLTEXT INDEX statement formatting
"""
import pytest
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.expression.statements import (
    CreateFulltextIndexExpression,
    DropFulltextIndexExpression
)
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBMatchAgainstExpression


class TestFullTextProtocol:
    """Test FULLTEXT protocol implementation."""

    def test_supports_fulltext_index_version_check(self):
        """Test version check for FULLTEXT index support."""
        dialect_old = MariaDBDialect(version=(5, 5, 0))
        assert dialect_old.supports_fulltext_index()

        dialect_100 = MariaDBDialect(version=(10, 0, 0))
        assert dialect_100.supports_fulltext_index()

    def test_format_match_against(self):
        """Test format_match_against method."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        sql, params = dialect.format_match_against(
            ['title', 'content'],
            'MariaDB',
            mode='NATURAL_LANGUAGE'
        )

        assert 'MATCH(`title`, `content`)' in sql
        assert 'AGAINST' in sql
        assert 'IN NATURAL LANGUAGE MODE' in sql
        assert params == ('MariaDB',)

    def test_match_against_expression(self):
        """Test MariaDBMatchAgainstExpression class."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBMatchAgainstExpression(
            dialect,
            columns=['title', 'content'],
            search_string='database',
            mode='BOOLEAN'
        )

        sql, params = expr.to_sql()

        assert 'MATCH(`title`, `content`)' in sql
        assert 'AGAINST' in sql
        assert 'IN BOOLEAN MODE' in sql
        assert params == ('database',)

    def test_match_against_with_alias(self):
        """Test MariaDBMatchAgainstExpression with alias."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBMatchAgainstExpression(
            dialect,
            columns=['title', 'content'],
            search_string='test'
        )

        aliased = expr.as_('relevance')
        sql, params = aliased.to_sql()

        assert 'MATCH(`title`, `content`)' in sql
        assert 'AGAINST' in sql
        assert params == ('test',)

    def test_supports_fulltext_parser(self):
        """Test parser plugin support."""
        dialect = MariaDBDialect(version=(10, 0, 0))
        assert dialect.supports_fulltext_parser()

        dialect_old = MariaDBDialect(version=(5, 5, 0))
        assert dialect_old.supports_fulltext_parser()

    def test_supports_fulltext_query_expansion(self):
        """Test query expansion support."""
        dialect = MariaDBDialect(version=(10, 0, 0))
        assert dialect.supports_fulltext_query_expansion()

    def test_format_fulltext_match_natural_mode(self):
        """Test MATCH ... AGAINST with natural language mode."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        sql, params = dialect.format_fulltext_match(
            ['title', 'content'],
            'database system'
        )

        assert 'MATCH(`title`, `content`)' in sql
        assert 'AGAINST' in sql
        assert 'IN NATURAL LANGUAGE MODE' in sql
        assert params == ('database system',)

    def test_format_fulltext_match_boolean_mode(self):
        """Test MATCH ... AGAINST with boolean mode."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        sql, params = dialect.format_fulltext_match(
            ['title', 'content'],
            '+database +system',
            mode='BOOLEAN'
        )

        assert 'MATCH(`title`, `content`)' in sql
        assert 'AGAINST' in sql
        assert 'IN BOOLEAN MODE' in sql
        assert params == ('+database +system',)

    def test_format_fulltext_match_query_expansion(self):
        """Test MATCH ... AGAINST with query expansion."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        sql, params = dialect.format_fulltext_match(
            ['content'],
            'database',
            mode='WITH QUERY EXPANSION'
        )

        assert 'MATCH(`content`)' in sql
        assert 'AGAINST' in sql
        assert 'WITH QUERY EXPANSION' in sql
        assert params == ('database',)

    def test_format_create_fulltext_index(self):
        """Test CREATE FULLTEXT INDEX statement formatting."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = CreateFulltextIndexExpression(
            dialect=dialect,
            index='idx_content',
            table='articles',
            columns=['title', 'content']
        )
        sql, params = expr.to_sql()

        assert 'CREATE FULLTEXT INDEX' in sql
        assert '`idx_content`' in sql
        assert 'ON `articles`' in sql
        assert '`title`, `content`' in sql
        assert params == ()

    def test_format_create_fulltext_index_with_parser(self):
        """Test CREATE FULLTEXT INDEX with parser plugin."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = CreateFulltextIndexExpression(
            dialect=dialect,
            index='idx_content',
            table='articles',
            columns=['content'],
            parser='ngram'
        )
        sql, params = expr.to_sql()

        assert 'CREATE FULLTEXT INDEX' in sql
        assert 'WITH PARSER `ngram`' in sql
        assert params == ()


class TestAsyncFullTextProtocol:
    """Test async FULLTEXT protocol (same as sync, but verifies parity)."""

    @pytest.mark.asyncio
    async def test_async_supports_fulltext_index(self):
        """Test async version of supports_fulltext_index."""
        dialect = MariaDBDialect(version=(10, 6, 0))
        assert dialect.supports_fulltext_index()

    @pytest.mark.asyncio
    async def test_async_format_fulltext_match(self):
        """Test async version of MATCH formatting."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        sql, params = dialect.format_fulltext_match(
            ['title'],
            'test',
            mode='BOOLEAN'
        )

        assert 'MATCH(`title`)' in sql
        assert 'IN BOOLEAN MODE' in sql
