# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/test_neutral_type_adapters.py
"""DB-free tests for the MariaDB adapters of the core neutral types.

Every test here runs without a MariaDB connection: the adapters are pure
value <-> wire-format conversions. What is pinned:

* the encode/decode round-trips (including the declared-width caveat of
  ``BIT`` and the JSON-array carrier of vectors);
* that every conversion failure surfaces as ``TypeConversionError`` rather
  than a driver exception or a silently wrong value;
* that the backend inventory registers all of the neutral adapters without
  displacing the JSON adapter for plain ``list`` values.
"""

import datetime
import json
from decimal import Decimal

import pytest
from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    GeometryCollection,
    LineString,
    MacAddress,
    Multirange,
    Point,
    Polygon,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.errors import TypeConversionError

from rhosocial.activerecord.backend.impl.mariadb.adapters import (
    MariaDBBitStringAdapter,
    MariaDBGeometryAdapter,
    MariaDBJSONAdapter,
    MariaDBMacAddressAdapter,
    MariaDBRangeAdapter,
    MariaDBVectorAdapter,
)
from rhosocial.activerecord.backend.impl.mariadb.backend import (
    AsyncMariaDBBackend,
    MariaDBBackend,
)

# --- Geometry --------------------------------------------------------------


class TestGeometryAdapter:
    @pytest.fixture
    def adapter(self):
        return MariaDBGeometryAdapter()

    def test_encode_plain_wkt(self, adapter):
        assert adapter.to_database(Point(1, 2), str) == "POINT (1.0 2.0)"

    def test_encode_prepends_srid_from_value(self, adapter):
        assert adapter.to_database(Point(1, 2, srid=4326), str) == "SRID=4326;POINT (1.0 2.0)"

    def test_encode_prepends_srid_from_options(self, adapter):
        assert adapter.to_database(Point(1, 2), str, {"srid": 3857}) == "SRID=3857;POINT (1.0 2.0)"

    def test_encode_value_srid_wins_over_options(self, adapter):
        text = adapter.to_database(Point(1, 2, srid=4326), str, {"srid": 3857})
        assert text == "SRID=4326;POINT (1.0 2.0)"

    def test_encode_bytes_target_is_utf8(self, adapter):
        encoded = adapter.to_database(Point(1, 2), bytes)
        assert encoded == b"POINT (1.0 2.0)"
        assert isinstance(encoded, bytes)

    def test_encode_accepts_wkt_text_input(self, adapter):
        assert adapter.to_database("POINT (3 4)", str) == "POINT (3.0 4.0)"

    def test_decode_wkt_text(self, adapter):
        assert adapter.from_database("SRID=4326;POINT (1.0 2.0)", Geometry) == Point(
            1, 2, srid=4326
        )

    def test_decode_utf8_wkt_bytes(self, adapter):
        assert adapter.from_database(b"POINT (1.0 2.0)", Point) == Point(1, 2)

    def test_decode_options_srid_applied_without_prefix(self, adapter):
        assert adapter.from_database("POINT (1.0 2.0)", Point, {"srid": 4326}) == Point(
            1, 2, srid=4326
        )

    def test_decode_non_text_binary_is_reported_not_guessed(self, adapter):
        # The MariaDB connector hands geometry columns back in the server's
        # internal binary layout; bytes that are not UTF-8 must fail loudly
        # instead of being decoded as some other format.
        with pytest.raises(TypeConversionError) as info:
            adapter.from_database(b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\xf0\x3f", Point)
        assert "ST_AsText" in str(info.value)
        assert "Cannot convert bytes to Geometry" in str(info.value)

    def test_roundtrip_point(self, adapter):
        value = Point(1.5, -2.25, srid=4326)
        assert adapter.from_database(adapter.to_database(value, str), Geometry) == value

    def test_roundtrip_polygon(self, adapter):
        value = Polygon([[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]], srid=4326)
        assert adapter.from_database(adapter.to_database(value, str), Geometry) == value

    def test_roundtrip_line_string(self, adapter):
        value = LineString([(0, 0), (1, 1), (2, 0)])
        assert adapter.from_database(adapter.to_database(value, str), Geometry) == value

    def test_roundtrip_geometry_collection(self, adapter):
        value = GeometryCollection([Point(1, 2), LineString([(0, 0), (1, 1)])])
        assert adapter.from_database(adapter.to_database(value, str), Geometry) == value

    def test_invalid_wkt_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError) as info:
            adapter.from_database("SRID=4326;POINT (1 2 3)", Point)
        assert "only 2D coordinates are supported" in str(info.value)

    def test_invalid_srid_option_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(Point(1, 2), str, {"srid": -1})

    def test_unsupported_target_type_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError) as info:
            adapter.to_database(Point(1, 2), int)
        assert "str or bytes" in str(info.value)


