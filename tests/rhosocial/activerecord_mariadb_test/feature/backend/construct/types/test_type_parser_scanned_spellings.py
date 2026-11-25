# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/types/test_type_parser_scanned_spellings.py
"""The read-direction scans keep the spellings MariaDB actually reports.

``MariaDBTypeParser`` reads a catalog type string with character scans
(``_scan.py``) rather than patterns, so the edges the scans have to get right
are worth pinning separately from the formatter round trips: a type word is
matched whole rather than by prefix, an enum label is read past its commas and
digits, a space inside the length parenthesis keeps the length unread (as the
catalog never writes one), and a spatial reference system is read only from
MariaDB's own attribute name.

Everything here is offline: no server is asked anything, and every expected
value is the one MariaDB writes into ``COLUMN_TYPE``.
"""

import pytest
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    CustomType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    TimestampTzType,
    TimeTzType,
    VarCharType,
)

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBBigIntType,
    MariaDBEnumType,
    MariaDBIntType,
    MariaDBSetType,
    MariaDBTinyIntType,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.type_parser import (
    MariaDBTypeParser,
)


@pytest.fixture
def parser():
    # 10.7 is above every gate the parser reads in these cases, so the
    # spellings below are not masked by a version refusal.
    return MariaDBTypeParser(MariaDBDialect(version=(10, 7, 0)))


# ---------------------------------------------------------------------------
# The leading type word is compared whole, not by prefix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("INT8", MariaDBBigIntType),
        ("INT1", MariaDBTinyIntType),
        ("INTEGER", MariaDBIntType),
        # The old alternation needed \b to keep these apart from INT; the whole-word
        # scan keeps them apart because they are simply not words in the set.
        ("INT16", CustomType),
        ("INT_UNSIGNED", CustomType),
    ],
)
def test_the_leading_word_is_matched_whole(parser, raw, expected):
    assert type(parser.parse(raw)) is expected


def test_a_bare_int1_is_not_a_boolean(parser):
    """INT1's name contains a "1"; only a parenthesised width may be read."""
    assert isinstance(parser.parse("INT1"), MariaDBTinyIntType)
    assert isinstance(parser.parse("INT1(4)"), MariaDBTinyIntType)


def test_bool_is_its_own_word(parser):
    assert isinstance(parser.parse("BOOL"), BooleanType)
    assert isinstance(parser.parse("BOOLEAN"), BooleanType)


# ---------------------------------------------------------------------------
# Enum / SET: quoted labels and the attribute tail
# ---------------------------------------------------------------------------


def test_enum_labels_are_read_whole(parser):
    """Digits, commas and an empty label inside the quotes all stay inside."""
    parsed = parser.parse("enum('a1','b,c','')")
    assert isinstance(parsed, MariaDBEnumType)
    assert parsed.values == ("a1", "b,c", "")


def test_enum_charset_and_collation_are_read_from_the_tail(parser):
    parsed = parser.parse("enum('a','b') character set utf8mb4 collate utf8mb4_bin")
    assert (parsed.charset, parsed.collation) == ("UTF8MB4", "UTF8MB4_BIN")
    assert parser.dialect.format_data_type(parsed) == (
        "ENUM('a','b') CHARACTER SET UTF8MB4 COLLATE UTF8MB4_BIN",
        (),
    )


def test_set_charset_and_collation_are_read_from_the_tail(parser):
    parsed = parser.parse("set('read','write') collate utf8mb4_bin")
    assert isinstance(parsed, MariaDBSetType)
    assert parsed.values == ("read", "write")
    assert (parsed.charset, parsed.collation) == (None, "UTF8MB4_BIN")


def test_an_unterminated_quote_is_not_half_read(parser):
    parsed = parser.parse("enum('a','b")
    assert isinstance(parsed, MariaDBEnumType)
    assert parsed.values == ("a",)


# ---------------------------------------------------------------------------
# Length and display width: what counts as "inside the parentheses"
# ---------------------------------------------------------------------------


def test_a_tight_parenthesis_carries_the_length(parser):
    assert isinstance(parser.parse("varchar(255)"), VarCharType)
    assert parser.parse("varchar(255)").length == 255
    # The scan searches anywhere, exactly as the catalog's own spelling allows.
    assert parser.parse("char (10)").length == 10


def test_a_padded_length_is_not_read(parser):
    """``CHAR( 10 )`` is not a spelling MariaDB reports, so it stays unread."""
    assert parser.parse("char( 10 )").length is None


@pytest.mark.parametrize("raw", ["tinyint(1)", "tinyint (1)", "tinyint( 1 )"])
def test_the_display_width_tolerates_padding(parser, raw):
    """``TINYINT(1)`` is the boolean spelling when nothing else is declared."""
    assert isinstance(parser.parse(raw), BooleanType)


def test_decimal_reads_both_parameters_from_digit_runs(parser):
    parsed = parser.parse("decimal(10,2) unsigned")
    assert parsed == DecimalType(parser.dialect, 10, 2, unsigned=True)


def test_float_p_still_chooses_the_storage_class(parser):
    """One bit-precision argument below 25 is FLOAT; 25 and above is DOUBLE."""
    assert isinstance(parser.parse("float(24)"), FloatType)
    assert isinstance(parser.parse("float(25)"), DoubleType)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("datetime(6)", 6),
        ("timestamp(3)", 3),
        ("time(2)", 2),
    ],
)
def test_fractional_seconds_come_from_the_first_digit_run(parser, raw, expected):
    assert parser.parse(raw).precision == expected


def test_a_time_zone_tail_keeps_the_precision(parser):
    assert isinstance(parser.parse("timestamp(3) with time zone"), TimestampTzType)
    assert isinstance(parser.parse("time(2) with time zone"), TimeTzType)
    assert parser.parse("timestamp(3) with time zone").precision == 3
    # DATE has no fractional-seconds argument to read in the first place.
    assert isinstance(parser.parse("date"), DateType)


# ---------------------------------------------------------------------------
# Spatial reference system: MariaDB's spelling only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "point ref_system_id=4326",
        "point REF_SYSTEM_ID = 4326",
        "polygon ref_system_id  =  4326",
    ],
)
def test_the_spatial_reference_system_is_read(parser, raw):
    assert parser.parse(raw).srid == 4326


def test_mysql_srid_spelling_declares_nothing(parser):
    assert parser.parse("point srid 4326").srid is None
