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
them here. ``AlterConstraintAction.enforced`` is covered separately below: its
grammar is mandatory and its refusal comes from core's formatter, because
MariaDB declares no ``supports_alter_constraint_enforced``.
"""

import re
from typing import Any, Callable, Dict, NamedTuple, Tuple

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.errors import IntegrityError
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
    AddTableConstraintAction,
    AlterConstraintAction,
    AlterTableStatement,
    ValidateConstraintAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_function import (
    DropFunctionStatement,
)
from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
    AlterSequenceStatement,
    CreateSequenceStatement,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ConstraintValidation,
    TableConstraint,
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateStatement,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    DropViewStatement,
)
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionStatement,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBExchangePartitionExpression,
)

VERSION = (10, 6, 0)
MARIADB_IMPL_PREFIX = "rhosocial.activerecord.backend.impl.mariadb"


def _dialect() -> MariaDBDialect:
    return MariaDBDialect(VERSION)


def _seq(d):
    return Sequence(d, "probe_seq")


def _table(d, name="probe_t"):
    return Table(d, name)


def _check(d, **kw):
    # The kind is the branch; the keywords that follow are the production's
    # (name / validation / the enforcement and deferral pairs).
    return TableConstraint(
        d,
        branch=TableCheckConstraint(
            d, ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b"))
        ),
        name="probe_ck",
        **kw,
    )


def _fk(d, **kw):
    return TableConstraint(
        d,
        branch=TableForeignKeyConstraint(d, ["a"], (_table(d, "probe_t2"), ["b"])),
        name="probe_fk",
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
        "CreateSequenceStatement.cycle",
        lambda d, **kw: CreateSequenceStatement(d, _seq(d), **kw),
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
        "CreateSequenceStatement.cache",
        lambda d, **kw: CreateSequenceStatement(d, _seq(d), **kw),
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
        "CreateSequenceStatement.order",
        lambda d, **kw: CreateSequenceStatement(d, _seq(d), **kw),
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
        "AlterSequenceStatement.cycle",
        lambda d, **kw: AlterSequenceStatement(d, _seq(d), **kw),
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
        "AlterSequenceStatement.cache",
        lambda d, **kw: AlterSequenceStatement(d, _seq(d), **kw),
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
        "AlterSequenceStatement.order",
        lambda d, **kw: AlterSequenceStatement(d, _seq(d), **kw),
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
        "TruncateStatement.restart_identity",
        lambda d, **kw: TruncateStatement(d, _table(d), **kw),
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
        "TruncateStatement.cascade",
        lambda d, **kw: TruncateStatement(d, _table(d), **kw),
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
        "DropViewStatement.cascade",
        lambda d, **kw: DropViewStatement(d, View(d, "probe_v"), **kw),
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
        "DropFunctionStatement.cascade",
        lambda d, **kw: DropFunctionStatement(d, Function(d, "probe_fn"), **kw),
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
        "BeginTransactionStatement.deferrable",
        lambda d, **kw: BeginTransactionStatement(d, **kw),
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

    def test_mariadb_declares_neither_enforcement_nor_deferral(self):
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

    ``CreateSequenceStatement.no_cycle`` is dropped on purpose here, exactly
    the shape the sequence mixin had before this round consumed the pair. If
    the walk could not report that as a dropped spelling, it could not certify
    the defect it was written to catch.
    """

    def test_a_formatter_that_ignores_no_cycle_is_reported(self):
        case = next(c for c in PAIR_CASES if c.case_id == "CreateSequenceStatement.cycle")

        def deaf_builder(d, **kw):
            # Reads only the positive parameter; the negative one is dropped.
            return CreateSequenceStatement(d, _seq(d), cycle=kw.get("cycle", False))

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
            (lambda d: CreateSequenceStatement(d, _seq(d), no_cycle=True), "no_cycle"),
            (lambda d: CreateSequenceStatement(d, _seq(d), no_cache=True), "no_cache"),
            (lambda d: AlterSequenceStatement(d, _seq(d), no_order=True), "no_order"),
            (lambda d: TruncateStatement(d, _table(d), continue_identity=True), "continue_identity"),
            (lambda d: TruncateStatement(d, _table(d), restrict=True), "restrict"),
            (lambda d: _check(d, not_enforced=True), "not_enforced"),
            (lambda d: _fk(d, deferrable=True), "deferrable"),
            (lambda d: BeginTransactionStatement(d, deferrable=True), "deferrable"),
            (lambda d: SetTransactionExpression(d, not_deferrable=True), "not_deferrable"),
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
            "CreateSequenceStatement.no_cycle",
            "CreateSequenceStatement.no_cache",
            "AlterSequenceStatement.no_order",
            "TruncateStatement.continue_identity",
            "TruncateStatement.restrict",
            "TableConstraint.not_enforced",
            "TableConstraint.deferrable",
            "BeginTransactionStatement.deferrable",
            "SetTransactionExpression.not_deferrable",
            "MariaDBExchangePartitionExpression.with_validation",
            "MariaDBExchangePartitionExpression.without_validation",
        ],
    )
    def test_second_spelling_survives_the_round_trip(self, factory, field):
        from rhosocial.activerecord.backend.expression.serialization import (
            default_registry,
        )

        dialect = _dialect()
        expr = factory(dialect)
        # Backend-local classes are not in core's auto-populated registry (that
        # walk covers the framework's own packages only); the roundtrip matrix
        # registers them via ``collect_expression_classes``. Registering here
        # lets this focused round-trip deserialize MariaDB-owned expressions
        # too; re-registering a class the matrix already added is a no-op.
        default_registry().register_node(type(expr))
        decoded = deserialize_json(serialize_json(expr), dialect)
        assert getattr(decoded, field) is True


