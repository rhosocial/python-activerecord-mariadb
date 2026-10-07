# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_sequence_probes.py
"""Every MariaDB sequence option probe must be load-bearing.

A capability probe is *load-bearing* when the formatter's decision follows its
answer: flip the probe and the rendered statement (or the refusal) flips with
it. A probe whose answer can change while the behaviour does not is
*decorative* -- a capability declaration nobody consults.

This file exists because ``MariaDBSequenceMixin.format_alter_sequence_statement``
rendered ``START = value`` without consulting
``supports_alter_sequence_start()``: it consulted the CREATE-side
``supports_sequence_start()`` instead. Both answer ``True`` for MariaDB, so the
rendered SQL happened to agree with the declaration and the missing gate was
invisible. The seven neighbouring options in the same method already consulted
their own probes, so this was an internal inconsistency, not a design choice.

Core keeps the two START questions apart. ``supports_sequence_start`` answers
for ``CREATE SEQUENCE ... START`` (the initial value); the ALTER-side clause of
the same spelling is ``supports_alter_sequence_start``'s question, and four of
the six real backends refuse it. The CREATE formatter consults the former, the
ALTER formatter the latter.

The walk below renders every option through both formatters -- the probes are
the dialect's in both cases -- flipping exactly one probe in a subclass each
time. The ``start`` case is the one that caught the defect: before the gate was
fixed, the ``alter-start`` case stayed green while the probe was flipped, and
the guard reported it decorative.
"""

from typing import NamedTuple

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Sequence
from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
    AlterSequenceExpression,
    CreateSequenceExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

VERSION = (10, 6, 0)


@pytest.fixture
def dialect():
    return MariaDBDialect(VERSION)


def _seq(dialect):
    return Sequence(dialect, "probe_seq")


class _ProbeCase(NamedTuple):
    """One option request and the probe that must decide it.

    ``statement`` and ``expression_cls`` say which formatter renders the
    request; ``feature`` is the name the refusal must carry when the probe
    answers ``False``; ``kwargs`` request the option; ``probe_name`` is the
    capability that must answer for it.
    """

    label: str
    statement: str
    expression_cls: type
    option: str
    feature: str
    probe_name: str
    kwargs: dict


