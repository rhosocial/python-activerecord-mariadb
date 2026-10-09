# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_columns.py
"""
Tests for MariaDB column introspection.

This module tests the list_columns, get_column_info, and column_exists methods
for retrieving column metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ColumnInfo,
    ColumnNullable,
)


class TestListColumns:
    """Tests for list_columns method."""

    def test_list_columns_returns_column_info(self, backend_with_tables):
        """Test that list_columns returns ColumnInfo objects."""
        columns = backend_with_tables.introspector.list_columns("users")

        assert isinstance(columns, list)
        assert len(columns) > 0

        for col in columns:
            assert isinstance(col, ColumnInfo)

    def test_list_columns_users_table(self, backend_with_tables):
        """Test columns for users table."""
        columns = backend_with_tables.introspector.list_columns("users")
        column_names = [c.name for c in columns]

        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
        assert "age" in column_names
        assert "created_at" in column_names

    def test_list_columns_nonexistent_table(self, backend_with_tables):
        """Test list_columns for non-existent table."""
        columns = backend_with_tables.introspector.list_columns("nonexistent")

        # Should return empty list for non-existent table
        assert isinstance(columns, list)
        assert len(columns) == 0

    def test_list_columns_caching(self, backend_with_tables):
        """Test that column list is cached."""
        columns1 = backend_with_tables.introspector.list_columns("users")
        columns2 = backend_with_tables.introspector.list_columns("users")

        # Should return the same cached list
        assert columns1 is columns2


class TestGetColumnInfo:
    """Tests for get_column_info method."""

    def test_get_column_info_existing(self, backend_with_tables):
        """Test get_column_info for existing column."""
        col = backend_with_tables.introspector.get_column_info("users", "email")

        assert col is not None
        assert isinstance(col, ColumnInfo)
        assert col.name == "email"

    def test_get_column_info_nonexistent_column(self, backend_with_tables):
        """Test get_column_info for non-existent column."""
        col = backend_with_tables.introspector.get_column_info("users", "nonexistent")

        assert col is None

    def test_get_column_info_nonexistent_table(self, backend_with_tables):
        """Test get_column_info for non-existent table."""
        col = backend_with_tables.introspector.get_column_info("nonexistent", "id")

        assert col is None


class TestColumnExists:
    """Tests for column_exists method."""

    def test_column_exists_true(self, backend_with_tables):
        """Test column_exists returns True for existing column."""
        assert backend_with_tables.introspector.column_exists("users", "id") is True
        assert backend_with_tables.introspector.column_exists("users", "email") is True

    def test_column_exists_false(self, backend_with_tables):
        """Test column_exists returns False for non-existent column."""
        assert backend_with_tables.introspector.column_exists("users", "nonexistent") is False


class TestColumnInfoDetails:
    """Tests for detailed column information."""

    def test_column_ordinal_position(self, backend_with_tables):
        """Test column ordinal positions are correct."""
        columns = backend_with_tables.introspector.list_columns("users")

        # Columns should be ordered by ordinal position
        positions = [c.ordinal_position for c in columns]
        assert positions == sorted(positions)

        # First column should be id
        first_col = next(c for c in columns if c.ordinal_position == 1)
        assert first_col.name == "id"

    def test_column_data_type(self, backend_with_tables):
        """Test column data type detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.data_type == "int"

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.data_type == "varchar"

    def test_column_data_type_full(self, backend_with_tables):
        """Test full data type includes length."""
        columns = backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert "varchar(100)" in name_col.data_type_full.lower()

    def test_column_nullable(self, backend_with_tables):
        """Test nullable column detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.nullable == ColumnNullable.NOT_NULL

        age_col = next(c for c in columns if c.name == "age")
        assert age_col.nullable == ColumnNullable.NULLABLE

    def test_column_primary_key(self, backend_with_tables):
        """Test primary key detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.is_primary_key is True

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.is_primary_key is False

    def test_column_unique(self, backend_with_tables):
        """Test unique column detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        email_col = next(c for c in columns if c.name == "email")
        # email has unique index
        assert email_col.is_unique is True

    def test_column_auto_increment(self, backend_with_tables):
        """Test auto increment detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.is_auto_increment is True

    def test_column_default_value(self, backend_with_tables):
        """Test default value detection."""
        columns = backend_with_tables.introspector.list_columns("posts")

        status_col = next(c for c in columns if c.name == "status")
        assert status_col.default_value is not None

    def test_column_charset_collation(self, backend_with_tables):
        """Test charset and collation detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.charset is not None
        assert name_col.collation is not None

    def test_column_numeric_precision_scale(self, backend_with_tables):
        """Test numeric precision and scale detection."""
        backend_with_tables.executescript("""
            DROP TABLE IF EXISTS test_numeric;
            CREATE TABLE test_numeric (
                id INT PRIMARY KEY,
                amount DECIMAL(10, 2)
            );
        """)

        columns = backend_with_tables.introspector.list_columns("test_numeric")

        amount_col = next(c for c in columns if c.name == "amount")
        assert amount_col.numeric_precision == 10
        assert amount_col.numeric_scale == 2

        backend_with_tables.executescript("DROP TABLE IF EXISTS test_numeric;")

    def test_column_character_maximum_length(self, backend_with_tables):
        """Test character maximum length detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.character_maximum_length == 100

    def test_enum_column_type(self, backend_with_tables):
        """Test ENUM column type detection."""
        columns = backend_with_tables.introspector.list_columns("posts")

        status_col = next(c for c in columns if c.name == "status")
        assert "enum" in status_col.data_type_full.lower()
        assert "draft" in status_col.data_type_full.lower()

    def test_text_column_type(self, backend_with_tables):
        """Test TEXT column type detection."""
        columns = backend_with_tables.introspector.list_columns("posts")

        content_col = next(c for c in columns if c.name == "content")
        assert content_col.data_type == "text"


