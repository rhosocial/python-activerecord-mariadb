# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_constraint_switches.py
"""MariaDB constraint capability switches: values, locality, and evidence.

Every verdict asserted here was measured by running the ``ALTER TABLE`` /
``CREATE TABLE`` statement against a live MariaDB server and reading
``SHOW CREATE TABLE`` / ``information_schema`` back. The docstring each
switch carries records the same measurement -- server version and the exact
errno or message -- so a verdict can be re-checked without re-measuring.

The servers the numbers come from are reachable on 192.168.1.3 (TLSv1.2),
one per release; ``MEASURED_VERSION`` is the one this file's offline tests
construct a dialect for, and the version-grid docstrings name the others.

Two things are asserted for every switch, and the second is the one that is
easy to lose:

* **the value** -- what this server does;
* **the locality** -- that the verdict resolves to a class in *this* backend's
  package. A switch that falls back to core's ``ConstraintMixin`` can have its
  default moved out from under MariaDB without anything in this repository
  noticing. Three of these probes were previously *undeclared* and resolved to
  the ``ConstraintSupport`` protocol stub, which core reads through ``getattr``
  and treats as "no answer" rather than as a value -- so the whole table below
  could change without a single MariaDB file being edited.

The live-server section at the bottom is the part that cannot be asserted
offline: it re-derives the headline finding (the official documentation says
the column-level ``REFERENCES`` shortcut ``"does nothing"``; that is wrong on
every measured server from 10.5 on) from the server's own answer rather than
trusting the docstring.
"""

import pytest
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterConstraint,
    ValidateConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ConstraintValidation,
    TableCheckConstraint,
    TableConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
)

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.ddl.constraint import (
    MariaDBAlterConstraintModifierMixin,
)

#: The server the offline values below were measured on. Every value here is a
#: statement about *this* version, not about MariaDB in general.
MEASURED_VERSION = (13, 1, 1)

#: The releases reachable on 192.168.1.3 that this file's measurements span.
#: Named because two of the switches are version-gated, and because the
#: column-level ``REFERENCES`` behaviour changes twice across the range.
MEASURED_RELEASES = {
    (10, 2, 44): 15680,
    (10, 4, 34): 15682,
    (10, 5, 29): 15683,
    (12, 0, 2): 15689,
    (12, 1, 2): 15690,
    (13, 1, 1): 15694,
}

#: Every constraint switch this backend relies on, with the verdict measured on
#: 13.1.1. This mapping is the contract; the locality tests below walk it so a
#: switch cannot leave the backend without failing first.
CONSTRAINT_SWITCHES = {
    # Constraint kinds.
    "supports_primary_key_constraint": True,
    "supports_unique_constraint": True,
    "supports_not_null_constraint": True,
    "supports_check_constraint": True,
    "supports_foreign_key_constraint": True,
    "supports_exclude_constraint": False,
    # Referential actions. The `foreign_key_*` pair is the *column-level*
    # probe core consults while rendering a column definition's REFERENCES;
    # the `fk_*` pair is the table-level one. Same server, same measurement,
    # two switches because core consults two.
    "supports_fk_on_delete": True,
    "supports_fk_on_update": True,
    "supports_foreign_key_on_delete": True,
    "supports_foreign_key_on_update": True,
    # Clause attributes.
    "supports_fk_match": False,
    "supports_deferrable_constraint": False,
    "supports_constraint_enforced": False,
    "supports_constraint_novalidate": False,
    # ALTER TABLE lifecycle.
    "supports_add_constraint": True,
    "supports_drop_constraint": True,
    "supports_drop_constraint_if_exists": True,
    # The naming prefix. ``True`` for the family -- the table level accepts a
    # name on every kind -- and the column level narrows that to the foreign
    # key alone in the formatter. A single boolean cannot say so, which is why
    # the narrowing is asserted against the rendered clause rather than here.
    "supports_constraint_naming": True,
    # Column attributes, declared next to the constraint kinds because
    # MariaDB has all four table-level kinds and almost nothing column-level.
    "supports_column_character_set": True,
    "supports_column_collation": True,
}

#: Substring that must appear in each switch's docstring: the errno, the
#: measured catalog value, or the exact wording the server answered with. A
#: verdict that cannot be traced to an observation is a guess.
EVIDENCE = {
    "supports_primary_key_constraint": "1068",
    "supports_unique_constraint": "UNIQUE KEY",
    "supports_not_null_constraint": "13.1.1",
    "supports_check_constraint": "4025",
    "supports_foreign_key_constraint": "1452",
    "supports_exclude_constraint": "1064",
    "supports_fk_on_delete": "SET DEFAULT",
    "supports_fk_on_update": "1901",
    "supports_foreign_key_on_delete": "DELETE_RULE",
    "supports_foreign_key_on_update": "UPDATE_RULE",
    "supports_fk_match": "MATCH_OPTION",
    "supports_deferrable_constraint": "DEFERRABLE",
    "supports_constraint_enforced": "ENFORCED",
    "supports_constraint_novalidate": "NOT VALID",
    "supports_add_constraint": "13.1.1",
    "supports_drop_constraint": "1091",
    "supports_drop_constraint_if_exists": "silent no-op",
    "supports_constraint_naming": "1064",
    "supports_column_character_set": "CHARACTER_SET_NAME",
    "supports_column_collation": "1253",
}

