# src/rhosocial/activerecord/backend/impl/mariadb/mixins/column_type.py
"""MariaDB's answer to "which column class does this Python type mean here".

This is the **column** half of the column-type protocol (the DataType half is
:meth:`MariaDBDialect.suggested_data_types`), and it answers a different
question from storage. A column class says what a value can *do*; how it is
stored is the DDL layer's separate decision. That separation is why MariaDB's
one famous divergence from MySQL does not show up in this table at all -- see
the ``dict`` entry below.

The table answers all 18 entries of the framework's common Python types,
because an entry left out is indistinguishable from one nobody thought about,
and only the first of those is actionable. Where MariaDB genuinely has no
column class for an entry the answer is ``None`` -- the last resort, and the
one that makes a refusal distinguishable from an oversight -- which resolution
turns into a definition-time failure naming ``UseColumnType``.

**MariaDB is not MySQL; the facts below are not translatable between them.**

* ``JSON`` is **not** a native type here. It is an alias for
  ``LONGTEXT COLLATE utf8mb4_bin``, and from 10.4.3 the server silently adds
  ``CHECK (json_valid(...))`` to it. Measured across nine wired servers
  (10.2.44 through 13.1.1): ``information_schema.COLUMNS.COLUMN_TYPE`` always
  reads back ``longtext``, never ``json`` -- see
  ``secondary-gaps-investigation.md`` §2 R5 and §5 item 5. The *column* answer
  is still :class:`JSONColumn`, because a column class is about operations and
  MariaDB's JSON function family is real; which storage word carries it is
  :meth:`MariaDBDialect.suggested_data_types`'s business, and a table here
  naming ``LONGTEXT`` instead would be answering a question nobody asked.
* ``UUID`` **is** native from 10.7 (MySQL has no UUID type at all and
  substitutes ``BINARY(16)``). That difference lives entirely on the storage
  side: the column answer is :class:`UUIDColumn` either way, because a UUID
  carries the same operations -- equality and ``IN`` -- wherever it lives. The
  10.7 gate is therefore deliberately **absent** from this table; putting it
  here would make the column class flip on a storage fact, which is the exact
  confusion the two-layer split exists to prevent.
* ``YEAR(2)``, ``ZEROFILL``, display widths and ``REF_SYSTEM_ID`` differ from
  MySQL too, but none of them reaches this table: they are all storage-word
  facts with no operation surface.

Evidence for the version gates is in ``.claude/plan/2026-10-08/``
(``suggested-pairing-json.md`` §"发现" item 7, ``suggested-pairing-array.md``
§"发现" item 5, and this repository's ``secondary-gaps-investigation.md``
§5), all of it measured against live servers rather than read off a manual.
"""

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.dialect.mixins.column_type import (
    ColumnTypeMixin,
)
from rhosocial.activerecord.backend.expression.column_types import (
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    TimestampColumn,
    UUIDColumn,
)

from .backend import MARIADB_VERSION_BOUNDARIES

#: MariaDB's complete answer for every entry of the framework's common types.
#:
#: The three entries where the measurement says more than the portable
#: baseline does:
#:
#: ``float`` / ``decimal.Decimal``
#:     :class:`NumericColumn`. MariaDB stores ``FLOAT`` and ``DECIMAL`` as
#:     distinct types and their arithmetic differs (a ``DECIMAL`` is exact, a
#:     ``FLOAT`` is not), so the two were once named by two column classes.
#:     The framework now carries one numeric column class, which is the honest
#:     description of the *operations* -- comparison and arithmetic are the
#:     same either way -- while the exactness the two storage types differ in
#:     is a value-layer and DataType concern, not an operation surface.
#:
#: ``dict`` / ``list`` / ``tuple`` / ``set`` / ``frozenset``
#:     :class:`JSONColumn`, all five. MariaDB implements **no array type at
#:     all** -- SQL:2016 arrays are a constructed type MariaDB does not
#:     provide, so a column cannot be declared ``INT[]``. The operations
#:     those values can carry (length, element access, containment,
#:     whole-column equality) are all reachable through the JSON path
#:     family, which is measured working from 10.5, so
#:     :class:`~...column_types.ArrayColumn` -- whose whole surface is
#:     ``array_length`` / ``unnest`` over a *native* array -- would name
#:     operations this server answers by refusing.
#:     ``MariaDBArrayMixin`` already says as much in its own error:
#:     "MariaDB does not support native array types. Use JSON arrays
#:     instead."
#:
#: ``datetime.timedelta``
#:     :class:`NumericColumn`. ``INTERVAL`` on MariaDB is an *expression*
#:     keyword (``INTERVAL 1 DAY`` inside ``DATE_ADD``) and never a column
#:     type, so a span has to be stored as a number of seconds or as its
#:     character form. PostgreSQL and Oracle have a real interval column
#:     type and are answered differently; there is no ``IntervalColumn``
#:     class, so this is the same honest answer the portable baseline gives,
#:     reached here from measurement rather than by default.
#:
#: ``uuid.UUID``
#:     :class:`UUIDColumn` on **every** supported version, including those
#:     below 10.7 where the server has no UUID type. MariaDB's native UUID
#:     from 10.7 (``secondary-gaps-investigation.md`` §2 R1; measured:
#:     10.6.28 rejects ``UUID`` with errno 4161, 11.4.13 and later accept
#:     it) changes what the column is *stored as* and nothing about what it
#:     can do, so gating it here would move the answer for a storage
#:     reason. Compare MySQL, which has no UUID type on any version.
MARIADB_COLUMN_TYPES: Dict[Any, Type[ColumnBase]] = {
    bool: BooleanColumn,
    int: IntegerColumn,
    float: NumericColumn,
    decimal.Decimal: NumericColumn,
    str: StringColumn,
    bytes: BinaryColumn,
    bytearray: BinaryColumn,
    datetime.date: TimestampColumn,
    datetime.time: TimestampColumn,
    datetime.datetime: TimestampColumn,
    datetime.timedelta: NumericColumn,
    uuid.UUID: UUIDColumn,
    dict: JSONColumn,
    list: JSONColumn,
    tuple: JSONColumn,
    set: JSONColumn,
    frozenset: JSONColumn,
    enum.Enum: StringColumn,
}


