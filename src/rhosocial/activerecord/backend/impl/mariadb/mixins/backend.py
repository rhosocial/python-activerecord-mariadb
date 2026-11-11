# src/rhosocial/activerecord/backend/impl/mariadb/mixins/backend.py
"""MariaDB backend mixin.

Provides shared non-I/O methods for both sync and async MariaDB backends.
"""
import logging
from datetime import date, datetime, time
import mariadb
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    LockError,
    OperationalError,
    QueryError,
    attach_diagnostics,
)
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple, Type, TYPE_CHECKING
from uuid import UUID

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.result import QueryResult

if TYPE_CHECKING:
    from ..dialect import MariaDBDialect
    from rhosocial.activerecord.backend.options import ExecutionOptions

#: Single source of truth for "feature X first appeared in MariaDB <version>".
#:
#: Every version gate in this backend must read a key from here. Do NOT
#: rebind this name in another module: a shadowing local copy silently
#: diverges from this table and turns gates into ``KeyError`` at runtime.
MARIADB_VERSION_BOUNDARIES = {
    'WINDOW_FUNCTIONS': (10, 2, 0),
    'JSON_FUNCTIONS': (10, 2, 3),
    'JSON_ARROWS': (10, 2, 7),
    'JSON_TABLE': (10, 6, 0),
    'CTE': (10, 2, 0),
    'INTERSECT_EXCEPT': (10, 3, 0),
    'SEQUENCE': (10, 3, 0),
    'SYSTEM_VERSIONING': (10, 3, 0),
    'RETURNING': (10, 5, 0),
    'EXPLAIN_FORMAT': (10, 6, 0),
    'INSTEAD_OF_TRIGGER': (10, 4, 0),
    # The two FOR UPDATE wait modifiers do not travel together on MariaDB,
    # so they get separate keys -- core's own ``supports_for_update_nowait``
    # docstring spells out why a shared probe would have to be answered
    # True for a dialect that rejects half the requests it admits.
    # Measured live on the 15-server grid (each statement is a
    # parse-or-reject probe):
    #   FOR UPDATE NOWAIT     errno 1064 on 10.2.44, accepted from 10.3.39.
    #   FOR UPDATE SKIP LOCKED errno 1064 on 10.3.39, 10.4.34, 10.5.29,
    #                       accepted from 10.6.28.
    # The pair previously shared one 10.3.0 key, which answered NOWAIT for
    # the whole 10.3-10.5 range the server rejects SKIP LOCKED on.
    'FOR_UPDATE_NOWAIT': (10, 3, 0),
    'SKIP_LOCKED': (10, 6, 0),
    'RENAME_TABLE_IF_EXISTS': (10, 5, 0),
    'RENAME_TABLE_WAIT': (10, 3, 0),
    'TRUNCATE_WAIT': (10, 3, 0),
    # EXCHANGE PARTITION itself is accepted from 10.2 (the oldest measured
    # version; it predates the 10.2 floor). The two validation options are a
    # later addition: 10.2.44 through 11.3.2 reject both spellings with errno
    # 1064, and 11.4.13 is the first measured version that parses them.
    'EXCHANGE_PARTITION_VALIDATION': (11, 4, 0),
    'ROUTINE_OR_REPLACE': (10, 1, 3),
    'ROUTINE_IF_NOT_EXISTS': (10, 1, 3),
    'GRANT_OR_REPLACE': (10, 1, 4),
    'GRANT_IF_EXISTS': (10, 1, 4),
    'CHECK_CONSTRAINT': (10, 2, 1),
    # --- 10.7 (UUID data type) ---
    # https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type
    'UUID': (10, 7, 0),
    # --- 12.3 (LTS) ---
    'IS_JSON_PREDICATE': (12, 3, 0),
    'TO_DATE_FUNCTION': (12, 3, 0),
    # --- 12.3 (LTS) — data types ---
    # Native XMLTYPE column type. Documented as "available from MariaDB 12.3";
    # 12.3 is itself GA (first GA of the series is 12.3.2) and an LTS line
    # maintained to June 2029, so the boundary names a real release rather than
    # a preview. Verified against live servers: `CREATE TABLE t (c XMLTYPE)`
    # succeeds on 12.3.3 / 13.0.2 / 13.1.1 and fails with errno 4161
    # ("Unknown data type: 'XMLTYPE'") on 11.8.9 and 12.2.2.
    # https://mariadb.com/docs/server/reference/data-types/string-data-types/xmltype
    'XMLTYPE': (12, 3, 0),
    # --- 13.0 (GA) ---
    'RETURNING_UPDATE': (13, 0, 0),
    # --- 13.1 (RC) ---
    'DENY': (13, 1, 0),
    'JSON_ARROW_NATIVE': (13, 1, 0),
}


