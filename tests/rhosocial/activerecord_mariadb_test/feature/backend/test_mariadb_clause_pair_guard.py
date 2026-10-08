# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_clause_pair_guard.py
"""MariaDB guard: every clause pair this dialect consumes is really consumed.

Core's ``test_clause_pair_guard.py`` renders through ``DummyDialect``, the
reference switchboard that declares every capability ``True``. It certifies the
*encoding* of each pair -- that both parameters exist and the both-set state is
refused -- but it cannot certify that MariaDB's own formatters read them: a
backend formatter that ignores the second parameter passes core's guard while
silently dropping a spelling the caller asked for. This file closes that half.

For every pair below, MariaDB's own formatter (or a capability probe MariaDB
declares) decides the outcome. The four states must be pairwise distinguishable:

====================  =====================================================
neither parameter     neither spelling rendered
parameter A           A's spelling rendered, or refused naming that spelling
parameter B           B's spelling rendered, or refused naming that spelling
both parameters       ``ValueError`` at construction
====================  =====================================================

A refusal is an acceptable outcome only where MariaDB cannot express the
spelling (measured: see ``mixins/sequence.py``, ``mixins/truncate.py``,
``dialect.py``). The refusal must name the requested spelling, so the A state
and the B state can never collapse into one another -- a shared "unsupported"
message for both sides would be exactly the silent-drop failure this guard
exists to catch.

Pairs consumed by core's inherited formatters (CTE materialization, set
operation ALL/DISTINCT, materialized-view WITH DATA, identity options) are
certified by core's guard; MariaDB adds no decision to them and does not repeat
them here. ``AlterConstraint.enforced`` is covered separately below: its
grammar is mandatory and its refusal comes from core's formatter, because
MariaDB declares no ``supports_alter_constraint_enforced``.
"""

