# src/rhosocial/activerecord/backend/impl/mariadb/__init__.py
"""
MariaDB backend implementation for ActiveRecord.

This module provides a MariaDB-specific implementation including:
- MariaDB backend with connection management and query execution
- Async MariaDB backend with full async support
- MariaDB dialect and expression handling
- MariaDB-specific type definitions
- Support for RETURNING clause (available since MariaDB 10.5)
- Support for SEQUENCE (available since MariaDB 10.3)
- Support for INTERSECT/EXCEPT (available since MariaDB 10.3)
- MariaDB-specific SQL function factories (JSON, spatial, full-text, etc.)
"""

__version__ = "1.0.0.dev1"

from .backend import MariaDBBackend
from .backend.async_backend import AsyncMariaDBBackend
from .dialect import MariaDBDialect, MARIADB_VERSION_BOUNDARIES
from .transaction import MariaDBTransactionManager, MariaDBTransactionMixin
from .async_transaction import AsyncMariaDBTransactionManager
from .config import MariaDBConnectionConfig
from .types import MariaDBEnumType, MariaDBSetType
from .explain import MariaDBExplainResult, MariaDBExplainRow, MariaDBExplainJsonResult, MariaDBExplainAnalyzeResult

# Import MariaDB-specific functions directly for convenience
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

# Import MariaDB SHOW command expressions
from .show.expressions import (
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

# Import MariaDB SHOW command result types
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
    # Synchronous Backend
    'MariaDBBackend',

    # Asynchronous Backend
    'AsyncMariaDBBackend',

    # Configuration
    'MariaDBConnectionConfig',

    # Dialect related
    'MariaDBDialect',
    'MARIADB_VERSION_BOUNDARIES',

    # Transaction - Sync and Async
    'MariaDBTransactionManager',
    'AsyncMariaDBTransactionManager',
    'MariaDBTransactionMixin',

    # MariaDB-specific Type Helpers
    'MariaDBEnumType',
    'MariaDBSetType',

    # MariaDB EXPLAIN Result Types
    'MariaDBExplainResult',
    'MariaDBExplainRow',
    'MariaDBExplainJsonResult',
    'MariaDBExplainAnalyzeResult',

    # MariaDB-specific Functions - JSON
    'json_extract',
    'json_unquote',
    'json_object',
    'json_array',
    'json_contains',
    'json_set',
    'json_remove',
    'json_type',
    'json_valid',
    'json_search',

    # MariaDB-specific Functions - Spatial
    'st_geom_from_text',
    'st_geom_from_wkb',
    'st_as_text',
    'st_as_geojson',
    'st_distance',
    'st_within',
    'st_contains',
    'st_intersects',

    # MariaDB-specific Functions - Full-text Search
    'match_against',

    # MariaDB-specific Functions - SET/Enum
    'find_in_set',
    'elt',
    'field',

    # MariaDB SHOW Command Expressions
    'ShowExpression',
    'ShowCreateTableExpression',
    'ShowColumnsExpression',
    'ShowTableStatusExpression',
    'ShowIndexExpression',
    'ShowTablesExpression',
    'ShowDatabasesExpression',
    'ShowTriggersExpression',
    'ShowCreateViewExpression',
    'ShowVariablesExpression',
    'ShowStatusExpression',
    'ShowWarningsExpression',
    'ShowErrorsExpression',
    'ShowCreateTriggerExpression',
    'ShowGrantsExpression',
    'ShowProcessListExpression',
    'ShowEnginesExpression',
    'ShowCharsetExpression',
    'ShowCollationExpression',
    'ShowPluginsExpression',

    # MariaDB SHOW Command Result Types
    'ShowCreateTableResult',
    'ShowCreateViewResult',
    'ShowCreateTriggerResult',
    'ShowColumnResult',
    'ShowTableStatusResult',
    'ShowIndexResult',
    'ShowTableResult',
    'ShowDatabaseResult',
    'ShowTriggerResult',
    'ShowVariableResult',
    'ShowStatusResult',
    'ShowWarningResult',
    'ShowGrantResult',
    'ShowProcessListResult',
    'ShowEngineResult',
    'ShowCharsetResult',
    'ShowCollationResult',
    'ShowPluginResult',
]