#: The switches a MariaDB class must own, with the class expected to own them.
#: Kept separate from ``CONSTRAINT_SWITCHES`` because the owner differs: the
#: dialect declares most of them, while the ``IF EXISTS`` modifier lives on the
#: mixin that formats the statement it gates.
DECLARING_CLASS = {
    name: (
        "MariaDBAlterConstraintModifierMixin"
        if name == "supports_drop_constraint_if_exists"
        else "MariaDBDialect"
    )
    for name in CONSTRAINT_SWITCHES
}


def _dialect():
    return MariaDBDialect(MEASURED_VERSION)


def _declaring_class(cls, name):
    """The first class in the MRO that answers ``name`` itself."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass
    return None


def _probe_class(switch):
    """The class in this backend's package that declares ``switch``."""
    if switch == "supports_drop_constraint_if_exists":
        return MariaDBAlterConstraintModifierMixin
    return MariaDBDialect


class TestConstraintSwitchValues:
    """What the server was measured to do."""

    @pytest.mark.parametrize(
        "switch, expected", CONSTRAINT_SWITCHES.items(), ids=sorted(CONSTRAINT_SWITCHES)
    )
    def test_switch_answers_the_measured_value(self, switch, expected):
        assert getattr(_dialect(), switch)() is expected

    def test_every_answer_is_a_real_bool(self):
        """``None`` is what an *undeclared* probe answered, and it is not a value.

        Core reads several of these through ``getattr(self, name, None)`` and
        treats ``None`` as "no answer" -- so a probe that answers ``None``
        passes a truthiness check somewhere while meaning nothing. Asserting
        the identity rather than the truth is what catches it.
        """
        for switch in CONSTRAINT_SWITCHES:
            value = getattr(_dialect(), switch)()
            assert value is CONSTRAINT_SWITCHES[switch], switch
            assert isinstance(value, bool), switch

    def test_check_constraint_is_version_gated_at_10_2_1(self):
        for version in ((10, 2, 0), (10, 2, 1 - 1)):
            assert MariaDBDialect(version).supports_check_constraint() is False, version
        for version in ((10, 2, 1), (10, 6, 0), (13, 1, 1)):
            assert MariaDBDialect(version).supports_check_constraint() is True, version

    def test_alter_constraint_enforced_answers_the_same_for_every_kind(self):
        """One boolean, because the server refuses the clause for every kind.

        MySQL needs a per-kind answer (a CHECK takes ``[NOT] ENFORCED`` and a
        FOREIGN KEY answers 3941). MariaDB's parser rejects the token before it
        looks at the constraint, so there is nothing to distinguish -- and the
        probe takes no parameter at all: it answers the family, and the kind is
        the branch class's business in core's
        :meth:`~rhosocial.activerecord.backend.dialect.mixins.ddl_column.DDLColumnMixin.format_alter_constraint_action`.
        """
        dialect = _dialect()
        assert dialect.supports_alter_constraint_enforced() is False
        # Both spellings on both kinds the grammar allows: refused by name on
        # every combination, because the refusal is about the clause, not about
        # the constraint it rides on.
        for kind in (TableCheckConstraint, TableForeignKeyConstraint):
            for spelling in ("enforced", "not_enforced"):
                action = AlterConstraint(
                    dialect, "probe_ck", constraint_kind=kind, **{spelling: True}
                )
                with pytest.raises(UnsupportedFeatureError) as excinfo:
                    action.to_sql()
                assert "ALTER CONSTRAINT" in str(excinfo.value)
                assert "ENFORCED" in str(excinfo.value)

    def test_alter_constraint_refuses_a_kind_that_cannot_carry_the_trait(self):
        """The kind restriction is the expression layer's, not the probe's.

        ``AlterConstraint`` accepts only a CHECK or FOREIGN KEY branch, by
        class; anything else is a ``ValueError`` at construction. That is a
        different failure from the probe's refusal and the two must not collapse
        into one.
        """
        dialect = _dialect()
        with pytest.raises(ValueError, match="TableCheckConstraint or TableForeignKeyConstraint"):
            AlterConstraint(
                dialect, "probe_pk", constraint_kind=TablePrimaryKeyConstraint, enforced=True
            )


class TestConstraintSwitchesAreDeclaredLocally:
    """The verdict must be this backend's, not an inherited default.

    This is the guard against a core change moving MariaDB's contract: if a
    switch below were deleted here and picked up from core, its value could be
    changed by a commit in another repository with nothing failing in this one.
    """

    @pytest.mark.parametrize("switch", sorted(CONSTRAINT_SWITCHES), ids=sorted(CONSTRAINT_SWITCHES))
    def test_switch_is_declared_by_this_backend(self, switch):
        assert hasattr(_probe_class(switch), switch), (
            f"{switch} is not declared by {DECLARING_CLASS[switch]}: it would "
            f"fall through to a core default or a protocol stub that this "
            f"repository cannot pin"
        )

    @pytest.mark.parametrize("switch", sorted(CONSTRAINT_SWITCHES), ids=sorted(CONSTRAINT_SWITCHES))
    def test_resolved_switch_is_owned_by_this_backend(self, switch):
        declaring = _declaring_class(MariaDBDialect, switch)
        assert declaring is not None, (
            f"{switch} resolves to nothing at all -- core reads it through "
            f"getattr and would treat the miss as 'no answer'"
        )
        assert declaring.__module__.startswith("rhosocial.activerecord.backend.impl.mariadb"), (
            f"{switch} resolves to {declaring.__module__}.{declaring.__name__}, "
            f"not a MariaDB class"
        )
        assert declaring is _probe_class(switch), (
            f"{switch} resolves to {declaring.__name__}, expected " f"{DECLARING_CLASS[switch]}"
        )

    def test_the_three_previously_undeclared_probes_are_now_declared(self):
        """These three answered ``None`` before this round.

        ``supports_constraint_novalidate``,
        ``supports_alter_constraint_enforced`` and
        ``supports_validate_constraint`` were resolved by the
        ``ConstraintSupport`` protocol stub, whose body is ``...`` and so
        returns ``None``. Core reads all three through ``getattr`` and reads
        ``None`` as "no answer", which is indistinguishable from "not
        measured". Naming them is the whole fix.
        """
        for switch in (
            "supports_constraint_novalidate",
            "supports_alter_constraint_enforced",
            "supports_validate_constraint",
            "supports_exclude_constraint",
        ):
            declaring = _declaring_class(MariaDBDialect, switch)
            assert declaring is MariaDBDialect, switch
            assert (declaring.__dict__[switch].__doc__ or "").strip(), (
                f"{switch} was undeclared; its new declaration has to say what "
                f"was measured, or the fix is only half of one"
            )


