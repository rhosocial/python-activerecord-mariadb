# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/dialect/test_mariadb_if_exists_probes.py
"""MariaDB IF [NOT] EXISTS probes, with the formatter's refusal pinned to them.

Every value below is measured, not inherited from the MySQL sibling:

- ``CREATE TRIGGER IF NOT EXISTS``: MariaDB 10.1.4 (MDEV-7286). The 10.1.4
  release notes say "Consistent support for IF EXISTS, IF NOT EXISTS, and
  OR REPLACE clauses was added to: ... CREATE TRIGGER and DROP TRIGGER".
  10.0.15's grammar has no slot for it, and 10.1.4-to-10.0.15 comparison of
  ``sql_yacc.yy`` / ``sql_trigger.cc`` shows the rule and its handler
  arriving together. Verified live on 10.2.44, 10.4.34, 10.5.29, 10.6.28,
  10.11.19, 11.4.13, 12.0.2, 13.1.1: the clause is accepted, a repeated
  create is warning 1359, and a sentinel between the clause and the name is
  errno 1064.
- ``DROP TRIGGER IF EXISTS``: present already in the 10.0.15 grammar
  (``DROP TRIGGER_SYM opt_if_exists sp_name``); 10.1.4 made its support
  consistent rather than introducing it. Accepted on all eight live servers;
  an absent name with the clause is warning 1360, without it errno 1360.
- ``CREATE VIEW IF NOT EXISTS``: MariaDB 10.1.4. The 10.0.15 view rule is
  ``view_suid VIEW_SYM table_ident``; 10.1.4 adds ``opt_if_not_exists``.
  Accepted on all eight live servers (repeated create is warning 1050);
  sentinel errno 1064.
- ``DROP CONSTRAINT IF EXISTS``: MariaDB 10.2.1, the first release whose
  ALTER TABLE grammar has ``DROP CONSTRAINT``; the rule carries
  ``opt_if_exists_table_element`` from the start, so the qualifier shares
  that floor. Accepted on all eight live servers for an absent name
  (warning 1091) while the bare spelling answers errno 1091.

The other probes in the cross-backend matrix were re-checked and are MariaDB's
own answers, not MySQL's: ADD/DROP COLUMN and CREATE/DROP INDEX qualifiers
predate 10.0.2 (already in the 10.0.15 grammar), table and database qualifiers
are older than that, ``RENAME COLUMN`` is 10.5.2, and every one of those is
accepted live on the eight servers above. The two schema qualifiers stay False
on purpose: MariaDB has no schema namespace, so ``supports_create_schema`` is
False and the database mixin carries the same ``CREATE SCHEMA`` bytes as
``CREATE DATABASE``.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger, View
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    DropTableConstraintAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
    CreateTriggerStatement,
    DropTriggerStatement,
    TriggerEvent,
    TriggerTiming,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    CreateViewStatement,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

MARIADB_IMPL_PREFIX = "rhosocial.activerecord.backend.impl.mariadb"


def _dialect(version=(10, 6, 0)) -> MariaDBDialect:
    return MariaDBDialect(version)


def _create_trigger(d, if_not_exists=False):
    return CreateTriggerStatement(
        d,
        trigger=Trigger(d, "trg"),
        table=Table(d, "t"),
        timing=TriggerTiming.BEFORE,
        events=[TriggerEvent.INSERT],
        function=Function(d, "fn"),
        if_not_exists=if_not_exists,
    )


def _create_view(d, if_not_exists=False):
    return CreateViewStatement(
        d,
        view=View(d, "v"),
        query=QueryStatement(d, select=[Column(d, "id")], from_=Table(d, "t")),
        if_not_exists=if_not_exists,
    )


def _declaring_class(cls, name):
    """The first class in the MRO that answers ``name`` itself."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass
    return None


