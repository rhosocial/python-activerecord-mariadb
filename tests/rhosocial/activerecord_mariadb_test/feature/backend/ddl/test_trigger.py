# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_trigger.py
"""MariaDB trigger DDL formatting tests.

This module covers the ``MariaDBTriggerMixin``: capability gates (including
MariaDB 10.4+ INSTEAD OF / multiple triggers) and the pure SQL formatters
for CREATE TRIGGER and DROP TRIGGER statements.

The mixin is exercised through a minimal harness class so the version-gated
capability methods (which ``MariaDBDialect`` overrides with static answers)
are covered directly.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements import (
    CreateTriggerExpression,
    DropTriggerExpression,
    TriggerEvent,
    TriggerLevel,
    TriggerTiming,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.trigger import MariaDBTriggerMixin

VERSION_10_4 = (10, 4, 0)
VERSION_10_3 = (10, 3, 0)
VERSION_10_2 = (10, 2, 2)


class _TriggerHarness(MariaDBTriggerMixin):
    """Minimal dialect harness exposing just the trigger mixin."""

    def __init__(self, version):
        """Store the version tuple used by capability gates."""
        self.version = version
        self.name = "TestTrigger"

    def format_identifier(self, identifier):
        """Backtick-quote an identifier like the real dialect."""
        return f"`{identifier}`"


class _BodyStub:
    """Minimal body expression stub exposing ``to_sql()``."""

    def __init__(self, sql, params=()):
        """Store the SQL text and bind parameters to return from to_sql()."""
        self._sql = sql
        self._params = params

    def to_sql(self):
        """Return the stubbed (SQL, params) tuple."""
        return self._sql, self._params


def _make_trigger(dialect, **overrides):
    """Build a CreateTriggerExpression with MariaDB-extension attributes.

    Args:
        dialect: The trigger harness instance to bind.
        **overrides: Keyword overrides for constructor args and mixin-only
            attributes (or_replace, ordering, body).

    Returns:
        A configured CreateTriggerExpression instance.
    """
    kwargs = {
        "trigger": "trg_update_ts",
        "table": "users",
        "timing": TriggerTiming.BEFORE,
        "events": [TriggerEvent.UPDATE],
        "function_name": "update_ts",
    }
    kwargs.update(overrides)
    expr = CreateTriggerExpression(dialect, **{
        k: v for k, v in kwargs.items() if k not in ("or_replace", "ordering", "body")
    })
    defaults = {"or_replace": False, "ordering": None, "body": None}
    defaults.update(kwargs)
    for attr, value in defaults.items():
        setattr(expr, attr, value)
    return expr


class TestTriggerCapabilities:
    """Tests for trigger capability gates."""

    def test_always_supported(self):
        """Test that basic trigger support always returns True."""
        dialect = _TriggerHarness(VERSION_10_3)
        assert dialect.supports_trigger() is True, "basic triggers are always supported"
        assert dialect.supports_create_trigger() is True, "CREATE TRIGGER is always supported"
        assert dialect.supports_drop_trigger() is True, "DROP TRIGGER is always supported"
        assert dialect.supports_or_replace_trigger() is True, \
            "OR REPLACE is supported since MariaDB 10.1.4"

    def test_never_supported(self):
        """Test that unsupported trigger features always return False."""
        dialect = _TriggerHarness(VERSION_10_4)
        assert dialect.supports_statement_trigger() is False, \
            "FOR EACH STATEMENT triggers are unsupported"
        assert dialect.supports_trigger_referencing() is False, \
            "REFERENCING clause is unsupported"
        assert dialect.supports_trigger_when() is False, "WHEN condition is unsupported"
        assert dialect.supports_trigger_if_not_exists() is False, \
            "IF NOT EXISTS is replaced by OR REPLACE"

    @pytest.mark.parametrize("version,expected", [
        (VERSION_10_4, True),
        (VERSION_10_3, False),
    ])
    def test_instead_of_trigger_gate(self, version, expected):
        """Test the 10.4 version gate for INSTEAD OF triggers."""
        dialect = _TriggerHarness(version)
        assert dialect.supports_instead_of_trigger() is expected, \
            "supports_instead_of_trigger() must match the 10.4 boundary"

    @pytest.mark.parametrize("version,expected", [
        (VERSION_10_4, True),
        (VERSION_10_2, False),
    ])
    def test_multiple_triggers_per_timing_gate(self, version, expected):
        """Test the 10.4 version gate for multiple triggers per timing."""
        dialect = _TriggerHarness(version)
        assert dialect.supports_multiple_triggers_per_timing() is expected, \
            "supports_multiple_triggers_per_timing() must match the 10.4 boundary"

    @pytest.mark.parametrize("version,expected", [
        ((10, 2, 3), True),
        (VERSION_10_2, False),
    ])
    def test_trigger_order_gate(self, version, expected):
        """Test the 10.2.3 version gate for trigger ordering."""
        dialect = _TriggerHarness(version)
        assert dialect.supports_trigger_order() is expected, \
            "supports_trigger_order() must match the 10.2.3 boundary"


class TestCreateTriggerStatement:
    """Tests for CREATE TRIGGER statement formatting."""

    def test_basic_function_call(self):
        """Test a basic trigger that calls a stored function."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect)
        sql, params = expr.to_sql()
        assert sql.startswith("CREATE TRIGGER"), "statement must start with CREATE TRIGGER"
        assert "`trg_update_ts`" in sql, "trigger name must be identifier-quoted"
        assert "BEFORE" in sql, "timing must be rendered"
        assert "UPDATE" in sql, "event must be rendered"
        assert "ON `users`" in sql, "table must be rendered after ON"
        assert "FOR EACH ROW" in sql, "row-level trigger must be rendered"
        assert "CALL `update_ts`();" in sql, "function call must be rendered"
        assert "BEGIN" in sql, "body must be wrapped in BEGIN"
        assert "END" in sql, "body must end with END"
        assert params == (), "function-call triggers have no bind parameters"

    def test_or_replace(self):
        """Test CREATE OR REPLACE TRIGGER."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, or_replace=True)
        sql, _ = expr.to_sql()
        assert "CREATE OR REPLACE TRIGGER" in sql, "OR REPLACE must follow CREATE"

    def test_if_not_exists(self):
        """Test CREATE TRIGGER IF NOT EXISTS rendering."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, if_not_exists=True)
        sql, _ = expr.to_sql()
        assert "TRIGGER IF NOT EXISTS" in sql, "IF NOT EXISTS must follow TRIGGER"

    def test_ordering(self):
        """Test the FOLLOWS/PRECEDES ordering clause."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, ordering=("FOLLOWS", "other_trg"))
        sql, _ = expr.to_sql()
        assert "FOLLOWS" in sql, "ordering type must be uppercased"
        assert "`other_trg`" in sql, "ordering target must be identifier-quoted"

    def test_body_string(self):
        """Test a trigger with an inline string body."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, function_name="", body="SET NEW.updated_at = NOW();")
        sql, params = expr.to_sql()
        assert "SET NEW.updated_at = NOW();" in sql, "string body must be inlined"
        assert params == (), "string body produces no bind parameters"

    def test_body_expression(self):
        """Test a trigger with an expression body carrying parameters."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(
            dialect,
            function_name="",
            body=_BodyStub("SELECT ?", ("v",)),
        )
        sql, params = expr.to_sql()
        assert "SELECT ?" in sql, "expression body SQL must be inlined"
        assert params == ("v",), "expression body params must be forwarded"

    def test_no_events(self):
        """Test a trigger with an empty events list omits the event keyword."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, events=[])
        sql, _ = expr.to_sql()
        assert "FOR EACH ROW" in sql, "row-level clause must still be rendered"
        assert "INSERT" not in sql and "UPDATE" not in sql and "DELETE" not in sql, \
            "no event keyword may appear for an empty events list"

    def test_no_function_and_no_body(self):
        """Test a trigger with neither function_name nor body renders an empty body."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, function_name="", body=None)
        sql, _ = expr.to_sql()
        assert "BEGIN" in sql, "empty body must still open with BEGIN"
        assert "END" in sql, "empty body must still close with END"

    def test_instead_of_supported(self):
        """Test INSTEAD OF timing on a supported version."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(
            dialect,
            trigger="trg_view",
            table="user_view",
            timing=TriggerTiming.INSTEAD_OF,
            events=[TriggerEvent.INSERT],
        )
        sql, _ = expr.to_sql()
        assert "INSTEAD OF" in sql, "INSTEAD OF timing must be rendered"

    def test_instead_of_unsupported(self):
        """Test INSTEAD OF raises on MariaDB < 10.4."""
        dialect = _TriggerHarness(VERSION_10_3)
        expr = _make_trigger(
            dialect,
            timing=TriggerTiming.INSTEAD_OF,
            events=[TriggerEvent.INSERT],
        )
        with pytest.raises(UnsupportedFeatureError, match="INSTEAD OF"):
            expr.to_sql()

    def test_statement_level_unsupported(self):
        """Test FOR EACH STATEMENT level raises."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, level=TriggerLevel.STATEMENT)
        with pytest.raises(UnsupportedFeatureError, match="FOR EACH STATEMENT"):
            expr.to_sql()

    def test_condition_unsupported(self):
        """Test a WHEN condition raises."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, condition=_BodyStub("NEW.x = 1"))
        with pytest.raises(UnsupportedFeatureError, match="WHEN"):
            expr.to_sql()

    def test_referencing_unsupported(self):
        """Test a REFERENCING clause raises."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, referencing="OLD AS o")
        with pytest.raises(UnsupportedFeatureError, match="REFERENCING"):
            expr.to_sql()

    def test_multiple_events_unsupported(self):
        """Test multiple trigger events raise."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = _make_trigger(dialect, events=[TriggerEvent.INSERT, TriggerEvent.UPDATE])
        with pytest.raises(UnsupportedFeatureError, match="Multiple trigger events"):
            expr.to_sql()


class TestDropTriggerStatement:
    """Tests for DROP TRIGGER statement formatting."""

    def test_minimal(self):
        """Test DROP TRIGGER with only the trigger name."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = DropTriggerExpression(dialect, trigger="trg_update_ts", table="users")
        sql, params = expr.to_sql()
        assert sql == "DROP TRIGGER `trg_update_ts`", "minimal form must include only name"
        assert params == (), "drop trigger has no bind parameters"

    def test_if_exists(self):
        """Test DROP TRIGGER IF EXISTS."""
        dialect = _TriggerHarness(VERSION_10_4)
        expr = DropTriggerExpression(dialect, trigger="trg_update_ts", if_exists=True)
        sql, _ = expr.to_sql()
        assert sql == "DROP TRIGGER IF EXISTS `trg_update_ts`", \
            "IF EXISTS qualifier must be present"