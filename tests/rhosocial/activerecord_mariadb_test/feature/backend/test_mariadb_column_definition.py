# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_column_definition.py
"""Tests for the MariaDB-specific column definition expressions."""

import pytest

from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBColumnDefinition,
    MariaDBColumnFormat,
    MariaDBColumnOptions,
    MariaDBColumnStorage,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

    return MariaDBDialect((10, 6, 0))


def _column(dialect, **kwargs):
    return MariaDBColumnDefinition(dialect, "name", VarCharType(dialect, length=50), **kwargs)


def test_derives_generic_column_definition():
    assert ColumnDefinition in MariaDBColumnDefinition.__mro__


def test_character_set(dialect):
    sql, _ = _column(dialect, character_set="utf8mb4").to_sql()
    assert sql == "`name` VARCHAR(50) CHARACTER SET `utf8mb4`"


def test_column_format(dialect):
    sql, _ = _column(dialect, column_format=MariaDBColumnFormat.FIXED).to_sql()
    assert sql == "`name` VARCHAR(50) COLUMN_FORMAT FIXED"


def test_storage(dialect):
    sql, _ = _column(dialect, storage=MariaDBColumnStorage.DISK).to_sql()
    assert sql == "`name` VARCHAR(50) STORAGE DISK"


def test_invisible(dialect):
    sql, _ = _column(dialect, invisible=True).to_sql()
    assert sql == "`name` VARCHAR(50) INVISIBLE"


def test_combined_attributes(dialect):
    sql, _ = _column(
        dialect,
        character_set="utf8mb4",
        column_format=MariaDBColumnFormat.DYNAMIC,
        storage=MariaDBColumnStorage.MEMORY,
        invisible=True,
    ).to_sql()
    assert sql == (
        "`name` VARCHAR(50) CHARACTER SET `utf8mb4` "
        "COLUMN_FORMAT DYNAMIC STORAGE MEMORY INVISIBLE"
    )


def test_generic_column_still_renders_on_mariadb(dialect):
    generic = ColumnDefinition(dialect, "name", VarCharType(dialect, length=50), comment="c")
    sql, _ = generic.to_sql()
    assert sql == "`name` VARCHAR(50) COMMENT 'c'"


def test_invalid_column_format_type(dialect):
    with pytest.raises(TypeError, match="MariaDBColumnFormat"):
        _column(dialect, column_format="FIXED")


def test_options_select_mariadb_column_class():
    assert MariaDBColumnOptions(character_set="utf8mb4").column_definition_class() is (
        MariaDBColumnDefinition
    )


def test_options_apply_to(dialect):
    options = MariaDBColumnOptions(
        character_set="utf8mb4", invisible=True, storage=MariaDBColumnStorage.DISK
    )
    col = MariaDBColumnDefinition(dialect, "c", VarCharType(dialect, length=10))
    options.apply_to(col)
    assert col.character_set == "utf8mb4"
    assert col.invisible is True
    assert col.storage is MariaDBColumnStorage.DISK


def test_options_apply_to_rejects_generic_column(dialect):
    options = MariaDBColumnOptions(character_set="utf8mb4")
    generic = ColumnDefinition(dialect, "c", VarCharType(dialect, length=10))
    with pytest.raises(TypeError, match="MariaDBColumnDefinition"):
        options.apply_to(generic)
