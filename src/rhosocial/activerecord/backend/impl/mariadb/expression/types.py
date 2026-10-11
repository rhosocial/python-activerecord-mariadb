# src/rhosocial/activerecord/backend/impl/mariadb/expression/types.py
"""MariaDB-specific DataType subclasses.

Naming convention
-----------------
MariaDB-specific types use the ``MariaDB`` prefix to distinguish them from
the core types (which have no prefix).  This avoids ambiguity when both
core and backend types are used together.

Usage scope
-----------
These types are used **only** for MariaDB backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).

Value-object semantics
----------------------
Equality and hashing live on the core ``DataType`` base, which derives them
from :attr:`DataType.PARAMETERS` -- the closed tuple of fields that make up a
type's identity, read in order through :meth:`DataType.identity`.  Subclasses
declare their semantic parameters by widening or narrowing that tuple and must
**not** hand-write ``__eq__`` / ``__hash__``, and must not reintroduce a looser
cross-class comparison alongside ``==`` — ``==`` is the whole comparison (see the
plan's decision D4), and it is **class-exact**: two classes are never equal, which is
what keeps the eight spatial shapes and the five integer widths apart while they
share a base class.  The one method here that is deliberately *not* identity is
``is_storage_equivalent``, which answers a different question; see
:meth:`MariaDBBinaryType.is_storage_equivalent`.

Because ``PARAMETERS`` *is* identity, a field in it is a promise: flipping it has
to change the column the server builds, or the promise is false.  The five
integer classes below keep ``unsigned`` for exactly that reason — ``X`` and ``X
UNSIGNED`` really are two columns — and normalise ``zerofill`` against it at
construction, because the one combination MariaDB refuses to store is not a
column at all.  See :func:`_zerofill_signedness`.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from rhosocial.activerecord.backend.expression.types import (
    UUIDType,
    BigIntType,
    BinaryType,
    BlobType,
    DataType,
    EnumType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
    VarBinaryType,
    XmlType,
)


# ---------------------------------------------------------------------------
# Integer variants with UNSIGNED / ZEROFILL
#
# ``unsigned`` is **not** redeclared here: it is a field on the core integer
# classes since the plan's decision D5 (width is the class axis, signedness is
# a field), so the four classes below add only what MariaDB has and core does
# not — ``zerofill``, which is MariaDB-specific and has no core counterpart.
#
# ``zerofill`` is *not* independent of ``unsigned``, though: MariaDB makes it
# imply it. Every constructor below therefore normalises the pair through
# :func:`_zerofill_signedness` rather than storing the two as given, which is
# what makes ``(unsigned=False, zerofill=True)`` and
# ``(unsigned=True, zerofill=True)`` one value object — which they are, as
# columns, on every MariaDB version this backend supports.
# ---------------------------------------------------------------------------

def _zerofill_signedness(unsigned: bool, zerofill: bool) -> bool:
    """The signedness MariaDB will actually store, given these two flags.

    ``ZEROFILL`` is not independent of ``UNSIGNED`` on MariaDB, whatever the
    ``TYPE[(M)] [SIGNED | UNSIGNED | ZEROFILL]`` syntax line suggests. The
    Numeric Data Type Overview says:

        "If ZEROFILL is specified, the column will be set to UNSIGNED"

    and the INT page puts it beyond a hint:

        "If the ZEROFILL attribute has been specified, the column will
         automatically become UNSIGNED."

        "A special type of INT UNSIGNED is INT ZEROFILL, which pads out the
         values with leading zeros in SELECT results."

    So ``(unsigned=False, zerofill=True)`` does not name a column MariaDB can
    store. Measured on all fifteen wired servers — 10.2.44, 10.3.39, 10.4.34,
    10.5.29, 10.6.28, 10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.1, 12.1.2, 12.2.2,
    12.3.3, 13.0.2 and 13.1.1 — for every width this module has a class for
    (``TINYINT``, ``SMALLINT``, ``MEDIUMINT``, ``INT``, ``BIGINT``), with
    ``INT`` shown:

    ===========================  ===========================  ==============
    declared                    COLUMN_TYPE                 ``INSERT -1``
    ===========================  ===========================  ==============
    ``INT``                     ``int(11)``                 accepted
    ``INT UNSIGNED``            ``int(10) unsigned``        rejected
    ``INT ZEROFILL``            ``int(10) unsigned zerofill``  rejected
    ``INT UNSIGNED ZEROFILL``   ``int(10) unsigned zerofill``  rejected
    ``INT ZEROFILL UNSIGNED``   ``int(10) unsigned zerofill``  rejected
    ===========================  ===========================  ==============

    The last three are one column: identical ``COLUMN_TYPE``, identical
    ``SHOW CREATE TABLE`` line, and identical behaviour — none of them stores a
    negative number. ``(unsigned=False, zerofill=True)`` and
    ``(unsigned=True, zerofill=True)`` are therefore the *same column* on this
    backend, which is exactly why this function returns ``True`` whenever
    ``zerofill`` is set. That is the manual's own list of supported
    combinations read as two columns and one display flag rather than as three
    columns — it enumerates ``SIGNED``, ``UNSIGNED``, ``ZEROFILL``,
    ``UNSIGNED ZEROFILL`` and ``ZEROFILL UNSIGNED``, and says of the last two
    that they "should be replaced with simply ZEROFILL, but are still accepted
    by the parser".

    **This is MariaDB normalising the column, not the caller changing their
    mind.** The caller asked for a zero-padded column; MariaDB will hand them a
    zero-padded *unsigned* column and offers no way to decline. Normalising
    here means the value object describes what will be stored, so
    ``parse_type(rendered) == declared`` holds for every combination of width,
    signedness and zerofill — the round trip that was exact for 450 of its 600
    cells across the matrix before this, and is exact for all of them now.

    Applied at construction rather than in the formatter, deliberately. A
    formatter that emitted ``X ZEROFILL`` would write DDL whose stored range
    contradicts the declaration; one that emitted ``X UNSIGNED ZEROFILL`` while
    the object still claimed ``unsigned=False`` would write a column the object
    does not describe. Both are worse than the server's own normalisation being
    performed once, in the place where a caller can see it happen.

    Note what is **not** done here: ``unsigned`` stays in ``PARAMETERS`` on all
    five classes. Dropping it was considered, on the strength of the same
    documentation, and rejected on the same measurements — ``X`` and
    ``X UNSIGNED`` really are two columns (``int(11)`` vs ``int(10) unsigned``,
    and the first accepts ``-1`` while the second does not), so taking
    ``unsigned`` out of identity would hide a change MariaDB can make. Only the
    combination the server refuses to store is normalised; the distinction that
    is real stays in the identity.

    Official Documentation:
    https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
    https://mariadb.com/docs/server/reference/data-types/numeric-data-types/int
    """
    return True if zerofill else unsigned

class MariaDBIntType(IntegerType):
    """MariaDB ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL.

    ``zerofill=True`` implies ``unsigned=True``: MariaDB stores a zero-padded
    column as unsigned whatever the declaration says, so the object records what
    will be stored. See :func:`_zerofill_signedness` for the documentation and
    the measurements; the short form is that ``INT ZEROFILL`` and
    ``INT UNSIGNED ZEROFILL`` are one column on this backend.
    """

    name = "mariadb_int"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False):
        super().__init__(dialect)
        self.unsigned = _zerofill_signedness(unsigned, zerofill)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MariaDBTinyIntType(TinyIntType):
    """MariaDB ``TINYINT`` with optional UNSIGNED / ZEROFILL.

    ``zerofill=True`` implies ``unsigned=True`` — see
    :func:`_zerofill_signedness`. Worth stating here because this is the width
    where the implication bites hardest: ``TINYINT`` signed spans
    ``-128..127`` and ``TINYINT UNSIGNED`` spans ``0..255``, so a zero-padded
    ``TINYINT`` is an eight-bit non-negative column whatever was asked for.
    """

    name = "mariadb_tinyint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False):
        super().__init__(dialect)
        self.unsigned = _zerofill_signedness(unsigned, zerofill)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MariaDBSmallIntType(SmallIntType):
    """MariaDB ``SMALLINT`` with optional UNSIGNED / ZEROFILL.

    ``zerofill=True`` implies ``unsigned=True`` — see
    :func:`_zerofill_signedness`.
    """

    name = "mariadb_smallint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False):
        super().__init__(dialect)
        self.unsigned = _zerofill_signedness(unsigned, zerofill)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MariaDBMediumIntType(IntegerType):
    """MariaDB ``MEDIUMINT`` — 3 bytes, ``-8388608``..``8388607`` signed.

    MariaDB's own ``MEDIUMINT`` page gives the column "3 bytes" of storage and
    the two ranges ``-8388608`` to ``8388607`` (signed) and ``0`` to
    ``16777215`` (unsigned) — a width of its own, sitting between the 2-byte
    ``SMALLINT`` and the 4-byte ``INT``. Its syntax line is
    ``MEDIUMINT[(M)] [SIGNED | UNSIGNED | ZEROFILL]``, so it carries exactly the
    same attribute pair as its siblings and is handled the same way.

    **Why it is not a spelling of an existing type.** A width is a class in this
    hierarchy (D5), and 3 bytes is neither the 1-, 2-, 4- nor 8-byte concept, so
    there is nothing for it to be a synonym of. Mapping it onto
    :class:`MariaDBIntType` — which is what ``parse_type`` used to do — makes a
    3-byte column compare ``==`` to a 4-byte one and the differ report a change
    that was never made, or hide one that was.

    **Why it nevertheless derives from the 4-byte concept.** Not to claim the
    width: 3 bytes is not 4, and the docstring says so because the inheritance
    line is the one place a reader would otherwise be misled. It is to reuse the
    *signedness* contract — the type-checked ``unsigned`` field and its place in
    ``PARAMETERS`` — which is core's and which the module comment above says
    must not be re-declared per subclass. What a ``MEDIUMINT`` column *is* stays
    distinguishable because ``DataType.__eq__`` is class-exact, so this never
    compares equal to :class:`MariaDBIntType`; the inheritance buys the shared
    field and the separate ``name`` keeps the dispatch families apart.

    ``SPELLINGS`` is narrowed to the two words MariaDB actually uses for this
    width, so the class does not inherit the 4-byte concept's ``integer`` /
    ``int`` list it does not share. MariaDB documents ``MEDIUMINT`` and its
    synonym ``INT3``, and both are accepted here; the server normalises ``INT3``
    to ``MEDIUMINT`` in the catalog (verified: ``INT3`` introspects as
    ``mediumint(9)``), so ``MEDIUMINT`` is what gets rendered.

    ``zerofill=True`` implies ``unsigned=True`` — see
    :func:`_zerofill_signedness`. The catalog says so in the width's own terms:
    a zero-padded ``MEDIUMINT`` is stored as ``mediumint(8) unsigned zerofill``,
    which is the 8-digit unsigned range, not the 9-digit signed one.
    """

    name = "mariadb_mediumint"

    SPELLINGS = ("mediumint", "int3")

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False, spelling: str = "mediumint"):
        super().__init__(
            dialect,
            unsigned=_zerofill_signedness(unsigned, zerofill),
            spelling=spelling,
        )
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MariaDBBigIntType(BigIntType):
    """MariaDB ``BIGINT`` with optional UNSIGNED / ZEROFILL.

    ``zerofill=True`` implies ``unsigned=True`` — see
    :func:`_zerofill_signedness`.
    """

    name = "mariadb_bigint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False):
        super().__init__(dialect)
        self.unsigned = _zerofill_signedness(unsigned, zerofill)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MariaDBTinyBlobType(BlobType):
    """MariaDB ``TINYBLOB`` — maximum 255 bytes."""

    name = "mariadb_tinyblob"


class MariaDBBlobType(BlobType):
    """MariaDB ``BLOB`` — maximum 65,535 bytes."""

    name = "mariadb_blob"


class MariaDBMediumBlobType(BlobType):
    """MariaDB ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    name = "mariadb_mediumblob"


