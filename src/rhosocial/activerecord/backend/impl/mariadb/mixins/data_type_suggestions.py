# src/rhosocial/activerecord/backend/impl/mariadb/mixins/data_type_suggestions.py
"""MariaDB's **suggested data types**: what a bare field is declared as here.

The DDL half of the type answer; :mod:`.column_type` is the operation half.

Shapes this server forces:

* **a document and the four sequence entries share ``JSON``**: MariaDB has no
  array type, and its ``JSON`` column already holds an array.
* **a UUID is native from 10.7 on.** Before that the server has no ``UUID``
  type, so the suggestion falls back to ``VARCHAR(36)``; the table is
  therefore assembled per instance rather than being one module constant, and
  a dialect whose version is not known yet answers with the native form.
* **a bit string is text here.** The adapter writes the value as its digits
  (or bytes), and ``BIT(n)`` would need a width the annotation does not carry.
* **a vector is text here.** MariaDB 11.7's ``VECTOR`` needs a dimension, and
  the adapter's text form round-trips through a text column.

The three parameter-carrying families (``Vector``, ``Range``, ``Multirange``)
name text carriers, and a field that wants the server's native type declares
it with ``UseSqlType``. No key answers ``None``.

Each call returns a fresh dict whose values are read-only templates; the
derivation binds a dialect on a copy of the single entry it uses.
"""
from __future__ import annotations

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional

from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Multirange,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    JsonType,
    TextType,
    TimeType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBBlobType,
    MariaDBGeometryType,
    MariaDBIntType,
    MariaDBTextType,
    MariaDBUUIDType,
)

#: MariaDB's suggested declaration per framework-modelled Python type.
#: ``uuid.UUID`` is replaced per instance when the server is older than 10.7.
MARIADB_DATA_TYPE_SUGGESTIONS: Dict[Any, Optional[Any]] = {
    bool: BooleanType(),
    int: MariaDBIntType(),
    float: DoubleType(),
    decimal.Decimal: DecimalType(),
    str: MariaDBTextType(),
    bytes: MariaDBBlobType(),
    bytearray: MariaDBBlobType(),
    datetime.date: DateType(),
    datetime.time: TimeType(),
    datetime.datetime: TimestampType(precision=3),
    # MariaDB has no interval type; the value's text form is the carrier.
    datetime.timedelta: TextType(),
    uuid.UUID: MariaDBUUIDType(),
    dict: JsonType(),
    list: JsonType(),
    tuple: JsonType(),
    set: JsonType(),
    frozenset: JsonType(),
    enum.Enum: VarCharType(length=255),
    # -- Complex families ------------------------------------------------
    Geometry: MariaDBGeometryType(),
    # A dimension is column policy; the adapter's text form round-trips.
    Vector: TextType(),
    # BIT(n) needs a width the annotation does not carry; digits as text.
    BitString: TextType(),
    # The element type is column policy; the adapter writes JSON text.
    Range: TextType(),
    Multirange: TextType(),
    MacAddress: VarCharType(length=17),
}


class MariaDBDataTypeSuggestionsMixin:
    """MariaDB's answer to "what declaration does a bare field get here"."""

    def suggested_data_types(self) -> Dict[Any, Optional[Any]]:
        table = dict(MARIADB_DATA_TYPE_SUGGESTIONS)
        version = getattr(self, "_version", None)
        if version is not None and tuple(version) < (10, 7):
            # The server has no UUID type before 10.7; its text form is the
            # storage every version accepts.
            table[uuid.UUID] = VarCharType(length=36)
        return table


__all__ = ["MARIADB_DATA_TYPE_SUGGESTIONS", "MariaDBDataTypeSuggestionsMixin"]