class TestAlterConstraintPairIsConsumed:
    """``AlterConstraintAction``: mandatory pair, consumed by refusal on MariaDB.

    MariaDB declares ``supports_alter_constraint_enforced()`` as ``False``, so
    core's ``format_alter_constraint_action`` refuses both spellings by name.
    The mandatory grammar refuses "neither" too, which is the one place the
    four-state table differs.
    """

    def _action(self, **kw):
        return AlterConstraintAction(
            _dialect(), "probe_ck", constraint_kind=TableCheckConstraint, **kw
        )

    def test_mariadb_declares_the_alter_constraint_probe_as_false(self):
        # Declared, not inherited: ``(self)``, no kind, and the value is the
        # measured one. Before this branch the probe resolved to the
        # ``ConstraintSupport`` protocol stub, which answers ``None`` -- core
        # reads that as "no answer" rather than as "no", so the refusal could
        # change under this backend with no MariaDB file edited.
        assert _dialect().supports_alter_constraint_enforced() is False

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


class TestConstraintCapabilityGatesAreDeclaredAndMeasured:
    """Every constraint probe MariaDB answers: the value, and who answers it.

    ``MariaDBDialect`` does not put core's ``ConstraintMixin`` in its MRO, so a
    probe it does not declare resolves to the ``ConstraintSupport`` protocol
    stub and answers ``None``. Core reads three of those probes through
    ``getattr`` (``supports_constraint_novalidate``,
    ``supports_alter_constraint_enforced``, ``supports_validate_constraint``),
    where ``None`` reads as "no answer" rather than as an answer -- so the value
    could change under this backend with no MariaDB file edited, and no MariaDB
    test would notice.

    Measured live on **MariaDB 13.1.1** (192.168.1.3:15694, TLSv1.2, driver
    ``mariadb``). The errno, SQLSTATE or server output behind each row is in the
    docstring of the declaration on ``MariaDBDialect``; the one value the
    official documentation contradicts is spelled out below.
    """

    #: probe -> measured value. One capability question each, so the same
    #: answer holds on every measured version rather than being a boundary.
    MEASURED = [
        # Column / table shape.
        ("supports_foreign_key_constraint", True),
        ("supports_primary_key_constraint", True),
        ("supports_unique_constraint", True),
        ("supports_not_null_constraint", True),
        ("supports_column_character_set", True),
        ("supports_column_collation", True),
        # ALTER TABLE lifecycle.
        ("supports_add_constraint", True),
        ("supports_drop_constraint", True),
        ("supports_drop_constraint_if_exists", True),
        # Spellings the server refuses.
        ("supports_fk_match", False),
        ("supports_deferrable_constraint", False),
        ("supports_constraint_enforced", False),
        ("supports_constraint_novalidate", False),
        ("supports_alter_constraint_enforced", False),
        ("supports_validate_constraint", False),
    ]
    IDS = [name for name, _ in MEASURED]

    @pytest.mark.parametrize("probe, expected", MEASURED, ids=IDS)
    def test_value_is_the_measured_bool(self, probe, expected):
        value = getattr(_dialect(), probe)()
        assert value is expected, (
            f"{probe}() answered {value!r}; the measurement says {expected!r}. "
            f"A real bool is required: None and other truthy stand-ins are what "
            f"the undeclared-probe shape looked like."
        )

    @pytest.mark.parametrize("probe, expected", MEASURED, ids=IDS)
    def test_declared_by_a_mariadb_class(self, probe, expected):
        declaring = _declaring_constraint_probe(MariaDBDialect, probe)
        assert declaring is not None, f"no class in the MRO answers {probe}"
        assert declaring.__module__.startswith(MARIADB_IMPL_PREFIX), (
            f"{probe}() resolves to {declaring.__module__}.{declaring.__name__}, "
            f"not a MariaDB class. An inherited default or a protocol stub can "
            f"silently change under this backend; the measured answer must be "
            f"declared here."
        )

    def test_check_constraint_is_version_gated(self):
        # CHECK constraints land in 10.2.1 (MARIADB_VERSION_BOUNDARIES
        # ['CHECK_CONSTRAINT']); the boundary is already pinned by
        # test_mariadb_version_boundaries.py and is repeated here so this table
        # reads as the whole constraint surface.
        for version in ((10, 1, 0), (10, 2, 0), (10, 2, 1 - 1)):
            assert MariaDBDialect(version).supports_check_constraint() is False, version
        for version in ((10, 2, 1), (10, 2, 5), (10, 6, 0), (13, 1, 1)):
            assert MariaDBDialect(version).supports_check_constraint() is True, version


