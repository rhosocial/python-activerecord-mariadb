# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_system_versioning.py
"""MariaDB system-versioned table clause formatting tests.

This module covers the ``MariaDBSystemVersioningMixin``: version gating
(MariaDB 10.3+) and the pure SQL formatters for ``WITH SYSTEM VERSIONING``
and the ``FOR SYSTEM_TIME`` query clauses.
"""
from datetime import datetime

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.system_versioning import (
    MariaDBSystemVersioningMixin,
)

VERSION_SUPPORTED = (10, 3, 0)
VERSION_UNSUPPORTED = (10, 2, 0)


class _SystemVersioningHarness(MariaDBSystemVersioningMixin):
    """Minimal dialect harness exposing just the system-versioning mixin."""

    def __init__(self, version):
        """Store the version tuple used by capability gates."""
        self.version = version
        self.name = "TestSystemVersioning"

    def format_identifier(self, identifier):
        """Backtick-quote an identifier like the real dialect."""
        return f"`{identifier}`"


class _SqlExpressionStub:
    """Minimal expression stub exposing ``to_sql()`` for clause formatting."""

    def __init__(self, sql, params=()):
        """Store the SQL text and bind parameters to return from to_sql()."""
        self._sql = sql
        self._params = params

    def to_sql(self):
        """Return the stubbed (SQL, params) tuple."""
        return self._sql, self._params


class TestSystemVersioningCapabilities:
    """Tests for system-versioning capability gates."""

    @pytest.mark.parametrize("version,expected", [
        (VERSION_SUPPORTED, True),
        (VERSION_UNSUPPORTED, False),
    ])
    def test_supports_system_versioning(self, version, expected):
        """Test the version gate for system-versioned tables."""
        dialect = MariaDBDialect(version)
        assert dialect.supports_system_versioning() is expected, \
            "supports_system_versioning() must match the 10.3 boundary"

    @pytest.mark.parametrize("version,expected", [
        (VERSION_SUPPORTED, True),
        (VERSION_UNSUPPORTED, False),
    ])
    def test_supports_temporal_tables(self, version, expected):
        """Test the temporal-tables alias follows the same version gate."""
        dialect = _SystemVersioningHarness(version)
        assert dialect.supports_temporal_tables() is expected, \
            "supports_temporal_tables() must mirror supports_system_versioning()"


class TestSystemVersioningClause:
    """Tests for the WITH SYSTEM VERSIONING table clause."""

    def test_minimal(self):
        """Test the clause without table options."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_system_versioning_clause()
        assert sql == "WITH SYSTEM VERSIONING", "minimal clause must be exactly WITH SYSTEM VERSIONING"
        assert params == (), "clause has no bind parameters"

    def test_empty_options(self):
        """Test the clause with an empty options dict."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_system_versioning_clause({})
        assert sql == "WITH SYSTEM VERSIONING", "empty options must not add ON clauses"

    def test_on_delete(self):
        """Test the clause with versioning_on_delete only."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_system_versioning_clause(
            {"versioning_on_delete": "equal"}
        )
        assert "ON DELETE EQUAL" in sql, "ON DELETE EQUAL clause must be rendered"

    def test_on_update(self):
        """Test the clause with versioning_on_update only."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_system_versioning_clause(
            {"versioning_on_update": "before"}
        )
        assert "ON UPDATE BEFORE" in sql, "ON UPDATE BEFORE clause must be rendered"

    def test_on_delete_and_update(self):
        """Test the clause with both ON DELETE and ON UPDATE parts."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_system_versioning_clause(
            {"versioning_on_delete": "BEFORE", "versioning_on_update": "EQUAL"}
        )
        assert "ON DELETE BEFORE" in sql, "ON DELETE BEFORE clause must be rendered"
        assert "ON UPDATE EQUAL" in sql, "ON UPDATE EQUAL clause must be rendered"

    def test_unknown_option_key(self):
        """Test the clause with options that contain no versioning keys."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_system_versioning_clause({"engine": "InnoDB"})
        assert sql == "WITH SYSTEM VERSIONING", \
            "unrelated options must not add ON clauses"

    def test_unsupported_version(self):
        """Test the clause raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="System-Versioned Tables"):
            dialect.format_system_versioning_clause()


class TestForSystemTimeAsOf:
    """Tests for the FOR SYSTEM_TIME AS OF clause."""

    def test_string_timestamp(self):
        """Test AS OF with a plain timestamp string."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_as_of("2024-01-01 00:00:00")
        assert sql == "FOR SYSTEM_TIME AS OF '2024-01-01 00:00:00'", \
            "string timestamp must be single-quoted"
        assert params == (), "string timestamp produces no bind parameters"

    def test_datetime_timestamp(self):
        """Test AS OF with a datetime object."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_for_system_time_as_of(datetime(2024, 1, 1, 0, 0, 0))
        assert sql == "FOR SYSTEM_TIME AS OF '2024-01-01T00:00:00'", \
            "datetime must be rendered via isoformat()"

    def test_expression_timestamp(self):
        """Test AS OF with an expression exposing to_sql()."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        expr = _SqlExpressionStub("NOW()")
        sql, params = dialect.format_for_system_time_as_of(expr)
        assert sql == "FOR SYSTEM_TIME AS OF NOW()", "expression SQL must be inlined"
        assert params == (), "expression with no params keeps empty tuple"

    def test_expression_with_params(self):
        """Test AS OF with an expression that carries bind parameters."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        expr = _SqlExpressionStub("?", ("x",))
        sql, params = dialect.format_for_system_time_as_of(expr)
        assert sql == "FOR SYSTEM_TIME AS OF ?", "expression SQL must be inlined"
        assert params == ("x",), "expression params must be forwarded"

    def test_unsupported_version(self):
        """Test AS OF raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="AS OF"):
            dialect.format_for_system_time_as_of("2024-01-01")


