# src/rhosocial/activerecord/backend/impl/mariadb/mixins/column_suggestion.py
"""MariaDB's answer to "which column class does this Python type mean here".

This is the **column** half of the suggestion protocol (the DataType half is
:meth:`MariaDBDialect.suggested_data_types`), and it answers a different
question from storage. A column class says what a value can *do*; how it is
stored is the DDL layer's separate decision. That separation is why MariaDB's
one famous divergence from MySQL does not show up in this table at all -- see
the ``dict`` entry below.

The table answers all 18 entries of
:data:`~rhosocial.activerecord.backend.expression.column_suggestions.COLUMN_TYPE_ENTRIES`,
because an entry left out is indistinguishable from one nobody thought about,
and only the first of those is actionable. Where MariaDB genuinely has no
column class for an entry the answer is
:data:`~rhosocial.activerecord.backend.expression.column_suggestions.UNSUPPORTED`,
which resolution turns into a definition-time failure naming ``UseColumnType``.

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
from typing import Any, Dict, Type

from rhosocial.activerecord.backend.dialect.mixins.column_suggestion import (
    ColumnSuggestionMixin,
)
from rhosocial.activerecord.backend.expression.column_suggestions import UNSUPPORTED
from rhosocial.activerecord.backend.expression.column_types import (
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    DateTimeColumn,
    DecimalColumn,
    FloatColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)

from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBColumnSuggestionMixin(ColumnSuggestionMixin):
    """MariaDB's full 18-entry column suggestion table, and its narrowing.

    Composed into :class:`~...dialect.MariaDBDialect` ahead of core's mixins,
    so its :meth:`suggested_column_types` and :meth:`supports_column_operation`
    are the ones a model layer reaches.

    The table is a class attribute because it does not vary by version, with
    the one exception (:meth:`suggested_column_types` below) handled by
    building a copy rather than mutating the shared dict -- that method returns
    a copy precisely so a per-version answer cannot leak into the next dialect
    built at a different version.
    """

    #: MariaDB's complete answer for every entry of ``COLUMN_TYPE_ENTRIES``.
    #:
    #: Only three entries differ from core's neutral baseline, and each differs
    #: for a reason this server's own behaviour supplies:
    #:
    #: ``float`` / ``decimal.Decimal``
    #:     :class:`FloatColumn` / :class:`DecimalColumn`, where core's neutral
    #:     table still says ``NumericColumn`` for both. MariaDB stores ``FLOAT``
    #:     and ``DECIMAL`` as distinct types and their arithmetic differs (a
    #:     ``DECIMAL`` is exact, a ``FLOAT`` is not), so a column class that
    #:     cannot tell them apart is not describing this server's surface.
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
    #:     class yet, so this is the same honest answer core's baseline gives,
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
    COLUMN_TYPE_SUGGESTIONS: Dict[Any, Type[ColumnBase]] = {
        bool: BooleanColumn,
        int: IntegerColumn,
        float: FloatColumn,
        decimal.Decimal: DecimalColumn,
        str: StringColumn,
        bytes: BinaryColumn,
        bytearray: BinaryColumn,
        datetime.date: DateTimeColumn,
        datetime.time: DateTimeColumn,
        datetime.datetime: DateTimeColumn,
        datetime.timedelta: NumericColumn,
        uuid.UUID: UUIDColumn,
        dict: JSONColumn,
        list: JSONColumn,
        tuple: JSONColumn,
        set: JSONColumn,
        frozenset: JSONColumn,
        enum.Enum: StringColumn,
    }

    def suggested_column_types(self) -> Dict[Any, Type[ColumnBase]]:
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
          answer is therefore ``UNSUPPORTED``, which fails at model definition
          and points the author at ``UseColumnType``.

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
          *operation* facts, so they belong in
          :meth:`supports_column_operation`, where a caller can ask about one
          operation instead of losing the whole column class over it.

        The containers (``list`` / ``tuple`` / ``set`` / ``frozenset``) keep
        their :class:`~...column_types.JSONColumn` answer below 10.2 as well.
        The 10.2 gate exists because the JSON function family is what
        ``JSONColumn`` offers; an array of primitives carried as JSON text
        still has length and containment to lose, and refusing five entries to
        protect one would be a wider refusal than the measurement supports.
        """
        table = dict(self.COLUMN_TYPE_SUGGESTIONS)

        if self.version < MARIADB_VERSION_BOUNDARIES["JSON_FUNCTIONS"]:
            table[dict] = UNSUPPORTED

        return table

    def supports_column_operation(self, column_name: str, op: str) -> bool:
        """Whether ``op`` works on ``column_name`` on this MariaDB, at this version.

        Everything core's operation set offers is available except the pairs
        measured to fail. The narrowing is at the ``(column class, operation)``
        grain because that is the grain of the question: MariaDB cannot ``ilike``
        a string, but it can still add two integers, and answering at the
        operation level alone would over-refuse every other column.

        The pairs, each with the measurement behind it:

        ``("StringColumn", "ilike")`` -- **always False**
            MariaDB has no ``ILIKE`` operator on any version (the only two
            backends with one are PostgreSQL and ClickHouse; see
            ``suggested-mappings.md`` §8.1). The dialect already says so
            through ``supports_ilike()`` returning False and
            ``format_ilike_expression`` raising -- this records the same fact
            at the protocol's grain, so the pairing check reads it from one
            place. The default ``utf8mb4_general_ci`` collation already makes
            ``LIKE`` case-insensitive for ASCII, which is why this is a
            narrowing rather than a capability loss worth a version gate.

        ``("JSONColumn", "unnest")`` and ``("JSONColumn", "json_table")`` --
            **False below 10.6**
            Both name the same server fact: on MariaDB, expanding a JSON array
            into rows is ``JSON_TABLE``, which arrived in **10.6**
            (``MARIADB_VERSION_BOUNDARIES['JSON_TABLE']``, matching
            ``MariaDBJSONMixin.supports_json_table``). Measured: 10.5.29 has no
            ``JSON_TABLE`` at all; 11.4.13 and 13.1.1 both have it
            (``suggested-pairing-array.md`` table B, rows
            ``MariaDB 10.5.29`` and ``MariaDB 11.4 / 13.1``, and §"发现"
            item 5). The boundary is read from the boundary table rather than
            written here so the column-level answer and the expression-level
            one cannot disagree.

            This is where a summary table and the measurement part company, and
            the measurement wins: ``column-suggestion-protocol.md`` §12 pairs
            ``unnest`` with the 13 gate, but the same plan's array pairing
            report measures ``unnest`` working on **11.4** with ``JSON_TABLE``
            and failing only on 10.5. The 10.6 gate is what the servers say.
            It is also the conservative direction: over-declaring an operation
            as available hides an incompatibility, while under-declaring
            refuses a query that works, and §5 of the protocol puts the burden
            of proof on the narrowing.

        ``("JSONColumn", "json_equal")`` -- **False below 13.1**
            JSON-semantic whole-column equality is ``JSON_EQUALS`` on MariaDB,
            and it arrived with the native ``->`` / ``->>`` operators in
            **13.1** (``MARIADB_VERSION_BOUNDARIES['JSON_ARROW_NATIVE']``).
            Measured: 10.6.28 reports ``JSON_EQUALS does not exist``;
            13.1.1 accepts it (``suggested-pairing-json.md`` table B, rows
            ``mariadb10.6`` / ``mariadb13.1``, and §"发现" item 4).

            Below 13.1 the only whole-column equality available is **text**
            equality -- a different operation with different semantics, and on
            this backend a *correct* one, because MariaDB's JSON is a
            ``LONGTEXT`` alias the server does not normalise, so byte-for-byte
            comparison is not the silent-mismatch trap it is on native-JSON
            servers. That trap is MySQL 5.7/8.0, whose JSON columns normalise
            whitespace and key order, so a bound parameter silently matches
            nothing (``suggested-mappings.md`` §8.3 row 2). Hence the split
            rather than a blanket refusal: ``json_equal`` is unavailable, plain
            equality is not.
        """
        if column_name == "StringColumn" and op == "ilike":
            return False

        if column_name == "JSONColumn":
            if op in ("unnest", "json_table"):
                return self.version >= MARIADB_VERSION_BOUNDARIES["JSON_TABLE"]
            if op == "json_equal":
                return self.version >= MARIADB_VERSION_BOUNDARIES["JSON_ARROW_NATIVE"]

        return True


__all__ = ["MariaDBColumnSuggestionMixin"]