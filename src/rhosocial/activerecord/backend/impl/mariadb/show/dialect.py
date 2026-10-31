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
    from ..expression.show import (
        ShowCreateTableStatement,
        ShowCreateViewStatement,
        ShowColumnsStatement,
        ShowIndexStatement,
        ShowTablesStatement,
        ShowDatabasesStatement,
        ShowTableStatusStatement,
        ShowTriggersStatement,
        ShowCreateTriggerStatement,
        ShowVariablesStatement,
        ShowStatusStatement,
        ShowProcessListStatement,
        ShowWarningsStatement,
        ShowErrorsStatement,
        ShowEnginesStatement,
        ShowCharsetStatement,
        ShowCollationStatement,
        ShowGrantsStatement,
        ShowPluginsStatement,
    )


class MariaDBShowDialectMixin:
    """MariaDB SHOW command SQL generation mixin.

    Provides format_show_* methods for generating MariaDB SHOW command SQL.
    All methods take an expression parameter and return (sql, params) tuple.

    This mixin is added to MariaDBDialect to provide SHOW functionality.
    """

    # ========== SHOW CREATE Statements ==========

    def _show_relation_target(self, expr) -> str:
        """Render the relation a SHOW statement names.

        A table and a view are one concept for this purpose: both are
        relations in a namespace, and MariaDB's qualified name is
        ``database`.`name``. The database is a named slot on the object,
        which is why ``SHOW COLUMNS FROM app`.`users`` is expressible
        here at all -- a bare identifier plus a hand-written ``schema.``
        prefix could not carry it.

        The statement keeps its own formatter: only the *name* is shared,
        because only the name is one thing.
        """
        relation_sql, _ = expr.relation.to_sql()
        return relation_sql

    def format_show_create_table_statement(
        self, expr: "ShowCreateTableStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE TABLE statement."""
        return f"SHOW CREATE TABLE {self._show_relation_target(expr)}", ()

    def format_show_create_view_statement(
        self, expr: "ShowCreateViewStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE VIEW statement."""
        return f"SHOW CREATE VIEW {self._show_relation_target(expr)}", ()

    def format_show_create_trigger_statement(
        self, expr: "ShowCreateTriggerStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW CREATE TRIGGER statement.

        A trigger is not a relation, but its *name* is qualified the same
        way -- the database is part of it -- so it goes through the same
        renderer with the object kind that says so.
        """
        trigger_sql, _ = expr.trigger.to_sql()
        return f"SHOW CREATE TRIGGER {trigger_sql}", ()

    # ========== SHOW COLUMNS/INDEX ==========

    def format_show_columns_statement(self, expr: "ShowColumnsStatement") -> Tuple[str, tuple]:
        """Format SHOW [FULL] COLUMNS statement.

        The parameters are read off the node's declared fields: ``full`` and
        ``like_pattern`` are construction parameters, so they are always there
        and ``get_params()`` is not a second way to reach them.
        """
        full = expr.full
        like_pattern = expr.like_pattern

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("COLUMNS FROM")
        parts.append(self._show_relation_target(expr))

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_index_statement(self, expr: "ShowIndexStatement") -> Tuple[str, tuple]:
        """Format SHOW INDEX statement."""
        return f"SHOW INDEX FROM {self._show_relation_target(expr)}", ()

    # ========== SHOW TABLES/DATABASES ==========

    def format_show_tables_statement(self, expr: "ShowTablesStatement") -> Tuple[str, tuple]:
        """Format SHOW [FULL] TABLES statement."""
        schema = expr.schema
        full = expr.full
        like_pattern = expr.like_pattern

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("TABLES")
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_databases_statement(
        self, expr: "ShowDatabasesStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW DATABASES statement."""
        like_pattern = expr.like_pattern

        if like_pattern:
            return f"SHOW DATABASES LIKE {self.p()}", (like_pattern,)
        return "SHOW DATABASES", ()

    def format_show_table_status_statement(
        self, expr: "ShowTableStatusStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW TABLE STATUS statement."""
        schema = expr.schema
        like_pattern = expr.like_pattern

        parts = ["SHOW TABLE STATUS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW TRIGGERS ==========

    def format_show_triggers_statement(
        self, expr: "ShowTriggersStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW TRIGGERS statement."""
        schema = expr.schema
        table_name = expr.table_name

        parts = ["SHOW TRIGGERS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if table_name:
            parts.append(f"LIKE {self.p()}")
            sql_params = (table_name,)

        return " ".join(parts), sql_params

    # ========== SHOW VARIABLES/STATUS ==========

    def format_show_variables_statement(
        self, expr: "ShowVariablesStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW VARIABLES statement."""
        session = expr.session
        like_pattern = expr.like_pattern

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("VARIABLES")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_status_statement(self, expr: "ShowStatusStatement") -> Tuple[str, tuple]:
        """Format SHOW STATUS statement."""
        session = expr.session
        like_pattern = expr.like_pattern

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("STATUS")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW PROCESSLIST/WARNINGS/ERRORS ==========

    def format_show_process_list_statement(
        self, expr: "ShowProcessListStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW PROCESSLIST statement."""
        full = expr.full

        if full:
            return "SHOW FULL PROCESSLIST", ()
        return "SHOW PROCESSLIST", ()

    def format_show_warnings_statement(
        self, expr: "ShowWarningsStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW WARNINGS statement."""
        limit = expr.limit

        if limit is not None:
            return f"SHOW WARNINGS LIMIT {limit}", ()
        return "SHOW WARNINGS", ()

    def format_show_errors_statement(self, expr: "ShowErrorsStatement") -> Tuple[str, tuple]:
        """Format SHOW ERRORS statement."""
        limit = expr.limit

        if limit is not None:
            return f"SHOW ERRORS LIMIT {limit}", ()
        return "SHOW ERRORS", ()

    # ========== SHOW ENGINES/CHARSET/COLLATION ==========

    def format_show_engines_statement(self, expr: "ShowEnginesStatement") -> Tuple[str, tuple]:
        """Format SHOW ENGINES statement."""
        return "SHOW ENGINES", ()

    def format_show_charset_statement(self, expr: "ShowCharsetStatement") -> Tuple[str, tuple]:
        """Format SHOW CHARACTER SET statement."""
        like_pattern = expr.like_pattern

        if like_pattern:
            return f"SHOW CHARACTER SET LIKE {self.p()}", (like_pattern,)
        return "SHOW CHARACTER SET", ()

    def format_show_collation_statement(
        self, expr: "ShowCollationStatement"
    ) -> Tuple[str, tuple]:
        """Format SHOW COLLATION statement."""
        like_pattern = expr.like_pattern

        if like_pattern:
            return f"SHOW COLLATION LIKE {self.p()}", (like_pattern,)
        return "SHOW COLLATION", ()

    # ========== SHOW GRANTS/PLUGINS ==========

    def format_show_grants_statement(self, expr: "ShowGrantsStatement") -> Tuple[str, tuple]:
        """Format SHOW GRANTS statement."""
        user = expr.user
        host = expr.host

        if user:
            if host:
                return f"SHOW GRANTS FOR {self.p()}@{self.p()}", (user, host)
            return f"SHOW GRANTS FOR {self.p()}", (user,)
        return "SHOW GRANTS", ()

    def format_show_plugins_statement(self, expr: "ShowPluginsStatement") -> Tuple[str, tuple]:
        """Format SHOW PLUGINS statement."""
        return "SHOW PLUGINS", ()
