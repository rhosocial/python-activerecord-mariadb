# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/introspection/test_introspection_data_profile_parser.py
"""Parser-level tests for the MariaDB column data profile, with no server.

The live suite in ``feature/backend`` measures this family against a real
MariaDB, and that is where the arithmetic is proved. What it cannot do is
state the *shape* the columns arrive in, because a hand-written row is not the
same object as a connector row -- and the difference is what made one CI job
red on every matrix row at once: the profile was read out of a mapping whose
keys the parser never sees.

So this file pins the shape directly. It runs the statement the live path
runs, feeds the parser the row shape the connector actually produces, and
asserts the figures land. Three things are checked, and none of them needs a
database:

* the executor hands the parser a dict per row, keyed by ``cursor.description``
  -- the connector returns *tuples* from ``fetchall()``, so an executor that
  returned the connector's rows unchanged would hand the parser tuples, and
  every figure would read back ``None`` rather than raising;
* the keys are lower case, because the dialect quotes the aliases it writes
  and the server echoes the spelling it was given -- not the upper-case names
  ``information_schema`` uses, so a parser reading upper case would find
  nothing and return a list of empty profiles;
* the generic parser in core already reads exactly these keys, which is why
  MariaDB needs no ``parse_column_data_profiles`` override and this test
  asserts none exists.
"""

from types import SimpleNamespace

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.introspection import (
    MariaDBIntrospector,
)
from rhosocial.activerecord.backend.introspection.types import ColumnDataProfile
from rhosocial.activerecord.backend.expression.introspection import (
    ColumnDataProfileQueryStatement,
)

TABLE = "intro_profile_orders"


class _NoServerBackend:
    """The parts of a MariaDB backend an introspector reads, and nothing else."""

    def __init__(self):
        self.config = SimpleNamespace(database="shop")
        self.dialect = MariaDBDialect((12, 3, 0))


class _UnusedExecutor:
    """An executor that fails loudly if a parser-level test asks for SQL."""

    def execute(self, sql, params=()):
        raise AssertionError("a parser-level test must not execute SQL")


class _Executor:
    """The core ``IntrospectorExecutor``, reproduced with no connection.

    ``_get_cursor().description`` yields one tuple per column whose first
    entry is the column name, and ``fetchall()`` yields bare tuples. The
    pairing is done here, exactly as core does it, because that pairing is
    the contract the parser depends on.
    """

    def __init__(self, description, rows):
        self.description = tuple((name,) for name in description)
        self._rows = rows

    def execute(self, sql, params=()):
        columns = [desc[0] for desc in self.description]
        return [dict(zip(columns, row)) for row in self._rows]


def _introspector() -> MariaDBIntrospector:
    return MariaDBIntrospector(_NoServerBackend(), _UnusedExecutor())


def _statement():
    """The statement the live path renders, as a tuple of (sql, params)."""
    dialect = MariaDBDialect((12, 3, 0))
    return ColumnDataProfileQueryStatement(
        dialect, table_name=TABLE, schema="shop",
        columns=("id", "code", "amount", "note"),
    ).to_sql()


def _rows():
    """The four answers of the live table: 100 rows, code a/b/c, note 60% NULL.

    ``min_value``/``max_value`` are text on purpose -- a ``UNION ALL`` resolves
    one result type per column position, and the arm carrying ``amount``'s
    decimal decides the slot's type, so it arrives as ``"1.00"`` rather than a
    number. The figures are exact; only the Python type is the union's.
    """
    return [
        ("id", 0, 100, "1", "100", 100, "aggregate"),
        ("code", 0, 3, "a", "c", 100, "aggregate"),
        ("amount", 0, 100, "1.00", "100.00", 100, "aggregate"),
        ("note", 60, 2, "x", "y", 100, "aggregate"),
    ]


_DESCRIPTION = (
    "column_name", "null_count", "distinct_count",
    "min_value", "max_value", "row_count", "source",
)


