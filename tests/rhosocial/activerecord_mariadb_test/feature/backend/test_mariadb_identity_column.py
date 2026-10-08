# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_identity_column.py
"""MariaDB declares ``AUTO_INCREMENT`` and refuses the standard identity clause.

The two mechanisms are separate nodes, not two spellings of one:

* :class:`AutoIncrementClause` -- the parameterless marker MariaDB accepts;
* :class:`IdentityClause` -- the parameterised ``GENERATED ... AS IDENTITY``
  clause MariaDB refuses.

The refusal is measured, not assumed. This file renders the standard clause
with a MariaDB-quoting dialect whose probes are forced ``True``, sends each
form to a live server, and asserts the server rejects it -- with an acceptance
control for the frame, so the rejection is attributable to the clause and not
to quoting or naming. That measurement is why the production dialect's
``supports_identity_column()`` answers ``False`` and its formatter refuses,
instead of silently rewriting the clause to ``AUTO_INCREMENT`` (the pre-round
override did exactly that, dropping ``ALWAYS`` and the start/increment
options).

Every execution verdict is preceded by a sentinel: a deliberately invalid
statement must classify ``REJECTED``, or a null result could be read as
acceptance. The mariadb client prints nothing on success and raises on
failure, so the sentinel is the only proof that the classifier sees the
failure channel.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.execution_testing import (
    ExecutionOutcome,
    classify_execution,
    confirm_expression_execution,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AutoIncrementClause,
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    IdentityClause,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.base import IdentityAttribute


#: The versions measured for the probe table; every one answers the same.
MEASURED_VERSIONS = ((10, 2, 0), (10, 3, 0), (10, 6, 0), (11, 4, 0), (13, 1, 0))

#: The six parameter probes plus the mechanism switch. All answer False: the
#: standard clause is refused outright, so no option of it can be accepted.
IDENTITY_PROBES = (
    "supports_identity_column",
    "supports_identity_generation_always",
    "supports_identity_start",
    "supports_identity_increment",
    "supports_identity_minvalue",
    "supports_identity_maxvalue",
    "supports_identity_cycle",
)

#: One standard-clause request -> the probe that answers for it. Each request
#: is rendered through :class:`_IdentityDeclaringDialect` and sent to the live
#: server, where it must be rejected; the probe must answer False.
IDENTITY_REJECTION_CASES = (
    ("supports_identity_column", {}),
    ("supports_identity_generation_always", {"generation": "ALWAYS"}),
    ("supports_identity_start", {"start": 100}),
    ("supports_identity_increment", {"increment": 5}),
    ("supports_identity_minvalue", {"minvalue": 1}),
    ("supports_identity_maxvalue", {"maxvalue": 1000}),
    ("supports_identity_cycle", {"cycle": True}),
    ("supports_identity_cycle", {"cycle": False}),
    (
        "supports_identity_column",
        {
            "generation": "ALWAYS",
            "start": 100,
            "increment": 5,
            "minvalue": 1,
            "maxvalue": 1000,
            "cycle": True,
        },
    ),
)

IDENTITY_REJECTION_IDS = [
    f"{probe}-{sorted(kwargs)}" for probe, kwargs in IDENTITY_REJECTION_CASES
]


class _IdentityDeclaringDialect(MariaDBDialect):
    """MariaDB rendering with every identity probe forced ``True``.

    Models the server this dialect is *not*: one that accepts the standard
    clause. The formatter then renders the clause through core's standard
    path with MariaDB's backtick quoting, so the live verdict is about the
    clause itself rather than about identifier quoting.
    """

    def supports_identity_column(self) -> bool:
        return True

    def supports_identity_generation_always(self) -> bool:
        return True

    def supports_identity_start(self) -> bool:
        return True

    def supports_identity_increment(self) -> bool:
        return True

    def supports_identity_minvalue(self) -> bool:
        return True

    def supports_identity_maxvalue(self) -> bool:
        return True

    def supports_identity_cycle(self) -> bool:
        return True


def _create_table(dialect, name, *, auto_increment=False, identity=None):
    """Build ``CREATE TABLE <name> (id INT PRIMARY KEY ...)``.

    ``auto_increment`` selects the legacy constraint flag (the marker path);
    ``identity`` selects an AR-layer :class:`IdentityAttribute` (the standard
    clause path). The two never combine: they are different mechanisms.
    """
    constraints = [ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]
    if auto_increment:
        constraints = [
            ColumnConstraint(
                dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True
            )
        ]
    attributes = [IdentityAttribute(**identity)] if identity is not None else []
    return CreateTableExpression(
        dialect,
        Table(dialect, name),
        [
            ColumnDefinition(
                dialect,
                "id",
                IntegerType(dialect),
                constraints=constraints,
                attributes=attributes,
            )
        ],
    )


class TestProbeDeclarations:
    """The dialect's answers, for every measured version."""

    @pytest.mark.parametrize(
        "version", MEASURED_VERSIONS, ids=lambda v: ".".join(map(str, v))
    )
    def test_auto_increment_marker_is_declared(self, version):
        assert MariaDBDialect(version).supports_auto_increment_column() is True

    @pytest.mark.parametrize(
        "version", MEASURED_VERSIONS, ids=lambda v: ".".join(map(str, v))
    )
    def test_standard_identity_is_declined_on_every_probe(self, version):
        dialect = MariaDBDialect(version)
        for probe in IDENTITY_PROBES:
            assert getattr(dialect, probe)() is False, probe


