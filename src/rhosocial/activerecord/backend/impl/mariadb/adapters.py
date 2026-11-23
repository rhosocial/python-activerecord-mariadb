# src/rhosocial/activerecord/backend/impl/mariadb/adapters.py
"""MariaDB-specific type adapters.

This module provides type adapters for converting between Python types
and MariaDB database types, handling MariaDB-specific behaviors.
"""

import datetime
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from rhosocial.activerecord.backend.adapters import (
    BitString,
    BitStringAdapterBase,
    Geometry,
    GeometryAdapterBase,
    IPAddress,
    IPAddressAdapterBase,
    MacAddress,
    MacAddressAdapterBase,
    Multirange,
    Range,
    RangeAdapterBase,
    Vector,
    VectorAdapterBase,
)
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MariaDBBlobAdapter(SQLTypeAdapter):
    """Adapts Python bytes to MariaDB BLOB and vice-versa."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bytes: [bytes]}

    def to_database(
        self,
        value: bytes,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[bytes]:
        if value is None:
            return None
        return value


class MariaDBJSONAdapter(SQLTypeAdapter):
    """Adapts Python dict/list to MariaDB JSON (LONGTEXT) and vice-versa.

    MariaDB stores JSON as LONGTEXT internally but provides JSON functions
    for manipulation (since version 10.2.3).

    ``default`` / ``object_hook`` are forwarded to ``json.dumps`` / ``json.loads``
    so callers can plug in neutral-type codecs (see
    ``rhosocial.activerecord.backend.adapters.json_codec``) without changing the
    default behaviour.
    """

    def __init__(self, default=None, object_hook=None):
        self._json_default = default
        self._json_object_hook = object_hook

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {dict: [str], list: [str]}

    def to_database(
        self,
        value: Union[dict, list],
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=self._json_default)

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Union[dict, list]]:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value, object_hook=self._json_object_hook)


class MariaDBUUIDAdapter(SQLTypeAdapter):
    """Adapts Python UUID to MariaDB CHAR(36) or BINARY(16) and vice-versa."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {uuid.UUID: [str, bytes]}

    def to_database(
        self,
        value: uuid.UUID,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        if target_type is bytes:
            return value.bytes
        return str(value)

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[uuid.UUID]:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, bytes):
            return uuid.UUID(bytes=value)
        return uuid.UUID(value)


