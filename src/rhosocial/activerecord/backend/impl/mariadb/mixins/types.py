# src/rhosocial/activerecord/backend/impl/mariadb/mixins/types.py
"""MariaDB DataType formatting mixin (parsing is introspection-only)."""

from __future__ import annotations

import re
import warnings
from typing import Optional, Tuple

from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.protocols import DataTypeSupport
from .backend import MARIADB_VERSION_BOUNDARIES
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    CustomType,
    DataType,
    EnumType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    JsonBType,
    JsonType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    UUIDType,
    VarCharType,
)
from ..expression.types import (
    MariaDBBigIntType,
    MariaDBBinaryType,
    MariaDBBitType,
    MariaDBBlobType,
    MariaDBEnumType,
    MariaDBGeometryCollectionType,
    MariaDBGeometryType,
    MariaDBIntType,
    MariaDBLineStringType,
    MariaDBLongBlobType,
    MariaDBLongTextType,
    MariaDBMediumBlobType,
    MariaDBMediumIntType,
    MariaDBMediumTextType,
    MariaDBMultiLineStringType,
    MariaDBMultiPointType,
    MariaDBMultiPolygonType,
    MariaDBPointType,
    MariaDBPolygonType,
    MariaDBSetType,
    MariaDBSmallIntType,
    MariaDBTextType,
    MariaDBTinyBlobType,
    MariaDBTinyIntType,
    MariaDBTinyTextType,
    MariaDBUUIDType,
    MariaDBVarBinaryType,
    MariaDBXmlType,
    MariaDBYearType,
)


