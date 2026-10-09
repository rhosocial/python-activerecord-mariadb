# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_type_protocol.py
"""
MariaDB type protocol conformance tests.

Verifies the two-level data-type contract between the core ``DataType``
system and the MariaDB backend:

- ``supports_data_type_<name>`` / ``format_data_type_<name>`` 1:1
  correspondence on ``MariaDBDialect``;
- ``supports_data_types()`` merges the ``mariadb_*`` namespaced family with
  the core family;
- ``suggested_data_types()`` values are real ``DataType`` classes and its
  keys are disjoint from the supported keys;
- ``MariaDBEnumType`` renders ``ENUM('a','b')`` (with charset/collation
  extensions);
- the integer attribute pair ``UNSIGNED`` / ``ZEROFILL`` is honoured as two
  independent flags, so every width x signedness x zerofill cell round-trips;
- ``MEDIUMINT`` is the 3-byte width and a class of its own, not the 4-byte
  ``mariadb_int``;
- the ``xml`` substitute follows the server: ``TextType`` below MariaDB 12.3,
  the native ``XMLTYPE`` from 12.3;
- dialect-specific range checks live in the formatters (DECIMAL
  precision/scale, the FLOAT(p) refusal, fractional-seconds precision);
- ``dialect_options`` forwards through construction and participates in
  equality.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins import DataTypeMixin
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BooleanType,
    CustomType,
    DataType,
    DecimalType,
    DoubleType,
    EnumType,
    FloatType,
    IntegerType,
    RealType,
    SmallIntType,
    TextType,
    TimestampType,
    TinyIntType,
    UUIDType,
    XmlType,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.schema import MariaDBSchemaDiffer
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBBigIntType,
    MariaDBBinaryType,
    MariaDBBlobType,
    MariaDBEnumType,
    MariaDBIntType,
    MariaDBMediumIntType,
    MariaDBSetType,
    MariaDBSmallIntType,
    MariaDBTextType,
    MariaDBTinyIntType,
    MariaDBUUIDType,
    MariaDBXmlType,
)
from rhosocial.activerecord.backend.impl.mariadb.protocols.types import (
    MariaDBTypeSupport,
)
from rhosocial.activerecord.backend.introspection.types import ColumnInfo


@pytest.fixture
def dialect():
    # 10.7 is the floor for the native UUID type, so the fixture sits
    # just above it rather than below it.
    return MariaDBDialect(version=(10, 7, 0))


class TestSupportFormatCorrespondence:
    """Every format_data_type_<name> has supports_data_type_<name>, 1:1."""

    def test_format_family_equals_supports_family(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("format_data_type_")
        }
        support_names = {
            member[len("supports_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("supports_data_type_")
        }
        assert format_names, "MariaDBDialect must implement format_data_type_* members"
        assert format_names == support_names

    def test_supports_data_types_covers_every_formatter(self, dialect):
        """Every formatter is either in the mapping or gated off by version.

        ``supports_data_types()`` is built by walking the formatters and keeping
        the ones whose ``supports_*`` says yes, so one direction is true by
        construction; this asserts the other, that nothing is silently dropped,
        and names the exceptions.

        The equality this used to assert holds only while no formatter is
        version-gated. Two are now -- ``mariadb_xml`` needs 12.3 -- and the
        fixture sits at 10.7, so the correct statement is the difference below
        rather than ``==``: a formatter that exists and whose ``supports_*``
        answers no is a deliberate gate, and the gate is checked separately
        (``test_uuid_is_gated_at_10_7``, and the XML gate tests below).
        """
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("format_data_type_")
        }
        supported = dialect.supports_data_types()
        assert set(supported) <= format_names
        assert format_names - set(supported) == {"mariadb_xml"}

    def test_every_formatter_is_in_the_mapping_on_a_current_server(self):
        """At 12.3+ nothing is gated off, so the original equality holds again."""
        current = MariaDBDialect(version=(12, 3, 0))
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("format_data_type_")
        }
        assert set(current.supports_data_types()) == format_names

    def test_supports_data_types_returns_classes(self, dialect):
        for name, klass in dialect.supports_data_types().items():
            assert isinstance(klass, type), name
            assert issubclass(klass, DataType), name

    def test_inherits_mixin_scan_implementation(self, dialect):
        assert MariaDBDialect.supports_data_types is DataTypeMixin.supports_data_types


class TestSupportsDataTypesMapping:
    """supports_data_types() merges mariadb_* namespaced and core entries."""

    def test_includes_mariadb_namespaced_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "mariadb_int" in supported
        assert supported["mariadb_int"] is MariaDBIntType
        assert "mariadb_enum" in supported
        assert "mariadb_set" in supported
        assert supported["mariadb_uuid"] is MariaDBUUIDType

    def test_includes_core_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "integer" in supported
        assert supported["integer"] is IntegerType
        assert "varchar" in supported
        assert "decimal" in supported
        assert "json" in supported

    def test_per_type_support_methods_are_truthful(self, dialect):
        supported = dialect.supports_data_types()
        for name in supported:
            checker = getattr(dialect, f"supports_data_type_{name}")
            assert checker() is True, name


class TestSuggestedDataTypes:
    """suggested_data_types(): real classes, disjoint from supported keys."""

    def test_values_are_data_type_classes(self, dialect):
        suggestions = dialect.suggested_data_types()
        for key, klass in suggestions.items():
            assert isinstance(klass, type), key
            assert issubclass(klass, DataType), key

    def test_keys_disjoint_from_supported(self, dialect):
        suggestions = dialect.suggested_data_types()
        supported = dialect.supports_data_types()
        assert not (set(suggestions) & set(supported))

    def test_uuid_is_rendered_not_suggested(self, dialect):
        """MariaDB has a native ``UUID`` column type from 10.7, so it renders.

        It used to be *suggested*, pointing at a class that stood for the
        pre-10.7 ``BINARY(16)`` emulation. On every supported server that
        produced a column which is not a UUID -- stored without the byte-swap
        that makes UUIDv1 ordering index-friendly, and accepting inputs the real
        type rejects (``UUID_SHORT()``, braces)."""
        assert "uuid" not in dialect.suggested_data_types()
        assert dialect.supports_data_types()["mariadb_uuid"] is MariaDBUUIDType

    def test_uuid_type_renders_in_direct_column_expression(self, dialect):
        data_type = MariaDBUUIDType(dialect)
        column = ColumnDefinition(dialect, "id", data_type)
        assert dialect.supports_data_type_mariadb_uuid() is True
        assert column.to_sql() == ("`id` UUID", ())

    def test_uuid_is_gated_at_10_7(self):
        """Below 10.7 there is no UUID type at all. Answering "yes" would be a
        lie, and quietly emitting ``BINARY(16)`` would be a worse one."""
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )

        old = MariaDBDialect(version=(10, 6, 0))
        assert old.supports_data_type_mariadb_uuid() is False
        assert "mariadb_uuid" not in old.supports_data_types()
        with pytest.raises(UnsupportedFeatureError, match="UUID data type"):
            old.format_data_type(MariaDBUUIDType(old))

    def test_binary_16_is_not_a_uuid(self, dialect):
        """The pre-10.7 idiom is a 16-byte binary column, and it is a different
        column: no equivalence between the two is claimed anywhere."""
        assert dialect.format_data_type(MariaDBBinaryType(dialect, length=16)) == (
            "BINARY(16)", (),
        )
        assert MariaDBBinaryType(dialect, length=16) != MariaDBUUIDType(dialect)
    def test_enum_is_rendered_not_suggested(self, dialect):
        """MariaDB has a native ENUM, so the generic type is renderable here.

        It used to be suggested as MariaDBEnumType, which is a mapping meaning
        "I cannot render this, use that instead" — said by a dialect that can.
        A name in both sets is one of the two being a lie, so the generic type
        is rendered and the suggestion went.
        """
        suggestions = dialect.suggested_data_types()
        assert "enum" not in suggestions
        assert dialect.supports_data_types()["enum"] is EnumType

    def test_real_is_suggested_as_double_and_the_error_says_why(self, dialect):
        """``REAL`` cannot round-trip: MariaDB resolves it to ``DOUBLE``.

        The DOUBLE page groups ``DOUBLE``, ``DOUBLE PRECISION`` and ``REAL`` as
        one 8-byte type and says "``REAL`` and ``DOUBLE PRECISION`` are
        synonyms, unless the ``REAL_AS_FLOAT`` SQL mode is enabled, in which
        case ``REAL`` is a synonym for FLOAT rather than DOUBLE". Measured on
        all fifteen wired servers, 10.2.44 through 13.1.1: a ``REAL`` column
        reports ``double`` in ``information_schema`` and never ``real``. The
        class is therefore *substituted* rather than rendered, and the advice
        text carries the vendor fact so the caller can pick the right class.
        """
        suggestions = dialect.suggested_data_types()
        assert suggestions["real"] is DoubleType
        assert "real" not in dialect.supports_data_types()
        with pytest.raises(TypeError) as excinfo:
            dialect.format_data_type(RealType(dialect))
        message = str(excinfo.value)
        assert "DoubleType" in message
        assert "FloatType" in message
        assert "REAL_AS_FLOAT" in message
        assert "synonym" in message
        assert "cannot round-trip" in message


# ---------------------------------------------------------------------------
# Integer attributes: UNSIGNED and ZEROFILL are independent
#
# `unsigned` is in the type's PARAMETERS, so it is part of the type's identity
# and the differ reads it with `!=`. MariaDB infers UNSIGNED from a bare
# ZEROFILL, so a formatter that wrote ZEROFILL alone for an unsigned
# declaration would create a column whose stored range contradicts the emitted
# text -- and `parse_type` derives `unsigned` from the literal presence of the
# word "UNSIGNED", so the round-trip would hand back a different value object
# than the caller declared.
# ---------------------------------------------------------------------------

#: (type class, bare SQL word) for every width this dialect names. MEDIUMINT is
#: the 3-byte one; including it here is the point of defect 2's fix.
INTEGER_WIDTHS = (
    (MariaDBTinyIntType, "TINYINT"),
    (MariaDBSmallIntType, "SMALLINT"),
    (MariaDBMediumIntType, "MEDIUMINT"),
    (MariaDBIntType, "INT"),
    (MariaDBBigIntType, "BIGINT"),
)


class TestIntegerAttributeRoundTrip:
    """Every width x signedness x zerofill cell renders and parses back equal."""

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    @pytest.mark.parametrize("unsigned", [False, True])
    @pytest.mark.parametrize("zerofill", [False, True])
    def test_round_trips_to_the_same_value_object(
        self, dialect, cls, word, unsigned, zerofill,
    ):
        declared = cls(dialect, unsigned=unsigned, zerofill=zerofill)
        rendered, params = dialect.format_data_type(declared)
        assert params == ()
        back = dialect.parse_type(rendered)
        assert back == declared, (
            f"{declared!r} rendered as {rendered!r} but parsed back as {back!r}"
        )
        assert type(back) is cls

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_zerofill_never_displaces_unsigned(self, dialect, cls, word):
        """The regression itself: the word UNSIGNED must survive ZEROFILL.

        Before the fix ``format_data_type_*`` was an either/or -- ZEROFILL won
        and UNSIGNED was dropped -- so an unsigned+zerofill column rendered as
        ``INT ZEROFILL``.
        """
        both = dialect.format_data_type(
            cls(dialect, unsigned=True, zerofill=True)
        )[0]
        assert both == f"{word} UNSIGNED ZEROFILL"

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_the_signed_cells_have_not_moved(self, dialect, cls, word):
        """``X`` and ``X UNSIGNED`` are byte-identical to what was written before.

        Rendered SQL is not to change except where a plan item says a spelling is
        now honoured, and the only rendering this backend moved is the zero-padded
        one -- see :class:`TestZerofillImpliesUnsigned` for that cell and why.
        The signed and unsigned-but-unpadded columns are the two MariaDB integer
        columns that were always right, and neither has moved.
        """
        assert dialect.format_data_type(cls(dialect))[0] == word
        assert dialect.format_data_type(
            cls(dialect, unsigned=True)
        )[0] == f"{word} UNSIGNED"

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_attributes_are_independent(self, dialect, cls, word):
        """``UNSIGNED`` is a field, so flipping it must change the type."""
        signed = cls(dialect, unsigned=False)
        unsigned = cls(dialect, unsigned=True)
        assert signed != unsigned
        assert hash(signed) != hash(unsigned)

    def test_catalog_word_order_matches_the_rendered_order(self, dialect):
        """MariaDB writes ``<type>(<m>) unsigned zerofill`` into COLUMN_TYPE.

        Verified live against 11.8.9, 12.2.2, 12.3.3, 13.0.2 and 13.1.1: every
        one reports ``mediumint(8) unsigned zerofill`` for a zero-padded
        MEDIUMINT, i.e. UNSIGNED first -- the order this dialect now emits, which
        is what makes the round-trip above hold for a column that really exists.
        """
        parsed = dialect.parse_type("mediumint(8) unsigned zerofill")
        assert (parsed.unsigned, parsed.zerofill) == (True, True)
        assert dialect.format_data_type(parsed)[0] == "MEDIUMINT UNSIGNED ZEROFILL"


class TestExactAndApproximateNumericsHonourUnsigned:
    """MariaDB writes ``UNSIGNED`` after the ``(M[,D])`` group for all four
    exact/approximate numerics, so it is **honoured** here rather than refused.

    This is the other of the two answers the paradigm rule allows, and it is the
    one MariaDB's own grammar licenses — the "Numeric Data Type Overview" gives the
    attribute one place for the whole family, "Most numeric types can be defined as
    ``SIGNED``, ``UNSIGNED`` or ``ZEROFILL``", and adds "Floating point and
    fixed-point types also can be ``UNSIGNED``, but this only prevents negative
    values from being stored and doesn't alter the range"; the per-type pages fill
    in the argument list, ``DECIMAL[(M[,D])] [SIGNED | UNSIGNED | ZEROFILL]``,
    ``FLOAT[(M,D)] …``, ``DOUBLE[(M,D)] …`` and ``REAL[(M,D)] …``.
    https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
    https://mariadb.com/docs/server/reference/data-types/numeric-data-types/double

    **Measured on all fifteen wired servers** (10.2.44, 10.3.39, 10.4.34, 10.5.29,
    10.6.28, 10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2, 12.2.2, 12.3.3,
    13.0.2, 13.1.1), which agree byte for byte::

        DECIMAL(10,2) UNSIGNED  -> COLUMN_TYPE 'decimal(10,2) unsigned'   -1 rejected
        FLOAT(10,2) UNSIGNED    -> COLUMN_TYPE 'float(10,2) unsigned'     -1 rejected
        DOUBLE(10,2) UNSIGNED   -> COLUMN_TYPE 'double(10,2) unsigned'    -1 rejected
        DOUBLE UNSIGNED         -> COLUMN_TYPE 'double unsigned'          -1 rejected
        REAL UNSIGNED           -> COLUMN_TYPE 'double unsigned'          -1 rejected
        DECIMAL(10,2)           -> COLUMN_TYPE 'decimal(10,2)'            -1 stored
        FLOAT(10,2)             -> COLUMN_TYPE 'float(10,2)'              -1 stored
        DOUBLE(10,2)            -> COLUMN_TYPE 'double(10,2)'             -1 stored

    ("rejected" is 1264 *Out of range value for column 'c'* on inserting -1.) The
    range does not move — that is what the manual says too — but the stored column
    is a different column, and ``unsigned`` is in ``PARAMETERS``, so the differ has
    to see it.

    ``REAL`` is worth its own note, and it is why the table has one row more
    than the ``_NUMERICS`` list below. A bare ``REAL`` column reports
    ``COLUMN_TYPE = 'double'`` and ``REAL UNSIGNED`` reports
    ``'double unsigned'``, i.e. MariaDB's ``REAL`` **is** ``DOUBLE`` under the
    default SQL mode (and ``FLOAT`` under ``REAL_AS_FLOAT``). The word ``real``
    is therefore never what the catalog writes back, so ``RealType`` cannot
    round-trip and this dialect *substitutes* it — see
    ``TestSuggestedDataTypes.test_real_is_suggested_as_double_and_the_error_says_why``.
    The three concepts below are the ones the dialect renders.
    """

    #: ``(dispatch name, class, builder, signed SQL, unsigned SQL)``. The builders
    #: are callables so the ``(p, s)`` arguments stay inside the test body rather
    #: than being bound at class-definition time, where no dialect exists yet.
    _NUMERICS = [
        ("decimal", DecimalType,
         lambda d, u: DecimalType(d, 10, 2, unsigned=u),
         "DECIMAL(10, 2)", "DECIMAL(10, 2) UNSIGNED"),
        ("float", FloatType,
         lambda d, u: FloatType(d, unsigned=u),
         "FLOAT", "FLOAT UNSIGNED"),
        ("double", DoubleType,
         lambda d, u: DoubleType(d, unsigned=u),
         "DOUBLE", "DOUBLE UNSIGNED"),
    ]
    _IDS = [row[0] for row in _NUMERICS]

    @pytest.mark.parametrize("name,cls,build,signed_sql,unsigned_sql", _NUMERICS,
                             ids=_IDS)
    def test_flipping_unsigned_changes_the_rendered_sql(self, dialect, name, cls,
                                                       build, signed_sql,
                                                       unsigned_sql):
        """The rule itself: the field is in ``PARAMETERS``, so it must reach the
        SQL. Byte-identical SQL for both signs is the violation — and it is
        exactly what all of these formatters used to produce."""
        signed = dialect.format_data_type(build(dialect, False))[0]
        unsigned = dialect.format_data_type(build(dialect, True))[0]
        assert signed == signed_sql
        assert unsigned == unsigned_sql
        assert unsigned != signed

    @pytest.mark.parametrize("name,cls,build,signed_sql,unsigned_sql", _NUMERICS,
                             ids=_IDS)
    def test_round_trips_to_the_same_value_object(self, dialect, name, cls,
                                                 build, signed_sql,
                                                 unsigned_sql):
        """``parse_type`` is the half that restores the differ's sight.

        Without reading ``UNSIGNED`` out of the catalog string, an introspected
        unsigned column came back as the *signed* value object, ``==`` called the
        two equal, and the differ reported no change for the change MariaDB
        happily makes. Both directions are pinned, for both signs.
        """
        for unsigned in (False, True):
            declared = build(dialect, unsigned)
            rendered, params = dialect.format_data_type(declared)
            assert params == ()
            back = dialect.parse_type(rendered)
            assert back == declared, (
                f"{declared!r} rendered as {rendered!r} but parsed back as {back!r}"
            )
            assert type(back) is cls
            assert back.unsigned is unsigned

    @pytest.mark.parametrize("name,cls,build,signed_sql,unsigned_sql", _NUMERICS,
                             ids=_IDS)
    def test_parse_type_reads_the_catalog_word(self, dialect, name, cls, build,
                                              signed_sql, unsigned_sql):
        """The catalog strings themselves, byte for byte as measured above.

        Fed to ``parse_type`` directly rather than only through the formatter, so a
        change to either half alone fails here.
        """
        unsigned_back = dialect.parse_type(unsigned_sql)
        assert unsigned_back.unsigned is True
        assert dialect.format_data_type(unsigned_back)[0] == unsigned_sql
        signed_back = dialect.parse_type(signed_sql)
        assert signed_back.unsigned is False
        assert dialect.format_data_type(signed_back)[0] == signed_sql

    def test_parse_type_does_not_mistake_the_precision_for_a_sign(self, dialect):
        """``re.findall(r"\\d+", ...)`` reads the argument, not the attribute.

        The obvious way to break this is to look for a digit where the sign is, so
        the shape that catches it is a *sized, signed* declaration whose only
        digits are its own.

        ``float(10,2)`` is the deprecated two-argument form and is stored as
        4-byte single precision, so it parses as the precision-free
        ``FloatType``; ``real`` is a documented synonym of ``DOUBLE`` and
        canonicalises to ``DoubleType``.
        """
        assert dialect.parse_type("decimal(10,2) unsigned") == DecimalType(
            None, 10, 2, unsigned=True)
        assert dialect.parse_type("float(10,2) unsigned") == FloatType(
            None, unsigned=True)
        assert dialect.parse_type("double(10,2) unsigned") == DoubleType(
            unsigned=True)
        assert dialect.parse_type("real unsigned") == DoubleType(unsigned=True)

    def test_the_attribute_is_written_after_the_argument_group(self, dialect):
        """The slot the grammar gives it, which is also the slot the catalog reports
        it in — ``DECIMAL(10, 2) UNSIGNED``, never ``DECIMAL UNSIGNED (10, 2)``.

        Only the concepts that *have* an argument group to be after; ``DOUBLE``
        is declared bare by this dialect, so for it the whole assertion is that
        ``UNSIGNED`` follows the type word.
        """
        for _, _, build, _, unsigned_sql in self._NUMERICS:
            rendered = dialect.format_data_type(build(dialect, True))[0]
            assert rendered.endswith(" UNSIGNED")
            if "(" in rendered:
                assert rendered.index(")") < rendered.index(" UNSIGNED"), rendered

    def test_zerofill_is_not_reachable_from_these_concepts(self, dialect):
        """``ZEROFILL`` has no field on any of them, and must not grow one.

        It is a MariaDB display attribute: MariaDB *implies* ``UNSIGNED`` from it
        (``decimal(10,2) zerofill`` reports ``decimal(10,2) unsigned zerofill`` on
        every wired server), so honouring it would mean writing an attribute the
        declaration never asked for. MariaDB's own integer classes exist precisely
        to carry it, and those go through the same
        :meth:`~...types.MariaDBTypeSupportMixin._format_mariadb_integer`.
        """
        for cls in (DecimalType, FloatType, DoubleType):
            assert not hasattr(cls(dialect), "zerofill"), cls.__name__

    def test_unsigned_is_appended_so_hashes_are_stable(self, dialect):
        """Appended, never inserted: the order of ``PARAMETERS`` is what
        ``identity()`` reads, so it is what ``__eq__`` and ``__hash__`` read."""
        assert DecimalType.PARAMETERS == ("precision", "scale", "unsigned")
        assert FloatType.PARAMETERS == ("precision", "unsigned")
        assert DoubleType.PARAMETERS == ("unsigned",)
        for _, _, build, _, _ in self._NUMERICS:
            signed, unsigned = build(dialect, False), build(dialect, True)
            assert signed != unsigned
            assert hash(signed) != hash(unsigned)

    @pytest.mark.parametrize("case,expected", [
        # every pre-existing ValueError, still firing for a *signed* declaration
        ("decimal_precision", ValueError),
        ("decimal_scale", ValueError),
        ("decimal_scale_over_precision", ValueError),
        ("float_precision", ValueError),
        # ... and the spelling gate, which is a TypeError
        ("decimal_bad_spelling", TypeError),
    ])
    def test_every_pre_existing_check_still_fires_for_a_signed_declaration(
            self, dialect, case, expected):
        """Nothing besides the float/real contract moved.

        Pinned by *type*, because the point is that each of these still raises
        what it always raised — including the ``FLOAT(p)`` refusal, which was a
        ``ValueError`` before the precision became unrepresentable and is still
        one now.
        """
        built = {
            "decimal_precision": DecimalType(dialect, precision=99),
            "decimal_scale": DecimalType(dialect, scale=99),
            "decimal_scale_over_precision": DecimalType(dialect, 2, 5),
            "float_precision": FloatType(dialect, precision=999),
            "decimal_bad_spelling": DecimalType(dialect, precision=10,
                                                spelling="fixed"),
        }[case]
        with pytest.raises(expected):
            built.to_sql()


class TestFloatPrecisionAndSynonymsAreCanonicalised:
    """``FLOAT(p)`` selects a class; ``DOUBLE PRECISION``/``REAL`` are synonyms.

    Measured on all fifteen wired servers (10.2.44 through 13.1.1, which agree
    byte for byte): ``FLOAT(24)`` reports ``COLUMN_TYPE = 'float'`` while
    ``FLOAT(25)`` and ``FLOAT(53)`` report ``'double'``, and a ``DOUBLE
    PRECISION`` or ``REAL`` column reports ``'double'``. The parser follows the
    storage the catalog shows, not the word that was written.
    """

    def test_double_precision_is_a_spelling_of_double(self, dialect):
        """The DOUBLE page accepts ``DOUBLE PRECISION``; the catalog says double."""
        for raw in ("DOUBLE PRECISION", "double precision"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, DoubleType), raw
            assert not isinstance(parsed, CustomType), raw
        assert dialect.format_data_type(
            DoubleType(dialect, spelling="double precision")
        ) == ("DOUBLE", ())
        assert dialect.format_data_type(
            DoubleType(dialect, spelling="double", unsigned=True)
        ) == ("DOUBLE UNSIGNED", ())

    def test_real_canonicalises_to_double(self, dialect):
        """The documented default synonym is DOUBLE; the word never comes back.

        "``REAL`` and ``DOUBLE PRECISION`` are synonyms, unless the
        ``REAL_AS_FLOAT`` SQL mode is enabled, in which case ``REAL`` is a
        synonym for FLOAT rather than DOUBLE." A live column made under the
        mode reports ``float`` (which parses as ``FloatType``), so ``RealType``
        itself is substituted rather than parsed into.
        """
        for raw in ("REAL", "real"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, DoubleType), raw
            assert not isinstance(parsed, CustomType), raw
        assert dialect.parse_type("REAL UNSIGNED") == DoubleType(
            dialect, unsigned=True
        )

    @pytest.mark.parametrize("raw,expected", [
        ("FLOAT(24)", FloatType),
        ("FLOAT(25)", DoubleType),
        ("FLOAT(53)", DoubleType),
    ])
    def test_float_p_canonicalises_to_the_class_it_selects(self, dialect, raw,
                                                          expected):
        """p 0..24 is FLOAT storage and p 25..53 is DOUBLE storage.

        p itself is dropped because the catalog does not record it; the
        formatter refuses a precision-bearing ``FloatType`` for that reason and
        the caller is told which class to declare for each range.
        """
        parsed = dialect.parse_type(raw)
        assert type(parsed) is expected, raw
        assert dialect.format_data_type(parsed) == (expected.name.upper(), ())

    def test_float_md_is_single_precision_regardless_of_the_first_number(
            self, dialect):
        """The deprecated two-argument ``FLOAT(M,D)`` is *not* ``FLOAT(p)``.

        Measured on the wired servers: ``FLOAT(25,17)`` and ``FLOAT(53,17)``
        both store single-precision values (1.2345678806304932, against
        ``DOUBLE``'s 1.2345678901234567) and both report
        ``NUMERIC_PRECISION = M``, while one-argument ``FLOAT(25)`` resolves to
        ``double``. The first number is M (total decimal digits), not p (bits),
        so the declaration is the 4-byte concept.
        """
        for raw in ("FLOAT(10,2)", "FLOAT(24,2)", "FLOAT(25,2)", "FLOAT(53,2)"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, FloatType), raw
            assert parsed.precision is None, raw
        assert dialect.parse_type("FLOAT(53,2) UNSIGNED") == FloatType(
            dialect, unsigned=True
        )

    @pytest.mark.parametrize("precision", [0, 24, 25, 53])
    def test_float_precision_is_refused_and_names_single_and_double(
            self, dialect, precision):
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(FloatType(dialect, precision))
        message = str(excinfo.value)
        assert "FloatType(dialect)" in message, message
        assert "DoubleType(dialect)" in message, message

    @pytest.mark.parametrize("precision", [0, 24, 25, 53])
    def test_float_precision_refusal_is_a_value_error_not_a_feature_error(
            self, dialect, precision):
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(FloatType(dialect, precision))
        assert not isinstance(excinfo.value, UnsupportedFeatureError)


class TestMediumIntIsItsOwnWidth:
    """MEDIUMINT is 3 bytes. Reading it as the 4-byte INT was a false claim."""

    def test_own_dispatch_key_and_class(self, dialect):
        supported = dialect.supports_data_types()
        assert supported["mariadb_mediumint"] is MariaDBMediumIntType
        assert dialect.supports_data_type_mariadb_mediumint() is True
        assert MariaDBMediumIntType.name == "mariadb_mediumint"

    @pytest.mark.parametrize("raw", [
        "mediumint(9)",                # what the catalog actually reports
        "mediumint(8) unsigned",
        "mediumint(8) unsigned zerofill",
        "MEDIUMINT",
        "int3",                        # MariaDB's documented synonym
        "INT3 UNSIGNED",
    ])
    def test_parses_to_the_three_byte_class(self, dialect, raw):
        parsed = dialect.parse_type(raw)
        assert isinstance(parsed, MariaDBMediumIntType)
        assert parsed.name == "mariadb_mediumint"

    def test_mediumint_is_not_an_int(self, dialect):
        """The defect: 3 bytes was being read as 4 bytes, so the differ saw a
        MEDIUMINT column and an INT column as the same type."""
        medium = dialect.parse_type("mediumint(9)")
        assert medium != MariaDBIntType(dialect)
        assert type(medium) is not type(MariaDBIntType(dialect))
        assert MariaDBMediumIntType(dialect) != MariaDBIntType(dialect)

    def test_deriving_from_the_4_byte_concept_is_not_a_width_claim(self, dialect):
        """The inheritance buys the shared `unsigned` field, nothing else.

        DataType.__eq__ is class-exact, so the base class never makes a
        MEDIUMINT column equal to an INT one -- but the docstring has to say so
        explicitly, because the inheritance line is where a reader would
        otherwise take the width claim from.
        """
        assert issubclass(MariaDBMediumIntType, IntegerType)
        doc = MariaDBMediumIntType.__doc__
        assert "3 bytes" in doc and "not 4" in doc

    def test_spellings_are_narrowed_to_this_width(self, dialect):
        """MariaDB's words for 3 bytes are MEDIUMINT and INT3.

        The 4-byte concept's ``integer`` / ``int`` are not words for this width
        and must be refused rather than silently rewritten.
        """
        assert MariaDBMediumIntType.SPELLINGS == ("mediumint", "int3")
        assert "integer" not in MariaDBMediumIntType.SPELLINGS
        for spelling in MariaDBMediumIntType.SPELLINGS:
            assert dialect.format_data_type(
                MariaDBMediumIntType(dialect, spelling=spelling)
            )[0] == "MEDIUMINT"
        with pytest.raises(TypeError, match="integer"):
            dialect.format_data_type(
                MariaDBMediumIntType(dialect, spelling="integer")
            )

    def test_each_width_parses_to_its_own_class(self, dialect):
        """One concept in, one class out, for all five widths."""
        for cls, word in INTEGER_WIDTHS:
            parsed = dialect.parse_type(word)
            assert type(parsed) is cls, word
            assert parsed.unsigned is False
            assert dialect.format_data_type(cls(dialect)) == (word, ())
        assert dialect.format_data_type(MariaDBMediumIntType(dialect)) == (
            "MEDIUMINT", (),
        )


class TestXmlTypeSubstituteFollowsTheServer:
    """MariaDB 12.3 added a native XMLTYPE; before it there was no XML type."""

    @pytest.mark.parametrize("version,expected", [
        ((10, 6, 0), False),
        ((11, 8, 9), False),
        ((12, 2, 2), False),
        ((12, 3, 0), True),
        ((12, 3, 3), True),
        ((13, 0, 2), True),
        ((13, 1, 1), True),
    ])
    def test_gate_is_at_12_3(self, version, expected):
        target = MariaDBDialect(version=version)
        assert target.supports_data_type_mariadb_xml() is expected

    def test_below_12_3_the_substitute_is_text(self):
        """Unchanged behaviour on an older server: XML is text."""
        old = MariaDBDialect(version=(12, 2, 2))
        assert old.suggested_data_types()["xml"] is TextType
        assert old.format_data_type(TextType(old)) == ("TEXT", ())
        assert "mariadb_xml" not in old.supports_data_types()

    def test_from_12_3_the_substitute_is_the_native_type(self):
        """On 12.3+ the backend can store a real XML column, so TEXT is wrong."""
        new = MariaDBDialect(version=(12, 3, 0))
        assert new.suggested_data_types()["xml"] is MariaDBXmlType
        assert new.supports_data_types()["mariadb_xml"] is MariaDBXmlType
        assert new.format_data_type(MariaDBXmlType(new)) == ("XMLTYPE", ())

    def test_xml_is_substituted_not_rendered_under_the_core_name(self):
        """``xml`` stays a substitute on every server; ``mariadb_xml`` is the
        rendered key. The two sets stay disjoint on both sides of the gate."""
        for version in [(12, 2, 2), (13, 1, 1)]:
            target = MariaDBDialect(version=version)
            assert "xml" in target.suggested_data_types()
            assert "xml" not in target.supports_data_types()
            assert not (set(target.suggested_data_types())
                        & set(target.supports_data_types()))

    def test_xmltype_refuses_to_render_below_12_3(self):
        """Answering with TEXT would hand back a different column silently."""
        old = MariaDBDialect(version=(12, 2, 2))
        with pytest.raises(UnsupportedFeatureError, match="XMLTYPE"):
            old.format_data_type(MariaDBXmlType(old))

    def test_xmltype_renders_in_a_column_definition(self):
        new = MariaDBDialect(version=(13, 1, 1))
        column = ColumnDefinition(new, "doc", MariaDBXmlType(new))
        assert column.to_sql() == ("`doc` XMLTYPE", ())

    @pytest.mark.parametrize("version", [(12, 2, 2), (13, 1, 1)])
    def test_xmltype_round_trips_only_where_it_exists(self, version):
        target = MariaDBDialect(version=version)
        declared = MariaDBXmlType(target)
        if not target.supports_data_type_mariadb_xml():
            with pytest.raises(UnsupportedFeatureError, match="XMLTYPE"):
                target.format_data_type(declared)
            # Below the gate the word cannot come from the catalog, and handing
            # back a type this dialect refuses to render would be worse than
            # admitting ignorance.
            assert isinstance(target.parse_type("xmltype"), CustomType)
            return
        rendered, _ = target.format_data_type(declared)
        assert rendered == "XMLTYPE"
        assert target.parse_type(rendered) == declared

    def test_derives_from_the_core_xml_concept(self):
        """``isinstance(col.data_type, XmlType)`` must answer across backends.

        Deliberately not a ``TextType``: XMLTYPE takes no length and is capped at
        4 GB, so "it is text" is exactly the claim core's XmlType says is false.
        """
        assert issubclass(MariaDBXmlType, XmlType)
        assert not issubclass(MariaDBXmlType, TextType)
        assert MariaDBXmlType.name == "mariadb_xml"
        assert MariaDBXmlType.PARAMETERS == ()

    def test_length_is_refused_by_the_server_and_so_not_a_parameter(self):
        # "Data type 'XMLTYPE' doesn't support LENGTH attribute." -- so there is
        # nothing for a length field to hold, in either direction.
        assert MariaDBXmlType.__init__.__doc__ is None
        assert "LENGTH attribute" in MariaDBXmlType.__doc__


class TestTypeProtocolSetDeclaresTheNewFamilies:
    """The MariaDB type protocol states the attribute questions.

    The naming convention already declares ``format_data_type_<name>`` /
    ``supports_data_type_<name>`` for every ``mariadb_*`` key, so this protocol
    exists for the parts a name cannot express -- here the two-attribute integer
    rule, the 3-byte width, and the 12.3 XML gate.
    """

    @pytest.mark.parametrize("capability", [
        "supports_mariadb_integer_attributes",
        "supports_mariadb_mediumint_width",
        "supports_mariadb_xml_type",
    ])
    def test_capability_is_declared_with_a_docstring(self, capability):
        assert capability in vars(MariaDBTypeSupport)
        assert getattr(MariaDBTypeSupport, capability).__doc__

    def test_integer_attribute_rule_states_both_attributes(self):
        """Both words, and the *relation* between them, which is the load-bearing part.

        The relation flipped with the ``ZEROFILL`` normalisation: they used to be
        described as independent, and they are not -- MariaDB resolves a bare
        ``ZEROFILL`` into ``UNSIGNED``. Asserting only that the word "independ"
        appears would now pass on a docstring that says the opposite of what it
        used to say, so the assertion states which way it goes.
        """
        doc = vars(MariaDBTypeSupport)[
            "supports_mariadb_integer_attributes"
        ].__doc__
        flat = " ".join(doc.split())
        assert "UNSIGNED" in doc and "ZEROFILL" in doc
        assert "not independent" in flat.lower()
        assert "will be set to ``UNSIGNED``" in flat
        assert "special type of ``INT UNSIGNED`` is ``INT ZEROFILL``" in flat
        assert "fifteen wired servers" in flat


# ---------------------------------------------------------------------------
# Integer spellings: D8 -- parse_type covers every SPELLINGS entry
#
# The defect: ``format_data_type_tinyint`` / ``_smallint`` / ``_bigint`` all
# accept a second spelling (``int1`` / ``int2`` / ``int8``, which are members of
# the core classes' ``SPELLINGS``) and render the canonical word, but
# ``_MARIA_INTEGER_TYPES`` did not match those words -- so ``parse_type("int8")``
# returned ``CustomType``. A dialect that will write a column whose declared
# spelling it cannot name back is the asymmetry D8 forbids. Only ``INT3`` was
# covered, because that is the one the previous round introduced.
#
# Which synonym belongs to which width is taken from MariaDB's own
# "Numeric Data Type Overview", which lists all six in one table, corroborated by
# each width's page and by a page per synonym:
#   https://mariadb.com/docs/server/reference/data-types/numeric-data-types/numeric-data-type-overview
#   .../tinyint  .../smallint  .../mediumint  .../int  .../bigint
#   .../int1  .../int2  .../int3  .../int4  .../int8
# ---------------------------------------------------------------------------

#: ``(core concept, every spelling its formatter accepts, documented synonym,
#: the class parse_type must return for each of them)``. The class is the
#: ``mariadb_*`` one because ``zerofill`` has nowhere to live on the core class,
#: so it is the only lossless answer and the one this dialect already returns for
#: the canonical word.
#:
#: All four documented ``INTn`` synonyms are listed, and all four are members of
#: their concept's ``SPELLINGS``: core's closed lists are the **union** across
#: dialects, so ``IntegerType.SPELLINGS`` is ``("integer", "int", "int4")`` --
#: MySQL and MariaDB each give ``INT4`` a page of its own. This dialect accepts
#: and normalises all of them to the canonical word, which means ``INT4`` is a
#: fourth D8 case and not a special one.
INTEGER_SPELLING_WIDTHS = (
    (TinyIntType, "TINYINT", "int1", MariaDBTinyIntType),
    (SmallIntType, "SMALLINT", "int2", MariaDBSmallIntType),
    (IntegerType, "INT", "int4", MariaDBIntType),
    (BigIntType, "BIGINT", "int8", MariaDBBigIntType),
)

#: The ones that were genuine D8 violations: the spelling is in the concept's own
#: ``SPELLINGS``, the formatter accepts it, and ``parse_type`` could not read it.
INTEGER_SPELLINGS_D8_VIOLATIONS = tuple(
    row for row in INTEGER_SPELLING_WIDTHS if row[2] in row[0].SPELLINGS
)

#: Every attribute combination a caller may write on an integer column.
INTEGER_ATTRS = ("", " UNSIGNED", " ZEROFILL", " UNSIGNED ZEROFILL")


class TestIntegerSpellingsParseBackToTheSameClass:
    """Every accepted spelling of an integer width is parseable, and canonical.

    Two directions, because D8 is a round trip and either half can break:

    * **read** -- ``parse_type(spelling)`` must give the same class, the same
      ``spelling`` and the same ``unsigned`` / ``zerofill`` as
      ``parse_type(canonical_word)``. That is "one concept in, one class out".
    * **write then read** -- ``parse_type(format_data_type(declared))`` must give
      the declared value object back for every accepted spelling. This is the
      half a pure-string test cannot see, because the formatter normalises
      ``INT8`` to ``BIGINT`` before the string exists.
    """

    def test_four_spellings_were_the_violation(self):
        """Pin the size of the defect, so a regression is visible.

        Every documented ``INTn`` synonym that a core concept claims in its
        closed ``SPELLINGS`` list was unreadable by ``parse_type``:
        ``int1``, ``int2``, ``int4`` and ``int8``. ``int3`` was already covered
        by the previous round because ``MariaDBMediumIntType`` declares it, and
        it is not listed here because ``MariaDBMediumIntType`` is not one of the
        four core concepts -- ``IntegerType`` does not claim ``int3``, which is
        correct: ``INT3`` is a 3-byte width and ``IntegerType`` is the 4-byte
        one.
        """
        assert {row[2] for row in INTEGER_SPELLINGS_D8_VIOLATIONS} == {
            "int1", "int2", "int4", "int8",
        }

    @pytest.mark.parametrize("concept,word,synonym,cls",
                             INTEGER_SPELLINGS_D8_VIOLATIONS)
    def test_formatter_accepts_and_parse_type_reads_the_spelling(
        self, dialect, concept, word, synonym, cls,
    ):
        """The defect: the word the formatter accepts, read back as its width.

        Before the fix every ``synonym`` case here returned ``CustomType`` -- and
        with any attribute appended it *raised* instead, because ``CustomType``
        validates ``raw`` as an identifier and ``"INT1 UNSIGNED"`` is not one. So
        the asymmetry was not even a wrong answer: it was an exception on a
        string this dialect's own formatter produces.
        """
        # write: the formatter accepts the spelling and emits the canonical word
        rendered, params = dialect.format_data_type(
            concept(dialect, spelling=synonym)
        )
        assert rendered == word
        assert params == ()

        # read: and the word it wrote comes back as the width's own class
        assert type(dialect.parse_type(rendered)) is cls

    @pytest.mark.parametrize("concept,word,synonym,cls",
                             INTEGER_SPELLINGS_D8_VIOLATIONS)
    @pytest.mark.parametrize("attr", INTEGER_ATTRS)
    def test_synonym_is_read_identically_to_the_canonical_word(
        self, dialect, concept, word, synonym, cls, attr,
    ):
        """The read direction, from the synonym itself.

        The two flags are read off what the word *means as a column*, not off
        which literal words happen to be in the string. ``zerofill`` obviously
        needs its own word; ``unsigned`` needs the ``UNSIGNED`` word **or** a
        ``ZEROFILL``, because MariaDB resolves one into the other -- "If
        ``ZEROFILL`` is specified, the column will be set to ``UNSIGNED``". A
        bare ``ZEROFILL`` therefore reads back as *unsigned + zerofill*, which is
        exactly the column the server builds from it (asserted on a live server
        in :class:`TestIntegerSpellingRoundTripOnALiveServer` and in
        :class:`TestZerofillImpliesUnsigned`).

        This assertion used to read ``unsigned is ("UNSIGNED" in attr)``, which
        asserted the defect: it made ``parse_type("INT1 ZEROFILL")`` a *signed*
        type for a column that cannot hold ``-1``.
        """
        canonical = dialect.parse_type(word + attr)
        from_synonym = dialect.parse_type(synonym + attr)

        assert type(from_synonym) is type(canonical) is cls
        assert from_synonym == canonical
        assert from_synonym.unsigned is canonical.unsigned
        assert from_synonym.zerofill is canonical.zerofill
        assert from_synonym.unsigned is (
            "UNSIGNED" in attr or "ZEROFILL" in attr
        )
        assert from_synonym.zerofill is ("ZEROFILL" in attr)

    @pytest.mark.parametrize("concept,word,synonym,cls",
                             INTEGER_SPELLINGS_D8_VIOLATIONS)
    @pytest.mark.parametrize("attr", INTEGER_ATTRS)
    def test_synonym_and_canonical_carry_the_same_spelling(
        self, dialect, concept, word, synonym, cls, attr,
    ):
        """Why the canonical word is the honest target, not the synonym.

        MariaDB rewrites its own synonyms in the catalog -- ``INT1`` comes back as
        ``tinyint(4)``, ``INT8`` as ``bigint(20)`` (verified live on all fifteen
        wired servers), so a synonym can never be the spelling of an
        *introspected* column. Recording ``spelling="int8"`` on the way in would
        be wrong for a second reason: this dialect normalises every spelling it
        accepts to MariaDB's own word, so ``spelling`` never reaches the DDL and
        never comes back from it either. ``spelling`` is deliberately not in
        ``PARAMETERS``, which is what lets a ``NUMERIC(10,2)`` column and the
        identical ``DECIMAL(10,2)`` column compare equal.

        So the honest round-trip target per width is the **canonical word**, and
        this is the assertion that says so: one spelling for a width, whichever
        word arrived.
        """
        assert dialect.parse_type(synonym + attr).spelling == \
            dialect.parse_type(word + attr).spelling

    @pytest.mark.parametrize("concept,word,synonym,cls",
                             INTEGER_SPELLINGS_D8_VIOLATIONS)
    def test_every_accepted_spelling_round_trips_the_declared_value_object(
        self, dialect, concept, word, synonym, cls,
    ):
        """Write then read, for every spelling of the concept -- not just the one.

        ``TestIntegerAttributeRoundTrip`` above walks the width x signedness x
        zerofill grid for the ``mariadb_*`` classes. This walks the *spelling*
        axis for the core concepts, which is the axis the defect was on: each
        core concept is built with each of its own ``SPELLINGS`` and has to come
        back as the width's class.

        ``zerofill`` is not asserted here: it is MariaDB's own field and lives
        only on the ``mariadb_*`` classes, which
        :class:`TestIntegerAttributeRoundTrip` above already covers across the
        full width x signedness x zerofill grid.
        """
        for spelling in concept.SPELLINGS:
            for unsigned in (False, True):
                declared = concept(dialect, spelling=spelling, unsigned=unsigned)
                rendered, params = dialect.format_data_type(declared)
                assert params == ()
                expected = cls(dialect, unsigned=unsigned)
                assert dialect.parse_type(rendered) == expected, (
                    f"{concept.__name__}(spelling={spelling!r}, "
                    f"unsigned={unsigned}) rendered {rendered!r}"
                )

    @pytest.mark.parametrize("raw,expected_name", [
        # Every word MariaDB's overview lists, plus the per-synonym pages.
        ("TINYINT", "MariaDBTinyIntType"),
        ("INT1", "MariaDBTinyIntType"),
        ("SMALLINT", "MariaDBSmallIntType"),
        ("INT2", "MariaDBSmallIntType"),
        ("MEDIUMINT", "MariaDBMediumIntType"),
        ("INT3", "MariaDBMediumIntType"),
        ("INT", "MariaDBIntType"),
        ("INTEGER", "MariaDBIntType"),
        ("INT4", "MariaDBIntType"),
        ("BIGINT", "MariaDBBigIntType"),
        ("INT8", "MariaDBBigIntType"),
        # With a display width, which is what the catalog actually reports.
        ("tinyint(4)", "MariaDBTinyIntType"),
        ("smallint(6)", "MariaDBSmallIntType"),
        ("mediumint(9)", "MariaDBMediumIntType"),
        ("int(11)", "MariaDBIntType"),
        ("bigint(20)", "MariaDBBigIntType"),
        ("bigint(20) unsigned zerofill", "MariaDBBigIntType"),
        ("int3(9)", "MariaDBMediumIntType"),
        ("int8(20)", "MariaDBBigIntType"),
    ])
    def test_every_documented_integer_word_lands_on_its_width(
        self, dialect, raw, expected_name,
    ):
        assert type(dialect.parse_type(raw)).__name__ == expected_name, raw

    @pytest.mark.parametrize("raw", ["INT11", "INT1X", "INTERVAL", "INET6",
                                     "INVISIBLE"])
    def test_a_word_that_only_looks_like_one_is_not_claimed(self, dialect, raw):
        """``\\b`` is load-bearing.

        ``INT1`` is a prefix of ``INT11``, and without the trailing word boundary
        the regex would accept it as the 1-byte width -- reading an
        unrecognised word as a real column type. The honest answer for a word
        MariaDB does not document is :class:`CustomType`.
        """
        assert isinstance(dialect.parse_type(raw), CustomType), raw

    def test_bool_is_not_int1(self, dialect):
        """``BOOL``/``BOOLEAN`` are documented synonyms of ``TINYINT(1)``, which is
        a **different column** from ``INT1``.

        The manual is explicit -- the overview says "BOOLEAN - Synonym for
        TINYINT(1)", listing it apart from "INT1 - Synonym for TINYINT" -- and
        the server agrees: ``BOOL`` is stored as ``tinyint(1)`` and ``INT1`` as
        ``tinyint(4)`` (verified live on all fifteen wired servers). So
        ``parse_type("bool")`` is a ``BooleanType`` and ``parse_type("int1")`` is
        a small integer.
        """
        assert isinstance(dialect.parse_type("BOOL"), BooleanType)
        assert isinstance(dialect.parse_type("BOOLEAN"), BooleanType)
        assert isinstance(dialect.parse_type("TINYINT(1)"), BooleanType)
        for raw in ("INT1", "INT1(4)", "TINYINT", "TINYINT(4)"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, MariaDBTinyIntType), raw
            assert not isinstance(parsed, BooleanType), raw

    @pytest.mark.parametrize("attr", (" UNSIGNED", " ZEROFILL",
                                      " UNSIGNED ZEROFILL"))
    def test_int1_with_attributes_is_not_a_boolean(self, dialect, attr):
        """The digit in ``INT1`` must not be mistaken for a display width.

        The bare-word check must not be satisfied by a digit anywhere in the
        string, or every ``UNSIGNED`` / ``ZEROFILL`` synonym would silently
        become a boolean.
        """
        parsed = dialect.parse_type("INT1" + attr)
        assert isinstance(parsed, MariaDBTinyIntType), attr
        assert not isinstance(parsed, BooleanType), attr

    def test_int4_is_written_normalised_and_read_back(self, dialect):
        """``INT4`` is a member of ``IntegerType.SPELLINGS``, so it is written.

        Core's closed spelling lists are the **union** across dialects, not one
        dialect's vocabulary, and ``INT4`` is on MariaDB's own list twice over:
        the Numeric Data Type Overview tabulates "``INT4`` - Synonym for
        ``INT``" and there is a page of its own at
        .../numeric-data-types/int4. So this dialect accepts it, normalises it
        to MariaDB's own ``INT`` -- the word ``COLUMN_TYPE`` reports, and the one
        that makes the round trip through the catalog stable -- and
        ``parse_type`` reads it back to the same class with the same
        ``spelling``.

        It was previously the odd one out: ``int4`` was *not* in
        ``IntegerType.SPELLINGS``, so ``format_data_type_integer`` refused it
        with a ``TypeError`` naming the spelling while ``parse_type`` read it
        anyway. That is the asymmetry D8 forbids in the other direction -- the
        reader is widened without the writer -- and the reader-only half could
        not be justified once the writer caught up.
        """
        assert "int4" in IntegerType.SPELLINGS
        assert dialect.format_data_type(
            IntegerType(dialect, spelling="int4")
        )[0] == "INT"
        assert isinstance(dialect.parse_type("INT4"), MariaDBIntType)
        assert dialect.parse_type("INT4") == dialect.parse_type("INTEGER")

    @pytest.mark.parametrize("raw,expected", [
        ("int1", MariaDBTinyIntType),
        ("int2", MariaDBSmallIntType),
        ("int3", MariaDBMediumIntType),
        ("int4", MariaDBIntType),
        ("int8", MariaDBBigIntType),
    ])
    def test_each_synonym_has_its_own_branch(self, dialect, raw, expected):
        """Guard against the regex and the dispatch drifting apart.

        Every documented synonym must be a *branch* of the integer dispatch, not
        merely a word the leading regex happens to match: a synonym added to the
        regex without a branch would fall through to the 4-byte default and be
        read as the wrong width, which is the MEDIUMINT defect all over again.
        """
        assert type(dialect.parse_type(raw)) is expected, raw


class TestZerofillImpliesUnsigned:
    """``X ZEROFILL`` and ``X UNSIGNED ZEROFILL`` are one column on MariaDB.

    The defect: a declaration of ``(unsigned=False, zerofill=True)`` was rendered
    as ``INT ZEROFILL``, which the server stores as ``int(10) unsigned zerofill``.
    So the stored column was unsigned while the declaration said signed, and
    ``parse_type`` -- which reads ``unsigned`` off the literal presence of the
    word -- handed back a different value object than the caller declared. That
    is 150 of the 600 formatter -> catalog -> ``parse_type`` round trips across
    the 15-server matrix, and it is what ``_zerofill_signedness`` fixes.

    **The fix is normalisation at construction, not an exemption.** Nothing here
    is listed as an exception to a test: the two declarations now build the same
    value object, because they name the same column.
    """

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_bare_zerofill_is_normalised_to_unsigned(self, dialect, cls, word):
        assert cls(dialect, zerofill=True).unsigned is True
        assert cls(dialect, unsigned=False, zerofill=True).unsigned is True
        assert cls(dialect, unsigned=True, zerofill=True).unsigned is True

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_signedness_is_untouched_without_zerofill(self, dialect, cls, word):
        """The normalisation must not leak into the other two cells.

        ``X`` and ``X UNSIGNED`` are two genuinely different MariaDB columns --
        ``int(11)`` and ``int(10) unsigned`` -- and the first accepts ``-1`` while
        the second does not, so this backend honours the flag rather than
        refusing it.
        """
        assert cls(dialect).unsigned is False
        assert cls(dialect, unsigned=False).unsigned is False
        assert cls(dialect, unsigned=True).unsigned is True
        assert cls(dialect) != cls(dialect, unsigned=True)

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_the_two_declarations_are_one_value_object(self, dialect, cls, word):
        """The consequence the differ reads: one column, one type.

        If these two were ``!=`` the schema differ would report a change to
        ``unsigned`` that this backend cannot make, because MariaDB will not
        store the column the signed declaration asks for.
        """
        signed_zerofill = cls(dialect, unsigned=False, zerofill=True)
        unsigned_zerofill = cls(dialect, unsigned=True, zerofill=True)
        assert signed_zerofill == unsigned_zerofill
        assert hash(signed_zerofill) == hash(unsigned_zerofill)
        assert dialect.format_data_type(signed_zerofill) == \
            dialect.format_data_type(unsigned_zerofill)

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_the_differ_sees_no_change_where_mariadb_can_make_none(self,
                                                                   dialect, cls, word):
        """The consequence, at the level the differ actually reads.

        ``SchemaDiffer._columns_equivalent`` compares ``parsed_data_type`` with
        ``!=`` when both sides carry one. Both sides of a real MariaDB diff are
        *introspected* -- a snapshot from before and a snapshot from now -- so
        both go through this dialect's own ``parse_type``. Two columns MariaDB
        stores identically must therefore arrive as the same object, or the
        differ reports a change the server cannot make.

        The two spellings are fed through the reader exactly as the catalog would
        deliver them, including the pre-fix emitted text ``X ZEROFILL``: the
        normalisation has to live in ``parse_type`` as well as in the
        constructor, or a dump written by the previous release would read back
        differently from one written now.
        """
        from rhosocial.activerecord.backend.introspection.types import (
            ColumnInfo,
            ColumnNullable,
        )

        differ = MariaDBSchemaDiffer()

        def column(catalog_text):
            return ColumnInfo(
                name="c", table_name="t", schema="d", ordinal_position=1,
                data_type=catalog_text.split("(")[0].lower(),
                data_type_full=catalog_text,
                parsed_data_type=dialect.parse_type(catalog_text),
                nullable=ColumnNullable.NULLABLE,
            )

        pre_fix_text = f"{word.lower()}({2 if word != 'BIGINT' else 20}) unsigned zerofill"
        assert differ._columns_equivalent(
            column(pre_fix_text), column(f"{word.lower()}(2) unsigned zerofill")
        )
        # And the reader normalises the bare spelling too, so text this backend
        # emitted before the fix reads back as the column it created.
        assert dialect.parse_type(f"{word} ZEROFILL") == \
            dialect.parse_type(f"{word} UNSIGNED ZEROFILL")

    @pytest.mark.parametrize("cls,word", INTEGER_WIDTHS)
    def test_unsigned_stays_in_identity(self, dialect, cls, word):
        """Why ``unsigned`` was **not** dropped from ``PARAMETERS``.

        Dropping it was the obvious way to make the two declarations compare
        equal, and it was rejected on the measurement rather than on taste:
        ``X`` and ``X UNSIGNED`` are two real columns (``int(11)`` vs
        ``int(10) unsigned``, and only the first stores ``-1``), so a signedness
        flag that is not in the identity would hide a change MariaDB can make.
        Only the combination the server refuses to store is normalised.
        """
        assert cls.PARAMETERS == ("unsigned", "zerofill")
        assert "unsigned" in cls.PARAMETERS
        assert cls(dialect, unsigned=True) != cls(dialect, unsigned=False)

    def test_core_integer_concepts_have_no_zerofill_and_are_unmoved(self, dialect):
        """Core's concepts carry no ``zerofill``, so nothing about them moved.

        ``zerofill`` is a MariaDB display attribute, not part of the concept, and
        the core classes deliberately have no field for it. The formatter reads
        it with ``getattr`` precisely so these classes need no ``ZEROFILL``
        branch -- which also means the normalisation cannot reach them.
        """
        for cls, word in ((TinyIntType, "TINYINT"), (SmallIntType, "SMALLINT"),
                          (IntegerType, "INT"), (BigIntType, "BIGINT")):
            assert not hasattr(cls(dialect), "zerofill")
            assert cls.PARAMETERS == ("unsigned",)
            for unsigned in (False, True):
                for spelling in cls.SPELLINGS:
                    assert dialect.format_data_type(
                        cls(dialect, unsigned=unsigned, spelling=spelling)
                    )[0] == (word if not unsigned else f"{word} UNSIGNED")

    def test_the_documentation_the_normalisation_rests_on_is_cited(self):
        """The claim is a claim about MariaDB, so the words are in the code.

        Not decoration: ``unsigned`` is only safe to normalise *because* the
        server does it, and the next reader has to be able to check that without
        leaving the file. Both pages are the ones the behaviour was measured
        against.
        """
        from rhosocial.activerecord.backend.impl.mariadb.expression import (
            types as maria_types,
        )
        doc = maria_types._zerofill_signedness.__doc__
        assert "will be set to UNSIGNED" in doc
        assert "automatically become UNSIGNED" in doc
        assert "special type of INT UNSIGNED is INT ZEROFILL" in doc
        assert "numeric-data-type-overview" in doc
        assert "numeric-data-types/int" in doc
        assert "normalising the column" in doc
        assert "not the caller changing their" in doc
        assert "15" in doc or "fifteen" in doc


class TestIntegerSpellingRoundTripOnALiveServer:
    """The same round trip, through a real MariaDB server.

    The unit tests above prove the string-level contract. This proves the
    contract survives the server, which is where two things happen that a string
    cannot show:

    * the server **rewrites its own synonyms** in the catalog -- ``INT1`` comes
      back as ``tinyint(4)``, ``INT2`` as ``smallint(6)``, ``INT3`` as
      ``mediumint(9)``, ``INT4`` as ``int(11)``, ``INT8`` as ``bigint(20)`` --
      which is why the honest round-trip target is the canonical word;
    * ``ZEROFILL`` makes the column unsigned whether or not the word
      ``UNSIGNED`` was written, so the attribute pair has to be read back from
      the catalog rather than from the text that was sent.

    Parametrised over the ``mariadb_backend`` fixture, so this runs against every
    wired scenario (10.2 through 13.1) rather than one.
    """

    #: ``(synonym, canonical word, class name)``
    WIDTHS = (
        ("INT1", "TINYINT", "MariaDBTinyIntType"),
        ("INT2", "SMALLINT", "MariaDBSmallIntType"),
        ("INT3", "MEDIUMINT", "MariaDBMediumIntType"),
        ("INT4", "INT", "MariaDBIntType"),
        ("INT8", "BIGINT", "MariaDBBigIntType"),
    )

    #: All four attribute combinations, including a bare ``ZEROFILL``. That one
    #: used to be left out with a comment saying ``unsigned`` "genuinely cannot
    #: come back as declared" -- which was the defect, stated as if it were a law
    #: of nature. It can come back, and it does: the backend normalises the pair
    #: at construction, so a bare ``ZEROFILL`` is declared, rendered and read
    #: back as the unsigned zero-padded column that is exactly what the server
    #: builds. See :class:`TestZerofillImpliesUnsigned`.
    ATTRS = ("", " UNSIGNED", " ZEROFILL", " UNSIGNED ZEROFILL")

    TABLE = "t_mariadb_synonym_roundtrip"

    @pytest.fixture
    def catalog_type(self, mariadb_backend):
        """Create one column with ``ddl``; return what the catalog reports."""
        def _read(ddl):
            mariadb_backend.execute(f"DROP TABLE IF EXISTS {self.TABLE}")
            mariadb_backend.execute(f"CREATE TABLE {self.TABLE} (c {ddl})")
            try:
                return mariadb_backend.fetch_one(
                    "SELECT COLUMN_TYPE AS t FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                    "AND COLUMN_NAME = 'c'",
                    (self.TABLE,),
                )["t"]
            finally:
                mariadb_backend.execute(f"DROP TABLE IF EXISTS {self.TABLE}")

        return _read

    @pytest.mark.parametrize("synonym,canonical,cls_name", WIDTHS)
    @pytest.mark.parametrize("attr", ATTRS)
    def test_synonym_column_reads_back_as_the_canonical_class(
        self, mariadb_backend, catalog_type, synonym, canonical, cls_name, attr,
    ):
        reported = catalog_type(synonym + attr)
        dialect = mariadb_backend.dialect
        parsed = dialect.parse_type(reported)

        assert type(parsed).__name__ == cls_name, reported
        assert parsed == dialect.parse_type(canonical + attr), reported
        assert parsed.unsigned is ("UNSIGNED" in attr or "ZEROFILL" in attr), reported
        assert parsed.zerofill is ("ZEROFILL" in attr), reported

    @pytest.mark.parametrize("synonym,canonical,cls_name", WIDTHS)
    def test_synonym_and_canonical_columns_are_identical_in_the_catalog(
        self, mariadb_backend, catalog_type, synonym, canonical, cls_name,
    ):
        """Same column, same reported type -- which is what proves they are one
        concept rather than two that merely look alike.

        It is also the observation that decides the round-trip target: MariaDB
        never reports its own synonyms back (``INT1`` is stored as ``tinyint(4)``,
        not as ``INT1``), so the synonym cannot be the spelling of an
        introspected column on any server, and a dialect that echoed it would
        make every such column differ from its own declaration.
        """
        from_synonym = catalog_type(synonym)
        from_canonical = catalog_type(canonical)
        assert from_synonym == from_canonical, (from_synonym, from_canonical)
        assert from_synonym.startswith(canonical.lower()), from_synonym

    @pytest.mark.parametrize("synonym,canonical,cls_name", WIDTHS)
    def test_bare_zerofill_makes_the_column_unsigned_server_side(
        self, mariadb_backend, catalog_type, synonym, canonical, cls_name,
    ):
        """The server fact the normalisation rests on.

        The manual says "If ``ZEROFILL`` is specified, the column will be set to
        ``UNSIGNED``", and it does: a column created ``INT ZEROFILL`` is stored as
        ``int(10) unsigned zerofill`` -- the same ``COLUMN_TYPE`` the explicit
        ``INT UNSIGNED ZEROFILL`` gets.

        This used to be recorded as an unfixed divergence, on the grounds that
        repairing it would change rendered SQL. It is now the *reason* the
        rendered SQL says what it says: ``_zerofill_signedness`` performs this
        same normalisation at construction, so the declaration, the DDL and the
        catalog all agree that a zero-padded integer is unsigned. See
        :class:`TestZerofillImpliesUnsigned`.
        """
        reported = catalog_type(f"{synonym} ZEROFILL")
        assert "unsigned" in reported.lower(), reported
        assert "zerofill" in reported.lower(), reported
        # One column, not two spellings of one: the catalog cannot tell them
        # apart, which is the whole reason the two declarations are the same
        # value object.
        assert reported == catalog_type(f"{canonical} UNSIGNED ZEROFILL")
        parsed = mariadb_backend.dialect.parse_type(reported)
        assert parsed.unsigned is True
        assert parsed.zerofill is True

    @pytest.mark.parametrize("synonym,canonical,cls_name", WIDTHS)
    @pytest.mark.parametrize("attr", ATTRS)
    def test_a_declared_column_survives_the_server_unchanged(
        self, mariadb_backend, catalog_type, synonym, canonical, cls_name, attr,
    ):
        """The whole round trip, live: declare, render, create, read back.

        This is the assertion the 150 failures across the matrix were about. It
        does not build the DDL by hand -- it takes ``format_data_type``'s own
        output, creates the column with it, reads ``COLUMN_TYPE`` back and
        parses it, so it fails if the formatter writes anything the catalog will
        not give back. Before the ``(unsigned=False, zerofill=True)``
        normalisation this failed for the bare-``ZEROFILL`` cell on all fifteen
        wired servers; ``ATTRS`` now includes it.
        """
        from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
            MariaDBBigIntType,
            MariaDBIntType,
            MariaDBMediumIntType,
            MariaDBSmallIntType,
            MariaDBTinyIntType,
        )
        cls = {
            "MariaDBTinyIntType": MariaDBTinyIntType,
            "MariaDBSmallIntType": MariaDBSmallIntType,
            "MariaDBMediumIntType": MariaDBMediumIntType,
            "MariaDBIntType": MariaDBIntType,
            "MariaDBBigIntType": MariaDBBigIntType,
        }[cls_name]

        dialect = mariadb_backend.dialect
        declared = cls(
            dialect,
            unsigned=("UNSIGNED" in attr or "ZEROFILL" in attr),
            zerofill=("ZEROFILL" in attr),
        )
        rendered = dialect.format_data_type(declared)[0]
        reported = catalog_type(rendered)
        back = dialect.parse_type(reported)

        assert back == declared, (
            f"{declared!r} rendered {rendered!r}, catalog said {reported!r}, "
            f"parsed back as {back!r}"
        )
        assert type(back) is cls, reported


class TestParseTypeReadsBackEveryTypeTheDialectWrites:
    """``parse_type`` must read back every type ``format_data_type`` writes.

    Populating ``ColumnInfo.parsed_data_type`` (see the introspection suite) is
    what made this observable: with the field left at ``None`` the schema differ
    compared the ``data_type`` string, so a type this dialect wrote and could
    not read back was invisible. Three such gaps were found by measuring the
    catalog on all fifteen wired servers and are fixed here.

    Each of them was found the same way -- render the type, create the column,
    read ``COLUMN_TYPE`` back, parse it, compare -- and each produced a *wrong*
    answer rather than an exception, which is the harder kind to notice.
    """

    def test_uuid_reads_back_as_the_native_type_not_a_custom_one(self, dialect):
        """``uuid`` is written by two formatters and read by none.

        ``format_data_type_uuid`` (the core ``uuid`` concept) and
        ``format_data_type_mariadb_uuid`` both write ``UUID``, and MariaDB 10.7
        stores it verbatim -- verified on all ten wired servers from 10.7 up,
        where ``CREATE TABLE t (c UUID)`` reports ``uuid``. ``parse_type`` had no
        branch for the word and fell through to ``CustomType('uuid')``, so a
        ``UUIDType`` column did not survive a round trip through this dialect's
        own vocabulary and introspection reported it as a type the backend does
        not model.
        """
        parsed = dialect.parse_type("uuid")
        assert isinstance(parsed, MariaDBUUIDType)
        assert dialect.format_data_type(parsed) == ("UUID", ())
        assert parsed == MariaDBUUIDType(dialect)
        # The core concept and the backend's own class are the same column, so
        # one renders and the other reads.
        assert dialect.format_data_type(UUIDType(dialect)) == ("UUID", ())

    def test_uuid_is_gated_at_10_7_like_xmltype(self):
        """Below the gate the word cannot come from the catalog, and saying so.

        Mirrors the ``XMLTYPE`` branch: on a server with no ``UUID`` type the
        honest reading is the fallback's -- ``CustomType`` -- rather than handing
        back a class whose formatter would raise ``UnsupportedFeatureError`` on
        the very dialect that produced it.
        """
        old = MariaDBDialect(version=(10, 6, 0))
        assert old.supports_data_type_uuid() is False
        assert isinstance(old.parse_type("uuid"), CustomType)
        new = MariaDBDialect(version=(10, 7, 0))
        assert isinstance(new.parse_type("uuid"), MariaDBUUIDType)

    @pytest.mark.parametrize("raw,expected", [
        ("geometry", "MariaDBGeometryType"),
        ("geometrycollection", "MariaDBGeometryCollectionType"),
        ("point", "MariaDBPointType"),
        ("linestring", "MariaDBLineStringType"),
        ("polygon", "MariaDBPolygonType"),
        ("multipoint", "MariaDBMultiPointType"),
        ("multilinestring", "MariaDBMultiLineStringType"),
        ("multipolygon", "MariaDBMultiPolygonType"),
    ])
    def test_each_spatial_word_reads_back_as_its_own_shape(self, dialect, raw, expected):
        """``GEOMETRYCOLLECTION`` was being read as ``GEOMETRY``.

        The dispatch was a ``startswith`` loop in declaration order, and
        ``GEOMETRYCOLLECTION`` begins with ``GEOMETRY`` -- verified on all fifteen
        servers, where ``CREATE TABLE t (c GEOMETRYCOLLECTION)`` introspected as
        ``MariaDBGeometryType``. That is a false identity claim in the worst
        direction for a differ: it made the schema differ report *no* change
        between a collection column and a geometry column, a difference MariaDB
        can certainly make. Dispatch is now on the leading **word**, so no
        ordering discipline is needed to keep the eight apart.
        """
        parsed = dialect.parse_type(raw)
        assert type(parsed).__name__ == expected, raw
        assert dialect.format_data_type(parsed) == (raw.upper(), ())

    def test_a_collection_is_not_the_generic_geometry_type(self, dialect):
        from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
            MariaDBGeometryCollectionType,
            MariaDBGeometryType,
        )

        collection = dialect.parse_type("geometrycollection")
        generic = dialect.parse_type("geometry")
        assert isinstance(collection, MariaDBGeometryCollectionType)
        assert collection != generic
        assert type(collection) is not type(generic)

    @pytest.mark.parametrize("raw,precision", [
        ("datetime", None),
        ("datetime(0)", 0),
        ("datetime(6)", 6),
        ("date", "DATE"),
    ])
    def test_datetime_keeps_its_fractional_seconds(self, dialect, raw, precision):
        """``DATETIME`` starts with ``DATE``, so branch order was load-bearing.

        With the ``DATE`` branch first, every ``DATETIME`` -- and every
        ``DATETIME(6)`` -- took its early return and came back as a bare
        ``DateTimeType``, precision dropped. Verified live on all fifteen
        servers, where ``CREATE TABLE t (c DATETIME(6))`` reports ``datetime(6)``
        and was read as ``DateTimeType(precision=None)`` -- indistinguishable
        from a plain ``DATETIME``. The fsp is the number of fractional digits
        the column keeps, so a ``DATETIME`` and a ``DATETIME(6)`` are different
        columns; the differ already reported that for ``TIMESTAMP`` and ``TIME``
        and silently missed it for ``DATETIME``.
        """
        from rhosocial.activerecord.backend.expression.types import (
            DateTimeType,
            DateType,
        )

        parsed = dialect.parse_type(raw)
        if precision == "DATE":
            assert isinstance(parsed, DateType), raw
        else:
            assert isinstance(parsed, DateTimeType), raw
            assert parsed.precision == precision, raw

    def test_datetime_fsp_survives_the_full_round_trip(self, dialect):
        from rhosocial.activerecord.backend.expression.types import DateTimeType

        for precision in (None, 0, 3, 6):
            declared = DateTimeType(dialect, precision)
            rendered = dialect.format_data_type(declared)[0]
            # The catalog keeps the parent'shesised form; the display width and
            # the fsp are both reported in COLUMN_TYPE.
            assert dialect.parse_type(rendered.lower()) == declared, rendered

    def test_every_type_this_dialect_writes_is_readable(self, dialect):
        """The general form of the rule, across every rendered name.

        For every type this dialect renders, the rendered text must come back out
        of ``parse_type`` as a real class -- never a ``CustomType``, which is the
        honest answer only for a type the backend has *no* class for.

        The round trip's target for a core concept is the ``mariadb_*`` class of
        the same width, not the concept itself, and that is deliberate rather than
        a defect left here: ``parse_type`` returns a ``MariaDBIntType`` for
        ``int(11)`` because ``zerofill`` has nowhere to live on the core concept,
        so the backend's class is the only lossless answer. It has no effect on
        the schema differ, which compares two *introspected* columns and so sees
        the ``mariadb_*`` class on both sides.
        """
        from rhosocial.activerecord.backend.expression.types import (
            DecimalType, FloatType, TextType, TimestampType, TimeType,
            DateTimeType, VarCharType, CharType, BlobType, JsonType,
            DataType as CoreDataType,
        )
        #: ``(declared, the class the round trip must come back as)``
        writable = [
            (MariaDBTinyIntType(dialect), MariaDBTinyIntType),
            (MariaDBSmallIntType(dialect), MariaDBSmallIntType),
            (MariaDBMediumIntType(dialect), MariaDBMediumIntType),
            (MariaDBIntType(dialect), MariaDBIntType),
            (MariaDBBigIntType(dialect, unsigned=True), MariaDBBigIntType),
            (TinyIntType(dialect, unsigned=True), MariaDBTinyIntType),
            (SmallIntType(dialect), MariaDBSmallIntType),
            (IntegerType(dialect), MariaDBIntType),
            (BigIntType(dialect), MariaDBBigIntType),
            (DecimalType(dialect, 10, 2), DecimalType),
            (FloatType(dialect), FloatType),
            (TextType(dialect), MariaDBTextType),
            (VarCharType(dialect, 100), VarCharType),
            (CharType(dialect, 4), CharType),
            (TimestampType(dialect, 6), TimestampType),
            (TimeType(dialect), TimeType),
            (DateTimeType(dialect), DateTimeType),
            (JsonType(dialect), JsonType),
            (BlobType(dialect), MariaDBBlobType),
        ]
        for declared, expected_cls in writable:
            rendered = dialect.format_data_type(declared)[0]
            back = dialect.parse_type(rendered)
            assert not isinstance(back, CustomType), (
                f"{declared!r} renders {rendered!r} but parse_type returned "
                f"{back!r}"
            )
            assert isinstance(back, CoreDataType), rendered
            assert type(back) is expected_cls, f"{rendered!r} -> {back!r}"
            assert back == dialect.parse_type(rendered), rendered
            # A core concept and the backend class of the same width are not
            # ``==`` (DataType.__eq__ is class-exact), so only the backend's own
            # declarations round-trip to themselves. For a core concept the
            # assertion is the class, which is the part that used to be
            # CustomType.
            if type(declared) is expected_cls:
                assert back == declared, f"{rendered!r} -> {back!r}"