class MariaDBLongBlobType(BlobType):
    """MariaDB ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    name = "mariadb_longblob"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MariaDBTinyTextType(TextType):
    """MariaDB ``TINYTEXT`` — maximum 255 bytes."""

    name = "mariadb_tinytext"


class MariaDBTextType(TextType):
    """MariaDB ``TEXT`` — maximum 65,535 bytes."""

    name = "mariadb_text"


class MariaDBMediumTextType(TextType):
    """MariaDB ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    name = "mariadb_mediumtext"


class MariaDBLongTextType(TextType):
    """MariaDB ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    name = "mariadb_longtext"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MariaDBBitType(DataType):
    """MariaDB ``BIT[(n)]`` — a bit-field type: *bits*, not a number.

    Deliberately **not** :class:`BooleanType` and deliberately **not** an
    ``unsigned`` flag on an integer class. ``BIT(8)`` holds eight bits; it is
    compared with ``b'1010'`` literals, read with ``ORD``/``CONV``, and carries
    no arithmetic beyond bitwise operators. ``BIT(1)`` looks like a boolean and
    is not one — it accepts only ``0`` and ``1`` and does not cast implicitly
    to ``TRUE``/``FALSE``, exactly the argument the plan's decision D6 records
    for SQL Server's ``BIT`` against MySQL/PostgreSQL's ``BIT(n)``.

    ``n`` is the declared width in bits. MariaDB pads to it, so a shorter input
    is not an error: the *value* is length-``n``, whatever was written.
    ``n=None`` means the type was declared bare, which MariaDB treats as
    ``BIT(1)``.

    On ``DataType`` rather than derived from anything in core because SQL:2016
    has **no bit-string type** — it was proposed and dropped — so there is no
    core concept for this to be an instance of. See the datatype-hierarchy plan,
    decision D7: sitting directly on ``DataType`` is a legitimate decision, but
    it has to be written down, and this is the writing down.

    Args:
        dialect: The dialect this type is bound to. First positional parameter,
            as for every ``DataType`` — with ``n`` first, a caller following the
            documented convention would have their dialect silently stored as
            the bit count, and the error would only surface at render time.
        n: Declared width in bits, or ``None`` for a bare ``BIT``.
    """

    name = "mariadb_bit"

    n: Optional[int] = None

    def __init__(self, dialect=None, n: Optional[int] = None):
        super().__init__(dialect)
        self.n = n

    PARAMETERS = ("n",)

# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MariaDBYearType(DataType):
    """MariaDB ``YEAR[(4)]`` — a one-byte year.

    ``display_width`` accepts only ``None`` (bare ``YEAR``) or ``4``.
    ``YEAR(2)`` was deprecated in 2012 and is **rejected outright by
    MariaDB 13.0+** (verified: ``CREATE TABLE t (y YEAR(2))`` succeeds on
    12.2/12.3 and fails with errno 1064 on 13.0/13.1). Accepting it here
    would let a schema that builds on an older server fail to deploy on a
    newer one, so it is rejected at construction time regardless of dialect.

    On ``DataType`` for two reasons, both about the concept rather than the
    storage. First, SQL:2016 has no ``YEAR`` type at all: a year is not a date,
    so the standard offers only ``DATE``/``TIMESTAMP`` for anything
    calendar-ish, and a MariaDB ``YEAR`` column is a year. Second, the
    *value* is not a year number: MariaDB stores ``YEAR`` as a single byte with
    an offset, so ``0`` is the zeroth year of the cycle rather than the integer
    zero, which is why it is not ``TINYINT`` with a different name. See the
    datatype-hierarchy plan, decision D7.
    """

    name = "mariadb_year"

    display_width: Optional[int] = None

    #: Widths this backend is willing to emit.
    ALLOWED_DISPLAY_WIDTHS = (4,)

    def __init__(self, dialect=None, display_width: Optional[int] = None):
        super().__init__(dialect)
        if display_width is not None and display_width not in self.ALLOWED_DISPLAY_WIDTHS:
            allowed = ", ".join(str(w) for w in self.ALLOWED_DISPLAY_WIDTHS)
            raise ValueError(
                f"YEAR display_width must be None or {allowed}; got {display_width!r}. "
                "YEAR(2) was deprecated in 2012 and is not accepted by MariaDB 13.0+."
            )
        self.display_width = display_width

    PARAMETERS = ("display_width",)

# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MariaDBBinaryType(BinaryType):
    """MariaDB ``BINARY[(n)]`` — fixed-length binary.

    Derives from the core :class:`BinaryType` because the generic name
    ``mariadb_binary`` already declares the concept: ``BINARY(n)`` on MariaDB
    and ``BinaryType`` are the same storage, only spelled differently. The base
    class supplies ``__init__``, ``length`` and ``PARAMETERS`` — the local
    copies were byte-for-byte identical and are gone.

    Why that matters: ``isinstance(col.data_type, BinaryType)`` is now true for a
    MariaDB fixed-length byte string, which is what a caller asking "is this a
    fixed-width byte column?" wants. It was false before, which meant every
    such caller had to know this backend's private class list — and the MySQL
    twin, which already derived from ``BinaryType``, disagreed with it for no
    reason at all.
    """

    # ``BINARY(n)``'s width is the type: a BINARY(16) column cannot hold what a
    #     BINARY(8) column can, so it is part of identity.

    PARAMETERS = ("length",)

    name = "mariadb_binary"


class MariaDBUUIDType(UUIDType):
    """MariaDB's native ``UUID`` column type, available since **MariaDB 10.7**.

    Documented at
    https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type

    This is a real column type, not an emulation over ``BINARY(16)``, and the
    differences are behavioural rather than cosmetic:

    * values are stored **byte-swapped** so that a UUIDv1's node-then-timestamp
      ordering is index-friendly — a plain 16-byte binary column has no such
      ordering;
    * retrieval is the RFC 4122 string form;
    * ``UUID_SHORT()`` is **rejected** (it is not a full-length UUID);
    * braces around the literal are **rejected**, though several implementations
      accept them.

    Derives from the core :class:`UUIDType` because it *is* the UUID concept:
    the value means a UUID on every backend that has one, which is what makes
    ``isinstance(col.data_type, UUIDType)`` answerable across backends. The
    storage above is this backend's own choice and belongs here in the
    docstring, not in the inheritance.

    Before 10.7 there is no UUID type, and the idiom is
    :class:`MariaDBBinaryType` with ``length=16`` — a 16-byte binary column and
    nothing more. That is a different column, and the schema differ should say
    so; there is no equivalence between the two, which is why this class needs
    no comparison helper beyond ``==``.

    Args:
        dialect: The dialect this type is bound to. First positional parameter,
            as for every ``DataType``.

    Raises:
        UnsupportedFeatureError: when rendering against a server older than
            10.7, which has no ``UUID`` type at all.
    """

    name = "mariadb_uuid"


class MariaDBVarBinaryType(VarBinaryType):
    """MariaDB ``VARBINARY(n)`` — variable-length binary.

    The variable-length sibling of :class:`MariaDBBinaryType` and, for the same
    reason, derived from the core :class:`VarBinaryType`: the generic name
    ``mariadb_varbinary`` declares the concept and the base class supplies
    ``__init__``, ``length`` and the (previously duplicated) ``PARAMETERS``.
    """

    PARAMETERS = ("length",)

    name = "mariadb_varbinary"


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------

class MariaDBXmlType(XmlType):
    """MariaDB ``XMLTYPE`` — MariaDB's own XML column type, from **12.3**.

    Documented at
    https://mariadb.com/docs/server/reference/data-types/string-data-types/xmltype

    MariaDB had no XML type at all before 12.3: not a native one, not an alias,
    no ``XML`` keyword in its DDL grammar (``CREATE TABLE t (c XML)`` fails with
    errno 4161, "Unknown data type: 'XML'"). 12.3 added a real one, so from that
    release this backend can store a genuine XML column instead of
    substituting ``TEXT``.

    What the type is and is not, per its own documentation:

    * **basic storage only** — "provides basic XML storage capabilities only,
      without validation or specialized XML-specific functionality". No schema
      association, no well-formedness check on input, no XPath.
    * **4 GB maximum** — "Maximum storage capacity: 4GB (same as ``LONGBLOB``)".
      That is a real ceiling a ``MEDIUMTEXT`` column does not share.
    * **it converts to a string when a string function touches it**, and it is
      maintained as a string in temporary tables, which is why the initial
      implementation is deliberately thin.
    * **no length may be given** — ``XMLTYPE(100)`` is an error ("Data type
      'XMLTYPE' doesn't support LENGTH attribute"), so the type carries no
      parameters at all. An associated XML Schema is a column or domain
      attribute on every backend, never part of the type's identity.
    * **Oracle compatibility is the design goal** — the type exists to be
      substitutable for Oracle's ``XMLType``.

    Derives from the core :class:`~...expression.types.XmlType` because it *is*
    the XML concept: the value means "an XML document" on every backend that
    has one, which is what makes ``isinstance(col.data_type, XmlType)``
    answerable across backends. It is deliberately **not** a
    :class:`...expression.types.TextType` — core's own ``XmlType`` docstring
    makes that exact argument ("'it is text' is false where it matters most"),
    and here it is doubly true: ``TEXT`` accepts a length, ``XMLTYPE`` does not,
    and ``TEXT`` is not capped at 4 GB while ``XMLTYPE`` is.

    Below 12.3 there is no such column type and the framework's substitute is
    ``TextType`` — a character string with no XML semantics. That is a different
    column, which is why ``MariaDBTypeSupportMixin.format_data_type_mariadb_xml``
    refuses to emit ``XMLTYPE`` on an older server instead of quietly handing
    back ``TEXT``.

    Args:
        dialect: The dialect this type is bound to. First positional parameter,
            as for every ``DataType``.

    Raises:
        UnsupportedFeatureError: when rendering against a server older than
            12.3, which has no ``XMLTYPE`` type at all.
    """

    name = "mariadb_xml"


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MariaDBEnumType(EnumType):
    """MariaDB ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE.

    Derives from the core :class:`EnumType`, which owns the ``values``
    validation and the value-object semantics; the local checks below are kept
    only so the message names the class the caller actually constructed. The
    MariaDB-only additions — ``charset`` and ``collation``, emitted as
    ``CHARACTER SET`` / ``COLLATE`` suffixes on the ``ENUM(...)`` form — are
    why ``PARAMETERS`` stays local: it must widen the base's
    ``(values,)`` to ``(values, charset, collation)``, which is what makes an
    enum with a collation differ from the same enum without one.

    This is the twin of ``MySQLEnumType`` and must stay isomorphic to it: the
    two backends write the same DDL for the same declaration, and a schema
    written for one is expected to migrate to the other unchanged.
    """

    name = "mariadb_enum"

    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None):
        if values is None:
            raise ValueError("MariaDBEnumType requires values")
        if not values:
            raise ValueError("ENUM must have at least one value")
        super().__init__(dialect, values=values)
        self.charset = charset
        self.collation = collation

    PARAMETERS = ("values", "charset", "collation",)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={list(self.values)!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MariaDBSetType(DataType):
    """MariaDB ``SET('val', ...)`` with optional CHARACTER SET / COLLATE.

    Deliberately **not** an :class:`EnumType` subclass, and the difference is
    in the value, not in the DDL: an ``ENUM`` holds **exactly one** of its
    labels, a ``SET`` holds **zero or more**. ``SET('read','write')`` can be
    ``''``, ``'read'``, ``'write'`` or ``'read,write'``; ``ENUM`` with those two
    labels can be only the first two. A column holding a ``SET`` can therefore
    hold a value an ``ENUM`` column of the same labels cannot, and its
    membership operations are ``FIND_IN_SET`` rather than equality, so it is a
    different concept rather than an ``ENUM`` with a flag.

    On ``DataType`` for the same reason as :class:`MariaDBBitType`: SQL:2016
    has no ``SET`` type. ``SET`` is MariaDB's own, and the plan's decision D7
    requires that sitting directly on ``DataType`` be justified in writing.
    """

    name = "mariadb_set"

    values: Tuple[str, ...] = ()
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
        if values is None:
            raise ValueError("MariaDBSetType requires values")
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = tuple(values)
        self.charset = charset
        self.collation = collation

    PARAMETERS = ("values", "charset", "collation",)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={list(self.values)!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MariaDBGeometryType(DataType):
    """MariaDB ``GEOMETRY`` with optional SRID.

    The generic spatial value: one ``GEOMETRY`` column may hold a point, a
    polygon, several of them, or none of the named shapes, tagged internally.
    That is why the seven classes below derive from **this** one rather than the
    other way round: ``POINT`` is not a special case that *is* a geometry, it
    is a geometry whose contents are constrained, so narrowing the parent is
    the honest direction.

    ``srid`` names the coordinate reference system the column declares, spelled
    ``REF_SYSTEM_ID=<n>`` in MariaDB DDL (``SRID <n>`` is MySQL's spelling and
    a syntax error here; measured on every wired server). The declaration is
    recorded but not enforced: stored values keep their own SRID, so two
    ``POINT`` columns declaring different systems are still not
    interchangeable — the same numbers mean different places — which is why it
    belongs in ``PARAMETERS`` and a diff must see it change.

    On ``DataType`` because SQL:2016 has **no spatial types**: the standard's
    type list stops at character, numeric, datetime, boolean, and the
    user-defined extension point. Every spatial type here is MariaDB's own (the
    OGC simple-features set that MyISAM/Aria/InnoDB implement natively), so
    there is no core concept for one to be an instance of. Adding a spatial
    family to core is a separate design decision — the datatype-hierarchy plan's
    out-of-scope list — and is not settled by inheritance here. See decision D7.
    """

    name = "mariadb_geometry"

    srid: Optional[int] = None

    def __init__(self, dialect=None, srid: Optional[int] = None):
        super().__init__(dialect)
        self.srid = srid

    PARAMETERS = ("srid",)

class MariaDBPointType(MariaDBGeometryType):
    """MariaDB ``POINT`` with optional SRID — one coordinate pair ``(x, y)``."""

    name = "mariadb_point"


class MariaDBLineStringType(MariaDBGeometryType):
    """MariaDB ``LINESTRING`` with optional SRID — a path of two or more points.

    The open variant: a closed path is a :class:`MariaDBPolygonType`, and the
    difference is what the value *means* (a ring bounds an area), not how the
    points are stored.
    """

    name = "mariadb_linestring"


class MariaDBPolygonType(MariaDBGeometryType):
    """MariaDB ``POLYGON`` with optional SRID — a closed path bounding an area.

    Closed by the type rather than by convention, which is the difference from
    :class:`MariaDBLineStringType`: the first and last vertex coincide and the
    ring has an interior, so a diff sees a real change of concept.
    """

    name = "mariadb_polygon"


class MariaDBMultiPointType(MariaDBGeometryType):
    """MariaDB ``MULTIPOINT`` with optional SRID — a set of points.

    Separate from :class:`MariaDBPointType` because the value may be empty or
    hold several points, which ``POINT`` cannot.
    """

    name = "mariadb_multipoint"


class MariaDBMultiLineStringType(MariaDBGeometryType):
    """MariaDB ``MULTILINESTRING`` with optional SRID — a set of open paths."""

    name = "mariadb_multilinestring"


class MariaDBMultiPolygonType(MariaDBGeometryType):
    """MariaDB ``MULTIPOLYGON`` with optional SRID — a set of area-bounding rings."""

    name = "mariadb_multipolygon"


class MariaDBGeometryCollectionType(MariaDBGeometryType):
    """MariaDB ``GEOMETRYCOLLECTION`` with optional SRID — a heterogeneous set.

    The one spatial type that may mix kinds: a collection of points *and*
    polygons together, which no single-shape class above can express.
    """

    name = "mariadb_geometrycollection"

