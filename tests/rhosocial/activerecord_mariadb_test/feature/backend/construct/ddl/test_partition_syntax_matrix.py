# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/ddl/test_partition_syntax_matrix.py
"""Offline fixture-driven matrix for MariaDB partition syntax.

Every test here is driven by ``CASES`` from ``partition_syntax_fixtures``.
No server is required: rendering and refusal are observable through the
expression layer.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
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


def test_every_required_family_has_one_case():
    """The matrix remains complete even if the case table is edited."""
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))
    assert REQUIRED_CASE_NAMES <= set(names)
    for case in CASES:
        assert case.name and case.description
        assert case.builders or case.refusal_builder


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
        assert (
            position > previous_end
        ), f"{case.name} has fragment {fragment!r} out of order in {sql!r}"
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
