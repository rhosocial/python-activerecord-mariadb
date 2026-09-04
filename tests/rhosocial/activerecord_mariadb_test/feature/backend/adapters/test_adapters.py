# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/test_adapters.py
"""Offline adapter round-trip coverage for the MariaDB backend."""
import datetime
import uuid
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.impl.mariadb.adapters import (
    MariaDBBlobAdapter,
    MariaDBBooleanAdapter,
    MariaDBDateAdapter,
    MariaDBDatetimeAdapter,
    MariaDBDecimalAdapter,
    MariaDBJSONAdapter,
    MariaDBTimeAdapter,
    MariaDBUUIDAdapter,
)


@pytest.fixture
def blob(): return MariaDBBlobAdapter()
@pytest.fixture
def json_a(): return MariaDBJSONAdapter()
@pytest.fixture
def uuid_a(): return MariaDBUUIDAdapter()
@pytest.fixture
def bool_a(): return MariaDBBooleanAdapter()
@pytest.fixture
def dec_a(): return MariaDBDecimalAdapter()
@pytest.fixture
def date_a(): return MariaDBDateAdapter()
@pytest.fixture
def time_a(): return MariaDBTimeAdapter()
@pytest.fixture
def dt_a(): return MariaDBDatetimeAdapter()


class TestBlob:
    def test_roundtrip(self, blob):
        assert blob.to_database(b"data", bytes) == b"data"
        assert blob.from_database(b"data", bytes) == b"data"
    def test_none(self, blob):
        assert blob.to_database(None, bytes) is None

class TestJSON:
    def test_roundtrip(self, json_a):
        val = {"a": 1, "b": [2, 3]}
        s = json_a.to_database(val, str)
        assert isinstance(s, str)
        assert json_a.from_database(s, dict) == val

class TestUUID:
    def test_roundtrip(self, uuid_a):
        u = uuid.uuid4()
        assert uuid_a.to_database(u, str) == str(u)
        assert uuid_a.from_database(str(u), uuid.UUID) == u

class TestBoolean:
    def test_true(self, bool_a):
        assert bool_a.to_database(True, int) == 1
        assert bool_a.from_database(1, bool) is True

class TestDecimal:
    def test_roundtrip(self, dec_a):
        d = Decimal("123.45")
        assert dec_a.from_database(d, Decimal) == d

class TestDate:
    def test_roundtrip(self, date_a):
        d = datetime.date(2026, 8, 26)
        assert date_a.to_database(d, datetime.date) == "2026-08-26"
        assert date_a.from_database(d, datetime.date) == d

class TestTime:
    def test_roundtrip(self, time_a):
        t = datetime.time(14, 30, 0)
        s = time_a.to_database(t, str)
        assert isinstance(s, str)
        assert time_a.from_database(s, datetime.time) == t

class TestDatetime:
    def test_formats_string(self, dt_a):
        dt = datetime.datetime(2026, 8, 26, 14, 30, 0)
        assert dt_a.to_database(dt, str) == "2026-08-26 14:30:00.000000"
    def test_roundtrip(self, dt_a):
        dt = datetime.datetime(2026, 8, 26, 14, 30, 0)
        s = dt_a.to_database(dt, str)
        result = dt_a.from_database(s, datetime.datetime)
        # from_database returns a UTC-aware datetime.
        assert result.replace(tzinfo=None) == dt
    def test_none(self, dt_a):
        assert dt_a.to_database(None, str) is None
