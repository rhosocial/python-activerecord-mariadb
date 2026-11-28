# tests/test_expression_registry_construct.py
"""MariaDB value handling at construct level -- no live database.

Values reach SQL as bind parameters by default; ``inline=True`` is the one
escape hatch, spelling the value as dialect-literal text with no parameters.
A raw value at a value position is coerced to a bound ``Parameter``.
"""
import pytest

from rhosocial.activerecord.backend.expression.core import Column, Parameter
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


@pytest.fixture
def dialect() -> MariaDBDialect:
    return MariaDBDialect(version=(11, 4, 0))


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