class TestParsedDataType:
    """``ColumnInfo.parsed_data_type`` is populated for every column.

    The field is what makes the schema differ compare *type objects* instead of
    the ``data_type`` string. Core's ``SchemaDiffer._columns_equivalent`` reads
    it twice: with a type on both sides it compares them with ``!=``, and only
    when one side is ``None`` does it fall back to the string. MariaDB was the
    only backend that left it at its ``None`` default, so on this backend the
    entire type-identity model was inert: the differ saw ``int`` for ``int(11)``
    and for ``int(10) unsigned``, ``varchar`` for ``varchar(100)`` and
    ``varchar(200)``, ``enum`` for any two sets of labels.

    Every other backend populates it in ``_parse_columns`` via
    ``DataType.parse_data_type_str(dialect, raw)``, and so does this one now.
    """

    def test_every_column_carries_a_parsed_type(self, backend_with_tables):
        """Zero ``None``s on a table covering the ordinary vocabulary."""
        columns = backend_with_tables.introspector.list_columns("users")
        assert columns
        unset = [c.name for c in columns if c.parsed_data_type is None]
        assert unset == [], f"columns with no parsed_data_type: {unset}"

    def test_the_parsed_type_is_built_from_the_catalog_string(
        self, backend_with_tables,
    ):
        columns = backend_with_tables.introspector.list_columns("users")
        for col in columns:
            assert col.parsed_data_type is not None, col.name
            # Same reader, same input: re-parsing the catalog string must give
            # the same object, or the field is not derived from the catalog.
            reparsed = backend_with_tables.dialect.parse_type(col.data_type_full)
            assert col.parsed_data_type == reparsed, col.name

    def test_parameters_survive_into_the_parsed_type(self, backend_with_tables):
        """The point of the field: ``VARCHAR(100)`` is not ``VARCHAR``.

        ``data_type`` is ``col_type.split("(")[0].lower()``, so the length was
        always thrown away for the string comparison; the parsed type keeps it.
        """
        columns = backend_with_tables.introspector.list_columns("users")
        name_col = next(c for c in columns if c.name == "name")
        assert name_col.data_type == "varchar"
        assert name_col.parsed_data_type.length == 100

    def test_enum_labels_survive_into_the_parsed_type(self, backend_with_tables):
        columns = backend_with_tables.introspector.list_columns("posts")
        status_col = next(c for c in columns if c.name == "status")
        assert list(status_col.parsed_data_type.values) == [
            "draft", "published", "archived",
        ]

    def test_the_differ_sees_a_change_the_string_cannot(self, backend_with_tables):
        """A worked example of what populating the field buys.

        ``VARCHAR(100)`` and ``VARCHAR(200)`` have the same ``data_type``
        string, so the pre-fix comparison called them equal; their parsed types
        are not, so the differ now reports a change MariaDB can certainly make.
        """
        differ = backend_with_tables.dialect.create_schema_differ()

        def column(width):
            text = f"varchar({width})"
            return ColumnInfo(
                name="c", table_name="t", ordinal_position=1,
                data_type="varchar", data_type_full=text,
                parsed_data_type=backend_with_tables.dialect.parse_type(text),
            )

        assert differ._columns_equivalent(column(100), column(100)) is True
        assert differ._columns_equivalent(column(100), column(200)) is False

    def test_one_unreadable_column_does_not_take_down_the_table(
        self, backend_with_tables,
    ):
        """A single bad ``COLUMN_TYPE`` degrades that column, not the table.

        ``parse_type`` ends in ``CustomType``, whose constructor validates the
        raw name as a SQL type name and raises for anything that is not
        identifier-shaped. The catalog is not under the backend's control, so the
        introspector catches that, leaves ``parsed_data_type`` unset for that one
        column -- which is the field's documented ``None``, and exactly what core's
        differ already treats as "fall back to the string" -- and warns rather
        than failing. The rest of the table is unaffected.

        The trigger is a stub rather than a live column: the point under test is
        the containment, and no MariaDB release in the matrix reports such a type.
        """
        from rhosocial.activerecord.backend.expression.types import (
            DataType,
            InvalidTypeNameError,
        )

        introspector = backend_with_tables.introspector
        rows = [
            {
                "COLUMN_NAME": "good", "ORDINAL_POSITION": 1,
                "COLUMN_TYPE": "INT(11)", "IS_NULLABLE": "NO",
            },
            {
                # Not identifier-shaped, so CustomType refuses it.
                "COLUMN_NAME": "bad", "ORDINAL_POSITION": 2,
                "COLUMN_TYPE": "some type not a name", "IS_NULLABLE": "YES",
            },
            {
                "COLUMN_NAME": "alsogood", "ORDINAL_POSITION": 3,
                "COLUMN_TYPE": "VARCHAR(10)", "IS_NULLABLE": "YES",
            },
        ]

        def explode(dialect, raw):
            # Faithful to the real failure mode: only the shape
            # ``CustomType`` refuses reaches the exception. A type this dialect
            # *can* read is unaffected, which is what makes the containment
            # per-column rather than per-table.
            if " " in raw:
                raise InvalidTypeNameError(raw)
            return backend_with_tables.dialect.parse_type(raw)

        original = DataType.parse_data_type_str
        try:
            DataType.parse_data_type_str = staticmethod(explode)
            with pytest.warns(RuntimeWarning, match="some type not a name"):
                columns = introspector._parse_columns(rows, "t", "d")
        finally:
            DataType.parse_data_type_str = original

        assert [c.name for c in columns] == ["good", "bad", "alsogood"]
        # Every column is still reported -- that is the containment -- and the
        # two readable ones keep their types.
        assert len(columns) == 3
        assert columns[0].parsed_data_type is not None
        assert columns[2].parsed_data_type is not None
        # The unreadable one degrades to the string comparison core already
        # implements, and says so loudly.
        assert columns[1].parsed_data_type is None
        assert columns[0].data_type == "int"
        assert columns[1].data_type == "some type not a name"
        assert columns[2].data_type == "varchar"


