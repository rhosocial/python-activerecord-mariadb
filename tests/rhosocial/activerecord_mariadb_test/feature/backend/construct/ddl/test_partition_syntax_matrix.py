# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/ddl/test_partition_syntax_matrix.py
"""Offline fixture-driven matrix for MariaDB partition syntax.

Every test here is driven by ``CASES`` from ``partition_syntax_fixtures``.
No server is required: rendering, plan validation, refusal, and maintenance
planning are all observable through the expression and planner layers.  A
fake backend supplies partition rows and records the DDL that ``ensure`` and
``drop_before`` would send.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBPartitionMaxValue,
)
from rhosocial.activerecord.backend.impl.mariadb.partition_maintenance import (
    MariaDBPartitionMaintenance,
    plan_additions,
)
from partition_syntax_fixtures import CASES, partition_syntax_case

# The fixture is looked up by pytest through the test parameter name; the
# assignment keeps it referenced for linters that do not model fixtures.
_ = partition_syntax_case

REQUIRED_CASE_NAMES = frozenset(
    {
        "range",
        "range_columns",
        "list",
        "list_columns",
        "hash",
        "key",
        "linear_hash",
        "linear_key",
        "range_maxvalue",
        "hash_subpartition",
        "key_subpartition",
        "range_subpartition_refused",
        "list_subpartition_refused",
        "partition_options",
        "lifecycle_add_drop",
        "lifecycle_truncate",
        "lifecycle_reorganize",
        "lifecycle_remove",
        "lifecycle_coalesce",
        "lifecycle_analyze_check_optimize_rebuild_repair",
        "lifecycle_get_partitions",
        "maintenance_ensure_list_drop_before",
    }
)


@pytest.fixture
def dialect() -> MariaDBDialect:
    """The dialect every offline case renders with."""
    return MariaDBDialect(version=(10, 6, 0))


def _render_builder(builder, dialect):
    """Render one builder into a list of expressions."""
    built = builder(dialect)
    if isinstance(built, BaseExpression):
        return [built]
    return list(built)


def _render_case(case, dialect):
    """Render all expressions of a case into one joined SQL string."""
    expressions = []
    for builder in case.builders:
        expressions.extend(_render_builder(builder, dialect))
    sql_parts = []
    params = []
    for expression in expressions:
        sql, expression_params = expression.to_sql()
        sql_parts.append(sql)
        params.append(expression_params)
    return expressions, "\n".join(sql_parts), params


class FakeBackend:
    """Minimal backend surface used by MariaDBPartitionMaintenance."""

    def __init__(self, rows):
        self.dialect = MariaDBDialect(version=(10, 6, 0))
        self._rows = rows
        self.executed = []

    def fetch_all(self, sql, params=None):
        return list(self._rows)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))


def _rows_for(definitions):
    """Build information_schema.PARTITIONS-shaped rows for RANGE definitions."""
    rows = []
    for definition in definitions:
        bound = definition.less_than[0] if definition.less_than else None
        description = getattr(bound, "value", None)
        rows.append(
            {
                "name": definition.name,
                "subname": None,
                "method": "RANGE",
                "submethod": None,
                "description": description,
                "table_rows": 1,
                "data_length": 2,
                "index_length": 3,
            }
        )
    return rows


def test_every_required_family_has_one_case():
    """The matrix remains complete even if the case table is edited."""
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))
    assert REQUIRED_CASE_NAMES <= set(names)
    for case in CASES:
        assert case.name and case.description
        assert case.builders or case.refusal_builder or case.plan_builder


def test_renders_required_and_forbidden_fragments(partition_syntax_case, dialect):
    """Each rendering contains its required fragments and leaks no forbidden one."""
    case = partition_syntax_case
    if not case.builders:
        pytest.skip("case has no rendering builders")
    expressions, sql, params = _render_case(case, dialect)
    assert expressions
    for fragment in case.required_fragments:
        assert fragment in sql, f"{case.name} missing fragment {fragment!r} in {sql!r}"
    for fragment in case.forbidden_fragments:
        assert fragment not in sql, f"{case.name} leaked fragment {fragment!r} in {sql!r}"
    previous_end = -1
    for fragment in case.ordered_fragments:
        position = sql.find(fragment, previous_end + 1)
        assert position > previous_end, (
            f"{case.name} has fragment {fragment!r} out of order in {sql!r}"
        )
        previous_end = position + len(fragment)
    if case.expected_params is not None:
        for expression_params in params:
            assert expression_params == case.expected_params


def test_refused_syntax_raises_unsupported_feature(partition_syntax_case, dialect):
    """Refused subpartition strategies raise UnsupportedFeatureError by name."""
    case = partition_syntax_case
    if case.refusal_builder is None:
        pytest.skip("case is not a refusal case")
    with pytest.raises(UnsupportedFeatureError) as caught:
        case.refusal_builder(dialect)
    assert case.refused_feature in (caught.value.feature_name or "")


def test_plan_is_validated(partition_syntax_case, dialect):
    """A valid plan is accepted; an invalid plan is refused with its reason."""
    case = partition_syntax_case
    if case.plan_builder is None:
        pytest.skip("case has no partition plan")
    plan = case.plan_builder(dialect)
    assert plan.table == "events"
    names = [definition.name for definition in plan.definitions]
    assert names
    assert len(names) == len(set(names))
    maxvalue_positions = [
        index
        for index, definition in enumerate(plan.definitions)
        if definition.less_than
        and isinstance(definition.less_than[0], MariaDBPartitionMaxValue)
    ]
    if maxvalue_positions:
        assert maxvalue_positions == [len(plan.definitions) - 1]
    if case.invalid_plan_builder is not None:
        with pytest.raises(ValueError, match=case.invalid_plan_error):
            case.invalid_plan_builder(dialect)


def test_plan_additions_matches_expected(partition_syntax_case, dialect):
    """plan_additions returns the declared additions and skips the rest."""
    case = partition_syntax_case
    if case.plan_builder is None:
        pytest.skip("case has no partition plan")
    plan = case.plan_builder(dialect)
    additions, skipped = plan_additions(plan, case.existing_partitions)
    assert tuple(definition.name for definition in additions) == case.expected_additions
    assert tuple(name for name, _ in skipped) == case.expected_skipped


def test_maintenance_ensure_list_drop_before(partition_syntax_case, dialect):
    """ensure/list/drop_before plan and execute against a fake backend."""
    case = partition_syntax_case
    if not case.exercise_maintenance:
        pytest.skip("case does not exercise maintenance")
    plan = case.plan_builder(dialect)

    existing_definitions = [
        definition
        for definition in plan.definitions
        if definition.name in case.existing_partitions
    ]
    backend = FakeBackend(_rows_for(existing_definitions))
    maintenance = MariaDBPartitionMaintenance(backend)

    ensured = maintenance.ensure(plan)
    assert ensured.added == case.expected_additions
    assert ensured.skipped == ()
    assert ensured.dry_run is False
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` ADD PARTITION")
    assert params == ()

    all_rows = _rows_for(plan.definitions)
    list_backend = FakeBackend(all_rows)
    listed = MariaDBPartitionMaintenance(list_backend).list("events", plan=plan)
    assert listed.partition_names == tuple(
        definition.name for definition in plan.definitions
    )
    assert listed.orphans == ()
    assert list_backend.executed == []

    dry_backend = FakeBackend(all_rows)
    dry = MariaDBPartitionMaintenance(dry_backend).drop_before(plan, case.drop_cutoff)
    assert dry.dropped == case.expected_dropped
    assert dry.dry_run is True
    assert dry_backend.executed == []

    execute_backend = FakeBackend(all_rows)
    executed = MariaDBPartitionMaintenance(execute_backend).drop_before(
        plan, case.drop_cutoff, dry_run=False
    )
    assert executed.dropped == case.expected_dropped
    assert executed.dry_run is False
    assert len(execute_backend.executed) == 1
    sql, params = execute_backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` DROP PARTITION")
    assert params == ()


def test_live_setup_and_check_are_opt_in(partition_syntax_case):
    """A case runs live setup/check only when a scenario supplies both hooks."""
    case = partition_syntax_case
    if case.live_setup is None:
        pytest.skip("no live MariaDB scenario configured for this case")
    live_object = case.live_setup(None)
    if case.live_check is not None:
        case.live_check(live_object)
