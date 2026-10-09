# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_dialect_function_support.py
"""
Test SQLFunctionSupport protocol implementation for MySQL dialect.

This module tests the supports_functions() method and version-dependent
function availability detection in MariaDBDialect.
"""
import pytest
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestMySQLFunctionSupportBasic:
    """Basic tests for MySQL function support detection."""

    def test_supports_functions_returns_dict(self):
        """Test that supports_functions returns a dictionary."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_supports_functions_all_values_are_bool(self):
        """Test that all values in the returned dict are booleans."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()
        for func_name, supported in result.items():
            assert isinstance(supported, bool), f"Value for {func_name} is not bool"

    def test_core_functions_always_supported(self):
        """Test that core functions are marked as supported."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()
        core_functions = ["count", "sum_", "avg", "min_", "max_", "coalesce", "nullif"]
        for func in core_functions:
            assert func in result, f"Core function {func} not in result"
            assert result[func] is True, f"Core function {func} should be supported"

    def test_sqlxml_constructors_are_not_plain_functions(self):
        """Test that standard SQL/XML constructors are not plain functions."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()
        sqlxml_constructors = [
            "xmlparse", "xmlserialize", "xmlelement", "xmlattributes",
            "xmlforest", "xmlconcat", "xmlcomment", "xmlpi", "xmlroot",
            "xmlagg", "xmlquery", "xmlexists", "xmltable",
        ]
        for func in sqlxml_constructors:
            assert func not in result


class TestMySQLFunctionSupportVersionDependent:
    """Tests for version-dependent function support."""

    def test_json_functions_require_mariadb_10_2_3(self):
        """Test that JSON functions require MariaDB 10.2.3+."""
        json_functions = ["json_extract", "json_unquote", "json_object", "json_array",
                         "json_contains", "json_set", "json_remove", "json_type",
                         "json_valid", "json_search"]

        dialect_old = MariaDBDialect(version=(10, 2, 2))
        result_old = dialect_old.supports_functions()
        for func in json_functions:
            assert result_old.get(func) is False

        dialect_new = MariaDBDialect(version=(10, 2, 3))
        result_new = dialect_new.supports_functions()
        for func in json_functions:
            assert result_new.get(func) is True

    def test_spatial_functions_require_mariadb_10_2_0(self):
        """Test that spatial functions require MariaDB 10.2.0+."""
        spatial_functions = ["st_geom_from_text", "st_geom_from_wkb", "st_as_text",
                            "st_distance", "st_within", "st_contains", "st_intersects"]

        dialect_old = MariaDBDialect(version=(10, 1, 99))
        result_old = dialect_old.supports_functions()
        for func in spatial_functions:
            assert result_old.get(func) is False

        dialect_new = MariaDBDialect(version=(10, 2, 0))
        result_new = dialect_new.supports_functions()
        for func in spatial_functions:
            assert result_new.get(func) is True

    def test_st_as_geojson_requires_mariadb_10_2_0(self):
        """Test that st_as_geojson requires MariaDB 10.2.0+."""
        dialect_old = MariaDBDialect(version=(10, 1, 99))
        result_old = dialect_old.supports_functions()
        assert result_old.get("st_as_geojson") is False

        dialect_new = MariaDBDialect(version=(10, 2, 0))
        result_new = dialect_new.supports_functions()
        assert result_new.get("st_as_geojson") is True

    def test_always_available_functions(self):
        """Functions available in every MariaDB version this backend targets.

        TRUNC is not on the list. It was, and running it against the scenario
        matrix showed it missing from 10.2 through 12.1 and present from 12.2 on,
        so the registry now gates it and this list follows. See
        TestMeasuredVersionGates for the measurement."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()

        always_available = [
            "match_against",
            "find_in_set", "elt", "field",
            "round_", "pow", "power", "sqrt", "mod", "ceil", "floor",
            "max_", "min_", "avg",
            "bit_and", "bit_or", "bit_xor", "bit_count",
        ]
        for func in always_available:
            assert result.get(func) is True, f"{func} should be always available"

    def test_trunc_is_not_always_available(self):
        """The other half of the correction: on 10.11 it is absent."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        assert dialect.supports_functions().get("trunc") is False

    def test_bit_shift_functions_always_supported(self):
        """Test that bit shift functions are supported in all MariaDB versions."""
        dialect = MariaDBDialect(version=(10, 0, 0))
        result = dialect.supports_functions()
        assert result.get("bit_shift_left") is True
        assert result.get("bit_shift_right") is True
        assert result.get("bit_get_bit") is True