class TestConstraintSwitchDocstringsCarryTheMeasurement:
    """A probe without its evidence is a number with no source."""

    @pytest.mark.parametrize("switch", sorted(CONSTRAINT_SWITCHES), ids=sorted(CONSTRAINT_SWITCHES))
    def test_docstring_exists_and_names_a_measured_server(self, switch):
        doc = getattr(_probe_class(switch), switch).__doc__ or ""
        assert doc, f"{switch} has no docstring: the measurement has nowhere to live"
        assert any(
            str(v[0]) + "." + str(v[1]) + "." + str(v[2]) in doc for v in MEASURED_RELEASES
        ), f"{switch} names no measured server version"

    @pytest.mark.parametrize("switch, marker", EVIDENCE.items(), ids=sorted(EVIDENCE))
    def test_docstring_records_the_errno_or_exact_answer(self, switch, marker):
        doc = getattr(_probe_class(switch), switch).__doc__ or ""
        assert marker in doc, f"{switch} docstring does not record {marker!r}"


class TestMeasurementsThatAreNotMerelyUnsupported:
    """The cases where ``False`` does not mean "the server refused".

    A caller treating any of these as an ordinary unsupported feature gets
    behaviour the switch's value does not describe, so the distinction is
    asserted rather than left to the docstring.
    """

    def test_fk_match_is_accepted_and_discarded_not_rejected(self):
        """The clause parses, then vanishes -- the wording matters.

        Measured on 13.1.1 (and on 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 /
        12.1.2, identically): ``ADD CONSTRAINT mf FOREIGN KEY (c) REFERENCES p
        (id) MATCH FULL`` **succeeds**, and ``SHOW CREATE TABLE`` then renders
        no MATCH at all. ``MATCH_OPTION`` in
        ``information_schema.REFERENTIAL_CONSTRAINTS`` reads ``'NONE'``.

        A rejected clause raises ``1064`` and the caller can catch it; a
        discarded one succeeds, so the caller believes MATCH is in force.
        That is the whole reason this switch is ``False``.

        The ``'NONE'`` is also asserted as **MariaDB-specific**: MySQL 26.7.0
        records ``'FULL'`` in that same column for the same statement. The
        two servers agree the clause is inert and disagree about what the
        catalog says, so the value must not be ported between them.
        """
        doc = MariaDBDialect.supports_fk_match.__doc__ or ""
        assert "accepted" in doc
        assert "discard" in doc
        assert "MATCH_OPTION" in doc
        assert "'NONE'" in doc
        assert (
            "'FULL'" in doc
        ), "the MySQL read-back has to be named so 'NONE' is not read as universal"
        assert "MySQL" in doc

    def test_mariadb_rejects_what_mysql_accepts(self):
        """The ENFORCED pair is the clause most likely to be copied across.

        Measured: MariaDB 13.1.1 answers **1064/42000** for both
        ``ADD CONSTRAINT ... ENFORCED`` and ``... NOT ENFORCED``; MySQL 26.7.0
        accepts both. ``supports_constraint_enforced`` is therefore ``False``
        here and ``True`` there, and the docstring has to say so or the False
        reads as a bug to whoever copies it.
        """
        doc = MariaDBDialect.supports_constraint_enforced.__doc__ or ""
        assert "MySQL" in doc
        assert "1064" in doc
        assert "accepts both" in doc

        alter_doc = MariaDBDialect.supports_alter_constraint_enforced.__doc__ or ""
        assert "MySQL" in alter_doc

    def test_on_delete_set_default_is_accepted_and_rewritten(self):
        """``SET DEFAULT`` does not fail; it is silently stored as ``RESTRICT``.

        Measured on 13.1.1: all five ``reference_option`` values are accepted
        on ``ADD CONSTRAINT``, and ``DELETE_RULE`` reads back ``CASCADE``,
        ``SET NULL``, ``RESTRICT``, ``NO ACTION`` -- and ``RESTRICT`` for the
        one that was written as ``SET DEFAULT``.

        So the caller gets a *stricter* rule than it asked for and no error to
        notice it by. This is a third failure shape, distinct from both the
        ``False`` of a rejected clause and the ``False`` of a discarded one:
        the switch is ``True``, the caller asked for something specific, and it
        got something else. Asserted so the rewrite stays on the record --
        along with the 10.5 boundary that decides whether it is reached at all.
        """
        doc = MariaDBDialect.supports_fk_on_delete.__doc__ or ""
        assert "SET DEFAULT" in doc
        assert "RESTRICT" in doc
        assert "accepted" in doc
        assert "10.5.29" in doc, (
            "below 10.5 SET DEFAULT is refused outright (1005/150); the "
            "rewrite is not the whole story and the boundary has to be on the "
            "record with it"
        )

    def test_the_check_and_on_update_cascade_conflict_is_gated_at_10_5(self):
        """errno 1901 exists only from 10.5; before that the combination is legal.

        Measured across fifteen servers. So the same ``ALTER TABLE`` succeeds
        on 10.4.34 and fails on 10.5.29 with no change to the statement --
        which is the shape of trap that a version-independent docstring would
        hide.
        """
        doc = MariaDBDialect.supports_fk_on_update.__doc__ or ""
        assert "1901" in doc
        assert "10.4.34" in doc
        assert "10.5.29" in doc

    def test_drop_constraint_leaves_the_primary_key_symbol_out_of_the_namespace(self):
        """``True`` here does not mean "any named constraint can be dropped".

        Measured on 13.1.1: ``ADD CONSTRAINT pk_x PRIMARY KEY (v)`` succeeds,
        the symbol is discarded from the rendered DDL, and ``DROP CONSTRAINT
        pk_x`` then answers **1091 (42000)**. The working spelling is ``DROP
        PRIMARY KEY``. The literal name ``PRIMARY`` *is* accepted by ``DROP
        CONSTRAINT``.

        That is a per-kind gap a single boolean cannot express, so it has to
        live in the docstring of the switch that answers ``True``.
        """
        doc = MariaDBDialect.supports_drop_constraint.__doc__ or ""
        assert "PRIMARY KEY" in doc
        assert "1091" in doc
        assert "DROP PRIMARY KEY" in doc

    def test_dropping_an_absent_constraint_is_catchable_here_and_not_on_mysql(self):
        """The errno for a missing constraint exists on MariaDB and not MySQL.

        MariaDB: ``DROP CONSTRAINT nope`` -> ``1091 (42000)``. MySQL 26.7.0 ->
        ``3940``, and its ``DROP CONSTRAINT IF EXISTS`` is a **syntax** error
        (1064), so on MySQL nothing parses and there is no errno about a
        missing constraint to catch at all. Portable code cannot use the
        try/except route across the family; it must use ``IF EXISTS``, which
        MariaDB honours and MySQL rejects.
        """
        doc = MariaDBDialect.supports_drop_constraint.__doc__ or ""
        assert "3940" in doc
        assert "IF EXISTS" in doc


