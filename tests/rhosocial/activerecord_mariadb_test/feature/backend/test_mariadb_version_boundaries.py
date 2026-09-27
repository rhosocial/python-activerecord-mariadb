# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_version_boundaries.py
"""
Version-gate regression tests for MariaDB 12.3 / 13.0 / 13.1.

Every feature gate added for a new MariaDB release needs a boundary test.
A gate that is only exercised on one side is indistinguishable from a gate
that is hardcoded, which is how ``supports_returning_for_update`` came to
return ``False`` unconditionally for every version including 13.0 and 13.1,
where the server does support the clause.

The integration tests at the bottom close the loop against a real server:
the gate value is compared with what the server actually accepts, so a
threshold that drifts from reality fails here rather than in production.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.mariadb import dialect as dialect_mod
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins import backend as backend_mixin_mod
from rhosocial.activerecord.backend.impl.mariadb.mixins.backend import (
    MARIADB_VERSION_BOUNDARIES,
)
from rhosocial.activerecord.backend.impl.mariadb.reserved_words import (
    MARIADB_RESERVED_WORDS,
    reserved_words_for_version,
)

# Versions bracketing every boundary this backend knows about.
OLD = (10, 6, 0)
LTS_122 = (12, 2, 2)
LTS_123 = (12, 3, 3)
GA_130 = (13, 0, 2)
RC_131 = (13, 1, 1)


def _dialect(version):
    return MariaDBDialect(version=version)


class TestBoundaryTableIsSingleSource:
    """The boundary table must not be duplicated or shadowed.

    ``dialect.py`` once rebound ``MARIADB_VERSION_BOUNDARIES`` to a local
    19-key copy that omitted ``CHECK_CONSTRAINT``, shadowing the imported
    20-key table. Every other module imports from ``.mixins.backend``, so the
    two had silently diverged and the omission surfaced as a ``KeyError`` at
    call time rather than at import time.
    """

    def test_dialect_exports_the_mixin_table_by_identity(self):
        assert dialect_mod.MARIADB_VERSION_BOUNDARIES is MARIADB_VERSION_BOUNDARIES

    def test_mixin_module_exports_the_same_table(self):
        assert backend_mixin_mod.MARIADB_VERSION_BOUNDARIES is MARIADB_VERSION_BOUNDARIES

    def test_every_boundary_is_a_comparable_triple(self):
        for name, boundary in MARIADB_VERSION_BOUNDARIES.items():
            assert isinstance(boundary, tuple), name
            assert len(boundary) == 3, name
            assert all(isinstance(part, int) for part in boundary), name

    def test_boundaries_are_sorted_within_each_release_line(self):
        # A 13.0 feature must not be gated below a 12.3 feature, otherwise a
        # tuple comparison silently enables the newer feature too early.
        by_line = {}
        for name, boundary in MARIADB_VERSION_BOUNDARIES.items():
            by_line.setdefault(boundary[:2], []).append(name)
        for line, names in by_line.items():
            assert names, line

    def test_check_constraint_boundary_present(self):
        assert "CHECK_CONSTRAINT" in MARIADB_VERSION_BOUNDARIES

    def test_supports_check_constraint_does_not_raise(self):
        for version in [OLD, LTS_123, GA_130, RC_131]:
            assert _dialect(version).supports_check_constraint() is True
        assert _dialect((10, 2, 0)).supports_check_constraint() is False

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("RETURNING_UPDATE", (13, 0, 0)),
            ("DENY", (13, 1, 0)),
            ("IS_JSON_PREDICATE", (12, 3, 0)),
            ("TO_DATE_FUNCTION", (12, 3, 0)),
            ("JSON_ARROW_NATIVE", (13, 1, 0)),
            ("JSON_TABLE", (10, 6, 0)),
        ],
    )
    def test_new_boundaries_have_intended_thresholds(self, key, expected):
        assert MARIADB_VERSION_BOUNDARIES[key] == expected


class TestFunctionUpperBound:
    """A function removed in a later release must be gated, not assumed."""

    @pytest.mark.parametrize("version,expected", [
        (LTS_123, True),
        ((13, 0, 0), True),
        (GA_130, False),
        (RC_131, False),
    ])
    def test_des_encrypt_removed_in_13_0(self, version, expected):
        assert _dialect(version).supports_function_name("des_encrypt") is expected

    def test_lookup_is_case_insensitive(self):
        assert _dialect(GA_130).supports_function_name("DES_ENCRYPT") is False

    def test_unbounded_functions_still_supported(self):
        for name in ("json_extract", "elt", "find_in_set"):
            assert _dialect(RC_131).supports_function_name(name) is True

    def test_unknown_name_is_permitted(self):
        # An unlisted name is not this table's business to reject; the server
        # is the authority on whether a function exists.
        assert _dialect(RC_131).supports_function_name("not_a_real_function") is True

    def test_non_string_is_rejected(self):
        assert _dialect(RC_131).supports_function_name(None) is False


class TestUpdateReturning:
    """``UPDATE ... RETURNING`` arrived in MariaDB 13.0."""

    @pytest.mark.parametrize("version,expected", [
        (OLD, False),
        (LTS_123, False),
        ((13, 0, 0), True),
        (GA_130, True),
        (RC_131, True),
    ])
    def test_gate(self, version, expected):
        dialect = _dialect(version)
        assert dialect.supports_returning_for_update() is expected
        # The core format_update_statement consults the un-suffixed alias, so
        # a divergence between the two would silently disable the feature.
        assert dialect.supports_returning_update() is expected

    def test_insert_and_delete_gates_unchanged(self):
        for version in (OLD, LTS_123, GA_130, RC_131):
            dialect = _dialect(version)
            assert dialect.supports_returning_for_insert() is True
            assert dialect.supports_returning_for_delete() is True

    def test_unsupported_version_raises_rather_than_silently_dropping(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            Literal,
            TableExpression,
            UpdateExpression,
        )
        from rhosocial.activerecord.backend.expression.statements import ReturningClause

        dialect = _dialect(LTS_123)
        table = TableExpression(dialect, "t")
        expr = UpdateExpression(
            dialect,
            table=table,
            assignments={"v": Literal(dialect, 1)},
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id")]),
        )
        with pytest.raises(UnsupportedFeatureError):
            dialect.format_update_statement(expr)

    def test_supported_version_renders_the_clause(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            Literal,
            TableExpression,
            UpdateExpression,
        )
        from rhosocial.activerecord.backend.expression.statements import ReturningClause

        dialect = _dialect(GA_130)
        table = TableExpression(dialect, "t")
        expr = UpdateExpression(
            dialect,
            table=table,
            assignments={"v": Literal(dialect, 1)},
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id")]),
        )
        sql, _ = dialect.format_update_statement(expr)
        assert sql.endswith("RETURNING `id`")


class TestJsonTableAndArrows:
    def test_json_table_gate(self):
        assert _dialect((10, 5, 9)).supports_json_table() is False
        for version in ((10, 6, 0), LTS_123, GA_130, RC_131):
            assert _dialect(version).supports_json_table() is True

    def test_json_table_renders(self):
        from rhosocial.activerecord.backend.expression.query_sources import (
            JSONTableColumn,
            JSONTableExpression,
        )

        dialect = _dialect(GA_130)
        expr = JSONTableExpression(
            dialect,
            json_column="j",
            path="$[*]",
            columns=[JSONTableColumn("a", "INTEGER", "$.a")],
            alias="jt",
        )
        sql, _ = dialect.format_json_table_expression(expr)
        assert sql == "JSON_TABLE(`j`, '$[*]' COLUMNS(`a` INTEGER PATH '$.a')) AS `jt`"

    def test_json_table_rejected_before_10_6(self):
        from rhosocial.activerecord.backend.expression.query_sources import (
            JSONTableColumn,
            JSONTableExpression,
        )

        dialect = _dialect((10, 5, 9))
        expr = JSONTableExpression(
            dialect,
            json_column="j",
            path="$[*]",
            columns=[JSONTableColumn("a", "INTEGER", "$.a")],
        )
        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_arrows_rendered_as_functions_on_every_version(self):
        dialect = _dialect(RC_131)
        assert dialect.supports_json_arrow_operators() is False
        assert dialect.get_json_access_operator() == ""

    def test_native_arrow_gate(self):
        for version in (LTS_123, GA_130):
            assert _dialect(version).supports_json_arrow_operators_native() is False
        assert _dialect(RC_131).supports_json_arrow_operators_native() is True


class TestReservedWords:
    def test_baseline_size(self):
        assert len(MARIADB_RESERVED_WORDS) == 239

    @pytest.mark.parametrize("version,expected", [
        (OLD, False),
        ((12, 2, 2), False),
        (LTS_123, True),
        (GA_130, True),
        (RC_131, True),
    ])
    def test_conversion_and_to_date_reserved_from_12_3(self, version, expected):
        words = reserved_words_for_version(version)
        assert ("conversion" in words) is expected
        assert ("to_date" in words) is expected

    def test_deny_reserved_from_13_1(self):
        assert "deny" not in reserved_words_for_version(GA_130)
        assert "deny" in reserved_words_for_version(RC_131)

    def test_unknown_version_returns_baseline(self):
        assert reserved_words_for_version(None) is MARIADB_RESERVED_WORDS

    def test_dialect_uses_version_appropriate_set(self):
        assert _dialect((12, 2, 2)).is_reserved_word("to_date") is False
        assert _dialect(LTS_123).is_reserved_word("to_date") is True
        assert _dialect(GA_130).is_reserved_word("conversion") is True

    def test_reserved_words_track_a_late_version_assignment(self):
        # backend.introspect_and_adapt() re-assigns version after
        # construction; the reserved-word set must follow it.
        dialect = _dialect((12, 2, 2))
        assert dialect.is_reserved_word("to_date") is False
        dialect.version = LTS_123
        assert dialect.is_reserved_word("to_date") is True
        dialect.version = RC_131
        assert dialect.is_reserved_word("deny") is True

    def test_unadapted_dialect_uses_baseline(self):
        dialect = MariaDBDialect()
        assert dialect.is_reserved_word("to_date") is False

    def test_unquoted_reserved_word_still_warns(self):
        from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning

        with pytest.warns(IdentifierQuotingWarning):
            _dialect(LTS_123).format_identifier("to_date", need_quote=False)

    def test_quoted_identifier_is_unaffected_by_the_reserved_list(self):
        for version in (LTS_123, GA_130, RC_131):
            assert _dialect(version).format_identifier("to_date") == "`to_date`"


class TestYearDisplayWidth:
    def test_year_2_rejected_at_construction(self):
        from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
            MariaDBYearType,
        )

        with pytest.raises(ValueError, match="YEAR"):
            MariaDBYearType(_dialect(GA_130), 2)

    @pytest.mark.parametrize("width", [None, 4])
    def test_allowed_widths(self, width):
        from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
            MariaDBYearType,
        )

        assert MariaDBYearType(_dialect(GA_130), width).display_width == width

    def test_formatter_emits(self):
        from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
            MariaDBYearType,
        )

        dialect = _dialect(GA_130)
        assert dialect.format_data_type_mariadb_year(MariaDBYearType(dialect, 4))[0] == "YEAR(4)"
        assert dialect.format_data_type_mariadb_year(MariaDBYearType(dialect))[0] == "YEAR"

    def test_server_reported_year_2_degrades_with_a_warning(self):
        dialect = _dialect((10, 6, 0))
        with pytest.warns(DeprecationWarning, match="YEAR"):
            data_type = dialect.parse_type("YEAR(2)")
        assert data_type.display_width is None

    def test_year_4_round_trips_without_warning(self):
        import warnings

        dialect = _dialect((10, 6, 0))
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            data_type = dialect.parse_type("YEAR(4)")
        assert data_type.display_width == 4


# ---------------------------------------------------------------------------
# Integration: compare each gate against what a live server actually accepts.
# ---------------------------------------------------------------------------

def _server_version(backend):
    return backend.fetch_one("SELECT VERSION() AS v")["v"]


def _parse_version(text):
    return tuple(int(p) for p in text.split("-")[0].split(".")[:3])


class TestGatesMatchLiveServer:
    """A gate that disagrees with the server is worse than no gate."""

    def test_update_returning_gate_matches_server(self, mariadb_backend):
        version = _parse_version(_server_version(mariadb_backend))
        gate = mariadb_backend.dialect.supports_returning_update()
        mariadb_backend.execute("DROP TABLE IF EXISTS t_gate_ret")
        mariadb_backend.execute("CREATE TABLE t_gate_ret (id INT PRIMARY KEY, v INT)")
        mariadb_backend.execute("INSERT INTO t_gate_ret VALUES (1, 10)")
        try:
            if gate:
                mariadb_backend.execute(
                    "UPDATE t_gate_ret SET v = v + 1 WHERE id = 1 RETURNING id, v"
                )
                assert mariadb_backend.fetch_one(
                    "SELECT v FROM t_gate_ret WHERE id = 1"
                )["v"] == 11
            else:
                with pytest.raises(DatabaseError):
                    mariadb_backend.execute(
                        "UPDATE t_gate_ret SET v = v + 1 WHERE id = 1 RETURNING id, v"
                    )
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS t_gate_ret")
        # The observed behaviour above must be what the boundary table says.
        assert gate is (version >= MARIADB_VERSION_BOUNDARIES["RETURNING_UPDATE"])

    def test_deny_gate_matches_server(self, mariadb_backend):
        gate = mariadb_backend.dialect.supports_deny()
        statement = "DENY SELECT ON *.* TO 'no_such_user_gate_probe'@'localhost'"
        if gate:
            # Parses on 13.1+; the user need not exist for that to be true.
            try:
                mariadb_backend.execute(statement)
            except DatabaseError as exc:
                # The account does not exist, which is fine: the point is that
                # the statement parsed rather than being a syntax error.
                assert "1133" in str(exc) or "DENY" in str(exc)
        else:
            with pytest.raises(DatabaseError):
                mariadb_backend.execute(statement)

    def test_json_table_gate_matches_server(self, mariadb_backend):
        from rhosocial.activerecord.backend.dialect.protocols import JSONSupport

        gate = mariadb_backend.dialect.supports_json_table()
        mariadb_backend.execute("DROP TABLE IF EXISTS t_gate_jt")
        mariadb_backend.execute("CREATE TABLE t_gate_jt (id INT, j JSON)")
        mariadb_backend.execute("""INSERT INTO t_gate_jt VALUES (1, '[{"a":1},{"a":2}]')""")
        try:
            query = (
                "SELECT jt.a FROM t_gate_jt JOIN JSON_TABLE(j, '$[*]' "
                "COLUMNS(a INTEGER PATH '$.a')) AS jt ON TRUE ORDER BY jt.a"
            )
            if gate:
                rows = mariadb_backend.fetch_all(query)
                assert [r["a"] for r in rows] == [1, 2]
            else:
                with pytest.raises(DatabaseError):
                    mariadb_backend.fetch_all(query)
        finally:
            mariadb_backend.execute("DROP TABLE IF EXISTS t_gate_jt")
        assert gate is (
            tuple(int(p) for p in _server_version(mariadb_backend)
                  .split("-")[0].split(".")[:3]) >= MARIADB_VERSION_BOUNDARIES["JSON_TABLE"]
        )
        assert JSONSupport is not None

    def test_des_encrypt_gate_matches_server(self, mariadb_backend):
        gate = mariadb_backend.dialect.supports_function_name("des_encrypt")
        try:
            mariadb_backend.execute("SELECT DES_ENCRYPT('x', 'k') AS v")
            available = True
        except DatabaseError:
            available = False
        assert gate is available
