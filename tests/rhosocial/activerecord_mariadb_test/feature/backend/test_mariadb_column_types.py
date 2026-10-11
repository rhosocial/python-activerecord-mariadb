# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_column_types.py
"""MariaDB's own column-type table, read through the rebuilt core protocol.

Two things are under test, and they are the two halves of
``column-suggestion-protocol.md`` §12's MariaDB row:

* the **table** -- all 18 common entries answered, with MariaDB's own answer
  where it differs from the portable baseline, and one version-gated refusal;
* the **storage side** -- that the facts MariaDB answers differently from MySQL
  live on the DataType layer and never move the column class.

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

from rhosocial.activerecord.backend.dialect.mixins import ColumnTypeMixin
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
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
from rhosocial.activerecord.backend.impl.dummy.column_type import DUMMY_COLUMN_TYPES
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins import (
    MariaDBColumnTypeMixin,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.backend import (
    MARIADB_VERSION_BOUNDARIES,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.column_type import (
    MARIADB_COLUMN_TYPES,
)
from rhosocial.activerecord.base.field_proxy import (
    ColumnTypeResolutionError,
    FieldAccessor,
)
from rhosocial.activerecord.testsuite.feature.query.typed_column.column_helpers import (
    COMMON_TYPES,
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


def resolve(dialect, annotation, declared=None):
    """The class *dialect* selects for *annotation*, through the protocol.

    The selection step ``Model.c.<field>`` performs, invoked without a model:
    with nothing declared the backend's own table answers, and *declared* is
    the field's column-type declaration when a test exercises one.
    """
    return FieldAccessor._select_column_class(dialect, annotation, declared)


#: ``{entry: column class}`` as MariaDB states it. Written out in full rather
#: than derived, because a derived table would restate the code's own answer
#: back at itself and could not catch a change to it.
_MARIADB_ANSWERS = [
    (bool, BooleanColumn),
    (int, IntegerColumn),
    (float, NumericColumn),
    (decimal.Decimal, NumericColumn),
    (str, StringColumn),
    (bytes, BinaryColumn),
    (bytearray, BinaryColumn),
    (datetime.date, TimestampColumn),
    (datetime.time, TimestampColumn),
    (datetime.datetime, TimestampColumn),
    (datetime.timedelta, NumericColumn),
    (uuid.UUID, UUIDColumn),
    (dict, JSONColumn),
    (list, JSONColumn),
    (tuple, JSONColumn),
    (set, JSONColumn),
    (frozenset, JSONColumn),
    (enum.Enum, StringColumn),
]

_ENTRY_IDS = [getattr(entry, "__name__", str(entry)) for entry, _ in _MARIADB_ANSWERS]


class TestCompleteness:
    """Every entry of the closed protocol list is answered."""

    def test_all_eighteen_entries_are_answered(self):
        table = _dialect(RC_131).suggested_column_types()
        missing = [e for e in COMMON_TYPES if e not in table]
        assert missing == [], f"unanswered entries: {missing}"

    def test_the_table_carries_no_entry_beyond_the_contract(self):
        """Asserted so an extension added later is a deliberate act.

        MariaDB has no Python type of its own to offer through
        ``suggested_extra_column_types()``, so the two lists coincide.
        """
        table = _dialect(RC_131).suggested_column_types()
        assert set(table) == set(COMMON_TYPES)
        assert _dialect(RC_131).suggested_extra_column_types() == {}

    def test_no_entry_is_none_on_a_modern_server(self):
        """``None`` is the last resort, and MariaDB is past arriving at one.

        Every measurement below found a working pairing, so answering ``None``
        on 13.1 would read as "not filled in yet" rather than as a decision.
        """
        table = _dialect(RC_131).suggested_column_types()
        for entry in COMMON_TYPES:
            assert table[entry] is not None, entry

    def test_every_answer_is_a_column_class(self):
        """The two allowed states, asserted together: a class, or a refusal.

        Anything else -- a string, a type that is not a ``ColumnBase`` -- is a
        malformed table that whichever consumer meets it first would read as a
        column class, so it fails here instead.
        """
        table = _dialect(PRE_JSON).suggested_column_types()
        for entry in COMMON_TYPES:
            answer = table[entry]
            assert answer is None or issubclass(answer, ColumnBase), entry

    def test_a_none_answer_is_deliberate_and_scoped(self):
        """The only refusal this backend makes, and where it is allowed to be.

        A ``None`` anywhere else would be an unexamined hole: it must be
        ``dict`` (the entry the JSON gate refuses) and it must be reachable
        only on the below-10.2 side of that gate.
        """
        old = _dialect(PRE_JSON).suggested_column_types()
        refused = {e for e, answer in old.items() if answer is None}
        assert refused == {dict}, f"unexpected refusals: {refused}"

        new = _dialect(RC_131).suggested_column_types()
        assert not [e for e, answer in new.items() if answer is None]

    def test_list_is_not_an_array_column(self):
        """MariaDB implements no array type, so ``ArrayColumn`` would be a false promise.

        ``ArrayColumn``'s whole surface is ``array_length`` / ``unnest`` over a
        native array; ``MariaDBArrayMixin`` refuses the rendering outright.
        """
        assert MARIADB_COLUMN_TYPES[list] is JSONColumn
        assert MARIADB_COLUMN_TYPES[list] is not ArrayColumn

    def test_the_table_is_not_the_portable_baseline(self):
        """A backend that answered with the dummy's table would promise arrays.

        The dummy states the dialect-less baseline, where a sequence is an
        ``ArrayColumn``; that is the honest answer on PostgreSQL and a wrong
        one here, so the check that this table is MariaDB's own is that it
        differs from the dummy's in the sequence entries.
        """
        assert MARIADB_COLUMN_TYPES is not DUMMY_COLUMN_TYPES
        for entry in (list, tuple, set, frozenset):
            assert MARIADB_COLUMN_TYPES[entry] is not DUMMY_COLUMN_TYPES[entry]

    def test_the_returned_table_is_a_copy(self):
        """A per-version answer must not leak into the next dialect built."""
        dialect = _dialect(PRE_JSON)
        first = dialect.suggested_column_types()
        first[dict] = StringColumn
        assert _dialect(RC_131).suggested_column_types()[dict] is JSONColumn

    @pytest.mark.parametrize("annotation, expected", _MARIADB_ANSWERS, ids=_ENTRY_IDS)
    def test_each_entry_answers_what_mariadb_can_do(self, annotation, expected):
        assert resolve(_dialect(RC_131), annotation) is expected


class TestDialectComposition:
    """The dialect really composes the new mixin, and ahead of core's copy."""

    def test_the_dialect_is_the_mixin(self):
        assert isinstance(_dialect(RC_131), MariaDBColumnTypeMixin)

    def test_the_mariadb_mixin_precedes_core_copy(self):
        """C3 puts a subclass first, but only because the dialect composes it.

        Core's ``ColumnTypeMixin`` answers nothing -- it raises -- so if the
        ordering were reversed the dialect would refuse every field instead of
        answering MariaDB's table. The assertion pins the composition rather
        than the inheritance the two classes already have.
        """
        mro = MariaDBDialect.__mro__
        assert mro.index(MariaDBColumnTypeMixin) < mro.index(ColumnTypeMixin)

    def test_the_answer_the_dialect_gives_is_the_backends_own(self):
        """Not core's ``NotImplementedError``, and not the dummy's table."""
        dialect = _dialect(RC_131)
        assert resolve(dialect, list) is JSONColumn
        assert resolve(dialect, list) is not DUMMY_COLUMN_TYPES[list]
        assert resolve(dialect, int) is IntegerColumn


