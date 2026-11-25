# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/table_constraint_change_suggestion.py
"""MariaDB's answer to the table-constraint change point.

A named constraint removed from the declaration is dropped with the real
``DropTableConstraintAction`` (``DROP CONSTRAINT <name>``) on 10.2.1+, where
MariaDB's grammar has that rule. Below the floor this backend falls back to
the per-kind spellings the older grammar does have: ``DROP INDEX`` for a
UNIQUE key and ``DROP PRIMARY KEY`` for a primary key. CHECK constraints do
not exist there, and there is no expression node for ``DROP FOREIGN KEY``,
so those two cases answer explicit unsupported instead.

A constraint added by the declaration is returned as a real
``AddTableConstraintAction`` carrying a reconstructed ``TableConstraint``.
Reconstruction is deliberately conservative: the frozen projection drops the
branch class, so a columns-only projection cannot say whether it was a
PRIMARY KEY or a UNIQUE constraint. Such a projection is refused rather than
guessed; a branch carrying ``references`` (FOREIGN KEY), an explicit ``kind``
field, or a real ``TableConstraint`` node is rebuilt faithfully.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ....expression.objects import Index
from ....expression.statements import (
    AddTableConstraintAction,
    DropIndexAction,
    DropTableConstraintAction,
    TableCheckConstraint,
    TableConstraint,
    TableExcludeConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from ....suggestion import TableConstraintChangeSuggestion
from ._change_plan_common import (
    canonical,
    name_of,
    one_statement,
    params_of,
    table_for,
)

#: The capability probe that gates adding each kind of table constraint.
_KIND_GATES = {
    "PRIMARY KEY": "supports_primary_key_constraint",
    "UNIQUE": "supports_unique_constraint",
    "FOREIGN KEY": "supports_foreign_key_constraint",
    "CHECK": "supports_check_constraint",
    "EXCLUDE": "supports_exclude_constraint",
}

_TRAIT_FLAGS = (
    "deferrable",
    "not_deferrable",
    "initially_deferred",
    "initially_immediate",
)

#: Why a columns-only constraint projection cannot be added: the frozen branch
#: projection has no class tag to tell PRIMARY KEY from UNIQUE.
AMBIGUOUS_BRANCH_REASON = (
    "A columns-only frozen constraint branch cannot distinguish PRIMARY KEY "
    "from UNIQUE; adding one would guess a kind."
)


def _kind(value: Any) -> Optional[str]:
    """The constraint kind, when the value says which one it is.

    A real ``TableConstraint`` answers from its branch class. A frozen
    projection answers from an explicit ``kind`` field or from fields only one
    branch has (``references``, ``condition``, ``operator``/``index_method``).
    A columns-only projection has no class tag and answers ``None``.
    """
    if isinstance(value, TableConstraint):
        branch = value.branch
        if isinstance(branch, TablePrimaryKeyConstraint):
            return "PRIMARY KEY"
        if isinstance(branch, TableUniqueConstraint):
            return "UNIQUE"
        if isinstance(branch, TableForeignKeyConstraint):
            return "FOREIGN KEY"
        if isinstance(branch, TableCheckConstraint):
            return "CHECK"
        if isinstance(branch, TableExcludeConstraint):
            return "EXCLUDE"
        return None

    params = params_of(value)
    if params is None:
        return None
    branch = params_of(params.get("branch"))
    explicit = params.get("kind") or (branch.get("kind") if branch else None)
    if isinstance(explicit, str) and explicit.strip():
        return " ".join(explicit.strip().upper().split())
    # MariaDB's PRIMARY KEY has no symbol to carry a name, so the literal name
    # PRIMARY is the one unambiguous columns-only case in a frozen projection.
    declared_name = params.get("name")
    if isinstance(declared_name, str) and declared_name.strip().upper() == "PRIMARY":
        return "PRIMARY KEY"
    if branch is None:
        return None
    if "references" in branch:
        return "FOREIGN KEY"
    if "condition" in branch:
        return "CHECK"
    if "operator" in branch or "index_method" in branch:
        return "EXCLUDE"
    return None


def _gated(dialect: Any, kind: Optional[str]) -> bool:
    """Whether this dialect declares support for adding ``kind``."""
    probe = _KIND_GATES.get(kind or "")
    return probe is not None and bool(getattr(dialect, probe, lambda: False)())


def _traits_allowed(dialect: Any, params: Dict[str, Any]) -> bool:
    """Refuse a trait MariaDB cannot spell instead of dropping it quietly."""
    if params.get("validation") is not None:
        # MariaDB has no NOT VALID and no add-first-validate-later spelling.
        return False
    if any(params.get(flag) for flag in _TRAIT_FLAGS):
        if not getattr(dialect, "supports_deferrable_constraint", lambda: False)():
            return False
    if params.get("enforced") or params.get("not_enforced"):
        if not getattr(dialect, "supports_constraint_enforced", lambda: False)():
            return False
    return True


def _columns(branch: Dict[str, Any]) -> Optional[List[str]]:
    columns = branch.get("columns")
    if not isinstance(columns, (list, tuple)) or not columns:
        return None
    if not all(isinstance(column, str) and column.strip() for column in columns):
        return None
    return list(columns)


def _build_add(dialect: Any, value: Any) -> Optional[AddTableConstraintAction]:
    """Build a real ADD CONSTRAINT action, or ``None`` when not truthful."""
    kind = _kind(value)
    if not _gated(dialect, kind):
        return None

    if isinstance(value, TableConstraint):
        constraint = value
        if (
            value.validation is not None
            or any(getattr(value, flag, False) for flag in _TRAIT_FLAGS)
            or value.enforced
            or value.not_enforced
        ):
            return None
    else:
        params = params_of(value)
        if params is None or not _traits_allowed(dialect, params):
            return None
        branch = params_of(params.get("branch"))
        if branch is None:
            return None
        columns = _columns(branch)
        if columns is None:
            return None
        if kind in ("PRIMARY KEY", "UNIQUE"):
            branch_class = (
                TablePrimaryKeyConstraint if kind == "PRIMARY KEY" else TableUniqueConstraint
            )
            node = branch_class(dialect, columns)
        elif kind == "FOREIGN KEY":
            references = branch.get("references")
            if not isinstance(references, (list, tuple)) or len(references) != 2:
                return None
            referenced_table = references[0]
            table_params = params_of(referenced_table)
            referenced_name = (
                table_params.get("name")
                if table_params is not None
                else getattr(referenced_table, "name", None)
            )
            referenced_columns = references[1]
            if (
                not isinstance(referenced_name, str)
                or not referenced_name.strip()
                or not isinstance(referenced_columns, (list, tuple))
                or not referenced_columns
            ):
                return None
            from ....expression.objects import Table

            node = TableForeignKeyConstraint(
                dialect,
                columns=columns,
                references=(Table(dialect, referenced_name), list(referenced_columns)),
                on_delete=branch.get("on_delete"),
                on_update=branch.get("on_update"),
                match_type=branch.get("match_type"),
            )
        else:
            # CHECK needs a predicate class the frozen projection no longer
            # carries; EXCLUDE has no MariaDB grammar at all.
            return None
        constraint = TableConstraint(dialect, branch=node, name=params.get("name"))

    return AddTableConstraintAction(dialect, constraint)


def _build_drop(dialect: Any, value: Any) -> Optional[Any]:
    """Build the real drop action for a removed constraint, or ``None``."""
    kind = _kind(value)
    name = name_of(value)
    if kind == "PRIMARY KEY":
        # MariaDB discards a PRIMARY KEY symbol; PRIMARY is the name its
        # DROP CONSTRAINT grammar accepts, and it spells DROP PRIMARY KEY.
        name = "PRIMARY"
    if not name:
        return None
    if getattr(dialect, "supports_drop_constraint", lambda: False)():
        return DropTableConstraintAction(dialect, name)
    if kind == "PRIMARY KEY":
        return DropTableConstraintAction(dialect, "PRIMARY")
    if kind == "UNIQUE" and getattr(dialect, "supports_alter_table_index_actions", lambda: False)():
        return DropIndexAction(dialect, Index(dialect, name))
    # No expression node spells DROP FOREIGN KEY, and CHECK has no grammar on
    # a server too old to have DROP CONSTRAINT.
    return None


def _diff(old: Tuple[Any, ...], new: Tuple[Any, ...]) -> Tuple[List[Any], List[Any]]:
    old_by_key = {canonical(item): item for item in old}
    new_by_key = {canonical(item): item for item in new}
    dropped = [item for key, item in old_by_key.items() if key not in new_by_key]
    added = [item for key, item in new_by_key.items() if key not in old_by_key]
    return dropped, added


class MariaDBTableConstraintChangeSuggestionMixin:
    """Answer a table-constraint change with real drop/add action chains."""

    def suggest_table_constraint_change(
        self, point: TableConstraintChangeSuggestion
    ) -> TableConstraintChangeSuggestion:
        """Return one ALTER TABLE statement per dropped then added constraint."""
        table = table_for(self, point.table_name)
        if table is None:
            return TableConstraintChangeSuggestion(operations=False)
        dropped, added = _diff(
            tuple(point.old_constraints or ()), tuple(point.new_constraints or ())
        )
        if not dropped and not added:
            return TableConstraintChangeSuggestion(operations=None)
        if added and not getattr(self, "supports_add_constraint", lambda: False)():
            return TableConstraintChangeSuggestion(operations=False)

        operations = []
        for value in dropped:
            action = _build_drop(self, value)
            if action is None:
                return TableConstraintChangeSuggestion(operations=False)
            operations.append(one_statement(self, table, action))
        for value in added:
            action = _build_add(self, value)
            if action is None:
                return TableConstraintChangeSuggestion(operations=False)
            operations.append(one_statement(self, table, action))
        return TableConstraintChangeSuggestion(operations=tuple(operations))


__all__ = ["AMBIGUOUS_BRANCH_REASON", "MariaDBTableConstraintChangeSuggestionMixin"]
