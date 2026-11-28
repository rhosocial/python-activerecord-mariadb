# src/rhosocial/activerecord/backend/impl/mariadb/expression_registry.py
"""MariaDB's expression table: core's kinds merged with MariaDB's own.

``MARIADB_EXPRESSIONS`` is the mapping this backend's expression package
declares. The published table is the merge of core's mapping and that one --
never a sibling backend's, and no dialect takes part.

Both mappings are data (``kind -> fully qualified class name``); resolution
imports a class only when an artifact names its kind.
"""

from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSIONS,
    ExpressionRegistry,
    collect_expressions,
    merge_expressions,
)

#: The kinds MariaDB's own expression package declares.
MARIADB_EXPRESSIONS = collect_expressions(
    "rhosocial.activerecord.backend.impl.mariadb.expression"
)

#: MariaDB's table: core's kinds plus MariaDB's own, frozen.
MARIADB_EXPRESSION_REGISTRY = ExpressionRegistry(
    merge_expressions(CORE_EXPRESSIONS, MARIADB_EXPRESSIONS)
).freeze()

__all__ = ["MARIADB_EXPRESSIONS", "MARIADB_EXPRESSION_REGISTRY"]