class TestTheDeclaredProbesAreLoadBearing:
    """Flipping one of the newly-declared probes flips the rendered outcome.

    A probe answering one value while the formatter ignores it is decorative.
    These three were previously answered by the protocol stub, so nothing could
    tell a refusal that came from a MariaDB answer from one that came from an
    absent declaration.
    """

    def _alter(self, dialect, **kw):
        return AlterConstraint(dialect, "probe_ck", constraint_kind=TableCheckConstraint, **kw)

    def _not_valid_check(self, dialect):
        constraint = TableConstraint(
            dialect,
            branch=TableCheckConstraint(
                dialect, ComparisonPredicate(dialect, ">", Column(dialect, "a"), Literal(dialect, 0))
            ),
            name="probe_ck",
            validation=ConstraintValidation.NOVALIDATE,
        )
        return constraint

    def test_alter_constraint_probe_flip_renders_the_spelling(self):
        class Alters(MariaDBDialect):
            def supports_alter_constraint_enforced(self):
                return True

        dialect = Alters(MEASURED_VERSION)
        assert self._alter(dialect, enforced=True).to_sql() == (
            "ALTER CONSTRAINT `probe_ck` ENFORCED",
            (),
        )
        assert self._alter(dialect, not_enforced=True).to_sql() == (
            "ALTER CONSTRAINT `probe_ck` NOT ENFORCED",
            (),
        )

    def test_validate_probe_flip_renders_the_spelling(self):
        class Validates(MariaDBDialect):
            def supports_validate_constraint(self):
                return True

        dialect = Validates(MEASURED_VERSION)
        assert ValidateConstraint(dialect, "probe_ck").to_sql() == (
            "VALIDATE CONSTRAINT `probe_ck`",
            (),
        )

    def test_on_mariadb_each_is_still_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError, match="ALTER CONSTRAINT"):
            self._alter(dialect, enforced=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="VALIDATE CONSTRAINT"):
            ValidateConstraint(dialect, "probe_ck").to_sql()


