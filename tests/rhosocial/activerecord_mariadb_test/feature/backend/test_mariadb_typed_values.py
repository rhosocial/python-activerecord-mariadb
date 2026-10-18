# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_typed_values.py
"""MariaDB's spellings for the typed value nodes.

Every overridden kind is asserted in both positions the class-level
``inline_params`` strategy distinguishes:

* **data position** (the plain node, ``inline_params = False``): the
  placeholder plus the host value -- the driver binds ``bytes`` and the
  canonical forms natively;
* **DDL syntax position** (the class that owns the position declares
  ``inline_params = True``, exactly as core's ``DdlLiteral`` does for
  ``Literal``): the exact inline literal text.

INTERVAL has no literal form on MariaDB, so its DDL position must fail
explicitly with the base's :class:`NotImplementedError` -- that refusal
is the documented answer, not a missing feature of this test.

The tier-1 audit (NULL / booleans / numbers / strings / date-times) is
kept as render assertions: MariaDB agrees with the base spellings, so
none of them is overridden, and these assertions pin that agreement.

The live cases confirm the DDL spellings against the first configured
server (``mariadb_131rc``, 13.1.1 at 192.168.1.3:15694): a ``DEFAULT``
carrying the literal is created, a row is inserted without the column,
and the column is read back. Measured evidence for the refusals the
docstrings cite lives in ``impl/mariadb/mixins/typed_value.py``.
"""
import uuid
from datetime import date, timedelta

import pytest

from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    CreateTableStatement,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.values import (
    BinaryValue,
    BooleanValue,
    DateValue,
    IntegerValue,
    IntervalValue,
    StringValue,
    UUIDValue,
)
from rhosocial.activerecord.backend.impl.mariadb.types import MariaDBVarBinaryType

# ---------------------------------------------------------------------------
# DDL-position carriers
#
# Whether a value inlines is a decision of its class (spec 4.4), so the DDL
# position is exercised through a subclass that declares the inline strategy
# -- the same relationship ``DdlLiteral`` has to ``Literal`` in core. No
# instance flag is flipped anywhere.
# ---------------------------------------------------------------------------


class _DdlBinaryValue(BinaryValue):
    """A binary value at a DDL syntax position."""

    inline_params = True


class _DdlUUIDValue(UUIDValue):
    """A UUID value at a DDL syntax position."""

    inline_params = True


class _DdlIntervalValue(IntervalValue):
    """An interval value at a DDL syntax position (none exists here)."""

    inline_params = True


class _DdlBooleanValue(BooleanValue):
    """A boolean value at a DDL syntax position."""

    inline_params = True


class _DdlIntegerValue(IntegerValue):
    """An integer value at a DDL syntax position."""

    inline_params = True


class _DdlStringValue(StringValue):
    """A string value at a DDL syntax position."""

    inline_params = True


class _DdlDateValue(DateValue):
    """A date value at a DDL syntax position."""

    inline_params = True


class TestMariaDBBinaryValueSpelling:
    """``X'0102FF'`` -- the x-quoted upper-case hex form."""

    def test_data_position_binds_host_bytes(self, mariadb_dialect):
        expr = BinaryValue(mariadb_dialect, b"\x01\x02\xff")
        assert expr.to_sql() == ("%s", (b"\x01\x02\xff",))

    def test_ddl_position_renders_x_hex(self, mariadb_dialect):
        expr = _DdlBinaryValue(mariadb_dialect, b"\x01\x02\xff")
        assert expr.to_sql() == ("X'0102FF'", ())


class TestMariaDBUUIDValueSpelling:
    """The bare quoted canonical text -- MariaDB's only UUID literal form."""

    CANONICAL = "550e8400-e29b-41d4-a716-446655440000"

    def test_data_position_binds_host_uuid(self, mariadb_dialect):
        host = uuid.UUID(self.CANONICAL)
        expr = UUIDValue(mariadb_dialect, host)
        assert expr.to_sql() == ("%s", (host,))

    def test_ddl_position_renders_quoted_text(self, mariadb_dialect):
        expr = _DdlUUIDValue(mariadb_dialect, uuid.UUID(self.CANONICAL))
        assert expr.to_sql() == (f"'{self.CANONICAL}'", ())


class TestMariaDBIntervalValueHasNoLiteral:
    """INTERVAL is a keyword-parameter of date arithmetic, not a value.

    ``SELECT INTERVAL 1 DAY`` is errno 1064 and an ``INTERVAL DEFAULT`` is
    errno 4161 "Unknown data type" (measured on 13.1.1), so the DDL
    position must refuse rather than invent a spelling.
    """

    def test_data_position_binds_host_timedelta(self, mariadb_dialect):
        expr = IntervalValue(mariadb_dialect, timedelta(days=1))
        assert expr.to_sql() == ("%s", (timedelta(days=1),))

    def test_ddl_position_refuses_explicitly(self, mariadb_dialect):
        expr = _DdlIntervalValue(mariadb_dialect, timedelta(days=1))
        with pytest.raises(NotImplementedError) as raised:
            expr.to_sql()
        assert "does not implement INTERVAL literals" in str(raised.value)
        assert "format_interval_value" in str(raised.value)


