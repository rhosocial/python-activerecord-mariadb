# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_tables.py
"""
Tests for MariaDB table introspection.

This module tests the list_tables, get_table_info, and table_exists methods
for retrieving table metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    IntrospectionTableInfo,
    TableType,
)


class TestListTables:
    """Tests for list_tables method."""

    def test_list_tables_returns_table_info(self, backend_with_tables):
        """Test that list_tables returns IntrospectionTableInfo objects."""
        tables = backend_with_tables.introspector.list_tables()

        assert isinstance(tables, list)
        assert len(tables) > 0

        for table in tables:
            assert isinstance(table, IntrospectionTableInfo)

    def test_list_tables_includes_created_tables(self, backend_with_tables):
        """Test that created tables are listed."""
        tables = backend_with_tables.introspector.list_tables()
        table_names = [t.name for t in tables]

        assert "users" in table_names
        assert "posts" in table_names
        assert "tags" in table_names
        assert "post_tags" in table_names

    def test_list_tables_excludes_system_tables(self, backend_with_tables):
        """Test that system tables are excluded by default."""
        tables = backend_with_tables.introspector.list_tables()

        for table in tables:
            assert table.table_type != TableType.SYSTEM_TABLE

    def test_list_tables_caching(self, backend_with_tables):
        """Test that table list is cached."""
        tables1 = backend_with_tables.introspector.list_tables()
        tables2 = backend_with_tables.introspector.list_tables()

        # Should return the same cached list
        assert tables1 is tables2

    def test_list_tables_empty_database(self, mariadb_backend_single):
        """Test list_tables on empty database (no user tables)."""
        # Clear any existing tables first
        tables = mariadb_backend_single.introspector.list_tables()

        # MariaDB always has some tables, but they might be filtered
        # This test just verifies the method works
        assert isinstance(tables, list)


class TestListTablesExcludesSequences:
    """A sequence is a table in ``TABLES``, but not an entry in this listing.

    MariaDB 10.3+ reports ``TABLE_TYPE='SEQUENCE'`` in the same view as base
    tables and views. Handing those rows back as tables with no columns and no
    rows is the defect these cases pin; the sequence family reports them.
    """

    def test_sequence_is_not_listed_as_a_table(self, backend_with_sequence_and_table):
        names = {
            table.name
            for table in backend_with_sequence_and_table.introspector.list_tables()
        }

        assert "intro_options" in names
        assert "intro_seq" not in names

    def test_sequence_is_not_reachable_by_table_lookup(self, backend_with_sequence_and_table):
        """``table_exists`` / ``get_table_info`` read the same listing."""
        introspector = backend_with_sequence_and_table.introspector

        assert introspector.table_exists("intro_options") is True
        assert introspector.get_table_info("intro_seq") is None
        assert introspector.table_exists("intro_seq") is False

    def test_the_sequence_family_still_reports_it(self, backend_with_sequence_and_table):
        names = {
            sequence.name
            for sequence in backend_with_sequence_and_table.introspector.list_sequences()
        }

        assert "intro_seq" in names
        assert "intro_options" not in names


class TestGetTableInfo:
    """Tests for get_table_info method."""

    def test_get_table_info_existing(self, backend_with_tables):
        """Test get_table_info for existing table."""
        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        assert isinstance(table, IntrospectionTableInfo)
        assert table.name == "users"

    def test_get_table_info_nonexistent(self, backend_with_tables):
        """Test get_table_info for non-existent table."""
        table = backend_with_tables.introspector.get_table_info("nonexistent")

        assert table is None

    def test_get_table_info_includes_columns(self, backend_with_tables):
        """Test that get_table_info includes column information."""
        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        assert table.columns is not None
        assert len(table.columns) > 0

    def test_get_table_info_includes_indexes(self, backend_with_tables):
        """Test that get_table_info includes index information."""
        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        assert table.indexes is not None
        assert len(table.indexes) > 0

    def test_get_table_info_includes_foreign_keys(self, backend_with_tables):
        """Test that get_table_info includes foreign key information."""
        table = backend_with_tables.introspector.get_table_info("posts")

        assert table is not None
        assert table.foreign_keys is not None
        assert len(table.foreign_keys) > 0


class TestTableExists:
    """Tests for table_exists method."""

    def test_table_exists_true(self, backend_with_tables):
        """Test table_exists returns True for existing table."""
        assert backend_with_tables.introspector.table_exists("users") is True
        assert backend_with_tables.introspector.table_exists("posts") is True

    def test_table_exists_false(self, backend_with_tables):
        """Test table_exists returns False for non-existent table."""
        assert backend_with_tables.introspector.table_exists("nonexistent") is False


class TestTableInfoDetails:
    """Tests for detailed table information."""

    def test_table_type_base_table(self, backend_with_tables):
        """Test that regular tables are BASE_TABLE type."""
        tables = backend_with_tables.introspector.list_tables()

        user_tables = [t for t in tables if t.name in ("users", "posts", "tags", "post_tags")]
        for table in user_tables:
            assert table.table_type == TableType.BASE_TABLE

    def test_table_comment(self, backend_with_tables):
        """Test that table comment can be retrieved."""
        # Create table with comment
        backend_with_tables.executescript("""
            DROP TABLE IF EXISTS test_comment;
            CREATE TABLE test_comment (
                id INT PRIMARY KEY
            ) COMMENT 'Test table comment';
        """)

        table = backend_with_tables.introspector.get_table_info("test_comment")

        assert table is not None
        assert table.comment == "Test table comment"

        # Cleanup
        backend_with_tables.executescript("DROP TABLE IF EXISTS test_comment;")

    def test_table_row_count(self, backend_with_tables):
        """Test that row count can be retrieved."""
        # Insert some data
        backend_with_tables.execute("INSERT INTO users (name, email) VALUES ('Test', 'test@example.com')")

        # Clear cache to get fresh data
        backend_with_tables.introspector.clear_cache()

        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        # Note: TABLE_ROWS from information_schema may be approximate
        # for InnoDB tables, so we just check it exists
        if table.row_count is not None:
            assert table.row_count >= 1

    def test_table_auto_increment(self, backend_with_tables):
        """Test that auto_increment value can be retrieved."""
        # Insert some data
        backend_with_tables.execute("INSERT INTO users (name, email) VALUES ('Test', 'test@example.com')")

        # Clear cache
        backend_with_tables.introspector.clear_cache()

        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        # auto_increment should be at least 2 after one insert
        if table.auto_increment is not None:
            assert table.auto_increment >= 2

    def test_table_create_time(self, backend_with_tables):
        """Test that create_time can be retrieved."""
        table = backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        assert table.create_time is not None


class TestAsyncTableIntrospection:
    """Async tests for table introspection."""

    @pytest.mark.asyncio
    async def test_async_list_tables(self, async_backend_with_tables):
        """Test async list_tables returns IntrospectionTableInfo objects."""
        tables = await async_backend_with_tables.introspector.list_tables()

        assert isinstance(tables, list)
        assert len(tables) > 0

        for table in tables:
            assert isinstance(table, IntrospectionTableInfo)

    @pytest.mark.asyncio
    async def test_async_get_table_info(self, async_backend_with_tables):
        """Test async get_table_info for existing table."""
        table = await async_backend_with_tables.introspector.get_table_info("users")

        assert table is not None
        assert isinstance(table, IntrospectionTableInfo)
        assert table.name == "users"

    @pytest.mark.asyncio
    async def test_async_table_exists(self, async_backend_with_tables):
        """Test async table_exists returns True for existing table."""
        exists = await async_backend_with_tables.introspector.table_exists("users")
        assert exists is True

    @pytest.mark.asyncio
    async def test_async_list_tables_caching(self, async_backend_with_tables):
        """Test that async table list is cached."""
        tables1 = await async_backend_with_tables.introspector.list_tables()
        tables2 = await async_backend_with_tables.introspector.list_tables()

        # Should return the same cached list
        assert tables1 is tables2

    @pytest.mark.asyncio
    async def test_async_sequence_is_not_listed_as_a_table(
        self, async_backend_with_sequence_and_table
    ):
        """The async path renders the same statement, so it excludes the same row."""
        introspector = async_backend_with_sequence_and_table.introspector
        names = {table.name for table in await introspector.list_tables()}

        assert "intro_options" in names
        assert "intro_seq" not in names

    @pytest.mark.asyncio
    async def test_async_the_sequence_family_still_reports_it(
        self, async_backend_with_sequence_and_table
    ):
        introspector = async_backend_with_sequence_and_table.introspector
        names = {sequence.name for sequence in await introspector.list_sequences()}

        assert "intro_seq" in names