# --- Vector ----------------------------------------------------------------


class TestVectorAdapter:
    @pytest.fixture
    def adapter(self):
        return MariaDBVectorAdapter()

    def test_encode_canonical_json_text(self, adapter):
        assert adapter.to_database(Vector([1.0, 2.0, 3.0]), str) == "[1.0,2.0,3.0]"

    def test_encode_bytes_target(self, adapter):
        assert adapter.to_database(Vector([1.0, 2.0]), bytes) == b"[1.0,2.0]"

    def test_encode_accepts_plain_list(self, adapter):
        assert adapter.to_database([1, 2], str) == "[1.0,2.0]"

    def test_decode_text(self, adapter):
        assert adapter.from_database("[1.0,2.0,3.0]", Vector) == Vector([1.0, 2.0, 3.0])

    def test_decode_bytes(self, adapter):
        assert adapter.from_database(b"[1.0,2.0]", Vector) == Vector([1.0, 2.0])

    def test_decode_preparsed_list(self, adapter):
        assert adapter.from_database([1.0, 2.0], Vector) == Vector([1.0, 2.0])

    def test_roundtrip(self, adapter):
        value = Vector([0.5, -1.25, 4.0])
        assert adapter.from_database(adapter.to_database(value, str), Vector) == value

    def test_non_finite_roundtrip(self, adapter):
        value = Vector([float("nan"), float("inf"), 1.0], allow_non_finite=True)
        decoded = adapter.from_database(adapter.to_database(value, str), Vector)
        assert decoded.dimension == 3
        assert decoded.allow_non_finite is True
        assert decoded.values[1] == float("inf")

    def test_invalid_json_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database("not-a-vector", Vector)

    def test_empty_array_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database("[]", Vector)

    def test_invalid_utf8_bytes_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError) as info:
            adapter.from_database(b"\xff\xfe", Vector)
        assert "UTF-8" in str(info.value)

    def test_non_numeric_element_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(["nope"], Vector)

    def test_unsupported_target_type_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(Vector([1.0]), dict)


# --- Bit string ------------------------------------------------------------


