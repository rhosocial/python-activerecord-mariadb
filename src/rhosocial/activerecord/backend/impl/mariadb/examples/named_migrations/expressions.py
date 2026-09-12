# src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/expressions.py
"""
DDL named expression functions for MariaDB migration examples.

Each function receives a *dialect* and returns a DDL expression object.
These are the building blocks used by NamedMigration up()/down() methods.
"""

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    DropTableExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBIntType,
    MariaDBTextType,
)


def create_users_table(dialect):
    """CREATE TABLE users (id INT PRIMARY KEY AUTO_INCREMENT, name TEXT, email TEXT)."""
    return CreateTableExpression(
        dialect,
        table="users",
        columns=[
            ColumnDefinition(
                dialect,
                "id",
                MariaDBIntType(dialect),
                constraints=[
                    ColumnConstraint(
                        dialect,
                        ColumnConstraintType.PRIMARY_KEY,
                        is_auto_increment=True,
                    ),
                ],
            ),
            ColumnDefinition(dialect, "name", MariaDBTextType(dialect)),
            ColumnDefinition(dialect, "email", MariaDBTextType(dialect)),
        ],
    )


def drop_users_table(dialect):
    """DROP TABLE IF EXISTS users."""
    return DropTableExpression(dialect, table="users", if_exists=True)


def create_posts_table(dialect):
    """CREATE TABLE posts (id INT PRIMARY KEY AUTO_INCREMENT, title TEXT, user_id INT)."""
    return CreateTableExpression(
        dialect,
        table="posts",
        columns=[
            ColumnDefinition(
                dialect,
                "id",
                MariaDBIntType(dialect),
                constraints=[
                    ColumnConstraint(
                        dialect,
                        ColumnConstraintType.PRIMARY_KEY,
                        is_auto_increment=True,
                    ),
                ],
            ),
            ColumnDefinition(dialect, "title", MariaDBTextType(dialect)),
            ColumnDefinition(dialect, "user_id", MariaDBIntType(dialect)),
        ],
    )


def drop_posts_table(dialect):
    """DROP TABLE IF EXISTS posts."""
    return DropTableExpression(dialect, table="posts", if_exists=True)


def create_custom_table(dialect, table_name: str = "custom_table"):
    """CREATE TABLE <table_name> (id INT PRIMARY KEY AUTO_INCREMENT, value TEXT).

    This expression accepts an extra ``table_name`` parameter, allowing
    the migration to control the target table name at runtime.
    """
    return CreateTableExpression(
        dialect,
        table=table_name,
        columns=[
            ColumnDefinition(
                dialect,
                "id",
                MariaDBIntType(dialect),
                constraints=[
                    ColumnConstraint(
                        dialect,
                        ColumnConstraintType.PRIMARY_KEY,
                        is_auto_increment=True,
                    ),
                ],
            ),
            ColumnDefinition(dialect, "value", MariaDBTextType(dialect)),
        ],
    )


def drop_custom_table(dialect, table_name: str = "custom_table"):
    """DROP TABLE IF EXISTS <table_name>."""
    return DropTableExpression(dialect, table=table_name, if_exists=True)