class MariaDBTypeSupportMixin(DataTypeMixin, DataTypeSupport):
    """MariaDB DataType formatting and parsing.

    Implements ``DataTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings. Reading raw type strings back is a separate,
    introspection-only concern handled by ``introspection.type_parser``.

    Formatting dispatches by the type instance's ``name`` through the
    naming-convention ``format_data_type_<name>`` methods (see
    ``DataTypeMixin``). MariaDB-specific types carry ``mariadb_``-prefixed
    names; core types render their real MariaDB SQL.

    Two policies run through this file and are worth stating once here:

    * **Spelling.** A core concept that has several spellings declares them as
      a closed ``SPELLINGS`` list, and this mixin says which of them MariaDB
      renders. A spelling MariaDB does not write is refused by
      ``_check_spelling`` with a message naming it; one it does write is
      normalised to MariaDB's own word. See the note above
      :meth:`_validate_fsp`.
    * **Correspondence.** Every core concept is declared — rendered here, or
      named in ``MariaDBDialect.suggest_data_types()`` as what MariaDB stores
      instead. Silence would leave a caller told only "unsupported", which is
      indistinguishable from the concept never having been considered.
    """

    # ------------------------------------------------------------------
    # DataTypeSupport — formatting
    # ------------------------------------------------------------------

    # How this dialect spells a concept
    # ---------------------------------
    # MariaDB writes a narrow set of type words, and the ones it does *not*
    # write are refused rather than quietly rewritten. ``CHARACTER VARYING``,
    # ``CLOB``, ``BYTEA``, ``INT1``/``INT2``/``INT8`` are all real SQL, and all
    # of them are words MariaDB's own DDL grammar does not use — accepting them
    # here would be claiming MariaDB spells a type it does not, and rejecting
    # them with no message would turn an explicit request into a different type
    # without saying so. The concepts themselves are still usable: the *default*
    # spelling always renders on every concept below, which is the property that
    # keeps ``IntegerType(dialect)`` and friends working unchanged.
    #
    # Where MariaDB accepts a spelling but has a shorter form of its own, the
    # formatter **normalises** to MariaDB's word rather than echoing the
    # spelling back: ``INT`` is what ``SHOW CREATE TABLE`` reports for the
    # 4-byte signed integer, so rendering ``INTEGER`` for ``spelling="integer"``
    # would make every round-trip through introspection report a difference that
    # does not exist. ``NUMERIC``/``DEC`` and ``DOUBLE PRECISION`` are the same
    # story. Only PostgreSQL gets ``DOUBLE PRECISION`` echoed back, because
    # PostgreSQL is what reports it.

    def _validate_fsp(self, label: str, precision: Optional[int]) -> None:
        """Validate fractional-seconds precision (MariaDB range 0-6)."""
        if precision is not None and not 0 <= precision <= 6:
            raise ValueError(
                f"MariaDB {label} fractional seconds precision must be "
                f"between 0 and 6, got {precision}."
            )

    # --- MariaDB-specific type formatters (dispatch key = type name) ---

    def _format_mariadb_integer(self, sql: str, data_type: DataType) -> Tuple[str, tuple]:
        """Append the ``UNSIGNED`` / ``ZEROFILL`` attributes in MariaDB's order.

        One attribute slot for the whole numeric family -- the four integer
        widths and the four exact/approximate numerics -- so every numeric
        formatter on this dialect routes through here rather than writing its
        own copy of the rule. The name is the historical one and stays: it is
        what the four ``:meth:`` references above ``format_data_type_mariadb_int``
        point at, and renaming it would break them for nothing.

        MariaDB's "Numeric Data Type Overview" gives the pair one grammar for all
        of them -- ``TYPE[(M)] [SIGNED | UNSIGNED | ZEROFILL]`` -- with the
        per-type pages filling in the argument list (``DECIMAL[(M[,D])]``,
        ``FLOAT[(M,D)]``, ``DOUBLE[(M,D)]``, ``DOUBLE PRECISION[(M,D)]``,
        ``REAL[(M,D)]``), so ``UNSIGNED`` goes **after** the ``(M[,D])`` group in
        every case. That is also the order the server writes back into
        ``COLUMN_TYPE``: measured on all fifteen wired servers, 10.2.44 through
        13.1.1, which agree byte for byte --
        ``decimal(10,2) unsigned``, ``float(10,2) unsigned``,
        ``double(10,2) unsigned`` and ``double unsigned`` for ``REAL UNSIGNED``.

        **There are three reachable outputs, not four**, and which three is the
        server's decision rather than the caller's:

        ========================  ===================  ==========================
        declaration               emitted             column the server creates
        ========================  ===================  ==========================
        ``X``                     ``X``               signed, unpadded
        ``X UNSIGNED``            ``X UNSIGNED``      unsigned, unpadded
        ``X ZEROFILL``            ``X UNSIGNED ZEROFILL``  unsigned, padded
        ``X UNSIGNED ZEROFILL``   ``X UNSIGNED ZEROFILL``  unsigned, padded
        ========================  ===================  ==========================

        The last two rows are one row. MariaDB's own overview says "If
        ``ZEROFILL`` is specified, the column will be set to ``UNSIGNED``", the
        ``INT`` page says "A special type of ``INT UNSIGNED`` is ``INT
        ZEROFILL``", and that is what the server does: ``CREATE TABLE t (c INT
        ZEROFILL)`` reports ``int(10) unsigned zerofill`` on all fifteen wired
        servers (10.2.44 through 13.1.1), byte for byte what
        ``INT UNSIGNED ZEROFILL`` reports, and neither accepts ``-1``. So there
        is no ``(unsigned=False, zerofill=True)`` column for this formatter to
        emit, and ``_format_mariadb_integer`` therefore only has to read one
        flag to know that ``UNSIGNED`` is needed.

        That flag is read, not recomputed, because the five
        :class:`~...expression.types.MariaDB*IntType` constructors already
        normalised the pair at construction — see ``_zerofill_signedness`` in
        ``expression/types.py``, where the documentation and the measurements
        live. By the time anything reaches this function,
        ``data_type.unsigned`` is already ``True`` for every declaration that
        asks to be zero-padded, and it is ``True`` because that is the column
        MariaDB is about to build.

        **The shape is judged before the value is read.** The expressions
        collect ``unsigned`` without judging it — a value is not a wrong value
        until a backend has to honour it, and this is the backend that has to,
        so the non-bool arrives here rather than being refused at construction.
        But ``UNSIGNED`` here is a *modifier* in the rendered DDL, and a truthy
        string would render as one silently: ``unsigned="yes"`` would write
        ``INT UNSIGNED`` and report success for a column nobody asked for, the
        same silent loss the three-row table above is written to prevent. So the
        shape is named, not guessed at.

        **``ZEROFILL`` reaches only the integer widths.** It is a MariaDB display
        attribute with no field on the exact/approximate concepts — core's
        ``FloatType`` carries ``precision`` and ``unsigned`` and nothing else,
        ``DecimalType`` carries ``precision``, ``scale`` and ``unsigned`` — and
        that is exactly the same reason MariaDB's own integer classes exist for
        it. The ``getattr`` below is what lets one method serve both families
        honestly instead of giving the four numerics a second, near-identical
        attribute rule that could drift from this one. The three-row table above
        is therefore reachable only through the integer widths, and the four
        numerics reach its first two rows.

        **This is MariaDB normalising the column, not the caller changing their
        mind.** A formatter that emitted ``X ZEROFILL`` here would write DDL
        whose stored range contradicts the declaration and whose text does not
        contain the word the backend's introspection parser reads ``unsigned``
        from, handing back a different value object than the caller declared and
        making the differ report a change nobody made. Emitting what will
        actually be stored is the honest output, and it is what keeps the
        parser's round-trip ``parse(format_data_type(t)[0]) == t`` true for every
        combination of width, signedness and zerofill.

        ``unsigned`` alone is honoured because it is a real, storable range
        change: ``INT`` and ``INT UNSIGNED`` are two different columns
        (``int(11)`` vs ``int(10) unsigned``, and the first stores ``-1`` while
        the second does not), and ``unsigned`` is in ``PARAMETERS`` so the
        differ sees it change.

        Args:
            sql: The bare type word, e.g. ``"MEDIUMINT"``.
            data_type: The declared type, read for ``unsigned`` and ``zerofill``.

        Returns:
            ``(sql, ())`` — the type word plus whatever attributes apply. Both
            attributes are column modifiers, never bound parameters.

        Raises:
            TypeError: if ``unsigned`` is not a ``bool`` — it becomes a type
                modifier in the rendered DDL, so a truthy non-bool would render
                ``UNSIGNED`` and report success.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        # Direct read, not ``getattr(..., False)``: the field is on every concept
        # routed through here, and probing for it would turn a caller passing the
        # wrong class into the same silent render this guard exists to prevent.
        # What arrives is what ``__init__`` normalised to, so a ``zerofill``
        # declaration shows up as the ``True`` that column actually is.
        unsigned = data_type.unsigned
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        if unsigned:
            sql = f"{sql} UNSIGNED"
        # ``getattr`` rather than a direct read: this helper serves both
        # MariaDB's own width classes, which carry ``zerofill``, and the core
        # concepts — the four integer widths and the four exact/approximate
        # numerics — which do not.  ``zerofill`` is a MariaDB display attribute,
        # not part of any of those concepts, so they must not be given a field
        # for it just to satisfy this function.  The branch therefore never runs
        # for them and a core ``IntegerType`` renders ``INT`` or ``INT UNSIGNED``
        # — and a core ``DecimalType`` ``DECIMAL(10, 2)`` or ``DECIMAL(10, 2)
        # UNSIGNED`` — exactly as the grammar says.
        if getattr(data_type, "zerofill", False):
            sql = f"{sql} ZEROFILL"
        return sql, ()

    def format_data_type_mariadb_tinyint(self, expr: MariaDBTinyIntType) -> Tuple[str, tuple]:
        """``TINYINT`` — 1 byte, ``-128``..``127`` signed / ``0``..``255``
        unsigned, with MariaDB's own two attributes.

        Spelled ``TINYINT`` and rendered that way because that is what the
        catalog reports: MariaDB rewrites MariaDB's own ``INT1`` synonym to
        ``tinyint(4)`` (verified), so echoing the synonym back would make an
        introspected column differ from its own declaration.
        """
        return self._format_mariadb_integer("TINYINT", expr)

    def format_data_type_mariadb_smallint(self, expr: MariaDBSmallIntType) -> Tuple[str, tuple]:
        """``SMALLINT`` — 2 bytes, ``-32768``..``32767`` / ``0``..``65535``."""
        return self._format_mariadb_integer("SMALLINT", expr)

    def format_data_type_mariadb_mediumint(self, expr: MariaDBMediumIntType) -> Tuple[str, tuple]:
        """``MEDIUMINT`` — 3 bytes, ``-8388608``..``8388607`` / ``0``..``16777215``.

        MariaDB spells this width with two words, ``MEDIUMINT`` and its
        documented synonym ``INT3``, so both are accepted and ``MEDIUMINT`` is
        rendered — the form the server itself writes into ``COLUMN_TYPE``, which
        is what lets the backend's introspection parser read its own output back.
        """
        self._check_spelling(expr, MariaDBMediumIntType)
        return self._format_mariadb_integer("MEDIUMINT", expr)

    def format_data_type_mariadb_int(self, expr: MariaDBIntType) -> Tuple[str, tuple]:
        """``INT`` — 4 bytes, ``-2147483648``..``2147483647`` / ``0``..``4294967295``."""
        return self._format_mariadb_integer("INT", expr)

    def format_data_type_mariadb_bigint(self, expr: MariaDBBigIntType) -> Tuple[str, tuple]:
        """``BIGINT`` — 8 bytes, the full signed and unsigned 64-bit ranges."""
        return self._format_mariadb_integer("BIGINT", expr)

    def format_data_type_mariadb_tinyblob(self, expr: MariaDBTinyBlobType) -> Tuple[str, tuple]:
        return "TINYBLOB", ()

    def format_data_type_mariadb_blob(self, expr: MariaDBBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def format_data_type_mariadb_mediumblob(self, expr: MariaDBMediumBlobType) -> Tuple[str, tuple]:
        return "MEDIUMBLOB", ()

    def format_data_type_mariadb_longblob(self, expr: MariaDBLongBlobType) -> Tuple[str, tuple]:
        return "LONGBLOB", ()

    def format_data_type_mariadb_tinytext(self, expr: MariaDBTinyTextType) -> Tuple[str, tuple]:
        return "TINYTEXT", ()

    def format_data_type_mariadb_text(self, expr: MariaDBTextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_mariadb_mediumtext(self, expr: MariaDBMediumTextType) -> Tuple[str, tuple]:
        return "MEDIUMTEXT", ()

    def format_data_type_mariadb_longtext(self, expr: MariaDBLongTextType) -> Tuple[str, tuple]:
        return "LONGTEXT", ()

    def format_data_type_mariadb_bit(self, expr: MariaDBBitType) -> Tuple[str, tuple]:
        if expr.n is not None:
            return f"BIT({expr.n})", ()
        return "BIT", ()

    def format_data_type_mariadb_year(self, expr: MariaDBYearType) -> Tuple[str, tuple]:
        if expr.display_width is not None:
            return f"YEAR({expr.display_width})", ()
        return "YEAR", ()

    def format_data_type_mariadb_binary(self, expr: MariaDBBinaryType) -> Tuple[str, tuple]:
        if expr.length is not None:
            return f"BINARY({expr.length})", ()
        return "BINARY", ()

    def format_data_type_mariadb_uuid(self, expr: MariaDBUUIDType) -> Tuple[str, tuple]:
        """``UUID`` — MariaDB's native type, available from 10.7.

        Not ``BINARY(16)``: the native type stores values byte-swapped so UUIDv1
        ordering is index-friendly, and it rejects ``UUID_SHORT()`` and braces.
        A 16-byte binary column is a different column and is built with
        :class:`~...expression.types.MariaDBBinaryType`.

        Raises:
            UnsupportedFeatureError: below 10.7 there is no UUID type, and
                silently emitting ``BINARY(16)`` instead would produce a column
                that behaves nothing like the one that was asked for.
        """
        if self.version < MARIADB_VERSION_BOUNDARIES["UUID"]:
            floor = ".".join(map(str, MARIADB_VERSION_BOUNDARIES["UUID"]))
            have = ".".join(map(str, self.version))
            raise UnsupportedFeatureError(
                self.name,
                "the UUID data type",
                f"it arrived in MariaDB {floor} and this server is {have}. "
                f"On an older server a UUID is emulated as a 16-byte BINARY "
                f"column, which is a different column: build "
                f"MariaDBBinaryType(length=16) for that deliberately rather "
                f"than getting it by asking for a UUID.",
            )
        return "UUID", ()

    def format_data_type_mariadb_xml(self, expr: MariaDBXmlType) -> Tuple[str, tuple]:
        """``XMLTYPE`` — MariaDB's native XML column type, available from 12.3.

        Not ``TEXT``, which is what this backend substituted before 12.3 and
        still does on an older server. The two are different columns: ``TEXT``
        takes a length and has no 4 GB ceiling or XML semantics, while
        ``XMLTYPE`` is documented as "basic XML storage capabilities only,
        without validation" capped at "4GB (same as ``LONGBLOB``)", and it takes
        no length at all. Emitting ``TEXT`` for a request for ``XMLTYPE`` would
        hand back a column that cannot hold what was asked for.

        No parameters are rendered because MariaDB refuses them: a length
        specification is an error ("Data type 'XMLTYPE' doesn't support LENGTH
        attribute"), so an XML Schema association stays a column or domain
        attribute, as it is on every backend.

        Raises:
            UnsupportedFeatureError: below 12.3 there is no ``XMLTYPE`` at all.
                Answering with ``TEXT`` instead would silently produce a
                different column, so the caller is told the version and pointed
                at ``TextType`` — the substitute ``suggest_data_types()``
                reports for an older server.
        """
        if self.version < MARIADB_VERSION_BOUNDARIES["XMLTYPE"]:
            floor = ".".join(map(str, MARIADB_VERSION_BOUNDARIES["XMLTYPE"]))
            have = ".".join(map(str, self.version))
            raise UnsupportedFeatureError(
                self.name,
                "the XMLTYPE data type",
                f"it arrived in MariaDB {floor} and this server is {have}. "
                f"On an older server an XML document is stored as TEXT, which "
                f"is a different column: build TextType for that deliberately "
                f"rather than getting it by asking for XMLTYPE.",
            )
        return "XMLTYPE", ()

    def format_data_type_mariadb_varbinary(self, expr: MariaDBVarBinaryType) -> Tuple[str, tuple]:
        if expr.length is not None:
            return f"VARBINARY({expr.length})", ()
        return "VARBINARY", ()

    def format_data_type_enum(self, expr: EnumType) -> Tuple[str, tuple]:
        """Render the core ``EnumType``.

        MariaDB has a native ENUM, so the generic type is renderable here
        rather than something to substitute. ``MariaDBEnumType`` stays for the
        cases that need the charset and collation this form does not carry.
        """
        values_str = ",".join(self.format_literal(value) for value in expr.values)
        return f"ENUM({values_str})", ()

    def format_data_type_mariadb_enum(self, expr: MariaDBEnumType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in expr.values)
        result = f"ENUM({values_str})"
        if expr.charset:
            result += f" CHARACTER SET {expr.charset}"
        if expr.collation:
            result += f" COLLATE {expr.collation}"
        return result, ()

    def format_data_type_mariadb_set(self, expr: MariaDBSetType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in expr.values)
        result = f"SET({values_str})"
        if expr.charset:
            result += f" CHARACTER SET {expr.charset}"
        if expr.collation:
            result += f" COLLATE {expr.collation}"
        return result, ()

    def _format_mariadb_spatial(self, sql: str, data_type: MariaDBGeometryType) -> Tuple[str, tuple]:
        """Append the ``REF_SYSTEM_ID`` attribute to a spatial type word.

        MariaDB spells the declaration ``REF_SYSTEM_ID=<n>`` -- the form its
        ``GEOMETRY_COLUMNS`` documentation uses
        (``CREATE TABLE g1 (g GEOMETRY(9,4) REF_SYSTEM_ID=101)``) -- and **not**
        ``SRID <n>``. The latter is MySQL's attribute: every MariaDB server
        measured rejects it with errno 1064 (10.2.44 and 13.1.1 live for this
        change; 10.6.28, 11.4.13, 11.8.9, 12.1.2 and 12.3.3 in the
        typed-columns investigation), so rendering it wrote DDL no server would
        accept. ``REF_SYSTEM_ID=4326`` is accepted by all of them, with and
        without spaces around ``=``; the tight spelling is rendered so the
        output is one string rather than two.

        The declaration is a statement about the column, not a constraint on
        its values: on a column declared ``REF_SYSTEM_ID=4326``, MariaDB stored
        ``ST_GeomFromText('POINT(1 1)')`` with ``ST_SRID`` 0 and an explicit
        3857 value unchanged (measured on 10.2.44 and 13.1.1). It is still a
        real declaration -- MariaDB records it in
        ``I_S.GEOMETRY_COLUMNS.SRID`` and drops it from ``COLUMN_TYPE`` and
        ``SHOW CREATE`` -- so two declarations that differ are two different
        columns to this backend, and ``srid`` is in the classes' ``PARAMETERS``.

        Official Documentation:
        https://mariadb.com/docs/server/reference/system-tables/information-schema/information-schema-tables/information-schema-geometry_columns-table
        """
        if data_type.srid is not None:
            return f"{sql} REF_SYSTEM_ID={data_type.srid}", ()
        return sql, ()

    def format_data_type_mariadb_geometry(self, expr: MariaDBGeometryType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("GEOMETRY", expr)

    def format_data_type_mariadb_point(self, expr: MariaDBPointType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("POINT", expr)

    def format_data_type_mariadb_linestring(self, expr: MariaDBLineStringType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("LINESTRING", expr)

    def format_data_type_mariadb_polygon(self, expr: MariaDBPolygonType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("POLYGON", expr)

    def format_data_type_mariadb_multipoint(self, expr: MariaDBMultiPointType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTIPOINT", expr)

    def format_data_type_mariadb_multilinestring(self, expr: MariaDBMultiLineStringType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTILINESTRING", expr)

    def format_data_type_mariadb_multipolygon(self, expr: MariaDBMultiPolygonType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTIPOLYGON", expr)

    def format_data_type_mariadb_geometrycollection(
        self, expr: MariaDBGeometryCollectionType
    ) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("GEOMETRYCOLLECTION", expr)

    # --- Core types (pure names) rendered to real MariaDB SQL ---

    def format_data_type_integer(self, expr: IntegerType) -> Tuple[str, tuple]:
        """``INT`` / ``INTEGER`` — the 4-byte signed integer.

        Both spellings are accepted because MariaDB accepts both, and its own
        manual documents ``INT`` as the abbreviation of ``INTEGER``. Neither is
        echoed back: MariaDB writes and reports ``INT``, so that is what this
        renders for either — normalising the spelling rather than refusing it,
        so that a column introspected as ``int(11)`` and one declared as
        ``INTEGER`` render alike.

        ``unsigned`` is honoured rather than dropped: MariaDB has unsigned
        integers -- its own numeric-types overview says a ``ZEROFILL`` column
        "will be set to UNSIGNED", and its per-type pages repeat it -- so the
        attribute can be written, and a declared unsigned column rendered as a
        signed one is a different column than the caller asked for. Routed
        through :meth:`_format_mariadb_integer` so the documented
        ``[UNSIGNED] [ZEROFILL]`` order is stated in exactly one place. Core's
        integer concepts carry no ``zerofill`` field: it is a display
        attribute, not part of the concept.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        self._check_spelling(expr, IntegerType)
        return self._format_mariadb_integer("INT", expr)

    def format_data_type_bigint(self, expr: BigIntType) -> Tuple[str, tuple]:
        """``BIGINT`` / ``INT8`` — both accepted, ``BIGINT`` rendered.

        MariaDB's ``BIGINT`` page states plainly that "``INT8`` is a synonym for
        ``BIGINT``", so refusing that spelling would refuse a word the server
        accepts. It is normalised to ``BIGINT`` because that is what MariaDB
        reports back, so a round-trip through the catalog is stable.

        ``unsigned`` is honoured rather than dropped: MariaDB has unsigned
        integers -- its own numeric-types overview says a ``ZEROFILL`` column
        "will be set to UNSIGNED", and its per-type pages repeat it -- so the
        attribute can be written, and a declared unsigned column rendered as a
        signed one is a different column than the caller asked for. Routed
        through :meth:`_format_mariadb_integer` so the documented
        ``[UNSIGNED] [ZEROFILL]`` order is stated in exactly one place. Core's
        integer concepts carry no ``zerofill`` field: it is a display
        attribute, not part of the concept.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        self._check_spelling(expr, BigIntType)
        return self._format_mariadb_integer("BIGINT", expr)

    def format_data_type_smallint(self, expr: SmallIntType) -> Tuple[str, tuple]:
        """``SMALLINT`` / ``INT2`` — both accepted, ``SMALLINT`` rendered.

        MariaDB's ``SMALLINT`` page states that "``INT2`` is a synonym for
        ``SMALLINT``". Normalised rather than refused, because MariaDB reports
        ``SMALLINT`` back.

        ``unsigned`` is honoured rather than dropped: MariaDB has unsigned
        integers -- its own numeric-types overview says a ``ZEROFILL`` column
        "will be set to UNSIGNED", and its per-type pages repeat it -- so the
        attribute can be written, and a declared unsigned column rendered as a
        signed one is a different column than the caller asked for. Routed
        through :meth:`_format_mariadb_integer` so the documented
        ``[UNSIGNED] [ZEROFILL]`` order is stated in exactly one place. Core's
        integer concepts carry no ``zerofill`` field: it is a display
        attribute, not part of the concept.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        self._check_spelling(expr, SmallIntType)
        return self._format_mariadb_integer("SMALLINT", expr)

    def format_data_type_tinyint(self, expr: TinyIntType) -> Tuple[str, tuple]:
        """``TINYINT`` / ``INT1`` — both accepted, ``TINYINT`` rendered.

        MariaDB's ``TINYINT`` page lists "``INT1``, ``BOOL``, and ``BOOLEAN``"
        as synonyms, so all of those words are ones the server accepts.

        Note the deliberate asymmetry with :meth:`format_data_type_boolean`:
        MariaDB stores a boolean as ``TINYINT(1)``, so the introspection parser reads
        ``TINYINT(1)`` back as a :class:`BooleanType`. A bare ``TINYINT`` — no
        display width — is a small integer and stays one.

        ``unsigned`` is honoured rather than dropped: MariaDB has unsigned
        integers -- its own numeric-types overview says a ``ZEROFILL`` column
        "will be set to UNSIGNED", and its per-type pages repeat it -- so the
        attribute can be written, and a declared unsigned column rendered as a
        signed one is a different column than the caller asked for. Routed
        through :meth:`_format_mariadb_integer` so the documented
        ``[UNSIGNED] [ZEROFILL]`` order is stated in exactly one place. Core's
        integer concepts carry no ``zerofill`` field: it is a display
        attribute, not part of the concept.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        self._check_spelling(expr, TinyIntType)
        return self._format_mariadb_integer("TINYINT", expr)

    def format_data_type_varchar(self, expr: VarCharType) -> Tuple[str, tuple]:
        """``VARCHAR`` / ``CHARACTER VARYING`` — both accepted, ``VARCHAR``
        rendered.

        MariaDB's ``VARCHAR`` page says "``VARCHAR`` is shorthand for
        ``CHARACTER VARYING``" and lists ``CHARACTER VARYING`` among the
        synonyms, so both are accepted. The long form is normalised to
        ``VARCHAR`` because that is what MariaDB stores and reports — which is
        also what lets the introspection parser read its own output back as
        ``varchar``.
        """
        self._check_spelling(expr, VarCharType)
        return (f"VARCHAR({expr.length})" if expr.length is not None else "VARCHAR"), ()

    def format_data_type_char(self, expr: CharType) -> Tuple[str, tuple]:
        """``CHAR`` / ``CHARACTER`` — both accepted, ``CHAR`` rendered.

        MariaDB has a ``CHARACTER`` page that says "This is a synonym for
        ``CHAR``", with a worked example whose ``SHOW CREATE TABLE`` output is
        ``char(1)``. ``CHARACTER`` is also the keyword introducing a character
        *set* clause (``CHARACTER SET utf8``), which is a different thing and
        not a reason to refuse the type spelling.
        """
        self._check_spelling(expr, CharType)
        return (f"CHAR({expr.length})" if expr.length is not None else "CHAR"), ()

    def format_data_type_text(self, expr: TextType) -> Tuple[str, tuple]:
        """``TEXT`` only. MariaDB has no ``CLOB`` type — an unbounded string is a
        ``TEXT``, and the four sized ``*TEXT`` variants are this backend's own
        ``mariadb_tinytext``/``mariadb_mediumtext``/``mariadb_longtext`` classes
        rather than spellings of this one, because the maximum length is part of
        what the column can hold."""
        self._check_spelling(expr, ("text",))
        return "TEXT", ()

    def format_data_type_boolean(self, expr: BooleanType) -> Tuple[str, tuple]:
        """MariaDB has no native boolean type: both ``BOOLEAN`` and ``BOOL`` are
        documented synonyms of ``TINYINT``, and the framework writes the
        conventional ``TINYINT(1)`` so that the column's storage width is visible
        in the DDL.

        The width is the reason ``TINYINT(1)`` is not the same declaration as a
        bare ``TINYINT``, which is why :meth:`format_data_type_tinyint` renders
        the latter without one.
        """
        self._check_spelling(expr, BooleanType)
        return "TINYINT(1)", ()

    def format_data_type_date(self, expr: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    def format_data_type_datetime(self, expr: DateTimeType) -> Tuple[str, tuple]:
        self._validate_fsp("DATETIME", expr.precision)
        return (f"DATETIME({expr.precision})" if expr.precision is not None else "DATETIME"), ()

    def format_data_type_time(self, expr: TimeType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", expr.precision)
        return (f"TIME({expr.precision})" if expr.precision is not None else "TIME"), ()

    def format_data_type_timetz(self, expr: TimeTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", expr.precision)
        return (f"TIME({expr.precision})" if expr.precision is not None else "TIME"), ()

    def format_data_type_timestamp(self, expr: TimestampType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", expr.precision)
        return (f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"), ()

    def format_data_type_timestamptz(self, expr: TimestampTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", expr.precision)
        return (f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"), ()

    def format_data_type_float(self, expr: FloatType) -> Tuple[str, tuple]:
        """``FLOAT`` only; ``unsigned`` honoured in MariaDB's documented slot.

        The FLOAT page gives the declaration as ``FLOAT[(M,D)] [SIGNED |
        UNSIGNED | ZEROFILL]`` and says what the attribute does — "``UNSIGNED``,
        if specified, disallows negative values" — so the attribute goes after
        the type word through :meth:`_format_mariadb_integer`, which owns the
        whole attribute slot.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/float

        **``precision`` is refused, because ``FLOAT(p)`` cannot round-trip.**
        *p* is consumed to choose the storage class and is recorded nowhere:
        measured on all fifteen wired servers (10.2.44 through 13.1.1, which
        agree byte for byte), ``CREATE TABLE t (c FLOAT(24))`` reports
        ``COLUMN_TYPE = 'float'`` while ``FLOAT(25)`` and ``FLOAT(53)`` report
        ``'double'``. A declared ``FloatType(precision=24)`` would therefore be
        introspected back as a precision-free ``FloatType``, and
        ``FloatType(precision=53)`` as a ``DoubleType`` — the second is a
        different storage class, not a different spelling of one, and the first
        is a parameter silently gone. The caller is told which class to declare
        for each range instead of being handed a declaration the catalog
        contradicts.

        ``precision=None`` — the bare ``FLOAT`` — round-trips: it renders
        ``FLOAT``, the server stores 4-byte single precision, and the catalog
        reports ``float``. The deprecated two-argument ``FLOAT(M,D)`` is a
        different declaration whose first number is M (total *decimal* digits),
        not p (bits); it is not reachable through this class, whose only
        parameter is a bit precision, and the API does not pretend otherwise.

        **The range does not move, and that does not make ``unsigned``
        decorative.** The overview says so in as many words: "Floating point and
        fixed-point types also can be ``UNSIGNED``, but this only prevents
        negative values from being stored and doesn't alter the range." The
        stored column is still a different column — measured on all fifteen
        wired servers, 10.2.44 through 13.1.1, ``INSERT INTO t (c) VALUES (-1)``
        into a ``FLOAT(10,2)`` column stores it and into ``FLOAT(10,2)
        UNSIGNED`` fails with 1264 "Out of range value for column 'c'" — and
        ``unsigned`` is in ``PARAMETERS``, so the differ has to see the change.

        MariaDB does **not** deprecate this the way MySQL does, and nothing here
        routes around it: the current documented grammar has the attribute in
        that slot.

        :raises ValueError: if ``precision`` is set — see above for the two
            ranges and the class to declare for each.
        """
        if expr.precision is not None:
            raise ValueError(
                "MariaDB cannot round-trip FLOAT(p): the catalog records FLOAT "
                "without p, and p chooses the storage class. p 0..24 creates "
                "single-precision FLOAT storage — declare FloatType(dialect) "
                "with no precision; p 25..53 creates double-precision DOUBLE "
                f"storage — declare DoubleType(dialect). "
                f"Got precision={expr.precision}."
            )
        return self._format_mariadb_integer("FLOAT", expr)

    def format_data_type_double(self, expr: DoubleType) -> Tuple[str, tuple]:
        """``DOUBLE`` — both core spellings accepted, ``unsigned`` honoured
        through :meth:`_format_mariadb_integer`.

        MariaDB documents ``DOUBLE``, ``DOUBLE PRECISION`` and ``REAL`` as the
        same 8-byte float and gives all three the same grammar, ``[(M,D)]
        [SIGNED | UNSIGNED | ZEROFILL]``, adding: "``REAL`` and ``DOUBLE
        PRECISION`` are synonyms, unless the ``REAL_AS_FLOAT`` SQL mode is
        enabled, in which case ``REAL`` is a synonym for FLOAT rather than
        DOUBLE." ``DOUBLE`` and ``DOUBLE PRECISION`` are the two core spellings
        and both are accepted; neither is echoed back — ``DOUBLE`` is what
        MariaDB reports, and rendering the long form would make an introspected
        column differ from its own declaration.

        ``REAL`` is deliberately *not* a third spelling here even though the
        server treats it as one. It is mode-dependent storage — ``DOUBLE``
        normally, ``FLOAT`` under ``REAL_AS_FLOAT`` — and the catalog never
        writes the word ``real`` back (measured on all fifteen wired servers,
        10.2.44 through 13.1.1: a ``REAL`` column reports ``'double'``, or
        ``'float'`` under the mode). A ``RealType`` therefore cannot round-trip,
        so this dialect substitutes it; see
        ``MariaDBDialect.suggest_substitute_advice``.

        ``unsigned`` is honoured through :meth:`_format_mariadb_integer`, in the
        slot that grammar gives it — measured on all fifteen wired servers:
        ``DOUBLE(10,2) UNSIGNED`` reports ``'double(10,2) unsigned'`` and
        rejects ``-1`` with 1264.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/double
        """
        self._check_spelling(expr, DoubleType)
        return self._format_mariadb_integer("DOUBLE", expr)

    def format_data_type_decimal(self, expr: DecimalType) -> Tuple[str, tuple]:
        """``DECIMAL`` — MariaDB's manual states that ``NUMERIC`` and ``DEC`` are
        synonyms of ``DECIMAL``, so all three spellings are accepted and the
        canonical short form is what gets written.

        The precision and scale limits are MariaDB's, not SQL's: at most 65
        digits of precision and 30 of scale, and a scale larger than the
        precision it belongs to is rejected by the server, so it is rejected
        here where the mistake can be attributed. Every one of those three
        ``ValueError`` s is untouched by ``unsigned`` and still fires for a
        signed declaration.

        ``unsigned`` is honoured rather than dropped. The DECIMAL page gives the
        declaration as ``DECIMAL[(M[,D])] [SIGNED | UNSIGNED | ZEROFILL]`` and
        spends a section on it — "The ``DECIMAL`` data type may be ``SIGNED``
        (allowing negative values) or ``UNSIGNED`` (not allowing negative
        values)" — so the attribute goes after the ``(M[,D])`` group, which is
        both the position the grammar gives it and the position the catalog
        reports it in.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/decimal

        Measured on all fifteen wired servers (10.2.44 - 13.1.1), which agree
        byte for byte: ``DECIMAL(10,2) UNSIGNED`` reports ``COLUMN_TYPE =
        'decimal(10,2) unsigned'`` and rejects ``-1`` with 1264 "Out of range
        value for column 'c'", while ``DECIMAL(10,2)`` stores it. That is the
        difference the flag exists to express, and it is why the flag is written
        rather than accepted and discarded — which would hand the caller a
        signed column and report success.

        ``ZEROFILL`` is MariaDB's and has no field on the concept, so it is not
        reachable from here; see :meth:`_format_mariadb_integer`, which owns the
        whole attribute slot and explains why one method serves the integers and
        these four numerics alike.
        """
        self._check_spelling(expr, DecimalType)
        if expr.precision is not None and not 1 <= expr.precision <= 65:
            raise ValueError(
                f"MariaDB DECIMAL precision must be between 1 and 65, "
                f"got {expr.precision}."
            )
        if expr.scale is not None and not 0 <= expr.scale <= 30:
            raise ValueError(
                f"MariaDB DECIMAL scale must be between 0 and 30, "
                f"got {expr.scale}."
            )
        if (expr.precision is not None and expr.scale is not None
                and expr.scale > expr.precision):
            raise ValueError(
                f"MariaDB DECIMAL scale ({expr.scale}) cannot exceed "
                f"precision ({expr.precision})."
            )
        if expr.precision is not None and expr.scale is not None:
            base = f"DECIMAL({expr.precision}, {expr.scale})"
        elif expr.precision is not None:
            base = f"DECIMAL({expr.precision})"
        else:
            base = "DECIMAL"
        return self._format_mariadb_integer(base, expr)

    def format_data_type_json(self, expr: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_jsonb(self, expr: JsonBType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_blob(self, expr: BlobType) -> Tuple[str, tuple]:
        """``BLOB`` only. ``BYTEA`` is PostgreSQL's name for the same unbounded
        byte storage; MariaDB writes ``BLOB`` and the four sized ``*BLOB``
        variants are this backend's own classes rather than spellings, because
        their maximum length is part of the column.

        This dialect *renders* the concept rather than substituting
        :class:`MariaDBBinaryType` for it: ``BLOB`` is unbounded and
        ``VARBINARY(n)`` is not, so the substitution would be a different
        storage, not a different name for the same one.
        """
        self._check_spelling(expr, ("blob",))
        return "BLOB", ()

    def format_data_type_custom(self, expr: CustomType) -> Tuple[str, tuple]:
        return expr.raw, ()

    # ------------------------------------------------------------------
    # DataTypeSupport — per-type support declarations
    #
    # MariaDB declares support for exactly the format_data_type_* family
    # above (1:1 correspondence contract): every type this mixin renders
    # is genuinely storable in MariaDB, so support is honest True for
    # each, and honestly absent for everything else (e.g. uuid, interval
    # — see MariaDBDialect.suggest_data_types()).
    # ------------------------------------------------------------------

    def supports_data_type_mariadb_tinyint(self) -> bool:
        return True

    def supports_data_type_mariadb_smallint(self) -> bool:
        return True

    def supports_data_type_mariadb_mediumint(self) -> bool:
        """Whether the 3-byte ``MEDIUMINT`` width is supported.

        Ungated: MariaDB has had ``MEDIUMINT`` since well before any release
        this backend supports, and it is a distinct 3-byte width — so it is a
        distinct concept with its own dispatch key rather than something folded
        into ``mariadb_int``.
        """
        return True

    def supports_data_type_mariadb_int(self) -> bool:
        return True

    def supports_data_type_mariadb_bigint(self) -> bool:
        return True

    def supports_data_type_mariadb_tinyblob(self) -> bool:
        return True

    def supports_data_type_mariadb_blob(self) -> bool:
        return True

    def supports_data_type_mariadb_mediumblob(self) -> bool:
        return True

    def supports_data_type_mariadb_longblob(self) -> bool:
        return True

    def supports_data_type_mariadb_tinytext(self) -> bool:
        return True

    def supports_data_type_mariadb_text(self) -> bool:
        return True

    def supports_data_type_mariadb_mediumtext(self) -> bool:
        return True

    def supports_data_type_mariadb_longtext(self) -> bool:
        return True

    def supports_data_type_mariadb_bit(self) -> bool:
        return True

    def supports_data_type_mariadb_year(self) -> bool:
        return True

    def supports_data_type_mariadb_binary(self) -> bool:
        return True

    def supports_data_type_mariadb_uuid(self) -> bool:
        """Whether this server has the native ``UUID`` type (MariaDB 10.7+).

        Answering yes below 10.7 would hand the caller a ``BINARY(16)`` column
        that is not what they asked for — see
        :meth:`format_data_type_mariadb_uuid`.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES["UUID"])

    def supports_data_type_uuid(self) -> bool:
        """Same gate, reached through the core type's name.

        The documented way to declare a column is with the *core* type —
        ``ColumnDefinition(d, "id", UUIDType())`` — so a backend that has the
        concept has to render the core name too, not only its own namespaced
        one. Without this, ``UUIDType(d)`` fails on a backend that plainly has
        UUID columns, and the error tells the reader nothing about which class
        to reach for instead.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES["UUID"])

    def format_data_type_uuid(self, expr: UUIDType) -> Tuple[str, tuple]:
        """``UUID`` — see :meth:`format_data_type_mariadb_uuid` for the gate and
        for why this is not the pre-10.7 ``BINARY(16)`` emulation."""
        return self.format_data_type_mariadb_uuid(expr)

    def supports_data_type_mariadb_xml(self) -> bool:
        """Whether this server has the native ``XMLTYPE`` column type (12.3+).

        Below 12.3 MariaDB has no XML type of any kind, so the honest answer
        there is no, and the ``xml`` concept is *substituted* — see
        ``MariaDBDialect.suggest_data_types()``, which reports ``TextType`` on
        an older server and this class on a 12.3+ one. Answering yes below 12.3
        would get the caller a DDL the server rejects; answering yes and emitting
        ``TEXT`` would get them a different column than they asked for.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES["XMLTYPE"])

    def supports_data_type_mariadb_varbinary(self) -> bool:
        return True

    def supports_data_type_enum(self) -> bool:
        return True

    def supports_data_type_mariadb_enum(self) -> bool:
        return True

    def supports_data_type_mariadb_set(self) -> bool:
        return True

    def supports_data_type_mariadb_geometry(self) -> bool:
        return True

    def supports_data_type_mariadb_point(self) -> bool:
        return True

    def supports_data_type_mariadb_linestring(self) -> bool:
        return True

    def supports_data_type_mariadb_polygon(self) -> bool:
        return True

    def supports_data_type_mariadb_multipoint(self) -> bool:
        return True

    def supports_data_type_mariadb_multilinestring(self) -> bool:
        return True

    def supports_data_type_mariadb_multipolygon(self) -> bool:
        return True

    def supports_data_type_mariadb_geometrycollection(self) -> bool:
        return True

    def supports_data_type_integer(self) -> bool:
        return True

    def supports_data_type_bigint(self) -> bool:
        return True

    def supports_data_type_smallint(self) -> bool:
        return True

    def supports_data_type_tinyint(self) -> bool:
        return True

    def supports_data_type_varchar(self) -> bool:
        return True

    def supports_data_type_char(self) -> bool:
        return True

    def supports_data_type_text(self) -> bool:
        return True

    def supports_data_type_boolean(self) -> bool:
        return True

    def supports_data_type_date(self) -> bool:
        return True

    def supports_data_type_datetime(self) -> bool:
        return True

    def supports_data_type_time(self) -> bool:
        return True

    def supports_data_type_timetz(self) -> bool:
        return True

    def supports_data_type_timestamp(self) -> bool:
        return True

    def supports_data_type_timestamptz(self) -> bool:
        return True

    def supports_data_type_float(self) -> bool:
        return True

    def supports_data_type_double(self) -> bool:
        return True

    def supports_data_type_decimal(self) -> bool:
        return True

    def supports_data_type_json(self) -> bool:
        return True

    def supports_data_type_jsonb(self) -> bool:
        return True

    def supports_data_type_blob(self) -> bool:
        return True

    def supports_data_type_custom(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # MariaDBTypeSupport — the capability questions a name cannot answer
    #
    # These are the members declared by
    # :class:`~...protocols.types.MariaDBTypeSupport`, and they are what that
    # protocol is composed into ``MariaDBDialect`` for. The naming convention
    # above already answers "can this dialect render the concept named X"; what
    # it cannot answer is the *attribute* questions — is this server old enough
    # to have the type at all, and may these modifiers be written on it.
    #
    # Every member here is an ``isinstance``-reachable method rather than a
    # constant: each returns the same value the corresponding formatter's own
    # gate does, so a caller can branch on the capability and a caller who
    # renders the type get the same answer. Where that is possible the method
    # *delegates* rather than repeating the comparison — one version boundary
    # table, two entry points, no way for the two to drift.
    # ------------------------------------------------------------------

    def supports_mariadb_integer_attributes(self) -> bool:
        """Whether ``UNSIGNED`` and ``ZEROFILL`` may be written on an integer column.

        True on every MariaDB version this backend supports, and ungated on
        purpose: these are MySQL-and-MariaDB extensions that arrived long before
        the oldest release here, so there is no version to compare against and a
        gate that always answers yes is a second copy of the truth rather than
        a measurement.

        The question is worth answering explicitly anyway, because a caller
        writing DDL has to know how the two relate — and they are **not**
        independent, whatever the ``[SIGNED | UNSIGNED | ZEROFILL]`` syntax line
        suggests:

        * ``UNSIGNED`` changes the representable range (``TINYINT UNSIGNED`` is
          ``0``..``255``, not ``-128``..``127``), is part of the type's
          identity, and is honoured on its own.
        * ``ZEROFILL`` pads the output with leading zeros — **and MariaDB makes
          the column ``UNSIGNED`` when it is set.** The overview says "If
          ``ZEROFILL`` is specified, the column will be set to ``UNSIGNED``";
          the ``INT`` page says "A special type of ``INT UNSIGNED`` is ``INT
          ZEROFILL``". Verified on all fifteen wired servers:
          ``CREATE TABLE t (c INT ZEROFILL)`` reports ``int(10) unsigned
          zerofill``, byte for byte what ``INT UNSIGNED ZEROFILL`` reports, and
          neither stores ``-1``.

        So the two words a caller may write are ``UNSIGNED`` and ``ZEROFILL``,
        but the two *columns* are signed and unsigned, with ``zerofill`` as a
        display flag on the unsigned one. The ``MariaDB*IntType`` constructors
        perform that normalisation at construction
        (``_zerofill_signedness``), which is what keeps ``X ZEROFILL`` and ``X
        UNSIGNED ZEROFILL`` one value object as well as one column.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/int
        """
        return True

    def supports_mariadb_mediumint_width(self) -> bool:
        """Whether the 3-byte ``MEDIUMINT`` width is a type of its own here.

        True on every version, for the reason :class:`MariaDBMediumIntType`
        exists: 3 bytes is neither the 1-, 2-, 4- nor 8-byte concept, so folding
        it into ``mariadb_int`` would let a 3-byte column compare equal to a
        4-byte one. The class, the dispatch key and the per-width rendering all
        follow from this answer being yes, which is why it is stated rather than
        inferred from the presence of a formatter.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/mediumint
        """
        return True

    def supports_mariadb_xml_type(self) -> bool:
        """Whether this server has the native ``XMLTYPE`` column type (12.3+).

        The one capability here that is genuinely version-dependent, and it is
        delegated to the per-type gate so the two cannot disagree:
        ``supports_data_type_mariadb_xml()`` is the same comparison read through
        the naming convention, and this is the same comparison read as a
        capability. Both answer *for the server*, not for the type.

        Below 12.3 there is no XML type of any kind — ``CREATE TABLE t (c XML)``
        fails with errno 4161 — and the framework's substitute is ``TextType``,
        which is a different column. Above it, ``XMLTYPE`` is real storage: "basic
        XML storage capabilities only, without validation", 4 GB maximum "same as
        ``LONGBLOB``", and no length permitted at all.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/xmltype
        """
        return self.supports_data_type_mariadb_xml()

    def supports_mariadb_uuid_type(self) -> bool:
        """Whether this server has the native ``UUID`` column type (10.7+).

        Delegated to :meth:`supports_data_type_uuid` for the same reason as the
        XML gate: one boundary in ``MARIADB_VERSION_BOUNDARIES``, read through
        two names. MariaDB's ``UUID`` is not an emulation over ``BINARY(16)`` —
        values are stored byte-swapped so UUIDv1 ordering is index-friendly,
        ``UUID_SHORT()`` is rejected, and braces in the literal form are refused
        — so below 10.7 the answer is no and the caller should reach for
        ``MariaDBBinaryType(length=16)`` deliberately.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type
        """
        return self.supports_data_type_uuid()

    def supports_mariadb_year_display_width(self) -> bool:
        """Whether an explicit ``YEAR(4)`` may be written.

        True on every version this backend supports. ``YEAR`` alone means
        ``YEAR(4)``, so the width is legacy decoration the server still accepts
        for compatibility, and this backend renders it only when the caller asked
        for it.

        The one thing that is *not* writable is ``YEAR(2)``: deprecated in 2012
        and rejected outright by MariaDB 13.0+ (verified live — errno 1064 on
        13.0.2 and 13.1.1, parses on 12.2 and 12.3). That is enforced at
        construction in :class:`~...expression.types.MariaDBYearType` rather than
        here, because a capability flag nobody is obliged to consult is a weaker
        place for it than a ``ValueError`` naming the width at the point the
        caller chose it. A ``YEAR(2)`` read back off a 12.x server still parses,
        with a ``DeprecationWarning`` and the width degraded to ``None``.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/date-and-time-data-types/year
        """
        return True

    def supports_mariadb_enum_charset(self) -> bool:
        """Whether ``CHARACTER SET`` / ``COLLATE`` may be written on an ``ENUM``.

        True on every version. MariaDB allows a per-column character set and
        collation on the string types, which is why
        :class:`~...expression.types.MariaDBEnumType` exists alongside core's
        :class:`~rhosocial.activerecord.backend.expression.types.EnumType`: it
        carries the two attributes in its ``PARAMETERS``, so an enum with a
        collation compares *unequal* to the same labels without one. Without the
        attributes there would be nothing to declare and no reason for the
        backend to have its own enum class at all.

        This is the same treatment the framework gives a charset on any string
        type — a *field* on the type, not a separate national-character type —
        which is a deliberate decision shared with core's string types; see their
        module docstring.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/enum
        """
        return True

    def supports_mariadb_geometry_srid(self) -> bool:
        """Whether a spatial column may declare its reference system.

        True on every version, and spelled ``REF_SYSTEM_ID=<n>`` as a column
        attribute: ``POINT REF_SYSTEM_ID=4326``. ``SRID <n>`` is MySQL's
        spelling of the same idea and is a syntax error here -- rejected with
        errno 1064 by every server measured (10.2.44 and 13.1.1 live for this
        change; 10.6.28, 11.4.13, 11.8.9, 12.1.2 and 12.3.3 in the
        typed-columns investigation) -- so it must not be rendered. See
        :meth:`_format_mariadb_spatial`.

        It is a value question rather than a storage question: the same
        coordinate pair means different places in different reference systems,
        so two spatial columns declaring different systems are not
        interchangeable and the schema differ must see the difference -- which
        is why ``srid`` is in ``PARAMETERS`` on the eight ``MariaDB*`` spatial
        classes instead of being a table option. MariaDB does not enforce the
        declaration against stored values (they keep their own SRID), but it
        does record it.

        It is also not readable from ``COLUMN_TYPE`` the way an integer
        attribute is: MariaDB reports the bare ``point`` there and in ``SHOW
        CREATE``, and keeps the declaration only in
        ``I_S.GEOMETRY_COLUMNS.SRID``. The column introspector joins that view
        and folds the value back into the parsed type.

        Official Documentation:
        https://mariadb.com/docs/server/reference/system-tables/information-schema/information-schema-tables/information-schema-geometry_columns-table
        """
        return True

    def supports_mariadb_sized_text(self) -> bool:
        """Whether the four bounded-text types exist (``TINYTEXT``..``LONGTEXT``).

        True on every version. They are separate *types* rather than spellings of
        core's ``text`` because the maximum length **is** the type:
        ``TINYTEXT`` holds 65,535 bytes and ``LONGTEXT`` holds 4,294,967,295, so
        a schema that switches between them has made a real change and the diff
        has to report it. Core's ``TextType`` carries no length, so each of the
        four is a ``mariadb_*text`` class of its own with its own dispatch key.

        Note the deliberate mismatch with ``VARCHAR``: there the length is a
        parameter of one type, because ``VARCHAR`` has a declared limit the caller
        picks. A ``TEXT`` variant's ceiling is fixed by the name, so it belongs
        in the class.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/text
        """
        return True

    def supports_mariadb_sized_blob(self) -> bool:
        """Whether the four bounded-blob types exist (``TINYBLOB``..``LONGBLOB``).

        True on every version, and for the same reason as
        :meth:`supports_mariadb_sized_text`: the byte ceiling is the type. The
        sizes are 255 / 65,535 / 16,777,215 / 4,294,967,295 bytes.

        Core's ``blob`` concept is the 65,535-byte one, so ``BLOB`` and
        ``mariadb_blob`` are the same 4-byte-limit storage under two names, and
        only one of them is MariaDB's own dispatch key — which is exactly the
        situation D8 says must not arise *within* one concept, and does not: the
        two are different classes for different concepts, and the rendered word
        is ``BLOB`` for both.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/blob
        """
        return True
