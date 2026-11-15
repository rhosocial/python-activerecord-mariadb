# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_bit.py
"""``BIT(n)``: byte-aligned, non-aligned, and rejected widths.

MariaDB returns ``BIT`` values as ``bytes`` (big-endian, no length metadata),
so the adapter's declared width is what restores the leading zeros. Each
case asserts the three consistency forms of the testing plan (§3.4):

* S1 -- the model round-trip keeps both ``data`` and ``bit_length``;
* S2 -- the stored ``HEX`` form does not change on a rewrite;
* S3 -- a bit-string written by native SQL (``b'10101'``) is decoded and
  rewritten in the same canonical form.

The original column value is read with ``HEX(col)`` / ``col + 0``, never
through the adapter.
"""

import pytest

from rhosocial.activerecord.backend.adapters import BitString
from rhosocial.activerecord.backend.errors import DatabaseError

from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    insert_native,
    read_raw,
)


def test_byte_aligned_roundtrip(native_bit):
    value = BitString.from_bits("10101010")
    instance = native_bit(flags8=value)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.flags8 == value, "byte-aligned BIT must round-trip exactly"
    assert found.flags8.bit_length == 8

    raw_before = read_raw(native_bit, "HEX(flags8)", instance.id)
    assert raw_before == "AA", "the stored form is two hex digits"
    assert read_raw(native_bit, "flags8 + 0", instance.id) == 0xAA

    found.flags8 = value
    found.save()
    assert read_raw(native_bit, "HEX(flags8)", instance.id) == raw_before, (
        "the stored form must be stable across a rewrite"
    )


def test_non_aligned_roundtrip_keeps_width(native_bit):
    value = BitString.from_bits("10101")
    instance = native_bit(flags5=value)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.flags5 == value, "BIT(5) must keep its leading zero"
    assert found.flags5.bit_length == 5
    assert read_raw(native_bit, "HEX(flags5)", instance.id) == "15"

    found.flags5 = value
    found.save()
    assert read_raw(native_bit, "HEX(flags5)", instance.id) == "15", (
        "rewriting must not widen the stored bytes"
    )


def test_non_aligned_multi_byte(native_bit):
    value = BitString.from_bits("1010101010")
    instance = native_bit(flags10=value)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.flags10 == value, "BIT(10) spans two bytes"
    assert found.flags10.bit_length == 10
    assert read_raw(native_bit, "HEX(flags10)", instance.id) == "2AA"
    assert read_raw(native_bit, "flags10 + 0", instance.id) == 0b1010101010


def test_foreign_bit_text_is_decoded_and_rewritten(native_bit):
    insert_native(native_bit, {"id": "9001", "flags5": "b'10101'", "flags8": "b'11110000'"})

    foreign = native_bit.find_one(9001)
    assert foreign.flags5 == BitString.from_bits("10101")
    assert foreign.flags8 == BitString.from_bits("11110000")

    foreign.flags5 = BitString.from_bits("10101")
    foreign.flags8 = BitString.from_bits("11110000")
    foreign.save()
    assert read_raw(native_bit, "HEX(flags5)", 9001) == "15"
    assert read_raw(native_bit, "HEX(flags8)", 9001) == "F0"


def test_width_overflow_is_rejected_by_the_server(native_bit):
    instance = native_bit(flags5=BitString.from_bits("101010"))
    with pytest.raises(DatabaseError) as info:
        instance.save()
    assert "1406" in str(info.value), "BIT(5) must reject a 6-bit value (errno 1406)"


def test_null_bit_columns_stay_null(native_bit):
    instance = native_bit()
    instance.save()
    found = native_bit.find_one(instance.id)
    assert found.flags8 is None
    assert found.flags5 is None
    assert found.flags10 is None
