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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.UNIQUE)]),
            ColumnDefinition("email", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.UNIQUE)]),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("balance", FloatType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0.0)]),
            ColumnDefinition("is_active", BooleanType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_type_cases_table(dialect, table_name: str = "type_cases") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", CharType(36),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("username", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("tiny_int", TextType()),
            ColumnDefinition("small_int", TextType()),
            ColumnDefinition("big_int", TextType()),
            ColumnDefinition("float_val", TextType()),
            ColumnDefinition("double_val", TextType()),
            ColumnDefinition("decimal_val", TextType()),
            ColumnDefinition("char_val", TextType()),
            ColumnDefinition("varchar_val", TextType()),
            ColumnDefinition("text_val", TextType()),
            ColumnDefinition("date_val", TextType()),
            ColumnDefinition("time_val", TextType()),
            ColumnDefinition("timestamp_val", TextType()),
            ColumnDefinition("blob_val", TextType()),
            ColumnDefinition("json_val", TextType()),
            ColumnDefinition("array_val", TextType()),
            ColumnDefinition("is_active", TextType()),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_type_tests_table(dialect, table_name: str = "type_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", CharType(36),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("string_field", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="test string")]),
            ColumnDefinition("int_field", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=42)]),
            ColumnDefinition("float_field", FloatType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=3.14)]),
            ColumnDefinition("decimal_field", DoubleType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=10.99)]),
            ColumnDefinition("bool_field", TinyIntType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition("datetime_field", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("json_field", JsonType()),
            ColumnDefinition("nullable_field", VarCharType(255)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_validated_field_users_table(dialect, table_name: str = "validated_field_users") -> CreateTableExpression:
    status_enum = MariaDBEnumType(['active', 'inactive', 'banned', 'pending', 'suspended'])
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("balance", DecimalType(precision=10, scale=2)),
            ColumnDefinition("credit_score", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", status_enum,
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="active")]),
            ColumnDefinition("is_active", TinyIntType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1)]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_validated_users_table(dialect, table_name: str = "validated_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", VarCharType(50),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("code", VarCharType(32)),
            ColumnDefinition("quantity", IntegerType()),
            ColumnDefinition("step_count", IntegerType()),
            ColumnDefinition("price", DecimalType(precision=10, scale=2)),
            ColumnDefinition("start_at", DateTimeType()),
            ColumnDefinition("end_at", DateTimeType()),
            ColumnDefinition("status", VarCharType(32)),
            ColumnDefinition("normalized_name", VarCharType(50)),
            ColumnDefinition("created_token", VarCharType(255)),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_bulk_users_table(dialect, table_name: str = "bulk_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("email", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("author", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("title", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType()),
            ColumnDefinition("published_at", DateTimeType(precision=6)),
            ColumnDefinition("published", BooleanType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("created_at", DateTimeType(precision=6)),
            ColumnDefinition("updated_at", DateTimeType(precision=6)),
        ],
        indexes=[IndexDefinition(name="idx_author", columns=["author"])],
        table_constraints=[
            ForeignKeyConstraint(columns=["author"], foreign_key_table="users", foreign_key_columns=["id"],
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("post_ref", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("author", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("text", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("created_at", DateTimeType(precision=6),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("updated_at", DateTimeType(precision=6)),
            ColumnDefinition("approved", BooleanType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
        ],
        indexes=[
            IndexDefinition(name="idx_post_ref", columns=["post_ref"]),
            IndexDefinition(name="idx_author", columns=["author"]),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["post_ref"], foreign_key_table="posts", foreign_key_columns=["id"],
                on_delete=_CASCADE),
            ForeignKeyConstraint(columns=["author"], foreign_key_table="users", foreign_key_columns=["id"],
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("item_total", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("remarks", IntegerType()),
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("tags", TextType()),
            ColumnDefinition("meta", TextType()),
            ColumnDefinition("description", TextType()),
            ColumnDefinition("status", TextType()),
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("optional_name", VarCharType(255)),
            ColumnDefinition("optional_age", IntegerType()),
            ColumnDefinition("last_login", TextType()),
            ColumnDefinition("is_premium", BooleanType()),
            ColumnDefinition("unsupported_union", VarCharType(255)),
            ColumnDefinition("custom_bool", VarCharType(3)),
            ColumnDefinition("optional_custom_bool", VarCharType(3)),
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
            ColumnDefinition("order_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1)]),
            ColumnDefinition("unit_price", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[
            TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY,
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
            ColumnDefinition("store_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("batch_id", VarCharType(64),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("stock", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL),
                             ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
        ],
        table_constraints=[
            TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY,
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("total", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        storage_options=dict(_DEFAULT_STORAGE_OPTIONS),
    )


def create_product_table(dialect, table_name: str = "product") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("price", FloatType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
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