#: Every sequence option probe, exercised on every statement that carries the
#: option. ``start`` maps to a different probe per statement: CREATE asks
#: whether the initial value can be set, ALTER whether it can be changed.
SEQUENCE_OPTION_PROBES = [
    _ProbeCase(
        "create-start", "CREATE", CreateSequenceExpression,
        "start", "SEQUENCE START",
        "supports_sequence_start", {"start": 5},
    ),
    _ProbeCase(
        "create-increment", "CREATE", CreateSequenceExpression,
        "increment", "SEQUENCE INCREMENT",
        "supports_sequence_increment", {"increment": 2},
    ),
    _ProbeCase(
        "create-minvalue", "CREATE", CreateSequenceExpression,
        "minvalue", "SEQUENCE MINVALUE",
        "supports_sequence_minvalue", {"minvalue": 1},
    ),
    _ProbeCase(
        "create-maxvalue", "CREATE", CreateSequenceExpression,
        "maxvalue", "SEQUENCE MAXVALUE",
        "supports_sequence_maxvalue", {"maxvalue": 500},
    ),
    _ProbeCase(
        "create-cycle", "CREATE", CreateSequenceExpression,
        "cycle", "SEQUENCE CYCLE",
        "supports_sequence_cycle", {"cycle": True},
    ),
    _ProbeCase(
        "create-cache", "CREATE", CreateSequenceExpression,
        "cache", "SEQUENCE CACHE",
        "supports_sequence_cache", {"cache": 10},
    ),
    _ProbeCase(
        "create-order", "CREATE", CreateSequenceExpression,
        "order", "SEQUENCE ORDER",
        "supports_sequence_order", {"order": True},
    ),
    _ProbeCase(
        "create-owned-by", "CREATE", CreateSequenceExpression,
        "owned_by", "SEQUENCE OWNED BY",
        "supports_sequence_owned_by", {"owned_by": "orders.id"},
    ),
    _ProbeCase(
        "alter-start", "ALTER", AlterSequenceExpression,
        "start", "ALTER SEQUENCE START",
        "supports_alter_sequence_start", {"start": 5},
    ),
    _ProbeCase(
        "alter-increment", "ALTER", AlterSequenceExpression,
        "increment", "ALTER SEQUENCE INCREMENT",
        "supports_sequence_increment", {"increment": 2},
    ),
    _ProbeCase(
        "alter-minvalue", "ALTER", AlterSequenceExpression,
        "minvalue", "ALTER SEQUENCE MINVALUE",
        "supports_sequence_minvalue", {"minvalue": 1},
    ),
    _ProbeCase(
        "alter-maxvalue", "ALTER", AlterSequenceExpression,
        "maxvalue", "ALTER SEQUENCE MAXVALUE",
        "supports_sequence_maxvalue", {"maxvalue": 500},
    ),
    _ProbeCase(
        "alter-cycle", "ALTER", AlterSequenceExpression,
        "cycle", "ALTER SEQUENCE CYCLE",
        "supports_sequence_cycle", {"cycle": True},
    ),
    _ProbeCase(
        "alter-cycle-default", "ALTER", AlterSequenceExpression,
        "cycle-default", "ALTER SEQUENCE CYCLE",
        "supports_sequence_cycle", {"cycle": False},
    ),
    _ProbeCase(
        "alter-cache", "ALTER", AlterSequenceExpression,
        "cache", "ALTER SEQUENCE CACHE",
        "supports_sequence_cache", {"cache": 10},
    ),
    _ProbeCase(
        "alter-order", "ALTER", AlterSequenceExpression,
        "order", "ALTER SEQUENCE ORDER",
        "supports_sequence_order", {"order": True},
    ),
    _ProbeCase(
        "alter-owned-by", "ALTER", AlterSequenceExpression,
        "owned_by", "ALTER SEQUENCE OWNED BY",
        "supports_sequence_owned_by", {"owned_by": "orders.id"},
    ),
]

#: The probes the walk must keep covering. Hard-coded on purpose: deriving it
#: from the cases would let a case and its probe be deleted together without
#: this floor moving.
OPTION_PROBES_AT_WALK_BIRTH = frozenset(
    {
        "supports_sequence_start",
        "supports_alter_sequence_start",
        "supports_sequence_increment",
        "supports_sequence_minvalue",
        "supports_sequence_maxvalue",
        "supports_sequence_cycle",
        "supports_sequence_cache",
        "supports_sequence_order",
        "supports_sequence_owned_by",
    }
)


def _flipped_dialect(probe_name):
    """A stock dialect with exactly one capability probe flipped.

    The flip is the only difference from the stock dialect, so any behaviour
    change between the two is attributable to that probe alone.
    """
    stock_value = getattr(MariaDBDialect(VERSION), probe_name)()
    flipped = type(
        f"MariaDBDialectFlipped_{probe_name}",
        (MariaDBDialect,),
        {probe_name: lambda self: not stock_value},
    )
    return flipped(VERSION)


def _render_outcome(expression_cls, dialect, kwargs):
    """Render one statement; a refusal is an outcome, not an error.

    Returns ``("rendered", (sql, params))`` or ``("refused", message)`` so the
    guard can compare the two dialects' behaviour without ``pytest.raises``.
    """
    try:
        sql, params = expression_cls(dialect, _seq(dialect), **kwargs).to_sql()
    except UnsupportedFeatureError as exc:
        return "refused", str(exc)
    return "rendered", (sql, params)


