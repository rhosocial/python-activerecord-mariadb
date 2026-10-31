# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_show_statements.py
"""Offline assertions on the SHOW and status statements' rendered SQL.

Two things are pinned here:

* the statements the status layer used to spell as f-strings and string
  literals -- ``SHOW VARIABLES LIKE '...'``, ``SHOW GLOBAL STATUS LIKE '...'``,
  ``SELECT VERSION()``, the storage totals, the database list, the user list and
  the session facts -- now render from nodes, and their text and bind parameters
  are what the server sees;
* the ``@@`` sigil and the ``SHOW`` verbs are the dialect's spelling, so the
  node carries a name and nothing else.

Whitespace and identifier quoting are the formatter's business and are written
as rendered.
"""
import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    ShowStatusStatement,
    ShowVariablesStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.status import (
    MariaDBDatabaseListQuery,
    MariaDBSessionInfoQuery,
    MariaDBStorageSizeQuery,
    MariaDBSystemVariableExpression,
    MariaDBUserListQuery,
    MariaDBVersionQuery,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestSystemVariableExpression:
    """The ``@@`` sigil is the dialect's spelling; the name is the node's."""

    def test_bare_variable(self, dialect):
        assert MariaDBSystemVariableExpression(dialect, "have_ssl").to_sql() == (
            "@@have_ssl",
            (),
        )

    def test_variable_with_alias(self, dialect):
        assert MariaDBSystemVariableExpression(
            dialect, "hostname", alias="host"
        ).to_sql() == ("@@hostname AS `host`", ())

    @pytest.mark.parametrize(
        "name", ["", "have ssl", "have_ssl'", "@/@hostname", "1hostname"]
    )
    def test_a_name_that_is_not_an_identifier_is_refused(self, dialect, name):
        """A name carrying a quote or a space fails at the caller, not at the server."""
        with pytest.raises(ValueError, match="system variable name is an identifier"):
            MariaDBSystemVariableExpression(dialect, name)

    def test_a_dotted_name_is_accepted(self, dialect):
        assert MariaDBSystemVariableExpression(
            dialect, "innodb.lock_wait_timeout"
        ).to_sql() == ("@@innodb.lock_wait_timeout", ())


class TestStatusQueries:
    """The status introspector's catalogue reads."""

    def test_version_query_reads_no_relation(self, dialect):
        assert MariaDBVersionQuery(dialect).to_sql() == ("SELECT VERSION()", ())

    def test_storage_totals_exclude_the_system_schemas(self, dialect):
        sql, params = MariaDBStorageSizeQuery(dialect).to_sql()
        assert sql == (
            "SELECT SUM(`data_length`) AS `data_bytes`, "
            "SUM(`index_length`) AS `index_bytes` "
            "FROM `information_schema`.`TABLES` "
            "WHERE NOT (`TABLE_SCHEMA` IN "
            "('information_schema', 'performance_schema', 'mysql', 'sys'))"
        )
        assert params == ()

    def test_database_list_groups_and_counts_by_type(self, dialect):
        sql, params = MariaDBDatabaseListQuery(dialect).to_sql()
        assert sql == (
            "SELECT `s`.`schema_name`, "
            "SUM(`t`.`data_length` + `t`.`index_length`) AS `size_bytes`, "
            "COUNT(CASE WHEN `t`.`table_type` = 'BASE TABLE' THEN 1 END) AS `table_count`, "
            "COUNT(CASE WHEN `t`.`table_type` = 'VIEW' THEN 1 END) AS `view_count` "
            "FROM `information_schema`.`SCHEMATA` AS `s` "
            "LEFT JOIN `information_schema`.`TABLES` AS `t` "
            "ON `s`.`schema_name` = `t`.`table_schema` "
            "GROUP BY `s`.`schema_name` ORDER BY `s`.`schema_name`"
        )
        assert params == ()

    def test_user_list_names_the_mysql_catalogue(self, dialect):
        sql, params = MariaDBUserListQuery(dialect).to_sql()
        assert sql == (
            "SELECT `user`, `host`, `Super_priv` FROM `mysql`.`user` "
            "ORDER BY `user`"
        )
        assert params == ()

    def test_session_info_mixes_functions_and_variables(self, dialect):
        sql, params = MariaDBSessionInfoQuery(dialect).to_sql()
        assert sql == (
            "SELECT CURRENT_USER() AS `cur_user`, DATABASE() AS `cur_db`, "
            "@@hostname AS `host`, @@have_ssl AS `have_ssl`"
        )
        assert params == ()


class TestStatusReadsGoThroughShowNodes:
    """The two reads the status introspector used to spell as f-strings."""

    def test_session_variables(self, dialect):
        assert ShowVariablesStatement(
            dialect, like_pattern="max_connections"
        ).to_sql() == ("SHOW VARIABLES LIKE %s", ("max_connections",))

    def test_global_status(self, dialect):
        assert ShowStatusStatement(
            dialect, like_pattern="Threads_connected", session=False
        ).to_sql() == ("SHOW GLOBAL STATUS LIKE %s", ("Threads_connected",))

    @pytest.mark.parametrize(
        "name", ["max_connections", "Threads_connected", "Ssl_version"]
    )
    def test_a_read_name_is_bound_not_spliced(self, dialect, name):
        """The name is data: it reaches the server as a parameter, never as text."""
        sql, params = ShowVariablesStatement(dialect, like_pattern=name).to_sql()
        assert name not in sql
        assert params == (name,)

    def test_a_hostile_name_cannot_break_the_statement(self, dialect):
        hostile = "x' OR '1'='1"
        sql, params = ShowStatusStatement(
            dialect, like_pattern=hostile, session=False
        ).to_sql()
        assert hostile not in sql
        assert params == (hostile,)
