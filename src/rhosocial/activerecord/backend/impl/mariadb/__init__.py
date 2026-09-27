# src/rhosocial/activerecord/backend/impl/mariadb/__init__.py
"""MariaDB backend implementation for ActiveRecord.

This module provides a MariaDB-specific implementation including:
- MariaDB backend with connection management and query execution
- Async MariaDB backend with full async support
- MariaDB dialect and expression handling
- MariaDB-specific type definitions
- Support for RETURNING clause (available since MariaDB 10.5)
- Support for SEQUENCE (available since MariaDB 10.3)
- Support for INTERSECT/EXCEPT (available since MariaDB 10.3)
- MariaDB-specific SQL function factories (JSON, spatial, full-text, etc.)"""

# Public names are resolved on first access rather than at package-execution
# time. Importing this package used to import every submodule eagerly, which
# pulled in the DB driver through ``.backend`` and made the expression classes
# unreachable without it: Python executes a parent package's ``__init__`` before
# any submodule, so ``impl.<name>.expression`` could not be imported on its own.
# The exports themselves are unchanged -- attribute access, ``__all__``, ``dir()``
# and ``from ... import *`` all behave as before.
from typing import TYPE_CHECKING

__version__ = "1.0.0.dev1"

#: Public name -> (submodule that defines it, attribute name within it).
#: The two differ when the original import was aliased.
_EXPORTS = {
    "AsyncMariaDBBackend": (".backend.async_backend", "AsyncMariaDBBackend"),
    "AsyncMariaDBTransactionManager": (".async_transaction", "AsyncMariaDBTransactionManager"),
    "MARIADB_VERSION_BOUNDARIES": (".dialect", "MARIADB_VERSION_BOUNDARIES"),
    "MariaDBBackend": (".backend", "MariaDBBackend"),
    "MariaDBCharset": (".mixins.charset_collation", "MariaDBCharset"),
    "MariaDBCollation": (".mixins.charset_collation", "MariaDBCollation"),
    "MariaDBConnectionConfig": (".config", "MariaDBConnectionConfig"),
    "MariaDBDialect": (".dialect", "MariaDBDialect"),
    "MariaDBEnumType": (".types", "MariaDBEnumType"),
    "MariaDBExplainAnalyzeResult": (".explain", "MariaDBExplainAnalyzeResult"),
    "MariaDBExplainJsonResult": (".explain", "MariaDBExplainJsonResult"),
    "MariaDBExplainResult": (".explain", "MariaDBExplainResult"),
    "MariaDBExplainRow": (".explain", "MariaDBExplainRow"),
    "MariaDBSetType": (".types", "MariaDBSetType"),
    "MariaDBStorageEngine": (".mixins.charset_collation", "MariaDBStorageEngine"),
    "MariaDBTransactionManager": (".transaction", "MariaDBTransactionManager"),
    "MariaDBTransactionMixin": (".transaction", "MariaDBTransactionMixin"),
    "ShowCharsetExpression": (".expression.show", "ShowCharsetExpression"),
    "ShowCharsetResult": (".show.types", "ShowCharsetResult"),
    "ShowCollationExpression": (".expression.show", "ShowCollationExpression"),
    "ShowCollationResult": (".show.types", "ShowCollationResult"),
    "ShowColumnResult": (".show.types", "ShowColumnResult"),
    "ShowColumnsExpression": (".expression.show", "ShowColumnsExpression"),
    "ShowCreateTableExpression": (".expression.show", "ShowCreateTableExpression"),
    "ShowCreateTableResult": (".show.types", "ShowCreateTableResult"),
    "ShowCreateTriggerExpression": (".expression.show", "ShowCreateTriggerExpression"),
    "ShowCreateTriggerResult": (".show.types", "ShowCreateTriggerResult"),
    "ShowCreateViewExpression": (".expression.show", "ShowCreateViewExpression"),
    "ShowCreateViewResult": (".show.types", "ShowCreateViewResult"),
    "ShowDatabaseResult": (".show.types", "ShowDatabaseResult"),
    "ShowDatabasesExpression": (".expression.show", "ShowDatabasesExpression"),
    "ShowEngineResult": (".show.types", "ShowEngineResult"),
    "ShowEnginesExpression": (".expression.show", "ShowEnginesExpression"),
    "ShowErrorsExpression": (".expression.show", "ShowErrorsExpression"),
    "ShowExpression": (".expression.show", "ShowExpression"),
    "ShowGrantResult": (".show.types", "ShowGrantResult"),
    "ShowGrantsExpression": (".expression.show", "ShowGrantsExpression"),
    "ShowIndexExpression": (".expression.show", "ShowIndexExpression"),
    "ShowIndexResult": (".show.types", "ShowIndexResult"),
    "ShowPluginResult": (".show.types", "ShowPluginResult"),
    "ShowPluginsExpression": (".expression.show", "ShowPluginsExpression"),
    "ShowProcessListExpression": (".expression.show", "ShowProcessListExpression"),
    "ShowProcessListResult": (".show.types", "ShowProcessListResult"),
    "ShowStatusExpression": (".expression.show", "ShowStatusExpression"),
    "ShowStatusResult": (".show.types", "ShowStatusResult"),
    "ShowTableResult": (".show.types", "ShowTableResult"),
    "ShowTableStatusExpression": (".expression.show", "ShowTableStatusExpression"),
    "ShowTableStatusResult": (".show.types", "ShowTableStatusResult"),
    "ShowTablesExpression": (".expression.show", "ShowTablesExpression"),
    "ShowTriggerResult": (".show.types", "ShowTriggerResult"),
    "ShowTriggersExpression": (".expression.show", "ShowTriggersExpression"),
    "ShowVariableResult": (".show.types", "ShowVariableResult"),
    "ShowVariablesExpression": (".expression.show", "ShowVariablesExpression"),
    "ShowWarningResult": (".show.types", "ShowWarningResult"),
    "ShowWarningsExpression": (".expression.show", "ShowWarningsExpression"),
    "elt": (".functions", "elt"),
    "field": (".functions", "field"),
    "find_in_set": (".functions", "find_in_set"),
    "json_array": (".functions", "json_array"),
    "json_contains": (".functions", "json_contains"),
    "json_extract": (".functions", "json_extract"),
    "json_object": (".functions", "json_object"),
    "json_remove": (".functions", "json_remove"),
    "json_search": (".functions", "json_search"),
    "json_set": (".functions", "json_set"),
    "json_type": (".functions", "json_type"),
    "json_unquote": (".functions", "json_unquote"),
    "json_valid": (".functions", "json_valid"),
    "match_against": (".functions", "match_against"),
    "st_as_geojson": (".functions", "st_as_geojson"),
    "st_as_text": (".functions", "st_as_text"),
    "st_contains": (".functions", "st_contains"),
    "st_distance": (".functions", "st_distance"),
    "st_geom_from_text": (".functions", "st_geom_from_text"),
    "st_geom_from_wkb": (".functions", "st_geom_from_wkb"),
    "st_intersects": (".functions", "st_intersects"),
    "st_within": (".functions", "st_within"),
}