#: MariaDB server error codes -> the label used for an integrity violation.
#: Reference: https://mariadb.com/kb/en/mariadb-error-codes/
INTEGRITY_ERROR_REASONS: Dict[int, str] = {
    1022: "Duplicate key error",
    1048: "Null constraint violation",
    1062: "Duplicate key error",
    1169: "Duplicate key error",
    1364: "Null constraint violation",
    1451: "Foreign key constraint violation",
    1452: "Foreign key constraint violation",
    3819: "Check constraint violation",
    4025: "Check constraint violation",
}

#: Server codes that carry a taxonomy of their own.
DEADLOCK_ERROR_CODE = 1213
LOCK_WAIT_TIMEOUT_ERROR_CODE = 1205
READ_ONLY_ERROR_CODE = 1290

#: Client codes. A lost connection is transient (a retry can succeed), while a
#: refused connection or an unknown protocol is not.
LOST_CONNECTION_ERROR_CODES = frozenset({2006, 2013, 2055, 2502})
CONNECT_FAILURE_ERROR_CODES = frozenset({2002, 2003, 2048})

#: Message fallbacks, only consulted when neither the class nor the code has
#: settled the category. Kept together so a wording change is one edit.
LOST_CONNECTION_MESSAGE_PATTERNS = (
    "lost connection",
    "server has gone away",
    "gone away",
    "broken pipe",
    "connection reset",
)
CONNECT_FAILURE_MESSAGE_PATTERNS = (
    "can't connect",
    "cannot connect",
    "connection refused",
    "connection timed out",
    "unknown server host",
    "is not allowed to connect",
)


def _integrity_reason(error_code, error_msg: str) -> Optional[str]:
    """Label an integrity violation by code first, then by message text."""
    if error_code in INTEGRITY_ERROR_REASONS:
        return INTEGRITY_ERROR_REASONS[error_code]
    lowered = error_msg.lower()
    if "duplicate entry" in lowered:
        return "Duplicate key error"
    if "cannot delete or update" in lowered or "foreign key constraint" in lowered:
        return "Foreign key constraint violation"
    if "cannot be null" in lowered:
        return "Null constraint violation"
    if "check constraint" in lowered:
        return "Check constraint violation"
    return None


def _outcome_from_code(error_code):
    """Return (error_class, message_prefix, transient, sqlstate) for a code."""
    if error_code is None:
        return None
    if error_code in INTEGRITY_ERROR_REASONS:
        return IntegrityError, INTEGRITY_ERROR_REASONS[error_code], None, None
    if error_code == DEADLOCK_ERROR_CODE:
        return DeadlockError, None, True, None
    if error_code == LOCK_WAIT_TIMEOUT_ERROR_CODE:
        return LockError, None, True, None
    if error_code == READ_ONLY_ERROR_CODE:
        return OperationalError, None, False, "HY000"
    if error_code in LOST_CONNECTION_ERROR_CODES:
        return OperationalError, None, True, None
    if error_code in CONNECT_FAILURE_ERROR_CODES:
        return ConnectionError, None, False, None
    return None


def _outcome_from_message(error_msg: str):
    """Return (error_class, message_prefix, transient, sqlstate) from text."""
    if "Deadlock found" in error_msg:
        return DeadlockError, None, True, None
    if "Lock wait timeout exceeded" in error_msg:
        return LockError, None, True, None
    lowered = error_msg.lower()
    if "read-only" in lowered or "read only" in lowered:
        return OperationalError, None, False, "HY000"
    if any(pattern in lowered for pattern in LOST_CONNECTION_MESSAGE_PATTERNS):
        return OperationalError, None, True, None
    if any(pattern in lowered for pattern in CONNECT_FAILURE_MESSAGE_PATTERNS):
        return ConnectionError, None, False, None
    return None