class TestSpatialSRIDSurvivesIntrospection:
    """A spatial column's declared reference system survives introspection.

    ``COLUMN_TYPE`` does not carry it: MariaDB reports the bare ``point`` and
    keeps the declaration only in ``I_S.GEOMETRY_COLUMNS.SRID`` (measured on
    10.2.44 and 13.1.1; ``SHOW CREATE`` drops the attribute too). The column
    query joins that view and rebuilds the full type text as
    ``point REF_SYSTEM_ID=4326`` before parsing, so the differ compares the
    declared type rather than a bare one. SRID 0 -- what the view reports for a
    spatial column with no declaration -- means "no declared system", not
    ``REF_SYSTEM_ID=0``, which the server cannot tell apart from it.
    """

    TABLE = "test_spatial_srid_introspection"

    def _columns(self, backend):
        backend.executescript(
            f"DROP TABLE IF EXISTS {self.TABLE}; "
            f"CREATE TABLE {self.TABLE} ("
            "  id INT PRIMARY KEY,"
            "  location POINT REF_SYSTEM_ID=4326,"
            "  plain POINT,"
            "  body TEXT)"
        )
        backend.introspector.clear_cache()
        try:
            return backend.introspector.list_columns(self.TABLE)
        finally:
            backend.introspector.clear_cache()
            backend.executescript(f"DROP TABLE IF EXISTS {self.TABLE};")

    def test_declared_srid_reaches_the_parsed_type(self, backend_with_tables):
        columns = self._columns(backend_with_tables)
        location = next(c for c in columns if c.name == "location")

        assert location.data_type == "point"
        assert location.data_type_full == "point REF_SYSTEM_ID=4326"
        assert location.parsed_data_type.srid == 4326

    def test_the_parsed_type_is_rebuilt_from_the_full_text(self, backend_with_tables):
        """The full text is the parse input, SRID included.

        Same invariant as ``TestParsedDataType``: a caller holding
        ``data_type_full`` can rebuild the parsed type, so the synthesized
        attribute is part of the text rather than a side channel.
        """
        columns = self._columns(backend_with_tables)
        for col in columns:
            assert col.parsed_data_type is not None, col.name
            assert col.parsed_data_type == backend_with_tables.dialect.parse_type(
                col.data_type_full
            ), col.name

    def test_a_bare_spatial_column_has_no_declared_reference_system(
        self, backend_with_tables,
    ):
        columns = self._columns(backend_with_tables)
        location = next(c for c in columns if c.name == "location")
        plain = next(c for c in columns if c.name == "plain")

        # The view reports 0 for a bare spatial column, and 0 is MariaDB's
        # default coordinate system: reading it as a declaration would make
        # every bare POINT differ from a POINT declared with no system.
        assert plain.data_type_full == "point"
        assert plain.parsed_data_type.srid is None
        assert location.parsed_data_type != plain.parsed_data_type


