# src/rhosocial/activerecord/backend/impl/mariadb/protocols/types.py
"""MariaDB native data-type protocol.

The shape of the questions a MariaDB type family can be asked that the
naming convention cannot answer on its own.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MariaDBTypeSupport(Protocol):
    """MariaDB's own data types, and the capabilities they carry.

    What this protocol is for
    -------------------------
    Core's :class:`~...dialect.protocols.DataTypeSupport` already covers
    "can this dialect render the concept named X" through the
    ``format_data_type_<name>`` / ``supports_data_type_<name>`` naming family,
    and that family is deliberately **not** enumerated here: a type's generic
    ``name`` is the contract, so a backend that adds one needs no change to the
    protocol. Thirty-odd ``mariadb_*`` names are therefore already declared by
    virtue of the formatters existing, and restating them as stubs here would
    add a second list to keep in step with the first, not a guarantee.

    What the naming family genuinely cannot express is the *attributes* a type
    carries — the parts where a MariaDB type can do more than its core concept,
    or where the honest answer is narrower than the type name suggests. Those
    are the members below, and each one is a question a caller migrating a
    schema has to ask before writing DDL.

    Related protocols
    -----------------
    :class:`MariaDBSetTypeSupport` covers the ``SET`` type's expressions and
    membership operators; :class:`MariaDBSpatialSupport` covers the spatial
    *functions*. Neither says anything about the type declarations, which is
    what this protocol is for — including the seven spatial column types and
    the one spatial ``GEOMETRY`` type, whose storage attribute (``srid``) no
    other MariaDB protocol mentions.

    Version Requirements
    --------------------
    All members below hold for every MariaDB version this backend supports.
    No gate is claimed where none has been measured, and the one boundary that
    *is* known — ``YEAR(2)`` being rejected outright by MariaDB 13.0+ — is
    enforced inside :class:`~...expression.types.MariaDBYearType` at
    construction, which is a stricter and more useful place for it than a
    capability flag nobody is obliged to consult.

    The two members that *are* version-dependent answer for the **server**, not
    for the type: :meth:`supports_mariadb_xml_type` is false below 12.3 because
    the column type does not exist there, which is a fact about MariaDB versions
    and not about the type's shape. The per-type rendering gate that callers
    actually branch on is ``supports_data_type_mariadb_xml`` on the dialect,
    which is the same comparison read through the naming convention.
    """

    def supports_mariadb_integer_attributes(self) -> bool:
        """Whether ``UNSIGNED`` and ``ZEROFILL`` may be written on an integer column.

        Both are MariaDB extensions to the integer types and both survive
        :meth:`format_data_type_mariadb_int` and its four width siblings as
        trailing modifiers, in MariaDB's documented order — ``INT UNSIGNED``,
        ``BIGINT UNSIGNED ZEROFILL``.

        They are **not independent**, and that is the part a caller writing DDL
        has to know. ``UNSIGNED`` is a real schema decision on its own: it
        doubles the range of the width (``TINYINT UNSIGNED`` is ``0``..``255``,
        not ``-128``..``127``) and is in the type's identity, so the differ sees
        it change. ``ZEROFILL`` is a display attribute — leading zeros in
        ``SELECT`` output — that **MariaDB resolves into ``UNSIGNED`` for you**:
        the Numeric Data Type Overview says "If ``ZEROFILL`` is specified, the
        column will be set to ``UNSIGNED``", and the ``INT`` page says "A special
        type of ``INT UNSIGNED`` is ``INT ZEROFILL``". Measured on all fifteen
        wired servers, 10.2.44 through 13.1.1: ``CREATE TABLE t (c INT
        ZEROFILL)`` reports ``int(10) unsigned zerofill``, identical to what
        ``INT UNSIGNED ZEROFILL`` reports and identical in ``SHOW CREATE TABLE``,
        and neither of the two accepts ``-1`` while plain ``INT`` does.

        So a caller cannot ask for a zero-padded *signed* integer here, and this
        backend does not pretend otherwise: the ``MariaDB*IntType`` constructors
        normalise the pair (see ``_zerofill_signedness`` in
        ``expression/types.py``), which is why ``X ZEROFILL`` and ``X UNSIGNED
        ZEROFILL`` are one value object and not merely one column.

        The overview's note that ``UNSIGNED ZEROFILL`` "should be replaced with
        simply ``ZEROFILL``, but [is] still accepted by the parser" is about
        *spelling*, not about storage — which is why this backend always emits
        the explicit form: it says what the server will store, and it is what
        ``parse_type`` reads back.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/int
        """
        ...

    def supports_mariadb_mediumint_width(self) -> bool:
        """Whether the 3-byte ``MEDIUMINT`` width is a type of its own here.

        It is, and it has to be: ``MEDIUMINT`` is "3 bytes" with ranges
        ``-8388608``..``8388607`` / ``0``..``16777215`` — neither the 2-byte nor
        the 4-byte concept — so mapping it onto ``mariadb_int`` would let a
        3-byte column compare equal to a 4-byte one. Answering no would be a
        different kind of wrong: the width does exist, on every MariaDB release
        this backend supports, and refusing the word would be refusing a real
        type. ``mariadb_mediumint`` therefore exists alongside the other four
        widths.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/numeric-data-types/mediumint
        """
        ...

    def supports_mariadb_xml_type(self) -> bool:
        """Whether this server has the native ``XMLTYPE`` column type (12.3+).

        MariaDB 12.3 introduced it; before that there is no XML type of any kind
        (``CREATE TABLE t (c XML)`` fails with errno 4161) and the framework's
        substitute is ``TextType``. Where the type exists it is real storage,
        not a relabelling of text: "basic XML storage capabilities only, without
        validation", 4 GB maximum "same as ``LONGBLOB``", and no length may be
        specified at all. Those differences are why the gate has to be a gate —
        answering yes below 12.3 either gets the caller DDL the server rejects
        or, worse, hands them a ``TEXT`` column that is not what they asked for.

        Official Documentation:
        https://mariadb.com/docs/server/reference/data-types/string-data-types/xmltype
        """
        ...

    def supports_mariadb_year_display_width(self) -> bool:
        """Whether an explicit ``YEAR(4)`` may be written.

        ``YEAR`` alone means ``YEAR(4)``, so the width is legacy decoration that
        the server accepts for compatibility. ``YEAR(2)`` — the two-digit form —
        was deprecated in 2012 and is rejected by MariaDB 13.0+, which is why
        :class:`~...expression.types.MariaDBYearType` refuses to construct one
        rather than letting the DDL fail on a newer server.
        """
        ...

    def supports_mariadb_enum_charset(self) -> bool:
        """Whether ``CHARACTER SET`` / ``COLLATE`` may be written on an ``ENUM``.

        MariaDB allows a per-column character set and collation on the string
        types, which is why :class:`~...expression.types.MariaDBEnumType` exists
        alongside the core :class:`~...expression.types.EnumType`: it carries the
        two attributes in ``PARAMETERS`` so that an enum with a collation
        compares unequal to the same labels without one.

        The framework treats a charset as a *field* on a type rather than as a
        separate national-character type, which is a deliberate decision shared
        with the core ``string`` types — see their module docstring.
        """
        ...

    def supports_mariadb_geometry_srid(self) -> bool:
        """Whether a spatial column may declare its reference system.

        ``POINT REF_SYSTEM_ID=4326`` names the coordinate reference system the
        column is declared for. MariaDB's spelling is ``REF_SYSTEM_ID=<n>`` --
        ``SRID <n>`` is MySQL's attribute and is rejected with errno 1064 by
        every MariaDB server measured -- so only the former is rendered or
        read back. It is a *declaration*, not a constraint: stored values keep
        their own SRID and MariaDB does not enforce the attribute against them.
        Two spatial columns declaring different systems are still not
        interchangeable -- the same numbers mean different places -- so the
        schema differ must see the difference. That is why ``srid`` is in
        ``PARAMETERS`` on the eight ``MariaDB*`` spatial classes rather than
        being a table option.

        The declaration is readable back from ``I_S.GEOMETRY_COLUMNS.SRID``,
        not from ``COLUMN_TYPE`` (MariaDB reports the bare ``point`` there).
        """
        ...

    def supports_mariadb_sized_text(self) -> bool:
        """Whether the four bounded-text types exist (``TINYTEXT``..``LONGTEXT``).

        They are separate types rather than spellings of the core ``text``
        because the maximum length *is* the type: a ``TINYTEXT`` column cannot
        hold what a ``LONGTEXT`` can, and a schema that switches between them has
        made a real change that a diff must report. Core's ``TextType`` carries
        no length, so each is a ``mariadb_*text`` class of its own.
        """
        ...

    def supports_mariadb_sized_blob(self) -> bool:
        """Whether the four bounded-blob types exist (``TINYBLOB``..``LONGBLOB``).

        The byte-storage counterpart of
        :meth:`supports_mariadb_sized_text`, for the same reason: the length is
        the type. ``BLOB`` — core's concept — is the 65,535-byte one, so the
        unbounded ``blob`` and MariaDB's ``mariadb_blob`` are the same 4-byte-limit
        storage under two names, and only one of them is MariaDB's own dispatch
        key.
        """
        ...

    def supports_mariadb_uuid_type(self) -> bool:
        """Whether this server has the native ``UUID`` column type.

        MariaDB 10.7 introduced it, documented at
        https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type
        It is a real column type, not an emulation over ``BINARY(16)``: values
        are stored byte-swapped so that UUIDv1 ordering is index-friendly,
        ``UUID_SHORT()`` is rejected, and braces in the literal form are
        refused.

        Below 10.7 there is no UUID type and the idiom is
        :class:`~...expression.types.MariaDBBinaryType` with ``length=16``,
        which is a 16-byte binary column and nothing more — so on such a server
        a caller wanting a UUID should build that, not this class.
        """
        ...
