# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_show_expressions.py
"""Offline tests for the MariaDB SHOW expression classes.

Covers the keyword-only ``__init__`` parameters folded from the fluent
API (schema/full/like_pattern/session/limit/user/host/table_name), which
the introspection-based ``get_params()`` reads back for serialization and
for the dialect's ``format_show_*`` methods.
"""
import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.show.expressions import (
    ShowCharsetExpression,
    ShowCollationExpression,
    ShowColumnsExpression,
    ShowDatabasesExpression,
    ShowErrorsExpression,
    ShowExpression,
    ShowGrantsExpression,
    ShowProcessListExpression,
    ShowStatusExpression,
    ShowTableStatusExpression,
    ShowTablesExpression,
    ShowTriggersExpression,
    ShowVariablesExpression,
    ShowWarningsExpression,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestShowExpressionBase:
    def test_schema_init_param(self, dialect):
        expr = ShowExpression(dialect, schema="app")
        assert expr.get_params() == {"schema": "app"}

    def test_schema_fluent(self, dialect):
        expr = ShowExpression(dialect).schema("app")
        assert expr.get_params() == {"schema": "app"}

    def test_to_sql_not_implemented(self, dialect):
        with pytest.raises(NotImplementedError):
            ShowExpression(dialect).to_sql()


class TestShowColumnsExpression:
    def test_keyword_params(self, dialect):
        expr = ShowColumnsExpression(dialect, "users", full=True, like_pattern="%a%")
        assert expr.get_params() == {
            "table": "users",
            "full": True,
            "like_pattern": "%a%",
        }
        assert expr.to_sql() == ("SHOW FULL COLUMNS FROM `users` LIKE %s", ("%a%",))

    def test_default_params(self, dialect):
        expr = ShowColumnsExpression(dialect, "users")
        assert expr.get_params() == {
            "table": "users", "full": False, "like_pattern": None
        }
        assert expr.to_sql() == ("SHOW COLUMNS FROM `users`", ())


class TestShowTablesExpression:
    def test_keyword_params(self, dialect):
        expr = ShowTablesExpression(dialect, full=True, like_pattern="t%")
        assert expr.get_params() == {"full": True, "like_pattern": "t%"}
        assert expr.to_sql() == ("SHOW FULL TABLES LIKE %s", ("t%",))

    def test_fluent_api(self, dialect):
        expr = ShowTablesExpression(dialect).full().like("t%")
        assert expr.get_params() == {"full": True, "like_pattern": "t%"}
        assert expr.to_sql() == ("SHOW FULL TABLES LIKE %s", ("t%",))


class TestShowDatabasesExpression:
    def test_keyword_param(self, dialect):
        expr = ShowDatabasesExpression(dialect, like_pattern="app%")
        assert expr.get_params() == {"like_pattern": "app%"}
        assert expr.to_sql() == ("SHOW DATABASES LIKE %s", ("app%",))

    def test_no_pattern(self, dialect):
        assert ShowDatabasesExpression(dialect).to_sql() == ("SHOW DATABASES", ())


class TestShowTableStatusExpression:
    def test_keyword_param(self, dialect):
        expr = ShowTableStatusExpression(dialect, like_pattern="log_%")
        assert expr.get_params() == {"like_pattern": "log_%"}
        assert expr.to_sql() == ("SHOW TABLE STATUS LIKE %s", ("log_%",))

    def test_no_pattern(self, dialect):
        assert ShowTableStatusExpression(dialect).to_sql() == ("SHOW TABLE STATUS", ())


class TestShowTriggersExpression:
    def test_keyword_param(self, dialect):
        expr = ShowTriggersExpression(dialect, table="orders")
        assert expr.get_params() == {"table": "orders"}
        assert expr.to_sql() == ("SHOW TRIGGERS LIKE %s", ("orders",))

    def test_no_table(self, dialect):
        assert ShowTriggersExpression(dialect).to_sql() == ("SHOW TRIGGERS", ())


class TestShowVariablesExpression:
    def test_keyword_params_global(self, dialect):
        expr = ShowVariablesExpression(dialect, like_pattern="%ver%", session=False)
        assert expr.get_params() == {"like_pattern": "%ver%", "session": False}
        assert expr.to_sql() == ("SHOW GLOBAL VARIABLES LIKE %s", ("%ver%",))

    def test_default_session(self, dialect):
        expr = ShowVariablesExpression(dialect)
        assert expr.get_params() == {"like_pattern": None, "session": True}
        assert expr.to_sql() == ("SHOW VARIABLES", ())


class TestShowStatusExpression:
    def test_keyword_params_global(self, dialect):
        expr = ShowStatusExpression(dialect, like_pattern="Threads%", session=False)
        assert expr.get_params() == {"like_pattern": "Threads%", "session": False}
        assert expr.to_sql() == ("SHOW GLOBAL STATUS LIKE %s", ("Threads%",))

    def test_default_session(self, dialect):
        assert ShowStatusExpression(dialect).to_sql() == ("SHOW STATUS", ())


class TestShowProcessListExpression:
    def test_keyword_param(self, dialect):
        expr = ShowProcessListExpression(dialect, full=True)
        assert expr.get_params() == {"full": True}
        assert expr.to_sql() == ("SHOW FULL PROCESSLIST", ())

    def test_default(self, dialect):
        assert ShowProcessListExpression(dialect).to_sql() == ("SHOW PROCESSLIST", ())


class TestShowWarningsExpression:
    def test_keyword_param(self, dialect):
        expr = ShowWarningsExpression(dialect, limit=5)
        assert expr.get_params() == {"limit": 5}
        assert expr.to_sql() == ("SHOW WARNINGS LIMIT 5", ())

    def test_default(self, dialect):
        assert ShowWarningsExpression(dialect).to_sql() == ("SHOW WARNINGS", ())


class TestShowErrorsExpression:
    def test_keyword_param(self, dialect):
        expr = ShowErrorsExpression(dialect, limit=10)
        assert expr.get_params() == {"limit": 10}
        assert expr.to_sql() == ("SHOW ERRORS LIMIT 10", ())

    def test_default(self, dialect):
        assert ShowErrorsExpression(dialect).to_sql() == ("SHOW ERRORS", ())


class TestShowCharsetExpression:
    def test_keyword_param(self, dialect):
        expr = ShowCharsetExpression(dialect, like_pattern="utf8%")
        assert expr.get_params() == {"like_pattern": "utf8%"}
        assert expr.to_sql() == ("SHOW CHARACTER SET LIKE %s", ("utf8%",))

    def test_default(self, dialect):
        assert ShowCharsetExpression(dialect).to_sql() == ("SHOW CHARACTER SET", ())


class TestShowCollationExpression:
    def test_keyword_param(self, dialect):
        expr = ShowCollationExpression(dialect, like_pattern="utf8%")
        assert expr.get_params() == {"like_pattern": "utf8%"}
        assert expr.to_sql() == ("SHOW COLLATION LIKE %s", ("utf8%",))

    def test_default(self, dialect):
        assert ShowCollationExpression(dialect).to_sql() == ("SHOW COLLATION", ())


class TestShowGrantsExpression:
    def test_keyword_params_user_host(self, dialect):
        expr = ShowGrantsExpression(dialect, user="app", host="localhost")
        assert expr.get_params() == {"user": "app", "host": "localhost"}
        assert expr.to_sql() == ("SHOW GRANTS FOR %s@%s", ("app", "localhost"))

    def test_user_only(self, dialect):
        expr = ShowGrantsExpression(dialect, user="app")
        assert expr.get_params() == {"user": "app", "host": None}
        assert expr.to_sql() == ("SHOW GRANTS FOR %s", ("app",))

    def test_default(self, dialect):
        assert ShowGrantsExpression(dialect).to_sql() == ("SHOW GRANTS", ())
