# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_charset_alias.py
"""
The ``utf8`` character set alias changed meaning in MariaDB 13.1.

MDEV-30041 stopped ``old_mode`` from setting ``UTF8_IS_UTF8MB3`` by default, so
``CHARACTER SET utf8`` resolves to ``utf8mb3`` on every release up to 13.0 and
to ``utf8mb4`` from 13.1. A schema built from the same DDL therefore got a
different column charset depending on the server, and 4-byte characters were
accepted on one version and rejected on the next.

The backend resolves the alias to ``utf8mb3`` -- the meaning it always had
before 13.1 -- so one statement produces one schema everywhere. These tests
pin both the resolution and the resulting parity.
"""
import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.charset_collation import (
    _CHARSET_ALIASES,
    _CHARSET_MIN_VERSIONS,
    _COLLATION_MIN_VERSIONS,
    MariaDBCharset,
)

OLD = (10, 6, 0)
LTS_122 = (12, 2, 2)
LTS_123 = (12, 3, 3)
GA_130 = (13, 0, 2)
RC_131 = (13, 1, 1)


def _dialect(version):
    return MariaDBDialect(version=version)


class TestAliasResolution:
    # 10.6 is where the explicit utf8mb3 spelling becomes documented, so that
    # is where the alias starts being rewritten. Below it the alias is
    # unambiguous already and is passed through unchanged.
    @pytest.mark.parametrize("version", [OLD, LTS_122, LTS_123, GA_130, RC_131])
    @pytest.mark.parametrize("spelling", ["utf8", "UTF8", "Utf8"])
    def test_utf8_resolves_to_utf8mb3_from_10_6(self, version, spelling):
        expected = "utf8" if version < (10, 6, 0) else "utf8mb3"
        assert _dialect(version).validate_charset_name(spelling) == expected

    @pytest.mark.parametrize("version", [(10, 2, 0), (10, 3, 0), (10, 4, 0), (10, 5, 9)])
    def test_below_10_6_the_alias_is_passed_through(self, version):
        # Emitting the undocumented utf8mb3 spelling on a 10.2 server would
        # rely on leniency MariaDB does not promise.
        assert _dialect(version).validate_charset_name("utf8") == "utf8"

    @pytest.mark.parametrize("version", [LTS_123, GA_130, RC_131])
    def test_resolves_from_the_enum_too(self, version):
        assert _dialect(version).validate_charset_name(MariaDBCharset.UTF8) == "utf8mb3"

    def test_explicit_spellings_are_left_alone(self):
        dialect = _dialect(RC_131)
        assert dialect.validate_charset_name("utf8mb3") == "utf8mb3"
        assert dialect.validate_charset_name("utf8mb4") == "utf8mb4"

    def test_utf8_is_not_advertised_as_an_emittable_spelling(self):
        # It is accepted as input but never offered as output, because the
        # output is what reaches the server.
        for version in (OLD, LTS_123, GA_130, RC_131):
            assert "utf8" not in _dialect(version).supported_charsets()

    def test_resolved_target_is_advertised(self):
        for version in (OLD, LTS_123, GA_130, RC_131):
            assert "utf8mb3" in _dialect(version).supported_charsets()

    def test_alias_table_is_the_single_declared_source(self):
        assert _CHARSET_ALIASES == {"utf8": ((10, 6, 0), "utf8mb3")}

    def test_utf8_accepted_even_though_absent_from_supported_set(self):
        # Accepted-for-input / not-offered-for-output is intentional.
        dialect = _dialect(RC_131)
        assert dialect.supports_charset("utf8") is True
        assert dialect.validate_charset_name("utf8") == "utf8mb3"

    def test_utf8_offered_for_output_below_10_6_where_unambiguous(self):
        assert "utf8" in _dialect((10, 2, 0)).supported_charsets()

    def test_unknown_charset_still_rejected(self):
        with pytest.raises(ValueError):
            _dialect(RC_131).validate_charset_name("utf9")

    def test_non_string_rejected(self):
        with pytest.raises(TypeError):
            _dialect(RC_131).validate_charset_name(42)


class TestCharsetVersionTable:
    def test_utf8mb3_gated_at_10_6(self):
        assert _CHARSET_MIN_VERSIONS["utf8mb3"] == (10, 6, 0)
        with pytest.raises(ValueError, match="10.6"):
            _dialect((10, 5, 9)).validate_charset_name("utf8mb3")
        assert _dialect((10, 6, 0)).validate_charset_name("utf8mb3") == "utf8mb3"

    def test_utf8mb4_threshold_is_a_real_mariadb_release(self):
        # 5.5.3 is a genuine MariaDB release, not a MySQL-only version, so
        # this gate can actually fire for a backend supporting 10.2+.
        assert _CHARSET_MIN_VERSIONS["utf8mb4"] == (5, 5, 3)

    def test_utf8_usable_on_oldest_supported_version(self):
        # 10.2 predates the explicit utf8mb3 spelling, so the alias passes
        # through -- it is still accepted, and still means the 3-byte family.
        assert _dialect((10, 2, 0)).validate_charset_name("utf8") == "utf8"
        assert _dialect((10, 2, 0)).supports_charset("utf8") is True


