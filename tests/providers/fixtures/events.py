# tests/providers/fixtures/events.py
"""DDL expressions for the ``feature/events`` table group (MariaDB).

Reference: ``tests/rhosocial/activerecord_mariadb_test/feature/events/schema/``.
"""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    DateTimeType,
    IntegerType,
    TextType,
    VarCharType,
)

from . import _common

_DEFAULT_STORAGE_OPTIONS = {
    "ENGINE": "InnoDB",
    "DEFAULT CHARSET": "utf8mb4",
    "COLLATE": "utf8mb4_unicode_ci",
}


def to_sql(expr: CreateTableExpression):
    return _common.to_mariadb_ddl_sql(expr)


def create_event_tests_table(dialect, table_name: str = "event_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(length=255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", VarCharType(length=50),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="draft")]),
            ColumnDefinition("revision", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition("content", TextType()),
            ColumnDefinition("created_at", DateTimeType(precision=6)),
            ColumnDefinition("updated_at", DateTimeType(precision=6)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_event_tracking_models_table(
    dialect, table_name: str = "event_tracking_models"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", VarCharType(length=255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("view_count", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("last_viewed_at", DateTimeType(precision=6),
                constraints=[ColumnConstraint(ColumnConstraintType.NULL)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "event_tests": create_event_tests_table,
    "event_tracking_models": create_event_tracking_models_table,
}
