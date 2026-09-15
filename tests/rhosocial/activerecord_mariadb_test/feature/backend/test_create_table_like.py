# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_create_table_like.py
"""
MariaDB CREATE TABLE ... LIKE syntax tests.

This module tests the MariaDB-specific LIKE syntax for CREATE TABLE statements.
The LIKE form is modelled by CreateTableLikeExpression and rendered by the
dialect's ``format_create_table_like_statement`` (MariaDB inherits the generic
TableMixin implementation).
"""

from rhosocial.activerecord.backend.expression import CreateTableLikeExpression
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestMariaDBCreateTableLike:
    """Tests for MariaDB CREATE TABLE ... LIKE syntax."""

    def test_basic_like_syntax(self):
        """Test basic CREATE TABLE ... LIKE syntax."""
        dialect = MariaDBDialect()
        expr = CreateTableLikeExpression(dialect, table="users_copy", like_table="users")
        sql, params = expr.to_sql()

        assert sql == "CREATE TABLE `users_copy` LIKE `users`"
        assert params == ()

    def test_like_with_if_not_exists(self):
        """Test CREATE TABLE ... LIKE with IF NOT EXISTS."""
        dialect = MariaDBDialect()
        expr = CreateTableLikeExpression(
            dialect, table="users_copy", like_table="users", if_not_exists=True
        )
        sql, params = expr.to_sql()

        assert sql == "CREATE TABLE IF NOT EXISTS `users_copy` LIKE `users`"
        assert params == ()

    def test_like_with_temporary(self):
        """Test CREATE TEMPORARY TABLE ... LIKE."""
        dialect = MariaDBDialect()
        expr = CreateTableLikeExpression(
            dialect, table="temp_users", like_table="users", temporary=True
        )
        sql, params = expr.to_sql()

        assert sql == "CREATE TEMPORARY TABLE `temp_users` LIKE `users`"
        assert params == ()

    def test_like_with_schema_qualified_table(self):
        """Test CREATE TABLE ... LIKE with schema-qualified source table."""
        dialect = MariaDBDialect()
        expr = CreateTableLikeExpression(
            dialect, table="users_copy", like_table=("production", "users")
        )
        sql, params = expr.to_sql()

        assert sql == "CREATE TABLE `users_copy` LIKE `production`.`users`"
        assert params == ()

    def test_like_with_temporary_and_if_not_exists(self):
        """Test CREATE TEMPORARY TABLE ... LIKE with IF NOT EXISTS."""
        dialect = MariaDBDialect()
        expr = CreateTableLikeExpression(
            dialect,
            table="temp_users_copy",
            like_table=("test_db", "users"),
            temporary=True,
            if_not_exists=True,
        )
        sql, params = expr.to_sql()

        assert sql == (
            "CREATE TEMPORARY TABLE IF NOT EXISTS `temp_users_copy` "
            "LIKE `test_db`.`users`"
        )
        assert params == ()

    def test_supports_create_table_like(self):
        """MariaDB advertises CREATE TABLE ... LIKE support."""
        dialect = MariaDBDialect()
        assert dialect.supports_create_table_like() is True