class TestCompositePrimaryKey:
    def test_composite_primary_key(self, backend_with_tables):
        """Test composite primary key detection."""
        columns = backend_with_tables.introspector.list_columns("post_tags")

        pk_columns = [c for c in columns if c.is_primary_key]
        assert len(pk_columns) == 2

        pk_col_names = {c.name for c in pk_columns}
        assert "post_id" in pk_col_names
        assert "tag_id" in pk_col_names


class TestAsyncColumnIntrospection:
    """Async tests for column introspection."""

    @pytest.mark.asyncio
    async def test_async_list_columns(self, async_backend_with_tables):
        """Test async list_columns returns ColumnInfo objects."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        assert isinstance(columns, list)
        assert len(columns) > 0

        for col in columns:
            assert isinstance(col, ColumnInfo)

    @pytest.mark.asyncio
    async def test_async_get_column_info(self, async_backend_with_tables):
        """Test async get_column_info for existing column."""
        col = await async_backend_with_tables.introspector.get_column_info("users", "email")

        assert col is not None
        assert isinstance(col, ColumnInfo)
        assert col.name == "email"

    @pytest.mark.asyncio
    async def test_async_column_exists(self, async_backend_with_tables):
        """Test async column_exists returns True for existing column."""
        exists = await async_backend_with_tables.introspector.column_exists("users", "id")
        assert exists is True

    @pytest.mark.asyncio
    async def test_async_list_columns_caching(self, async_backend_with_tables):
        """Test that async column list is cached."""
        columns1 = await async_backend_with_tables.introspector.list_columns("users")
        columns2 = await async_backend_with_tables.introspector.list_columns("users")

        # Should return the same cached list
        assert columns1 is columns2
