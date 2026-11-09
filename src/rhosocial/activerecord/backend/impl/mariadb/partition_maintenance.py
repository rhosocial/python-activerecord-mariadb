# src/rhosocial/activerecord/backend/impl/mariadb/partition_maintenance.py
"""Backend-level MariaDB partition maintenance helpers.

The expression layer builds one statement at a time.  This module supplies the
three operations an application needs around that layer:

* ``ensure`` -- add the partitions a plan declares that the table does not have;
* ``list`` -- read ``information_schema.PARTITIONS`` into a small report;
* ``drop_before`` -- drop the partitions whose whole range is older than a
  caller-supplied cutoff, dry-run by default.

The module deliberately carries no table names, retention defaults, or
calendar vocabulary.  A plan is a caller-owned list of partition definitions,
so the application decides which partitions exist and how long they live.

MariaDB notes that shape the API:

* ``ALTER TABLE ... ADD PARTITION`` only appends to the current RANGE maximum.
  A missing definition in a gap below the maximum is created by reorganising
  the following partition into ``(missing definitions, that partition)``.
* A definition that must land before an existing ``MAXVALUE`` partition is
  created by reorganising that ``MAXVALUE`` partition the same way.
* The catalogue has to agree with the plan before either verb is safe.  An
  existing partition the plan does not name, a boundary that disagrees with
  the plan, a method drift, or a subpartitioned reorganisation target leaves
  the change in ``skipped`` with the reason.
* ``DROP PARTITION`` cannot remove the last partition of a table.  When the
  cutoff would remove every existing partition, the newest candidate is kept
  and reported.

The catalogue rules are reported, never silently worked around.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    FunctionCall,
    Literal,
    LogicalPredicate,
    OrderByClause,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.partition import PartitionInfo, PartitionReport

from .expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBPartitionDefinition,
    MariaDBPartitionMaxValue,
    MariaDBReorganizePartitionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import (
        AsyncMariaDBBackend,
    )
    from rhosocial.activerecord.backend.impl.mariadb.backend.backend import MariaDBBackend

__all__ = [
    "MariaDBPartitionInfo",
    "MariaDBPartitionPlan",
    "MariaDBPartitionReport",
    "MariaDBPartitionMaintenance",
    "AsyncMariaDBPartitionMaintenance",
    "plan_additions",
    "select_drops",
]

#: Sentinel used when a plan's upper bound is ``MAXVALUE``.
_MAXVALUE = object()

# The report value objects come from the core contract. The module keeps its
# historical names so callers and tests do not depend on the import path.
MariaDBPartitionInfo = PartitionInfo
MariaDBPartitionReport = PartitionReport


@dataclass(frozen=True)
class MariaDBPartitionPlan:
    """A caller-owned set of partition definitions.

    The plan does not say how to lay out a calendar; it only lists the
    definitions that must exist.  Definitions must carry unique names.  When
    all definitions use ``less_than`` (RANGE), they must also be in ascending
    order, because that is the order ``ALTER TABLE ... ADD PARTITION``
    executes them in.

    Attributes:
        table: Target table name.
        definitions: Partition definitions in declaration order.

    Raises:
        ValueError: if the table name is blank, the list is empty, names
            repeat, or RANGE definitions are not in ascending order.
    """

    table: str
    definitions: Tuple[MariaDBPartitionDefinition, ...]

    def __post_init__(self) -> None:
        if not self.table or not self.table.strip():
            raise ValueError("table must be a non-empty string")
        if not self.definitions:
            raise ValueError("definitions must not be empty")

        names = [definition.name for definition in self.definitions]
        if len(set(names)) != len(names):
            raise ValueError("partition names in a plan must be unique")

        bounds = [_upper_bound_value(definition) for definition in self.definitions]
        if all(bound is not None for bound in bounds):
            previous = None
            for index, (definition, bound) in enumerate(zip(self.definitions, bounds)):
                if bound is _MAXVALUE:
                    if index != len(self.definitions) - 1:
                        raise ValueError(
                            "a MAXVALUE partition must be the last definition in a plan"
                        )
                    continue
                key = _comparable(bound)
                if previous is not None and _compare(key, previous) <= 0:
                    raise ValueError(
                        "RANGE partition definitions must be in ascending order: "
                        f"{definition.name} does not advance the upper bound"
                    )
                previous = key
        elif any(bound is not None for bound in bounds):
            raise ValueError(
                "a plan must use either less_than (RANGE) or in_values (LIST) "
                "definitions, not both"
            )


def _upper_bound_value(definition: MariaDBPartitionDefinition) -> Any:
    """Return the first ``less_than`` value, ``_MAXVALUE``, or ``None``."""
    if definition.less_than is None:
        return None
    first = definition.less_than[0]
    if isinstance(first, MariaDBPartitionMaxValue):
        return _MAXVALUE
    return getattr(first, "value", first)


def _comparable(value: Any) -> Any:
    """Normalise a boundary value for ordering and cutoff comparisons."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        try:
            return datetime.combine(date.fromisoformat(text), time.min)
        except ValueError:
            return text
    return value