def _declaring_constraint_probe(cls, name):
    """The first class in the MRO that answers ``name`` itself."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass
    return None


class _AlterConstraintEnforcedDialect(MariaDBDialect):
    def supports_alter_constraint_enforced(self) -> bool:
        return True


class _ValidateConstraintDialect(MariaDBDialect):
    def supports_validate_constraint(self) -> bool:
        return True


class _NovalidateConstraintDialect(MariaDBDialect):
    def supports_constraint_novalidate(self) -> bool:
        return True


class TestTheThreeDeclaredProbesAreLoadBearing:
    """Flipping one of the newly-declared probes flips the rendered outcome.

    A probe answering one value while the formatter ignores it is decorative.
    These three were previously answered by the protocol stub, so nothing could
    tell a refusal that came from a MariaDB answer from one that came from an
    absent declaration.
    """

    def _alter(self, dialect, **kw):
        return AlterConstraintAction(
            dialect, "probe_ck", constraint_kind=TableCheckConstraint, **kw
        )

    def _add_not_valid(self, dialect):
        constraint = _check(
            dialect, validation=ConstraintValidation.NOVALIDATE
        )
        return AlterTableStatement(
            dialect, Table(dialect, "probe_t"), actions=[AddTableConstraintAction(dialect, constraint)]
        )

    def test_alter_constraint_probe_flip_renders_the_spelling(self):
        assert self._alter(_AlterConstraintEnforcedDialect(VERSION), enforced=True).to_sql() == (
            "ALTER CONSTRAINT `probe_ck` ENFORCED",
            (),
        )
        assert self._alter(_AlterConstraintEnforcedDialect(VERSION), not_enforced=True).to_sql() == (
            "ALTER CONSTRAINT `probe_ck` NOT ENFORCED",
            (),
        )

    def test_validate_probe_flip_renders_the_spelling(self):
        assert ValidateConstraintAction(_ValidateConstraintDialect(VERSION), "probe_ck").to_sql() == (
            "VALIDATE CONSTRAINT `probe_ck`",
            (),
        )

    def test_novalidate_probe_flip_renders_the_spelling(self):
        sql, params = self._add_not_valid(_NovalidateConstraintDialect(VERSION)).to_sql()
        assert sql.endswith(" NOT VALID")
        # A DDL CHECK predicate carries no bind parameters (core refuses one in
        # `_format_ddl_condition`), so the action adds none either.
        assert params == ()

    def test_on_mariadb_each_is_still_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError, match="ALTER CONSTRAINT"):
            self._alter(MariaDBDialect(VERSION), enforced=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="VALIDATE CONSTRAINT"):
            ValidateConstraintAction(MariaDBDialect(VERSION), "probe_ck").to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NOT VALID"):
            self._add_not_valid(MariaDBDialect(VERSION)).to_sql()


class TestColumnLevelReferencesBuildsARealForeignKey:
    """The column-level ``REFERENCES`` shortcut: what each server actually builds.

    The official MariaDB documentation says the shortcut ``"does nothing"``
    (mariadb.com/docs/server/reference/sql-statements/data-definition/
    constraint). Live measurement across the wired servers shows that is
    version-dependent, so these tests read the server's version and assert what
    *that* release was measured to do rather than one shape everywhere:

    ============  =========================================================
    version        ``c INT REFERENCES r(id)``
    ============  =========================================================
    10.2 - 10.4    nothing -- no FK, no index, violating row inserts fine
    10.5 - 12.0    enforced FK, generated name ``<tbl>_ibfk_N``
    12.1 - 13.1    enforced FK, generated name is a positional integer
    ============  =========================================================

    The grid granularity is the servers available: 10.4.34 builds nothing,
    10.5.29 is the first that builds one, and 12.0.2 still names it
    ``<tbl>_ibfk_1`` while 12.1.2 already names it ``1``. The boundaries are
    therefore "10.5" and "12.1" only to the resolution those servers give.
    """

    TABLES = "probe_ref_parent, probe_ref_child, probe_ref_two, probe_ref_idx"

    def _cleanup(self, backend):
        # Both directions need the checks off: a parent cannot be dropped while
        # a child still references it (errno 1451), and a child cannot be
        # dropped while the parent is named in a live FK's definition.
        # ``SET FOREIGN_KEY_CHECKS = 0`` is accepted on every measured version.
        try:
            backend.execute("SET FOREIGN_KEY_CHECKS = 0")
            backend.execute(f"DROP TABLE IF EXISTS {self.TABLES}")
        finally:
            backend.execute("SET FOREIGN_KEY_CHECKS = 1")

    def _version(self, backend):
        return tuple(
            int(p) for p in backend.fetch_one("SELECT VERSION() AS v")["v"]
            .split("-")[0].split(".")[:3]
        )

    def test_shortcut_is_inert_below_10_5(self, mariadb_backend):
        """Below 10.5 the shortcut builds nothing, exactly as documented."""
        self._cleanup(mariadb_backend)
        try:
            backend = mariadb_backend
            if self._version(backend) >= (10, 5, 0):
                pytest.skip("the shortcut is enforced from 10.5 onward")
            backend.execute("CREATE TABLE probe_ref_parent (id INT PRIMARY KEY)")
            backend.execute(
                "CREATE TABLE probe_ref_child (id INT PRIMARY KEY, "
                "c INT REFERENCES probe_ref_parent (id))"
            )
            ddl = backend.fetch_one("SHOW CREATE TABLE probe_ref_child")["Create Table"]
            assert "FOREIGN KEY" not in ddl, ddl
            assert backend.fetch_all(
                "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'probe_ref_child' "
                "AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
            ) == []
            assert [r["Key_name"] for r in backend.fetch_all("SHOW INDEX FROM probe_ref_child")] == [
                "PRIMARY"
            ]
            # A row the referenced table does not have is accepted -- which is
            # the whole hazard the documentation is warning about.
            backend.execute("INSERT INTO probe_ref_child (id, c) VALUES (1, 999)")
        finally:
            self._cleanup(mariadb_backend)

    def test_shortcut_creates_an_enforced_foreign_key(self, mariadb_backend):
        self._cleanup(mariadb_backend)
        try:
            backend = mariadb_backend
            if self._version(backend) < (10, 5, 0):
                pytest.skip("the shortcut builds no foreign key before 10.5")
            backend.execute("CREATE TABLE probe_ref_parent (id INT PRIMARY KEY)")
            backend.execute(
                "CREATE TABLE probe_ref_child (id INT PRIMARY KEY, "
                "c INT REFERENCES probe_ref_parent (id))"
            )
            names = {
                row["CONSTRAINT_NAME"]
                for row in backend.fetch_all(
                    "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'probe_ref_child' "
                    "AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
                )
            }
            assert len(names) == 1, names
            with pytest.raises(IntegrityError) as excinfo:
                backend.execute("INSERT INTO probe_ref_child (id, c) VALUES (1, 999)")
            assert "1452" in str(excinfo.value), excinfo.value
        finally:
            self._cleanup(mariadb_backend)

    def test_generated_name_shape_moved_at_12_1(self, mariadb_backend):
        """``<tbl>_ibfk_N`` before 12.1, a positional integer from 12.1.

        The 13.1.1 measurement that disproved the documentation landed on
        ``CONSTRAINT `1```, which reads like "MariaDB never names a
        column-level FK". It does -- through 12.0 -- and then stopped.
        """
        self._cleanup(mariadb_backend)
        try:
            backend = mariadb_backend
            if self._version(backend) < (10, 5, 0):
                pytest.skip("the shortcut builds no foreign key before 10.5")
            backend.execute("CREATE TABLE probe_ref_parent (id INT PRIMARY KEY)")
            backend.execute(
                "CREATE TABLE probe_ref_two (id INT PRIMARY KEY, "
                "c1 INT REFERENCES probe_ref_parent (id), "
                "c2 INT REFERENCES probe_ref_parent (id))"
            )
            names = {
                row["CONSTRAINT_NAME"]
                for row in backend.fetch_all(
                    "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'probe_ref_two' "
                    "AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
                )
            }
            if self._version(backend) >= (12, 1, 0):
                assert names == {"1", "2"}, names
            else:
                assert names == {"probe_ref_two_ibfk_1", "probe_ref_two_ibfk_2"}, names
        finally:
            self._cleanup(mariadb_backend)

    def test_an_index_named_after_the_column_is_created(self, mariadb_backend):
        self._cleanup(mariadb_backend)
        try:
            backend = mariadb_backend
            if self._version(backend) < (10, 5, 0):
                pytest.skip("the shortcut builds no index before 10.5")
            backend.execute("CREATE TABLE probe_ref_parent (id INT PRIMARY KEY)")
            backend.execute(
                "CREATE TABLE probe_ref_idx (id INT PRIMARY KEY, "
                "c INT REFERENCES probe_ref_parent (id))"
            )
            names = [r["Key_name"] for r in backend.fetch_all("SHOW INDEX FROM probe_ref_idx")]
            assert "c" in names, names
            # The index is named after the column, not after the constraint, so
            # that is the name to drop alongside it.
            assert "PRIMARY" in names, names
        finally:
            self._cleanup(mariadb_backend)