class TestCollationVersionTable:
    def test_table_is_populated(self):
        # It used to be empty, which made the version branch in
        # supported_collations() and validate_collation_by_name() unreachable.
        assert _COLLATION_MIN_VERSIONS
        for name, boundary in _COLLATION_MIN_VERSIONS.items():
            assert isinstance(boundary, tuple) and len(boundary) == 3, name

    def test_utf8_family_collations_gated_at_10_6(self):
        before = _dialect((10, 5, 9)).supported_collations()
        after = _dialect((10, 6, 0)).supported_collations()
        assert "utf8_general_ci" not in before
        assert "utf8mb4_bin" not in before
        assert "utf8_general_ci" in after
        assert "utf8mb4_bin" in after

    def test_version_branch_is_reachable(self):
        with pytest.raises(ValueError, match="10.6"):
            _dialect((10, 5, 9)).validate_collation_by_name("utf8mb4_bin")
        assert _dialect((10, 6, 0)).validate_collation_by_name("utf8mb4_bin") == "utf8mb4_bin"

    def test_non_utf8_collations_ungated(self):
        assert "latin1_swedish_ci" in _dialect((10, 5, 9)).supported_collations()
        assert "binary" in _dialect((10, 5, 9)).supported_collations()


class TestCharsetParityAcrossVersions:
    """The property that motivated the change."""

    @pytest.mark.parametrize("version", [OLD, LTS_122, LTS_123, GA_130, RC_131])
    def test_resolved_spelling_always_denotes_utf8mb3(self, version):
        # The emitted text differs below 10.6, but it must never denote the
        # 4-byte family -- that is the whole point of the alias handling.
        dialect = _dialect(version)
        resolved = dialect.validate_charset_name(MariaDBCharset.UTF8)
        assert resolved in ("utf8", "utf8mb3")
        assert resolved != "utf8mb4"

    def test_predicate_constant_is_shared_by_every_call_site(self):
        from rhosocial.activerecord.backend.impl.mariadb.mixins.introspection import (
            SYSTEM_SCHEMAS,
            SYSTEM_SCHEMAS_SQL_PREDICATE,
        )

        # One definition, not an inline tuple repeated per query.
        assert SYSTEM_SCHEMAS == ("information_schema", "performance_schema", "mysql", "sys")
        for schema in SYSTEM_SCHEMAS:
            assert f"'{schema}'" in SYSTEM_SCHEMAS_SQL_PREDICATE


class TestCharsetParityOnLiveServer:
    """End-to-end: the emitted DDL yields one collation on every server."""

    def _table_collation(self, backend, charset_sql):
        backend.execute("DROP TABLE IF EXISTS t_charset_parity")
        backend.execute(f"CREATE TABLE t_charset_parity (s VARCHAR(50)) CHARACTER SET {charset_sql}")
        try:
            row = backend.fetch_one(
                "SELECT TABLE_COLLATION AS c FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 't_charset_parity'"
            )
            return row["c"]
        finally:
            backend.execute("DROP TABLE IF EXISTS t_charset_parity")

    def test_resolved_charset_is_accepted_by_the_server(self, mariadb_backend):
        dialect = mariadb_backend.dialect
        resolved = dialect.validate_charset_name(MariaDBCharset.UTF8)
        collation = self._table_collation(mariadb_backend, resolved)
        # The exact collation name is the server's own default for the family
        # and varies by release (utf8_general_ci -> utf8mb3_general_ci ->
        # utf8mb3_uca1400_ai_ci). What must hold everywhere is that the column
        # landed in the 3-byte family, never the 4-byte one.
        assert collation.startswith("utf8") and "mb4" not in collation

    def test_explicit_utf8mb4_request_still_yields_4_byte_storage(self, mariadb_backend):
        collation = self._table_collation(mariadb_backend, "utf8mb4")
        assert collation.startswith("utf8mb4")

    def test_4_byte_character_accepted_only_where_4_byte_storage_was_asked_for(
        self, mariadb_backend
    ):
        version = tuple(
            int(p) for p in mariadb_backend.fetch_one("SELECT VERSION() AS v")["v"]
            .split("-")[0].split(".")[:3]
        )
        if version < (10, 6, 0):
            pytest.skip("utf8mb4 alias resolution is not exercised before 10.6")
        backend = mariadb_backend
        backend.execute("DROP TABLE IF EXISTS t_charset_4b")
        backend.execute(
            "CREATE TABLE t_charset_4b (s VARCHAR(50)) "
            f"CHARACTER SET {backend.dialect.validate_charset_name(MariaDBCharset.UTF8)}"
        )
        try:
            with pytest.raises(DatabaseError):
                backend.execute(
                    "INSERT INTO t_charset_4b (s) VALUES (_utf8mb4 0xF09F9880)"
                )
        finally:
            backend.execute("DROP TABLE IF EXISTS t_charset_4b")

    def test_bare_alias_would_have_drifted(self, mariadb_backend):
        """Documents the hazard: the un-resolved spelling is version-dependent.

        Only meaningful on 13.1+, where the alias flipped. On <= 13.0 the bare
        spelling agrees with the resolved one, which is the point.
        """
        resolved = self._table_collation(mariadb_backend, "utf8mb3")
        bare = self._table_collation(mariadb_backend, "utf8")
        version = tuple(
            int(p) for p in mariadb_backend.fetch_one("SELECT VERSION() AS v")["v"]
            .split("-")[0].split(".")[:3]
        )
        if version >= (13, 1, 0):
            assert bare != resolved, "13.1 is expected to resolve utf8 to utf8mb4"
            assert "mb4" in bare and "mb4" not in resolved
        else:
            assert bare == resolved