def _compare(left: Any, right: Any) -> int:
    """Compare two normalised values, refusing incomparable kinds."""
    try:
        if left < right:
            return -1
        if left > right:
            return 1
        return 0
    except TypeError as error:
        raise ValueError(
            f"partition bound value {left!r} is not comparable to {right!r}"
        ) from error


def _ordered_definitions(plan: MariaDBPartitionPlan) -> List[MariaDBPartitionDefinition]:
    """Return RANGE definitions in plan order; refuse LIST plans."""
    if any(definition.less_than is None for definition in plan.definitions):
        raise ValueError(
            "drop_before applies only to RANGE plans (definitions with less_than)"
        )
    return list(plan.definitions)


def _plan_kind(plan: MariaDBPartitionPlan) -> str:
    """Return ``"RANGE"`` or ``"LIST"`` for the plan's boundary form."""
    bounds = [_upper_bound_value(definition) for definition in plan.definitions]
    if all(bound is None for bound in bounds):
        return "LIST"
    if all(bound is not None for bound in bounds):
        return "RANGE"
    raise ValueError(
        "a plan must use either less_than (RANGE) or in_values (LIST) definitions"
    )


def _expected_methods(kind: str) -> Tuple[str, ...]:
    """Return the MariaDB ``PARTITION_METHOD`` words a plan kind accepts."""
    if kind == "RANGE":
        return ("RANGE", "RANGE COLUMNS")
    return ("LIST", "LIST COLUMNS")


def _top_level_infos(report: MariaDBPartitionReport) -> Dict[str, PartitionInfo]:
    """Return the report's first-level partitions keyed by name."""
    names = set(report.partition_names)
    return {info.name: info for info in report.partitions if info.name in names}