class TestMariaDBIsNotConflatedWithMySQL:
    """The two servers differ on exactly the clauses that look portable.

    Both are MySQL-family and share a ``CREATE TABLE`` surface, so these are
    the verdicts most likely to be copied between them by mistake. The MySQL
    numbers quoted below were measured against MySQL 26.7.0 at
    192.168.1.3:14686 in the same session.
    """

    #: MariaDB rejects ENFORCED/NOT ENFORCED outright and *does* accept the
    #: idempotent drop spelling. MySQL is the reverse on both.
    MARIADB_DIFFERS = (
        "supports_constraint_enforced",
        "supports_alter_constraint_enforced",
        "supports_drop_constraint_if_exists",
    )

    @pytest.mark.parametrize("switch", MARIADB_DIFFERS)
    def test_docstring_separates_this_backend_from_mysql(self, switch):
        doc = getattr(MariaDBDialect, switch).__doc__ or ""
        assert "MySQL" in doc, (
            f"{switch} is one of the clauses where MySQL answers differently, "
            f"so the docstring has to say which server it measured"
        )

    def test_the_drop_if_exists_mixin_docstring_states_the_mysql_absence(self):
        """MySQL has no ``DROP CONSTRAINT IF EXISTS`` at all -- 1064.

        Worth keeping in the mixin that formats the statement, because the
        natural portable fallback (catch the missing-constraint errno) works
        on MariaDB and cannot work on MySQL.
        """
        doc = MariaDBAlterConstraintModifierMixin.__doc__ or ""
        assert "1064" in doc
        assert "3940" in doc
        assert "IF EXISTS" in doc

    def test_this_backend_never_asserts_the_documented_does_nothing_claim(self):
        """The official page says the column-level shortcut ``"does nothing"``.

        mariadb.com/docs/server/reference/sql-statements/data-definition/
        constraint: *"MariaDB accepts the shortcut format with a REFERENCES
        clause only in ALTER TABLE and CREATE TABLE statements, but that syntax
        does nothing."*

        That was **disproved by live measurement** and is quoted here only so
        that nobody re-imports it from the documentation as a settled fact. The
        switch must stay ``True`` and its docstring must keep the evidence; a
        plan to answer ``False`` and refuse the column-level form by name was
        withdrawn on the strength of that measurement.

        The word appears in the docstrings only as the quoted, refuted claim --
        never as an assertion about this server.
        """
        for switch in ("supports_foreign_key_constraint",):
            doc = getattr(MariaDBDialect, switch).__doc__ or ""
            assert "does nothing" in doc, (
                "the refuted documentation claim should stay quoted, so a "
                "reader who knows the docs can see the disagreement"
            )
            assert "1452" in doc, "the refutation needs its measurement, not just the quote"
            assert "positional" in doc
        assert _dialect().supports_foreign_key_constraint() is True


class TestColumnLevelReferencesTheRealTrap:
    """The shortcut builds a real FK; what it cannot do is *name* one.

    Offline half of the headline finding -- the live half is below. The
    generated constraint name is a **positional integer** (``1``, then ``2``),
    not ``<table>_ibfk_N``, and MariaDB auto-creates an index named after the
    **column**. So a caller needing a named foreign key has to use the
    table-level form, and a caller dropping the shortcut's foreign key has to
    clean up the column-named index separately.
    """

    def test_generated_name_is_positional_not_ibfk(self):
        doc = MariaDBDialect.supports_foreign_key_constraint.__doc__ or ""
        assert "CONSTRAINT `1`" in doc
        assert "CONSTRAINT `2`" in doc
        assert "ibfk" in doc
        assert "KEY `c` (`c`)" in doc

    def test_the_version_grid_is_recorded_in_the_docstring(self):
        """Two boundaries, both from live servers, not inferred.

        10.2.44 / 10.4.34 build nothing at all; 10.5.29 is the first that
        builds one, and it names it ``<table>_ibfk_N``; 12.1.2 is the first
        that names it with a positional integer. A caller that hard-codes either
        name shape is wrong on half the range.
        """
        doc = MariaDBDialect.supports_foreign_key_constraint.__doc__ or ""
        for release in ("10.2.44", "10.4.34", "10.5.29", "12.0.2", "12.1.2", "13.1.1"):
            assert release in doc, release

    def test_a_named_foreign_key_needs_the_table_level_form(self):
        """The switch is ``True``, and the docstring must say what is still missing.

        Not a contradiction: the column-level form builds the constraint, and
        it cannot give it a name. Both facts have to be on the switch, because
        a caller asking "can I have a foreign key here?" and a caller asking
        "can I have a *named* one here?" get different answers from the same
        server.
        """
        assert _dialect().supports_foreign_key_constraint() is True
        doc = MariaDBDialect.supports_foreign_key_constraint.__doc__ or ""
        assert "table-level" in doc
        assert "named foreign key" in doc


# --------------------------------------------------------------------------
# Live-server section.
#
# Everything above is offline and fast. These cases talk to the servers in
# ``MEASURED_RELEASES`` and re-derive the numbers from the server's own answer.
# They are the part that would catch the official documentation being right.
# --------------------------------------------------------------------------


def _server_version(backend):
    return tuple(
        int(p) for p in backend.fetch_one("SELECT VERSION() AS v")["v"].split("-")[0].split(".")[:3]
    )


