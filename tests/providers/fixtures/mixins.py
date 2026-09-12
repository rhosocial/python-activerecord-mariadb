# tests/providers/fixtures/mixins.py
"""DDL expressions for the ``feature/mixins`` table group (MariaDB).

Reference: ``tests/rhosocial/activerecord_mariadb_test/feature/mixins/schema/``.
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
    BooleanType,
    DateTimeType,
    DecimalType,
    IntegerType,
    TextType,
    TinyIntType,
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


def create_combined_articles_table(dialect, table_name: str = "combined_articles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", VarCharType(dialect, 50),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="draft")]),
            ColumnDefinition(dialect, "created_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "updated_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "version", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition(dialect, "deleted_at", DateTimeType(dialect, precision=6),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NULL)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_tasks_table(dialect, table_name: str = "tasks") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "is_completed", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "deleted_at", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NULL)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_timestamped_posts_table(dialect, table_name: str = "timestamped_posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "updated_at", DateTimeType(dialect, precision=6)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_versioned_products_table(dialect, table_name: str = "versioned_products") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "price", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0.0)]),
            ColumnDefinition(dialect, "version", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "combined_articles": create_combined_articles_table,
    "tasks": create_tasks_table,
    "timestamped_posts": create_timestamped_posts_table,
    "versioned_products": create_versioned_products_table,
}