def _format_bound_text(value: Any) -> str:
    """Return the text MariaDB uses for one boundary value."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _expected_description(
    definition: MariaDBPartitionDefinition,
    kind: str,
) -> str:
    """Return the ``PARTITION_DESCRIPTION`` text a plan definition implies."""
    parts: List[str] = []
    if kind == "RANGE":
        for item in definition.less_than or ():
            if isinstance(item, MariaDBPartitionMaxValue):
                parts.append("MAXVALUE")
            else:
                parts.append(_format_bound_text(getattr(item, "value", item)))
    else:
        for item in definition.in_values or ():
            if isinstance(item, (list, tuple)):
                inner = ", ".join(
                    _format_bound_text(getattr(value, "value", value))
                    for value in item
                )
                parts.append(f"({inner})")
            else:
                parts.append(_format_bound_text(getattr(item, "value", item)))
    return ", ".join(parts)


def _description_tokens(text: Optional[str]) -> Tuple[str, ...]:
    """Split a catalogue description into comparable boundary tokens."""
    if text is None:
        return ()
    cleaned = str(text).strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    tokens: List[str] = []
    for token in cleaned.split(","):
        value = token.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        tokens.append(value)
    return tuple(tokens)


def _token_matches(expected: str, actual: str) -> bool:
    """Compare boundary tokens, accepting equivalent numeric and temporal text."""
    if expected == actual:
        return True
    try:
        if Decimal(expected) == Decimal(actual):
            return True
    except (ArithmeticError, ValueError):
        pass
    left = _comparable(expected)
    right = _comparable(actual)
    try:
        return _compare(left, right) == 0
    except ValueError:
        return False


def _description_matches(
    definition: MariaDBPartitionDefinition,
    info: PartitionInfo,
    kind: str,
) -> bool:
    """Return whether the catalogue description agrees with the plan."""
    expected = _description_tokens(_expected_description(definition, kind))
    actual = _description_tokens(info.bound)
    if len(expected) != len(actual):
        return False
    return all(
        _token_matches(expected_token, actual_token)
        for expected_token, actual_token in zip(expected, actual)
    )


def _catalogue_issues(
    plan: MariaDBPartitionPlan,
    report: MariaDBPartitionReport,
) -> List[str]:
    """Return boundary and method findings for the partitions the plan names."""
    infos = _top_level_infos(report)
    if not infos:
        return [
            f"table {plan.table} has no partitions; the plan describes "
            "partitions that require an existing partition layout"
        ]

    kind = _plan_kind(plan)
    methods = _expected_methods(kind)
    issues: List[str] = []
    for definition in plan.definitions:
        info = infos.get(definition.name)
        if info is None:
            continue
        method = (info.method or "").strip().upper()
        if method not in methods:
            issues.append(
                f"partition {definition.name}: PARTITION_METHOD is "
                f"{info.method or 'missing'}, expected {' or '.join(methods)} "
                "(method drift)"
            )
        if not _description_matches(definition, info, kind):
            issues.append(
                f"partition {definition.name}: PARTITION_DESCRIPTION is "
                f"{info.bound!r}, expected "
                f"{_expected_description(definition, kind)!r} (boundary drift)"
            )
    return issues


@dataclass(frozen=True)
class _MariaDBReorganization:
    """One ``REORGANIZE PARTITION`` the planner intends to run."""

    partition: str
    into: Tuple[MariaDBPartitionDefinition, ...]


def _plan_changes(
    plan: MariaDBPartitionPlan,
    report: MariaDBPartitionReport,
) -> Tuple[
    List[MariaDBPartitionDefinition],
    List[_MariaDBReorganization],
    List[Tuple[str, str]],
]:
    """Return the ADD definitions, REORGANIZE operations and skipped work.

    The plan is trusted only when the catalogue agrees with it: every existing
    partition is named by the plan, and every named one reports the plan's
    method and boundary.  Anything else is reported in the skipped list rather
    than sent as DDL MariaDB would reject or apply to the wrong range.
    """
    infos = _top_level_infos(report)
    plan_names = {definition.name for definition in plan.definitions}
    missing = [
        definition
        for definition in plan.definitions
        if definition.name not in infos
    ]
    if not missing:
        return [], [], []

    if not infos:
        reason = (
            f"table {plan.table} is not partitioned; ADD PARTITION and "
            "REORGANIZE PARTITION require an existing partition layout"
        )
        return [], [], [(definition.name, reason) for definition in missing]

    unknown = sorted(set(infos) - plan_names)
    if unknown:
        reason = (
            "existing partition(s) not named by the plan make the current "
            f"upper bound unknown: {', '.join(unknown)}"
        )
        return [], [], [(definition.name, reason) for definition in missing]

    issues = _catalogue_issues(plan, report)
    if issues:
        reason = "; ".join(issues)
        return [], [], [(definition.name, reason) for definition in missing]

    kind = _plan_kind(plan)
    if kind == "LIST":
        return missing, [], []

    definitions_by_name = {
        definition.name: definition for definition in plan.definitions
    }
    existing_definitions = [
        definition
        for definition in plan.definitions
        if definition.name in infos
    ]
    has_maxvalue = any(
        _upper_bound_value(definition) is _MAXVALUE
        for definition in existing_definitions
    )

    additions: List[MariaDBPartitionDefinition] = []
    groups: Dict[str, List[MariaDBPartitionDefinition]] = {}
    skipped: List[Tuple[str, str]] = []

    for index, definition in enumerate(plan.definitions):
        if definition.name in infos:
            continue
        bound = _upper_bound_value(definition)
        previous = next(
            (
                candidate
                for candidate in reversed(plan.definitions[:index])
                if candidate.name in infos
            ),
            None,
        )
        following = next(
            (
                candidate
                for candidate in plan.definitions[index + 1:]
                if candidate.name in infos
            ),
            None,
        )

        if following is None:
            if has_maxvalue:
                skipped.append(
                    (
                        definition.name,
                        "cannot add a partition after the existing MAXVALUE "
                        "partition",
                    )
                )
            else:
                additions.append(definition)
            continue

        if bound is _MAXVALUE:
            skipped.append(
                (
                    definition.name,
                    "a MAXVALUE definition cannot precede the existing "
                    f"partition {following.name}",
                )
            )
            continue

        if previous is not None:
            previous_bound = _upper_bound_value(previous)
            if previous_bound is not _MAXVALUE:
                if _compare(_comparable(bound), _comparable(previous_bound)) <= 0:
                    skipped.append(
                        (
                            definition.name,
                            f"bound {_format_bound_text(bound)} is not above the "
                            f"previous existing partition {previous.name}",
                        )
                    )
                    continue

        following_bound = _upper_bound_value(following)
        if following_bound is not _MAXVALUE:
            if _compare(_comparable(bound), _comparable(following_bound)) >= 0:
                skipped.append(
                    (
                        definition.name,
                        f"bound {_format_bound_text(bound)} is not below the "
                        f"following existing partition {following.name}",
                    )
                )
                continue

        groups.setdefault(following.name, []).append(definition)

    reorganizations: List[_MariaDBReorganization] = []
    for target_name, group in groups.items():
        target_info = infos[target_name]
        children = (target_info.extras or {}).get("children")
        if children:
            reason = (
                f"partition {target_name} has subpartitions; MariaDB cannot "
                "REORGANIZE PARTITION a subpartitioned partition"
            )
            skipped.extend((definition.name, reason) for definition in group)
            continue
        reorganizations.append(
            _MariaDBReorganization(
                partition=target_name,
                into=tuple(group) + (definitions_by_name[target_name],),
            )
        )

    return additions, reorganizations, skipped


def plan_additions(
    plan: MariaDBPartitionPlan,
    existing_names: Sequence[str],
) -> Tuple[List[MariaDBPartitionDefinition], List[Tuple[str, str]]]:
    """Return the definitions a plain ``ADD PARTITION`` may append.

    Args:
        plan: Caller-owned plan.
        existing_names: Top-level partition names currently on the table.

    Returns:
        ``(additions, skipped)``.  ``additions`` are in plan order and can be
        sent in one ``ALTER TABLE ... ADD PARTITION`` statement.  ``skipped``
        pairs a definition name with the reason it cannot be added.

    Raises:
        ValueError: if the plan mixes RANGE and LIST definitions.
    """
    existing = set(existing_names)
    missing = [definition for definition in plan.definitions if definition.name not in existing]
    if not missing:
        return [], []

    bounds = [_upper_bound_value(definition) for definition in plan.definitions]
    is_range = all(bound is not None for bound in bounds)
    if not is_range and any(bound is not None for bound in bounds):
        raise ValueError(
            "a plan must use either less_than (RANGE) or in_values (LIST) "
            "definitions, not both"
        )

    if not is_range:
        # LIST values are independent, so missing definitions can simply be added.
        return missing, []

    skipped: List[Tuple[str, str]] = []
    existing_definitions = [
        definition for definition in plan.definitions if definition.name in existing
    ]
    unknown = existing - {definition.name for definition in existing_definitions}
    if unknown:
        for definition in missing:
            skipped.append(
                (
                    definition.name,
                    "existing partition(s) not named by the plan make the "
                    "current upper bound unknown; include them in the plan",
                )
            )
        return [], skipped

    current_max = None
    for definition in existing_definitions:
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            for candidate in missing:
                skipped.append(
                    (
                        candidate.name,
                        "the table already has a MAXVALUE partition; "
                        "REORGANIZE PARTITION is required",
                    )
                )
            return [], skipped
        key = _comparable(bound)
        if current_max is None or _compare(key, current_max) > 0:
            current_max = key

    additions: List[MariaDBPartitionDefinition] = []
    for definition in missing:
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            additions.append(definition)
            current_max = None
            continue
        key = _comparable(bound)
        if current_max is not None and _compare(key, current_max) <= 0:
            skipped.append(
                (
                    definition.name,
                    "upper bound is not above the current maximum; "
                    "REORGANIZE PARTITION is required",
                )
            )
            continue
        additions.append(definition)
        current_max = key

    return additions, skipped


def select_drops(
    plan: MariaDBPartitionPlan,
    existing_names: Sequence[str],
    cutoff: Any,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Return the partitions ``drop_before`` may drop and the skipped ones.

    A partition is a candidate when its whole range is at or before ``cutoff``:
    its upper bound (the first column, for multi-column RANGE) is less than or
    equal to the cutoff.  The newest candidate is kept when dropping all
    existing partitions would make the table non-partitioned, because MariaDB
    refuses to drop the last partition.

    Returns:
        ``(dropped, skipped)``.

    Raises:
        ValueError: if the plan is not RANGE, or a bound and the cutoff are
            not comparable.
    """
    existing = set(existing_names)
    ordered = _ordered_definitions(plan)
    threshold = _comparable(cutoff)

    candidates: List[MariaDBPartitionDefinition] = []
    for definition in ordered:
        if definition.name not in existing:
            continue
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            continue
        if _compare(_comparable(bound), threshold) <= 0:
            candidates.append(definition)

    skipped: List[Tuple[str, str]] = []
    if candidates and len(candidates) == len(existing):
        keep = candidates[-1]
        candidates = candidates[:-1]
        skipped.append(
            (
                keep.name,
                "keeping the newest partition; MariaDB cannot drop the last "
                "partition of a table",
            )
        )

    return [definition.name for definition in candidates], skipped


