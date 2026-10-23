# src/rhosocial/activerecord/backend/impl/mariadb/show/__init__.py
"""MariaDB SHOW command support module.

MariaDB SHOW commands are fully compatible with MySQL SHOW commands.
This module provides expression classes, result types, and dialect support
for executing SHOW commands on MariaDB databases.

Design principle: Sync and Async are separate and cannot coexist.
"""

from ..expression.show import (
    ShowExpression,
    ShowRelationExpression,
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
from .types import (
    ShowCreateRelationResult,
    ShowCreateTableResult,
    ShowCreateViewResult,
    ShowCreateTriggerResult,
    ShowColumnResult,
    ShowTableStatusResult,
    ShowIndexResult,
    ShowTableResult,
    ShowDatabaseResult,
    ShowTriggerResult,
    ShowVariableResult,
    ShowStatusResult,
    ShowWarningResult,
    ShowEngineResult,
    ShowCharsetResult,
    ShowCollationResult,
    ShowGrantResult,
    ShowPluginResult,
    ShowProcessListResult,
)
from .dialect import MariaDBShowDialectMixin
from .functionality import MariaDBShowFunctionality, AsyncMariaDBShowFunctionality
from .backend_mixin import MariaDBShowMixin, AsyncMariaDBShowMixin

__all__ = [
    # Base expressions
    "ShowExpression",
    # Base for the SHOW commands that name one relation (table or view)
    "ShowRelationExpression",
    # Expressions
    "ShowCreateTableStatement",
    "ShowCreateViewStatement",
    "ShowColumnsStatement",
    "ShowIndexStatement",
    "ShowTablesStatement",
    "ShowDatabasesStatement",
    "ShowTableStatusStatement",
    "ShowTriggersStatement",
    "ShowCreateTriggerStatement",
    "ShowVariablesStatement",
    "ShowStatusStatement",
    "ShowProcessListStatement",
    "ShowWarningsStatement",
    "ShowErrorsStatement",
    "ShowEnginesStatement",
    "ShowCharsetStatement",
    "ShowCollationStatement",
    "ShowGrantsStatement",
    "ShowPluginsStatement",
    # Types
    # Shared base of the two SHOW CREATE results; a table and a view
    # report the same two facts about the one relation they name.
    "ShowCreateRelationResult",
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
    "ShowEngineResult",
    "ShowCharsetResult",
    "ShowCollationResult",
    "ShowGrantResult",
    "ShowPluginResult",
    "ShowProcessListResult",
    # Dialect
    "MariaDBShowDialectMixin",
    # Functionality classes
    "MariaDBShowFunctionality",
    "AsyncMariaDBShowFunctionality",
    # Backend mixins
    "MariaDBShowMixin",
    "AsyncMariaDBShowMixin",
]
