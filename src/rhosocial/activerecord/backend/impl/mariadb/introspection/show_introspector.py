# src/rhosocial/activerecord/backend/impl/mariadb/introspection/show_introspector.py
"""
MariaDB SHOW command sub-introspectors.

Provides MariaDB-specific SHOW commands as sub-introspectors accessible via
``backend.introspector.show``. Execution is delegated to the executor,
keeping the class I/O-free except for the executor calls.

MariaDB SHOW commands are fully compatible with MySQL SHOW commands.

Design principle: Sync and Async are separate and cannot coexist.
- SyncShowIntrospector: for synchronous backends (method names without _async suffix)
- AsyncShowIntrospector: for asynchronous backends (method names without _async suffix)
"""

from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from ..show.expressions import (
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


class ShowMixin:
    """Mixin providing shared SHOW command logic.

    Both SyncShowIntrospector and AsyncShowIntrospector inherit
    from this mixin to share:
    - Dialect access
    - SQL generation helpers
    - _parse_* static methods
    """

    @property
    def dialect(self):
        """Get the SQL dialect from the backend."""
        return self._backend.dialect

    # ------------------------------------------------------------------ #
    # Pure parse helpers (shared by sync and async, no I/O)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_create_table(rows: List[Dict], table_name: str):
        from ..show.types import ShowCreateTableResult
        if not rows:
            return None
        row = rows[0]
        return ShowCreateTableResult(
            table_name=row.get("Table", row.get("TABLE", table_name)),
            create_statement=row.get("Create Table", row.get("CREATE TABLE", "")),
        )

    @staticmethod
    def _parse_create_view(rows: List[Dict], view_name: str):
        from ..show.types import ShowCreateViewResult
        if not rows:
            return None
        row = rows[0]
        return ShowCreateViewResult(
            view_name=row.get("View", row.get("VIEW", view_name)),
            create_statement=row.get("Create View", row.get("CREATE VIEW", "")),
            character_set_client=row.get("character_set_client"),
            collation_connection=row.get("collation_connection"),
        )

    @staticmethod
    def _parse_columns(rows: List[Dict]):
        from ..show.types import ShowColumnResult
        columns = []
        for row in rows:
            col = ShowColumnResult(
                field=row.get("Field", row.get("COLUMN_NAME")),
                type=row.get("Type", row.get("COLUMN_TYPE")),
                null=row.get("Null", row.get("IS_NULLABLE")),
                key=row.get("Key", row.get("COLUMN_KEY")),
                default=row.get("Default", row.get("COLUMN_DEFAULT")),
                extra=row.get("Extra", row.get("EXTRA")),
            )
            if "Collation" in row or "Privileges" in row:
                col.privileges = row.get("Privileges")
                col.comment = row.get("Comment")
            columns.append(col)
        return columns

    @staticmethod
    def _parse_indexes(rows: List[Dict]):
        from ..show.types import ShowIndexResult
        return [
            ShowIndexResult(
                table=row.get("Table", row.get("TABLE_NAME")),
                non_unique=row.get("Non_unique", row.get("NON_UNIQUE")),
                key_name=row.get("Key_name", row.get("INDEX_NAME")),
                seq_in_index=row.get("Seq_in_index", row.get("SEQ_IN_INDEX")),
                column_name=row.get("Column_name", row.get("COLUMN_NAME")),
                collation=row.get("Collation", row.get("COLLATION")),
                cardinality=row.get("Cardinality", row.get("CARDINALITY")),
                sub_part=row.get("Sub_part", row.get("SUB_PART")),
                packed=row.get("Packed", row.get("PACKED")),
                null=row.get("Null", row.get("NULLABLE")),
                index_type=row.get("Index_type", row.get("INDEX_TYPE"), "BTREE"),
                comment=row.get("Comment", row.get("INDEX_COMMENT")),
                index_comment=row.get("Index_comment", row.get("INDEX_COMMENT")),
                visible=row.get("Visible", row.get("IS_VISIBLE")),
                expression=row.get("Expression", row.get("EXPRESSION")),
            )
            for row in rows
        ]

    @staticmethod
    def _parse_tables(rows: List[Dict]):
        from ..show.types import ShowTableResult
        result = []
        for row in rows:
            if len(row) == 1:
                result.append(ShowTableResult(name=list(row.values())[0], table_type=None))
            else:
                name_key = next((k for k in row.keys() if k.startswith("Tables_in_")), None)
                if name_key:
                    result.append(ShowTableResult(name=row[name_key], table_type=row.get("Table_type")))
        return result

    @staticmethod
    def _parse_databases(rows: List[Dict]):
        from ..show.types import ShowDatabaseResult
        return [ShowDatabaseResult(name=row.get("Database")) for row in rows]

    @staticmethod
    def _parse_table_status(rows: List[Dict]):
        from ..show.types import ShowTableStatusResult
        return [
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
            for row in rows
        ]

    @staticmethod
    def _parse_triggers(rows: List[Dict]):
        from ..show.types import ShowTriggerResult
        return [
            ShowTriggerResult(
                trigger=row.get("Trigger", row.get("TRIGGER_NAME")),
                event=row.get("Event", row.get("EVENT_MANIPULATION")),
                table=row.get("Table", row.get("EVENT_OBJECT_TABLE")),
                statement=row.get("Statement", row.get("ACTION_STATEMENT")),
                timing=row.get("Timing", row.get("ACTION_TIMING")),
                created=row.get("Created"),
                sql_mode=row.get("sql_mode"),
                definer=row.get("Definer"),
                character_set_client=row.get("character_set_client"),
                collation_connection=row.get("collation_connection"),
                database_collation=row.get("Database Collation"),
            )
            for row in rows
        ]

    @staticmethod
    def _parse_create_trigger(rows: List[Dict], trigger_name: str):
        from ..show.types import ShowCreateTriggerResult
        if not rows:
            return None
        row = rows[0]
        return ShowCreateTriggerResult(
            trigger_name=row.get("Trigger", row.get("TRIGGER", trigger_name)),
            create_statement=row.get("SQL Original Statement", row.get("CREATE TRIGGER", "")),
            character_set_client=row.get("character_set_client"),
            collation_connection=row.get("collation_connection"),
            database_collation=row.get("Database Collation"),
        )

    @staticmethod
    def _parse_variables(rows: List[Dict]):
        from ..show.types import ShowVariableResult
        return [
            ShowVariableResult(variable_name=row.get("Variable_name"), value=row.get("Value"))
            for row in rows
        ]

    @staticmethod
    def _parse_status(rows: List[Dict]):
        from ..show.types import ShowStatusResult
        return [
            ShowStatusResult(variable_name=row.get("Variable_name"), value=row.get("Value"))
            for row in rows
        ]

    @staticmethod
    def _parse_processlist(rows: List[Dict]):
        from ..show.types import ShowProcessListResult
        return [
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
            for row in rows
        ]

    @staticmethod
    def _parse_warnings(rows: List[Dict]):
        from ..show.types import ShowWarningResult
        return [
            ShowWarningResult(level=row.get("Level"), code=row.get("Code"), message=row.get("Message"))
            for row in rows
        ]

    @staticmethod
    def _parse_engines(rows: List[Dict]):
        from ..show.types import ShowEngineResult
        return [
            ShowEngineResult(
                engine=row.get("Engine"),
                support=row.get("Support"),
                transactions=row.get("Transactions"),
                xa=row.get("XA"),
                savepoints=row.get("Savepoints"),
            )
            for row in rows
        ]

    @staticmethod
    def _parse_charset(rows: List[Dict]):
        from ..show.types import ShowCharsetResult
        return [
            ShowCharsetResult(
                charset=row.get("Charset"),
                description=row.get("Description"),
                default_collation=row.get("Default collation"),
                maxlen=row.get("Maxlen"),
            )
            for row in rows
        ]

    @staticmethod
    def _parse_collation(rows: List[Dict]):
        from ..show.types import ShowCollationResult
        return [
            ShowCollationResult(
                collation=row.get("Collation"),
                charset=row.get("Charset"),
                id=row.get("Id"),
                default=row.get("Default"),
                compiled=row.get("Compiled"),
                sortlen=row.get("Sortlen"),
            )
            for row in rows
        ]

    @staticmethod
    def _parse_grants(rows: List[Dict]):
        from ..show.types import ShowGrantResult
        return [ShowGrantResult(grants=row.get("Grants for")) for row in rows]

    @staticmethod
    def _parse_plugins(rows: List[Dict]):
        from ..show.types import ShowPluginResult
        return [
            ShowPluginResult(
                name=row.get("Name"),
                status=row.get("Status"),
                type=row.get("Type"),
                library=row.get("Library"),
                license=row.get("License"),
            )
            for row in rows
        ]


class SyncShowIntrospector(ShowMixin):
    """Synchronous SHOW command sub-introspector for MariaDB backends.

    All methods are synchronous. Method names do NOT have an _async suffix.

    Access via ``backend.introspector.show``::

        tables    = backend.introspector.show.tables()
        create    = backend.introspector.show.create_table("users")
        variables = backend.introspector.show.variables(like="max_%")
    """

    def __init__(self, backend: Any, executor: SyncIntrospectorExecutor) -> None:
        self._backend = backend
        self._executor = executor

    def _exec(self, sql: str, params: tuple) -> List[Dict[str, Any]]:
        """Execute SQL synchronously."""
        return self._executor.execute(sql, params)

    # ------------------------------------------------------------------ #
    # Public synchronous API
    # ------------------------------------------------------------------ #

    def create_table(self, table_name: str, schema: Optional[str] = None):
        """Get CREATE TABLE statement for a table."""
        expr = ShowCreateTableExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_table(self._exec(sql, params), table_name)

    def create_view(self, view_name: str, schema: Optional[str] = None):
        """Get CREATE VIEW statement for a view."""
        expr = ShowCreateViewExpression(self.dialect, view_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_view(self._exec(sql, params), view_name)

    def columns(
        self,
        table_name: str,
        schema: Optional[str] = None,
        full: bool = False,
        like: Optional[str] = None,
    ):
        """Get column information for a table."""
        expr = ShowColumnsExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        if full:
            expr.full()
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_columns(self._exec(sql, params))

    def indexes(self, table_name: str, schema: Optional[str] = None):
        """Get index information for a table."""
        expr = ShowIndexExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_indexes(self._exec(sql, params))

    def tables(
        self,
        schema: Optional[str] = None,
        like: Optional[str] = None,
        full: bool = False,
    ):
        """List tables in the database."""
        expr = ShowTablesExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        return self._parse_tables(self._exec(sql, params))

    def databases(self, like: Optional[str] = None):
        """List databases."""
        expr = ShowDatabasesExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_databases(self._exec(sql, params))

    def table_status(self, schema: Optional[str] = None, like: Optional[str] = None):
        """Get table status information."""
        expr = ShowTableStatusExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_table_status(self._exec(sql, params))

    def triggers(self, schema: Optional[str] = None, table_name: Optional[str] = None):
        """List triggers."""
        expr = ShowTriggersExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if table_name:
            expr.for_table(table_name)
        sql, params = expr.to_sql()
        return self._parse_triggers(self._exec(sql, params))

    def create_trigger(self, trigger_name: str, schema: Optional[str] = None):
        """Get CREATE TRIGGER statement."""
        expr = ShowCreateTriggerExpression(self.dialect, trigger_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_trigger(self._exec(sql, params), trigger_name)

    def variables(self, like: Optional[str] = None, session: bool = True):
        """Show server variables."""
        expr = ShowVariablesExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_vars()
        sql, params = expr.to_sql()
        return self._parse_variables(self._exec(sql, params))

    def status(self, like: Optional[str] = None, session: bool = True):
        """Show server status."""
        expr = ShowStatusExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_status()
        sql, params = expr.to_sql()
        return self._parse_status(self._exec(sql, params))

    def processlist(self, full: bool = False):
        """Show process list."""
        expr = ShowProcessListExpression(self.dialect)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        return self._parse_processlist(self._exec(sql, params))

    def warnings(self, limit: Optional[int] = None):
        """Show warnings."""
        expr = ShowWarningsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        return self._parse_warnings(self._exec(sql, params))

    def errors(self, limit: Optional[int] = None):
        """Show errors."""
        expr = ShowErrorsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        return self._parse_warnings(self._exec(sql, params))

    def engines(self):
        """Show storage engines."""
        expr = ShowEnginesExpression(self.dialect)
        sql, params = expr.to_sql()
        return self._parse_engines(self._exec(sql, params))

    def charset(self, like: Optional[str] = None):
        """Show character sets."""
        expr = ShowCharsetExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_charset(self._exec(sql, params))

    def collation(self, like: Optional[str] = None):
        """Show collations."""
        expr = ShowCollationExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_collation(self._exec(sql, params))

    def grants(self, user: Optional[str] = None, host: Optional[str] = None):
        """Show grants."""
        expr = ShowGrantsExpression(self.dialect)
        if user:
            expr.for_user(user, host)
        sql, params = expr.to_sql()
        return self._parse_grants(self._exec(sql, params))

    def plugins(self):
        """Show plugins."""
        expr = ShowPluginsExpression(self.dialect)
        sql, params = expr.to_sql()
        return self._parse_plugins(self._exec(sql, params))


class AsyncShowIntrospector(ShowMixin):
    """Asynchronous SHOW command sub-introspector for MariaDB backends.

    All methods are async. Method names match the sync version (no _async suffix).

    Access via ``backend.introspector.show``::

        tables    = await backend.introspector.show.tables()
        create    = await backend.introspector.show.create_table("users")
        variables = await backend.introspector.show.variables(like="max_%")
    """

    def __init__(self, backend: Any, executor: AsyncIntrospectorExecutor) -> None:
        self._backend = backend
        self._executor = executor

    async def _exec(self, sql: str, params: tuple) -> List[Dict[str, Any]]:
        """Execute SQL asynchronously."""
        return await self._executor.execute(sql, params)

    # ------------------------------------------------------------------ #
    # Public asynchronous API
    # Method names match the sync version (no _async suffix).
    # ------------------------------------------------------------------ #

    async def create_table(self, table_name: str, schema: Optional[str] = None):
        """Get CREATE TABLE statement for a table."""
        expr = ShowCreateTableExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_table(await self._exec(sql, params), table_name)

    async def create_view(self, view_name: str, schema: Optional[str] = None):
        """Get CREATE VIEW statement for a view."""
        expr = ShowCreateViewExpression(self.dialect, view_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_view(await self._exec(sql, params), view_name)

    async def columns(
        self,
        table_name: str,
        schema: Optional[str] = None,
        full: bool = False,
        like: Optional[str] = None,
    ):
        """Get column information for a table."""
        expr = ShowColumnsExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        if full:
            expr.full()
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_columns(await self._exec(sql, params))

    async def indexes(self, table_name: str, schema: Optional[str] = None):
        """Get index information for a table."""
        expr = ShowIndexExpression(self.dialect, table_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_indexes(await self._exec(sql, params))

    async def tables(
        self,
        schema: Optional[str] = None,
        like: Optional[str] = None,
        full: bool = False,
    ):
        """List tables in the database."""
        expr = ShowTablesExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        return self._parse_tables(await self._exec(sql, params))

    async def databases(self, like: Optional[str] = None):
        """List databases."""
        expr = ShowDatabasesExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_databases(await self._exec(sql, params))

    async def table_status(self, schema: Optional[str] = None, like: Optional[str] = None):
        """Get table status information."""
        expr = ShowTableStatusExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_table_status(await self._exec(sql, params))

    async def triggers(self, schema: Optional[str] = None, table_name: Optional[str] = None):
        """List triggers."""
        expr = ShowTriggersExpression(self.dialect)
        if schema:
            expr.schema(schema)
        if table_name:
            expr.for_table(table_name)
        sql, params = expr.to_sql()
        return self._parse_triggers(await self._exec(sql, params))

    async def create_trigger(self, trigger_name: str, schema: Optional[str] = None):
        """Get CREATE TRIGGER statement."""
        expr = ShowCreateTriggerExpression(self.dialect, trigger_name)
        if schema:
            expr.schema(schema)
        sql, params = expr.to_sql()
        return self._parse_create_trigger(await self._exec(sql, params), trigger_name)

    async def variables(self, like: Optional[str] = None, session: bool = True):
        """Show server variables."""
        expr = ShowVariablesExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_vars()
        sql, params = expr.to_sql()
        return self._parse_variables(await self._exec(sql, params))

    async def status(self, like: Optional[str] = None, session: bool = True):
        """Show server status."""
        expr = ShowStatusExpression(self.dialect)
        if like:
            expr.like(like)
        if not session:
            expr.global_status()
        sql, params = expr.to_sql()
        return self._parse_status(await self._exec(sql, params))

    async def processlist(self, full: bool = False):
        """Show process list."""
        expr = ShowProcessListExpression(self.dialect)
        if full:
            expr.full()
        sql, params = expr.to_sql()
        return self._parse_processlist(await self._exec(sql, params))

    async def warnings(self, limit: Optional[int] = None):
        """Show warnings."""
        expr = ShowWarningsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        return self._parse_warnings(await self._exec(sql, params))

    async def errors(self, limit: Optional[int] = None):
        """Show errors."""
        expr = ShowErrorsExpression(self.dialect)
        if limit is not None:
            expr.limit(limit)
        sql, params = expr.to_sql()
        return self._parse_warnings(await self._exec(sql, params))

    async def engines(self):
        """Show storage engines."""
        expr = ShowEnginesExpression(self.dialect)
        sql, params = expr.to_sql()
        return self._parse_engines(await self._exec(sql, params))

    async def charset(self, like: Optional[str] = None):
        """Show character sets."""
        expr = ShowCharsetExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_charset(await self._exec(sql, params))

    async def collation(self, like: Optional[str] = None):
        """Show collations."""
        expr = ShowCollationExpression(self.dialect)
        if like:
            expr.like(like)
        sql, params = expr.to_sql()
        return self._parse_collation(await self._exec(sql, params))

    async def grants(self, user: Optional[str] = None, host: Optional[str] = None):
        """Show grants."""
        expr = ShowGrantsExpression(self.dialect)
        if user:
            expr.for_user(user, host)
        sql, params = expr.to_sql()
        return self._parse_grants(await self._exec(sql, params))

    async def plugins(self):
        """Show plugins."""
        expr = ShowPluginsExpression(self.dialect)
        sql, params = expr.to_sql()
        return self._parse_plugins(await self._exec(sql, params))