def _metadata_expression(dialect: Any, table: str) -> QueryStatement:
    """Build the ``information_schema.PARTITIONS`` query for one table."""
    partitions = Table(dialect, "PARTITIONS", catalog_name="information_schema")
    return QueryStatement(
        dialect,
        select=[
            Column(dialect, "PARTITION_NAME", alias="name"),
            Column(dialect, "SUBPARTITION_NAME", alias="subname"),
            Column(dialect, "PARTITION_METHOD", alias="method"),
            Column(dialect, "SUBPARTITION_METHOD", alias="submethod"),
            Column(dialect, "PARTITION_DESCRIPTION", alias="description"),
            Column(dialect, "TABLE_ROWS", alias="table_rows"),
            Column(dialect, "DATA_LENGTH", alias="data_length"),
            Column(dialect, "INDEX_LENGTH", alias="index_length"),
        ],
        from_=partitions,
        where=LogicalPredicate(
            dialect,
            "AND",
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "TABLE_SCHEMA"),
                FunctionCall(dialect, "DATABASE"),
            ),
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "TABLE_NAME"),
                Literal(dialect, table),
            ),
            Column(dialect, "PARTITION_NAME").is_not_null(),
        ),
        order_by=OrderByClause(
            dialect,
            [
                (Column(dialect, "PARTITION_NAME"), "ASC"),
                (Column(dialect, "SUBPARTITION_NAME"), "ASC"),
            ],
        ),
    )