class MariaDBBackendMixin:
    """MariaDB backend common functionality.

    Provides shared non-I/O methods for both sync and async MariaDB backends.
    This mixin assumes the following attributes exist in the class:
    - self._version: MariaDB server version tuple
    - self._dialect: MariaDBDialect instance (lazy loaded)
    - self._transaction_manager: Transaction manager instance
    - self._connection: Database connection
    - self.adapter_registry: Type adapter registry
    - self.config: Connection configuration
    - self.logger: Logger instance (from ``BackendLoggingMixin``)
    """

    def _register_mariadb_adapters(self):
        """Register MariaDB-specific type adapters."""
        from ..adapters import (
            MariaDBBlobAdapter,
            MariaDBBooleanAdapter,
            MariaDBDateAdapter,
            MariaDBDatetimeAdapter,
            MariaDBDecimalAdapter,
            MariaDBEnumAdapter,
            MariaDBJSONAdapter,
            MariaDBSetAdapter,
            MariaDBTimeAdapter,
            MariaDBUUIDAdapter,
        )

        mariadb_adapters = [
            MariaDBBlobAdapter(),
            MariaDBBooleanAdapter(),
            MariaDBDateAdapter(),
            MariaDBDatetimeAdapter(self._version if hasattr(self, '_version') else None),
            MariaDBDecimalAdapter(),
            MariaDBEnumAdapter(use_int_storage=False),
            MariaDBJSONAdapter(),
            MariaDBSetAdapter(),
            MariaDBTimeAdapter(),
            MariaDBUUIDAdapter(),
        ]

        for adapter in mariadb_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)

        self.log(logging.DEBUG, "Registered MariaDB-specific type adapters")

    @property
    def dialect(self) -> "MariaDBDialect":
        """Get the MariaDB dialect instance (lazy loads with configured version)."""
        from ..dialect import MariaDBDialect
        if self._dialect is None:
            self._dialect = MariaDBDialect(self._version)
        return self._dialect

    @property
    def transaction_manager(self):
        """Get the MariaDB transaction manager."""
        if self._transaction_manager:
            self._transaction_manager._connection = self._connection
        return self._transaction_manager

    def requires_manual_commit(self) -> bool:
        """Check if manual commit is required for this database."""
        return not getattr(self.config, 'autocommit', False)

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """Provide default type adapter suggestions for MariaDB.

        Returns:
            Dict[Type, Tuple[SQLTypeAdapter, Type]]: A dictionary where keys are
            original Python types, and values are tuples containing a
            SQLTypeAdapter instance and the target Python type.
        """
        suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]] = {}

        type_mappings = [
            (bool, int),
            (datetime, str),
            (date, str),
            (time, str),
            (Decimal, float),
            (UUID, str),
            (dict, str),
            (list, str),
            (Enum, str),
            (set, str),
            (frozenset, str),
        ]

        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                self.log(
                    logging.DEBUG,
                    f"No adapter found for ({py_type.__name__}, {db_type.__name__}). "
                    "Suggestion will not be provided for this type."
                )

        return suggestions

    def _liveness_probe(self) -> Tuple[str, tuple]:
        """The statement that answers "is this connection still usable?".

        Rendered once per backend and kept, because this runs before *every*
        query and a probe is the one statement whose text never varies. It is a
        node like any other: the engine is asked for a constant, no relation is
        read.
        """
        cached = getattr(self, "_liveness_probe_sql", None)
        if cached is None:
            from rhosocial.activerecord.backend.expression import (
                Literal,
                QueryStatement,
            )

            cached = QueryStatement(
                self.dialect, select=[Literal(self.dialect, 1, inline=True)]
            ).to_sql()
            self._liveness_probe_sql = cached
        return cached

    def _apply_result_mapping(
        self,
        result: QueryResult,
        options: "ExecutionOptions"
    ) -> QueryResult:
        """Apply column mapping and adapters to a query result."""
        column_mapping = options.column_mapping or {}
        column_adapters = options.column_adapters or {}

        if not result.data:
            return result

        data = result.data
        if isinstance(data, list) and len(data) > 0:
            first_row = data[0]
            if isinstance(first_row, dict):
                if column_adapters:
                    adapted_data = []
                    for row in data:
                        adapted_row = dict(row)
                        for col_name, (adapter, target_type) in column_adapters.items():
                            if col_name in adapted_row:
                                adapted_row[col_name] = adapter.from_database(
                                    row[col_name], target_type
                                )
                        adapted_data.append(adapted_row)
                    data = adapted_data

                if column_mapping:
                    mapped_data = []
                    for row in data:
                        mapped_row = {column_mapping.get(k, k): v for k, v in row.items()}
                        mapped_data.append(mapped_row)
                    data = mapped_data

                result.data = data

        return result

    def _handle_mariadb_error(self, error: Exception) -> None:
        """Map a driver error onto the framework's error taxonomy.

        Recognition order: driver exception class, then MariaDB error code, then
        message text. Codes are stable across driver versions, so they win over
        the message text, which is a last-resort fallback.

        Detection is by isinstance and message, never by class name: callers
        raise subclasses of the mariadb errors, so a name-based check silently
        misses them and lets the driver's own exception escape to the caller.

        Args:
            error: The error raised by the driver.

        Raises:
            The matching rhosocial.activerecord.backend.errors type, or the
            original error when it is not a driver error at all.
        """
        error_msg = str(error)
        # The connector reports errno 0 for failures that carry no server code.
        error_code = getattr(error, "errno", None) or None

        # 1. Driver exception class.
        if isinstance(error, mariadb.ProgrammingError):
            self.log(logging.DEBUG, f"Programming error ({error_code}): {error_msg}")
            raise attach_diagnostics(
                QueryError(error_msg),
                operation="execute",
                driver_code=error_code,
                backend="mariadb",
            ) from error

        if isinstance(error, mariadb.IntegrityError):
            reason = _integrity_reason(error_code, error_msg)
            message = f"{reason}: {error_msg}" if reason else error_msg
            self.log(logging.DEBUG, f"Integrity error ({error_code}): {error_msg}")
            raise attach_diagnostics(
                IntegrityError(message),
                operation="execute",
                driver_code=error_code,
                backend="mariadb",
            ) from error

        if not isinstance(error, mariadb.Error):
            self.log(logging.DEBUG, f"Unhandled error: {error_msg}")
            raise error

        # 2. Error code, then 3. message text, for the remaining driver classes.
        outcome = _outcome_from_code(error_code) or _outcome_from_message(error_msg)
        if outcome is None:
            if isinstance(error, mariadb.OperationalError):
                outcome = (OperationalError, None, None, None)
            else:
                outcome = (DatabaseError, None, None, None)

        error_class, message_prefix, transient, sqlstate = outcome
        message = f"{message_prefix}: {error_msg}" if message_prefix else error_msg
        self.log(logging.DEBUG, f"{error_class.__name__} ({error_code}): {error_msg}")
        raise attach_diagnostics(
            error_class(message),
            operation="execute",
            sqlstate=sqlstate,
            driver_code=error_code,
            backend="mariadb",
            transient=transient,
        ) from error


# MariaDB connection error codes that indicate connection loss
# Reference: https://mariadb.com/kb/en/mariadb-error-codes/
CONNECTION_ERROR_CODES = {
    2003,  # CR_CONN_HOST_ERROR - Can't connect to MariaDB server
    2006,  # CR_SERVER_GONE_ERROR - MariaDB server has gone away
    2013,  # CR_SERVER_LOST - Lost connection to MariaDB server during query
    2048,  # CR_CONN_UNKNOW_PROTOCOL - Invalid connection protocol
    2055,  # CR_SERVER_LOST_EXTENDED - Lost connection to MariaDB server
    2502,  # CR_SERVER_GONE - The server has gone away
}

__all__ = ['MariaDBBackendMixin', 'MARIADB_VERSION_BOUNDARIES', 'CONNECTION_ERROR_CODES']