if TYPE_CHECKING:  # pragma: no cover - re-exports for type checkers
    from .backend import MariaDBBackend
    from .backend.async_backend import AsyncMariaDBBackend
    from .dialect import MariaDBDialect, MARIADB_VERSION_BOUNDARIES
    from .transaction import MariaDBTransactionManager, MariaDBTransactionMixin
    from .async_transaction import AsyncMariaDBTransactionManager
    from .config import MariaDBConnectionConfig
    from .mixins.charset_collation import (
        MariaDBCharset,
        MariaDBCollation,
        MariaDBStorageEngine,
    )
    from .types import MariaDBEnumType, MariaDBSetType
    from .explain import MariaDBExplainResult, MariaDBExplainRow, MariaDBExplainJsonResult, MariaDBExplainAnalyzeResult
    from .functions import (
        # JSON functions
        json_extract,
        json_unquote,
        json_object,
        json_array,
        json_contains,
        json_set,
        json_remove,
        json_type,
        json_valid,
        json_search,
        # Spatial functions
        st_geom_from_text,
        st_geom_from_wkb,
        st_as_text,
        st_as_geojson,
        st_distance,
        st_within,
        st_contains,
        st_intersects,
        # Full-text search
        match_against,
        # SET type functions
        find_in_set,
        # Enum type functions
        elt,
        field,
    )
    from .expression.show import (
        ShowExpression,
        ShowCreateTableExpression,
        ShowColumnsExpression,
        ShowTableStatusExpression,
        ShowIndexExpression,
        ShowTablesExpression,
        ShowDatabasesExpression,
        ShowTriggersExpression,
        ShowCreateViewExpression,
        ShowVariablesExpression,
        ShowStatusExpression,
        ShowWarningsExpression,
        ShowErrorsExpression,
        ShowCreateTriggerExpression,
        ShowGrantsExpression,
        ShowProcessListExpression,
        ShowEnginesExpression,
        ShowCharsetExpression,
        ShowCollationExpression,
        ShowPluginsExpression,
    )
    from .show.types import (
        # CREATE statement results
        ShowCreateTableResult,
        ShowCreateViewResult,
        ShowCreateTriggerResult,
        # Column information results
        ShowColumnResult,
        # Table status results
        ShowTableStatusResult,
        # Index information results
        ShowIndexResult,
        # Database and table list results
        ShowTableResult,
        ShowDatabaseResult,
        # Trigger results
        ShowTriggerResult,
        # Variables and status results
        ShowVariableResult,
        ShowStatusResult,
        # Warning and error results
        ShowWarningResult,
        # Grants results
        ShowGrantResult,
        # Process list results
        ShowProcessListResult,
        # Engine results
        ShowEngineResult,
        # Charset and collation results
        ShowCharsetResult,
        ShowCollationResult,
        # Plugin results
        ShowPluginResult,
    )

