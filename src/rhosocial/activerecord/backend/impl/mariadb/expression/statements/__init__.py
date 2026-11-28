# src/rhosocial/activerecord/backend/impl/mariadb/expression/statements/__init__.py
"""MariaDB statement expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``.
"""

from importlib import import_module as _import_module

__all__ = [
    "AccountSpec",
    "FlushOption",
    "GrantPrivilege",
    "KillTarget",
    "LoadDataOptions",
    "MariaDBAlterTableExpression",
    "MariaDBAlterTableOptionsStatement",
    "MariaDBAlterUserStatement",
    "MariaDBCallStatement",
    "MariaDBCreateFunctionStatement",
    "MariaDBCreateProcedureStatement",
    "MariaDBCreateRoleStatement",
    "MariaDBCreateTableOptions",
    "MariaDBCreateUserStatement",
    "MariaDBDenyStatement",
    "MariaDBDropFunctionStatement",
    "MariaDBDropProcedureStatement",
    "MariaDBDropRoleStatement",
    "MariaDBDropUserStatement",
    "MariaDBFlushStatement",
    "MariaDBGrantStatement",
    "MariaDBInsertExpression",
    "MariaDBKillStatement",
    "MariaDBLoadDataStatement",
    "MariaDBRenameIndexStatement",
    "MariaDBRenameTableStatement",
    "MariaDBRevokeStatement",
    "MariaDBRoutineExpression",
    "MariaDBShowCharsetStatement",
    "MariaDBShowCollationStatement",
    "MariaDBShowColumnsStatement",
    "MariaDBShowCreateTableStatement",
    "MariaDBShowCreateTriggerStatement",
    "MariaDBShowCreateViewStatement",
    "MariaDBShowDatabasesStatement",
    "MariaDBShowEnginesStatement",
    "MariaDBShowErrorsStatement",
    "MariaDBShowExpression",
    "MariaDBShowGrantsStatement",
    "MariaDBShowIndexStatement",
    "MariaDBShowMasterStatusStatement",
    "MariaDBShowPluginsStatement",
    "MariaDBShowProcessListStatement",
    "MariaDBShowRelationExpression",
    "MariaDBShowSlaveStatusStatement",
    "MariaDBShowStatusStatement",
    "MariaDBShowTableStatusStatement",
    "MariaDBShowTablesStatement",
    "MariaDBShowTriggersStatement",
    "MariaDBShowVariablesStatement",
    "MariaDBShowWarningsStatement",
    "MariaDBShutdownStatement",
    "MariaDBTableMaintenanceStatement",
    "MariaDBTruncateExpression",
    "TableMaintenanceOperation",

]

#: name -> defining module, relative to this package
_REEXPORTS = {
    "AccountSpec": ".admin",
    "FlushOption": ".admin",
    "GrantPrivilege": ".admin",
    "KillTarget": ".admin",
    "LoadDataOptions": ".load_data",
    "MariaDBAlterTableExpression": ".alter_table",
    "MariaDBAlterTableOptionsStatement": ".alter_table_options",
    "MariaDBAlterUserStatement": ".admin",
    "MariaDBCallStatement": ".routine",
    "MariaDBCreateFunctionStatement": ".routine",
    "MariaDBCreateProcedureStatement": ".routine",
    "MariaDBCreateRoleStatement": ".admin",
    "MariaDBCreateTableOptions": ".table_options",
    "MariaDBCreateUserStatement": ".admin",
    "MariaDBDenyStatement": ".admin",
    "MariaDBDropFunctionStatement": ".routine",
    "MariaDBDropProcedureStatement": ".routine",
    "MariaDBDropRoleStatement": ".admin",
    "MariaDBDropUserStatement": ".admin",
    "MariaDBFlushStatement": ".admin",
    "MariaDBGrantStatement": ".admin",
    "MariaDBInsertExpression": ".dml",
    "MariaDBKillStatement": ".admin",
    "MariaDBLoadDataStatement": ".load_data",
    "MariaDBRenameIndexStatement": ".rename_index",
    "MariaDBRenameTableStatement": ".rename_table",
    "MariaDBRevokeStatement": ".admin",
    "MariaDBRoutineExpression": ".routine",
    "MariaDBShowCharsetStatement": ".show",
    "MariaDBShowCollationStatement": ".show",
    "MariaDBShowColumnsStatement": ".show",
    "MariaDBShowCreateTableStatement": ".show",
    "MariaDBShowCreateTriggerStatement": ".show",
    "MariaDBShowCreateViewStatement": ".show",
    "MariaDBShowDatabasesStatement": ".show",
    "MariaDBShowEnginesStatement": ".show",
    "MariaDBShowErrorsStatement": ".show",
    "MariaDBShowExpression": ".show",
    "MariaDBShowGrantsStatement": ".show",
    "MariaDBShowIndexStatement": ".show",
    "MariaDBShowMasterStatusStatement": ".show",
    "MariaDBShowPluginsStatement": ".show",
    "MariaDBShowProcessListStatement": ".show",
    "MariaDBShowRelationExpression": ".show",
    "MariaDBShowSlaveStatusStatement": ".show",
    "MariaDBShowStatusStatement": ".show",
    "MariaDBShowTableStatusStatement": ".show",
    "MariaDBShowTablesStatement": ".show",
    "MariaDBShowTriggersStatement": ".show",
    "MariaDBShowVariablesStatement": ".show",
    "MariaDBShowWarningsStatement": ".show",
    "MariaDBShutdownStatement": ".admin",
    "MariaDBTableMaintenanceStatement": ".maintenance",
    "MariaDBTruncateExpression": ".truncate",
    "TableMaintenanceOperation": ".maintenance",

}


def __getattr__(name: str):
    """Resolve a re-exported name on first access (PEP 562)."""
    try:
        module_name = _REEXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = _import_module(module_name, __name__).__dict__[name]
    globals()[name] = value  # cache: subsequent access is a plain attribute lookup
    return value


def __dir__() -> list:
    """Make the lazy re-exports visible to ``dir()``."""
    return sorted(set(globals()) | set(__all__))
