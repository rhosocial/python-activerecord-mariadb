# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_column_suggestions.py
"""MariaDB's column-type suggestion table, and the capabilities it narrows.

Two things are under test, and they are the two halves of
``column-suggestion-protocol.md`` §12's MariaDB row:

* the **table** -- all 18 entries answered, with MariaDB's own answer where it
  differs from core's neutral baseline, and one version-gated refusal;
* the **narrowing** -- the ``(column class, operation)`` pairs MariaDB cannot
  honour, and the versions at which each becomes available.

Nothing here needs a server. Every version boundary the tests assert is the one
``MARIADB_VERSION_BOUNDARIES`` already records, and each of those was measured
against a live MariaDB (see ``suggested-pairing-json.md`` /
``suggested-pairing-array.md``); asserting against the same table the mixin
reads is what keeps the two from drifting apart silently.

The completeness assertion is deliberately in this repository as well as in the
testsuite: a backend with a hole in its table should fail its own tests, not
only the cross-backend contract run.
"""

import datetime
import decimal
import enum
import uuid

import pytest

from rhosocial.activerecord.backend.expression.column_suggestions import (
    COLUMN_TYPE_ENTRIES,
    NEUTRAL_COLUMN_TYPE_SUGGESTIONS,
    UNSUPPORTED,
    ColumnTypeResolutionError,
)
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
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
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.backend import (
    MARIADB_VERSION_BOUNDARIES,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.column_suggestion import (
    MariaDBColumnSuggestionMixin,
)

# Bracketing versions, matching the ones the pairing reports measured on:
# 10.2.44 / 10.3.39 sit below the JSON gate, 10.5.29 has JSON but no
# JSON_TABLE, 10.6.28 has both, 11.4.13 adds native UUID, and 13.1.1 adds the
# native arrows and JSON_EQUALS.
PRE_JSON = (10, 1, 41)
JSON_NO_TABLE = (10, 5, 29)
JSON_WITH_TABLE = (10, 6, 28)
PRE_NATIVE_UUID = (10, 6, 28)
LTS_114 = (11, 4, 13)
RC_131 = (13, 1, 1)


def _dialect(version):
    return MariaDBDialect(version=version)


class TestCompleteness:
    """Every entry of the closed protocol list is answered."""

    def test_all_eighteen_entries_are_answered(self):
        table = _dialect(RC_131).suggested_column_types()
        missing = [e for e in COLUMN_TYPE_ENTRIES if e not in table]
        assert missing == [], f"unanswered entries: {missing}"

    def test_no_entry_is_none(self):
        """``None`` would read as "not filled in yet"; ``UNSUPPORTED`` is the refusal."""
        table = _dialect(RC_131).suggested_column_types()
        for entry in COLUMN_TYPE_ENTRIES:
            assert table[entry] is not None, entry

    def test_every_answer_is_a_column_class(self):
        table = _dialect(RC_131).suggested_column_types()
        for entry in COLUMN_TYPE_ENTRIES:
            answer = table[entry]
            assert answer is UNSUPPORTED or issubclass(answer, ColumnBase), entry

    def test_the_table_is_not_core_baseline_aliasing(self):
        """A backend that inherited core's table would answer ``ArrayColumn`` for ``list``.

        That is the honest answer on PostgreSQL and a wrong one here, so the
        check that this table is MariaDB's own is that it is not core's dict.
        """
        assert MariaDBColumnSuggestionMixin.COLUMN_TYPE_SUGGESTIONS is not \
            NEUTRAL_COLUMN_TYPE_SUGGESTIONS

    @pytest.mark.parametrize(
        "annotation, expected",
        [
            (bool, BooleanColumn),
            (int, IntegerColumn),
            (float, FloatColumn),
            (decimal.Decimal, DecimalColumn),
            (str, StringColumn),
            (bytes, BinaryColumn),
            (bytearray, BinaryColumn),
            (datetime.date, DateTimeColumn),
            (datetime.time, DateTimeColumn),
            (datetime.datetime, DateTimeColumn),
            (datetime.timedelta, NumericColumn),
            (uuid.UUID, UUIDColumn),
            (dict, JSONColumn),
            (list, JSONColumn),
            (tuple, JSONColumn),
            (set, JSONColumn),
            (frozenset, JSONColumn),
            (enum.Enum, StringColumn),
        ],
        ids=lambda v: getattr(v, "__name__", str(v)),
    )
    def test_each_entry_answers_what_mariadb_can_do(self, annotation, expected):
        assert _dialect(RC_131).column_class_for(annotation) is expected

    def test_list_is_not_an_array_column(self):
        """MariaDB implements no array type, so ``ArrayColumn`` would be a false promise.

        ``ArrayColumn``'s whole surface is ``array_length`` / ``unnest`` over a
        native array; MariaDBArrayMixin refuses both outright.
        """
        table = _dialect(RC_131).suggested_column_types()
        assert table[list] is JSONColumn
        assert table[list] is not ArrayColumn

    def test_the_returned_table_is_a_copy(self):
        """A per-version answer must not leak into the next dialect built."""
        dialect = _dialect(PRE_JSON)
        first = dialect.suggested_column_types()
        first[dict] = StringColumn
        assert _dialect(RC_131).suggested_column_types()[dict] is JSONColumn


class TestDictVersionGate:
    """``dict`` is refused below MariaDB 10.2, where no JSON function exists."""

    def test_dict_is_refused_below_the_json_gate(self):
        table = _dialect(PRE_JSON).suggested_column_types()
        assert table[dict] is UNSUPPORTED

    def test_dict_is_json_column_from_the_gate_up(self):
        for version in (JSON_NO_TABLE, JSON_WITH_TABLE, LTS_114, RC_131):
            table = _dialect(version).suggested_column_types()
            assert table[dict] is JSONColumn, version

    def test_the_gate_is_the_boundary_the_json_mixin_uses(self):
        """Not a number written twice: the gate and the JSON mixin share one table."""
        assert _dialect((10, 2, 2)).suggested_column_types()[dict] is UNSUPPORTED
        assert _dialect(MARIADB_VERSION_BOUNDARIES["JSON_FUNCTIONS"]) \
            .suggested_column_types()[dict] is JSONColumn

    def test_the_gate_agrees_with_supports_json_type(self):
        """Two gates for one fact must not disagree.

        The refusal exists because the JSON functions are absent; if
        ``supports_json_type`` said they were present on a version where the
        table says otherwise, one of the two is wrong.
        """
        for version in (PRE_JSON, JSON_WITH_TABLE, LTS_114, RC_131):
            dialect = _dialect(version)
            assert (dialect.suggested_column_types()[dict] is UNSUPPORTED) is (
                not dialect.supports_json_type()
            ), version

    def test_refusal_becomes_a_definition_time_failure(self):
        with pytest.raises(ColumnTypeResolutionError, match="UNSUPPORTED"):
            _dialect(PRE_JSON).column_class_for(dict)

    def test_the_containers_are_not_refused_below_the_gate(self):
        """One entry is gated, on the evidence gathered for one entry.

        Length and containment over a JSON array are reachable through the same
        function family, so refusing five entries on the strength of one
        entry's measurement would be a wider refusal than the servers support.
        """
        table = _dialect(PRE_JSON).suggested_column_types()
        for annotation in (list, tuple, set, frozenset):
            assert table[annotation] is JSONColumn, annotation


class TestUuidIsNotGatedOnStorage:
    """MariaDB's native UUID (10.7+) is a storage fact, so the column answer does not move."""

    @pytest.mark.parametrize(
        "version", [PRE_NATIVE_UUID, LTS_114, RC_131], ids=lambda v: ".".join(map(str, v))
    )
    def test_uuid_column_on_both_sides_of_the_native_type(self, version):
        """MySQL has no UUID type on any version and substitutes BINARY(16).

        MariaDB gained a native one at 10.7. Both carry the same operations --
        equality and ``IN`` -- so the column class is the same on both sides of
        the boundary; only the storage word differs, and that is the DataType
        layer's answer.
        """
        dialect = _dialect(version)
        assert dialect.column_class_for(uuid.UUID) is UUIDColumn

        # ...while the storage side does follow the server: the native `uuid`
        # key appears at 10.7 and the 16-byte substitute is suggested instead.
        native = version >= MARIADB_VERSION_BOUNDARIES["UUID"]
        assert ("uuid" in dialect.supports_data_types()) is native
        assert "uuid" not in dialect.suggested_data_types()


class TestOperationNarrowing:
    """The ``(column class, operation)`` pairs MariaDB cannot honour."""

    def test_ilike_is_unavailable_on_every_version(self):
        """MariaDB has no ILIKE operator; only PostgreSQL and ClickHouse do."""
        for version in (PRE_JSON, JSON_NO_TABLE, JSON_WITH_TABLE, LTS_114, RC_131):
            assert _dialect(version).supports_column_operation("StringColumn", "ilike") is False

    def test_ilike_narrowing_matches_the_dialect_own_ilike_support(self):
        """Two declarations of one fact must agree."""
        for version in (JSON_WITH_TABLE, RC_131):
            dialect = _dialect(version)
            assert dialect.supports_column_operation("StringColumn", "ilike") is \
                dialect.supports_ilike()

    def test_like_is_not_narrowed(self):
        """Narrowing one pair must not refuse the others on the same class.

        The default collation already makes ``LIKE`` case-insensitive, which is
        why losing ``ilike`` costs nothing and must not cost ``like``.
        """
        assert _dialect(RC_131).supports_column_operation("StringColumn", "like") is True

    def test_the_narrowing_is_scoped_to_the_column_class(self):
        """``ilike`` is a string operation; other columns keep their own surface."""
        assert _dialect(RC_131).supports_column_operation("IntegerColumn", "ilike") is True

    @pytest.mark.parametrize("op", ["unnest", "json_table"])
    def test_json_table_backed_operations_need_10_6(self, op):
        """Both names the same server fact: expanding a JSON array is JSON_TABLE."""
        assert _dialect(JSON_NO_TABLE).supports_column_operation("JSONColumn", op) is False
        for version in (JSON_WITH_TABLE, LTS_114, RC_131):
            assert _dialect(version).supports_column_operation("JSONColumn", op) is True

    def test_json_table_narrowing_matches_the_json_mixin_gate(self):
        dialect = _dialect(JSON_NO_TABLE)
        assert dialect.supports_column_operation("JSONColumn", "json_table") is \
            dialect.supports_json_table()

    def test_json_equal_needs_the_native_arrow_release(self):
        """JSON_EQUALS arrived with the native ``->`` / ``->>`` operators in 13.1."""
        for version in (JSON_WITH_TABLE, LTS_114, (13, 0, 2)):
            assert _dialect(version).supports_column_operation("JSONColumn", "json_equal") is False
        assert _dialect(RC_131).supports_column_operation("JSONColumn", "json_equal") is True

    def test_below_13_1_plain_equality_is_still_available(self):
        """MariaDB's JSON is a LONGTEXT alias the server does not normalise.

        So text equality is *correct* here, unlike on MySQL 5.7/8.0 whose JSON
        columns normalise whitespace and key order and turn a bound parameter
        into a silent zero-match. The refusal is for the JSON-semantic
        operation, not for equality as such.
        """
        for version in (JSON_WITH_TABLE, LTS_114):
            assert _dialect(version).supports_column_operation("JSONColumn", "eq") is True

    def test_json_path_access_is_never_narrowed(self):
        """The arrow operators are 13.1-native, but the function form works everywhere.

        This backend renders ``JSON_EXTRACT`` rather than ``->``, so no version
        loses path access -- which is why ``dict`` needs no gate above 10.2.
        """
        for op in ("json_path", "json_value"):
            for version in (JSON_WITH_TABLE, LTS_114, RC_131):
                assert _dialect(version).supports_column_operation("JSONColumn", op) is True

    def test_a_column_class_this_backend_never_suggests_is_unaffected(self):
        """The narrowing is a property of MariaDB's operation surface, not of a guess.

        ``ArrayColumn`` is not in the table (MariaDB has no arrays), so its
        operations are not narrowed here; a caller who declares one explicitly
        with ``UseColumnType`` gets the core answer and the server's refusal.
        """
        dialect = _dialect(RC_131)
        assert dialect.supports_column_operation("ArrayColumn", "unnest") is True


def test_every_narrowed_pair_has_a_version_gate_that_exists():
    """A gate keyed on a name the boundary table does not define would be a KeyError.

    The two JSON gates are read from ``MARIADB_VERSION_BOUNDARIES`` rather than
    written inline, which is what lets this assert rather than assume: the keys
    are named here, so a renamed boundary fails here instead of at the first
    ``supports_column_operation`` call on an old server.
    """
    for key in ("JSON_FUNCTIONS", "JSON_TABLE", "JSON_ARROW_NATIVE"):
        assert key in MARIADB_VERSION_BOUNDARIES