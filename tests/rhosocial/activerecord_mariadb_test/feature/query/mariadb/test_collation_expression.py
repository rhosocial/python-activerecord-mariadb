# tests/rhosocial/activerecord_mariadb_test/feature/query/mariadb/test_collation_expression.py
"""
Tests for expression-level COLLATE support on MariaDB.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.collation import CollationName
from rhosocial.activerecord.backend.impl.mariadb import MariaDBCollation, MariaDBDialect


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


@pytest.fixture
def collation_table(mariadb_backend):
    mariadb_backend.execute("DROP TABLE IF EXISTS test_collation_expression")
    mariadb_backend.execute("""
        CREATE TABLE test_collation_expression (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    mariadb_backend.execute("""
        INSERT INTO test_collation_expression (name)
        VALUES ('Alice'), ('alice'), ('Bob')
    """)
    yield "test_collation_expression"
    mariadb_backend.execute("DROP TABLE IF EXISTS test_collation_expression")


class TestMariaDBCollationExpression:
    def test_column_collate_generates_sql(self, dialect):
        expr = Column(dialect, "name", table="users").collate(MariaDBCollation.UTF8MB4_BIN)

        sql, params = expr.to_sql()

        assert sql == "`users`.`name` COLLATE utf8mb4_bin"
        assert params == ()

    def test_literal_collate_preserves_parameter_binding(self, dialect):
        expr = Literal(dialect, "Alice").collate(MariaDBCollation.UTF8MB4_UNICODE_CI)

        sql, params = expr.to_sql()

        assert sql == "%s COLLATE utf8mb4_unicode_ci"
        assert params == ("Alice",)

    def test_rejects_schema_qualified_collation(self, dialect):
        expr = Column(dialect, "name").collate(CollationName("utf8mb4_bin", schema="public"))

        with pytest.raises(Exception, match="schema-qualified or keyword COLLATE"):
            expr.to_sql()

    def test_rejects_unsupported_collation(self, dialect):
        expr = Column(dialect, "name").collate("unknown_ci")

        with pytest.raises(ValueError, match="Unsupported MariaDB collation"):
            expr.to_sql()

    def test_collate_executes_case_sensitive_match(self, mariadb_backend, collation_table):
        expr = Column(mariadb_backend.dialect, "name", table=collation_table).collate(
            MariaDBCollation.UTF8MB4_BIN
        )
        sql, params = expr.to_sql()

        rows = mariadb_backend.fetch_all(
            f"SELECT name FROM `{collation_table}` WHERE {sql} = %s ORDER BY id",
            (*params, "Alice"),
        )

        assert [row["name"] for row in rows] == ["Alice"]

    def test_collate_executes_case_insensitive_match(self, mariadb_backend, collation_table):
        expr = Column(mariadb_backend.dialect, "name", table=collation_table).collate(
            MariaDBCollation.UTF8MB4_UNICODE_CI
        )
        sql, params = expr.to_sql()

        rows = mariadb_backend.fetch_all(
            f"SELECT name FROM `{collation_table}` WHERE {sql} = %s ORDER BY id",
            (*params, "Alice"),
        )

        assert [row["name"] for row in rows] == ["Alice", "alice"]
