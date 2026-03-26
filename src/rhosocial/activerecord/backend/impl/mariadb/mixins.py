# src/rhosocial/activerecord/backend/impl/mariadb/mixins.py
"""MariaDB dialect-specific Mixin implementations.

This module provides mixin classes that implement MariaDB-specific
functionality shared between sync and async backends.
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.transaction import IsolationLevel


MARIADB_VERSION_BOUNDARIES = {
    'WINDOW_FUNCTIONS': (10, 2, 0),
    'JSON_FUNCTIONS': (10, 2, 3),
    'JSON_ARROWS': (10, 2, 7),
    'CTE': (10, 2, 0),
    'INTERSECT_EXCEPT': (10, 3, 0),
    'SEQUENCE': (10, 3, 0),
    'SYSTEM_VERSIONING': (10, 3, 0),
    'RETURNING': (10, 5, 0),
    'EXPLAIN_FORMAT': (10, 6, 0),
}


class MariaDBTransactionMixin:
    """MariaDB transaction common functionality.

    Provides shared isolation level management for both sync and async
    MariaDB transaction managers.
    """

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level."""
        from rhosocial.activerecord.backend.transaction import IsolationLevelError
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level


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
    - self._logger: Logger instance
    """

    def _register_mariadb_adapters(self):
        """Register MariaDB-specific type adapters."""
        from .adapters import (
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
    def dialect(self):
        """Get the MariaDB dialect instance (lazy loads with configured version)."""
        from .dialect import MariaDBDialect
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


class MariaDBSequenceMixin:
    """MariaDB SEQUENCE support mixin.

    MariaDB 10.3+ supports SEQUENCE storage engine for generating
    sequential numbers.
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        MariaDB 10.3+ supports SEQUENCE storage engine.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def format_nextval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format NEXTVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"NEXT VALUE FOR {self.format_identifier(sequence_name)}", ()

    def format_currval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format CURRVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"CURRENT VALUE FOR {self.format_identifier(sequence_name)}", ()

    def format_setval(
        self,
        sequence_name: str,
        value: int,
        is_called: bool = True
    ) -> Tuple[str, tuple]:
        """Format SETVAL expression.

        Args:
            sequence_name: Name of the sequence
            value: Value to set
            is_called: If True, next NEXTVAL returns value + increment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f"SET {self.format_identifier(sequence_name)} = {value}"
        if not is_called:
            sql += ", 0"
        return sql, ()


class MariaDBReturningMixin:
    """MariaDB RETURNING clause support mixin.

    MariaDB 10.5+ supports RETURNING clause for INSERT, DELETE,
    and REPLACE statements.
    """

    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported.

        MariaDB 10.5+ supports RETURNING.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_expression(self) -> bool:
        """Whether expressions are supported in RETURNING.

        MariaDB 10.5+ supports expressions and aliases in RETURNING.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def format_returning_clause(
        self,
        columns: Optional[List[str]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None,
        aliases: Optional[Dict[str, str]] = None
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause for MariaDB.

        Args:
            columns: Column names to return
            expressions: Expressions with optional aliases
            aliases: Column/expression to alias mappings

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if not self.supports_returning():
            return "", ()

        items = []

        if columns:
            for col in columns:
                alias = aliases.get(col) if aliases else None
                if alias:
                    items.append(f"{self.format_identifier(col)} AS {self.format_identifier(alias)}")
                else:
                    items.append(self.format_identifier(col))

        if expressions:
            for expr in expressions:
                expr_text = expr.get("expression", "")
                expr_alias = expr.get("alias")
                if expr_alias:
                    items.append(f"{expr_text} AS {self.format_identifier(expr_alias)}")
                else:
                    items.append(expr_text)

        if not items:
            return "RETURNING *", ()

        return f"RETURNING {', '.join(items)}", ()


class MariaDBIntersectExceptMixin:
    """MariaDB INTERSECT/EXCEPT support mixin.

    MariaDB 10.3+ supports INTERSECT and EXCEPT set operations.
    """

    def supports_intersect(self) -> bool:
        """Whether INTERSECT is supported.

        MariaDB 10.3+ supports INTERSECT.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_except(self) -> bool:
        """Whether EXCEPT is supported.

        MariaDB 10.3+ supports EXCEPT.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_intersect_all(self) -> bool:
        """Whether INTERSECT ALL is supported.

        MariaDB 10.3+ supports INTERSECT ALL.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_except_all(self) -> bool:
        """Whether EXCEPT ALL is supported.

        MariaDB 10.3+ supports EXCEPT ALL.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']


class MariaDBCTEMixin:
    """MariaDB CTE (Common Table Expression) support mixin.

    MariaDB 10.2+ supports CTEs with the WITH clause.
    """

    def supports_cte(self) -> bool:
        """Whether CTEs (WITH clause) are supported.

        MariaDB 10.2+ supports CTEs.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported.

        MariaDB 10.2+ supports recursive CTEs.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']


class MariaDBWindowFunctionMixin:
    """MariaDB Window Function support mixin.

    MariaDB 10.2+ supports window functions.
    """

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported.

        MariaDB 10.2+ supports window functions.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']

    def supports_named_windows(self) -> bool:
        """Whether named window definitions are supported.

        MariaDB 10.2+ supports named windows.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']


class MariaDBJSONMixin:
    """MariaDB JSON function support mixin.

    MariaDB 10.2.3+ supports JSON functions, and 10.2.7+ supports
    JSON arrow operators (-> and ->>).
    """

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported.

        Args:
            function_name: Name of JSON function

        Returns:
            True if function is supported in current MariaDB version
        """
        if self.version < MARIADB_VERSION_BOUNDARIES['JSON_FUNCTIONS']:
            return False

        json_functions = {
            'json_extract', 'json_unquote', 'json_object', 'json_array',
            'json_contains', 'json_set', 'json_insert', 'json_replace',
            'json_remove', 'json_type', 'json_valid', 'json_keys',
            'json_length', 'json_depth', 'json_merge', 'json_merge_patch',
            'json_search', 'json_array_append', 'json_quote',
        }
        return function_name.lower() in json_functions

    def supports_json_arrows(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        MariaDB 10.2.7+ supports JSON arrow operators.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_ARROWS']


__all__ = [
    'MARIADB_VERSION_BOUNDARIES',
    'MariaDBTransactionMixin',
    'MariaDBBackendMixin',
    'MariaDBSequenceMixin',
    'MariaDBReturningMixin',
    'MariaDBIntersectExceptMixin',
    'MariaDBCTEMixin',
    'MariaDBWindowFunctionMixin',
    'MariaDBJSONMixin',
]