class TestTriggerIfExistsGates:
    """The trigger qualifiers answer MariaDB's documented version floors."""

    @pytest.mark.parametrize(
        "version, expected",
        [
            ((10, 0, 15), False),
            ((10, 1, 3), False),
            ((10, 1, 4), True),
            ((10, 2, 0), True),
            ((10, 2, 44), True),
            ((13, 1, 1), True),
        ],
        ids=lambda value: "v" + ".".join(map(str, value)) if isinstance(value, tuple) else str(value),
    )
    def test_create_trigger_if_not_exists_is_gated_at_10_1_4(self, version, expected):
        assert _dialect(version).supports_trigger_if_not_exists() is expected

    @pytest.mark.parametrize(
        "version",
        [(10, 0, 15), (10, 1, 4), (10, 2, 0), (13, 1, 1)],
        ids=lambda value: "v" + ".".join(map(str, value)) if isinstance(value, tuple) else str(value),
    )
    def test_drop_trigger_if_exists_is_true_on_every_supported_version(self, version):
        assert _dialect(version).supports_trigger_if_exists() is True

    @pytest.mark.parametrize(
        "probe",
        ["supports_trigger_if_not_exists", "supports_trigger_if_exists"],
    )
    def test_probe_is_declared_by_a_mariadb_class(self, probe):
        declaring = _declaring_class(MariaDBDialect, probe)
        assert declaring is not None, f"no class in the MRO answers {probe}"
        assert declaring.__module__.startswith(MARIADB_IMPL_PREFIX), (
            f"{probe} resolves to {declaring.__module__}.{declaring.__name__}; "
            f"an inherited stub is not MariaDB's answer"
        )


class TestTriggerQualifiersAreLoadBearing:
    """The formatter consults the probe instead of dropping or emitting blindly."""

    def test_create_below_10_1_4_refuses_by_name(self):
        dialect = _dialect((10, 1, 3))
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect.format_create_trigger_statement(_create_trigger(dialect, True))
        assert "CREATE TRIGGER IF NOT EXISTS" in str(excinfo.value)
        assert "10.1.4" in str(excinfo.value)

    def test_create_from_10_1_4_renders_the_clause(self):
        dialect = _dialect((10, 1, 4))
        sql, params = _create_trigger(dialect, True).to_sql()
        assert sql == (
            "CREATE TRIGGER IF NOT EXISTS `trg` BEFORE INSERT ON `t` "
            "FOR EACH ROW BEGIN CALL `fn`(); END"
        )
        assert params == ()

    def test_create_without_the_flag_renders_plain_form(self):
        sql, _ = _create_trigger(_dialect(), False).to_sql()
        assert sql.startswith("CREATE TRIGGER `trg` ")
        assert "IF NOT EXISTS" not in sql

    def test_drop_renders_the_clause(self):
        dialect = _dialect((10, 1, 3))
        sql, params = DropTriggerStatement(
            dialect, trigger=Trigger(dialect, "trg"), if_exists=True
        ).to_sql()
        assert sql == "DROP TRIGGER IF EXISTS `trg`"
        assert params == ()

    def test_drop_refuses_when_the_probe_is_false(self):
        class _NoDropIfExistsDialect(MariaDBDialect):
            def supports_trigger_if_exists(self) -> bool:
                return False

        dialect = _NoDropIfExistsDialect((10, 6, 0))
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            DropTriggerStatement(
                dialect, trigger=Trigger(dialect, "trg"), if_exists=True
            ).to_sql()
        assert "DROP TRIGGER IF EXISTS" in str(excinfo.value)

    def test_create_emits_when_the_probe_is_flipped_true_below_the_floor(self):
        class _IfNotExistsLoweredDialect(MariaDBDialect):
            def supports_trigger_if_not_exists(self) -> bool:
                return True

        dialect = _IfNotExistsLoweredDialect((10, 0, 15))
        sql, _ = _create_trigger(dialect, True).to_sql()
        assert sql.startswith("CREATE TRIGGER IF NOT EXISTS `trg` ")


class TestViewIfNotExistsGate:
    """CREATE VIEW IF NOT EXISTS shares the 10.1.4 floor with the trigger."""

    @pytest.mark.parametrize(
        "version, expected",
        [
            ((10, 0, 15), False),
            ((10, 1, 3), False),
            ((10, 1, 4), True),
            ((10, 6, 0), True),
            ((13, 1, 1), True),
        ],
        ids=lambda value: "v" + ".".join(map(str, value)) if isinstance(value, tuple) else str(value),
    )
    def test_gate(self, version, expected):
        assert _dialect(version).supports_if_not_exists_view() is expected

    def test_declared_by_a_mariadb_class(self):
        declaring = _declaring_class(MariaDBDialect, "supports_if_not_exists_view")
        assert declaring is not None
        assert declaring.__module__.startswith(MARIADB_IMPL_PREFIX), (
            "supports_if_not_exists_view still resolves to "
            f"{declaring.__module__}.{declaring.__name__}"
        )

    def test_below_the_floor_refuses_by_name(self):
        dialect = _dialect((10, 1, 3))
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            _create_view(dialect, True).to_sql()
        assert "CREATE VIEW IF NOT EXISTS" in str(excinfo.value)

    def test_from_the_floor_renders_the_clause(self):
        dialect = _dialect((10, 1, 4))
        sql, params = _create_view(dialect, True).to_sql()
        assert sql.startswith("CREATE VIEW IF NOT EXISTS `v` ")
        assert " AS SELECT `id` FROM `t`" in sql
        assert params == ()


