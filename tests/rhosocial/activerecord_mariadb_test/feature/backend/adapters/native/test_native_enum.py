# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_enum.py
"""``ENUM``: the database label is the member's ``.value``, never ``.name``.

The fixture enum deliberately uses names (``LOW``/``HIGH``) that differ from
their values (``p1``/``p2``), so a stored ``p1`` proves which one is written.
"""

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)
from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.native_models import (
    Priority,
)

#: The native tables this module uses.  ``schema`` creates only these, so
#: a server missing another family's type does not fail this module's setup.
TABLES = ("native_enum",)


def test_enum_roundtrips_by_value(native_enum):
    value = Priority.HIGH
    instance = native_enum(color=value)
    instance.save()

    found = native_enum.find_one(instance.id)
    assert found.color is Priority.HIGH, "the enum member must round-trip"

    raw_before = read_raw(native_enum, "CAST(color AS CHAR)", instance.id)
    assert raw_before == "p2", "the stored label is the enum's value"
    assert raw_before != value.name, "the member name must never be stored"

    found.color = value
    found.save()
    assert read_raw(native_enum, "CAST(color AS CHAR)", instance.id) == raw_before


def test_foreign_enum_label_is_decoded_and_rewritten(native_enum):
    insert_native(native_enum, {"id": "9001", "color": "'p1'"})

    foreign = native_enum.find_one(9001)
    assert foreign.color is Priority.LOW

    foreign.color = Priority.LOW
    foreign.save()
    assert read_raw(native_enum, "CAST(color AS CHAR)", 9001) == "p1"


def test_unknown_enum_label_is_rejected_by_the_server(native_enum):
    with pytest.raises(DatabaseError) as info:
        native_enum.backend().execute(
            "INSERT INTO native_enum (id, color) VALUES (9002, 'purple')", ()
        )
    assert "1265" in str(info.value), "a label outside the ENUM list is rejected"


def test_null_enum_stays_null(native_enum):
    instance = native_enum()
    instance.save()
    assert native_enum.find_one(instance.id).color is None
