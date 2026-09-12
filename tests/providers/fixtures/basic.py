# tests/providers/fixtures/basic.py
"""DDL expressions for the ``feature/basic`` table group (MariaDB).

Each factory builds a :class:`CreateTableExpression` whose generated MariaDB
DDL is semantically equivalent to the reference ``.sql`` schema files under
``tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/``.
"""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
    ReferentialAction,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    CharType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    JsonType,
    TextType,
    TinyIntType,
    VarCharType,
)

from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBEnumType

from . import _common

_DEFAULT_STORAGE_OPTIONS = {
    "ENGINE": "InnoDB",
    "DEFAULT CHARSET": "utf8mb4",
    "COLLATE": "utf8mb4_unicode_ci",
}

_CASCADE = ReferentialAction.CASCADE


def to_sql(expr: CreateTableExpression):
    """Route a CreateTableExpression through the canonical MariaDB DDL post-processor."""
    return _common.to_mariadb_ddl_sql(expr)


def create_users_table(dialect, table_name: str = "users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.UNIQUE)]),
            ColumnDefinition(dialect, "email", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.UNIQUE)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect)),
            ColumnDefinition(dialect, "balance", FloatType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0.0)]),
            ColumnDefinition(dialect, "is_active", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_type_cases_table(dialect, table_name: str = "type_cases") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", CharType(dialect, 36),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "username", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "tiny_int", TextType(dialect)),
            ColumnDefinition(dialect, "small_int", TextType(dialect)),
            ColumnDefinition(dialect, "big_int", TextType(dialect)),
            ColumnDefinition(dialect, "float_val", TextType(dialect)),
            ColumnDefinition(dialect, "double_val", TextType(dialect)),
            ColumnDefinition(dialect, "decimal_val", TextType(dialect)),
            ColumnDefinition(dialect, "char_val", TextType(dialect)),
            ColumnDefinition(dialect, "varchar_val", TextType(dialect)),
            ColumnDefinition(dialect, "text_val", TextType(dialect)),
            ColumnDefinition(dialect, "date_val", TextType(dialect)),
            ColumnDefinition(dialect, "time_val", TextType(dialect)),
            ColumnDefinition(dialect, "timestamp_val", TextType(dialect)),
            ColumnDefinition(dialect, "blob_val", TextType(dialect)),
            ColumnDefinition(dialect, "json_val", TextType(dialect)),
            ColumnDefinition(dialect, "array_val", TextType(dialect)),
            ColumnDefinition(dialect, "is_active", TextType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_type_tests_table(dialect, table_name: str = "type_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", CharType(dialect, 36),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "string_field", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="test string")]),
            ColumnDefinition(dialect, "int_field", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=42)]),
            ColumnDefinition(dialect, "float_field", FloatType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=3.14)]),
            ColumnDefinition(dialect, "decimal_field", DoubleType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=10.99)]),
            ColumnDefinition(dialect, "bool_field", TinyIntType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition(dialect, "datetime_field", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "json_field", JsonType(dialect)),
            ColumnDefinition(dialect, "nullable_field", VarCharType(dialect, 255)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_validated_field_users_table(dialect, table_name: str = "validated_field_users") -> CreateTableExpression:
    status_enum = MariaDBEnumType(dialect, ['active', 'inactive', 'banned', 'pending', 'suspended'])
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect)),
            ColumnDefinition(dialect, "balance", DecimalType(dialect, precision=10, scale=2)),
            ColumnDefinition(dialect, "credit_score", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", status_enum,
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="active")]),
            ColumnDefinition(dialect, "is_active", TinyIntType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_validated_users_table(dialect, table_name: str = "validated_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", VarCharType(dialect, 50),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_pydantic_validated_models_table(
    dialect, table_name: str = "pydantic_validated_models"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "code", VarCharType(dialect, 32)),
            ColumnDefinition(dialect, "quantity", IntegerType(dialect)),
            ColumnDefinition(dialect, "step_count", IntegerType(dialect)),
            ColumnDefinition(dialect, "price", DecimalType(dialect, precision=10, scale=2)),
            ColumnDefinition(dialect, "start_at", DateTimeType(dialect)),
            ColumnDefinition(dialect, "end_at", DateTimeType(dialect)),
            ColumnDefinition(dialect, "status", VarCharType(dialect, 32)),
            ColumnDefinition(dialect, "normalized_name", VarCharType(dialect, 50)),
            ColumnDefinition(dialect, "created_token", VarCharType(dialect, 255)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_bulk_users_table(dialect, table_name: str = "bulk_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "email", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "author", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "title", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect)),
            ColumnDefinition(dialect, "published_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "published", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "created_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "updated_at", DateTimeType(dialect, precision=6)),
        ],
        indexes=[IndexDefinition(dialect, name="idx_author", columns=["author"])],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["author"], foreign_key_table="users", foreign_key_columns=["id"],
                on_delete=_CASCADE),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "post_ref", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "author", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "text", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", DateTimeType(dialect, precision=6),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "updated_at", DateTimeType(dialect, precision=6)),
            ColumnDefinition(dialect, "approved", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
        ],
        indexes=[
            IndexDefinition(dialect, name="idx_post_ref", columns=["post_ref"]),
            IndexDefinition(dialect, name="idx_author", columns=["author"]),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["post_ref"], foreign_key_table="posts", foreign_key_columns=["id"],
                on_delete=_CASCADE),
            ForeignKeyConstraint(dialect, columns=["author"], foreign_key_table="users", foreign_key_columns=["id"],
                on_delete=_CASCADE),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_column_mapping_items_table(
    dialect, table_name: str = "column_mapping_items"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "item_total", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "remarks", IntegerType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_mixed_annotation_items_table(
    dialect, table_name: str = "mixed_annotation_items"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "tags", TextType(dialect)),
            ColumnDefinition(dialect, "meta", TextType(dialect)),
            ColumnDefinition(dialect, "description", TextType(dialect)),
            ColumnDefinition(dialect, "status", TextType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_type_adapter_tests_table(
    dialect, table_name: str = "type_adapter_tests"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "optional_name", VarCharType(dialect, 255)),
            ColumnDefinition(dialect, "optional_age", IntegerType(dialect)),
            ColumnDefinition(dialect, "last_login", TextType(dialect)),
            ColumnDefinition(dialect, "is_premium", BooleanType(dialect)),
            ColumnDefinition(dialect, "unsupported_union", VarCharType(dialect, 255)),
            ColumnDefinition(dialect, "custom_bool", VarCharType(dialect, 3)),
            ColumnDefinition(dialect, "optional_custom_bool", VarCharType(dialect, 3)),
        ],
    )


def create_composite_pk_order_items_table(
    dialect, table_name: str = "order_items"
) -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "order_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition(dialect, "unit_price", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[
            TableConstraint(dialect, constraint_type=TableConstraintType.PRIMARY_KEY,
                columns=["order_id", "product_id"]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_store_inventory_table(dialect, table_name: str = "store_inventory") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "store_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "batch_id", VarCharType(dialect, 64),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "stock", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
        ],
        table_constraints=[
            TableConstraint(dialect, constraint_type=TableConstraintType.PRIMARY_KEY,
                columns=["store_id", "product_id", "batch_id"]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_orders_table(dialect, table_name: str = "orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "total", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_product_table(dialect, table_name: str = "product") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "price", FloatType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
        ],
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "users": create_users_table,
    "type_cases": create_type_cases_table,
    "type_tests": create_type_tests_table,
    "validated_field_users": create_validated_field_users_table,
    "validated_users": create_validated_users_table,
    "pydantic_validated_models": create_pydantic_validated_models_table,
    "bulk_users": create_bulk_users_table,
    "posts": create_posts_table,
    "comments": create_comments_table,
    "column_mapping_items": create_column_mapping_items_table,
    "mixed_annotation_items": create_mixed_annotation_items_table,
    "type_adapter_tests": create_type_adapter_tests_table,
    "order_items": create_composite_pk_order_items_table,
    "store_inventory": create_store_inventory_table,
    "orders": create_orders_table,
    "product": create_product_table,
}