class TestDropConstraintIfExistsGate:
    """DROP CONSTRAINT and its IF EXISTS qualifier both start at 10.2.1."""

    @pytest.mark.parametrize(
        "version, expected",
        [
            ((10, 1, 20), False),
            ((10, 2, 0), False),
            ((10, 2, 1), True),
            ((10, 2, 44), True),
            ((13, 1, 1), True),
        ],
        ids=lambda value: "v" + ".".join(map(str, value)) if isinstance(value, tuple) else str(value),
    )
    def test_gate(self, version, expected):
        assert _dialect(version).supports_drop_constraint_if_exists() is expected

    def test_below_the_floor_refuses_the_qualifier_by_name(self):
        dialect = _dialect((10, 2, 0))
        action = DropTableConstraintAction(dialect, "uq", if_exists=True)
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            action.to_sql()
        assert "DROP CONSTRAINT IF EXISTS" in str(excinfo.value)

    def test_from_the_floor_renders_the_qualifier(self):
        dialect = _dialect((10, 2, 1))
        action = DropTableConstraintAction(dialect, "uq", if_exists=True)
        sql, params = action.to_sql()
        assert sql == "DROP CONSTRAINT IF EXISTS `uq`"
        assert params == ()

    def test_plain_form_is_not_refused(self):
        """The qualifier probe gates only the qualifier, not the statement.

        ``supports_drop_constraint`` is the statement-level switch; this
        probe is asked only when ``if_exists=True``. The formatter's division
        is what this pins.
        """
        dialect = _dialect((10, 2, 0))
        action = DropTableConstraintAction(dialect, "uq")
        sql, _ = action.to_sql()
        assert sql == "DROP CONSTRAINT `uq`"


class TestRecheckedMatrix:
    """The sibling-inherited rows that were re-measured and left unchanged."""

    OTHER_PROBES = [
        "supports_add_column_if_not_exists",
        "supports_drop_column_if_exists",
        "supports_index_if_not_exists",
        "supports_index_if_exists",
        "supports_if_not_exists_table",
        "supports_if_exists_table",
        "supports_if_exists_view",
        "supports_database_if_not_exists",
        "supports_database_if_exists",
    ]

    @pytest.mark.parametrize("probe", OTHER_PROBES)
    def test_true_on_the_oldest_measured_version(self, probe):
        assert getattr(_dialect((10, 2, 44)), probe)() is True

    @pytest.mark.parametrize(
        "probe",
        ["supports_schema_if_not_exists", "supports_schema_if_exists"],
    )
    def test_schema_qualifiers_stay_false_for_the_schema_namespace(self, probe):
        """MariaDB has no schema namespace, so the schema DDL path stays closed.

        ``CREATE SCHEMA`` is a synonym for ``CREATE DATABASE`` on this server,
        which the database mixin renders; ``supports_schema`` and
        ``supports_create_schema`` are False here by the documented decision
        (see ``test_schema_support.py``). Answering True for a qualifier on a
        statement the formatter refuses would be incoherent, so these two
        remain False even though the bytes ``CREATE SCHEMA IF NOT EXISTS`` are
        accepted live -- the database-side probes carry that spelling.
        """
        assert getattr(_dialect((10, 2, 44)), probe)() is False

    @pytest.mark.parametrize(
        "version, expected",
        [((10, 5, 1), False), ((10, 5, 2), True)],
        ids=lambda value: "v" + ".".join(map(str, value)) if isinstance(value, tuple) else str(value),
    )
    def test_rename_column_keeps_its_10_5_2_gate(self, version, expected):
        assert _dialect(version).supports_rename_column() is expected
