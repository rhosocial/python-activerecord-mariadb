# src/rhosocial/activerecord/backend/impl/mariadb/mixins/backend.py
"""MariaDB backend mixin.

Provides shared non-I/O methods for both sync and async MariaDB backends.
"""
import logging
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING
from uuid import UUID

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.result import QueryResult

if TYPE_CHECKING:
    from ..dialect import MariaDBDialect
    from rhosocial.activerecord.backend.options import ExecutionOptions

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
    'INSTEAD_OF_TRIGGER': (10, 4, 0),
    'SKIP_LOCKED': (10, 3, 0),
}


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

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            print(f"[{logging.getLevelName(level)}] {message}")

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


__all__ = ['MariaDBBackendMixin', 'MARIADB_VERSION_BOUNDARIES']
