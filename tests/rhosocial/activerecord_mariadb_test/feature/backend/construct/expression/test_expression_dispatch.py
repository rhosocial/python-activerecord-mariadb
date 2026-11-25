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

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.admin import (
    FlushOption,
    MariaDBFlushStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    ShowCreateTableStatement,
    ShowWarningsStatement,
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
            lambda dialect: ShowCreateTableStatement(dialect, "app.users"),
            "format_show_create_table_statement",
        ),
        (lambda dialect: ShowWarningsStatement(dialect, limit=3), "format_show_warnings_statement"),
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