class MariaDBColumnTypeMixin(ColumnTypeMixin):
    """MariaDB's full 18-entry column-type table, and its narrowing.

    Composed into :class:`~...dialect.MariaDBDialect` ahead of core's mixins,
    so its :meth:`suggested_column_types` is the one a model layer reaches.

    The table is a class attribute because it does not vary by version, with
    the one exception (:meth:`suggested_column_types` below) handled by
    building a copy rather than mutating the shared dict -- that method returns
    a copy precisely so a per-version answer cannot leak into the next dialect
    built at a different version.
    """

    def suggested_column_types(self) -> Dict[Any, Optional[Type[ColumnBase]]]:
        """The table above, with ``dict`` refused below MariaDB 10.2.

        The one version-dependent entry, and it is a refusal rather than a
        different class:

        * **Below 10.2** MariaDB has no JSON *functions* at all -- neither
          ``JSON_EXTRACT``, ``JSON_VALID`` nor ``JSON_OBJECT``. What it has is
          the ``JSON`` keyword as a plain ``LONGTEXT`` alias, so a value would
          bind and read back as text while every operation a
          :class:`~...column_types.JSONColumn` offers (``json_path``,
          ``json_value``, the key/validity family) failed at the server. That
          is precisely the silent degradation the protocol forbids: a default
          that renders SQL the server rejects, with the error pointing at the
          column rather than at the annotation that asked for it. The honest
          answer is therefore ``None``, which fails at model definition and
          points the author at ``UseColumnType``.

          The boundary is the existing ``JSON_FUNCTIONS`` entry of
          :data:`MARIADB_VERSION_BOUNDARIES` (10.2.3), not a number written
          here, so the gate and the JSON mixin's own ``supports_json_type`` /
          ``supports_json_function`` cannot drift apart. Measured bracket:
          10.6.28 and 13.1.1 both pass the whole JSON family
          (``suggested-pairing-json.md`` table A rows ``mariadb10.6`` /
          ``mariadb13.1``, and §"发现" item 7 lists the gate set). No server
          below 10.2 is wired, so the *low* side of this gate rests on the
          documented 10.2.3 arrival of the functions rather than on a probe --
          which is the same evidence the JSON mixin itself already relies on.

        * **10.2 and above** :class:`~...column_types.JSONColumn`. Note what
          is *not* gated here: neither the ``->`` / ``->>`` operators (native
          only from 13.1, and this backend renders ``JSON_EXTRACT`` instead,
          which works on every version) nor ``JSON_EQUALS`` (13.1+). Those are
          *operation* facts, owned by the JSON mixin's own capability probes,
          where a caller can ask about one operation instead of losing the
          whole column class over it.

        The containers (``list`` / ``tuple`` / ``set`` / ``frozenset``) keep
        their :class:`~...column_types.JSONColumn` answer below 10.2 as well.
        The 10.2 gate exists because the JSON function family is what
        ``JSONColumn`` offers; an array of primitives carried as JSON text
        still has length and containment to lose, and refusing five entries to
        protect one would be a wider refusal than the measurement supports.
        """
        table: Dict[Any, Optional[Type[ColumnBase]]] = dict(MARIADB_COLUMN_TYPES)

        if self.version < MARIADB_VERSION_BOUNDARIES["JSON_FUNCTIONS"]:
            # No JSON function family exists below 10.2 (see above), so no
            # column class can keep the promise a `dict` value needs: the
            # last-resort `None`, not a class that silently degrades.
            table[dict] = None

        return table


__all__ = ["MARIADB_COLUMN_TYPES", "MariaDBColumnTypeMixin"]