import re
from typing import Any, Callable, Dict, NamedTuple, Tuple

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import (
    Function,
    Sequence,
    Table,
    View,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.serialization import (
    deserialize_json,
    serialize_json,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_function import (
    DropFunctionExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
    AlterSequenceExpression,
    CreateSequenceExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    DropViewExpression,
)
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBExchangePartitionExpression,
)

VERSION = (10, 6, 0)


def _dialect() -> MariaDBDialect:
    return MariaDBDialect(VERSION)


def _seq(d):
    return Sequence(d, "probe_seq")


def _table(d, name="probe_t"):
    return Table(d, name)


def _check(d, **kw):
    return TableConstraint(
        d,
        TableConstraintType.CHECK,
        name="probe_ck",
        check_condition=ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b")),
        **kw,
    )


def _fk(d, **kw):
    return TableConstraint(
        d,
        TableConstraintType.FOREIGN_KEY,
        name="probe_fk",
        columns=["a"],
        foreign_key_table=_table(d, "probe_t2"),
        foreign_key_columns=["b"],
        **kw,
    )


class PairCase(NamedTuple):
    """One clause pair MariaDB consumes and the outcome each state must have."""

    case_id: str
    builder: Callable[..., Any]
    a: str
    b: str
    a_kwargs: Dict[str, Any]
    b_kwargs: Dict[str, Any]
    a_spelling: str  # regex: A's spelling in SQL
    b_spelling: str  # regex: B's spelling in SQL
    expect_a: Tuple[str, str]  # ("rendered", regex fragment) | ("refused", name)
    expect_b: Tuple[str, str]


#: ``CYCLE`` inside ``NOCYCLE`` is why the positive patterns carry a
#: negative lookbehind (MariaDB spells the negative form without a space).
PAIR_CASES = (
    PairCase(
        "CreateSequenceExpression.cycle",
        lambda d, **kw: CreateSequenceExpression(d, _seq(d), **kw),
        "cycle",
        "no_cycle",
        {"cycle": True},
        {"no_cycle": True},
        r"(?<!NO)CYCLE\b",
        r"NOCYCLE\b",
        ("rendered", r"(?<!NO)CYCLE\b"),
        ("rendered", r"NOCYCLE\b"),
    ),
    PairCase(
        "CreateSequenceExpression.cache",
        lambda d, **kw: CreateSequenceExpression(d, _seq(d), **kw),
        "cache",
        "no_cache",
        {"cache": 10},
        {"no_cache": True},
        r"CACHE = 10\b",
        r"NOCACHE\b",
        ("rendered", r"CACHE = 10\b"),
        ("rendered", r"NOCACHE\b"),
    ),
    PairCase(
        "CreateSequenceExpression.order",
        lambda d, **kw: CreateSequenceExpression(d, _seq(d), **kw),
        "order",
        "no_order",
        {"order": True},
        {"no_order": True},
        r"(?<!NO )ORDER\b",
        r"NO ORDER\b",
        ("refused", "SEQUENCE ORDER"),
        ("refused", "SEQUENCE NO ORDER"),
    ),
    PairCase(
        "AlterSequenceExpression.cycle",
        lambda d, **kw: AlterSequenceExpression(d, _seq(d), **kw),
        "cycle",
        "no_cycle",
        {"cycle": True},
        {"no_cycle": True},
        r"(?<!NO)CYCLE\b",
        r"NOCYCLE\b",
        ("rendered", r"(?<!NO)CYCLE\b"),
        ("rendered", r"NOCYCLE\b"),
    ),
    PairCase(
        "AlterSequenceExpression.cache",
        lambda d, **kw: AlterSequenceExpression(d, _seq(d), **kw),
        "cache",
        "no_cache",
        {"cache": 10},
        {"no_cache": True},
        r"CACHE = 10\b",
        r"NOCACHE\b",
        ("rendered", r"CACHE = 10\b"),
        ("rendered", r"NOCACHE\b"),
    ),
    PairCase(
        "AlterSequenceExpression.order",
        lambda d, **kw: AlterSequenceExpression(d, _seq(d), **kw),
        "order",
        "no_order",
        {"order": True},
        {"no_order": True},
        r"(?<!NO )ORDER\b",
        r"NO ORDER\b",
        ("refused", "ALTER SEQUENCE ORDER"),
        ("refused", "ALTER SEQUENCE NO ORDER"),
    ),
    PairCase(
        "TruncateExpression.restart_identity",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "restart_identity",
        "continue_identity",
        {"restart_identity": True},
        {"continue_identity": True},
        r"RESTART IDENTITY\b",
        r"CONTINUE IDENTITY\b",
        ("refused", "TRUNCATE RESTART IDENTITY"),
        ("refused", "TRUNCATE CONTINUE IDENTITY"),
    ),
    PairCase(
        "TruncateExpression.cascade",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "cascade",
        "restrict",
        {"cascade": True},
        {"restrict": True},
        r"CASCADE\b",
        r"RESTRICT\b",
        ("refused", "TRUNCATE CASCADE"),
        ("refused", "TRUNCATE RESTRICT"),
    ),
    PairCase(
        "DropViewExpression.cascade",
        lambda d, **kw: DropViewExpression(d, View(d, "probe_v"), **kw),
        "cascade",
        "restrict",
        {"cascade": True},
        {"restrict": True},
        r"CASCADE\b",
        r"RESTRICT\b",
        ("rendered", r"CASCADE\b"),
        ("rendered", r"RESTRICT\b"),
    ),
    PairCase(
        "DropFunctionExpression.cascade",
        lambda d, **kw: DropFunctionExpression(d, Function(d, "probe_fn"), **kw),
        "cascade",
        "restrict",
        {"cascade": True},
        {"restrict": True},
        r"CASCADE\b",
        r"RESTRICT\b",
        ("refused", "DROP FUNCTION CASCADE"),
        ("refused", "DROP FUNCTION RESTRICT"),
    ),
    PairCase(
        "TableConstraint.enforced",
        _check,
        "enforced",
        "not_enforced",
        {"enforced": True},
        {"not_enforced": True},
        r"(?<!NOT )ENFORCED\b",
        r"NOT ENFORCED\b",
        ("refused", "CONSTRAINT ENFORCED"),
        ("refused", "CONSTRAINT NOT ENFORCED"),
    ),
    PairCase(
        "TableConstraint.deferrable",
        _fk,
        "deferrable",
        "not_deferrable",
        {"deferrable": True},
        {"not_deferrable": True},
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
        ("refused", "CONSTRAINT DEFERRABLE"),
        ("refused", "CONSTRAINT NOT DEFERRABLE"),
    ),
    PairCase(
        "TableConstraint.initially_deferred",
        _fk,
        "initially_deferred",
        "initially_immediate",
        {"initially_deferred": True},
        {"initially_immediate": True},
        r"INITIALLY DEFERRED\b",
        r"INITIALLY IMMEDIATE\b",
        ("refused", "CONSTRAINT INITIALLY DEFERRED"),
        ("refused", "CONSTRAINT INITIALLY IMMEDIATE"),
    ),
    PairCase(
        "BeginTransactionExpression.deferrable",
        lambda d, **kw: BeginTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        {"deferrable": True},
        {"not_deferrable": True},
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
        ("refused", "TRANSACTION DEFERRABLE"),
        ("refused", "TRANSACTION NOT DEFERRABLE"),
    ),
    PairCase(
        "SetTransactionExpression.deferrable",
        lambda d, **kw: SetTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        {"deferrable": True},
        {"not_deferrable": True},
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
        ("refused", "TRANSACTION DEFERRABLE"),
        ("refused", "TRANSACTION NOT DEFERRABLE"),
    ),
    PairCase(
        "MariaDBExchangePartitionExpression.with_validation",
        lambda d, **kw: MariaDBExchangePartitionExpression(
            d, _table(d, "probe_part"), "p0", _table(d, "probe_exch"), **kw
        ),
        "with_validation",
        "without_validation",
        {"with_validation": True},
        {"without_validation": True},
        r"WITH VALIDATION\b",
        r"WITHOUT VALIDATION\b",
        ("refused", "EXCHANGE PARTITION WITH VALIDATION"),
        ("refused", "EXCHANGE PARTITION WITHOUT VALIDATION"),
    ),
)

PAIR_IDS = [case.case_id for case in PAIR_CASES]


def _outcome(case: PairCase, dialect: Any, kwargs: Dict[str, Any]) -> Tuple[str, str]:
    """One state's outcome: what was rendered, refused, or raised at build time."""
    try:
        expr = case.builder(dialect, **kwargs)
    except ValueError as exc:
        return "construction-error", str(exc)
    try:
        sql, _params = expr.to_sql()
    except UnsupportedFeatureError as exc:
        return "refused", str(exc)
    return "rendered", sql


def _state_failure(case: PairCase, dialect: Any) -> str:
    """Return the first reason ``case`` is not pairwise distinguishable, or ``""``."""
    states = {
        "neither": _outcome(case, dialect, {}),
        "a": _outcome(case, dialect, case.a_kwargs),
        "b": _outcome(case, dialect, case.b_kwargs),
        "both": _outcome(case, dialect, {**case.a_kwargs, **case.b_kwargs}),
    }

    kind, detail = states["neither"]
    if kind != "rendered":
        return f"neither set must render the plain statement; got {kind}: {detail!r}"
    if re.search(case.a_spelling, detail):
        return f"neither set still spells {case.a!r}: {detail!r}"
    if re.search(case.b_spelling, detail):
        return f"neither set still spells {case.b!r}: {detail!r}"

    for side, expected in (("a", case.expect_a), ("b", case.expect_b)):
        kind, detail = states[side]
        want_kind, fragment = expected
        if kind != want_kind:
            return (
                f"setting {case.a if side == 'a' else case.b!r} must be "
                f"{want_kind}; got {kind}: {detail!r}"
            )
        if kind == "rendered":
            if not re.search(fragment, detail):
                return (
                    f"setting {case.a if side == 'a' else case.b!r} must spell "
                    f"{fragment!r}; got {detail!r}"
                )
            other = case.b_spelling if side == "a" else case.a_spelling
            if re.search(other, detail):
                return (
                    f"setting {case.a if side == 'a' else case.b!r} also spelled "
                    f"the other side: {detail!r}"
                )
        elif fragment not in detail:
            return (
                f"the refusal for {case.a if side == 'a' else case.b!r} must name "
                f"{fragment!r}; got {detail!r}"
            )

    kind, detail = states["both"]
    if kind != "construction-error":
        return f"setting both parameters must raise ValueError; got {kind}: {detail!r}"
    if f"{case.a} and {case.b} are mutually exclusive" not in detail:
        return f"the both-set refusal must name the pair; got {detail!r}"

    if states["a"] == states["b"]:
        return (
            f"states A and B are indistinguishable: {states['a']!r}. "
            f"The formatter collapses one spelling into the other."
        )
    if states["a"] == states["neither"] or states["b"] == states["neither"]:
        return "a spelling state is indistinguishable from the clause being absent"
    return ""


class TestFourStatesArePairwiseDistinguishable:
    """Every pair MariaDB consumes renders/refuses all four states distinctly."""

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_four_states_are_pairwise_distinguishable(self, case):
        failure = _state_failure(case, _dialect())
        assert failure == "", f"{case.case_id}: {failure}"

    def test_every_case_has_two_distinct_parameters(self):
        for case in PAIR_CASES:
            assert case.a != case.b, case.case_id

    def test_maria_db_declares_neither_enforcement_nor_deferral(self):
        # Measured on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc (all four spellings
        # rejected with errno 1064, sentinels rejected) and by 10.6's grammar,
        # which has no ENFORCED / DEFERRABLE / INITIALLY token. A future
        # declaration changes the outcome and this pin with it.
        dialect = _dialect()
        assert dialect.supports_constraint_enforced() is False
        assert dialect.supports_deferrable_constraint() is False


class TestExchangePartitionValidationBoundary:
    """The two validation spellings parse from MariaDB 11.4; bare from 10.2.

    Measured live (direct connections, TLSv1.2, fresh tables per case and a
    sentinel on every connection): the bare form is accepted from 10.2.44
    through 13.1.1, with a mismatching row failing at runtime with errno 1737
    (so the statement parsed); ``WITH VALIDATION`` and ``WITHOUT VALIDATION``
    are syntax errors (errno 1064) on 10.2.44 / 10.3.39 / 10.4.34 / 10.5.29 /
    10.6.28 / 10.11.19 / 11.0.6 / 11.1.6 / 11.2.6 / 11.3.2 and accepted from
    11.4.13 onward. 11.3.2 is the last version seen rejecting both spellings
    and 11.4.13 the first accepting them, so the boundary is ``11.4``.
    """

    def _expr(self, version, **kw):
        dialect = MariaDBDialect(version)
        return MariaDBExchangePartitionExpression(
            dialect, _table(dialect, "probe_part"), "p0", _table(dialect, "probe_exch"), **kw
        )

    def test_probes_answer_the_measured_boundary(self):
        for version in ((10, 2, 0), (10, 6, 0), (10, 11, 0), (11, 3, 2)):
            dialect = MariaDBDialect(version)
            assert dialect.supports_exchange_partition_with_validation() is False, version
            assert dialect.supports_exchange_partition_without_validation() is False, version
        for version in ((11, 4, 0), (11, 4, 13), (13, 1, 1)):
            dialect = MariaDBDialect(version)
            assert dialect.supports_exchange_partition_with_validation() is True, version
            assert dialect.supports_exchange_partition_without_validation() is True, version

    def test_last_rejecting_version_refuses_both_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            self._expr((11, 3, 2), with_validation=True).to_sql()
        assert "EXCHANGE PARTITION WITH VALIDATION" in str(excinfo.value)
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            self._expr((11, 3, 2), without_validation=True).to_sql()
        assert "EXCHANGE PARTITION WITHOUT VALIDATION" in str(excinfo.value)

    def test_first_accepting_version_renders_each_spelling(self):
        bare, params = self._expr((11, 4, 0)).to_sql()
        assert bare == "ALTER TABLE `probe_part` EXCHANGE PARTITION `p0` WITH TABLE `probe_exch`"
        assert params == ()
        with_validation, _ = self._expr((11, 4, 0), with_validation=True).to_sql()
        assert with_validation.endswith(" WITH VALIDATION")
        without_validation, _ = self._expr((11, 4, 0), without_validation=True).to_sql()
        assert without_validation.endswith(" WITHOUT VALIDATION")

    def test_bare_form_renders_on_the_oldest_measured_version(self):
        sql, _ = self._expr((10, 2, 0)).to_sql()
        assert sql == "ALTER TABLE `probe_part` EXCHANGE PARTITION `p0` WITH TABLE `probe_exch`"

    def test_both_spellings_raise_at_construction_on_every_version(self):
        for version in ((10, 6, 0), (11, 4, 0)):
            with pytest.raises(ValueError, match="mutually exclusive"):
                self._expr(version, with_validation=True, without_validation=True)

    def test_exchange_table_must_be_a_table(self):
        dialect = _dialect()
        with pytest.raises(TypeError, match="exchange_table"):
            MariaDBExchangePartitionExpression(
                dialect, _table(dialect, "probe_part"), "p0", "probe_exch"
            )


class TestTheGuardCanSeeADroppedSpelling:
    """The guard is live: a formatter that ignores the second parameter fails.

    ``CreateSequenceExpression.no_cycle`` is dropped on purpose here, exactly
    the shape the sequence mixin had before this round consumed the pair. If
    the walk could not report that as a dropped spelling, it could not certify
    the defect it was written to catch.
    """

    def test_a_formatter_that_ignores_no_cycle_is_reported(self):
        case = next(c for c in PAIR_CASES if c.case_id == "CreateSequenceExpression.cycle")

        def deaf_builder(d, **kw):
            # Reads only the positive parameter; the negative one is dropped.
            return CreateSequenceExpression(d, _seq(d), cycle=kw.get("cycle", False))

        deaf = case._replace(builder=deaf_builder)
        failure = _state_failure(deaf, _dialect())
        assert failure != "", "the walk did not notice a dropped spelling"
        assert "must be refused" in failure or "must spell" in failure or "indistinguishable" in failure, failure


class TestPairParametersSurviveSerialization:
    """The new pair fields round-trip through the serialization channels.

    ``test_expression_roundtrip_all.py`` builds every class with default
    parameters, so it cannot see a field the serializer drops. These cases set
    the second spelling and assert the decoded object still carries it -- a
    dropped field would render "unspecified" and silently lose the clause.
    """

    @pytest.mark.parametrize(
        "factory, field",
        [
            (lambda d: CreateSequenceExpression(d, _seq(d), no_cycle=True), "no_cycle"),
            (lambda d: CreateSequenceExpression(d, _seq(d), no_cache=True), "no_cache"),
            (lambda d: AlterSequenceExpression(d, _seq(d), no_order=True), "no_order"),
            (lambda d: TruncateExpression(d, _table(d), continue_identity=True), "continue_identity"),
            (lambda d: TruncateExpression(d, _table(d), restrict=True), "restrict"),
            (lambda d: _check(d, not_enforced=True), "not_enforced"),
            (lambda d: _fk(d, deferrable=True), "deferrable"),
            (lambda d: BeginTransactionExpression(d, deferrable=True), "_deferrable"),
            (lambda d: SetTransactionExpression(d, not_deferrable=True), "_not_deferrable"),
            (
                lambda d: MariaDBExchangePartitionExpression(
                    d, _table(d, "probe_part"), "p0", _table(d, "probe_exch"), with_validation=True
                ),
                "with_validation",
            ),
            (
                lambda d: MariaDBExchangePartitionExpression(
                    d, _table(d, "probe_part"), "p0", _table(d, "probe_exch"), without_validation=True
                ),
                "without_validation",
            ),
        ],
        ids=[
            "CreateSequenceExpression.no_cycle",
            "CreateSequenceExpression.no_cache",
            "AlterSequenceExpression.no_order",
            "TruncateExpression.continue_identity",
            "TruncateExpression.restrict",
            "TableConstraint.not_enforced",
            "TableConstraint.deferrable",
            "BeginTransactionExpression.deferrable",
            "SetTransactionExpression.not_deferrable",
            "MariaDBExchangePartitionExpression.with_validation",
            "MariaDBExchangePartitionExpression.without_validation",
        ],
    )
    def test_second_spelling_survives_the_round_trip(self, factory, field):
        from rhosocial.activerecord.backend.expression.serialization import (
            ExpressionRegistry,
        )

        dialect = _dialect()
        expr = factory(dialect)
        # Backend-local classes are not in core's auto-registry (that walk
        # covers ``backend/expression`` only); the roundtrip matrix registers
        # them via ``collect_expression_classes``. Registering here lets this
        # focused round-trip deserialize MariaDB-owned expressions too.
        ExpressionRegistry.register(type(expr))
        decoded = deserialize_json(serialize_json(expr), dialect)
        assert getattr(decoded, field) is True


class TestAlterConstraintPairIsConsumed:
    """``AlterConstraint``: mandatory pair, consumed by refusal on MariaDB.

    MariaDB declares no ``supports_alter_constraint_enforced``, so core's
    ``format_alter_constraint_action`` refuses both spellings by name. The
    mandatory grammar refuses "neither" too, which is the one place the
    four-state table differs.
    """

    def _action(self, **kw):
        return AlterConstraint(
            _dialect(), "probe_ck", constraint_type=TableConstraintType.CHECK, **kw
        )

    def test_maria_db_does_not_declare_the_alter_constraint_probe(self):
        # The resolved method is the ConstraintSupport protocol stub (returns
        # None): MariaDB adds no declaration of its own, so core's formatter
        # refuses both spellings. A future declaration would change the
        # outcome and this pin with it.
        assert not _dialect().supports_alter_constraint_enforced()

    def test_neither_set_is_refused_at_construction(self):
        with pytest.raises(ValueError, match="exactly one of enforced=True or not_enforced=True"):
            self._action()

    def test_both_set_is_refused_at_construction(self):
        with pytest.raises(
            ValueError, match="enforced and not_enforced are mutually exclusive"
        ):
            self._action(enforced=True, not_enforced=True)

    def test_enforced_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            self._action(enforced=True).to_sql()
        assert "ENFORCED" in str(excinfo.value)

    def test_not_enforced_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            self._action(not_enforced=True).to_sql()
        assert "NOT ENFORCED" in str(excinfo.value)
