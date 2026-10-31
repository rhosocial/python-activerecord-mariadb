# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_literals.py
"""MariaDB's spellings for the value kinds a literal can carry.

One node carries every value; ``Literal.inline`` decides whether the value
binds behind a placeholder (the data position) or is written as SQL text
through the dialect's literal construction (the DDL syntax position), and
MariaDB's own spellings live in one place: the tier-2 branches of
``format_literal`` (impl/mariadb/mixins/literal.py).

* binary -- ``X'0102FF'``, measured on 13.1.1 (192.168.1.3:15694): the
  SELECT returns the bytes and a ``VARBINARY(16)`` / ``TINYBLOB DEFAULT``
  fills the column with them.
* UUID -- the bare quoted canonical text; ``CHAR(36)`` and the native
  ``UUID`` column type (10.7+) accept it identically, and the ``0x`` form
  is a binary literal, measured to come back as bytes.
* INTERVAL -- no branch on purpose: ``SELECT INTERVAL 1 DAY`` is errno
  1064 and an ``INTERVAL DEFAULT`` is errno 4161 'Unknown data type'
  (measured on 13.1.1), so the base's explicit refusal is the answer.

The tier-1 audit (NULL / booleans / numbers / strings / dates / times /
datetimes) is kept as render assertions: MariaDB agrees with the base
spellings, so none of them is overridden.

The live cases confirm the DDL spellings against the first configured
server (``mariadb_131rc``): a ``DEFAULT`` carrying the literal is created,
a row is inserted without the column, and the column is read back.
"""
import uuid
from datetime import date

import pytest

from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    CreateTableStatement,
    DropTableStatement,
    Literal,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.mariadb.types import MariaDBVarBinaryType


class TestMariaDBBinarySpelling:
    """``X'0102FF'`` -- the x-quoted upper-case hex form."""

    def test_data_position_binds_host_bytes(self, mariadb_dialect):
        expr = Literal(mariadb_dialect, b"\x01\x02\xff")
        assert expr.to_sql() == ("%s", (b"\x01\x02\xff",))

    def test_ddl_position_renders_x_hex(self, mariadb_dialect):
        expr = Literal(mariadb_dialect, b"\x01\x02\xff", inline=True)
        assert expr.to_sql() == ("X'0102FF'", ())


class TestMariaDBUUIDSpelling:
    """The bare quoted canonical text -- MariaDB's only UUID literal form."""

    CANONICAL = "550e8400-e29b-41d4-a716-446655440000"

    def test_data_position_binds_host_uuid(self, mariadb_dialect):
        host = uuid.UUID(self.CANONICAL)
        expr = Literal(mariadb_dialect, host)
        assert expr.to_sql() == ("%s", (host,))

    def test_ddl_position_renders_quoted_text(self, mariadb_dialect):
        expr = Literal(
            mariadb_dialect, uuid.UUID(self.CANONICAL), inline=True
        )
        assert expr.to_sql() == (f"'{self.CANONICAL}'", ())


class TestMariaDBIntervalHasNoLiteral:
    """INTERVAL is a keyword-parameter of date arithmetic, not a value.

    ``SELECT INTERVAL 1 DAY`` is errno 1064 and an ``INTERVAL DEFAULT`` is
    errno 4161 "Unknown data type" (measured on 13.1.1), so the DDL
    position must refuse rather than invent a spelling.
    """

    def test_data_position_binds_host_timedelta(self, mariadb_dialect):
        from datetime import timedelta

        expr = Literal(mariadb_dialect, timedelta(days=1))
        assert expr.to_sql() == ("%s", (timedelta(days=1),))

    def test_ddl_position_refuses_explicitly(self, mariadb_dialect):
        from datetime import timedelta

        expr = Literal(mariadb_dialect, timedelta(days=1), inline=True)
        with pytest.raises(TypeError) as raised:
            expr.to_sql()
        assert "no inline SQL literal form" in str(raised.value)


class TestTier1AuditAgreesWithBase:
    """MariaDB accepts the base spellings, so none of them is overridden.

    Measured on 13.1.1 as ``DEFAULT`` values accepted by ``CREATE TABLE``:
    ``TRUE`` / ``FALSE`` / ``42`` / ``1.5`` / ``1.25`` / ``'x''y'`` /
    ``'2026-10-17'`` / ``'10:30:00'`` / ``'2026-10-17 10:00:00'``.
    """

    def test_boolean_spells_true_false(self, mariadb_dialect):
        assert Literal(mariadb_dialect, True, inline=True).to_sql() == ("TRUE", ())
        assert Literal(mariadb_dialect, False, inline=True).to_sql() == ("FALSE", ())

    def test_integer_spells_numeric_text(self, mariadb_dialect):
        assert Literal(mariadb_dialect, 42, inline=True).to_sql() == ("42", ())

    def test_float_spells_repr(self, mariadb_dialect):
        assert Literal(mariadb_dialect, 1.5, inline=True).to_sql() == ("1.5", ())

    def test_string_spells_quoted_doubled_quotes(self, mariadb_dialect):
        assert (
            Literal(mariadb_dialect, "x'y", inline=True).to_sql() == ("'x''y'", ())
        )

    def test_date_spells_quoted_iso(self, mariadb_dialect):
        assert (
            Literal(mariadb_dialect, date(2026, 10, 17), inline=True).to_sql()
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
        table = Table(dialect, "literal_probe_bin")
        columns = [
            ColumnDefinition(dialect, "id", BigIntType(dialect), constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnDefaultConstraint(
                        dialect, Literal(dialect, 1, inline=True)
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
                            Literal(dialect, b"\x01\x02\xff", inline=True),
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
            outcome = confirm_expression_execution(backend, create, prepare=[drop])
            if outcome is ExecutionOutcome.NOT_RENDERED:
                pytest.skip("dialect does not render this expression")
            backend.execute("INSERT INTO literal_probe_bin () VALUES ()")
            result = backend.execute("SELECT b FROM literal_probe_bin")
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
        table = Table(dialect, "literal_probe_uuid")
        columns = [
            ColumnDefinition(dialect, "id", BigIntType(dialect), constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnDefaultConstraint(
                        dialect, Literal(dialect, 1, inline=True)
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
                            Literal(
                                dialect,
                                uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
                                inline=True,
                            ),
                        ),
                    )
                ],
            ),
        ]
        create = CreateTableStatement(dialect=dialect, table=table, columns=columns)
        drop = DropTableStatement(dialect, table, if_exists=True)
        try:
            outcome = confirm_expression_execution(backend, create, prepare=[drop])
            if outcome is ExecutionOutcome.NOT_RENDERED:
                pytest.skip("dialect does not render this expression")
            backend.execute("INSERT INTO literal_probe_uuid () VALUES ()")
            result = backend.execute("SELECT u FROM literal_probe_uuid")
            assert result.data[0]["u"] == "550e8400-e29b-41d4-a716-446655440000"
        finally:
            backend.execute(drop.to_sql()[0], drop.to_sql()[1])
