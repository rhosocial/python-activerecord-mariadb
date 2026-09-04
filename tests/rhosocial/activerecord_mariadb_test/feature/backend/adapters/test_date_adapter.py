# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/test_date_adapter.py
"""Regression tests for MariaDBDateAdapter.

Locks the correct isinstance ordering in from_database (datetime is a
subclass of date) so the sqlserver S3-style dead-branch bug cannot regress
here. Also covers to_database round-trip and None semantics.
"""
import datetime

import pytest

from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBDateAdapter


@pytest.fixture
def adapter():
    return MariaDBDateAdapter()


class TestToDatabase:
    def test_date_to_isoformat(self, adapter):
        d = datetime.date(2026, 8, 26)
        assert adapter.to_database(d, datetime.date) == "2026-08-26"

    def test_none_passthrough(self, adapter):
        assert adapter.to_database(None, datetime.date) is None


class TestFromDatabase:
    def test_date_object_returned_as_is(self, adapter):
        d = datetime.date(2026, 8, 26)
        result = adapter.from_database(d, datetime.date)
        assert result == d
        assert isinstance(result, datetime.date)

    def test_datetime_object_not_truncated(self, adapter):
        """datetime (subclass of date) must not be .date()-truncated — the
        sqlserver S3 regression would have done so."""
        dt = datetime.datetime(2026, 8, 26, 14, 30, 0)
        result = adapter.from_database(dt, datetime.date)
        assert result == dt
        assert isinstance(result, datetime.datetime)

    def test_string_parsed_to_date(self, adapter):
        result = adapter.from_database("2026-08-26", datetime.date)
        assert result == datetime.date(2026, 8, 26)
        assert isinstance(result, datetime.date)

    def test_none_returns_none(self, adapter):
        assert adapter.from_database(None, datetime.date) is None


class TestSupportedTypes:
    def test_registered_for_date(self, adapter):
        assert datetime.date in adapter.supported_types
