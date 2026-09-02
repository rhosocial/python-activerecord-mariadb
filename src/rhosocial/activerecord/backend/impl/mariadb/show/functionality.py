# src/rhosocial/activerecord/backend/impl/mariadb/show/functionality.py
"""
MariaDB SHOW functionality implementation.

This module provides the MariaDB-specific implementation of ShowFunctionality.
It uses expression-dialect pattern for SQL generation and backend.execute()
for all SQL execution.

The implementation:
- Creates expression objects with the dialect
- Calls expression.to_sql() to get SQL
- Executes SQL via backend.execute()
- Parses results into typed dataclasses
"""

from typing import Optional, Tuple, TYPE_CHECKING

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

if TYPE_CHECKING:
    from ..backend import MariaDBBackend
    from ..async_backend import AsyncMariaDBBackend


class MariaDBShowFunctionality:
    """MariaDB-specific SHOW functionality implementation.

    Provides all MariaDB SHOW commands using expression-dialect pattern.
    Supports version-aware feature detection for MariaDB version differences.
    """

    def __init__(self, backend: "MariaDBBackend", version: Optional[Tuple[int, ...]] = None):
        """Initialize MariaDB SHOW functionality.

        Args:
            backend: MariaDBBackend instance for executing queries.
            version: MariaDB server version tuple, e.g., (10, 5, 0) for MariaDB 10.5.
        """
        self._backend = backend
        self._version = version
        self.dialect = backend.dialect
        # MariaDB 10.3+ supports invisible columns
        self._supports_invisible_columns = version >= (10, 3, 0) if version else True

    # ========== Parsing Helper Methods ==========

    def _parse_create_table_result(self, result, table: str):
        """Parse SHOW CREATE TABLE result."""
        from .types import ShowCreateTableResult

        if not result.data or len(result.data) == 0:
            return None

        row = result.data[0]
        return ShowCreateTableResult(
            table_name=row.get("Table", row.get("TABLE", table)),
            create_statement=row.get("Create Table", row.get("CREATE TABLE", "")),
        )

    def _parse_create_view_result(self, result, view_name: str):
        """Parse SHOW CREATE VIEW result."""
        from .types import ShowCreateViewResult

        if not result.data or len(result.data) == 0:
            return None

        row = result.data[0]
        return ShowCreateViewResult(
            view_name=row.get("View", row.get("VIEW", view_name)),
            create_statement=row.get("Create View", row.get("CREATE VIEW", "")),
            character_set_client=row.get("character_set_client"),
            collation_connection=row.get("collation_connection"),
        )

    def _parse_columns_result(self, result):
        """Parse SHOW COLUMNS result."""
        from .types import ShowColumnResult

        columns = []
        for row in result.data:
            col = ShowColumnResult(
                field=row.get("Field", row.get("COLUMN_NAME")),
                type=row.get("Type", row.get("COLUMN_TYPE")),
                null=row.get("Null", row.get("IS_NULLABLE")),
                key=row.get("Key", row.get("COLUMN_KEY")),
                default=row.get("Default", row.get("COLUMN_DEFAULT")),
                extra=row.get("Extra", row.get("EXTRA")),
            )
            # FULL mode additional fields
            if "Collation" in row or "Privileges" in row:
                col.privileges = row.get("Privileges")
                col.comment = row.get("Comment")
            columns.append(col)
        return columns

    def _parse_indexes_result(self, result):
        """Parse SHOW INDEX result."""
        from .types import ShowIndexResult

        indexes = []
        for row in result.data:
            indexes.append(
                ShowIndexResult(
                    table_name=row.get("Table", row.get("TABLE_NAME")),
                    non_unique=row.get("Non_unique", row.get("NON_UNIQUE")),
                    key_name=row.get("Key_name", row.get("INDEX_NAME")),
                    seq_in_index=row.get("Seq_in_index", row.get("SEQ_IN_INDEX")),
                    column_name=row.get("Column_name", row.get("COLUMN_NAME")),
                    collation=row.get("Collation", row.get("COLLATION")),
                    cardinality=row.get("Cardinality", row.get("CARDINALITY")),
                    sub_part=row.get("Sub_part", row.get("SUB_PART")),
                    packed=row.get("Packed", row.get("PACKED")),
                    null=row.get("Null", row.get("NULLABLE")),
                    index_type=row.get("Index_type") or row.get("INDEX_TYPE") or "BTREE",
                    comment=row.get("Comment", row.get("INDEX_COMMENT")),
                    index_comment=row.get("Index_comment", row.get("INDEX_COMMENT")),
                    visible=row.get("Visible", row.get("IS_VISIBLE")),
                    expression=row.get("Expression", row.get("EXPRESSION")),
                )
            )
        return indexes

    def _parse_tables_result(self, result):
        """Parse SHOW TABLES result."""
        from .types import ShowTableResult

        tables = []
        for row in result.data:
            if len(row) == 1:
                tables.append(ShowTableResult(name=list(row.values())[0], table_type=None))
            else:
                name_key = next((k for k in row.keys() if k.startswith("Tables_in_")), None)
                if name_key:
                    tables.append(ShowTableResult(name=row[name_key], table_type=row.get("Table_type")))
        return tables

    def _parse_databases_result(self, result):
        """Parse SHOW DATABASES result."""
        from .types import ShowDatabaseResult

        return [ShowDatabaseResult(name=row.get("Database")) for row in result.data]

    def _parse_table_status_result(self, result):
        """Parse SHOW TABLE STATUS result."""
        from .types import ShowTableStatusResult

        statuses = []
        for row in result.data:
            statuses.append(
                ShowTableStatusResult(
                    name=row.get("Name"),
                    engine=row.get("Engine"),
                    version=row.get("Version"),
                    row_format=row.get("Row_format"),
                    rows=row.get("Rows"),
                    avg_row_length=row.get("Avg_row_length"),
                    data_length=row.get("Data_length"),
                    max_data_length=row.get("Max_data_length"),
                    index_length=row.get("Index_length"),
                    data_free=row.get("Data_free"),
                    auto_increment=row.get("Auto_increment"),
                    create_time=str(row["Create_time"]) if row.get("Create_time") else None,
                    update_time=str(row["Update_time"]) if row.get("Update_time") else None,
                    check_time=str(row["Check_time"]) if row.get("Check_time") else None,
                    collation=row.get("Collation"),
                    checksum=row.get("Checksum"),
                    create_options=row.get("Create_options"),
                    comment=row.get("Comment"),
                )
            )
        return statuses

    def _parse_triggers_result(self, result):
        """Parse SHOW TRIGGERS result."""
        from .types import ShowTriggerResult

        triggers = []
        for row in result.data:
            triggers.append(
                ShowTriggerResult(
                    trigger_name=row.get("Trigger", row.get("TRIGGER_NAME")),
                    event=row.get("Event", row.get("EVENT_MANIPULATION")),
                    table_name=row.get("Table", row.get("EVENT_OBJECT_TABLE")),
                    statement=row.get("Statement", row.get("ACTION_STATEMENT")),
                    timing=row.get("Timing", row.get("ACTION_TIMING")),
                    created=row.get("Created"),
                    sql_mode=row.get("sql_mode"),
                    definer=row.get("Definer"),
                    character_set_client=row.get("character_set_client"),
                    collation_connection=row.get("collation_connection"),
                    database_collation=row.get("Database Collation"),
                )
            )
        return triggers

    def _parse_create_trigger_result(self, result, trigger: str):
        """Parse SHOW CREATE TRIGGER result."""
        from .types import ShowCreateTriggerResult

        if not result.data or len(result.data) == 0:
            return None

        row = result.data[0]
        return ShowCreateTriggerResult(
            trigger_name=row.get("Trigger", row.get("TRIGGER", trigger)),
            create_statement=row.get("SQL Original Statement", row.get("CREATE TRIGGER", "")),
            character_set_client=row.get("character_set_client"),
            collation_connection=row.get("collation_connection"),
            database_collation=row.get("Database Collation"),
        )

    def _parse_variables_result(self, result):
        """Parse SHOW VARIABLES result."""
        from .types import ShowVariableResult

        return [
            ShowVariableResult(
                variable_name=row.get("Variable_name"),
                value=row.get("Value"),
            )
            for row in result.data
        ]

    def _parse_status_result(self, result):
        """Parse SHOW STATUS result."""
        from .types import ShowStatusResult

        return [
            ShowStatusResult(
                variable_name=row.get("Variable_name"),
                value=row.get("Value"),
            )
            for row in result.data
        ]

    def _parse_processlist_result(self, result):
        """Parse SHOW PROCESSLIST result."""
        from .types import ShowProcessListResult

        processes = []
        for row in result.data:
            processes.append(
                ShowProcessListResult(
                    id=row.get("Id", row.get("ID")),
                    user=row.get("User"),
                    host=row.get("Host"),
                    command=row.get("Command"),
                    time=row.get("Time"),
                    db=row.get("db"),
                    state=row.get("State"),
                    info=row.get("Info"),
                )
            )
        return processes

    def _parse_warnings_result(self, result):
        """Parse SHOW WARNINGS result."""
        from .types import ShowWarningResult

        return [
            ShowWarningResult(
                level=row.get("Level"),
                code=row.get("Code"),
                message=row.get("Message"),
            )
            for row in result.data
        ]

    def _parse_errors_result(self, result):
        """Parse SHOW ERRORS result."""
        from .types import ShowWarningResult

        return [
            ShowWarningResult(
                level=row.get("Level"),
                code=row.get("Code"),
                message=row.get("Message"),
            )
            for row in result.data
        ]

    def _parse_engines_result(self, result):
        """Parse SHOW ENGINES result."""
        from .types import ShowEngineResult

        engines = []
        for row in result.data:
            engines.append(
                ShowEngineResult(
                    engine=row.get("Engine"),
                    support=row.get("Support"),
                    transactions=row.get("Transactions"),
                    xa=row.get("XA"),
                    savepoints=row.get("Savepoints"),
                )
            )
        return engines

    def _parse_charset_result(self, result):
        """Parse SHOW CHARACTER SET result."""
        from .types import ShowCharsetResult

        return [
            ShowCharsetResult(
                charset=row.get("Charset"),
                description=row.get("Description"),
                default_collation=row.get("Default collation"),
                maxlen=row.get("Maxlen"),
            )
            for row in result.data
        ]

    def _parse_collation_result(self, result):
        """Parse SHOW COLLATION result."""
        from .types import ShowCollationResult

        return [
            ShowCollationResult(
                collation=row.get("Collation"),
                charset=row.get("Charset"),
                id=row.get("Id"),
                default=row.get("Default"),
                compiled=row.get("Compiled"),
                sortlen=row.get("Sortlen"),
            )
            for row in result.data
        ]

    def _parse_grants_result(self, result):
        """Parse SHOW GRANTS result."""
        from .types import ShowGrantResult

        return [ShowGrantResult(grants=row.get("Grants for")) for row in result.data]

    def _parse_plugins_result(self, result):
        """Parse SHOW PLUGINS result."""
        from .types import ShowPluginResult

        plugins = []
        for row in result.data:
            plugins.append(
                ShowPluginResult(
                    name=row.get("Name"),
                    status=row.get("Status"),
                    type=row.get("Type"),
                    library=row.get("Library"),
                    license=row.get("License"),
                )
            )
        return plugins

    # ========== SHOW CREATE TABLE ==========

    def create_table(
        self, table: str, schema: Optional[str] = None
    ):
        """Get CREATE TABLE statement for a table.

        Args:
            table: Name of the table.
            schema: Database/schema name (optional).

        Returns:
            ShowCreateTableResult with table name and CREATE statement,
            or None if table doesn't exist.
        """
        expr = ShowCreateTableExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_create_table_result(result, table)

    # ========== SHOW CREATE VIEW ==========

    def create_view(
        self, view_name: str, schema: Optional[str] = None
    ):
        """Get CREATE VIEW statement for a view.

        Args:
            view_name: Name of the view.
            schema: Database/schema name (optional).

        Returns:
            ShowCreateViewResult with view details, or None if view doesn't exist.
        """
        expr = ShowCreateViewExpression(self.dialect, view_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_create_view_result(result, view_name)

    # ========== SHOW COLUMNS ==========

    def columns(
        self,
        table: str,
        schema: Optional[str] = None,
        full: bool = False,
        like: Optional[str] = None,
    ):
        """Get column information for a table.

        Args:
            table: Name of the table.
            schema: Database/schema name (optional).
            full: Include privileges and comments.
            like: Filter columns by name pattern.

        Returns:
            List of ShowColumnResult objects.
        """
        expr = ShowColumnsExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        if full:
            expr.full()
        if like:
            expr.like(like)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_columns_result(result)

    # ========== SHOW INDEX ==========

    def indexes(
        self, table: str, schema: Optional[str] = None
    ):
        """Get index information for a table.

        Args:
            table: Name of the table.
            schema: Database/schema name (optional).

        Returns:
            List of ShowIndexResult objects.
        """
        expr = ShowIndexExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_indexes_result(result)

    # ========== SHOW TABLES ==========

    def tables(
        self,
        schema: Optional[str] = None,
        like: Optional[str] = None,
        full: bool = False,
    ):
        """List tables in the database.

        Args:
            schema: Database/schema name (optional).
            like: Filter tables by name pattern.
            full: Include table type (BASE TABLE or VIEW).

        Returns:
            List of ShowTableResult objects.
        """
        expr = ShowTablesExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        if full:
            expr.full()

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_tables_result(result)

    # ========== SHOW DATABASES ==========

    def databases(self, like: Optional[str] = None):
        """List databases.

        Args:
            like: Filter databases by name pattern.

        Returns:
            List of ShowDatabaseResult objects.
        """
        expr = ShowDatabasesExpression(self.dialect)
        if like:
            expr.like(like)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_databases_result(result)

    # ========== SHOW TABLE STATUS ==========

    def table_status(
        self, schema: Optional[str] = None, like: Optional[str] = None
    ):
        """Get table status information.

        Args:
            schema: Database/schema name (optional).
            like: Filter tables by name pattern.

        Returns:
            List of ShowTableStatusResult objects.
        """
        expr = ShowTableStatusExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_table_status_result(result)

    # ========== SHOW TRIGGERS ==========

    def triggers(
        self, schema: Optional[str] = None, table: Optional[str] = None
    ):
        """List triggers.

        Args:
            schema: Database/schema name (optional).
            table: Filter triggers for a specific table.

        Returns:
            List of ShowTriggerResult objects.
        """
        expr = ShowTriggersExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if table:
            expr.for_table(table)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_triggers_result(result)

    def create_trigger(
        self, trigger: str, schema: Optional[str] = None
    ):
        """Get CREATE TRIGGER statement.

        Args:
            trigger: Name of the trigger.
            schema: Database/schema name (optional).

        Returns:
            ShowCreateTriggerResult or None if not found.
        """
        expr = ShowCreateTriggerExpression(self.dialect, trigger)
        if schema:
            expr.schema(schema)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_create_trigger_result(result, trigger)

    # ========== SHOW VARIABLES ==========

    def variables(
        self, like: Optional[str] = None, session: bool = True
    ):
        """Show server variables.

        Args:
            like: Filter variables by name pattern.
            session: Show session variables (True) or global variables (False).

        Returns:
            List of ShowVariableResult objects.
        """
        expr = ShowVariablesExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_vars()

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_variables_result(result)

    # ========== SHOW STATUS ==========

    def status(
        self, like: Optional[str] = None, session: bool = True
    ):
        """Show server status.

        Args:
            like: Filter status by name pattern.
            session: Show session status (True) or global status (False).

        Returns:
            List of ShowStatusResult objects.
        """
        expr = ShowStatusExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_status()

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_status_result(result)

    # ========== SHOW PROCESSLIST ==========

    def processlist(self, full: bool = False):
        """Show process list.

        Args:
            full: Include full query text.

        Returns:
            List of ShowProcessListResult objects.
        """
        expr = ShowProcessListExpression(self.dialect)
        if full:
            expr.full()

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_processlist_result(result)

    # ========== SHOW WARNINGS/ERRORS ==========

    def warnings(self, limit: Optional[int] = None):
        """Show warnings.

        Args:
            limit: Maximum number of warnings to return.

        Returns:
            List of ShowWarningResult objects.
        """
        expr = ShowWarningsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_warnings_result(result)

    def errors(self, limit: Optional[int] = None):
        """Show errors.

        Args:
            limit: Maximum number of errors to return.

        Returns:
            List of ShowWarningResult objects.
        """
        expr = ShowErrorsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_errors_result(result)

    # ========== SHOW ENGINES ==========

    def engines(self):
        """Show storage engines.

        Returns:
            List of ShowEngineResult objects.
        """
        expr = ShowEnginesExpression(self.dialect)
        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_engines_result(result)

    # ========== SHOW CHARSET ==========

    def charset(self, like: Optional[str] = None):
        """Show character sets.

        Args:
            like: Filter character sets by name pattern.

        Returns:
            List of ShowCharsetResult objects.
        """
        expr = ShowCharsetExpression(self.dialect)
        if like:
            expr.like(like)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_charset_result(result)

    # ========== SHOW COLLATION ==========

    def collation(self, like: Optional[str] = None):
        """Show collations.

        Args:
            like: Filter collations by name pattern.

        Returns:
            List of ShowCollationResult objects.
        """
        expr = ShowCollationExpression(self.dialect)
        if like:
            expr.like(like)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_collation_result(result)

    # ========== SHOW GRANTS ==========

    def grants(
        self, user: Optional[str] = None, host: Optional[str] = None
    ):
        """Show grants.

        Args:
            user: User name (optional, defaults to current user).
            host: Host name (optional).

        Returns:
            List of ShowGrantResult objects.
        """
        expr = ShowGrantsExpression(self.dialect)
        if user:
            expr.for_user(user, host)

        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_grants_result(result)

    # ========== SHOW PLUGINS ==========

    def plugins(self):
        """Show plugins.

        Returns:
            List of ShowPluginResult objects.
        """
        expr = ShowPluginsExpression(self.dialect)
        sql, params = expr.to_sql()
        result = self._backend.execute(sql, params)
        return self._parse_plugins_result(result)


class AsyncMariaDBShowFunctionality:
    """Async MariaDB SHOW functionality implementation.

    Async version of MariaDBShowFunctionality. Mirrors the same interface
    but with async methods.
    """

    def __init__(
        self, backend: "AsyncMariaDBBackend", version: Optional[Tuple[int, ...]] = None
    ):
        """Initialize async MariaDB SHOW functionality.

        Args:
            backend: AsyncMariaDBBackend instance for executing queries.
            version: MariaDB server version tuple.
        """
        self._backend = backend
        self._version = version
        self.dialect = backend.dialect
        # Share parsing methods with sync implementation
        self._sync_impl = MariaDBShowFunctionality(backend, version)

    # ========== SHOW CREATE TABLE ==========

    async def create_table(
        self, table: str, schema: Optional[str] = None
    ):
        """Async version of create_table."""
        expr = ShowCreateTableExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_create_table_result(result, table)

    # ========== SHOW CREATE VIEW ==========

    async def create_view(
        self, view_name: str, schema: Optional[str] = None
    ):
        """Async version of create_view."""
        expr = ShowCreateViewExpression(self.dialect, view_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_create_view_result(result, view_name)

    # ========== SHOW COLUMNS ==========

    async def columns(
        self,
        table: str,
        schema: Optional[str] = None,
        full: bool = False,
        like: Optional[str] = None,
    ):
        """Async version of columns."""
        expr = ShowColumnsExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        if full:
            expr.full()
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_columns_result(result)

    # ========== SHOW INDEX ==========

    async def indexes(
        self, table: str, schema: Optional[str] = None
    ):
        """Async version of indexes."""
        expr = ShowIndexExpression(self.dialect, table)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_indexes_result(result)

    # ========== SHOW TABLES ==========

    async def tables(
        self,
        schema: Optional[str] = None,
        like: Optional[str] = None,
        full: bool = False,
    ):
        """Async version of tables."""
        expr = ShowTablesExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_tables_result(result)

    # ========== SHOW DATABASES ==========

    async def databases(self, like: Optional[str] = None):
        """Async version of databases."""
        expr = ShowDatabasesExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_databases_result(result)

    # ========== SHOW TABLE STATUS ==========

    async def table_status(
        self, schema: Optional[str] = None, like: Optional[str] = None
    ):
        """Async version of table_status."""
        expr = ShowTableStatusExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_table_status_result(result)

    # ========== SHOW TRIGGERS ==========

    async def triggers(
        self, schema: Optional[str] = None, table: Optional[str] = None
    ):
        """Async version of triggers."""
        expr = ShowTriggersExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if table:
            expr.for_table(table)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_triggers_result(result)

    async def create_trigger(
        self, trigger: str, schema: Optional[str] = None
    ):
        """Async version of create_trigger."""
        expr = ShowCreateTriggerExpression(self.dialect, trigger)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_create_trigger_result(result, trigger)

    # ========== SHOW VARIABLES ==========

    async def variables(
        self, like: Optional[str] = None, session: bool = True
    ):
        """Async version of variables."""
        expr = ShowVariablesExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_vars()
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_variables_result(result)

    # ========== SHOW STATUS ==========

    async def status(
        self, like: Optional[str] = None, session: bool = True
    ):
        """Async version of status."""
        expr = ShowStatusExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_status()
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_status_result(result)

    # ========== SHOW PROCESSLIST ==========

    async def processlist(self, full: bool = False):
        """Async version of processlist."""
        expr = ShowProcessListExpression(self.dialect)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_processlist_result(result)

    # ========== SHOW WARNINGS/ERRORS ==========

    async def warnings(self, limit: Optional[int] = None):
        """Async version of warnings."""
        expr = ShowWarningsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_warnings_result(result)

    async def errors(self, limit: Optional[int] = None):
        """Async version of errors."""
        expr = ShowErrorsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_errors_result(result)

    # ========== SHOW ENGINES ==========

    async def engines(self):
        """Async version of engines."""
        expr = ShowEnginesExpression(self.dialect)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_engines_result(result)

    # ========== SHOW CHARSET ==========

    async def charset(self, like: Optional[str] = None):
        """Async version of charset."""
        expr = ShowCharsetExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_charset_result(result)

    # ========== SHOW COLLATION ==========

    async def collation(self, like: Optional[str] = None):
        """Async version of collation."""
        expr = ShowCollationExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_collation_result(result)

    # ========== SHOW GRANTS ==========

    async def grants(
        self, user: Optional[str] = None, host: Optional[str] = None
    ):
        """Async version of grants."""
        expr = ShowGrantsExpression(self.dialect)
        if user:
            expr.for_user(user, host)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_grants_result(result)

    # ========== SHOW PLUGINS ==========

    async def plugins(self):
        """Async version of plugins."""
        expr = ShowPluginsExpression(self.dialect)
        sql, params = expr.to_sql()
        result = await self._backend.execute(sql, params)
        return self._sync_impl._parse_plugins_result(result)