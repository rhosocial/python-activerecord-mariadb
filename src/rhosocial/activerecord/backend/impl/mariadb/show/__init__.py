# src/rhosocial/activerecord/backend/impl/mariadb/show/__init__.py
"""MariaDB SHOW command support module.

MariaDB SHOW commands are fully compatible with MySQL SHOW commands.
This module provides expression classes, result types, and dialect support
for executing SHOW commands on MariaDB databases.

Design principle: Sync and Async are separate and cannot coexist.
"""

from .expressions import (
    ShowExpression,
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
from .types import (
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

__all__ = [
    # Base expression
    "ShowExpression",
    # Expressions
    "ShowCreateTableExpression",
    "ShowCreateViewExpression",
    "ShowColumnsExpression",
    "ShowIndexExpression",
    "ShowTablesExpression",
    "ShowDatabasesExpression",
    "ShowTableStatusExpression",
    "ShowTriggersExpression",
    "ShowCreateTriggerExpression",
    "ShowVariablesExpression",
    "ShowStatusExpression",
    "ShowProcessListExpression",
    "ShowWarningsExpression",
    "ShowErrorsExpression",
    "ShowEnginesExpression",
    "ShowCharsetExpression",
    "ShowCollationExpression",
    "ShowGrantsExpression",
    "ShowPluginsExpression",
    # Types
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
]
