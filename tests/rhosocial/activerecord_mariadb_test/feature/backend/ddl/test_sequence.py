# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_sequence.py
"""MariaDB SEQUENCE object formatting tests.

This module covers the ``MariaDBSequenceMixin``: version gating for
SEQUENCE support (MariaDB 10.3+) and the pure SQL formatters for
NEXTVAL / CURRVAL / SETVAL and the CREATE / DROP / ALTER SEQUENCE
statements.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.sequence import MariaDBSequenceMixin

VERSION_SUPPORTED = (10, 3, 0)
VERSION_UNSUPPORTED = (10, 2, 0)


class _SequenceHarness(MariaDBSequenceMixin):
    """Minimal dialect harness exposing just the sequence mixin."""

    def __init__(self, version):
        """Store the version tuple used by capability gates."""
        self.version = version
        self.name = "TestSequence"

    def format_identifier(self, identifier):
        """Backtick-quote an identifier like the real dialect."""
        return f"`{identifier}`"


class TestSequenceVersionGating:
    """Tests for SEQUENCE capability version gates."""

    @pytest.mark.parametrize("method", [
        "supports_sequence",
        "supports_create_sequence",
        "supports_drop_sequence",
        "supports_alter_sequence",
    ])
    @pytest.mark.parametrize("version,expected", [
        (VERSION_SUPPORTED, True),
        (VERSION_UNSUPPORTED, False),
    ])
    def test_support_gate(self, method, version, expected):
        """Test each SEQUENCE capability against the version boundary."""
        dialect = _SequenceHarness(version)
        assert getattr(dialect, method)() is expected, \
            f"{method}() should return {expected} for version {version}"

    def test_support_gate_via_dialect(self):
        """Test SEQUENCE capabilities through the real dialect."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        assert dialect.supports_sequence() is True, "dialect must support SEQUENCE at 10.3"


class TestSequenceValueFormatters:
    """Tests for NEXTVAL / CURRVAL / SETVAL formatting."""

    def test_format_nextval(self):
        """Test NEXTVAL expression formatting."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_nextval("user_seq")
        assert sql == "NEXT VALUE FOR `user_seq`", "nextval must use NEXT VALUE FOR syntax"
        assert params == (), "nextval has no bind parameters"

    def test_format_currval(self):
        """Test CURRVAL expression formatting."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_currval("user_seq")
        assert sql == "CURRENT VALUE FOR `user_seq`", "currval must use CURRENT VALUE FOR syntax"
        assert params == (), "currval has no bind parameters"

    def test_format_setval_called(self):
        """Test SETVAL with is_called=True (default)."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_setval("user_seq", 100)
        assert sql == "SET `user_seq` = 100", "called setval must set the bare value"
        assert params == (), "setval has no bind parameters"

    def test_format_setval_not_called(self):
        """Test SETVAL with is_called=False adds a trailing ,0."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_setval("user_seq", 100, is_called=False)
        assert sql == "SET `user_seq` = 100, 0", "uncalled setval must append , 0"
        assert params == (), "setval has no bind parameters"


class TestCreateSequenceStatement:
    """Tests for CREATE SEQUENCE statement formatting."""

    def test_minimal(self):
        """Test CREATE SEQUENCE with only the sequence name."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_create_sequence_statement("user_seq")
        assert sql == "CREATE SEQUENCE `user_seq`", "minimal form must include only name"
        assert params == (), "create sequence has no bind parameters"

    def test_if_not_exists(self):
        """Test CREATE SEQUENCE with IF NOT EXISTS."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_create_sequence_statement("user_seq", if_not_exists=True)
        assert "IF NOT EXISTS" in sql, "IF NOT EXISTS qualifier must be present"

    def test_all_options(self):
        """Test CREATE SEQUENCE with every option present."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_create_sequence_statement(
            "user_seq",
            start_with=10,
            increment_by=5,
            minvalue=1,
            maxvalue=1000,
            cache=20,
            cycle=True,
        )
        assert "START WITH = 10" in sql, "START WITH option must be rendered"
        assert "INCREMENT BY = 5" in sql, "INCREMENT BY option must be rendered"
        assert "MINVALUE = 1" in sql, "MINVALUE option must be rendered"
        assert "MAXVALUE = 1000" in sql, "MAXVALUE option must be rendered"
        assert "CACHE = 20" in sql, "CACHE option must be rendered"
        assert "CYCLE" in sql, "CYCLE option must be rendered"
        assert sql.startswith("CREATE SEQUENCE"), "statement must start with CREATE SEQUENCE"

    def test_no_cycle(self):
        """Test CREATE SEQUENCE without CYCLE omits the keyword."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_create_sequence_statement("user_seq", cycle=False)
        assert "CYCLE" not in sql, "CYCLE keyword must be absent when cycle=False"

    def test_unsupported_version(self):
        """Test CREATE SEQUENCE raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="CREATE SEQUENCE"):
            dialect.format_create_sequence_statement("user_seq")


class TestDropSequenceStatement:
    """Tests for DROP SEQUENCE statement formatting."""

    def test_minimal(self):
        """Test DROP SEQUENCE with only the sequence name."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_drop_sequence_statement("user_seq")
        assert sql == "DROP SEQUENCE `user_seq`", "minimal form must include only name"
        assert params == (), "drop sequence has no bind parameters"

    def test_if_exists(self):
        """Test DROP SEQUENCE with IF EXISTS."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_drop_sequence_statement("user_seq", if_exists=True)
        assert sql == "DROP SEQUENCE IF EXISTS `user_seq`", "IF EXISTS qualifier must be present"

    def test_unsupported_version(self):
        """Test DROP SEQUENCE raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="DROP SEQUENCE"):
            dialect.format_drop_sequence_statement("user_seq")


class TestAlterSequenceStatement:
    """Tests for ALTER SEQUENCE statement formatting."""

    def test_minimal(self):
        """Test ALTER SEQUENCE with only the sequence name."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, params = dialect.format_alter_sequence_statement("user_seq")
        assert sql == "ALTER SEQUENCE `user_seq`", "minimal form must include only name"
        assert params == (), "alter sequence has no bind parameters"

    def test_all_options(self):
        """Test ALTER SEQUENCE with every option present."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_alter_sequence_statement(
            "user_seq",
            restart_with=100,
            increment_by=2,
            minvalue=0,
            maxvalue=500,
            cache=10,
            cycle=True,
        )
        assert "RESTART WITH 100" in sql, "RESTART WITH option must be rendered"
        assert "INCREMENT BY = 2" in sql, "INCREMENT BY option must be rendered"
        assert "MINVALUE = 0" in sql, "MINVALUE option must be rendered"
        assert "MAXVALUE = 500" in sql, "MAXVALUE option must be rendered"
        assert "CACHE = 10" in sql, "CACHE option must be rendered"
        assert "CYCLE" in sql, "CYCLE option must be rendered"

    def test_nocycle(self):
        """Test ALTER SEQUENCE with cycle=False renders NOCYCLE."""
        dialect = MariaDBDialect(VERSION_SUPPORTED)
        sql, _ = dialect.format_alter_sequence_statement("user_seq", cycle=False)
        assert "NOCYCLE" in sql, "cycle=False must render NOCYCLE"

    def test_unsupported_version(self):
        """Test ALTER SEQUENCE raises for MariaDB < 10.3."""
        dialect = MariaDBDialect(VERSION_UNSUPPORTED)
        with pytest.raises(UnsupportedFeatureError, match="ALTER SEQUENCE"):
            dialect.format_alter_sequence_statement("user_seq")