class TestTier1AuditAgreesWithBase:
    """MariaDB accepts the base spellings, so none of them is overridden.

    Measured on 13.1.1 as ``DEFAULT`` values accepted by ``CREATE TABLE``:
    ``TRUE`` / ``FALSE`` / ``42`` / ``1.5`` / ``1.25`` / ``'x''y'`` /
    ``'2026-10-17'`` / ``'10:30:00'`` / ``'2026-10-17 10:00:00'``.
    """

    def test_boolean_spells_true_false(self, mariadb_dialect):
        assert _DdlBooleanValue(mariadb_dialect, True).to_sql() == ("TRUE", ())
        assert _DdlBooleanValue(mariadb_dialect, False).to_sql() == ("FALSE", ())

    def test_integer_spells_numeric_text(self, mariadb_dialect):
        assert _DdlIntegerValue(mariadb_dialect, 42).to_sql() == ("42", ())

    def test_string_spells_quoted_doubled_quotes(self, mariadb_dialect):
        assert _DdlStringValue(mariadb_dialect, "x'y").to_sql() == ("'x''y'", ())

    def test_date_spells_quoted_iso(self, mariadb_dialect):
        assert (
            _DdlDateValue(mariadb_dialect, date(2026, 10, 17)).to_sql()
            == ("'2026-10-17'", ())
        )


class TestLiveDefaultRoundTrip:
    """The DDL spellings against the live first scenario server.

    A sentinel first: a deliberately invalid statement must classify as
    REJECTED, or a null result could be read as acceptance.
    """

    def test_sentinel_rejection_is_visible(self, mariadb_backend_single):
        from rhosocial.activerecord.backend.expression.execution_testing import (
            ExecutionOutcome,
            classify_execution,
        )

        assert (
            classify_execution(mariadb_backend_single, "THIS IS NOT SQL")
            is ExecutionOutcome.REJECTED
        )

    def test_binary_default_reads_back_as_bytes(self, mariadb_backend_single):
        from rhosocial.activerecord.backend.expression.execution_testing import (
            ExecutionOutcome,
            confirm_expression_execution,
        )

        backend = mariadb_backend_single
        dialect = backend.dialect
        table = Table(dialect, "typed_values_probe_bin")
        columns = [
            ColumnDefinition(dialect, "id", BigIntType(dialect), constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnDefaultConstraint(
                        dialect, _DdlIntegerValue(dialect, 1)
                    ),
                )
            ]),
            ColumnDefinition(
                dialect,
                "b",
                MariaDBVarBinaryType(dialect, 16),
                constraints=[
                    ColumnConstraint(
                        dialect,
                        branch=ColumnDefaultConstraint(
                            dialect,
                            _DdlBinaryValue(dialect, b"\x01\x02\xff"),
                        ),
                    )
                ],
            ),
        ]
        create = CreateTableStatement(dialect=dialect, table=table, columns=columns)
        drop = DropTableStatement(dialect, table, if_exists=True)
        # The confirmation helper's teardown drops in a finally, which is
        # right for a pure accept/refuse verdict but not for a round trip:
        # the table has to outlive the CREATE, so the drop is ours to run.
        try:
            outcome = confirm_expression_execution(
                backend, create, prepare=[drop]
            )
            if outcome is ExecutionOutcome.NOT_RENDERED:
                pytest.skip("dialect does not render this expression")
            backend.execute("INSERT INTO typed_values_probe_bin () VALUES ()")
            result = backend.execute("SELECT b FROM typed_values_probe_bin")
            assert result.data[0]["b"] == b"\x01\x02\xff"
        finally:
            backend.execute(drop.to_sql()[0], drop.to_sql()[1])

    def test_uuid_default_reads_back_as_text(self, mariadb_backend_single):
        from rhosocial.activerecord.backend.expression.execution_testing import (
            ExecutionOutcome,
            confirm_expression_execution,
        )

        backend = mariadb_backend_single
        dialect = backend.dialect
        table = Table(dialect, "typed_values_probe_uuid")
        columns = [
            ColumnDefinition(dialect, "id", BigIntType(dialect), constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnDefaultConstraint(
                        dialect, _DdlIntegerValue(dialect, 1)
                    ),
                )
            ]),
            ColumnDefinition(
                dialect,
                "u",
                VarCharType(dialect, 36),
                constraints=[
                    ColumnConstraint(
                        dialect,
                        branch=ColumnDefaultConstraint(
                            dialect,
                            _DdlUUIDValue(
                                dialect,
                                uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
                            ),
                        ),
                    )
                ],
            ),
        ]
        create = CreateTableStatement(dialect=dialect, table=table, columns=columns)
        drop = DropTableStatement(dialect, table, if_exists=True)
        try:
            outcome = confirm_expression_execution(
                backend, create, prepare=[drop]
            )
            if outcome is ExecutionOutcome.NOT_RENDERED:
                pytest.skip("dialect does not render this expression")
            backend.execute("INSERT INTO typed_values_probe_uuid () VALUES ()")
            result = backend.execute("SELECT u FROM typed_values_probe_uuid")
            assert result.data[0]["u"] == "550e8400-e29b-41d4-a716-446655440000"
        finally:
            backend.execute(drop.to_sql()[0], drop.to_sql()[1])
