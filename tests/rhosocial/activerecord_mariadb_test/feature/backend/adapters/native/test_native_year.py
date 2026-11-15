# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_year.py
"""``YEAR``: a four-digit integer, deliberately not interpreted as a date.

The column type is pinned through ``information_schema``; the value is read
as ``int`` on both the adapter and the raw driver path.
"""

import datetime

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)


def _column_type(model) -> str:
    row = model.backend().fetch_one(
        "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'native_year' "
        "AND COLUMN_NAME = 'yr'",
        (),
    )
    return row["COLUMN_TYPE"]


def test_year_roundtrips_as_integer(native_year):
    instance = native_year(yr=2024)
    instance.save()

    found = native_year.find_one(instance.id)
    assert found.yr == 2024
    assert type(found.yr) is int, "YEAR is never turned into a date"

    raw_before = read_raw(native_year, "CAST(yr AS CHAR)", instance.id)
    assert raw_before == "2024"
    assert read_raw(native_year, "yr + 0", instance.id) == 2024
    assert type(read_raw(native_year, "yr", instance.id)) is int

    assert _column_type(native_year) == "year(4)"

    found.yr = 2024
    found.save()
    assert read_raw(native_year, "CAST(yr AS CHAR)", instance.id) == raw_before


def test_foreign_year_is_decoded_and_rewritten(native_year):
    insert_native(native_year, {"id": "9001", "yr": "1999"})

    foreign = native_year.find_one(9001)
    assert foreign.yr == 1999

    foreign.yr = 1999
    foreign.save()
    assert read_raw(native_year, "CAST(yr AS CHAR)", 9001) == "1999"


@pytest.mark.parametrize("value", [1901, 2155])
def test_year_boundaries_roundtrip(native_year, value):
    instance = native_year(yr=value)
    instance.save()
    assert native_year.find_one(instance.id).yr == value


def test_out_of_range_year_is_rejected_by_the_server(native_year):
    instance = native_year(yr=1800)
    with pytest.raises(DatabaseError) as info:
        instance.save()
    assert "1264" in str(info.value), "1800 is outside YEAR's 1901-2155 range"


def test_null_year_stays_null(native_year):
    instance = native_year()
    instance.save()
    found = native_year.find_one(instance.id)
    assert found.yr is None
    assert not isinstance(found.yr, datetime.date)
