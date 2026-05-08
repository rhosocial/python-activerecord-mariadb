# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_math_enhanced_functions.py
"""
Tests for MariaDB-specific enhanced math functions.

These include additional mathematical functions beyond the basic math module.
"""
from rhosocial.activerecord.backend.expression import Column
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
        result = round_(mariadb_dialect, 3.14159, 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_pow(self, mariadb_dialect: MariaDBDialect):
        """Test pow() function."""
        result = pow(mariadb_dialect, Column(mariadb_dialect, "base"), 2)
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
        result = power(mariadb_dialect, 2, 3)
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
        result = sqrt(mariadb_dialect, 16)
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, mariadb_dialect: MariaDBDialect):
        """Test mod() function."""
        result = mod(mariadb_dialect, Column(mariadb_dialect, "total"), 10)
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
        result = ceil(mariadb_dialect, 3.14)
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
        result = floor(mariadb_dialect, 3.14)
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
        result = trunc(mariadb_dialect, 3.14)
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_trunc_with_precision(self, mariadb_dialect: MariaDBDialect):
        """Test trunc() with precision."""
        result = trunc(mariadb_dialect, 3.14159, 2)
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
        result = max_(mariadb_dialect, 1, 2, 3)
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
        result = min_(mariadb_dialect, 1, 2, 3)
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
        result = avg(mariadb_dialect, 100)
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__with_string_integer(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with string integer value."""
        result = round_(mariadb_dialect, "123", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_float(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with string float value."""
        result = round_(mariadb_dialect, "3.14159", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_column_name(self, mariadb_dialect: MariaDBDialect):
        """Test round_() with non-numeric string treated as column."""
        result = round_(mariadb_dialect, "column_name", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`column_name`" in sql

    def test_pow_with_string_integer(self, mariadb_dialect: MariaDBDialect):
        """Test pow() with string integer exponent."""
        result = pow(mariadb_dialect, Column(mariadb_dialect, "base"), "2")
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_sqrt_with_string_integer(self, mariadb_dialect: MariaDBDialect):
        """Test sqrt() with string integer value."""
        result = sqrt(mariadb_dialect, "16")
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod_with_string_divisor(self, mariadb_dialect: MariaDBDialect):
        """Test mod() with string divisor."""
        result = mod(mariadb_dialect, Column(mariadb_dialect, "total"), "10")
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_max__with_string_literals(self, mariadb_dialect: MariaDBDialect):
        """Test max_() with non-numeric string values (treated as columns in GREATEST)."""
        result = max_(mariadb_dialect, "a", "b", "c")
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql
        # Non-numeric strings should be treated as column names and quoted with backticks
        assert "`a`" in sql

    def test_min__with_string_literals(self, mariadb_dialect: MariaDBDialect):
        """Test min_() with non-numeric string values (treated as columns in LEAST)."""
        result = min_(mariadb_dialect, "a", "b", "c")
        sql, _ = result.to_sql()
        assert "LEAST(" in sql
        # Non-numeric strings should be treated as column names and quoted with backticks
        assert "`a`" in sql

    def test_avg_with_string_literal(self, mariadb_dialect: MariaDBDialect):
        """Test avg() with string numeric value."""
        result = avg(mariadb_dialect, "100")
        sql, _ = result.to_sql()
        assert "AVG(" in sql
