# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_set.py
"""``SET('a','b','c')``: sorted text on the wire, ``set`` in Python.

MariaDB returns ``SET`` as the comma-separated display string; the adapter
sorts the members so the stored form is canonical regardless of set iteration
order. Ordering is part of the canonical form here, not a replay of the input.
"""

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError

from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)

#: The native tables this module uses.  ``schema`` creates only these, so
#: a server missing another family's type does not fail this module's setup.
TABLES = ("native_set",)


def test_set_roundtrip_is_sorted(native_set):
    value = {"c", "b"}
    instance = native_set(tags=value)
    instance.save()

    found = native_set.find_one(instance.id)
    assert found.tags == value, "SET members must round-trip as a set"

    raw_before = read_raw(native_set, "CAST(tags AS CHAR)", instance.id)
    assert raw_before == "b,c", "the stored form is the sorted member list"
    assert read_raw(native_set, "tags + 0", instance.id) == 6  # b=2, c=4

    found.tags = value
    found.save()
    assert read_raw(native_set, "CAST(tags AS CHAR)", instance.id) == raw_before, (
        "rewriting the same set must keep the canonical text"
    )


def test_empty_set_roundtrip(native_set):
    instance = native_set(tags=set())
    instance.save()

    found = native_set.find_one(instance.id)
    assert found.tags == set(), "an empty SET is the empty text, not NULL"
    assert read_raw(native_set, "CAST(tags AS CHAR)", instance.id) == ""


def test_foreign_set_text_is_decoded_and_rewritten(native_set):
    insert_native(native_set, {"id": "9001", "tags": "'a,c'"})

    foreign = native_set.find_one(9001)
    assert foreign.tags == {"a", "c"}

    foreign.tags = {"a", "c"}
    foreign.save()
    assert read_raw(native_set, "CAST(tags AS CHAR)", 9001) == "a,c"


def test_unknown_member_is_rejected_by_the_server(native_set):
    with pytest.raises(DatabaseError) as info:
        native_set.backend().execute(
            "INSERT INTO native_set (id, tags) VALUES (9002, 'z')", ()
        )
    assert "1265" in str(info.value), "a member outside the SET list is truncated/rejected"


def test_adapter_rejects_unknown_member_before_binding(native_set):
    from rhosocial.activerecord.backend.errors import ValidationError

    with pytest.raises(ValidationError) as info:
        native_set(tags={"z"}).save()
    assert "Invalid SET values" in str(info.value)


def test_null_set_stays_null(native_set):
    instance = native_set()
    instance.save()
    assert native_set.find_one(instance.id).tags is None