class TestBitStringAdapter:
    @pytest.fixture
    def adapter(self):
        return MariaDBBitStringAdapter()

    def test_encode_bytes_uses_data(self, adapter):
        bits = BitString.from_bits("10101010")
        assert adapter.to_database(bits, bytes) == b"\xaa"
        assert adapter.to_database(bits, bytes) == bits.data

    def test_encode_int_uses_significant_bits(self, adapter):
        assert adapter.to_database(BitString.from_bits("101"), int) == 5

    def test_encode_str_uses_bit_text(self, adapter):
        assert adapter.to_database(BitString.from_bits("10101"), str) == "10101"

    def test_roundtrip_byte_aligned_bytes(self, adapter):
        value = BitString.from_bits("1000000000000101")
        assert adapter.from_database(adapter.to_database(value, bytes), BitString) == value

    def test_roundtrip_declared_width_from_constructor(self):
        adapter = MariaDBBitStringAdapter(bit_length=10)
        value = BitString.from_int(0x205, 10)
        assert adapter.from_database(b"\x02\x05", BitString) == value
        assert value.to_bits() == "1000000101"

    def test_roundtrip_declared_width_from_options(self):
        adapter = MariaDBBitStringAdapter()
        value = BitString.from_int(0x205, 10)
        decoded = adapter.from_database(b"\x02\x05", BitString, {"bit_length": 10})
        assert decoded == value

    def test_options_width_wins_over_constructor(self):
        adapter = MariaDBBitStringAdapter(bit_length=16)
        assert adapter.from_database(b"\x05", BitString, {"bit_length": 3}) == (
            BitString.from_bits("101")
        )

    def test_decode_without_width_assumes_whole_bytes(self, adapter):
        assert adapter.from_database(b"\x05", BitString) == BitString.from_bits("00000101")

    def test_decode_int_requires_declared_width(self, adapter):
        with pytest.raises(TypeConversionError) as info:
            adapter.from_database(5, BitString)
        assert "declared bit_length" in str(info.value)

    def test_decode_int_with_declared_width(self):
        adapter = MariaDBBitStringAdapter(bit_length=3)
        assert adapter.from_database(5, BitString) == BitString.from_bits("101")

    def test_decode_bit_text(self, adapter):
        assert adapter.from_database("10101", BitString) == BitString.from_bits("10101")

    def test_empty_bytes_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database(b"", BitString)

    def test_value_too_wide_for_declared_width_is_wrapped(self):
        adapter = MariaDBBitStringAdapter(bit_length=3)
        with pytest.raises(TypeConversionError):
            adapter.from_database(b"\x05\x00", BitString)

    def test_unsupported_target_type_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(BitString.from_bits("1"), float)

    def test_invalid_constructor_width(self):
        with pytest.raises(ValueError):
            MariaDBBitStringAdapter(bit_length=0)
        with pytest.raises(TypeError):
            MariaDBBitStringAdapter(bit_length=True)


# --- Range / Multirange ----------------------------------------------------


class TestRangeAdapter:
    @pytest.fixture
    def adapter(self):
        return MariaDBRangeAdapter()

    def test_encode_is_lossless_json_text(self, adapter):
        text = adapter.to_database(Range(1, 10, "[)"), str)
        assert text == '{"lower":1,"upper":10,"bounds":"[)","empty":false,"element_type":"int"}'
        assert json.loads(text) == Range(1, 10, "[)").to_json_value()

    def test_encode_bytes_target(self, adapter):
        assert isinstance(adapter.to_database(Range(1, 10), bytes), bytes)

    def test_roundtrip_int_range(self, adapter):
        value = Range(1, 10, "[)")
        assert adapter.from_database(adapter.to_database(value, str), Range) == value

    def test_roundtrip_decimal_range(self, adapter):
        value = Range(Decimal("1.50"), Decimal("9.99"), "[]")
        assert adapter.from_database(adapter.to_database(value, str), Range) == value

    def test_roundtrip_date_range(self, adapter):
        value = Range(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31), "[)")
        assert adapter.from_database(adapter.to_database(value, str), Range) == value

    def test_roundtrip_empty_range(self, adapter):
        value = Range(empty=True)
        assert adapter.from_database(adapter.to_database(value, str), Range) == value

    def test_roundtrip_multirange_and_normalization(self, adapter):
        value = Multirange([Range(1, 10, "[)"), Range(10, 20, "[]")])
        encoded = adapter.to_database(value, str)
        decoded = adapter.from_database(encoded, Multirange)
        assert decoded == value
        assert len(decoded.ranges) == 1

    def test_decode_bytes_json(self, adapter):
        text = adapter.to_database(Range(1, 2), bytes)
        assert adapter.from_database(text, Range) == Range(1, 2)

    def test_decode_without_declared_type_infers_from_shape(self, adapter):
        assert adapter.from_database(
            '{"lower":1,"upper":2,"bounds":"[)","empty":false,' '"element_type":"int"}', object
        ) == Range(1, 2)
        assert adapter.from_database(
            '[{"lower":1,"upper":2,"bounds":"[)","empty":false,"element_type":"int"}]', object
        ) == Multirange([Range(1, 2)])

    def test_array_payload_cannot_be_a_range(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database(
                '[{"lower":1,"upper":2,"bounds":"[)","empty":false,"element_type":"int"}]',
                Range,
            )

    def test_invalid_json_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database("{not json", Range)

    def test_non_range_input_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError) as info:
            adapter.to_database("1,10", str)
        assert "expected Range or Multirange" in str(info.value)

    def test_unsupported_target_type_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(Range(1, 2), int)


