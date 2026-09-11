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
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(255, dialect=dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", VarCharType(50, dialect=dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="draft")]),
            ColumnDefinition(dialect, "revision", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition(dialect, "content", TextType(dialect)),
            ColumnDefinition(dialect, "created_at", DateTimeType(precision=6, dialect=dialect)),
            ColumnDefinition(dialect, "updated_at", DateTimeType(precision=6, dialect=dialect)),
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
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", VarCharType(255, dialect=dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "view_count", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "last_viewed_at", DateTimeType(precision=6, dialect=dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NULL)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "event_tests": create_event_tests_table,
    "event_tracking_models": create_event_tracking_models_table,
}
