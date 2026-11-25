# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/_change_plan_common.py
"""Shared readers for MariaDB's four change-plan suggestion protocols.

Core freezes a change point's old/new declarations with ``migration._freeze``:
an expression becomes ``("params", ((field, value), ...))``, while a plain
scalar survives unchanged. The four suggestion mixins therefore read the same
shape: they ask for a field by name, compare two projections by a canonical
key, and turn a projection back into a *real* expression node only where the
projection carries enough information to do so honestly.

Nothing here renders SQL. Nodes are built from existing expression classes and
rendered later by the dialect, in the usual expression -> formatter direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ....expression.objects import Table
from ....expression.statements import AlterTableStatement


def params_of(value: Any) -> Optional[Dict[str, Any]]:
    """Return the constructor parameters of a node or a frozen projection.

    ``None`` means the value carries no parameter map (a bare string, a
    ``("repr", ...)`` fallback, or anything else that cannot be read). A node
    is read through its own ``get_params()``, so a caller that hands the point
    real expression instances is handled the same way as core's frozen ones.
    """
    if value is None:
        return None
    getter = getattr(value, "get_params", None)
    if callable(getter):
        try:
            raw = getter()
        except Exception:  # pragma: no cover - a malformed node is not ours
            return None
        return dict(raw) if isinstance(raw, dict) else None
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "params":
        pairs = value[1]
        if isinstance(pairs, (list, tuple)):
            result: Dict[str, Any] = {}
            for pair in pairs:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    result[str(pair[0])] = pair[1]
            return result
    return None


def canonical(value: Any) -> Any:
    """A hashable, comparable key for a node or a frozen projection.

    Two projections with the same fields and values get the same key, which is
    what a change point needs in order to tell "added" from "dropped" without
    asking a dialect to render either one.
    """
    params = params_of(value)
    if params is not None:
        return ("params", tuple(sorted((key, canonical(item)) for key, item in params.items())))
    if isinstance(value, dict):
        return ("dict", tuple(sorted((str(key), canonical(item)) for key, item in value.items())))
    if isinstance(value, (list, tuple)):
        return tuple(canonical(item) for item in value)
    try:
        hash(value)
    except TypeError:
        return ("repr", repr(value))
    return value


def name_of(value: Any) -> Optional[str]:
    """The declared name of a node or projection, when it has a usable one."""
    params = params_of(value)
    if params is not None:
        name = params.get("name")
    else:
        name = getattr(value, "name", None)
    return name if isinstance(name, str) and name.strip() else None


def table_for(dialect: Any, table_name: Any) -> Optional[Table]:
    """Resolve the point's table name to a MariaDB-owned ``Table`` object.

    A change point without a table name cannot name a target for an ALTER
    TABLE; callers refuse the point rather than inventing a placeholder.
    """
    if not isinstance(table_name, str) or not table_name.strip():
        return None
    return Table(dialect, table_name)


def one_statement(dialect: Any, table: Table, action: Any) -> AlterTableStatement:
    """Wrap one ALTER TABLE action in its own statement.

    An expression maps to one SQL statement, and MariaDB's ``ALTER TABLE``
    grammar may not combine arbitrary actions; one action per statement keeps
    every returned operation executable on its own.
    """
    return AlterTableStatement(dialect, table, [action])


@dataclass(frozen=True)
class _PartitionPlan:
    """Minimal caller-owned plan read by the existing partition suggestions."""

    table: Table
    definitions: tuple = ()
    cutoff: object = None
    count: object = None