class TestRowShape:
    """What the connector gives the parser, and what that means for the keys."""

    def test_the_statement_names_the_slots_it_projects(self):
        """The SQL spells the seven slot names the parser reads.

        One alias per figure, in lower case, because the dialect quotes its
        identifiers and the server echoes the spelling it was given. This is
        the whole reason the row shape is not the information_schema spelling:
        the statement is written here, not read from a catalogue.
        """
        sql, _ = _statement()

        for slot in _DESCRIPTION:
            assert f"AS `{slot}`" in sql

    def test_the_executor_pairs_the_description_with_the_rows(self):
        """A tuple row paired with the description becomes a keyed dict.

        The connector returns tuples; the dict is core's doing. An executor
        that passed the connector's rows through unchanged would hand the
        parser tuples, and every figure would read back ``None`` instead of
        raising -- the failure that is hardest to notice, because it looks
        like a measurement of nothing.
        """
        rows = _Executor(_DESCRIPTION, _rows()).execute(*_statement())

        assert [sorted(row) for row in rows] == [sorted(_DESCRIPTION)] * 4
        assert rows[0]["column_name"] == "id"
        # A figure, not a slot the parser found absent.
        assert rows[3]["null_count"] == 60

    def test_the_connector_row_is_a_tuple_and_not_a_dict(self):
        """What the mariadb connector hands back: bare tuples, not dicts.

        Pinned against the connector's own configuration rather than against
        this file's fixtures, because the pairing above is only needed if the
        connector really does return tuples. A cursor becomes a dict or a named
        tuple source only when it is opened with ``dictionary=True`` or
        ``named_tuple=True``; the defaults are both ``False``, and neither the
        connection parameters the config builds nor the introspector's executor
        opens one that way, so a plain tuple is what arrives.
        """
        from mariadb.base_connection import Configuration

        config = Configuration.from_dict({})

        assert config.named_tuple is False
        assert config.dictionary is False

        # And this file's rows are tuples, like the connector's.
        assert all(isinstance(row, tuple) for row in _rows())


class TestParseColumnDataProfiles:
    """The rows this family projects land as filled profiles, not empty ones."""

    def test_the_profile_of_four_columns_is_read_from_the_rows(self):
        executor = _Executor(_DESCRIPTION, _rows())
        profiles = _introspector().parse_column_data_profiles(
            executor.execute(*_statement()), "shop", TABLE
        )

        assert [profile.column_name for profile in profiles] == [
            "id", "code", "amount", "note"
        ]
        by_name = {profile.column_name: profile for profile in profiles}

        # The exact figures of the live table, read the way the live test
        # asserts them, so the two files cannot drift apart.
        assert by_name["id"].null_fraction == 0.0
        assert by_name["id"].distinct_count == 100
        assert by_name["id"].row_count == 100
        assert by_name["id"].source == "aggregate"
        assert by_name["code"].distinct_count == 3
        assert by_name["note"].null_fraction == 0.6
        assert by_name["note"].distinct_count == 2
        assert by_name["note"].min_value == "x"
        assert by_name["note"].max_value == "y"
        assert by_name["amount"].min_value == "1.00"

    def test_every_slot_is_a_parsed_profile_object(self):
        """The elements are ``ColumnDataProfile`` records, not the raw rows.

        This is the assertion whose absence let a mapping of strings reach a
        caller: iterating a dict built from the profiles yields the *keys*,
        which are bare column names, and ``profile.source`` on one of those
        is an ``AttributeError``. Asserting the element type is what makes
        that impossible to do silently again.
        """
        executor = _Executor(_DESCRIPTION, _rows())
        profiles = _introspector().parse_column_data_profiles(
            executor.execute(*_statement()), "shop", TABLE
        )

        assert all(isinstance(profile, ColumnDataProfile) for profile in profiles)
        # ...and not a dict, not a string, not a tuple.
        assert {type(profile) for profile in profiles} == {ColumnDataProfile}

    def test_a_missing_count_leaves_the_fraction_undone_rather_than_zero(self):
        """A row count of zero has no fraction to divide, so it stays ``None``.

        ``SUM`` over no rows is NULL, so ``null_count`` arrives NULL and the
        fraction is not derived. Answering ``0.0`` would claim the column
        holds no NULLs, which an empty table does not establish.
        """
        rows = [("id", None, 0, None, None, 0, "aggregate")]
        executor = _Executor(_DESCRIPTION, rows)
        profiles = _introspector().parse_column_data_profiles(
            executor.execute(*_statement()), "shop", TABLE
        )

        assert len(profiles) == 1
        assert profiles[0].row_count == 0
        assert profiles[0].null_fraction is None
        assert profiles[0].distinct_count == 0
        assert profiles[0].source == "aggregate"

    def test_no_override_is_needed_because_the_generic_parser_works(self):
        """MariaDB does not override ``parse_column_data_profiles``.

        The generic one in core already reads these keys, so an override here
        would be a second convention for the same thing. If this test fails,
        someone added an override, and the reason for it belongs in this file
        rather than in a branch that never explains itself.
        """
        from rhosocial.activerecord.backend.introspection.base import (
            IntrospectorBase,
        )

        assert "parse_column_data_profiles" not in vars(MariaDBIntrospector)
        assert "parse_column_data_profiles" in vars(IntrospectorBase)
        assert (
            MariaDBIntrospector.parse_column_data_profiles
            is IntrospectorBase.parse_column_data_profiles
        )
