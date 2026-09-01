# mariadb/protocols/dialect_generated.py
"""Auto-generated protocol declarations (P7, 2026-09-01).

Functional-group principle: every public format_*/supports_* on a
backend mixin is declared here so dialect users can program against
the capability contract.  Regenerate via scripts/p7_generate_protocols.py
when mixins gain new public rendering methods.
"""

from typing import Any, Dict, List, Optional, Tuple

from typing import Protocol

class MariaDBShowDialectSupport(Protocol):
    """Auto-generated capability protocol (P7)."""

    def format_show_create_table(self, expr: 'ShowCreateTableExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_create_view(self, expr: 'ShowCreateViewExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_create_trigger(self, expr: 'ShowCreateTriggerExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_columns(self, expr: 'ShowColumnsExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_index(self, expr: 'ShowIndexExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_tables(self, expr: 'ShowTablesExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_databases(self, expr: 'ShowDatabasesExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_table_status(self, expr: 'ShowTableStatusExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_triggers(self, expr: 'ShowTriggersExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_variables(self, expr: 'ShowVariablesExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_status(self, expr: 'ShowStatusExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_processlist(self, expr: 'ShowProcessListExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_warnings(self, expr: 'ShowWarningsExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_errors(self, expr: 'ShowErrorsExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_engines(self, expr: 'ShowEnginesExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_charset(self, expr: 'ShowCharsetExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_collation(self, expr: 'ShowCollationExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_grants(self, expr: 'ShowGrantsExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_show_plugins(self, expr: 'ShowPluginsExpression') -> Tuple[str, tuple]:
        ...  # pragma: no cover