def build_report(table: str, rows: Sequence[Any]) -> MariaDBPartitionReport:
    """Turn ``information_schema.PARTITIONS`` rows into a partition tree.

    Args:
        table: Table name.
        rows: Mapping-like rows with the aliases used by
            :func:`_metadata_expression`.

    Returns:
        A report whose ``partitions`` are top-level entries first, each
        carrying its children, followed by the child entries themselves.
    """
    groups: Dict[str, List[Any]] = {}
    for row in rows:
        name = row["name"]
        groups.setdefault(name, []).append(row)

    infos: List[MariaDBPartitionInfo] = []
    for name, group in groups.items():
        subnames = [row["subname"] for row in group if row["subname"] is not None]
        method = group[0]["method"]
        description = group[0]["description"]

        def _sum(key: str, group: List[Any] = group) -> Optional[int]:
            values = [row[key] for row in group if row[key] is not None]
            return sum(int(value) for value in values) if values else None

        infos.append(
            PartitionInfo(
                name=name,
                level=1,
                method=method,
                bound=str(description) if description is not None else None,
                row_count=_sum("table_rows"),
                size_bytes=(
                    (_sum("data_length") or 0) + (_sum("index_length") or 0)
                    if any(
                        row["data_length"] is not None or row["index_length"] is not None
                        for row in group
                    )
                    else None
                ),
                is_partitioned=bool(subnames),
                extras={"children": tuple(subnames)},
            )
        )
        for row in group:
            if row["subname"] is None:
                continue
            infos.append(
                PartitionInfo(
                    name=row["subname"],
                    parent=name,
                    level=2,
                    method=row["submethod"],
                    row_count=(
                        int(row["table_rows"]) if row["table_rows"] is not None else None
                    ),
                    size_bytes=(
                        int(row["data_length"] or 0) + int(row["index_length"] or 0)
                        if row["data_length"] is not None
                        or row["index_length"] is not None
                        else None
                    ),
                )
            )
    return PartitionReport(target=table, partitions=tuple(infos))


