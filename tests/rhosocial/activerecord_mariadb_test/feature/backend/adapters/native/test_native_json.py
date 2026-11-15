# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_json.py
"""``JSON`` on MariaDB is a ``LONGTEXT`` alias, not a native JSON type.

Consequences pinned here (testing plan §4.4):

* the column's ``information_schema`` data type is ``longtext``;
* the stored form is exactly the text the adapter wrote -- no second encoding,
  no server re-formatting -- so S2 is a plain text comparison;
* MariaDB's JSON functions see the value as JSON (``JSON_TYPE``/``JSON_EXTRACT``
  agree), which is the only sense in which the column is "JSON".
"""

import json

import pytest

from rhosocial.activerecord.backend.errors import IntegrityError
from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)

PAYLOAD = {
    "k": "v",
    "n": [1, 2, None],
    "nested": {"unicode": "\u6d4b\u8bd5", "flag": True},
}


def _column_data_type(model) -> str:
    row = model.backend().fetch_one(
        "SELECT DATA_TYPE, COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'native_json' "
        "AND COLUMN_NAME = 'payload'",
        (),
    )
    return row["DATA_TYPE"], row["COLUMN_TYPE"]


def test_json_is_a_longtext_alias(native_json):
    data_type, column_type = _column_data_type(native_json)
    assert data_type == "longtext", "MariaDB stores JSON as LONGTEXT"
    assert column_type == "longtext"


def test_json_roundtrip_and_text_stability(native_json):
    instance = native_json(payload=PAYLOAD)
    instance.save()

    found = native_json.find_one(instance.id)
    assert found.payload == PAYLOAD, "structure must round-trip"

    raw_before = read_raw(native_json, "CAST(payload AS CHAR)", instance.id)
    assert json.loads(raw_before) == PAYLOAD
    expected = json.dumps(PAYLOAD, ensure_ascii=False)
    assert raw_before == expected, "the stored text is exactly one json.dumps output"

    found.payload = PAYLOAD
    found.save()
    assert read_raw(native_json, "CAST(payload AS CHAR)", instance.id) == raw_before, (
        "a rewrite must not re-encode the document"
    )


def test_json_functions_see_the_document(native_json):
    instance = native_json(payload=PAYLOAD)
    instance.save()
    row = native_json.backend().fetch_one(
        "SELECT JSON_VALID(payload) AS valid, JSON_TYPE(payload) AS kind, "
        "JSON_EXTRACT(payload, '$.n[1]') AS second "
        f"FROM native_json WHERE id = {int(instance.id)}",
        (),
    )
    assert row["valid"] == 1
    assert row["kind"] == "OBJECT"
    assert row["second"] == "2"


def test_foreign_json_text_is_decoded_and_rewritten(native_json):
    insert_native(native_json, {"id": "9001", "payload": '\'{"k": "v", "n": [1, 2]}\''})

    foreign = native_json.find_one(9001)
    assert foreign.payload == {"k": "v", "n": [1, 2]}

    foreign.payload = {"k": "v", "n": [1, 2]}
    foreign.save()
    assert read_raw(native_json, "CAST(payload AS CHAR)", 9001) == '{"k": "v", "n": [1, 2]}'


def test_invalid_json_is_rejected_by_the_column_constraint(native_json):
    with pytest.raises(IntegrityError) as info:
        native_json.backend().execute(
            "INSERT INTO native_json (id, payload) VALUES (9002, 'not json')", ()
        )
    assert "4025" in str(info.value), "MariaDB enforces JSON validity with a CHECK constraint"


def test_null_json_stays_null(native_json):
    instance = native_json()
    instance.save()
    found = native_json.find_one(instance.id)
    assert found.payload is None