class TestNodeRendering:
    """The two nodes render or refuse exactly as the probes say."""

    def test_auto_increment_clause_renders_the_marker(self):
        sql, params = AutoIncrementClause(MariaDBDialect((11, 4, 0))).to_sql()
        assert (sql, params) == (" AUTO_INCREMENT", ())

    def test_identity_clause_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError, match="IDENTITY column"):
            IdentityClause(MariaDBDialect((11, 4, 0))).to_sql()

    def test_identity_always_and_options_are_refused(self):
        with pytest.raises(UnsupportedFeatureError, match="IDENTITY column"):
            IdentityClause(
                MariaDBDialect((11, 4, 0)), "ALWAYS", start=10, increment=2
            ).to_sql()

    def test_identity_attribute_is_refused_not_rewritten(self):
        """The old override emitted `` AUTO_INCREMENT`` and dropped the rest."""
        dialect = MariaDBDialect((11, 4, 0))
        expression = _create_table(
            dialect,
            "ident_refused",
            identity={"generation": "ALWAYS", "start": 10, "increment": 2},
        )
        with pytest.raises(UnsupportedFeatureError, match="IDENTITY column"):
            expression.to_sql()

    def test_legacy_constraint_still_renders_the_marker(self):
        dialect = MariaDBDialect((11, 4, 0))
        sql, params = _create_table(
            dialect, "ident_ok", auto_increment=True
        ).to_sql()
        assert sql == "CREATE TABLE `ident_ok` (`id` INT PRIMARY KEY AUTO_INCREMENT)"
        assert params == ()

    def test_legacy_constraint_is_gated_by_the_marker_probe(self):
        """Withdrawing the probe must refuse; the marker is not appended behind it."""

        class WithdrawnMarkerDialect(MariaDBDialect):
            def supports_auto_increment_column(self) -> bool:
                return False

        dialect = WithdrawnMarkerDialect((11, 4, 0))
        with pytest.raises(UnsupportedFeatureError, match="AUTO_INCREMENT column"):
            _create_table(dialect, "ident_refused", auto_increment=True).to_sql()


class TestExecutionConfirmation:
    """Render, send to the live server, classify -- sentinel first."""

    @pytest.fixture
    def sentinel_backend(self, mariadb_backend):
        """Prove the classifier sees both answers before trusting a verdict.

        The invalid statement must come back ``REJECTED``; without that, a
        classifier reading a null result would call everything accepted. The
        valid statement proves the same channel can report acceptance.
        """
        backend = mariadb_backend
        assert (
            classify_execution(backend, "THIS IS NOT SQL")
            is ExecutionOutcome.REJECTED
        )
        assert classify_execution(backend, "SELECT 1") is ExecutionOutcome.ACCEPTED
        return backend

    def test_auto_increment_create_table_executes(self, sentinel_backend):
        dialect = sentinel_backend.dialect
        table = Table(dialect, "ident_round_ok")
        expression = _create_table(dialect, "ident_round_ok", auto_increment=True)

        outcome = confirm_expression_execution(
            sentinel_backend,
            expression,
            prepare=[("DROP TABLE IF EXISTS `ident_round_ok`", ())],
            teardown=[DropTableExpression(dialect, table)],
        )

        assert outcome is ExecutionOutcome.ACCEPTED
        # The teardown really ran: selecting from a missing table is a
        # rejection the same classifier can see.
        assert (
            classify_execution(sentinel_backend, "SELECT * FROM ident_round_ok")
            is ExecutionOutcome.REJECTED
        )

    def test_identity_create_table_is_not_rendered(self, sentinel_backend):
        """The production dialect refuses before anything reaches the server."""
        dialect = sentinel_backend.dialect
        expression = _create_table(
            dialect,
            "ident_round_refused",
            identity={"generation": "ALWAYS", "start": 100, "increment": 5},
        )
        outcome = confirm_expression_execution(sentinel_backend, expression)
        assert outcome is ExecutionOutcome.NOT_RENDERED

    def test_declaring_frame_is_otherwise_valid(self, sentinel_backend):
        """The rejection below is the clause's, not the frame's.

        The same declaring dialect renders the same table with the marker
        MariaDB accepts; that SQL must be ACCEPTED. Without this control, a
        rejection caused by quoting or naming would look like a verdict on the
        identity clause.
        """
        dialect = _IdentityDeclaringDialect((10, 6, 0))
        table = Table(dialect, "ident_round_frame")
        expression = _create_table(
            dialect, "ident_round_frame", auto_increment=True
        )
        outcome = confirm_expression_execution(
            sentinel_backend,
            expression,
            prepare=[("DROP TABLE IF EXISTS `ident_round_frame`", ())],
            teardown=[DropTableExpression(dialect, table)],
        )
        assert outcome is ExecutionOutcome.ACCEPTED

    @pytest.mark.parametrize(
        "probe,kwargs", IDENTITY_REJECTION_CASES, ids=IDENTITY_REJECTION_IDS
    )
    def test_probe_false_matches_server_rejection(
        self, sentinel_backend, probe, kwargs
    ):
        """Each False probe is justified: the server rejects what it gates."""
        assert getattr(MariaDBDialect(), probe)() is False
        dialect = _IdentityDeclaringDialect((10, 6, 0))
        expression = _create_table(dialect, "ident_round_std", identity=kwargs)
        sql, params = expression.to_sql()
        assert (
            classify_execution(sentinel_backend, sql, params)
            is ExecutionOutcome.REJECTED
        )