class MariaDBPartitionMaintenance:
    """Run partition maintenance against one MariaDB backend.

    Args:
        backend: A connected synchronous MariaDB backend.

    Example:
        >>> maintenance = MariaDBPartitionMaintenance(backend)
        >>> report = maintenance.ensure(plan)
        >>> report = maintenance.drop_before(plan, cutoff, dry_run=True)
    """

    def __init__(self, backend: "MariaDBBackend"):
        self.backend = backend
        self.dialect = backend.dialect

    def list(
        self,
        table: str,
        *,
        plan: Optional[MariaDBPartitionPlan] = None,
    ) -> MariaDBPartitionReport:
        """Read the partition tree for ``table``.

        Args:
            table: Table name.
            plan: Optional plan used to mark missing definitions and existing
                partitions the plan does not name as ``orphans``.

        Returns:
            A report with the current partition tree.
        """
        if not table or not table.strip():
            raise ValueError("table must be a non-empty string")
        rows = self.backend.fetch_all(
            *_metadata_expression(self.dialect, table).to_sql()
        )
        report = build_report(table, rows)
        if plan is not None:
            known = {definition.name for definition in plan.definitions}
            orphans = [
                name for name in report.partition_names if name not in known
            ]
            missing = tuple(
                (table, definition.name)
                for definition in plan.definitions
                if definition.name not in report.partition_names
            )
            report = replace(
                report, orphans=tuple(orphans), missing=missing
            )
        return report

    def validate(
        self,
        plan: MariaDBPartitionPlan,
    ) -> MariaDBPartitionReport:
        """Compare the catalogue with ``plan`` without changing anything.

        Args:
            plan: Caller-owned plan.

        Returns:
            The catalogue snapshot plus ``missing``, ``orphans`` and ``issues``
            for method or boundary drift.
        """
        report = self.list(plan.table, plan=plan)
        return replace(report, issues=tuple(_catalogue_issues(plan, report)))

    def ensure(
        self,
        plan: MariaDBPartitionPlan,
        *,
        dry_run: bool = False,
    ) -> MariaDBPartitionReport:
        """Add the plan's missing partitions.

        A definition above the current maximum is appended with one
        ``ADD PARTITION`` statement.  A definition in a gap, or one that must
        sit before an existing ``MAXVALUE`` partition, reorganises the
        following partition with ``REORGANIZE PARTITION``.  Work the
        catalogue makes unsafe stays in ``skipped``.

        Args:
            plan: Caller-owned plan.
            dry_run: Report what would be added without executing DDL.

        Returns:
            The pre-action snapshot plus ``missing``, ``added`` and ``skipped``.
        """
        report = self.list(plan.table, plan=plan)
        known = {definition.name for definition in plan.definitions}
        additions, reorganizations, skipped = _plan_changes(plan, report)

        planned = {definition.name for definition in additions}
        for reorganization in reorganizations:
            planned.update(
                definition.name
                for definition in reorganization.into
                if definition.name != reorganization.partition
            )
        added = tuple(
            definition.name
            for definition in plan.definitions
            if definition.name in planned
        )

        if not dry_run:
            for reorganization in reorganizations:
                expression = MariaDBReorganizePartitionExpression(
                    self.dialect,
                    Table(self.dialect, plan.table),
                    reorganization.partition,
                    reorganization.into,
                )
                self.backend.execute(*expression.to_sql())
            if additions:
                expression = MariaDBAddPartitionExpression(
                    self.dialect,
                    Table(self.dialect, plan.table),
                    additions,
                )
                self.backend.execute(*expression.to_sql())

        return replace(
            report,
            missing=tuple(
                (plan.table, definition.name)
                for definition in plan.definitions
                if definition.name not in report.partition_names
            ),
            added=added,
            orphans=tuple(
                name for name in report.partition_names if name not in known
            ),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )

    def drop_before(
        self,
        plan: MariaDBPartitionPlan,
        cutoff: Any,
        *,
        dry_run: bool = True,
    ) -> MariaDBPartitionReport:
        """Drop the plan's partitions whose whole range is at or before ``cutoff``.

        Args:
            plan: Caller-owned RANGE plan.
            cutoff: Inclusive upper threshold for retention.  Values must be
                comparable with the plan's ``less_than`` values.
            dry_run: Default ``True``; set ``False`` to execute the DDL.

        Returns:
            The pre-action snapshot plus ``dropped`` and ``skipped``.
        """
        report = self.list(plan.table, plan=plan)
        dropped, skipped = select_drops(plan, report.partition_names, cutoff)

        if dropped and not dry_run:
            expression = MariaDBDropPartitionExpression(
                self.dialect,
                Table(self.dialect, plan.table),
                dropped,
            )
            self.backend.execute(*expression.to_sql())

        return replace(
            report,
            dropped=tuple(dropped),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )


