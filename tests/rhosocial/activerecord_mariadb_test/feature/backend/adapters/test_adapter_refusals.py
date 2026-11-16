# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/test_adapter_refusals.py
"""The MariaDB adapters' refusals, pass-throughs and option guards.

The round-trip tests pin what each adapter produces for a good value; this file
pins what it does with a value it should not accept, and with a value already
in the right shape. Two families behave differently and the tests keep that
difference visible:

* the legacy adapters derive from ``SQLTypeAdapter`` and raise the plain
``TypeError``/``ValueError`` their docstrings describe;
* the neutral-family adapters derive from the core bases, which wrap a hook's
failure into ``TypeConversionError``.
"""

import datetime
import uuid
from decimal import Decimal
from enum import Enum

import pytest

from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Point,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.errors import TypeConversionError, ValidationError
from rhosocial.activerecord.backend.impl.mariadb.adapters import (
    MariaDBBitStringAdapter,
    MariaDBBlobAdapter,
    MariaDBBooleanAdapter,
    MariaDBDatetimeAdapter,
    MariaDBDecimalAdapter,
    MariaDBEnumAdapter,
    MariaDBGeometryAdapter,
    MariaDBMacAddressAdapter,
    MariaDBRangeAdapter,
    MariaDBSetAdapter,
    MariaDBTimeAdapter,
    MariaDBUUIDAdapter,
    MariaDBVectorAdapter,
)


class Colour(Enum):
    RED = "red"
    BLUE = "blue"


# ---------------------------------------------------------------------------
# Legacy adapters: plain exceptions
# ---------------------------------------------------------------------------


class TestBlobAdapterRefusals:
    def test_absence_passes_through(self):
        assert MariaDBBlobAdapter().from_database(None, bytes) is None


class TestUUIDAdapterRefusals:
    def test_a_uuid_is_carried_through_on_read(self):
        adapter = MariaDBUUIDAdapter()
        value = uuid.uuid4()
        assert adapter.from_database(value, uuid.UUID) is value

    def test_bytes_are_read_as_the_binary_form(self):
        adapter = MariaDBUUIDAdapter()
        value = uuid.UUID(int=1)
        assert adapter.from_database(value.bytes, uuid.UUID) == value


class TestBooleanAdapterRefusals:
    def test_absence_passes_through(self):
        adapter = MariaDBBooleanAdapter()
        assert adapter.to_database(None, int) is None
        assert adapter.from_database(None, bool) is None


class TestDecimalAdapterRefusals:
    def test_every_write_target(self):
        adapter = MariaDBDecimalAdapter()
        value = Decimal("1.50")

        assert adapter.to_database(None, Decimal) is None
        assert adapter.to_database(value, Decimal) is value
        assert adapter.to_database(value, float) == 1.5
        assert adapter.to_database(value, str) == "1.50"

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.to_database(value, int)

    def test_a_driver_number_is_read_through_text(self):
        adapter = MariaDBDecimalAdapter()

        assert adapter.from_database(None, Decimal) is None
        assert adapter.from_database(Decimal("1.5"), Decimal) == Decimal("1.5")
        assert adapter.from_database("1.50", Decimal) == Decimal("1.50")
        assert adapter.from_database(2, Decimal) == Decimal("2")


class TestTimeAdapterRefusals:
    def test_absence_and_the_text_wire_form(self):
        adapter = MariaDBTimeAdapter()

        assert adapter.to_database(None, str) is None
        assert adapter.to_database(datetime.time(1, 2, 3), str) == "01:02:03.000000"

    def test_all_three_read_shapes(self):
        adapter = MariaDBTimeAdapter()

        assert adapter.from_database(None, datetime.time) is None

        value = datetime.time(1, 2)
        assert adapter.from_database(value, datetime.time) is value

        converted = adapter.from_database(
            datetime.timedelta(hours=1, minutes=2, seconds=3), datetime.time
        )
        assert converted == datetime.time(1, 2, 3)

        assert adapter.from_database("01:02:03", datetime.time) == datetime.time(1, 2, 3)


class TestDatetimeAdapterRefusals:
    def test_an_aware_value_is_normalised_to_utc_before_the_text(self):
        adapter = MariaDBDatetimeAdapter()
        aware = datetime.datetime(
            2024, 1, 1, 12, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )

        assert adapter.to_database(aware, str) == "2024-01-01 10:00:00.000000"

    def test_every_read_shape_gets_a_utc_aware_value(self):
        adapter = MariaDBDatetimeAdapter()

        assert adapter.from_database(None, datetime.datetime) is None

        naive = datetime.datetime(2024, 1, 1, 12, 0)
        assert adapter.from_database(naive, datetime.datetime).tzinfo is datetime.timezone.utc

        aware = datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        assert adapter.from_database(aware, datetime.datetime) is aware

        assert adapter.from_database("2024-01-01T12:00:00", datetime.datetime).tzinfo is (
            datetime.timezone.utc
        )
        assert adapter.from_database("2024-01-01T12:00:00+00:00", datetime.datetime) == aware

        fallback = adapter.from_database(datetime.date(2024, 1, 1), datetime.datetime)
        assert fallback == aware.replace(hour=0, minute=0)


