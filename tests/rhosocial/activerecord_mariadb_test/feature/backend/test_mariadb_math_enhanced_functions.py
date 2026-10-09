# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_math_enhanced_functions.py
"""
Tests for MariaDB-specific enhanced math functions.

These include additional mathematical functions beyond the basic math module.

Every operand is an expression: a ``Column`` for a column, a ``Literal`` for a
number.  The factories used to parse a bare string to decide which of the two
it was, so a column named ``3.7`` could not be read at all.
"""
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.functions.math_enhanced import (
    round_,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_,
    min_,
    avg,
)


class TestMySQLMathEnhancedFunctions:
    """Tests for MySQL enhanced math functions."""

    def test_round__default(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with default precision."""
        result = round_(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`value`" in sql

    def test_round__with_precision(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with precision."""
        result = round_(mariadb_dialect, Column(mariadb_dialect, "price"), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with literal value."""
        result = round_(mariadb_dialect, Literal(mariadb_dialect, 3.14159), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_pow(self, mariadb_dialect: MariaDBDialect):
        """Test pow() function."""
        result = pow(mariadb_dialect, Column(mariadb_dialect, "base"),
                     Literal(mariadb_dialect, 2))
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_pow_both_columns(self, mariadb_dialect: MariaDBDialect):
        """Test pow() with both column references."""
        result = pow(
            mariadb_dialect,
            Column(mariadb_dialect, "x"),
            Column(mariadb_dialect, "y")
        )
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_power(self, mariadb_dialect: MariaDBDialect):
        """Test power() function (alias for POW)."""
        result = power(mariadb_dialect, Literal(mariadb_dialect, 2),
                       Literal(mariadb_dialect, 3))
        sql, _ = result.to_sql()
        assert "POWER(" in sql

    def test_sqrt(self, mariadb_dialect: MariaDBDialect):
        """Test sqrt() function."""
        result = sqrt(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql
        assert "`value`" in sql

    def test_sqrt_with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test sqrt() with literal value."""
        result = sqrt(mariadb_dialect, Literal(mariadb_dialect, 16))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, mariadb_dialect: MariaDBDialect):
        """Test mod() function."""
        result = mod(mariadb_dialect, Column(mariadb_dialect, "total"),
                    Literal(mariadb_dialect, 10))
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_mod_both_columns(self, mariadb_dialect: MariaDBDialect):
        """Test mod() with both column references."""
        result = mod(
            mariadb_dialect,
            Column(mariadb_dialect, "dividend"),
            Column(mariadb_dialect, "divisor")
        )
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_ceil(self, mariadb_dialect: MariaDBDialect):
        """Test ceil() function."""
        result = ceil(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql
        assert "`value`" in sql

    def test_ceil_with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test ceil() with literal value."""
        result = ceil(mariadb_dialect, Literal(mariadb_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql

    def test_floor(self, mariadb_dialect: MariaDBDialect):
        """Test floor() function."""
        result = floor(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql
        assert "`value`" in sql

    def test_floor_with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test floor() with literal value."""
        result = floor(mariadb_dialect, Literal(mariadb_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql

    def test_trunc(self, mariadb_dialect: MariaDBDialect):
        """Test trunc() function (becomes TRUNCATE in MySQL)."""
        result = trunc(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql
        assert "`value`" in sql

    def test_trunc_with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test trunc() with literal value."""
        result = trunc(mariadb_dialect, Literal(mariadb_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_trunc_with_precision(self, mariadb_dialect: MariaDBDialect):
        """Test trunc() with precision."""
        result = trunc(mariadb_dialect, Literal(mariadb_dialect, 3.14159), 2)
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_max__two_args(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with two arguments (uses GREATEST)."""
        result = max_(mariadb_dialect, Column(mariadb_dialect, "a"), Column(mariadb_dialect, "b"))
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__multiple_args(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with multiple arguments (uses GREATEST)."""
        result = max_(
            mariadb_dialect,
            Column(mariadb_dialect, "a"),
            Column(mariadb_dialect, "b"),
            Column(mariadb_dialect, "c")
        )
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__with_literals(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with literal values (uses GREATEST)."""
        result = max_(mariadb_dialect, Literal(mariadb_dialect, 1),
                      Literal(mariadb_dialect, 2), Literal(mariadb_dialect, 3))
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__single_arg(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with single column argument (uses MAX aggregate)."""
        result = max_(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__two_args(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with two arguments (uses LEAST)."""
        result = min_(mariadb_dialect, Column(mariadb_dialect, "a"), Column(mariadb_dialect, "b"))
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__multiple_args(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with multiple arguments (uses LEAST)."""
        result = min_(
            mariadb_dialect,
            Column(mariadb_dialect, "a"),
            Column(mariadb_dialect, "b"),
            Column(mariadb_dialect, "c")
        )
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__with_literals(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with literal values (uses LEAST)."""
        result = min_(mariadb_dialect, Literal(mariadb_dialect, 1),
                      Literal(mariadb_dialect, 2), Literal(mariadb_dialect, 3))
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__single_arg(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with single column argument (uses MIN aggregate)."""
        result = min_(mariadb_dialect, Column(mariadb_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg(self, mariadb_dialect: MariaDBDialect):
        """Test avg() aggregate function."""
        result = avg(mariadb_dialect, Column(mariadb_dialect, "price"))
        sql, _ = result.to_sql()
        assert "AVG(" in sql
        assert "`price`" in sql

    def test_avg_with_literal(self, mariadb_dialect: MariaDBDialect):
        """Test avg() with literal value."""
        result = avg(mariadb_dialect, Literal(mariadb_dialect, 100))
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__with_integer(self, mariadb_dialect: MariaDBDialect):
        """The number 123 is a value, and is bound rather than parsed."""
        result = round_(mariadb_dialect, Literal(mariadb_dialect, 123), 2)
        sql, params = result.to_sql()
        assert "ROUND(%s, %s)" == sql
        assert params == (123, 2)

    def test_round__with_float(self, mariadb_dialect: MariaDBDialect):
        """The number 3.14159 is a value, and is bound rather than parsed."""
        result = round_(mariadb_dialect, Literal(mariadb_dialect, 3.14159), 2)
        sql, params = result.to_sql()
        assert "ROUND(%s, %s)" == sql
        assert params == (3.14159, 2)

    def test_round__with_column(self, mariadb_dialect: MariaDBDialect):
        """A column is a Column, however numeric its name looks."""
        result = round_(mariadb_dialect, Column(mariadb_dialect, "3.7"), 2)
        sql, _ = result.to_sql()
        assert "ROUND(`3.7`, %s)" == sql

    def test_pow_with_integer_exponent(self, mariadb_dialect: MariaDBDialect):
        """Test pow() with an integer exponent."""
        result = pow(mariadb_dialect, Column(mariadb_dialect, "base"),
                     Literal(mariadb_dialect, 2))
        sql, params = result.to_sql()
        assert "POW(`base`, %s)" == sql
        assert params == (2,)

    def test_sqrt_with_column_named_sixteen(self, mariadb_dialect: MariaDBDialect):
        """A column named "16" is reachable, because the caller says so.

        sqrt() used to parse "16" as the number sixteen, so this column
        could not be read at all: the query rounded the number instead.
        """
        result = sqrt(mariadb_dialect, Column(mariadb_dialect, "16"))
        sql, _ = result.to_sql()
        assert "SQRT(`16`)" == sql

    def test_mod_with_integer_divisor(self, mariadb_dialect: MariaDBDialect):
        """Test mod() with an integer divisor."""
        result = mod(mariadb_dialect, Column(mariadb_dialect, "total"),
                     Literal(mariadb_dialect, 10))
        sql, params = result.to_sql()
        assert "MOD(`total`, %s)" == sql
        assert params == (10,)

    def test_max__with_columns(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with three columns in GREATEST."""
        result = max_(mariadb_dialect, Column(mariadb_dialect, "a"),
                      Column(mariadb_dialect, "b"), Column(mariadb_dialect, "c"))
        sql, _ = result.to_sql()
        assert "GREATEST(`a`, `b`, `c`)" == sql

    def test_min__with_columns(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with three columns in LEAST."""
        result = min_(mariadb_dialect, Column(mariadb_dialect, "a"),
                      Column(mariadb_dialect, "b"), Column(mariadb_dialect, "c"))
        sql, _ = result.to_sql()
        assert "LEAST(`a`, `b`, `c`)" == sql

    def test_avg_with_number(self, mariadb_dialect: MariaDBDialect):
        """Test avg() with the number 100."""
        result = avg(mariadb_dialect, Literal(mariadb_dialect, 100))
        sql, params = result.to_sql()
        assert "AVG(%s)" == sql
        assert params == (100,)
