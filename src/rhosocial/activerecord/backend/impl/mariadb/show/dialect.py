# src/rhosocial/activerecord/backend/impl/mariadb/show/dialect.py
"""
MariaDB SHOW command dialect mixin.

This module provides the MariaDB-specific SQL generation for SHOW commands.
It implements the format_show_* methods that are called by the expression classes.

MariaDB SHOW commands are fully compatible with MySQL SHOW commands.

The mixin is added to MariaDBDialect to provide SHOW command support.
All methods follow the pattern:
- Accept an expression parameter
- Extract parameters from expression.get_params()
- Generate SQL string and parameter tuple
- Return (sql, params) tuple
"""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .expressions import (
        ShowCreateTableExpression,
        ShowCreateViewExpression,
        ShowColumnsExpression,
        ShowIndexExpression,
        ShowTablesExpression,
        ShowDatabasesExpression,
        ShowTableStatusExpression,
        ShowTriggersExpression,
        ShowCreateTriggerExpression,
        ShowVariablesExpression,
        ShowStatusExpression,
        ShowProcessListExpression,
        ShowWarningsExpression,
        ShowErrorsExpression,
        ShowEnginesExpression,
        ShowCharsetExpression,
        ShowCollationExpression,
        ShowGrantsExpression,
        ShowPluginsExpression,
    )