# --- Mac address -----------------------------------------------------------


class TestMacAddressAdapter:
    @pytest.fixture
    def adapter(self):
        return MariaDBMacAddressAdapter()

    def test_encode_canonical_text(self, adapter):
        assert adapter.to_database(MacAddress.parse("08:00:2B:01:02:03"), str) == (
            "08:00:2b:01:02:03"
        )

    def test_encode_bytes_uses_octets(self, adapter):
        assert adapter.to_database(MacAddress.parse("08002b010203"), bytes) == (
            b"\x08\x00\x2b\x01\x02\x03"
        )

    def test_decode_text(self, adapter):
        assert adapter.from_database("08-00-2B-01-02-03", MacAddress) == (
            MacAddress.parse("08002b010203")
        )

    def test_decode_bytes(self, adapter):
        assert adapter.from_database(b"\x08\x00\x2b\x01\x02\x03", MacAddress) == (
            MacAddress.parse("08002b010203")
        )

    def test_roundtrip_text_and_bytes(self, adapter):
        value = MacAddress.parse("08:00:2b:01:02:03")
        assert adapter.from_database(adapter.to_database(value, str), MacAddress) == value
        assert adapter.from_database(adapter.to_database(value, bytes), MacAddress) == value

    def test_roundtrip_eui64(self, adapter):
        value = MacAddress.parse("01:02:03:04:05:06:07:08")
        assert adapter.from_database(adapter.to_database(value, str), MacAddress) == value

    def test_invalid_mac_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.from_database("zz:zz:zz:zz:zz:zz", MacAddress)

    def test_unsupported_target_type_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError):
            adapter.to_database(MacAddress.parse("08002b010203"), int)


# --- Inventory -------------------------------------------------------------


@pytest.fixture(params=[MariaDBBackend, AsyncMariaDBBackend], ids=["sync", "async"])
def backend(request):
    """Instantiate the backend without connecting to a server."""
    return request.param(version=(11, 4, 2), host="localhost", database="test")


class TestAdapterInventory:
    EXPECTED = (
        MariaDBBitStringAdapter,
        MariaDBGeometryAdapter,
        MariaDBMacAddressAdapter,
        MariaDBRangeAdapter,
        MariaDBVectorAdapter,
    )

    def test_every_neutral_adapter_is_in_the_inventory(self, backend):
        classes = {type(adapter) for adapter in backend.get_type_adapters()}
        for expected in self.EXPECTED:
            assert expected in classes

    def test_neutral_adapters_are_registered_under_their_neutral_type(self, backend):
        registry = backend.adapter_registry
        assert isinstance(registry.get_adapter(Geometry, str), MariaDBGeometryAdapter)
        assert isinstance(registry.get_adapter(Vector, str), MariaDBVectorAdapter)
        assert isinstance(registry.get_adapter(BitString, bytes), MariaDBBitStringAdapter)
        assert isinstance(registry.get_adapter(Range, str), MariaDBRangeAdapter)
        assert isinstance(registry.get_adapter(Multirange, str), MariaDBRangeAdapter)
        assert isinstance(registry.get_adapter(MacAddress, str), MariaDBMacAddressAdapter)

    def test_json_adapter_still_wins_for_plain_lists(self, backend):
        suggestions = backend.get_default_adapter_suggestions()
        assert isinstance(suggestions[list][0], MariaDBJSONAdapter)
        assert isinstance(backend.adapter_registry.get_adapter(list, str), MariaDBJSONAdapter)
