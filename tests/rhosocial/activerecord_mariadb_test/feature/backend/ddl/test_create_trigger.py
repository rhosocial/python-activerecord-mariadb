# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_create_trigger.py
"""MariaDB ``CREATE TRIGGER`` options, and the fields they need to exist.

``OR REPLACE`` and ``FOLLOWS``/``PRECEDES`` are documented by MariaDB and
rendered by the dialect, so they are real. They are not on core's
``CreateTriggerExpression``, which models SQL:1999 and is shared with dialects
that have neither option -- declaring them there would mean a PostgreSQL
trigger accepting ``or_replace=True`` and silently dropping it.

They therefore live on ``MariaDBCreateTriggerExpression``. That is what lets the
formatter read ``expr.or_replace`` and ``expr.ordering`` directly.

This matters because the alternative was tried: the formatter reached for them
with ``getattr(expr, "or_replace", False)``, so a caller asking for OR REPLACE
got a statement without it and no error. The crash that preceded that was the
honest failure; the silent default was the dishonest one. Neither is correct --
the field has to exist.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements import (
    TriggerEvent,
    TriggerLevel,
    TriggerTiming,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBCreateTriggerExpression,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(11, 4, 0))


def _build(dialect, **kwargs):
    return MariaDBCreateTriggerExpression(
        dialect,
        trigger_name="trg_orders_ai",
        table=TableExpression(dialect, "orders", schema_name=kwargs.get("schema_name")),
        timing=TriggerTiming.AFTER,
        events=[TriggerEvent.INSERT],
        **kwargs,
    )


class TestMariaDBOptionsRender:
    def test_minimal(self, dialect):
        assert _build(dialect).to_sql()[0] == (
            "CREATE TRIGGER `trg_orders_ai` AFTER INSERT ON `orders` "
            "FOR EACH ROW BEGIN END"
        )

    def test_or_replace(self, dialect):
        assert _build(dialect, or_replace=True).to_sql()[0].startswith(
            "CREATE OR REPLACE TRIGGER `trg_orders_ai`"
        )

    @pytest.mark.parametrize(
        "ordering,expected",
        [
            (("FOLLOWS", "trg_orders_bi"), "FOLLOWS `trg_orders_bi`"),
            (("PRECEDES", "trg_orders_bi"), "PRECEDES `trg_orders_bi`"),
        ],
    )
    def test_ordering(self, dialect, ordering, expected):
        sql = _build(dialect, ordering=ordering).to_sql()[0]
        assert expected in sql, sql

    def test_if_not_exists(self, dialect):
        assert _build(dialect, if_not_exists=True).to_sql()[0].startswith(
            "CREATE TRIGGER IF NOT EXISTS `trg_orders_ai`"
        )

    def test_schema_qualifies_trigger_and_table(self, dialect):
        sql = _build(dialect, schema_name="app").to_sql()[0]
        assert "ON `app`.`orders`" in sql, sql
        assert "TRIGGER `app`.`trg_orders_ai`" in sql, sql

    def test_inline_body_carries_its_parameters(self, dialect):
        """A body is an expression, so its placeholders have to travel with it."""
        body = Column(dialect, "n") + Literal(dialect, 1)
        sql, params = _build(dialect, body=body).to_sql()
        assert "BEGIN `n` + %s END" in sql, sql
        assert params == (1,), params


class TestFieldsExist:
    """The contract the formatter relies on, asserted directly.

    If a field were dropped from the expression, every test above would fail
    with an AttributeError pointing at the formatter rather than at the missing
    declaration. These assert the declaration itself, so the failure names the
    cause.
    """

    def test_defaults_are_declared_not_absent(self, dialect):
        expr = _build(dialect)
        assert expr.or_replace is False
        assert expr.ordering is None
        assert expr.body is None

    def test_inherited_fields_are_present(self, dialect):
        expr = _build(dialect)
        assert expr.schema_name is None
        assert expr.if_not_exists is False
        assert expr.trigger_name == "trg_orders_ai"

    def test_formatter_never_negotiates(self, dialect):
        """No probing: the formatter reads attributes it can rely on."""
        import inspect

        from rhosocial.activerecord.backend.impl.mariadb.mixins.trigger import (
            MariaDBTriggerMixin,
        )

        source = inspect.getsource(
            MariaDBTriggerMixin.format_create_trigger_statement
        )
        assert "getattr(" not in source, (
            "the formatter must read expr.or_replace / expr.ordering / "
            "expr.body directly; getattr would silently drop a MariaDB option"
        )
