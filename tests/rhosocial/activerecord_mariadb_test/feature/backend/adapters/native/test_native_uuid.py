# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_uuid.py
"""``UUID`` (native, 10.7+) and the ``CHAR(36)`` carrier.

MariaDB's ``UUID`` column is a 16-byte type whose client-visible form is the
canonical lowercase hyphenated text. The adapter can bind text (what a
``CHAR(36)`` carrier needs) or the 16 raw bytes (what the native column
accepts); in both cases the driver hands back text on read.
"""

from uuid import UUID

from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)

#: The native tables this module uses.  ``schema`` creates only these, so
#: a server missing another family's type does not fail this module's setup.
TABLES = ("native_uuid",)

UUID_TEXT = "123e4567-e89b-12d3-a456-426614174000"
UUID_OBJ = UUID(UUID_TEXT)

COLUMN_DATA_TYPES = (
    ("uid_native", "uuid"),
    ("uid_carrier", "char"),
    ("uid_bytes", "uuid"),
)


def _column_metadata(model):
    """Type, plus the character length where the catalogue records one."""
    rows = model.backend().fetch_all(
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH AS COLUMN_LENGTH "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'native_uuid' "
        "AND COLUMN_NAME IN ('uid_native','uid_carrier','uid_bytes')",
        (),
    )
    return {
        row["COLUMN_NAME"]: (row["DATA_TYPE"], row["COLUMN_LENGTH"]) for row in rows
    }


def test_native_and_carrier_columns_have_their_types(native_uuid):
    metadata = _column_metadata(native_uuid)
    for column, data_type in COLUMN_DATA_TYPES:
        assert metadata[column][0] == data_type
    assert metadata["uid_carrier"][1] == 36
    # The UUID width belongs to the type, not to the column: MariaDB records no
    # length for it (measured on 11.8 -- CHARACTER_MAXIMUM_LENGTH and
    # CHARACTER_OCTET_LENGTH are both NULL for a ``uuid`` column), so the
    # catalogue cannot be asked for the 16 bytes.
    assert metadata["uid_native"][1] is None


def test_uuid_text_target_roundtrips_both_columns(native_uuid):
    instance = native_uuid(uid_native=UUID_OBJ, uid_carrier=UUID_OBJ)
    instance.save()

    found = native_uuid.find_one(instance.id)
    assert found.uid_native == UUID_OBJ
    assert found.uid_carrier == UUID_OBJ

    raw_native = read_raw(native_uuid, "CAST(uid_native AS CHAR)", instance.id)
    raw_carrier = read_raw(native_uuid, "CAST(uid_carrier AS CHAR)", instance.id)
    assert raw_native == UUID_TEXT
    assert raw_carrier == UUID_TEXT

    found.uid_native = UUID_OBJ
    found.uid_carrier = UUID_OBJ
    found.save()
    assert read_raw(native_uuid, "CAST(uid_native AS CHAR)", instance.id) == UUID_TEXT
    assert read_raw(native_uuid, "CAST(uid_carrier AS CHAR)", instance.id) == UUID_TEXT


def test_uuid_bytes_target_binds_sixteen_bytes(native_uuid):
    instance = native_uuid(uid_bytes=UUID_OBJ)
    instance.save()

    found = native_uuid.find_one(instance.id)
    assert found.uid_bytes == UUID_OBJ

    # The driver returns text for a UUID column regardless of how it was bound.
    raw_text = read_raw(native_uuid, "CAST(uid_bytes AS CHAR)", instance.id)
    assert raw_text == UUID_TEXT
    assert read_raw(native_uuid, "HEX(uid_bytes)", instance.id) == UUID_TEXT.replace("-", "").upper()

    found.uid_bytes = UUID_OBJ
    found.save()
    assert read_raw(native_uuid, "CAST(uid_bytes AS CHAR)", instance.id) == UUID_TEXT


def test_foreign_uuid_text_is_decoded_and_rewritten(native_uuid):
    insert_native(
        native_uuid,
        {
            "id": "9001",
            "uid_native": f"'{UUID_TEXT}'",
            "uid_carrier": f"'{UUID_TEXT}'",
            "uid_bytes": f"'{UUID_TEXT}'",
        },
    )

    foreign = native_uuid.find_one(9001)
    assert foreign.uid_native == UUID_OBJ
    assert foreign.uid_carrier == UUID_OBJ
    assert foreign.uid_bytes == UUID_OBJ

    foreign.uid_native = UUID_OBJ
    foreign.uid_carrier = UUID_OBJ
    foreign.uid_bytes = UUID_OBJ
    foreign.save()
    assert read_raw(native_uuid, "CAST(uid_native AS CHAR)", 9001) == UUID_TEXT
    assert read_raw(native_uuid, "CAST(uid_carrier AS CHAR)", 9001) == UUID_TEXT
    assert read_raw(native_uuid, "CAST(uid_bytes AS CHAR)", 9001) == UUID_TEXT


def test_null_uuid_columns_stay_null(native_uuid):
    instance = native_uuid()
    instance.save()
    found = native_uuid.find_one(instance.id)
    assert found.uid_native is None
    assert found.uid_carrier is None
    assert found.uid_bytes is None
