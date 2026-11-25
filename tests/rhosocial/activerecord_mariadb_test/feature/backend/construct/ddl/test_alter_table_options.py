# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/ddl/test_alter_table_options.py
"""MariaDB ``ALTER TABLE ... <table options>`` rendering.

MariaDB's ``ALTER TABLE`` grammar accepts ``table_options`` as an alter
specification, so an existing table's engine, charset, collation, row format,
comment and auto-increment counter can change in place. Core models table
options for creation only, so the ALTER-time carrier is backend-proprietary.

Pure-construction tests: no database connection is required.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBAlterTableOptionsStatement,
)


@pytest.fixture
def dialect():
    return MariaDBDialect((11, 4, 0))


class TestRendering:
    def test_all_options(self, dialect):
        sql, params = MariaDBAlterTableOptionsStatement(
            dialect,
            "orders",
            engine="InnoDB",
            charset="utf8mb4",
            collate="utf8mb4_general_ci",
            row_format="COMPACT",
            comment="orders table",
            auto_increment=100,
            schema="shop",
        ).to_sql()
        assert sql == (
            "ALTER TABLE `shop`.`orders` ENGINE=InnoDB, DEFAULT CHARSET=utf8mb4, "
            "COLLATE=utf8mb4_general_ci, ROW_FORMAT=COMPACT, AUTO_INCREMENT=100, "
            "COMMENT='orders table'"
        )
        assert params == ()

    def test_engine_only(self, dialect):
        sql, _ = MariaDBAlterTableOptionsStatement(
            dialect, "orders", engine="InnoDB"
        ).to_sql()
        assert sql == "ALTER TABLE `orders` ENGINE=InnoDB"

    def test_comment_only(self, dialect):
        sql, _ = MariaDBAlterTableOptionsStatement(
            dialect, "orders", comment="orders"
        ).to_sql()
        assert sql == "ALTER TABLE `orders` COMMENT='orders'"

    def test_empty_comment_clears(self, dialect):
        sql, _ = MariaDBAlterTableOptionsStatement(
            dialect, "orders", comment=""
        ).to_sql()
        assert sql == "ALTER TABLE `orders` COMMENT=''"

    def test_row_format_accepts_the_enum_spelling(self, dialect):
        sql, _ = MariaDBAlterTableOptionsStatement(
            dialect, "orders", row_format="dynamic"
        ).to_sql()
        assert sql == "ALTER TABLE `orders` ROW_FORMAT=DYNAMIC"

    def test_comment_quotes_are_escaped(self, dialect):
        sql, _ = MariaDBAlterTableOptionsStatement(
            dialect, "orders", comment="O'Brien"
        ).to_sql()
        assert "COMMENT='O''Brien'" in sql


class TestRefusals:
    def test_no_options_is_refused(self, dialect):
        with pytest.raises(ValueError, match="at least one option"):
            MariaDBAlterTableOptionsStatement(dialect, "orders").to_sql()

    def test_blank_table_is_refused(self, dialect):
        with pytest.raises(ValueError, match="non-empty table name"):
            MariaDBAlterTableOptionsStatement(
                dialect, "  ", engine="InnoDB"
            ).to_sql()

    def test_unknown_engine_is_refused(self, dialect):
        with pytest.raises(ValueError):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", engine="NotAStorageEngine"
            ).to_sql()

    def test_unknown_charset_is_refused(self, dialect):
        with pytest.raises(ValueError):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", charset="not-a-charset"
            ).to_sql()

    def test_unknown_collation_is_refused(self, dialect):
        with pytest.raises(ValueError):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", collate="not_a_collation"
            ).to_sql()

    def test_unknown_row_format_is_refused(self, dialect):
        with pytest.raises(ValueError, match="Unsupported MariaDB ROW_FORMAT"):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", row_format="TINY"
            ).to_sql()

    def test_negative_auto_increment_is_refused(self, dialect):
        with pytest.raises(ValueError, match="must be positive"):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", auto_increment=0
            ).to_sql()

    def test_bool_auto_increment_is_refused(self, dialect):
        with pytest.raises(TypeError, match="auto_increment must be an int"):
            MariaDBAlterTableOptionsStatement(
                dialect, "orders", auto_increment=True
            ).to_sql()

    def test_non_string_comment_is_refused(self, dialect):
        with pytest.raises(TypeError, match="comment must be a string"):
            MariaDBAlterTableOptionsStatement(dialect, "orders", comment=1).to_sql()

    def test_wrong_node_kind_is_refused(self, dialect):
        from rhosocial.activerecord.backend.expression.objects import Table

        with pytest.raises(TypeError):
            dialect.format_mariadb_alter_table_options_statement(
                Table(dialect, "orders")
            )