class MariaDBBooleanAdapter(SQLTypeAdapter):
    """Adapts Python bool to MariaDB TINYINT(1) and vice-versa."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bool: [int]}

    def to_database(
        self,
        value: bool,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return 1 if value else 0

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)


class MariaDBDecimalAdapter(SQLTypeAdapter):
    """Adapts Python Decimal to MariaDB DECIMAL/NUMERIC and vice-versa."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Decimal: [Decimal, float, str]}

    def to_database(
        self,
        value: Decimal,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        if target_type is Decimal:
            return value
        if target_type is float:
            return float(value)
        if target_type is str:
            return str(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class MariaDBDateAdapter(SQLTypeAdapter):
    """Adapts Python date to MariaDB DATE string (YYYY-MM-DD) and vice-versa."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.date: [datetime.date, str]}

    def to_database(
        self,
        value: datetime.date,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value.isoformat()

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[datetime.date]:
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        return datetime.date.fromisoformat(str(value))


class MariaDBTimeAdapter(SQLTypeAdapter):
    """Adapts Python time to MariaDB TIME string and vice-versa.

    MariaDB connector may return timedelta for TIME columns.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.time: [datetime.timedelta, str]}

    def to_database(
        self,
        value: datetime.time,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value.isoformat(timespec='microseconds')

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[datetime.time]:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return datetime.time(hours, minutes, seconds, value.microseconds)
        return datetime.time.fromisoformat(str(value))


class MariaDBDatetimeAdapter(SQLTypeAdapter):
    """Adapts Python datetime to MariaDB DATETIME/TIMESTAMP and vice-versa.

    Handles timezone-aware datetime normalization to UTC.
    """

    def __init__(self, mariadb_version: Optional[Tuple[int, int, int]] = None):
        """Initialize the adapter.

        Args:
            mariadb_version: Accepted for call-site compatibility. Behaviour
                does not currently vary by server version, so the value is
                not retained.
        """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.datetime: [datetime.datetime, str]}

    def to_database(
        self,
        value: datetime.datetime,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value.strftime('%Y-%m-%d %H:%M:%S.%f')

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[datetime.datetime]:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value
        if isinstance(value, str):
            dt = datetime.datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        return datetime.datetime.fromisoformat(str(value)).replace(tzinfo=datetime.timezone.utc)


class MariaDBEnumAdapter(SQLTypeAdapter):
    """Adapts Python Enum to MariaDB ENUM type and vice-versa.

    MariaDB ENUM stores values as integers internally (1, 2, 3...) but
    displays as strings.
    """

    def __init__(self, use_int_storage: bool = False):
        """Initialize MariaDB ENUM adapter.

        Args:
            use_int_storage: If True, uses integer representation when writing.
                             If False (default), uses string representation.
        """
        self._use_int_storage = use_int_storage

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Enum: [str, int]}

    def to_database(
        self,
        value: Enum,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None

        enum_values = options.get('enum_values') if options else None
        if enum_values and value.value not in enum_values:
            raise ValueError(
                f"Invalid enum value '{value.value}'. Allowed values: {enum_values}"
            )

        use_int = (options.get('use_int_storage', self._use_int_storage)
                   if options else self._use_int_storage)

        if target_type is str:
            return str(value.value)

        if target_type is int:
            if use_int:
                enum_members = list(type(value))
                return enum_members.index(value) + 1
            else:
                if isinstance(value.value, int):
                    return value.value
                raise TypeError(
                    "Cannot convert string-based enum to int. "
                    "Set 'use_int_storage=True' to use MariaDB internal index."
                )

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")

    def from_database(
        self,
        value: Any,
        target_type: Type[Enum],
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Enum]:
        if value is None:
            return None

        if isinstance(value, str):
            for member in target_type:
                if str(member.value) == value:
                    return member
            try:
                return target_type[value]
            except KeyError:
                raise ValueError(
                    f"Invalid enum value '{value}'. "
                    f"Valid values: {[m.value for m in target_type]}"
                )

        if isinstance(value, int):
            enum_members = list(target_type)
            if 1 <= value <= len(enum_members):
                return enum_members[value - 1]
            try:
                return target_type(value)
            except ValueError:
                raise ValueError(
                    f"Invalid enum index {value}. "
                    f"Valid range: 1-{len(enum_members)}"
                )

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")


class MariaDBSetAdapter(SQLTypeAdapter):
    """Adapts Python set/frozenset to MariaDB SET type and vice-versa.

    MariaDB SET is a string object that can have zero or more values,
    stored as bit flags internally but displayed as comma-separated strings.
    """

    def __init__(self, allowed_values: Optional[List[str]] = None):
        """Initialize MariaDB SET adapter.

        Args:
            allowed_values: Optional list of allowed SET values for validation.
        """
        self._allowed_values = allowed_values

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {set: [str], frozenset: [str]}

    def to_database(
        self,
        value: Union[set, frozenset],
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None

        if target_type is not str:
            raise TypeError(
                f"MariaDB SET adapter only supports str target type, got {target_type.__name__}"
            )

        if len(value) > 64:
            raise ValueError(f"MariaDB SET supports maximum 64 members, got {len(value)}")

        allowed_values = (options.get('allowed_values', self._allowed_values)
                          if options else self._allowed_values)

        if allowed_values is not None:
            invalid_values = [v for v in value if str(v) not in allowed_values]
            if invalid_values:
                # A caller error, not a server error: nothing has been sent yet,
                # and the value can never be bound. Raising the framework's
                # validation error keeps save() from relabelling it a database
                # failure.
                from rhosocial.activerecord.backend.errors import ValidationError

                raise ValidationError(
                    f"Invalid SET values: {invalid_values}. Allowed values: {allowed_values}"
                )

        sorted_values = sorted(str(v) for v in value)
        return ','.join(sorted_values) if sorted_values else ''

    def _decode_set_from_int(
        self,
        value: int,
        target_type: Type,
        allowed_values: Optional[List[str]]
    ) -> Union[set, frozenset]:
        if allowed_values is None:
            raise ValueError(
                "Cannot decode SET from integer without allowed_values."
            )

        result = set()
        for i, val in enumerate(allowed_values):
            if value & (1 << i):
                result.add(val)

        return frozenset(result) if target_type is frozenset else result

    def _decode_set_from_string(
        self,
        value: str,
        target_type: Type
    ) -> Union[set, frozenset]:
        if not value:
            result = set()
        else:
            result = set(value.split(','))
        return frozenset(result) if target_type is frozenset else result

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Union[set, frozenset]]:
        if value is None:
            return None

        if isinstance(value, int):
            allowed_values = (self._allowed_values or
                              (options.get('allowed_values') if options else None))
            return self._decode_set_from_int(value, target_type, allowed_values)

        if isinstance(value, str):
            return self._decode_set_from_string(value, target_type)

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")


# ---------------------------------------------------------------------------
# Neutral-type adapters (their neutral types live in the core package)
# ---------------------------------------------------------------------------
#
# MariaDB has no range, MAC address or IP address column types, so those
# adapters carry their values in TEXT/BINARY columns. The spatial types are
# native to the server, but the adapter deliberately speaks WKT text rather
# than the server's internal binary geometry layout (see MariaDBGeometryAdapter).


class MariaDBGeometryAdapter(GeometryAdapterBase):
    """Carries neutral :class:`Geometry` values as WKT text.

    **This is not native geometry binding.** The adapter emits plain WKT, with
    an ``SRID=<n>;`` prefix when an SRID is known, and binds it as ``str``
    (or UTF-8 ``bytes``). It does not wrap the value in ``ST_GeomFromText``.

    Consequences, stated plainly rather than implied:

    * Whether a bound WKT string is accepted by a ``POINT``/``GEOMETRY``
      column depends on the server's implicit string-to-geometry conversion.
      That conversion is **not** guaranteed for parameter placeholders. When
      the server rejects it, the value must go through
      ``ST_GeomFromText(?, srid)`` at the expression layer. No live-server
      verification of plain-text binding was done in this change.
    * ``SRID=n;`` is the EWKT spelling. MariaDB's spatial functions normally
      take the SRID as a second argument (``ST_GeomFromText(wkt, srid)``) and
      declare it on the column with ``REF_SYSTEM_ID=<n>``, so an EWKT-prefixed
      string is only usable where the server parses the prefix itself.
    * ``_decode`` reads WKT text only. The MariaDB connector commonly returns
      geometry columns in the server's internal binary format; that is not
      WKT and is rejected with :class:`TypeConversionError`. Select
      ``ST_AsText(col)`` to read a geometry column through this adapter.

    Use this adapter when a WKT/TEXT carrier is acceptable, and treat native
    geometry-column round-trips as a follow-up (see the backend type-adapter
    plan's MariaDB spatial gap).
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Geometry: [str]}

    def _effective_srid(self, geometry: Geometry, options: Dict[str, Any]) -> Optional[int]:
        """Column SRID from the options, unless the value carries its own."""
        if geometry.srid is not None:
            return geometry.srid
        srid = options.get('srid')
        if srid is None:
            return None
        if isinstance(srid, bool) or not isinstance(srid, int):
            self._conversion_error(geometry, 'srid option must be int or None')
        if srid < 0:
            self._conversion_error(geometry, f'srid must be non-negative, got {srid}')
        return srid

    def _encode(self, geometry: Geometry, target_type: Type, options: Dict[str, Any]) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f'WKT text can only be bound as str or bytes, got {target_type.__name__}'
            )
        text = geometry.to_wkt()
        srid = self._effective_srid(geometry, options)
        if srid is not None:
            text = f'SRID={srid};{text}'
        if target_type is bytes:
            return text.encode('utf-8')
        return text

    def _decode(self, value: Any, options: Dict[str, Any]) -> Geometry:
        if isinstance(value, Geometry):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                text = bytes(value).decode('utf-8')
            except UnicodeDecodeError:
                self._conversion_error(
                    value,
                    'driver returned binary geometry (not WKT text); '
                    'select ST_AsText(col) or bind a WKT string',
                )
        elif isinstance(value, str):
            text = value
        else:
            raise TypeError(f'expected WKT str or UTF-8 bytes, got {type(value).__name__}')

        return Geometry.from_wkt(text, srid=options.get('srid'))


class MariaDBVectorAdapter(VectorAdapterBase):
    """Adapts neutral :class:`Vector` values to MariaDB TEXT/JSON columns.

    MariaDB 11.4 (the version wired for this backend) has no native ``VECTOR``
    column type, and this backend does not model the 11.7+ ``VECTOR(n)`` type
    yet. The adapter therefore writes the canonical JSON array text
    (``'[1.0,2.0,3.0]'``) that a ``TEXT``/``JSON``/``LONGTEXT`` column already
    accepts, and reads it back through :meth:`Vector.from_json_value`, which
    also understands the non-finite spellings (``"NaN"``, ``"Infinity"``,
    ``"-Infinity"``).

    If/when a native ``MariaDBVectorType`` is added, a binary wire format can
    be introduced without changing this neutral adapter's public behaviour:
    the target type and ``options`` already reach the encode/decode hooks.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Vector: [str, bytes]}

    def _encode(self, vector: Vector, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f'vector JSON text can only be bound as str or bytes, got {target_type.__name__}'
            )
        # Emit every finite component as a float, matching the wire text the
        # MySQL adapter produces (``'[1.0,2.0]'``), while keeping the
        # non-finite spellings that :meth:`Vector.to_json_value` chose.
        values = [item if isinstance(item, str) else float(item)
                  for item in vector.to_json_value()]
        text = json.dumps(values, ensure_ascii=False, separators=(',', ':'))
        if target_type is bytes:
            return text.encode('utf-8')
        return text

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> Vector:
        if isinstance(value, Vector):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                value = bytes(value).decode('utf-8')
            except UnicodeDecodeError as exc:
                raise ValueError(f'vector JSON text is not UTF-8: {exc}') from exc
        if isinstance(value, str):
            value = json.loads(value)
        if isinstance(value, (list, tuple)):
            return Vector.from_json_value(value)
        raise TypeError(f'expected a JSON array, got {type(value).__name__}')


class MariaDBBitStringAdapter(BitStringAdapterBase):
    """Adapts neutral :class:`BitString` values to MariaDB ``BIT``/binary columns.

    Encoding targets:

    * ``bytes`` -- :attr:`BitString.data`, the bits MSB-first. ``data`` keeps
      zero padding in the low bits of the last byte, so this form is exact for
      widths that are multiples of 8; for ``BIT(n)`` with ``n % 8 != 0`` the
      padded byte value is wider than the column and must not be bound there.
    * ``int`` -- :meth:`BitString.to_int`, the significant bits as an integer.
      Use this for a ``BIT(n)`` column of any width.
    * ``str`` -- :meth:`BitString.to_bits`, e.g. ``"10101"``.

    Decoding reads bytes/int as a big-endian unsigned number and takes the
    declared width as the significant bits. A width can come from the
    constructor (``bit_length=...``) or per-call ``options={"bit_length": n}``.

    **A declared width is required to restore leading zeros** when the column
    width is not a multiple of 8; without one, decoding assumes the whole
    byte length is significant (``8 * len(data)`` bits), which is correct for
    BLOB carriers and for ``BIT(n)`` with ``n % 8 == 0`` only. The adapter
    cannot read the width back from the value, because a ``BIT`` value carries
    no length metadata.
    """

    def __init__(self, bit_length: Optional[int] = None):
        super().__init__()
        if bit_length is not None:
            if isinstance(bit_length, bool) or not isinstance(bit_length, int):
                raise TypeError(f'bit_length must be int or None, got {type(bit_length).__name__}')
            if bit_length < 1:
                raise ValueError(f'bit_length must be at least 1, got {bit_length}')
        self._bit_length = bit_length

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {BitString: [bytes, int, str]}

    def _resolve_bit_length(self, options: Optional[Dict[str, Any]]) -> Optional[int]:
        length = self._bit_length
        if options and 'bit_length' in options:
            length = options['bit_length']
        if length is not None:
            if isinstance(length, bool) or not isinstance(length, int):
                raise TypeError(f'bit_length option must be int, got {type(length).__name__}')
            if length < 1:
                raise ValueError(f'bit_length option must be at least 1, got {length}')
        return length

    def _encode(self, bits: BitString, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is bytes:
            return bits.data
        if target_type is int:
            return bits.to_int()
        if target_type is str:
            return bits.to_bits()
        raise TypeError(
            f'BIT values can only be bound as bytes, int or str, got {target_type.__name__}'
        )

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> BitString:
        if isinstance(value, BitString):
            return value
        length = self._resolve_bit_length(options)
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            if not data:
                raise ValueError('BIT/BLOB value is empty bytes')
            number = int.from_bytes(data, 'big')
            return BitString.from_int(number, length if length is not None else len(data) * 8)
        if isinstance(value, int) and not isinstance(value, bool):
            if value < 0:
                raise ValueError(f'BIT value must be non-negative, got {value}')
            if length is None:
                raise ValueError('a declared bit_length is required to decode an int BIT value')
            return BitString.from_int(value, length)
        if isinstance(value, str):
            return BitString.from_bits(value)
        raise TypeError(f'expected bytes, int or bit text, got {type(value).__name__}')


class MariaDBRangeAdapter(RangeAdapterBase):
    """Carries neutral :class:`Range`/:class:`Multirange` as JSON text.

    MariaDB has no range column type, so values live in ``TEXT``/``JSON``
    columns. The payload is :meth:`Range.to_json_value` /
    :meth:`Multirange.to_json_value` (lossless, including ``element_type``).

    Multirange values require the target type to be ``Multirange`` or an
    untyped target; a bare JSON array cannot be restored as a ``Range``.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Range: [str], Multirange: [str]}

    def _encode(
        self, value: Union[Range, Multirange], target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f'range JSON text can only be bound as str or bytes, got {target_type.__name__}'
            )
        text = json.dumps(value.to_json_value(), ensure_ascii=False, separators=(',', ':'))
        if target_type is bytes:
            return text.encode('utf-8')
        return text

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        if isinstance(value, (Range, Multirange)):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                value = bytes(value).decode('utf-8')
            except UnicodeDecodeError as exc:
                raise ValueError(f'range JSON text is not UTF-8: {exc}') from exc
        if isinstance(value, str):
            value = json.loads(value)
        if target_type is Range:
            return Range.from_json_value(value)
        if target_type is Multirange:
            return Multirange.from_json_value(value)
        if isinstance(value, dict):
            return Range.from_json_value(value)
        if isinstance(value, (list, tuple)):
            return Multirange.from_json_value(value)
        raise TypeError(f'expected range JSON object or array, got {type(value).__name__}')


class MariaDBMacAddressAdapter(MacAddressAdapterBase):
    """Adapts neutral :class:`MacAddress` to text/binary MariaDB columns.

    MariaDB has no MAC address column type. The canonical text form
    (lowercase, colon separated) is used for ``CHAR``/``VARCHAR`` columns; the
    raw 6/8 octets are used when the target is ``bytes``
    (``BINARY``/``VARBINARY``).
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {MacAddress: [str, bytes]}

    def _encode(self, mac: MacAddress, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is str:
            return str(mac)
        if target_type is bytes:
            return mac.octets
        raise TypeError(
            f'MAC address can only be bound as str or bytes, got {target_type.__name__}'
        )

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> MacAddress:
        if isinstance(value, MacAddress):
            return value
        if isinstance(value, (str, bytes, bytearray, int)) and not isinstance(value, bool):
            return MacAddress.parse(value)
        raise TypeError(f'expected MAC address text or bytes, got {type(value).__name__}')


class MariaDBIPAddressAdapter(IPAddressAdapterBase):
    """Store neutral :class:`IPAddress` values as canonical text.

    MariaDB has no native IP address column type. The canonical compressed
    form (``192.0.2.1`` / ``2001:db8::1``) is bound as ``str`` into a
    ``VARCHAR(45)`` column, matching the framework's suggested declaration.
    """

    def __init__(self):
        super().__init__()
        self.register_type(IPAddress, str)

    def _encode(
        self, ip_addr: IPAddress, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> str:
        return str(ip_addr)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> IPAddress:
        return IPAddress.parse(self._require_text(value))


mariadb_adapters = [
    MariaDBBlobAdapter(),
    MariaDBJSONAdapter(),
    MariaDBUUIDAdapter(),
    MariaDBBooleanAdapter(),
    MariaDBDecimalAdapter(),
    MariaDBDateAdapter(),
    MariaDBTimeAdapter(),
    MariaDBEnumAdapter(use_int_storage=False),
    MariaDBSetAdapter(),
    MariaDBGeometryAdapter(),
    MariaDBVectorAdapter(),
    MariaDBBitStringAdapter(),
    MariaDBRangeAdapter(),
    MariaDBMacAddressAdapter(),
    MariaDBIPAddressAdapter(),
]

__all__ = [
    'MariaDBBlobAdapter',
    'MariaDBJSONAdapter',
    'MariaDBUUIDAdapter',
    'MariaDBBooleanAdapter',
    'MariaDBDecimalAdapter',
    'MariaDBDateAdapter',
    'MariaDBTimeAdapter',
    'MariaDBDatetimeAdapter',
    'MariaDBEnumAdapter',
    'MariaDBSetAdapter',
    'MariaDBGeometryAdapter',
    'MariaDBVectorAdapter',
    'MariaDBBitStringAdapter',
    'MariaDBRangeAdapter',
    'MariaDBMacAddressAdapter',
    'MariaDBIPAddressAdapter',
    'mariadb_adapters',
]
