# tests/test_expression_registry_construct.py
"""MariaDB publishes a frozen expression table: core's kinds plus its own.

Construct-level only -- no live database. The table is data: a backend's
registry must be core's mapping union its own, must not admit a sibling
backend's kinds, and must resolve a kind to exactly the class that owns it.
Values reach SQL as bind parameters by default; ``inline=True`` is the one
escape hatch, spelling the value as dialect-literal text with no parameters.
"""
import pytest

from rhosocial.activerecord.backend.expression.coerce import value_expression
from rhosocial.activerecord.backend.expression.core import Column, Parameter
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSIONS,
    RegistryError,
    RegistryReason,
    collect_expressions,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression_registry import (
    MARIADB_EXPRESSIONS,
    MARIADB_EXPRESSION_REGISTRY,
)


@pytest.fixture
def dialect() -> MariaDBDialect:
    return MariaDBDialect(version=(11, 4, 0))


def test_registry_is_frozen() -> None:
    assert MARIADB_EXPRESSION_REGISTRY.is_frozen is True
    with pytest.raises(RegistryError) as exc:
        MARIADB_EXPRESSION_REGISTRY.disable("parameter")
    assert exc.value.reason is RegistryReason.REGISTRY_FROZEN


def test_registry_kinds_are_core_union_mariadb() -> None:
    assert set(MARIADB_EXPRESSION_REGISTRY.node_kinds()) == (
        set(CORE_EXPRESSIONS) | set(MARIADB_EXPRESSIONS)
    )


def test_registry_has_no_sibling_backend_only_kind() -> None:
    sibling_only = set()
    for package in (
        "rhosocial.activerecord.backend.impl.dummy.expression",
        "rhosocial.activerecord.backend.impl.sqlite.expression",
    ):
        sibling_only |= set(collect_expressions(package))
    sibling_only -= set(CORE_EXPRESSIONS)
    sibling_only -= set(MARIADB_EXPRESSIONS)
    assert sibling_only, "expected at least one sibling-only kind to guard against"
    assert not (sibling_only & set(MARIADB_EXPRESSION_REGISTRY.node_kinds()))


def test_parameter_kind_resolves_to_core_class() -> None:
    assert MARIADB_EXPRESSION_REGISTRY.resolve_node("parameter") is Parameter


def test_mariadb_owned_kind_resolves_to_its_class() -> None:
    kind = "mariadb_analyze_partition_expression"
    assert kind in MARIADB_EXPRESSIONS
    assert kind not in CORE_EXPRESSIONS
    cls = MARIADB_EXPRESSION_REGISTRY.resolve_node(kind)
    assert cls.__module__.startswith(
        "rhosocial.activerecord.backend.impl.mariadb.expression"
    )


def test_parameter_binds_by_default(dialect: MariaDBDialect) -> None:
    sql, params = Parameter(dialect, "abc").to_sql()
    assert sql == "%s"
    assert params == ("abc",)


def test_parameter_inline_renders_backend_sql_text(dialect: MariaDBDialect) -> None:
    sql, params = Parameter(dialect, "x'y", inline=True).to_sql()
    assert sql == "'x''y'"  # MariaDB doubles the quote; no bind placeholder
    assert params == ()
    assert "%s" not in sql


def test_raw_value_at_value_position_is_bound_not_inlined(
    dialect: MariaDBDialect,
) -> None:
    predicate = ComparisonPredicate(dialect, "=", Column(dialect, "age"), 42)
    assert isinstance(predicate.right, Parameter)  # raw value coerced at value position
    sql, params = predicate.to_sql()
    assert "42" not in sql
    assert params == (42,)