class TestForSystemTimeBetween:
    """Tests for the FOR SYSTEM_TIME BETWEEN clause."""

    def test_strings(self):
        """Test BETWEEN with two plain timestamp strings."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_between("2024-01-01", "2024-02-01")
        assert sql == "FOR SYSTEM_TIME BETWEEN '2024-01-01' AND '2024-02-01'", \
            "both boundaries must be single-quoted"
        assert params == (), "plain strings produce no bind parameters"

    def test_datetimes(self):
        """Test BETWEEN with two datetime objects."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_for_system_time_between(
            datetime(2024, 1, 1), datetime(2024, 2, 1)
        )
        assert "2024-01-01T00:00:00" in sql, "start datetime must be isoformatted"
        assert "2024-02-01T00:00:00" in sql, "end datetime must be isoformatted"

    def test_expression_params(self):
        """Test BETWEEN with expressions that carry bind parameters."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_between(
            _SqlExpressionStub("?", ("start",)),
            _SqlExpressionStub("?", ("end",)),
        )
        assert sql == "FOR SYSTEM_TIME BETWEEN ? AND ?", "expression SQL must be inlined"
        assert params == ("start", "end"), "params from both expressions must be merged"

    def test_unsupported_version(self):
        """Test BETWEEN raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="BETWEEN"):
            dialect.format_for_system_time_between("2024-01-01", "2024-02-01")


class TestForSystemTimeFromTo:
    """Tests for the FOR SYSTEM_TIME FROM...TO clause."""

    def test_strings(self):
        """Test FROM...TO with two plain timestamp strings."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_from_to("2024-01-01", "2024-02-01")
        assert sql == "FOR SYSTEM_TIME FROM '2024-01-01' TO '2024-02-01'", \
            "both boundaries must be single-quoted"
        assert params == (), "plain strings produce no bind parameters"

    def test_expression_params(self):
        """Test FROM...TO with expressions that carry bind parameters."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_from_to(
            _SqlExpressionStub("?", ("s",)),
            _SqlExpressionStub("?", ("e",)),
        )
        assert sql == "FOR SYSTEM_TIME FROM ? TO ?", "expression SQL must be inlined"
        assert params == ("s", "e"), "params from both expressions must be merged"

    def test_datetimes(self):
        """Test FROM...TO with two datetime objects."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_for_system_time_from_to(
            datetime(2024, 1, 1), datetime(2024, 2, 1)
        )
        assert "2024-01-01T00:00:00" in sql, "start datetime must be isoformatted"
        assert "2024-02-01T00:00:00" in sql, "end datetime must be isoformatted"

    def test_unsupported_version(self):
        """Test FROM...TO raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="FROM"):
            dialect.format_for_system_time_from_to("2024-01-01", "2024-02-01")


class TestForSystemTimeAll:
    """Tests for the FOR SYSTEM_TIME ALL clause."""

    def test_supported(self):
        """Test ALL clause on a supported version."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_for_system_time_all()
        assert sql == "FOR SYSTEM_TIME ALL", "clause must be exactly FOR SYSTEM_TIME ALL"
        assert params == (), "clause has no bind parameters"

    def test_unsupported_version(self):
        """Test ALL clause raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="ALL"):
            dialect.format_for_system_time_all()


class TestWithoutSystemVersioning:
    """Tests for the WITHOUT SYSTEM VERSIONING clause."""

    def test_format(self):
        """Test WITHOUT SYSTEM VERSIONING formatting."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_without_system_versioning()
        assert sql == "WITHOUT SYSTEM VERSIONING", "clause must be exactly WITHOUT SYSTEM VERSIONING"
        assert params == (), "clause has no bind parameters"