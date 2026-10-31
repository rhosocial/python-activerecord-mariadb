# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_show_expressions.py
"""Offline tests for the MariaDB SHOW expression classes.

Covers the keyword-only ``__init__`` parameters (schema/full/like_pattern/
session/limit/user/host/table_name), which the introspection-based
``get_params()`` reads back for serialization and for the dialect's
``format_show_*`` methods.

Every parameter is given at construction. There is deliberately no fluent
surface to test: a statement is complete when it is built, so the artifact is
the constructor call and nothing else.
"""
import pytest

from rhosocial.activerecord.backend.expression.objects import Table, Trigger, View
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    ShowCharsetStatement,
    ShowCollationStatement,
    ShowColumnsStatement,
    ShowDatabasesStatement,
    ShowErrorsStatement,
    ShowExpression,
    ShowGrantsStatement,
    ShowProcessListStatement,
    ShowCreateTableStatement,
    ShowCreateTriggerStatement,
    ShowCreateViewStatement,
    ShowIndexStatement,
    ShowStatusStatement,
    ShowTableStatusStatement,
    ShowTablesStatement,
    ShowTriggersStatement,
    ShowVariablesStatement,
    ShowWarningsStatement,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestShowRelationExpressions:
    """The four relation-named statements name their target as one object.

    The database lives inside the relation object (``catalog_name``) rather
    than on the statement, so a qualified target is expressible and the same
    qualified-name renderer serves every one of them.
    """

    def test_create_table_qualified_through_the_relation(self, dialect):
        expr = ShowCreateTableStatement(
            dialect, Table(dialect, "users", catalog_name="app")
        )
        assert expr.to_sql() == ("SHOW CREATE TABLE `app`.`users`", ())

    def test_create_view_takes_a_view(self, dialect):
        expr = ShowCreateViewStatement(dialect, View(dialect, "v_users"))
        assert expr.to_sql() == ("SHOW CREATE VIEW `v_users`", ())

    def test_create_trigger_qualified_through_the_trigger(self, dialect):
        expr = ShowCreateTriggerStatement(
            dialect, Trigger(dialect, "trg", catalog_name="app")
        )
        assert expr.to_sql() == ("SHOW CREATE TRIGGER `app`.`trg`", ())

    def test_index_qualified_through_the_relation(self, dialect):
        expr = ShowIndexStatement(
            dialect, Table(dialect, "users", catalog_name="app")
        )
        assert expr.to_sql() == ("SHOW INDEX FROM `app`.`users`", ())

    def test_a_tuple_target_is_refused(self, dialect):
        with pytest.raises(TypeError, match="not \\(database, name\\) tuples"):
            ShowCreateTableStatement(dialect, ("app", "users"))

    def test_schema_init_param(self, dialect):
        expr = ShowExpression(dialect, schema="app")
        assert expr.get_params() == {"schema": "app"}

    def test_no_fluent_setter_survives(self, dialect):
        """A SHOW statement has no chained-parameter surface.

        Every parameter is a construction field, so a ``with_*`` method would be
        a second way to say the same thing -- and the one the artifact cannot
        express, because the artifact is the constructor call.
        """
        expr = ShowExpression(dialect, schema="app")
        assert not hasattr(expr, "with_schema")
        assert expr.get_params() == {"schema": "app"}

    def test_to_sql_not_implemented(self, dialect):
        with pytest.raises(NotImplementedError):
            ShowExpression(dialect).to_sql()


class TestShowColumnsExpression:
    def test_keyword_params(self, dialect):
        expr = ShowColumnsStatement(
            dialect, Table(dialect, "users"), full=True, like_pattern="%a%"
        )
        # get_params() introspects __init__, so the parameter is named after
        # the slot rather than after a table specifically: a SHOW COLUMNS
        # target is a relation, and get_params() reports it as one.
        assert expr.get_params() == {
            "relation": Table(dialect, "users"),
            "full": True,
            "like_pattern": "%a%",
        }
        assert expr.to_sql() == ("SHOW FULL COLUMNS FROM `users` LIKE %s", ("%a%",))

    def test_default_params(self, dialect):
        expr = ShowColumnsStatement(dialect, Table(dialect, "users"))
        assert expr.get_params() == {
            "relation": Table(dialect, "users"), "full": False, "like_pattern": None
        }
        assert expr.to_sql() == ("SHOW COLUMNS FROM `users`", ())


class TestShowTablesExpression:
    def test_keyword_params(self, dialect):
        expr = ShowTablesStatement(dialect, full=True, like_pattern="t%")
        assert expr.get_params() == {
            "schema": None, "full": True, "like_pattern": "t%"
        }
        assert expr.to_sql() == ("SHOW FULL TABLES LIKE %s", ("t%",))

    def test_schema_param_reaches_the_from_clause(self, dialect):
        expr = ShowTablesStatement(dialect, schema="app", full=True)
        assert expr.get_params() == {
            "schema": "app", "full": True, "like_pattern": None
        }
        assert expr.to_sql() == ("SHOW FULL TABLES FROM `app`", ())

    def test_all_options_at_construction(self, dialect):
        expr = ShowTablesStatement(dialect, schema="app", full=True, like_pattern="t%")
        assert expr.get_params() == {
            "schema": "app", "full": True, "like_pattern": "t%"
        }
        assert expr.to_sql() == ("SHOW FULL TABLES FROM `app` LIKE %s", ("t%",))