class MariaDBShowDialectMixin:
    """MariaDB SHOW command SQL generation mixin.

    Provides format_show_* methods for generating MariaDB SHOW command SQL.
    All methods take an expression parameter and return (sql, params) tuple.

    This mixin is added to MariaDBDialect to provide SHOW functionality.
    """

    # ========== SHOW CREATE Statements ==========

    def format_show_create_table(
        self, expr: "ShowCreateTableExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE TABLE statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")

        if schema:
            sql = f"SHOW CREATE TABLE {self.format_identifier(schema)}.{self.format_identifier(table_name)}"
        else:
            sql = f"SHOW CREATE TABLE {self.format_identifier(table_name)}"
        return sql, ()

    def format_show_create_view(
        self, expr: "ShowCreateViewExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE VIEW statement."""
        params = expr.get_params()
        view_name = params["view_name"]
        schema = params.get("schema")

        if schema:
            sql = f"SHOW CREATE VIEW {self.format_identifier(schema)}.{self.format_identifier(view_name)}"
        else:
            sql = f"SHOW CREATE VIEW {self.format_identifier(view_name)}"
        return sql, ()

    def format_show_create_trigger(
        self, expr: "ShowCreateTriggerExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE TRIGGER statement."""
        params = expr.get_params()
        trigger_name = params["trigger_name"]
        schema = params.get("schema")

        if schema:
            sql = f"SHOW CREATE TRIGGER {self.format_identifier(schema)}.{self.format_identifier(trigger_name)}"
        else:
            sql = f"SHOW CREATE TRIGGER {self.format_identifier(trigger_name)}"
        return sql, ()

    # ========== SHOW COLUMNS/INDEX ==========

    def format_show_columns(self, expr: "ShowColumnsExpression") -> Tuple[str, tuple]:
        """Format SHOW [FULL] COLUMNS statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")
        full = params.get("full", False)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("COLUMNS FROM")
        if schema:
            parts.append(f"{self.format_identifier(schema)}.")
        parts.append(self.format_identifier(table_name))

        sql_params = ()
        if like_pattern:
            parts.append("LIKE %s")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_index(self, expr: "ShowIndexExpression") -> Tuple[str, tuple]:
        """Format SHOW INDEX statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")

        if schema:
            sql = f"SHOW INDEX FROM {self.format_identifier(schema)}.{self.format_identifier(table_name)}"
        else:
            sql = f"SHOW INDEX FROM {self.format_identifier(table_name)}"
        return sql, ()

    # ========== SHOW TABLES/DATABASES ==========

    def format_show_tables(self, expr: "ShowTablesExpression") -> Tuple[str, tuple]:
        """Format SHOW [FULL] TABLES statement."""
        params = expr.get_params()
        schema = params.get("schema")
        full = params.get("full", False)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("TABLES")
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append("LIKE %s")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_databases(
        self, expr: "ShowDatabasesExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW DATABASES statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return "SHOW DATABASES LIKE %s", (like_pattern,)
        return "SHOW DATABASES", ()

    def format_show_table_status(
        self, expr: "ShowTableStatusExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW TABLE STATUS statement."""
        params = expr.get_params()
        schema = params.get("schema")
        like_pattern = params.get("like_pattern")

        parts = ["SHOW TABLE STATUS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append("LIKE %s")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW TRIGGERS ==========

    def format_show_triggers(
        self, expr: "ShowTriggersExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW TRIGGERS statement."""
        params = expr.get_params()
        schema = params.get("schema")
        table_name = params.get("table_name")

        parts = ["SHOW TRIGGERS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if table_name:
            parts.append("LIKE %s")
            sql_params = (table_name,)

        return " ".join(parts), sql_params

    # ========== SHOW VARIABLES/STATUS ==========

    def format_show_variables(
        self, expr: "ShowVariablesExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW VARIABLES statement."""
        params = expr.get_params()
        session = params.get("session", True)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("VARIABLES")

        sql_params = ()
        if like_pattern:
            parts.append("LIKE %s")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_status(self, expr: "ShowStatusExpression") -> Tuple[str, tuple]:
        """Format SHOW STATUS statement."""
        params = expr.get_params()
        session = params.get("session", True)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("STATUS")

        sql_params = ()
        if like_pattern:
            parts.append("LIKE %s")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW PROCESSLIST/WARNINGS/ERRORS ==========

    def format_show_processlist(
        self, expr: "ShowProcessListExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW PROCESSLIST statement."""
        params = expr.get_params()
        full = params.get("full", False)

        if full:
            return "SHOW FULL PROCESSLIST", ()
        return "SHOW PROCESSLIST", ()

    def format_show_warnings(
        self, expr: "ShowWarningsExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW WARNINGS statement."""
        params = expr.get_params()
        limit = params.get("limit")

        if limit is not None:
            return f"SHOW WARNINGS LIMIT {limit}", ()
        return "SHOW WARNINGS", ()

    def format_show_errors(self, expr: "ShowErrorsExpression") -> Tuple[str, tuple]:
        """Format SHOW ERRORS statement."""
        params = expr.get_params()
        limit = params.get("limit")

        if limit is not None:
            return f"SHOW ERRORS LIMIT {limit}", ()
        return "SHOW ERRORS", ()

    # ========== SHOW ENGINES/CHARSET/COLLATION ==========

    def format_show_engines(self, expr: "ShowEnginesExpression") -> Tuple[str, tuple]:
        """Format SHOW ENGINES statement."""
        return "SHOW ENGINES", ()

    def format_show_charset(self, expr: "ShowCharsetExpression") -> Tuple[str, tuple]:
        """Format SHOW CHARACTER SET statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return "SHOW CHARACTER SET LIKE %s", (like_pattern,)
        return "SHOW CHARACTER SET", ()

    def format_show_collation(
        self, expr: "ShowCollationExpression"
    ) -> Tuple[str, tuple]:
        """Format SHOW COLLATION statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return "SHOW COLLATION LIKE %s", (like_pattern,)
        return "SHOW COLLATION", ()

    # ========== SHOW GRANTS/PLUGINS ==========

    def format_show_grants(self, expr: "ShowGrantsExpression") -> Tuple[str, tuple]:
        """Format SHOW GRANTS statement."""
        params = expr.get_params()
        user = params.get("user")
        host = params.get("host")

        if user:
            if host:
                return "SHOW GRANTS FOR %s@%s", (user, host)
            return "SHOW GRANTS FOR %s", (user,)
        return "SHOW GRANTS", ()

    def format_show_plugins(self, expr: "ShowPluginsExpression") -> Tuple[str, tuple]:
        """Format SHOW PLUGINS statement."""
        return "SHOW PLUGINS", ()