class TestEnumAdapterRefusals:
    def test_a_value_that_is_neither_text_nor_an_index_is_named(self):
        adapter = MariaDBEnumAdapter()

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.from_database(object(), Colour)


class TestSetAdapterRefusals:
    def test_the_target_must_be_text(self):
        adapter = MariaDBSetAdapter()

        with pytest.raises(TypeError, match="only supports str target type"):
            adapter.to_database({"a"}, int)

    def test_at_most_sixty_four_members(self):
        adapter = MariaDBSetAdapter()

        with pytest.raises(ValueError, match="maximum 64 members"):
            adapter.to_database([str(index) for index in range(65)], str)

    def test_a_member_outside_the_declaration_is_named(self):
        """A caller error, not a server error: the framework's validation
        error says which members are outside the declaration."""
        adapter = MariaDBSetAdapter(allowed_values=["a"])

        with pytest.raises(ValidationError, match="Invalid SET"):
            adapter.to_database(["b"], str)

    def test_an_integer_needs_the_member_list_to_decode(self):
        """The bit positions are only meaningful against the declared list."""
        adapter = MariaDBSetAdapter()

        with pytest.raises(ValueError, match="without allowed_values"):
            adapter.from_database(1, set)

    def test_an_integer_decodes_against_the_member_list(self):
        adapter = MariaDBSetAdapter(allowed_values=["a", "b", "c"])

        assert adapter.from_database(0b101, set) == {"a", "c"}
        assert adapter.from_database(0b101, frozenset) == frozenset({"a", "c"})

    def test_an_unreadable_value_is_named(self):
        adapter = MariaDBSetAdapter()

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.from_database(object(), set)


# ---------------------------------------------------------------------------
# Neutral-family adapters: the base wraps failures as TypeConversionError
# ---------------------------------------------------------------------------


class TestGeometryAdapterRefusals:
    def test_an_unusable_srid_option_is_refused(self):
        adapter = MariaDBGeometryAdapter()

        with pytest.raises(TypeConversionError, match="srid option must be int or None"):
            adapter.to_database(Point(1, 2), str, {"srid": "epsg:4326"})
        with pytest.raises(TypeConversionError, match="srid must be non-negative"):
            adapter.to_database(Point(1, 2), str, {"srid": -1})

    def test_a_neutral_geometry_is_carried_through_on_read(self):
        adapter = MariaDBGeometryAdapter()
        value = Point(1, 2)

        assert adapter.from_database(value, Geometry) is value

    def test_an_unreadable_geometry_is_named(self):
        adapter = MariaDBGeometryAdapter()

        with pytest.raises(TypeConversionError, match="expected WKT str or UTF-8 bytes"):
            adapter.from_database(42, Geometry)


class TestVectorAdapterRefusals:
    def test_bytes_must_be_utf8(self):
        adapter = MariaDBVectorAdapter()

        with pytest.raises(TypeConversionError, match="is not UTF-8"):
            adapter.from_database(b"\xff\xfe", Vector)

    def test_an_unreadable_value_is_named(self):
        adapter = MariaDBVectorAdapter()

        with pytest.raises(TypeConversionError, match="expected a JSON array"):
            adapter.from_database(42, Vector)


class TestBitStringAdapterRefusals:
    def test_a_declared_width_must_be_a_positive_integer(self):
        adapter = MariaDBBitStringAdapter()

        with pytest.raises(TypeConversionError, match="bit_length option must be int"):
            adapter.from_database(b"\x01", BitString, {"bit_length": True})
        with pytest.raises(TypeConversionError, match="bit_length option must be at least 1"):
            adapter.from_database(b"\x01", BitString, {"bit_length": 0})

    def test_a_negative_integer_is_refused(self):
        adapter = MariaDBBitStringAdapter()

        with pytest.raises(TypeConversionError, match="must be non-negative"):
            adapter.from_database(-1, BitString, {"bit_length": 8})

    def test_an_unreadable_value_is_named(self):
        adapter = MariaDBBitStringAdapter()

        with pytest.raises(TypeConversionError, match="expected bytes, int or bit text"):
            adapter.from_database(object(), BitString)


class TestRangeAdapterRefusals:
    def test_bytes_must_be_utf8(self):
        adapter = MariaDBRangeAdapter()

        with pytest.raises(TypeConversionError, match="is not UTF-8"):
            adapter.from_database(b"\xff\xfe", Range)

    def test_an_unreadable_json_shape_is_named(self):
        adapter = MariaDBRangeAdapter()

        with pytest.raises(TypeConversionError, match="expected range JSON object or array"):
            adapter.from_database(42, str)


class TestMacAddressAdapterRefusals:
    def test_an_unreadable_value_is_named(self):
        adapter = MariaDBMacAddressAdapter()

        with pytest.raises(TypeConversionError, match="expected MAC address"):
            adapter.from_database(1.5, MacAddress)