def _load_bearing_failure(case, stock, flipped):
    """The reason ``case`` fails the load-bearing walk, or ``None``.

    The stock dialect's outcome must follow its own probe answer: rendered
    when the probe accepts the option, refused (naming it) when it does not.
    The flipped dialect must then answer the opposite. If both dialects behave
    the same, the probe is decorative.
    """
    stock_probe = getattr(stock, case.probe_name)()
    stock_kind, stock_detail = _render_outcome(case.expression_cls, stock, case.kwargs)
    flipped_kind, flipped_detail = _render_outcome(
        case.expression_cls, flipped, case.kwargs
    )
    expected_stock = "rendered" if stock_probe else "refused"
    expected_flipped = "refused" if stock_probe else "rendered"

    if stock_kind != expected_stock:
        return (
            f"{case.statement} SEQUENCE {case.option}: the stock dialect answers "
            f"{case.probe_name}()={stock_probe}, so the option must be "
            f"{expected_stock}; got {stock_kind}: {stock_detail!r}"
        )
    if stock_kind == "refused" and case.feature not in stock_detail:
        return (
            f"{case.statement} SEQUENCE {case.option}: the refusal does not name "
            f"{case.feature!r}: {stock_detail!r}"
        )
    if flipped_kind != expected_flipped:
        return (
            f"{case.statement} SEQUENCE {case.option}: with "
            f"{case.probe_name}() flipped to {not stock_probe}, the option must be "
            f"{expected_flipped}; got {flipped_kind}: {flipped_detail!r}. The "
            f"probe is decorative: the formatter ignores its answer."
        )
    if flipped_kind == "refused" and case.feature not in flipped_detail:
        return (
            f"{case.statement} SEQUENCE {case.option}: the flipped refusal does "
            f"not name {case.feature!r}: {flipped_detail!r}"
        )
    return None


class TestEverySequenceOptionProbeIsLoadBearing:
    """Flipping any one sequence-option probe must change the formatter's answer.

    Each case subclasses the stock dialect with exactly one probe flipped and
    renders the same expression through the same formatter. The stock dialect
    answers ``False`` for ``order`` and ``owned_by``, so those cases must
    refuse on the stock dialect and render on the flipped one; the other probes
    answer ``True``, so their cases must flip the other way.
    """

    @pytest.mark.parametrize(
        "case",
        SEQUENCE_OPTION_PROBES,
        ids=[case.label for case in SEQUENCE_OPTION_PROBES],
    )
    def test_every_sequence_option_probe_is_load_bearing(self, dialect, case):
        flipped_dialect = _flipped_dialect(case.probe_name)
        failure = _load_bearing_failure(case, dialect, flipped_dialect)
        assert failure is None, failure

    def test_the_walk_covers_every_option_probe(self):
        covered = {case.probe_name for case in SEQUENCE_OPTION_PROBES}
        assert covered >= OPTION_PROBES_AT_WALK_BIRTH, (
            f"the walk no longer covers {sorted(OPTION_PROBES_AT_WALK_BIRTH - covered)}"
        )


class TestTheGuardCanSeeADecorativeProbe:
    """The guard is live: a formatter that ignores a probe is reported.

    The dialect below is the shape ``format_alter_sequence_statement`` had
    before the gate was fixed -- it answers
    ``supports_alter_sequence_start()`` with ``False`` yet still renders
    ``START``. If the walk could not report that as decorative, it could not
    certify the defect it was written to catch.
    """

    def test_a_formatter_that_ignores_the_alter_start_probe_is_reported(self, dialect):
        case = next(c for c in SEQUENCE_OPTION_PROBES if c.label == "alter-start")

        class DeafToTheAlterStartProbe(MariaDBDialect):
            def supports_alter_sequence_start(self) -> bool:
                return False

            def format_alter_sequence_statement(self, expr):
                if expr.start is not None:
                    return (
                        f"ALTER SEQUENCE {expr.sequence.to_sql()[0]} "
                        f"START = {expr.start}",
                        (),
                    )
                return super().format_alter_sequence_statement(expr)

        flipped = DeafToTheAlterStartProbe(VERSION)
        failure = _load_bearing_failure(case, dialect, flipped)
        assert failure is not None, (
            "the walk did not notice a probe the formatter ignores"
        )
        assert "decorative" in failure, failure
