# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/ddl/test_auto_increment_ddl.py
"""Regression tests for DDL compilation of auto-increment, standard types,
boolean defaults, and timestamps.

Covers bugs found in rbac cross-backend testing:
- is_auto_increment=True on PRIMARY_KEY must produce AUTO_INCREMENT.
- format_create_table_statement must return a string for all types.
- BooleanType with DEFAULT True must be accepted.
- TimestampType must map to TIMESTAMP.
"""
from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402

import pytest

from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    ColumnDefinition,
    ColumnConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnNotNullConstraint,
    ColumnDefaultConstraint,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType, IntegerType, TextType, TimestampType, VarCharType,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.expression.objects import (
    Table,
)


@pytest.fixture
def dialect():
    return MariaDBDialect()


def _id_column(dialect, data_type, **kwargs):
    """Build an integer auto-increment id column from the backend suggestion."""
    suggested_type, attributes = integer_auto_increment_parts(dialect, data_type)
    return ColumnDefinition(
        dialect, "id", suggested_type,
        constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
        attributes=attributes,
        **kwargs,
    )


def _build_table(dialect):
    return CreateTableStatement(
        dialect=dialect, table=Table(dialect, "test_tbl"),
        columns=[
            _id_column(dialect, IntegerType(dialect)),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "flag", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                             ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, True))]),
            ColumnDefinition(dialect, "code", VarCharType(dialect, 16)),
            ColumnDefinition(dialect, "created_at", TimestampType(dialect)),
        ],
    )


class TestAutoIncrementDDL:

    def test_auto_increment_in_ddl(self, dialect):
        sql, _ = dialect.format_create_table_statement(_build_table(dialect))
        assert "AUTO_INCREMENT" in sql.upper(), f"auto-increment missing: {sql}"

    def test_all_standard_types_compile(self, dialect):
        sql, params = dialect.format_create_table_statement(_build_table(dialect))
        assert isinstance(sql, str)
        assert isinstance(params, tuple)

    def test_boolean_default_true(self, dialect):
        expr = CreateTableStatement(
            dialect=dialect, table=Table(dialect, "bool_test"),
            columns=[
                _id_column(dialect, IntegerType(dialect)),
                ColumnDefinition(dialect, "flag", BooleanType(dialect),
                    constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                                 ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, True))]),
            ],
        )
        sql, _ = dialect.format_create_table_statement(expr)
        assert "TINYINT" in sql.upper()

    def test_timestamp_type(self, dialect):
        expr = CreateTableStatement(
            dialect=dialect, table=Table(dialect, "ts_test"),
            columns=[
                _id_column(dialect, IntegerType(dialect)),
                ColumnDefinition(dialect, "created_at", TimestampType(dialect)),
            ],
        )
        sql, _ = dialect.format_create_table_statement(expr)
        assert "TIMESTAMP" in sql.upper()