class TestDictVersionGate:
    """``dict`` is refused below MariaDB 10.2, where no JSON function exists."""

    def test_dict_is_refused_below_the_json_gate(self):
        table = _dialect(PRE_JSON).suggested_column_types()
        assert table[dict] is None

    def test_dict_is_json_column_from_the_gate_up(self):
        for version in (JSON_NO_TABLE, JSON_WITH_TABLE, LTS_114, RC_131):
            table = _dialect(version).suggested_column_types()
            assert table[dict] is JSONColumn, version

    def test_the_gate_is_the_boundary_the_json_mixin_uses(self):
        """Not a number written twice: the gate and the JSON mixin share one table."""
        assert _dialect((10, 2, 2)).suggested_column_types()[dict] is None
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
            assert (dialect.suggested_column_types()[dict] is None) is (
                not dialect.supports_json_type()
            ), version

    def test_refusal_becomes_a_definition_time_failure(self):
        """And it names the escape hatch, so the author is not left guessing."""
        with pytest.raises(ColumnTypeResolutionError) as err:
            resolve(_dialect(PRE_JSON), dict)
        assert "UseColumnType" in str(err.value)

    def test_the_containers_are_not_refused_below_the_gate(self):
        """One entry is gated, on the evidence gathered for one entry.

        Length and containment over a JSON array are reachable through the same
        function family, so refusing five entries on the strength of one
        entry's measurement would be a wider refusal than the servers support.
        """
        table = _dialect(PRE_JSON).suggested_column_types()
        for annotation in (list, tuple, set, frozenset):
            assert table[annotation] is JSONColumn, annotation

    def test_a_none_answer_is_refused_by_the_escape_hatch(self):
        """The declaration is the only route past a refusal, and it wins.

        Asserted here because it is what makes the ``None`` below 10.2 a
        decision rather than a dead end: an author on an old server declares
        ``UseColumnType`` and gets the column they asked for.
        """
        from rhosocial.activerecord.base.fields import UseColumnType
        from rhosocial.activerecord.backend.expression.core import Column

        resolved = resolve(_dialect(PRE_JSON), dict, UseColumnType(Column))
        assert resolved is Column


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
        assert resolve(dialect, uuid.UUID) is UUIDColumn

        # ...while the storage side does follow the server: the native `uuid`
        # key appears at 10.7 and the 16-byte substitute is suggested instead.
        native = version >= MARIADB_VERSION_BOUNDARIES["UUID"]
        assert ("uuid" in dialect.supports_data_types()) is native
        assert "uuid" not in dialect.suggested_data_types()


def test_every_gate_the_mixin_reads_exists():
    """A gate keyed on a name the boundary table does not define would be a KeyError.

    The JSON gate is read from ``MARIADB_VERSION_BOUNDARIES`` rather than written
    inline, which is what lets this assert rather than assume: the key is named
    here, so a renamed boundary fails here instead of at the first
    ``suggested_column_types()`` call on an old server.
    """
    assert "JSON_FUNCTIONS" in MARIADB_VERSION_BOUNDARIES
