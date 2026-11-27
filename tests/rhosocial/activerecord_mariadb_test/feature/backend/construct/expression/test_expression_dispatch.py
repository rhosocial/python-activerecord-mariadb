# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/expression/test_expression_dispatch.py
"""Every MariaDB expression renders through the one dispatch path.

An expression collects parameters; the dialect formats and validates. The two
meet in exactly one place: ``BaseExpression.to_sql()`` reads the class's
``format_method`` and calls that method on the dialect. A class that overrides
``to_sql`` -- or ``_render`` -- bypasses that lookup, so its capability/probe
alignment is no longer the dialect's to answer.

These tests state the consequence directly:

* no expression class in this backend overrides the rendering entry point;
* a class built with ``dialect=None`` renders through ``to_sql(dialect)``,
  which was impossible while the class rendered itself.
"""

import inspect

import pytest

from rhosocial.activerecord.backend.expression.objects import Function
from rhosocial.activerecord.backend.expression.query_sources import (
    JSONTableColumn as CoreJSONTableColumn,
    JSONTableExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_function import (
    CreateFunctionStatement,
    DropFunctionStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.admin import (
    FlushOption,
    MariaDBFlushStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.json_table import (
    JSONTableColumn as MariaDBJSONTableColumn,
    MariaDBJSONTableExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.routine import (
    MariaDBCreateFunctionStatement,
    MariaDBDropFunctionStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    MariaDBShowCreateTableStatement,
    MariaDBShowWarningsStatement,
)

from expression_roundtrip_harness import collect_expression_classes

MARIADB_EXPR_PKG = "rhosocial.activerecord.backend.impl.mariadb.expression"


def _dialect() -> MariaDBDialect:
    return MariaDBDialect((10, 6, 0))


def test_no_expression_class_overrides_the_rendering_entry_point():
    """Dispatch is declared, never re-implemented, anywhere in the package."""
    offenders = []
    for fqn, cls in collect_expression_classes(MARIADB_EXPR_PKG).items():
        for name in ("to_sql", "_render"):
            if name in vars(cls):
                offenders.append(f"{fqn}.{name}")
    assert not offenders, (
        "These expressions bypass BaseExpression's dispatch by overriding it: "
        f"{sorted(offenders)}. Delete the override and declare `format_method`."
    )


@pytest.mark.parametrize(
    "factory,format_method",
    [
        (
            lambda dialect: MariaDBFlushStatement(dialect, [FlushOption.TABLES]),
            "format_flush_statement",
        ),
        (
            lambda dialect: MariaDBShowCreateTableStatement(dialect, "app.users"),
            "format_show_create_table_statement",
        ),
        (lambda dialect: MariaDBShowWarningsStatement(dialect, limit=3), "format_show_warnings_statement"),
    ],
)
def test_an_unbound_node_renders_through_the_dialect_argument(factory, format_method):
    """``to_sql(dialect)`` renders a node built without one, identically.

    The bound form is the reference: it renders the same node through the
    dialect it was constructed with. The unbound form must produce the same
    SQL and params, and it must resolve the same formatter name -- both are
    only possible when the class declares ``format_method`` instead of
    rendering itself.
    """
    dialect = _dialect()
    bound = factory(dialect)
    unbound = factory(None)

    assert unbound.format_method == format_method
    assert hasattr(dialect, format_method), (
        f"{type(unbound).__name__} names {format_method}, which the dialect " f"does not provide"
    )
    assert unbound.to_sql(dialect) == bound.to_sql()


def test_an_unbound_node_still_refuses_to_render_without_a_dialect():
    """The argument is the only thing ``to_sql(dialect)`` adds; none means no render."""
    expr = MariaDBFlushStatement(None, [FlushOption.TABLES])

    with pytest.raises(ValueError) as caught:
        expr.to_sql()
    assert "no dialect bound" in str(caught.value)


#: Pairs of distinct expression kinds that a dialect must not tell apart.
#:
#: Each side is its own registry kind with its own constructor contract, so
#: one formatter would have to branch on ``isinstance(expr, ...)`` to know
#: which fields exist. The pairs are split into two formatters; the checks
#: below fail if a branch or a shared name comes back.
_SPLIT_FORMATTER_CASES = [
    pytest.param(
        lambda d: MariaDBPartitionMaxValue(d),
        "format_partition_max_value",
        lambda d: MariaDBPartitionValue(d, 7),
        "format_partition_value",
        id="partition-boundary-token-vs-value",
    ),
    pytest.param(
        lambda d: MariaDBJSONTableExpression(
            d,
            '{"a": 1}',
            "$",
            [MariaDBJSONTableColumn(name="c", type="INT", path="$.c")],
        ),
        "format_mariadb_json_table_expression",
        lambda d: JSONTableExpression(
            d,
            "doc",
            "$",
            [CoreJSONTableColumn(name="c", data_type="INT", path="$.c")],
        ),
        "format_json_table_expression",
        id="json-table-mariadb-vs-core",
    ),
    pytest.param(
        lambda d: MariaDBCreateFunctionStatement(d, Function(d, "f"), returns="INT"),
        "format_mariadb_create_function_statement",
        lambda d: CreateFunctionStatement(d, Function(d, "f"), returns="INT"),
        "format_create_function_statement",
        id="create-function-mariadb-vs-core",
    ),
    pytest.param(
        lambda d: MariaDBDropFunctionStatement(d, Function(d, "f")),
        "format_mariadb_drop_function_statement",
        lambda d: DropFunctionStatement(d, Function(d, "f")),
        "format_drop_function_statement",
        id="drop-function-mariadb-vs-core",
    ),
]


@pytest.mark.parametrize("factory_a,method_a,factory_b,method_b", _SPLIT_FORMATTER_CASES)
def test_distinct_kinds_render_through_their_own_formatter(
    factory_a, method_a, factory_b, method_b
):
    """A formatter renders one kind; it never asks which class it was handed.

    Both instances must render through different, declared formatters, and
    neither formatter's source may branch on the sibling class -- asserting
    only the SQL would stay green if the dispatch silently regressed to one
    shared method.
    """
    dialect = _dialect()
    first = factory_a(dialect)
    second = factory_b(dialect)

    assert first.format_method == method_a
    assert second.format_method == method_b
    assert method_a != method_b
    assert hasattr(dialect, method_a)
    assert hasattr(dialect, method_b)
    assert first.to_sql()[0] and second.to_sql()[0]

    for method, sibling in ((method_a, type(second)), (method_b, type(first))):
        source = inspect.getsource(getattr(MariaDBDialect, method))
        assert f"isinstance(expr, {sibling.__name__})" not in source, (
            f"{method} asks whether it was handed a {sibling.__name__}; "
            f"give that kind its own formatter instead"
        )