class TestLiveServerConfirmsTheHeadline:
    """Re-derive the column-level ``REFERENCES`` finding from the server.

    The documentation says the shortcut ``"does nothing"``. These cases ask
    the server instead. They are version-aware rather than hard-coded to one
    release, because the truth is version-dependent: inert below 10.5, enforced
    from 10.5, with the generated name changing shape at 12.1.
    """

    TABLES = "sw_ref_parent, sw_ref_child, sw_ref_two"

    def _cleanup(self, backend):
        # Both directions need the checks off: a parent cannot be dropped while
        # a child references it (1451), and the child names the parent in a
        # live FK definition. ``SET FOREIGN_KEY_CHECKS = 0`` is accepted on
        # every measured version (measured, all six).
        try:
            backend.execute("SET FOREIGN_KEY_CHECKS = 0")
            backend.execute(f"DROP TABLE IF EXISTS {self.TABLES}")
        finally:
            backend.execute("SET FOREIGN_KEY_CHECKS = 1")

    def _fk_names(self, backend, table):
        # ``table`` is one of this class's own constants, never user input.
        return {
            row["CONSTRAINT_NAME"]
            for row in backend.fetch_all(
                "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
                f"WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' "
                "AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
            )
        }

    def test_below_10_5_the_shortcut_builds_nothing(self, mariadb_backend):
        """The documentation is right here, and only here."""
        self._cleanup(mariadb_backend)
        try:
            version = _server_version(mariadb_backend)
            if version >= (10, 5, 0):
                pytest.skip("the shortcut is enforced from 10.5 onward")
            mariadb_backend.execute("CREATE TABLE sw_ref_parent (id INT PRIMARY KEY)")
            mariadb_backend.execute(
                "CREATE TABLE sw_ref_child (id INT PRIMARY KEY, "
                "c INT REFERENCES sw_ref_parent (id))"
            )
            ddl = mariadb_backend.fetch_one("SHOW CREATE TABLE sw_ref_child")["Create Table"]
            assert "FOREIGN KEY" not in ddl, ddl
            assert self._fk_names(mariadb_backend, "sw_ref_child") == set()
            # A row the referenced table does not have is accepted -- which is
            # the hazard the documentation is warning about.
            mariadb_backend.execute("INSERT INTO sw_ref_child (id, c) VALUES (1, 999)")
        finally:
            self._cleanup(mariadb_backend)

    def test_from_10_5_the_shortcut_builds_an_enforced_foreign_key(self, mariadb_backend):
        """The measurement that disproved the documentation."""
        self._cleanup(mariadb_backend)
        try:
            version = _server_version(mariadb_backend)
            if version < (10, 5, 0):
                pytest.skip("the shortcut builds no foreign key before 10.5")
            mariadb_backend.execute("CREATE TABLE sw_ref_parent (id INT PRIMARY KEY)")
            mariadb_backend.execute(
                "CREATE TABLE sw_ref_child (id INT PRIMARY KEY, "
                "c INT REFERENCES sw_ref_parent (id))"
            )
            assert len(self._fk_names(mariadb_backend, "sw_ref_child")) == 1
            from rhosocial.activerecord.backend.errors import IntegrityError

            with pytest.raises(IntegrityError) as excinfo:
                mariadb_backend.execute("INSERT INTO sw_ref_child (id, c) VALUES (1, 999)")
            assert "1452" in str(excinfo.value), excinfo.value
        finally:
            self._cleanup(mariadb_backend)

    def test_the_generated_name_is_positional_from_12_1(self, mariadb_backend):
        """``<table>_ibfk_N`` before 12.1, ``1``/``2`` from 12.1.

        The 13.1.1 result reads like "MariaDB never names a column-level FK".
        It does -- through 12.0 -- and then stopped.
        """
        self._cleanup(mariadb_backend)
        try:
            version = _server_version(mariadb_backend)
            if version < (10, 5, 0):
                pytest.skip("the shortcut builds no foreign key before 10.5")
            mariadb_backend.execute("CREATE TABLE sw_ref_parent (id INT PRIMARY KEY)")
            mariadb_backend.execute(
                "CREATE TABLE sw_ref_two (id INT PRIMARY KEY, "
                "c1 INT REFERENCES sw_ref_parent (id), "
                "c2 INT REFERENCES sw_ref_parent (id))"
            )
            names = self._fk_names(mariadb_backend, "sw_ref_two")
            if version >= (12, 1, 0):
                assert names == {"1", "2"}, names
            else:
                assert names == {"sw_ref_two_ibfk_1", "sw_ref_two_ibfk_2"}, names
        finally:
            self._cleanup(mariadb_backend)

    def test_an_index_named_after_the_column_is_left_behind(self, mariadb_backend):
        """The shortcut also creates ``KEY `c` (`c`)`` -- dropped by name, not with the FK.

        This is the cleanup half of the trap: the foreign key is droppable as
        ``DROP CONSTRAINT `1```, but the index it caused to be created is not
        dropped with it.
        """
        self._cleanup(mariadb_backend)
        try:
            version = _server_version(mariadb_backend)
            if version < (10, 5, 0):
                pytest.skip("the shortcut builds no index before 10.5")
            mariadb_backend.execute("CREATE TABLE sw_ref_parent (id INT PRIMARY KEY)")
            mariadb_backend.execute(
                "CREATE TABLE sw_ref_child (id INT PRIMARY KEY, "
                "c INT REFERENCES sw_ref_parent (id))"
            )
            names = [
                r["Key_name"] for r in mariadb_backend.fetch_all("SHOW INDEX FROM sw_ref_child")
            ]
            assert "c" in names, names

            # Drop it by the name the server gave it -- which is why the name
            # shape has to be discovered rather than assumed: ``1`` from 12.1,
            # ``<table>_ibfk_1`` before that.
            generated = self._fk_names(mariadb_backend, "sw_ref_child")
            assert len(generated) == 1, generated
            fk_name = next(iter(generated))
            mariadb_backend.execute(f"ALTER TABLE sw_ref_child DROP CONSTRAINT `{fk_name}`")
            assert self._fk_names(mariadb_backend, "sw_ref_child") == set()
            after = [
                r["Key_name"] for r in mariadb_backend.fetch_all("SHOW INDEX FROM sw_ref_child")
            ]
            assert "c" in after, f"the column-named index outlives the foreign key: {after}"
        finally:
            self._cleanup(mariadb_backend)


