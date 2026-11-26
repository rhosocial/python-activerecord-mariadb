# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/charset_collation/test_mariadb_charset_collation_support.py
"""MariaDB charset / collation / storage-engine capability protocol tests."""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.mixins import MariaDBCharset, MariaDBStorageEngine
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
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
    assert MariaDBDialect(version=(10, 2, 0)).supports_storage_engine_sequence() is False
    assert MariaDBDialect(version=(10, 3, 0)).supports_storage_engine_sequence() is True


def test_storage_engine_switches_match_the_whitelist():
    """Every switch answers from the same whitelist the validator enforces."""
    dialect = MariaDBDialect(version=(10, 6, 0))
    engines = dialect.supported_storage_engines()

    declared = {
        "innodb": "InnoDB",
        "myisam": "MyISAM",
        "aria": "Aria",
        "memory": "MEMORY",
        "csv": "CSV",
        "archive": "ARCHIVE",
        "blackhole": "BLACKHOLE",
        "mrg_myisam": "MRG_MyISAM",
        "sequence": "SEQUENCE",
        "connect": "CONNECT",
        "federated": "FEDERATED",
        "performance_schema": "PERFORMANCE_SCHEMA",
    }
    for switch, engine in declared.items():
        assert getattr(dialect, f"supports_storage_engine_{switch}")() is True, switch
        assert engine in engines, switch


def test_engines_outside_the_whitelist_are_refused_by_both_sides():
    """NDB/NDBCLUSTER/EXAMPLE are not MariaDB engines; TEMPORARY is not an engine."""
    dialect = MariaDBDialect(version=(10, 6, 0))
    for switch in ("ndb", "ndbcluster", "example", "temporary"):
        assert getattr(dialect, f"supports_storage_engine_{switch}")() is False, switch


def test_text_encoding_suggestion():
    suggestion = MariaDBDialect(version=(10, 6, 0)).suggest_text_encoding()
    assert suggestion.charset == "utf8mb4"
    assert suggestion.collation == "utf8mb4_general_ci"
    assert suggestion.reason


def test_storage_engine_suggestion():
    suggestion = MariaDBDialect(version=(10, 6, 0)).suggest_storage_engine()
    assert suggestion.engine == "InnoDB"
    assert suggestion.transactional is True
    assert suggestion.reason


def test_table_options_reject_unknown_values():
    dialect = MariaDBDialect(version=(10, 6, 0))
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, engine="Evil")
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, charset="not_a_charset")
    with pytest.raises(ValueError):
        MariaDBCreateTableOptions(dialect, collate="not_a_collation")
