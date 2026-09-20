# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_charset_collation_support.py
"""MariaDB charset / collation / storage-engine capability protocol tests."""

import pytest

from rhosocial.activerecord.backend.impl.mariadb import (
    MariaDBCharset,
    MariaDBDialect,
    MariaDBStorageEngine,
)
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBCreateTableOptions
from rhosocial.activerecord.backend.impl.mariadb.protocols import (
    MariaDBCharsetCollationSupport,
)


def test_dialect_implements_protocol():
    assert isinstance(MariaDBDialect(version=(10, 6, 0)), MariaDBCharsetCollationSupport)


def test_validate_charset_accepts_enum_and_string():
    dialect = MariaDBDialect(version=(10, 6, 0))
    assert dialect.validate_charset_name(MariaDBCharset.UTF8MB4) == "utf8mb4"
    assert dialect.validate_charset_name("UTF8MB4") == "utf8mb4"
    with pytest.raises(ValueError):
        dialect.validate_charset_name("not_a_charset")


def test_validate_storage_engine_normalizes_case():
    dialect = MariaDBDialect(version=(10, 6, 0))
    assert dialect.validate_storage_engine_name(MariaDBStorageEngine.INNODB) == "InnoDB"
    assert dialect.validate_storage_engine_name("aria") == "Aria"
    with pytest.raises(ValueError):
        dialect.validate_storage_engine_name("Evil")


def test_sequence_engine_version_gated():
    assert MariaDBDialect(version=(10, 2, 0)).supports_storage_engine("SEQUENCE") is False
    assert MariaDBDialect(version=(10, 3, 0)).supports_storage_engine("SEQUENCE") is True


def test_table_options_reject_unknown_values():
    dialect = MariaDBDialect(version=(10, 6, 0))
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, engine="Evil")
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, charset="not_a_charset")
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, collate="not_a_collation")