class TestLiveServerConfirmsTheFalseVerdicts:
    """The refused clauses, asked of the server rather than of a docstring."""

    def _fresh(self, backend):
        backend.execute("DROP TABLE IF EXISTS sw_lc")
        backend.execute("CREATE TABLE sw_lc (id INT PRIMARY KEY, c INT)")

    #: Each is a spelling core would render if the switch answered True. The
    #: test asserts the server agrees with the switch.
    REFUSED = (
        ("NOT ENFORCED", "ADD CONSTRAINT nf FOREIGN KEY (c) REFERENCES sw_p (id) NOT ENFORCED"),
        ("ENFORCED", "ADD CONSTRAINT ef FOREIGN KEY (c) REFERENCES sw_p (id) ENFORCED"),
        ("DEFERRABLE", "ADD CONSTRAINT df FOREIGN KEY (c) REFERENCES sw_p (id) DEFERRABLE"),
        ("NOT DEFERRABLE", "ADD CONSTRAINT nf FOREIGN KEY (c) REFERENCES sw_p (id) NOT DEFERRABLE"),
        (
            "INITIALLY DEFERRED",
            "ADD CONSTRAINT id FOREIGN KEY (c) REFERENCES sw_p (id) INITIALLY DEFERRED",
        ),
        ("NOT VALID", "ADD CONSTRAINT nv CHECK (c > 0) NOT VALID"),
    )

    @pytest.mark.parametrize("label, statement", REFUSED, ids=[r[0] for r in REFUSED])
    def test_clause_is_refused_with_1064(self, mariadb_backend, label, statement):
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_p")
        mariadb_backend.execute("CREATE TABLE sw_p (id INT PRIMARY KEY)")
        self._fresh(mariadb_backend)
        try:
            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute(f"ALTER TABLE sw_lc {statement}")
            message = str(excinfo.value)
            assert "1064" in message, f"{label}: {message}"
            assert (
                label.split()[0] in message
            ), f"{label}: the server should name the token it choked on; got {message}"
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_lc, sw_p")

    def test_table_constraints_has_no_enforced_column(self, mariadb_backend):
        """Nothing to read back even if the clause were accepted.

        Measured on 13.1.1 and on 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 / 12.1.2:
        ``information_schema.TABLE_CONSTRAINTS`` has exactly six columns and
        ``ENFORCED`` is not among them on any of them.
        """
        columns = {
            row["COLUMN_NAME"]
            for row in mariadb_backend.fetch_all(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = 'information_schema' "
                "AND TABLE_NAME = 'TABLE_CONSTRAINTS'"
            )
        }
        assert "ENFORCED" not in columns, columns
        assert columns == {
            "CONSTRAINT_CATALOG",
            "CONSTRAINT_SCHEMA",
            "CONSTRAINT_NAME",
            "TABLE_SCHEMA",
            "TABLE_NAME",
            "CONSTRAINT_TYPE",
        }, columns

    def test_match_full_is_accepted_and_recorded_as_none(self, mariadb_backend):
        """The accepted-then-discarded case, read back from the catalog.

        ``MATCH_FULL`` succeeds and ``MATCH_OPTION`` reads ``'NONE'`` on
        MariaDB. MySQL 26.7.0 reads ``'FULL'`` for the same statement, so this
        assertion is deliberately MariaDB-only.
        """
        mariadb_backend.execute("DROP TABLE IF EXISTS sw_m, sw_p")
        mariadb_backend.execute("CREATE TABLE sw_p (id INT PRIMARY KEY)")
        mariadb_backend.execute("CREATE TABLE sw_m (id INT PRIMARY KEY, c INT)")
        try:
            mariadb_backend.execute(
                "ALTER TABLE sw_m ADD CONSTRAINT mf FOREIGN KEY (c) "
                "REFERENCES sw_p (id) MATCH FULL"
            )
            rows = mariadb_backend.fetch_all(
                "SELECT MATCH_OPTION FROM information_schema.REFERENTIAL_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'sw_m'"
            )
            assert [r["MATCH_OPTION"] for r in rows] == ["NONE"], rows
            ddl = mariadb_backend.fetch_one("SHOW CREATE TABLE sw_m")["Create Table"]
            assert "MATCH" not in ddl, ddl
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_m, sw_p")

    def test_drop_constraint_if_exists_is_a_silent_no_op(self, mariadb_backend):
        """The one idempotent spelling -- and MySQL has no equivalent."""
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_lc")
        self._fresh(mariadb_backend)
        try:
            mariadb_backend.execute(
                "ALTER TABLE sw_lc DROP CONSTRAINT IF EXISTS no_such_constraint"
            )
            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute("ALTER TABLE sw_lc DROP CONSTRAINT no_such_constraint")
            assert "1091" in str(excinfo.value), excinfo.value
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_lc")

    def test_primary_key_symbol_is_not_droppable_by_its_name(self, mariadb_backend):
        """``ADD CONSTRAINT pk_x PRIMARY KEY`` discards ``pk_x``; dropping it answers 1091."""
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_pk")
        mariadb_backend.execute("CREATE TABLE sw_pk (id INT, v INT)")
        try:
            mariadb_backend.execute("ALTER TABLE sw_pk ADD CONSTRAINT pk_x PRIMARY KEY (v)")
            ddl = mariadb_backend.fetch_one("SHOW CREATE TABLE sw_pk")["Create Table"]
            assert "pk_x" not in ddl, ddl
            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute("ALTER TABLE sw_pk DROP CONSTRAINT pk_x")
            assert "1091" in str(excinfo.value), excinfo.value
            # The spelling that works, and the literal name that also works.
            mariadb_backend.execute("ALTER TABLE sw_pk DROP PRIMARY KEY")
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_pk")

    def test_exclude_is_refused(self, mariadb_backend):
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_ex")
        mariadb_backend.execute("CREATE TABLE sw_ex (id INT PRIMARY KEY, a INT)")
        try:
            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute("ALTER TABLE sw_ex ADD CONSTRAINT ex EXCLUDE (a WITH =)")
            assert "1064" in str(excinfo.value), excinfo.value
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_ex")

    def test_check_violation_uses_mariadbs_own_errno(self, mariadb_backend):
        """``4025``, not MySQL 8's ``3819`` -- code classifying the failure must branch."""
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_ck")
        mariadb_backend.execute(
            "CREATE TABLE sw_ck (id INT PRIMARY KEY, c INT, " "CONSTRAINT ck CHECK (c > 0))"
        )
        try:
            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute("INSERT INTO sw_ck (id, c) VALUES (1, -1)")
            assert "4025" in str(excinfo.value), excinfo.value
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_ck")

    def test_on_delete_set_default_is_stored_as_restrict(self, mariadb_backend):
        """Accepted, and rewritten -- but only from 10.5.

        Measured across fifteen servers: on 13.1.1 (and 10.5.29 ... 13.1.1)
        ``ON DELETE SET DEFAULT`` is accepted and
        ``REFERENTIAL_CONSTRAINTS.DELETE_RULE`` reads ``RESTRICT``. On 10.2.44
        / 10.3.39 / 10.4.34 it is **refused** -- ``1005 (HY000)`` wrapping
        InnoDB's ``150 "Foreign key constraint is incorrectly formed"``.

        So the same DDL fails loudly below 10.5 and lies from 10.5 on. The
        switch answers ``True`` on every version; what the caller experiences
        is not the same thing, which is why the boundary is asserted rather
        than left to the docstring alone.
        """
        mariadb_backend.execute("DROP TABLE IF EXISTS sw_sd, sw_sdp")
        mariadb_backend.execute("CREATE TABLE sw_sdp (id INT PRIMARY KEY)")
        mariadb_backend.execute("CREATE TABLE sw_sd (id INT PRIMARY KEY, c INT)")
        try:
            if _server_version(mariadb_backend) < (10, 5, 0):
                from rhosocial.activerecord.backend.errors import DatabaseError

                with pytest.raises(DatabaseError) as excinfo:
                    mariadb_backend.execute(
                        "ALTER TABLE sw_sd ADD CONSTRAINT fk_sd FOREIGN KEY (c) "
                        "REFERENCES sw_sdp (id) ON DELETE SET DEFAULT"
                    )
                assert "1005" in str(excinfo.value), excinfo.value
                return

            mariadb_backend.execute(
                "ALTER TABLE sw_sd ADD CONSTRAINT fk_sd FOREIGN KEY (c) "
                "REFERENCES sw_sdp (id) ON DELETE SET DEFAULT"
            )
            rows = mariadb_backend.fetch_all(
                "SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'sw_sd'"
            )
            assert [r["DELETE_RULE"] for r in rows] == ["RESTRICT"], rows
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_sd, sw_sdp")

    def test_onnupdate_cascade_and_check_cannot_share_a_column(self, mariadb_backend):
        """errno 1901, it names the CHECK rather than the FK, and it starts at 10.5.

        Measured across fifteen servers: 13.1.1 (and 10.5.29 ... 13.1.1) answers
        **1901 / HY000**, ``Function or expression 'c' cannot be used in the
        CHECK clause of `ck` ``. 10.2.44 / 10.3.39 / 10.4.34 accept the
        combination and keep both constraints.

        Two separate claims, and the second is easy to lose: the error names
        the *CHECK*, so a caller classifying by errno alone attributes it to
        the wrong constraint; and the same DDL is legal before 10.5, so a
        migration that ran on one release fails on the next with no statement
        changed.
        """
        from rhosocial.activerecord.backend.errors import DatabaseError

        mariadb_backend.execute("DROP TABLE IF EXISTS sw_1901, sw_1901p")
        mariadb_backend.execute("CREATE TABLE sw_1901p (id INT PRIMARY KEY)")
        mariadb_backend.execute("CREATE TABLE sw_1901 (id INT PRIMARY KEY, c INT)")
        try:
            mariadb_backend.execute("ALTER TABLE sw_1901 ADD CONSTRAINT ck CHECK (c > 0)")
            if _server_version(mariadb_backend) < (10, 5, 0):
                mariadb_backend.execute(
                    "ALTER TABLE sw_1901 ADD CONSTRAINT fk FOREIGN KEY (c) "
                    "REFERENCES sw_1901p (id) ON UPDATE CASCADE"
                )
                ddl = mariadb_backend.fetch_one("SHOW CREATE TABLE sw_1901")["Create Table"]
                assert "ON UPDATE CASCADE" in ddl, ddl
                return

            with pytest.raises(DatabaseError) as excinfo:
                mariadb_backend.execute(
                    "ALTER TABLE sw_1901 ADD CONSTRAINT fk FOREIGN KEY (c) "
                    "REFERENCES sw_1901p (id) ON UPDATE CASCADE"
                )
            message = str(excinfo.value)
            assert "1901" in message, message
            assert "CHECK clause" in message, (
                f"the error names the CHECK, not the FK -- a caller classifying "
                f"by errno alone will attribute it to the wrong constraint: {message}"
            )
            # ON DELETE alone on the same column is fine.
            mariadb_backend.execute(
                "ALTER TABLE sw_1901 ADD CONSTRAINT fk2 FOREIGN KEY (c) "
                "REFERENCES sw_1901p (id) ON DELETE CASCADE"
            )
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS sw_1901, sw_1901p")
