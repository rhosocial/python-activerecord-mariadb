# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/introspection_queries/test_mariadb_introspection_queries.py
"""Offline assertions on the SQL the introspection formatters render.

Every ``format_*_query`` here is a tree of expression nodes now, and these
tests pin the rendered text and the bind parameters -- which is what the layer
above (and the server) sees. A projection that moved, an alias that went
missing or a value that stopped being bound all show up here rather than as a
surprise in the live introspection legs.

The projection order, the aliases and the parameter tuples are asserted
exactly. Whitespace and identifier quoting are the formatter's business and are
written as rendered.
"""
import pytest

from rhosocial.activerecord.backend.expression import Literal, QueryStatement
from rhosocial.activerecord.backend.expression.introspection import (
    ColumnInfoQueryStatement,
    DatabaseInfoQueryStatement,
    ForeignKeyQueryStatement,
    IndexInfoQueryStatement,
    TableListQueryStatement,
    TriggerListQueryStatement,
    ViewInfoQueryStatement,
    ViewListQueryStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.introspection import (
    MariaDBConstraintQuery,
    MariaDBPartitionQuery,
    MariaDBRoutineQuery,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.introspection import (
    INFORMATION_SCHEMA_DATABASE,
    SYSTEM_SCHEMAS,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestIntrospectionQueries:
    """The eight ``format_*_query`` formatters, rendered from their trees."""

    def test_database_info(self, dialect):
        assert DatabaseInfoQueryStatement(dialect, schema="app").to_sql() == (
            "SELECT `DEFAULT_CHARACTER_SET_NAME`, `DEFAULT_COLLATION_NAME` "
            "FROM `information_schema`.`SCHEMATA` WHERE `SCHEMA_NAME` = %s",
            ("app",),
        )

    def test_table_list_projects_in_declared_order(self, dialect):
        sql, params = TableListQueryStatement(dialect, schema="app").to_sql()
        assert sql == (
            "SELECT `TABLE_NAME`, `TABLE_TYPE`, `TABLE_COMMENT`, `TABLE_ROWS`, "
            "`DATA_LENGTH`, `INDEX_LENGTH`, `AUTO_INCREMENT`, `CREATE_TIME`, "
            "`UPDATE_TIME` "
            "FROM `information_schema`.`TABLES` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_TYPE` <> 'SEQUENCE' "
            "AND NOT (`TABLE_SCHEMA` IN "
            "('information_schema', 'performance_schema', 'mysql', 'sys'))"
        )
        # Only the caller's schema is bound; the system-schema list and the
        # sequence exclusion are statements about this backend's catalogue and
        # stay inline.
        assert params == ("app",)

    def test_table_list_carries_the_storage_split(self, dialect):
        """Data and index bytes are projected apart, not summed away.

        MariaDB's storage is row-plus-index shaped, so the narrow slots of
        ``IntrospectionTableInfo`` are answerable: the sum is computed in
        the parser, which is also where "reported neither" becomes ``None``
        rather than a zero.
        """
        sql, params = TableListQueryStatement(dialect, schema="app").to_sql()
        assert "`DATA_LENGTH`, `INDEX_LENGTH`" in sql
        assert params == ("app",)

    def test_supports_table_storage_introspection(self, dialect):
        """The family is declared, so the dialect answers the storage slots."""
        assert dialect.supports_table_storage_introspection() is True

    def test_table_list_excludes_sequences_inline(self, dialect):
        """A sequence is a table in TABLES, but not a row of this listing.

        MariaDB 10.3+ reports ``TABLE_TYPE='SEQUENCE'`` beside the base tables.
        The exclusion belongs to the statement, so it is rendered as a literal
        and does not appear in the parameter tuple.
        """
        sql, params = TableListQueryStatement(dialect, schema="app").to_sql()
        assert "`TABLE_TYPE` <> 'SEQUENCE'" in sql
        assert params == ("app",)

    def test_table_list_include_system_drops_the_exclusion(self, dialect):
        sql, params = TableListQueryStatement(
            dialect, schema="app", include_system=True
        ).to_sql()
        assert "NOT (" not in sql
        # The sequence exclusion is not the system-schema exclusion: it stays.
        assert "`TABLE_TYPE` <> 'SEQUENCE'" in sql
        assert params == ("app",)

    def test_table_list_without_views_pins_the_type_inline(self, dialect):
        sql, params = TableListQueryStatement(
            dialect, schema="app", include_views=False
        ).to_sql()
        assert "`TABLE_TYPE` <> 'SEQUENCE'" in sql
        assert sql.endswith("AND `TABLE_TYPE` = 'BASE TABLE'")
        assert params == ("app",)

    def test_table_list_type_filter_is_bound(self, dialect):
        sql, params = TableListQueryStatement(
            dialect, schema="app", table_type="BASE TABLE"
        ).to_sql()
        assert "`TABLE_TYPE` <> 'SEQUENCE'" in sql
        assert sql.endswith("AND `TABLE_TYPE` = %s")
        assert params == ("app", "BASE TABLE")

    def test_table_list_base_table_filter_still_means_base_tables_only(self, dialect):
        """The bound filter and the inline exclusion compose by conjunction.

        ``table_type='BASE TABLE'`` must not turn the listing back into "every
        name in TABLES": the two ``TABLE_TYPE`` conditions are ANDed, so a
        ``SEQUENCE`` row matches neither reading.
        """
        sql, params = TableListQueryStatement(
            dialect, schema="app", table_type="BASE TABLE"
        ).to_sql()
        assert sql.index("`TABLE_TYPE` <> 'SEQUENCE'") < sql.index("`TABLE_TYPE` = %s")
        assert params == ("app", "BASE TABLE")

    def test_column_info_keeps_the_srid_join_and_its_alias(self, dialect):
        sql, params = ColumnInfoQueryStatement(dialect, "users", schema="app").to_sql()
        assert sql == (
            "SELECT `c`.`COLUMN_NAME`, `c`.`ORDINAL_POSITION`, `c`.`COLUMN_DEFAULT`, "
            "`c`.`IS_NULLABLE`, `c`.`DATA_TYPE`, `c`.`CHARACTER_MAXIMUM_LENGTH`, "
            "`c`.`NUMERIC_PRECISION`, `c`.`NUMERIC_SCALE`, `c`.`COLUMN_TYPE`, "
            "`c`.`COLUMN_KEY`, `c`.`EXTRA`, `c`.`COLUMN_COMMENT`, "
            "`c`.`CHARACTER_SET_NAME`, `c`.`COLLATION_NAME`, `g`.`SRID` AS `SRID` "
            "FROM `information_schema`.`COLUMNS` AS `c` "
            "LEFT JOIN `information_schema`.`GEOMETRY_COLUMNS` AS `g` "
            "ON `g`.`G_TABLE_SCHEMA` = `c`.`TABLE_SCHEMA` "
            "AND `g`.`G_TABLE_NAME` = `c`.`TABLE_NAME` "
            "AND `g`.`G_GEOMETRY_COLUMN` = `c`.`COLUMN_NAME` "
            "WHERE `c`.`TABLE_SCHEMA` = %s AND `c`.`TABLE_NAME` = %s "
            "ORDER BY `c`.`ORDINAL_POSITION`"
        )
        assert params == ("app", "users")

    def test_index_info_orders_by_name_then_position(self, dialect):
        sql, params = IndexInfoQueryStatement(dialect, "users", schema="app").to_sql()
        assert sql == (
            "SELECT `INDEX_NAME`, `NON_UNIQUE`, `SEQ_IN_INDEX`, `COLUMN_NAME`, "
            "`INDEX_TYPE`, `SUB_PART`, `NULLABLE` "
            "FROM `information_schema`.`STATISTICS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s "
            "ORDER BY `INDEX_NAME`, `SEQ_IN_INDEX`"
        )
        assert params == ("app", "users")

    def test_foreign_key_joins_on_both_name_and_schema(self, dialect):
        sql, params = ForeignKeyQueryStatement(dialect, "users", schema="app").to_sql()
        assert sql == (
            "SELECT `kcu`.`CONSTRAINT_NAME`, `kcu`.`COLUMN_NAME`, "
            "`kcu`.`ORDINAL_POSITION`, `kcu`.`REFERENCED_TABLE_NAME`, "
            "`kcu`.`REFERENCED_COLUMN_NAME`, `rc`.`UPDATE_RULE`, "
            "`rc`.`DELETE_RULE` "
            "FROM `information_schema`.`KEY_COLUMN_USAGE` AS `kcu` "
            "JOIN `information_schema`.`REFERENTIAL_CONSTRAINTS` AS `rc` "
            "ON `kcu`.`CONSTRAINT_NAME` = `rc`.`CONSTRAINT_NAME` "
            "AND `kcu`.`CONSTRAINT_SCHEMA` = `rc`.`CONSTRAINT_SCHEMA` "
            "WHERE `kcu`.`TABLE_SCHEMA` = %s AND `kcu`.`TABLE_NAME` = %s "
            "AND `kcu`.`REFERENCED_TABLE_NAME` IS NOT NULL "
            "ORDER BY `kcu`.`CONSTRAINT_NAME`, `kcu`.`ORDINAL_POSITION`"
        )
        assert params == ("app", "users")

    def test_view_list_orders_by_name(self, dialect):
        sql, params = ViewListQueryStatement(dialect, schema="app").to_sql()
        assert sql == (
            "SELECT `TABLE_NAME`, `VIEW_DEFINITION`, `CHECK_OPTION`, `IS_UPDATABLE` "
            "FROM `information_schema`.`VIEWS` "
            "WHERE `TABLE_SCHEMA` = %s AND NOT (`TABLE_SCHEMA` IN "
            "('information_schema', 'performance_schema', 'mysql', 'sys')) "
            "ORDER BY `TABLE_NAME`"
        )
        assert params == ("app",)

    def test_view_list_include_system(self, dialect):
        sql, params = ViewListQueryStatement(
            dialect, schema="app", include_system=True
        ).to_sql()
        assert "NOT (" not in sql
        assert params == ("app",)

    def test_view_info_has_no_ordering(self, dialect):
        sql, params = ViewInfoQueryStatement(dialect, "v_users", schema="app").to_sql()
        assert sql == (
            "SELECT `TABLE_NAME`, `VIEW_DEFINITION`, `CHECK_OPTION`, `IS_UPDATABLE` "
            "FROM `information_schema`.`VIEWS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s"
        )
        assert params == ("app", "v_users")

    def test_trigger_list_without_a_table(self, dialect):
        sql, params = TriggerListQueryStatement(dialect, schema="app").to_sql()
        assert sql == (
            "SELECT `TRIGGER_NAME`, `EVENT_MANIPULATION`, `EVENT_OBJECT_TABLE`, "
            "`ACTION_TIMING`, `ACTION_STATEMENT`, `CREATED` "
            "FROM `information_schema`.`TRIGGERS` "
            "WHERE `TRIGGER_SCHEMA` = %s ORDER BY `TRIGGER_NAME`"
        )
        assert params == ("app",)

    def test_trigger_list_with_a_table_binds_it(self, dialect):
        sql, params = TriggerListQueryStatement(
            dialect, schema="app", table_name="users"
        ).to_sql()
        assert sql == (
            "SELECT `TRIGGER_NAME`, `EVENT_MANIPULATION`, `EVENT_OBJECT_TABLE`, "
            "`ACTION_TIMING`, `ACTION_STATEMENT`, `CREATED` "
            "FROM `information_schema`.`TRIGGERS` "
            "WHERE `TRIGGER_SCHEMA` = %s AND `EVENT_OBJECT_TABLE` = %s "
            "ORDER BY `TRIGGER_NAME`"
        )
        assert params == ("app", "users")


class TestPartitionRoutineConstraintQueries:
    """The three families added for introspection coverage."""

    def test_partition_query_excludes_the_non_partitioned_row(self, dialect):
        sql, params = MariaDBPartitionQuery(dialect, "app", "orders").to_sql()
        assert sql == (
            "SELECT `PARTITION_NAME`, `SUBPARTITION_NAME`, `PARTITION_METHOD`, "
            "`SUBPARTITION_METHOD`, `PARTITION_EXPRESSION`, "
            "`SUBPARTITION_EXPRESSION`, `PARTITION_DESCRIPTION`, "
            "`PARTITION_ORDINAL_POSITION`, "
            "`SUBPARTITION_ORDINAL_POSITION`, `TABLE_ROWS`, `DATA_LENGTH`, "
            "`INDEX_LENGTH`, `PARTITION_COMMENT` "
            "FROM `information_schema`.`PARTITIONS` "
            "WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s "
            "AND `PARTITION_NAME` IS NOT NULL "
            "ORDER BY `PARTITION_ORDINAL_POSITION`, "
            "`SUBPARTITION_ORDINAL_POSITION`"
        )
        assert params == ("app", "orders")

    def test_routine_query_joins_on_schema_name_and_kind(self, dialect):
        sql, params = MariaDBRoutineQuery(dialect, "app").to_sql()
        assert "LEFT JOIN `information_schema`.`PARAMETERS` AS `p`" in sql
        assert (
            "`p`.`SPECIFIC_SCHEMA` = `r`.`ROUTINE_SCHEMA` "
            "AND `p`.`SPECIFIC_NAME` = `r`.`ROUTINE_NAME` "
            "AND `p`.`ROUTINE_TYPE` = `r`.`ROUTINE_TYPE`"
        ) in sql
        assert params == ("app",)

    def test_routine_query_aliases_the_two_data_type_columns(self, dialect):
        """ROUTINES and PARAMETERS both have DATA_TYPE; one row cannot hold both."""
        sql, _ = MariaDBRoutineQuery(dialect, "app").to_sql()
        assert "`r`.`DATA_TYPE` AS `ROUTINE_DATA_TYPE`" in sql
        assert "`r`.`DTD_IDENTIFIER` AS `ROUTINE_DTD_IDENTIFIER`" in sql
        assert "`p`.`DATA_TYPE` AS `PARAMETER_DATA_TYPE`" in sql
        assert "`p`.`DTD_IDENTIFIER` AS `PARAMETER_DTD_IDENTIFIER`" in sql

    def test_routine_query_name_and_kind_are_bound_only_when_given(self):
        """A whole-schema listing binds only the schema."""
        dialect = MariaDBDialect(version=(10, 6, 0))
        _, listing_params = MariaDBRoutineQuery(dialect, "app").to_sql()
        assert listing_params == ("app",)

        sql, params = MariaDBRoutineQuery(
            dialect, "app", name="app_cleanup", kind="PROCEDURE"
        ).to_sql()
        assert "`r`.`ROUTINE_NAME` = %s" in sql
        assert "`r`.`ROUTINE_TYPE` = %s" in sql
        assert params == ("app", "app_cleanup", "PROCEDURE")

    def test_constraint_query_filters_check_inline(self, dialect):
        sql, params = MariaDBConstraintQuery(dialect, "app", "orders").to_sql()
        assert (
            "FROM `information_schema`.`TABLE_CONSTRAINTS` AS `tc` "
            "LEFT JOIN `information_schema`.`CHECK_CONSTRAINTS` AS `cc` "
            "ON `tc`.`CONSTRAINT_SCHEMA` = `cc`.`CONSTRAINT_SCHEMA` "
            "AND `tc`.`CONSTRAINT_NAME` = `cc`.`CONSTRAINT_NAME`"
        ) in sql
        assert "`tc`.`CONSTRAINT_TYPE` = 'CHECK'" in sql
        assert params == ("app", "orders")

    def test_constraint_query_does_not_put_the_type_in_the_tuple(self, dialect):
        """The type is a catalog fact, not caller data."""
        _, params = MariaDBConstraintQuery(dialect, "app", "orders").to_sql()
        assert "CHECK" not in params


class TestNewFamilyCapabilitySwitches:
    """Each family's probe answers for the family it governs."""

    def test_partition_info_is_declared(self, dialect):
        """Core's probe and the DDL protocol's probe answer the same."""
        assert dialect.supports_partition_info() is True
        assert dialect.supports_partition_metadata_introspection() is True

    def test_routine_introspection_is_declared(self, dialect):
        assert dialect.supports_routine_introspection() is True

    def test_constraint_introspection_follows_the_check_release(self):
        """No second copy of the 10.2.1 boundary."""
        old = MariaDBDialect(version=(10, 2, 0))
        new = MariaDBDialect(version=(10, 2, 1))
        assert old.supports_constraint_introspection() is False
        assert new.supports_constraint_introspection() is True
        assert new.supports_constraint_introspection() is (
            new.supports_check_constraint()
        )

    def test_old_server_also_reports_check_as_unsupported(self):
        """The two questions agree on every boundary the backend claims."""
        for version in ((10, 2, 0), (10, 2, 1), (10, 4, 34), (13, 1, 1)):
            dialect = MariaDBDialect(version)
            assert (
                dialect.supports_constraint_introspection()
                is dialect.supports_check_constraint()
            ), version


class TestSharedCatalogueConstants:
    """``information_schema`` is a catalog slot; the exclusions are data."""

    def test_information_schema_is_named_through_the_catalog_slot(self, dialect):
        relation = dialect._information_schema("TABLES")
        assert relation.catalog_name == INFORMATION_SCHEMA_DATABASE
        assert relation.schema_name is None
        assert relation.to_sql() == ("`information_schema`.`TABLES`", ())

    def test_the_system_schema_list_is_inlined_not_bound(self, dialect):
        """A catalogue fact, not caller data -- so the tuple stays as it was."""
        sql, params = dialect.system_schemas_predicate().to_sql()
        assert params == ()
        for schema in SYSTEM_SCHEMAS:
            assert f"'{schema}'" in sql


class TestQueryNodesStayStructures:
    """The reason the text moved into the formatter: the tree is inspectable."""

    def test_a_value_with_a_quote_cannot_break_the_statement(self, dialect):
        """A bound value is data; the formatter never splices it into text."""
        hostile = "app'; DROP TABLE users; --"
        sql, params = TableListQueryStatement(dialect, schema=hostile).to_sql()
        assert hostile not in sql
        assert params == (hostile,)

    def test_the_projection_is_an_expression_list(self, dialect):
        """What a query asks is a tree, and the caller can read it."""
        query = QueryStatement(dialect, select=[Literal(dialect, 1, inline=True)])
        assert query.to_sql() == ("SELECT 1", ())
