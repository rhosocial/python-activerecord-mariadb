# src/rhosocial/activerecord/backend/impl/mariadb/mixins/types.py
"""MariaDB DataType formatting and parsing mixin."""

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
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.

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
      named in ``MariaDBDialect.suggested_data_types()`` as what MariaDB stores
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
        contain the word ``parse_type`` reads ``unsigned`` from, handing back a
        different value object than the caller declared and making the differ
        report a change nobody made. Emitting what will actually be stored is
        the honest output, and it is what makes
        ``parse_type(format_data_type(t)[0]) == t`` hold for every combination
        of width, signedness and zerofill.

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

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        """
        if data_type.unsigned:
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

    def format_data_type_mariadb_tinyint(self, data_type: MariaDBTinyIntType) -> Tuple[str, tuple]:
        """``TINYINT`` — 1 byte, ``-128``..``127`` signed / ``0``..``255``
        unsigned, with MariaDB's own two attributes.

        Spelled ``TINYINT`` and rendered that way because that is what the
        catalog reports: MariaDB rewrites MariaDB's own ``INT1`` synonym to
        ``tinyint(4)`` (verified), so echoing the synonym back would make an
        introspected column differ from its own declaration.
        """
        return self._format_mariadb_integer("TINYINT", data_type)

    def format_data_type_mariadb_smallint(self, data_type: MariaDBSmallIntType) -> Tuple[str, tuple]:
        """``SMALLINT`` — 2 bytes, ``-32768``..``32767`` / ``0``..``65535``."""
        return self._format_mariadb_integer("SMALLINT", data_type)

    def format_data_type_mariadb_mediumint(self, data_type: MariaDBMediumIntType) -> Tuple[str, tuple]:
        """``MEDIUMINT`` — 3 bytes, ``-8388608``..``8388607`` / ``0``..``16777215``.

        MariaDB spells this width with two words, ``MEDIUMINT`` and its
        documented synonym ``INT3``, so both are accepted and ``MEDIUMINT`` is
        rendered — the form the server itself writes into ``COLUMN_TYPE``, which
        is what makes ``parse_type`` able to read this backend's own output back.
        """
        self._check_spelling(data_type, MariaDBMediumIntType)
        return self._format_mariadb_integer("MEDIUMINT", data_type)

    def format_data_type_mariadb_int(self, data_type: MariaDBIntType) -> Tuple[str, tuple]:
        """``INT`` — 4 bytes, ``-2147483648``..``2147483647`` / ``0``..``4294967295``."""
        return self._format_mariadb_integer("INT", data_type)

    def format_data_type_mariadb_bigint(self, data_type: MariaDBBigIntType) -> Tuple[str, tuple]:
        """``BIGINT`` — 8 bytes, the full signed and unsigned 64-bit ranges."""
        return self._format_mariadb_integer("BIGINT", data_type)

    def format_data_type_mariadb_tinyblob(self, data_type: MariaDBTinyBlobType) -> Tuple[str, tuple]:
        return "TINYBLOB", ()

    def format_data_type_mariadb_blob(self, data_type: MariaDBBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def format_data_type_mariadb_mediumblob(self, data_type: MariaDBMediumBlobType) -> Tuple[str, tuple]:
        return "MEDIUMBLOB", ()

    def format_data_type_mariadb_longblob(self, data_type: MariaDBLongBlobType) -> Tuple[str, tuple]:
        return "LONGBLOB", ()

    def format_data_type_mariadb_tinytext(self, data_type: MariaDBTinyTextType) -> Tuple[str, tuple]:
        return "TINYTEXT", ()

    def format_data_type_mariadb_text(self, data_type: MariaDBTextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_mariadb_mediumtext(self, data_type: MariaDBMediumTextType) -> Tuple[str, tuple]:
        return "MEDIUMTEXT", ()

    def format_data_type_mariadb_longtext(self, data_type: MariaDBLongTextType) -> Tuple[str, tuple]:
        return "LONGTEXT", ()

    def format_data_type_mariadb_bit(self, data_type: MariaDBBitType) -> Tuple[str, tuple]:
        if data_type.n is not None:
            return f"BIT({data_type.n})", ()
        return "BIT", ()

    def format_data_type_mariadb_year(self, data_type: MariaDBYearType) -> Tuple[str, tuple]:
        if data_type.display_width is not None:
            return f"YEAR({data_type.display_width})", ()
        return "YEAR", ()

    def format_data_type_mariadb_binary(self, data_type: MariaDBBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"BINARY({data_type.length})", ()
        return "BINARY", ()

    def format_data_type_mariadb_uuid(self, data_type: MariaDBUUIDType) -> Tuple[str, tuple]:
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

    def format_data_type_mariadb_xml(self, data_type: MariaDBXmlType) -> Tuple[str, tuple]:
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
                at ``TextType`` — the substitute ``suggested_data_types()``
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

    def format_data_type_mariadb_varbinary(self, data_type: MariaDBVarBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"VARBINARY({data_type.length})", ()
        return "VARBINARY", ()

    def format_data_type_enum(self, data_type: EnumType) -> Tuple[str, tuple]:
        """Render the core ``EnumType``.

        MariaDB has a native ENUM, so the generic type is renderable here
        rather than something to substitute. ``MariaDBEnumType`` stays for the
        cases that need the charset and collation this form does not carry.
        """
        values_str = ",".join(self.format_literal(value) for value in data_type.values)
        return f"ENUM({values_str})", ()

    def format_data_type_mariadb_enum(self, data_type: MariaDBEnumType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in data_type.values)
        result = f"ENUM({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
        return result, ()

    def format_data_type_mariadb_set(self, data_type: MariaDBSetType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in data_type.values)
        result = f"SET({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
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

    def format_data_type_mariadb_geometry(self, data_type: MariaDBGeometryType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("GEOMETRY", data_type)

    def format_data_type_mariadb_point(self, data_type: MariaDBPointType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("POINT", data_type)

    def format_data_type_mariadb_linestring(self, data_type: MariaDBLineStringType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("LINESTRING", data_type)

    def format_data_type_mariadb_polygon(self, data_type: MariaDBPolygonType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("POLYGON", data_type)

    def format_data_type_mariadb_multipoint(self, data_type: MariaDBMultiPointType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTIPOINT", data_type)

    def format_data_type_mariadb_multilinestring(self, data_type: MariaDBMultiLineStringType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTILINESTRING", data_type)

    def format_data_type_mariadb_multipolygon(self, data_type: MariaDBMultiPolygonType) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("MULTIPOLYGON", data_type)

    def format_data_type_mariadb_geometrycollection(
        self, data_type: MariaDBGeometryCollectionType
    ) -> Tuple[str, tuple]:
        return self._format_mariadb_spatial("GEOMETRYCOLLECTION", data_type)

    # --- Core types (pure names) rendered to real MariaDB SQL ---

    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
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
        self._check_spelling(data_type, IntegerType)
        return self._format_mariadb_integer("INT", data_type)

    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
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
        self._check_spelling(data_type, BigIntType)
        return self._format_mariadb_integer("BIGINT", data_type)

    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
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
        self._check_spelling(data_type, SmallIntType)
        return self._format_mariadb_integer("SMALLINT", data_type)

    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        """``TINYINT`` / ``INT1`` — both accepted, ``TINYINT`` rendered.

        MariaDB's ``TINYINT`` page lists "``INT1``, ``BOOL``, and ``BOOLEAN``"
        as synonyms, so all of those words are ones the server accepts.

        Note the deliberate asymmetry with :meth:`format_data_type_boolean`:
        MariaDB stores a boolean as ``TINYINT(1)``, so ``parse_type`` reads
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
        self._check_spelling(data_type, TinyIntType)
        return self._format_mariadb_integer("TINYINT", data_type)

    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        """``VARCHAR`` / ``CHARACTER VARYING`` — both accepted, ``VARCHAR``
        rendered.

        MariaDB's ``VARCHAR`` page says "``VARCHAR`` is shorthand for
        ``CHARACTER VARYING``" and lists ``CHARACTER VARYING`` among the
        synonyms, so both are accepted. The long form is normalised to
        ``VARCHAR`` because that is what MariaDB stores and reports — which is
        also what makes ``parse_type`` able to read its own output back as
        ``varchar``.
        """
        self._check_spelling(data_type, VarCharType)
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        """``CHAR`` / ``CHARACTER`` — both accepted, ``CHAR`` rendered.

        MariaDB has a ``CHARACTER`` page that says "This is a synonym for
        ``CHAR``", with a worked example whose ``SHOW CREATE TABLE`` output is
        ``char(1)``. ``CHARACTER`` is also the keyword introducing a character
        *set* clause (``CHARACTER SET utf8``), which is a different thing and
        not a reason to refuse the type spelling.
        """
        self._check_spelling(data_type, CharType)
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        """``TEXT`` only. MariaDB has no ``CLOB`` type — an unbounded string is a
        ``TEXT``, and the four sized ``*TEXT`` variants are this backend's own
        ``mariadb_tinytext``/``mariadb_mediumtext``/``mariadb_longtext`` classes
        rather than spellings of this one, because the maximum length is part of
        what the column can hold."""
        self._check_spelling(data_type, ("text",))
        return "TEXT", ()

    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        """MariaDB has no native boolean type: both ``BOOLEAN`` and ``BOOL`` are
        documented synonyms of ``TINYINT``, and the framework writes the
        conventional ``TINYINT(1)`` so that the column's storage width is visible
        in the DDL.

        The width is the reason ``TINYINT(1)`` is not the same declaration as a
        bare ``TINYINT``, which is why :meth:`format_data_type_tinyint` renders
        the latter without one.
        """
        self._check_spelling(data_type, BooleanType)
        return "TINYINT(1)", ()

    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        self._validate_fsp("DATETIME", data_type.precision)
        return (f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"), ()

    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", data_type.precision)
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", data_type.precision)
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", data_type.precision)
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", data_type.precision)
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
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
        if data_type.precision is not None:
            raise ValueError(
                "MariaDB cannot round-trip FLOAT(p): the catalog records FLOAT "
                "without p, and p chooses the storage class. p 0..24 creates "
                "single-precision FLOAT storage — declare FloatType(dialect) "
                "with no precision; p 25..53 creates double-precision DOUBLE "
                f"storage — declare DoubleType(dialect). "
                f"Got precision={data_type.precision}."
            )
        return self._format_mariadb_integer("FLOAT", data_type)

    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
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
        ``MariaDBDialect.substitute_advice``.

        ``unsigned`` is honoured through :meth:`_format_mariadb_integer`, in the
        slot that grammar gives it — measured on all fifteen wired servers:
        ``DOUBLE(10,2) UNSIGNED`` reports ``'double(10,2) unsigned'`` and
        rejects ``-1`` with 1264.
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/double
        """
        self._check_spelling(data_type, DoubleType)
        return self._format_mariadb_integer("DOUBLE", data_type)

    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
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
        self._check_spelling(data_type, DecimalType)
        if data_type.precision is not None and not 1 <= data_type.precision <= 65:
            raise ValueError(
                f"MariaDB DECIMAL precision must be between 1 and 65, "
                f"got {data_type.precision}."
            )
        if data_type.scale is not None and not 0 <= data_type.scale <= 30:
            raise ValueError(
                f"MariaDB DECIMAL scale must be between 0 and 30, "
                f"got {data_type.scale}."
            )
        if (data_type.precision is not None and data_type.scale is not None
                and data_type.scale > data_type.precision):
            raise ValueError(
                f"MariaDB DECIMAL scale ({data_type.scale}) cannot exceed "
                f"precision ({data_type.precision})."
            )
        if data_type.precision is not None and data_type.scale is not None:
            base = f"DECIMAL({data_type.precision}, {data_type.scale})"
        elif data_type.precision is not None:
            base = f"DECIMAL({data_type.precision})"
        else:
            base = "DECIMAL"
        return self._format_mariadb_integer(base, data_type)

    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_blob(self, data_type: BlobType) -> Tuple[str, tuple]:
        """``BLOB`` only. ``BYTEA`` is PostgreSQL's name for the same unbounded
        byte storage; MariaDB writes ``BLOB`` and the four sized ``*BLOB``
        variants are this backend's own classes rather than spellings, because
        their maximum length is part of the column.

        This dialect *renders* the concept rather than substituting
        :class:`MariaDBBinaryType` for it: ``BLOB`` is unbounded and
        ``VARBINARY(n)`` is not, so the substitution would be a different
        storage, not a different name for the same one.
        """
        self._check_spelling(data_type, ("blob",))
        return "BLOB", ()

    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()

    # ------------------------------------------------------------------
    # DataTypeSupport — per-type support declarations
    #
    # MariaDB declares support for exactly the format_data_type_* family
    # above (1:1 correspondence contract): every type this mixin renders
    # is genuinely storable in MariaDB, so support is honest True for
    # each, and honestly absent for everything else (e.g. uuid, interval
    # — see MariaDBDialect.suggested_data_types()).
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
        return self.version >= MARIADB_VERSION_BOUNDARIES["UUID"]

    def supports_data_type_uuid(self) -> bool:
        """Same gate, reached through the core type's name.

        The documented way to declare a column is with the *core* type —
        ``ColumnDefinition(d, "id", UUIDType())`` — so a backend that has the
        concept has to render the core name too, not only its own namespaced
        one. Without this, ``UUIDType(d)`` fails on a backend that plainly has
        UUID columns, and the error tells the reader nothing about which class
        to reach for instead.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES["UUID"]

    def format_data_type_uuid(self, data_type: UUIDType) -> Tuple[str, tuple]:
        """``UUID`` — see :meth:`format_data_type_mariadb_uuid` for the gate and
        for why this is not the pre-10.7 ``BINARY(16)`` emulation."""
        return self.format_data_type_mariadb_uuid(data_type)

    def supports_data_type_mariadb_xml(self) -> bool:
        """Whether this server has the native ``XMLTYPE`` column type (12.3+).

        Below 12.3 MariaDB has no XML type of any kind, so the honest answer
        there is no, and the ``xml`` concept is *substituted* — see
        ``MariaDBDialect.suggested_data_types()``, which reports ``TextType`` on
        an older server and this class on a 12.3+ one. Answering yes below 12.3
        would get the caller a DDL the server rejects; answering yes and emitting
        ``TEXT`` would get them a different column than they asked for.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES["XMLTYPE"]

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

    # ------------------------------------------------------------------
    # DataTypeSupport — parsing
    #
    # ``parse_type`` is the inverse of the formatters above, and it is held to
    # the same rule the plan's decision D8 states: **one concept in, one class
    # out**. Every spelling of a concept that MariaDB itself accepts — the ones
    # ``format_data_type_<name>`` lists as ``accepted`` — is recognised here, and
    # every one of them yields the *same* class with the *same* parameters.
    #
    # That last part is why the returned instances carry the **default**
    # ``spelling`` even when the server's word was the long one. This dialect
    # normalises every spelling it accepts to MariaDB's own word (see the note
    # above the formatters), so recording ``spelling="numeric"`` on the way in
    # would make a ``NUMERIC(10,2)`` column compare unequal to the identical
    # ``DECIMAL(10,2)`` column it renders as — and equality is what the schema
    # differ reads. PostgreSQL, which echoes its spellings back, records them;
    # MariaDB has no reason to.
    #
    # A type MariaDB does not write (``BYTEA``, ``CLOB``, ``CHARACTER VARYING``)
    # is not parsed: it cannot come back from a server, and guessing would be
    # worse than the honest :class:`CustomType` the fallback returns.
    # ------------------------------------------------------------------

    # Every word MariaDB's own "Numeric Data Type Overview" lists as an integer
    # synonym is recognised here, and each maps to **the class its canonical word
    # maps to** — that is the whole of D8 here. The manual's list is short and
    # exact, so there is nothing to guess:
    #
    #   BOOLEAN / BOOL  - Synonym for TINYINT(1)   -> BooleanType (below)
    #   INT1            - Synonym for TINYINT       -> MariaDBTinyIntType
    #   INT2            - Synonym for SMALLINT      -> MariaDBSmallIntType
    #   INT3            - Synonym for MEDIUMINT     -> MariaDBMediumIntType
    #   INT4            - Synonym for INT           -> MariaDBIntType
    #   INT8            - Synonym for BIGINT        -> MariaDBBigIntType
    #
    # https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
    #
    # The per-width pages say the same thing in their own words -- "INT1 is a
    # synonym for TINYINT" on the TINYINT page and again on INT1's own page at
    # .../numeric-data-types/int1, "INT2 is a synonym for SMALLINT", "INT3 is a
    # synonym for MEDIUMINT", "INT4 is a synonym for INT", "INT8 is a synonym
    # for BIGINT" -- and "INTEGER is a synonym for INT" on the INT page. The
    # overview is the one place all six appear together, which is why it is
    # cited above the per-width pages.
    #
    # Why ``INT1``/``INT2``/``INT8`` had to be added at all: each is a member of
    # the corresponding core concept's ``SPELLINGS`` (``TinyIntType``,
    # ``SmallIntType``, ``BigIntType``), so ``format_data_type_tinyint`` &
    # friends *accept* them and render the canonical word. A word the formatter
    # accepts and ``parse_type`` cannot read is the asymmetry D8 forbids: the
    # dialect will write a column whose declared spelling it cannot name back.
    # They came back as ``CustomType``, whose ``raw`` is then a type name the
    # caller never wrote.
    #
    # ``INT4`` is here for a different reason and is *not* one of those three.
    # Core's ``IntegerType.SPELLINGS`` is ``("integer", "int")`` -- it does not
    # carry ``int4`` -- so ``format_data_type_integer`` **refuses** it with a
    # ``TypeError`` naming the spelling, and this dialect therefore never writes
    # the word. It is still parsed, because ``parse_type`` is also the reader for
    # text that did not come from this dialect's formatters -- a MariaDB dump, a
    # hand-written migration, ``SHOW CREATE TABLE`` output pasted from elsewhere
    # -- and ``INT4`` is on the server's own synonym list. Refusing to *read* a
    # word the server writes is the guess in the other direction. It widens the
    # reader and never narrows it: ``INT4`` and ``INTEGER`` land on the same
    # class with the same ``spelling``, so D8's one-concept-one-class is intact.
    #
    # ``INT3`` was already here, for the same reason as ``INT4``: the catalog
    # only ever reports ``mediumint(...)`` because the server rewrites its own
    # synonym, but the dialect renders the word and a caller may hand it back.
    #
    # Order matters only for ``INT``'s own prefix: ``INT1``..``INT8`` are tried
    # before ``INT`` so the narrower word wins. Every alternative ends in ``\b``,
    # so a longer word that merely starts with one of these -- ``INT11`` -- does
    # not match at all, and the trailing attributes are left to the branches.
    _MARIA_INTEGER_TYPES = re.compile(
        r"^(?:TINYINT|SMALLINT|MEDIUMINT|"
        r"INT1|INT2|INT3|INT4|INT8|"
        r"INT|INTEGER|BIGINT)\b",
        re.IGNORECASE,
    )
    _MARIA_BOOLEAN_TYPES = re.compile(
        r"^(?:BOOL|BOOLEAN)\b",
        re.IGNORECASE,
    )
    _MARIA_FLOAT_TYPES = re.compile(
        r"^(?:FLOAT|REAL|DOUBLE)\b",
        re.IGNORECASE,
    )
    # DECIMAL before DEC so the longer word wins the alternation; the trailing
    # \b would reject "DEC" against "DECIMAL" anyway, but order states the
    # intent rather than relying on it.
    _MARIA_DECIMAL_TYPES = re.compile(
        r"^(?:DECIMAL|NUMERIC|DEC|FIXED)\b",
        re.IGNORECASE,
    )
    _MARIA_STRING_TYPES = re.compile(
        r"^(?:CHAR|VARCHAR|TEXT|TINYTEXT|MEDIUMTEXT|LONGTEXT|"
        r"ENUM|SET|BINARY|VARBINARY)\b",
        re.IGNORECASE,
    )
    _MARIA_BLOB_TYPES = re.compile(
        r"^(?:BLOB|TINYBLOB|MEDIUMBLOB|LONGBLOB)\b",
        re.IGNORECASE,
    )
    _MARIA_DATE_TYPES = re.compile(
        r"^(?:DATE|DATETIME|TIMESTAMP|TIME|YEAR)\b",
        re.IGNORECASE,
    )
    _MARIA_JSON_TYPES = re.compile(
        r"^(?:JSON)\b",
        re.IGNORECASE,
    )
    # MariaDB 12.3's native XML type. Kept out of ``_MARIA_STRING_TYPES`` on
    # purpose, even though MariaDB documents it under string data types: that
    # branch ends in a catch-all that returns ``CharType`` for any prefix it
    # does not recognise, so folding ``XMLTYPE`` in would hand back a character
    # string. It has its own regex and its own branch below.
    _MARIA_XML_TYPES = re.compile(
        r"^(?:XMLTYPE)\b",
        re.IGNORECASE,
    )
    # MariaDB 10.7's native UUID column type, the same shape of arrival as
    # XMLTYPE and gated the same way below.
    _MARIA_UUID_TYPES = re.compile(
        r"^(?:UUID)\b",
        re.IGNORECASE,
    )
    _MARIA_SPATIAL_TYPES = re.compile(
        r"^(?:GEOMETRY|POINT|LINESTRING|POLYGON|"
        r"MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)\b",
        re.IGNORECASE,
    )
    _MARIA_BIT_TYPES = re.compile(
        r"^(?:BIT)\b",
        re.IGNORECASE,
    )

    def parse_type(self, raw: str) -> DataType:
        """Turn one MariaDB type string into one ``DataType``.

        D8 in one sentence: the words MariaDB writes for one concept must all
        arrive here as one class. ``INT`` and ``INTEGER``, ``NUMERIC``/``DEC``/
        ``DECIMAL``, ``BOOL``/``BOOLEAN`` and ``DOUBLE``/``DOUBLE PRECISION``
        are each one concept with several spellings, and each is parsed to the
        same canonical instance shape. A word MariaDB does not write falls
        through to :class:`CustomType`, which is honest ignorance rather than a
        guess.
        """
        stripped = raw.strip()
        upper = stripped.upper()

        if self._MARIA_BIT_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            n = int(nums[0]) if nums else None
            from ..expression.types import MariaDBBitType
            return MariaDBBitType(self, n)

        # BOOL / BOOLEAN are documented synonyms of TINYINT on MariaDB, so this
        # branch has to run before anything that would otherwise claim the
        # prefix. It yields the same BooleanType that TINYINT(1) yields below,
        # which is what keeps ``parse_type`` round-tripping through
        # ``format_data_type_boolean`` -> ``TINYINT(1)`` -> ``BooleanType``.
        if self._MARIA_BOOLEAN_TYPES.match(upper):
            return BooleanType(self)

        if self._MARIA_INTEGER_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            # Each branch below is one *width*, and every word that width accepts
            # -- canonical or documented synonym -- arrives here and becomes the
            # same class with the same ``unsigned`` / ``zerofill``. That is the
            # whole of D8 for this branch: there is exactly one class per width,
            # so there is no synonym that can come back as a different concept.
            if upper.startswith("TINYINT") or upper.startswith("INT1"):
                # ``INT1`` is MariaDB's own synonym for the 1-byte width. It has
                # to be checked here rather than falling through to the boolean
                # branch, and the two are genuinely different: the server stores
                # ``BOOL`` / ``BOOLEAN`` as ``tinyint(1)`` but ``INT1`` as
                # ``tinyint(4)``, so ``INT1`` is a small integer and stays one.
                # The display width is the number **inside the parentheses**,
                # never any digit in the type word. That distinction is what
                # keeps ``INT1`` out of the boolean branch: a bare ``INT1`` has a
                # ``1`` in its *name*, not a display width of 1, and reading it
                # as one would make ``parse_type("int1")`` a ``BooleanType`` --
                # the exact asymmetry this branch's synonym was added to remove.
                # ``TINYINT(1)`` is a different declaration (and is what the
                # catalog reports for a ``BOOL`` column); a bare ``TINYINT`` --
                # no display width at all -- is a small integer and stays one.
                width_match = re.search(r"\(\s*(\d+)\s*\)", stripped)
                display_width = int(width_match.group(1)) if width_match else None
                from ..expression.types import MariaDBTinyIntType
                t = MariaDBTinyIntType(self, unsigned=unsigned, zerofill=zerofill)
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType(self)
                return t
            if upper.startswith("SMALLINT") or upper.startswith("INT2"):
                from ..expression.types import MariaDBSmallIntType
                t = MariaDBSmallIntType(self, unsigned=unsigned, zerofill=zerofill)
                return t
            if upper.startswith("MEDIUMINT") or upper.startswith("INT3"):
                # MEDIUMINT is 3 bytes — a width of its own, with its own class
                # and its own dispatch key. Reading it as the 4-byte
                # MariaDBIntType (as this branch used to) made a 3-byte column
                # compare equal to a 4-byte one, which is a false identity
                # claim the differ would then act on. ``INT3`` is MariaDB's own
                # documented synonym for the same width and lands here too; the
                # server normalises it to ``mediumint(...)`` in the catalog, and
                # like every other accepted spelling in this dialect it is
                # normalised to MariaDB's own word rather than recorded.
                return MariaDBMediumIntType(
                    self, unsigned=unsigned, zerofill=zerofill,
                )
            if upper.startswith("BIGINT") or upper.startswith("INT8"):
                from ..expression.types import MariaDBBigIntType
                t = MariaDBBigIntType(self, unsigned=unsigned, zerofill=zerofill)
                return t
            # INT, INTEGER and INT4 all land here: one concept, three words MariaDB
            # accepts, and the canonical `mariadb_int` class for all of them (D8).
            from ..expression.types import MariaDBIntType
            t = MariaDBIntType(self, unsigned=unsigned, zerofill=zerofill)
            return t

        if self._MARIA_FLOAT_TYPES.match(upper):
            # DOUBLE, DOUBLE PRECISION and REAL are the three words MariaDB's
            # DOUBLE page groups as one 8-byte type, and the first two arrive as
            # DoubleType with the default spelling; see the note at the head of
            # this section for why the spelling is not recorded.  REAL is the
            # mode-dependent word -- DOUBLE by default, FLOAT under
            # REAL_AS_FLOAT -- and the catalog never writes it back, so it
            # canonicalises to the storage it actually is, DoubleType (a live
            # column made under REAL_AS_FLOAT reports ``float`` and reaches the
            # FloatType branch below).  The dialect tells a caller who asks for
            # the RealType concept which class to declare instead; see
            # ``MariaDBDialect.suggested_data_types`` and ``substitute_advice``.
            #
            # ``unsigned`` is read here for the same reason the integer branch
            # reads it: MariaDB writes the attribute into ``COLUMN_TYPE`` in this
            # position for these three words exactly as it does for the integer
            # widths -- measured on all fifteen wired servers, 10.2.44 through
            # 13.1.1: ``double(10,2) unsigned``, ``float(10,2) unsigned``,
            # ``double unsigned`` -- and a parser that could not read its own
            # dialect's output back would make the differ report a change on
            # every unsigned float that was never touched.
            #
            # ``ZEROFILL`` is deliberately **not** read: it is a MariaDB display
            # attribute with no field on any of these concepts, so there is
            # nowhere to put it.  It is also unrepresentable on this backend --
            # ``FLOAT``'s and ``DECIMAL``'s concepts carry no ``zerofill``, so a
            # ``float(10,2) unsigned zerofill`` column introspects here as the
            # unsigned ``FloatType`` the declaration asked for, which is the same
            # column with the padding dropped.  That is not a signedness loss and
            # it is not this branch's to invent a field for.
            unsigned = "UNSIGNED" in upper
            if upper.startswith("DOUBLE"):
                return DoubleType(self, unsigned=unsigned)
            if upper.startswith("REAL"):
                return DoubleType(self, unsigned=unsigned)
            # FLOAT. A single argument is the bit-precision p: 0..24 selects
            # 4-byte FLOAT storage and 25..53 selects 8-byte DOUBLE storage --
            # measured on all fifteen wired servers: ``FLOAT(24)`` reports
            # ``float``, ``FLOAT(25)`` and ``FLOAT(53)`` report ``double``.
            # The class follows the storage, and p itself is dropped because
            # the catalog does not record it.
            #
            # The deprecated two-argument ``FLOAT(M,D)`` is a different
            # declaration: its first number is M (total *decimal* digits), not
            # p (bits).  Measured on the wired servers, ``FLOAT(25,17)`` and
            # ``FLOAT(53,17)`` both store single-precision values
            # (1.2345678806304932, against ``DOUBLE``'s 1.2345678901234567) and
            # both report ``NUMERIC_PRECISION = M``, while one-argument
            # ``FLOAT(25)`` resolves to ``double``.  So it is read as the
            # 4-byte concept with the (M,D) display spec dropped -- FloatType
            # carries no scale, and this dialect now refuses a precision it
            # cannot round-trip.
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return FloatType(self, unsigned=unsigned)
            precision = int(nums[0]) if nums else None
            if precision is not None and precision >= 25:
                return DoubleType(self, unsigned=unsigned)
            return FloatType(self, unsigned=unsigned)

        # DECIMAL / NUMERIC / DEC / FIXED are one concept with four accepted
        # words (MariaDB's own manual says DECIMAL is synonymous with NUMERIC
        # and DEC; FIXED is the MySQL-era synonym). All four become the same
        # DecimalType carrying the default spelling, so the differ does not see
        # a change where the server sees none.
        #
        # ``unsigned`` is read for the reason given in the float branch above,
        # and the position is the same one the DECIMAL page documents:
        # ``DECIMAL[(M[,D])] [SIGNED | UNSIGNED | ZEROFILL]``, with the catalog
        # reporting ``decimal(10,2) unsigned`` on every wired server.
        if self._MARIA_DECIMAL_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return DecimalType(self, int(nums[0]), int(nums[1]),
                                   unsigned=unsigned)
            if len(nums) == 1:
                return DecimalType(self, int(nums[0]), unsigned=unsigned)
            return DecimalType(self, unsigned=unsigned)

        if self._MARIA_STRING_TYPES.match(upper):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MariaDBTinyTextType
                return MariaDBTinyTextType(dialect=self)
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MariaDBMediumTextType
                return MariaDBMediumTextType(dialect=self)
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MariaDBLongTextType
                return MariaDBLongTextType(self)
            if upper.startswith("TEXT"):
                from ..expression.types import MariaDBTextType
                return MariaDBTextType(self)
            if upper.startswith("ENUM"):
                from ..expression.types import MariaDBEnumType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MariaDBEnumType(self, values, charset=charset, collation=collation)
            if upper.startswith("SET"):
                from ..expression.types import MariaDBSetType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MariaDBSetType(self, values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBBinaryType
                return MariaDBBinaryType(self, length)
            if upper.startswith("VARBINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBVarBinaryType
                return MariaDBVarBinaryType(self, length)
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None
            if upper.startswith("VARCHAR"):
                return VarCharType(self, length)
            return CharType(self, length)

        if self._MARIA_BLOB_TYPES.match(upper):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MariaDBTinyBlobType
                return MariaDBTinyBlobType(dialect=self)
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MariaDBMediumBlobType
                return MariaDBMediumBlobType(dialect=self)
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MariaDBLongBlobType
                return MariaDBLongBlobType(dialect=self)
            from ..expression.types import MariaDBBlobType
            return MariaDBBlobType(dialect=self)

        if self._MARIA_DATE_TYPES.match(upper):
            if upper.startswith("YEAR"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MariaDBYearType
                if display_width not in MariaDBYearType.ALLOWED_DISPLAY_WIDTHS:
                    # A pre-13.0 server can still report YEAR(2). We cannot
                    # round-trip it (MariaDBYearType rejects it, and
                    # MariaDB 13.0+ would refuse the DDL), so degrade to bare
                    # YEAR -- which is the 4-byte storage YEAR always used --
                    # and say so rather than failing introspection or
                    # silently rewriting the schema.
                    warnings.warn(
                        f"Server reported YEAR({display_width}); MariaDB 13.0+ rejects "
                        "YEAR(2). Reading it as YEAR. Use old_mode=2_DIGIT_YEAR (itself "
                        "deprecated) only if the 2-digit truncation is intentional.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    display_width = None
                return MariaDBYearType(self, display_width)
            # ``DATETIME`` before ``DATE``, and the fractional-seconds precision
            # read off it. ``DATETIME`` *begins with* ``DATE``, so the order of
            # these two branches is load-bearing: with ``DATE`` first, every
            # ``DATETIME`` -- and every ``DATETIME(6)`` -- took the ``DATE``
            # branch's early return and came back as a bare ``DateTimeType``
            # with its precision dropped. Verified live on all fifteen wired
            # servers, where ``CREATE TABLE t (c DATETIME(6))`` reports
            # ``datetime(6)`` in ``COLUMN_TYPE`` and was read as
            # ``DateTimeType(precision=None)`` -- indistinguishable from a
            # ``DATETIME``. The fsp is stored: it is the number of fractional
            # digits the column keeps, so a ``DATETIME`` and a ``DATETIME(6)``
            # are different columns and the differ has to see it, exactly as it
            # already does for ``TIMESTAMP`` and ``TIME`` below.
            #
            # https://mariadb.com/docs/server/reference/data-types/date-and-time-data-types/datetime
            if upper.startswith("DATETIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                return DateTimeType(self, precision)
            if upper.startswith("DATE"):
                return DateType(self)
            if upper.startswith("TIMESTAMP"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(self, precision)
                return TimestampType(self, precision)
            if upper.startswith("TIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(self, precision)
                return TimeType(self, precision)

        if self._MARIA_JSON_TYPES.match(upper):
            return JsonType(self)

        if self._MARIA_XML_TYPES.match(upper):
            # ``XMLTYPE`` only exists from MariaDB 12.3. On an older server the
            # word cannot come out of the catalog, so the honest reading there is
            # the fallback's — ``CustomType``, "this dialect does not model
            # that" — rather than handing back a class whose formatter would
            # raise UnsupportedFeatureError on the very dialect that produced
            # it. Gated for the same reason ``supports_data_type_mariadb_xml``
            # is: parse_type must never yield a type this dialect cannot render.
            if not self.supports_data_type_mariadb_xml():
                return CustomType(self, stripped)
            return MariaDBXmlType(self)

        if self._MARIA_UUID_TYPES.match(upper):
            # ``UUID`` arrived in MariaDB 10.7 and is gated for the same reason
            # ``XMLTYPE`` is: below 10.7 the word cannot come out of that
            # server's catalog (``CREATE TABLE t (c UUID)`` fails), and handing
            # back a class whose formatter raises ``UnsupportedFeatureError``
            # would be worse than admitting ignorance. ``parse_type`` must
            # never yield a type this dialect cannot render.
            #
            # The gap this fills was measured, not assumed: ``uuid`` is written
            # by both ``format_data_type_uuid`` (the core concept) and
            # ``format_data_type_mariadb_uuid``, and before this branch
            # ``parse_type("uuid")`` fell through to ``CustomType('uuid')`` --
            # verified on all fifteen wired servers, ten of which (10.7 and up)
            # store a real ``uuid`` column. So a ``UUIDType`` column did not
            # survive a round trip through this dialect's own vocabulary, and
            # introspection reported it as a type the backend does not model.
            #
            # https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type
            if not self.supports_data_type_uuid():
                return CustomType(self, stripped)
            from ..expression.types import MariaDBUUIDType
            return MariaDBUUIDType(self)

        if self._MARIA_SPATIAL_TYPES.match(upper):
            srid = None
            # ``REF_SYSTEM_ID=<n>`` is the spelling MariaDB accepts for a
            # spatial column's reference system; the spaces the server tolerates
            # around ``=`` are tolerated here too. ``SRID <n>`` is deliberately
            # **not** recognised: it is MySQL's attribute, and every server
            # measured rejects it with errno 1064 (10.2.44 and 13.1.1 live for
            # this change; 10.6.28, 11.4.13, 11.8.9, 12.1.2 and 12.3.3 in the
            # typed-columns investigation), so it can never come out of a
            # MariaDB catalog and is not one of the spellings this dialect
            # reads back (D8).
            srid_match = re.search(r"REF_SYSTEM_ID\s*=\s*(\d+)", upper)
            if srid_match:
                srid = int(srid_match.group(1))
            from ..expression.types import (
                MariaDBGeometryCollectionType,
                MariaDBGeometryType,
                MariaDBLineStringType,
                MariaDBMultiLineStringType,
                MariaDBMultiPointType,
                MariaDBMultiPolygonType,
                MariaDBPointType,
                MariaDBPolygonType,
            )
            spatial_map = {
                "GEOMETRY": MariaDBGeometryType,
                "POINT": MariaDBPointType,
                "LINESTRING": MariaDBLineStringType,
                "POLYGON": MariaDBPolygonType,
                "MULTIPOINT": MariaDBMultiPointType,
                "MULTILINESTRING": MariaDBMultiLineStringType,
                "MULTIPOLYGON": MariaDBMultiPolygonType,
                "GEOMETRYCOLLECTION": MariaDBGeometryCollectionType,
            }
            # Dispatch on the leading **word**, not on a prefix scanned in
            # declaration order. ``GEOMETRYCOLLECTION`` begins with
            # ``GEOMETRY``, so a ``startswith`` loop that reached ``GEOMETRY``
            # first read a collection column as the generic geometry type --
            # verified live on all fifteen wired servers, where
            # ``CREATE TABLE t (c GEOMETRYCOLLECTION)`` introspected as
            # ``MariaDBGeometryType``. That is a false identity claim in the
            # worst direction: it made the differ report *no* change between a
            # ``GEOMETRYCOLLECTION`` column and a ``GEOMETRY`` one, a
            # difference MariaDB can certainly make. Every one of the eight
            # words is a single identifier, so the leading word is the whole
            # name and the map needs no ordering discipline to stay correct.
            head = re.match(r"[A-Z]+", upper)
            name = head.group(0) if head else upper
            return spatial_map.get(name, MariaDBGeometryType)(self, srid)

        # The module-level ``CustomType`` import does the job; the local re-import
        # that used to sit here made ``CustomType`` a function-local name for the
        # whole of ``parse_type``, so any *earlier* branch returning
        # ``CustomType`` hit an ``UnboundLocalError`` on a path that had never
        # executed it.
        return CustomType(self, stripped)
