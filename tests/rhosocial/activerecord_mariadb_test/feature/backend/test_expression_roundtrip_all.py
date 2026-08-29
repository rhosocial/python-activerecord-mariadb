# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_expression_roundtrip_all.py
"""
Functional serialization coverage for MariaDB expression classes.

Every expression class defined in ``rhosocial.activerecord.backend.impl
.mariadb.expression`` must round-trip losslessly through dict / JSON / XML
encodings, and produce identical ``to_sql()`` where the MariaDB dialect
supports it.
"""

import pytest

from rhosocial.activerecord.testsuite.utils.expression import (
    collect_expression_classes,
    make_instance,
    register_all,
    register_special_constructor,
    roundtrip_expression,
    sql_consistent,
)

MARIADB_EXPR_PKG = "rhosocial.activerecord.backend.impl.mariadb.expression"

CLASSES = collect_expression_classes(MARIADB_EXPR_PKG)
register_all(CLASSES)


def _register_mariadb_specials():
    def match_against(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.match_against import (
            MariaDBMatchAgainstExpression,
        )
        return MariaDBMatchAgainstExpression(d, columns=["title"], search_string="x")

    def json_object(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
            MariaDBJSONObjectExpression,
        )
        return MariaDBJSONObjectExpression(d, {"a": 1})

    def json_array(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
            MariaDBJSONArrayExpression,
        )
        return MariaDBJSONArrayExpression(d, 1, 2, alias="arr")

    def json_extract(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
            MariaDBJSONExtractExpression,
        )
        return MariaDBJSONExtractExpression(d, "data", "$.a", alias="n")

    def json_contains(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
            MariaDBJSONContainsExpression,
        )
        return MariaDBJSONContainsExpression(d, "data", "x", "$.a")

    def st_distance(d):
        from rhosocial.activerecord.backend.impl.mariadb.expression.spatial import (
            MariaDBSTDistanceExpression,
        )
        return MariaDBSTDistanceExpression(d, "g1", "g2")

    register_special_constructor("match_against.MariaDBMatchAgainstExpression", match_against)
    register_special_constructor("json.MariaDBJSONObjectExpression", json_object)
    register_special_constructor("json.MariaDBJSONArrayExpression", json_array)
    register_special_constructor("json.MariaDBJSONExtractExpression", json_extract)
    register_special_constructor("json.MariaDBJSONContainsExpression", json_contains)
    register_special_constructor("spatial.MariaDBSTDistanceExpression", st_distance)


_register_mariadb_specials()


@pytest.fixture(params=[fqn for fqn in sorted(CLASSES)], ids=sorted(CLASSES))
def mariadb_expr_case(request, mariadb_dialect):
    fqn = request.param
    cls = CLASSES[fqn]
    instance, source = make_instance(cls, mariadb_dialect)
    if instance is None:
        pytest.skip(f"{fqn}: {source}")
    return fqn, instance


class TestMariaDBExpressionRoundtrip:
    """All constructible MariaDB expression classes round-trip losslessly."""

    def test_get_params_roundtrip(self, mariadb_expr_case, mariadb_dialect):
        fqn, instance = mariadb_expr_case
        roundtrip_expression(fqn, instance, mariadb_dialect)

    def test_to_sql_consistent(self, mariadb_expr_case, mariadb_dialect):
        fqn, instance = mariadb_expr_case
        sql_consistent(fqn, instance, mariadb_dialect)


def test_core_expressions_also_roundtrip(mariadb_dialect):
    from rhosocial.activerecord.backend.expression.core import Column, Literal
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

    expr = ComparisonPredicate(
        mariadb_dialect, "=", Column(mariadb_dialect, "a"), Literal(mariadb_dialect, 1)
    )
    roundtrip_expression("core", expr, mariadb_dialect)
    sql_consistent("core", expr, mariadb_dialect)