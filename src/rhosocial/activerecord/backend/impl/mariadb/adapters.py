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
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        if value is None:
            return None
        return value


class MariaDBJSONAdapter(SQLTypeAdapter):
    """Adapts Python dict/list to MariaDB JSON (LONGTEXT) and vice-versa.

    MariaDB stores JSON as LONGTEXT internally but provides JSON functions
    for manipulation (since version 10.2.3).
    """

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
        return json.dumps(value, ensure_ascii=False)

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[Union[dict, list]]:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)


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
        options: Optional[Dict[str, Any]] = None
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
        options: Optional[Dict[str, Any]] = None
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
        options: Optional[Dict[str, Any]] = None
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
        options: Optional[Dict[str, Any]] = None
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
        options: Optional[Dict[str, Any]] = None
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
        """Initialize adapter with MariaDB version info.

        Args:
            mariadb_version: MariaDB server version tuple (major, minor, patch).
                             If None, defaults to (10, 5, 0).
        """
        self._mariadb_version = mariadb_version or (10, 5, 0)

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
        options: Optional[Dict[str, Any]] = None
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
        options: Optional[Dict[str, Any]] = None
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
                raise ValueError(
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
        options: Optional[Dict[str, Any]] = None
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
    'mariadb_adapters',
]