class AsyncMariaDBPartitionMaintenance:
    """Asynchronously run partition maintenance against one MariaDB backend.

    The planning rules are shared with :class:`MariaDBPartitionMaintenance`;
    only the two backend calls are awaited.
    """

    def __init__(self, backend: "AsyncMariaDBBackend"):
        self.backend = backend
        self.dialect = backend.dialect

    async def list(
        self,
        table: str,
        *,
        plan: Optional[MariaDBPartitionPlan] = None,
    ) -> MariaDBPartitionReport:
        """Read the partition tree for ``table`` asynchronously."""
        if not table or not table.strip():
            raise ValueError("table must be a non-empty string")
        rows = await self.backend.fetch_all(
            *_metadata_expression(self.dialect, table).to_sql()
        )
        report = build_report(table, rows)
        if plan is not None:
            known = {definition.name for definition in plan.definitions}
            orphans = [
                name for name in report.partition_names if name not in known
            ]
            missing = tuple(
                (table, definition.name)
                for definition in plan.definitions
                if definition.name not in report.partition_names
            )
            report = replace(
                report, orphans=tuple(orphans), missing=missing
            )
        return report

    async def validate(
        self,
        plan: MariaDBPartitionPlan,
    ) -> MariaDBPartitionReport:
        """Compare the catalogue with ``plan`` asynchronously."""
        report = await self.list(plan.table, plan=plan)
        return replace(report, issues=tuple(_catalogue_issues(plan, report)))

    async def ensure(
        self,
        plan: MariaDBPartitionPlan,
        *,
        dry_run: bool = False,
    ) -> MariaDBPartitionReport:
        """Add the plan's missing partitions asynchronously."""
        report = await self.list(plan.table, plan=plan)
        known = {definition.name for definition in plan.definitions}
        additions, reorganizations, skipped = _plan_changes(plan, report)

        planned = {definition.name for definition in additions}
        for reorganization in reorganizations:
            planned.update(
                definition.name
                for definition in reorganization.into
                if definition.name != reorganization.partition
            )
        added = tuple(
            definition.name
            for definition in plan.definitions
            if definition.name in planned
        )

        if not dry_run:
            for reorganization in reorganizations:
                expression = MariaDBReorganizePartitionExpression(
                    self.dialect,
                    Table(self.dialect, plan.table),
                    reorganization.partition,
                    reorganization.into,
                )
                await self.backend.execute(*expression.to_sql())
            if additions:
                expression = MariaDBAddPartitionExpression(
                    self.dialect,
                    Table(self.dialect, plan.table),
                    additions,
                )
                await self.backend.execute(*expression.to_sql())

        return replace(
            report,
            missing=tuple(
                (plan.table, definition.name)
                for definition in plan.definitions
                if definition.name not in report.partition_names
            ),
            added=added,
            orphans=tuple(
                name for name in report.partition_names if name not in known
            ),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )

    async def drop_before(
        self,
        plan: MariaDBPartitionPlan,
        cutoff: Any,
        *,
        dry_run: bool = True,
    ) -> MariaDBPartitionReport:
        """Drop old partitions asynchronously; dry-run by default."""
        report = await self.list(plan.table, plan=plan)
        dropped, skipped = select_drops(plan, report.partition_names, cutoff)

        if dropped and not dry_run:
            expression = MariaDBDropPartitionExpression(
                self.dialect,
                Table(self.dialect, plan.table),
                dropped,
            )
            await self.backend.execute(*expression.to_sql())

        return replace(
            report,
            dropped=tuple(dropped),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )
