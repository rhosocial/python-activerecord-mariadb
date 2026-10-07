# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_master_probe_gates.py
"""MariaDB guard: the master probes core now gates on are MariaDB's own answers.

Core (``c4d6adc``) gave four previously-decorative probes a call site:

=============================  ===============================================
probe                          consumer
=============================  ===============================================
``supports_materialized_cte``  ``format_cte_expression`` (MATERIALIZED hint)
``supports_truncate``          ``format_truncate_statement``
``supports_with_data_clause``  CTAS / CREATE MATERIALIZED VIEW / REFRESH
``supports_transaction_wait``  the WAIT / NO WAIT transaction pair
=============================  ===============================================

An inherited default or a protocol stub is not an answer. Each probe below is
pinned twice: the measured value it must return, and the fact that a MariaDB
class declares it (``__module__`` under ``impl.mariadb``) rather than the
value arriving from a core default or the inherited protocol stub. The
declaration half matters because a core default can change under this backend
without any MariaDB file changing; a declared answer moves with the
measurement.

The probe must also be load-bearing: a subclass that flips it must flip the
outcome. A formatter that ignores its probe while the probe answers True is
the decorative shape this project removes, and a refusal for a spelling the
server accepts is just as wrong.

Measured live (direct connections, TLSv1.2; every connection and every group
carried a deliberately invalid sentinel that came back rejected; grid:
10.2.44 / 10.3.39 / 10.4.34 / 10.5.29 / 10.6.28 / 10.11.19 / 11.4.13 /
11.7.2 / 11.8.9 / 12.0.2 / 12.1.2 / 12.2.2 / 12.3.3 / 13.0.2 / 13.1.1, plus
11.0.6 / 11.1.6 / 11.2.6 / 11.3.2 for the exchange-partition grid):

- ``MATERIALIZED`` / ``NOT MATERIALIZED`` CTE: both rejected with errno 1064
  on every version; MariaDB 10.6.28's ``sql_yacc.yy`` has 0 ``MATERIALIZED``
  occurrences. Answer: ``False``.
- CTAS ``WITH DATA`` / ``WITH NO DATA``: both rejected with errno 1064 on
  every version while the plain ``CREATE TABLE ... AS SELECT`` is accepted
  (the control that makes the clause, not the statement, the rejected part).
  Answer: ``False``.
- ``TRUNCATE [TABLE]``: accepted on every version. Answer: ``True``.
- ``START TRANSACTION WAIT`` / ``NO WAIT`` / ``NOWAIT`` / ``WAIT 5``: all
  rejected with errno 1064 on every version; ``SET TRANSACTION WAIT`` /
  ``NO WAIT`` also rejected everywhere (errno 1193 on 10.2, 1064 after).
  Answer: ``False``.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, QueryExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableAsExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

VERSION = (10, 6, 0)
MARIADB_IMPL_PREFIX = "rhosocial.activerecord.backend.impl.mariadb"

#: The same answer on every measured version; each probe is one capability
#: question, not a version boundary.
VERSIONS = [(10, 2, 0), (10, 6, 0), (11, 4, 0), (13, 1, 0)]


def _dialect(version=VERSION) -> MariaDBDialect:
    return MariaDBDialect(version)


def _table(d, name="probe_t"):
    return Table(d, name)


def _query(d):
    return QueryExpression(d, select=[Column(d, "id")], from_=_table(d, "probe_src"))


def _declaring_class(cls, name):
    """The first class in the MRO that answers ``name`` itself."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass
    return None


class TestProbeValuesAreMariaDBsAnswers:
    """Every gated probe returns a measured bool and MariaDB declares it."""

    PROBES = [
        ("supports_materialized_cte", False),
        ("supports_with_data_clause", False),
        ("supports_truncate", True),
        ("supports_transaction_wait", False),
    ]
    IDS = [name for name, _ in PROBES]

    @pytest.mark.parametrize("version", VERSIONS, ids=lambda v: "v" + ".".join(map(str, v)))
    @pytest.mark.parametrize("probe, expected", PROBES, ids=IDS)
    def test_value_is_the_measured_bool(self, probe, expected, version):
        value = getattr(_dialect(version), probe)()
        assert value is expected, (
            f"{probe}() answered {value!r} on {version}; the measurement says "
            f"{expected!r}. A bool answer is required: None and other truthy "
            f"stand-ins are what the master gates were added to remove."
        )

    @pytest.mark.parametrize("probe, expected", PROBES, ids=IDS)
    def test_declared_by_a_mariadb_class(self, probe, expected):
        declaring = _declaring_class(MariaDBDialect, probe)
        assert declaring is not None, f"no class in the MRO answers {probe}"
        assert declaring.__module__.startswith(MARIADB_IMPL_PREFIX), (
            f"{probe}() resolves to {declaring.__module__}.{declaring.__name__}, "
            f"not a MariaDB class. An inherited default or protocol stub can "
            f"silently change under this backend; the measured answer must be "
            f"declared here."
        )


class TestGatedSpellingsAreConsumed:
    """Setting a gated spelling refuses by name; none set renders the plain form."""

    def test_neither_cte_hint_renders_the_plain_cte(self):
        sql, params = CTEExpression(_dialect(), "c", query="SELECT 1").to_sql()
        assert sql == "`c` AS (SELECT 1)"
        assert params == ()

    def test_materialized_hint_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            CTEExpression(_dialect(), "c", query="SELECT 1", materialized=True).to_sql()
        assert "MATERIALIZED CTE" in str(excinfo.value)

    def test_not_materialized_hint_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            CTEExpression(_dialect(), "c", query="SELECT 1", not_materialized=True).to_sql()
        assert "NOT MATERIALIZED CTE" in str(excinfo.value)

    def test_plain_ctas_renders_without_a_data_clause(self):
        sql, params = CreateTableAsExpression(_dialect(), _table(_dialect()), _query(_dialect())).to_sql()
        assert sql == "CREATE TABLE `probe_t` AS SELECT `id` FROM `probe_src`"
        assert params == ()

    def test_ctas_with_data_is_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            CreateTableAsExpression(dialect, _table(dialect), _query(dialect), with_data=True).to_sql()
        assert "WITH DATA" in str(excinfo.value)

    def test_ctas_with_no_data_is_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            CreateTableAsExpression(dialect, _table(dialect), _query(dialect), no_data=True).to_sql()
        assert "WITH NO DATA" in str(excinfo.value)

    def test_truncate_renders(self):
        sql, params = TruncateExpression(_dialect(), _table(_dialect())).to_sql()
        assert sql == "TRUNCATE TABLE `probe_t`"
        assert params == ()

    def test_transaction_wait_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            BeginTransactionExpression(_dialect(), wait=True).to_sql()
        assert "TRANSACTION WAIT" in str(excinfo.value)

    def test_transaction_no_wait_is_refused_by_name(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            SetTransactionExpression(_dialect(), no_wait=True).to_sql()
        assert "TRANSACTION NO WAIT" in str(excinfo.value)


class _MaterializedCTEDialect(MariaDBDialect):
    def supports_materialized_cte(self) -> bool:
        return True


class _WithDataDialect(MariaDBDialect):
    def supports_with_data_clause(self) -> bool:
        return True


class _NoTruncateDialect(MariaDBDialect):
    def supports_truncate(self) -> bool:
        return False


class _WaitDialect(MariaDBDialect):
    def supports_transaction_wait(self) -> bool:
        return True


class TestProbesAreLoadBearing:
    """Flipping a probe in a subclass flips the rendered outcome.

    A probe answering one value while the formatter ignores it is decorative:
    this walks each gate with the probe flipped and asserts the outcome moved.
    """

    def test_materialized_probe_flip_spells_the_hint(self):
        sql, _ = CTEExpression(
            _MaterializedCTEDialect(VERSION), "c", query="SELECT 1", materialized=True
        ).to_sql()
        assert sql == "`c` AS MATERIALIZED (SELECT 1)"

    def test_with_data_probe_flip_spells_the_clause(self):
        dialect = _WithDataDialect(VERSION)
        sql, _ = CreateTableAsExpression(
            dialect, _table(dialect), _query(dialect), with_data=True
        ).to_sql()
        assert sql.endswith(" WITH DATA")
        sql, _ = CreateTableAsExpression(
            dialect, _table(dialect), _query(dialect), no_data=True
        ).to_sql()
        assert sql.endswith(" WITH NO DATA")

    def test_truncate_probe_flip_refuses(self):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            TruncateExpression(_NoTruncateDialect(VERSION), _table(_NoTruncateDialect(VERSION))).to_sql()
        assert "TRUNCATE" in str(excinfo.value)

    def test_transaction_wait_probe_flip_renders_the_spelling(self):
        dialect = _WaitDialect(VERSION)
        assert BeginTransactionExpression(dialect, wait=True).to_sql() == ("START TRANSACTION WAIT", ())
        assert BeginTransactionExpression(dialect, no_wait=True).to_sql() == ("START TRANSACTION NO WAIT", ())
        assert SetTransactionExpression(dialect, wait=True).to_sql() == ("SET TRANSACTION WAIT", ())
        assert SetTransactionExpression(dialect, no_wait=True).to_sql() == ("SET TRANSACTION NO WAIT", ())

    def test_transaction_wait_declaration_owner_is_a_mariadb_class(self):
        # The probe starts as the inherited protocol stub (answering None), so
        # this pins the fix rather than only the behaviour above.
        declaring = _declaring_class(MariaDBDialect, "supports_transaction_wait")
        assert declaring is not None
        assert declaring.__module__.startswith(MARIADB_IMPL_PREFIX), (
            f"supports_transaction_wait still resolves to "
            f"{declaring.__module__}.{declaring.__name__}"
        )