class TestShowDatabasesExpression:
    def test_keyword_param(self, dialect):
        expr = ShowDatabasesStatement(dialect, like_pattern="app%")
        assert expr.get_params() == {"like_pattern": "app%"}
        assert expr.to_sql() == ("SHOW DATABASES LIKE %s", ("app%",))

    def test_no_pattern(self, dialect):
        assert ShowDatabasesStatement(dialect).to_sql() == ("SHOW DATABASES", ())


class TestShowTableStatusExpression:
    def test_keyword_param(self, dialect):
        expr = ShowTableStatusStatement(dialect, like_pattern="log_%")
        assert expr.get_params() == {
            "schema": None, "like_pattern": "log_%"
        }
        assert expr.to_sql() == ("SHOW TABLE STATUS LIKE %s", ("log_%",))

    def test_schema_param_reaches_the_from_clause(self, dialect):
        expr = ShowTableStatusStatement(dialect, schema="app")
        assert expr.to_sql() == ("SHOW TABLE STATUS FROM `app`", ())

    def test_no_pattern(self, dialect):
        assert ShowTableStatusStatement(dialect).to_sql() == ("SHOW TABLE STATUS", ())


class TestShowTriggersExpression:
    def test_keyword_param(self, dialect):
        expr = ShowTriggersStatement(dialect, table_name="orders")
        assert expr.get_params() == {
            "schema": None, "table_name": "orders"
        }
        assert expr.to_sql() == ("SHOW TRIGGERS LIKE %s", ("orders",))

    def test_schema_param_reaches_the_from_clause(self, dialect):
        expr = ShowTriggersStatement(dialect, schema="app", table_name="orders")
        assert expr.to_sql() == ("SHOW TRIGGERS FROM `app` LIKE %s", ("orders",))

    def test_no_table(self, dialect):
        assert ShowTriggersStatement(dialect).to_sql() == ("SHOW TRIGGERS", ())


class TestShowVariablesExpression:
    def test_keyword_params_global(self, dialect):
        expr = ShowVariablesStatement(dialect, like_pattern="%ver%", session=False)
        assert expr.get_params() == {"like_pattern": "%ver%", "session": False}
        assert expr.to_sql() == ("SHOW GLOBAL VARIABLES LIKE %s", ("%ver%",))

    def test_default_session(self, dialect):
        expr = ShowVariablesStatement(dialect)
        assert expr.get_params() == {"like_pattern": None, "session": True}
        assert expr.to_sql() == ("SHOW VARIABLES", ())


class TestShowStatusExpression:
    def test_keyword_params_global(self, dialect):
        expr = ShowStatusStatement(dialect, like_pattern="Threads%", session=False)
        assert expr.get_params() == {"like_pattern": "Threads%", "session": False}
        assert expr.to_sql() == ("SHOW GLOBAL STATUS LIKE %s", ("Threads%",))

    def test_default_session(self, dialect):
        assert ShowStatusStatement(dialect).to_sql() == ("SHOW STATUS", ())


class TestShowProcessListExpression:
    def test_keyword_param(self, dialect):
        expr = ShowProcessListStatement(dialect, full=True)
        assert expr.get_params() == {"full": True}
        assert expr.to_sql() == ("SHOW FULL PROCESSLIST", ())

    def test_default(self, dialect):
        assert ShowProcessListStatement(dialect).to_sql() == ("SHOW PROCESSLIST", ())


class TestShowWarningsExpression:
    def test_keyword_param(self, dialect):
        expr = ShowWarningsStatement(dialect, limit=5)
        assert expr.get_params() == {"limit": 5}
        assert expr.to_sql() == ("SHOW WARNINGS LIMIT 5", ())

    def test_default(self, dialect):
        assert ShowWarningsStatement(dialect).to_sql() == ("SHOW WARNINGS", ())


class TestShowErrorsExpression:
    def test_keyword_param(self, dialect):
        expr = ShowErrorsStatement(dialect, limit=10)
        assert expr.get_params() == {"limit": 10}
        assert expr.to_sql() == ("SHOW ERRORS LIMIT 10", ())

    def test_default(self, dialect):
        assert ShowErrorsStatement(dialect).to_sql() == ("SHOW ERRORS", ())


class TestShowCharsetExpression:
    def test_keyword_param(self, dialect):
        expr = ShowCharsetStatement(dialect, like_pattern="utf8%")
        assert expr.get_params() == {"like_pattern": "utf8%"}
        assert expr.to_sql() == ("SHOW CHARACTER SET LIKE %s", ("utf8%",))

    def test_default(self, dialect):
        assert ShowCharsetStatement(dialect).to_sql() == ("SHOW CHARACTER SET", ())


class TestShowCollationExpression:
    def test_keyword_param(self, dialect):
        expr = ShowCollationStatement(dialect, like_pattern="utf8%")
        assert expr.get_params() == {"like_pattern": "utf8%"}
        assert expr.to_sql() == ("SHOW COLLATION LIKE %s", ("utf8%",))

    def test_default(self, dialect):
        assert ShowCollationStatement(dialect).to_sql() == ("SHOW COLLATION", ())


class TestShowGrantsExpression:
    def test_keyword_params_user_host(self, dialect):
        expr = ShowGrantsStatement(dialect, user="app", host="localhost")
        assert expr.get_params() == {"user": "app", "host": "localhost"}
        assert expr.to_sql() == ("SHOW GRANTS FOR %s@%s", ("app", "localhost"))

    def test_user_only(self, dialect):
        expr = ShowGrantsStatement(dialect, user="app")
        assert expr.get_params() == {"user": "app", "host": None}
        assert expr.to_sql() == ("SHOW GRANTS FOR %s", ("app",))

    def test_default(self, dialect):
        assert ShowGrantsStatement(dialect).to_sql() == ("SHOW GRANTS", ())