class TestMySQLFunctionSupportPrivateMethod:
    """Tests for the private _is_mysql_function_supported method."""

    def test_unknown_function_returns_true(self):
        """Test that unknown functions return True (no restriction)."""
        dialect = MariaDBDialect()
        result = dialect._is_mariadb_function_supported("unknown_function_xyz")
        assert result is True

    def test_version_restricted_function_below_minimum(self):
        """Test that version-restricted function returns False below minimum."""
        dialect = MariaDBDialect(version=(10, 2, 2))
        result = dialect._is_mariadb_function_supported("json_extract")
        assert result is False

    def test_version_restricted_function_at_minimum(self):
        """Test that version-restricted function returns True at minimum."""
        dialect = MariaDBDialect(version=(10, 2, 3))
        result = dialect._is_mariadb_function_supported("json_extract")
        assert result is True

    def test_version_restricted_function_above_minimum(self):
        """Test that version-restricted function returns True above minimum."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect._is_mariadb_function_supported("json_extract")
        assert result is True


class TestMySQLFunctionSupportIntegration:
    """Integration tests for function support detection."""

    def test_function_dict_contains_both_core_and_backend_functions(self):
        """Test that the result contains both core and MariaDB-specific functions."""
        dialect = MariaDBDialect(version=(10, 11, 0))
        result = dialect.supports_functions()

        assert any(func in result for func in ["count", "sum_", "avg"])
        assert any(func in result for func in ["json_extract", "st_distance", "find_in_set"])

    def test_function_support_changes_with_version(self):
        """Test that function support changes across different versions."""
        old_dialect = MariaDBDialect(version=(10, 0, 0))
        new_dialect = MariaDBDialect(version=(10, 11, 0))

        old_result = old_dialect.supports_functions()
        new_result = new_dialect.supports_functions()

        assert old_result.get("json_extract") is False
        assert new_result.get("json_extract") is True

        assert old_result.get("st_geom_from_text") is False
        assert new_result.get("st_geom_from_text") is True


class TestMeasuredVersionGates:
    """Gates that came from asking servers rather than from docstrings.

    The registry marks most of these (None, None), meaning "every version this
    backend targets". That is a claim, and a claim about which versions have a
    function is cheap to check and easy to get wrong, so these boundaries were
    measured against the scenario matrix -- 10.2.44, 10.3.39, 10.4.34, 10.5.29,
    10.6.28, 10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2, 12.2.2,
    12.3.3, 13.0.2 and 13.1.1 -- by running the function on each.
    """

    def test_trunc_is_absent_before_12_2(self):
        """TRUNC does not exist below 12.2; it is not a synonym that older
        versions happen to accept."""
        for version in [(10, 2, 44), (10, 6, 28), (11, 4, 13), (11, 8, 9),
                        (12, 0, 2), (12, 1, 2)]:
            dialect = MariaDBDialect(version=version)
            assert dialect.supports_functions().get("trunc") is False, version

    def test_trunc_is_present_from_12_2(self):
        for version in [(12, 2, 2), (12, 3, 3), (13, 0, 2), (13, 1, 1)]:
            dialect = MariaDBDialect(version=version)
            assert dialect.supports_functions().get("trunc") is True, version

    @pytest.mark.parametrize(
        "name",
        ["round_", "pow", "power", "sqrt", "mod", "ceil", "floor",
         "max_", "min_", "avg",
         "bit_and", "bit_or", "bit_xor", "bit_count",
         "find_in_set", "elt", "field"],
    )
    @pytest.mark.parametrize("version", [(10, 2, 0), (11, 8, 0), (13, 1, 0)])
    def test_present_in_every_version_measured(self, name, version):
        """These were run on all fifteen servers and answered everywhere.

        bit_count is here because it is the one most likely to be wrong: the
        bit functions arrived in 10.0, which is below the oldest version this
        backend supports, so the floor and the target range do not overlap and
        the gate can stay open.
        """
        dialect = MariaDBDialect(version=version)
        assert dialect.supports_functions().get(name) is True, (name, version)