__all__ = [
    "MariaDBBackend",
    "AsyncMariaDBBackend",
    "MariaDBConnectionConfig",
    "MariaDBDialect",
    "MARIADB_VERSION_BOUNDARIES",
    "MariaDBCollation",
    "MariaDBCharset",
    "MariaDBStorageEngine",
    "MariaDBTransactionManager",
    "AsyncMariaDBTransactionManager",
    "MariaDBTransactionMixin",
    "MariaDBEnumType",
    "MariaDBSetType",
    "MariaDBExplainResult",
    "MariaDBExplainRow",
    "MariaDBExplainJsonResult",
    "MariaDBExplainAnalyzeResult",
    "json_extract",
    "json_unquote",
    "json_object",
    "json_array",
    "json_contains",
    "json_set",
    "json_remove",
    "json_type",
    "json_valid",
    "json_search",
    "st_geom_from_text",
    "st_geom_from_wkb",
    "st_as_text",
    "st_as_geojson",
    "st_distance",
    "st_within",
    "st_contains",
    "st_intersects",
    "match_against",
    "find_in_set",
    "elt",
    "field",
    "ShowExpression",
    "ShowCreateTableExpression",
    "ShowColumnsExpression",
    "ShowTableStatusExpression",
    "ShowIndexExpression",
    "ShowTablesExpression",
    "ShowDatabasesExpression",
    "ShowTriggersExpression",
    "ShowCreateViewExpression",
    "ShowVariablesExpression",
    "ShowStatusExpression",
    "ShowWarningsExpression",
    "ShowErrorsExpression",
    "ShowCreateTriggerExpression",
    "ShowGrantsExpression",
    "ShowProcessListExpression",
    "ShowEnginesExpression",
    "ShowCharsetExpression",
    "ShowCollationExpression",
    "ShowPluginsExpression",
    "ShowCreateTableResult",
    "ShowCreateViewResult",
    "ShowCreateTriggerResult",
    "ShowColumnResult",
    "ShowTableStatusResult",
    "ShowIndexResult",
    "ShowTableResult",
    "ShowDatabaseResult",
    "ShowTriggerResult",
    "ShowVariableResult",
    "ShowStatusResult",
    "ShowWarningResult",
    "ShowGrantResult",
    "ShowProcessListResult",
    "ShowEngineResult",
    "ShowCharsetResult",
    "ShowCollationResult",
    "ShowPluginResult",
]


def __getattr__(name: str):
    """Resolve a public name by importing its defining submodule once."""
    target = _EXPORTS.get(name)
    if target is not None:
        import importlib

        module_name, attr = target
        value = getattr(importlib.import_module(module_name, __name__), attr)
        globals()[name] = value  # cache, so __getattr__ runs at most once per name
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_EXPORTS))
