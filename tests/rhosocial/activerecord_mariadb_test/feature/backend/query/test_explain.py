# tests/rhosocial/activerecord_mariadb_test/feature/backend/query/test_explain.py
"""
Integration tests for MariaDBBackend.explain() and AsyncMariaDBBackend.explain().

These tests require a real MySQL connection configured via mariadb_scenarios.yaml.
The tests create temporary tables, run EXPLAIN, and verify the typed result objects.
"""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.explain import (
    SyncExplainBackendProtocol,
    AsyncExplainBackendProtocol,
)
from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.expression.statements import ExplainOptions, ExplainType
from rhosocial.activerecord.backend.impl.mariadb.explain import (
    MariaDBExplainResult,
    MariaDBExplainRow,
)


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_SETUP_SQL = """
    DROP TABLE IF EXISTS explain_order_items;
    DROP TABLE IF EXISTS explain_orders;

    CREATE TABLE explain_orders (
        id       INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
        status   VARCHAR(20)  NOT NULL,
        amount   DECIMAL(10,2),
        INDEX idx_orders_status (status)
    ) ENGINE=InnoDB;

    CREATE TABLE explain_order_items (
        id       INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
        order_id INT          NOT NULL,
        sku      VARCHAR(50)  NOT NULL,
        qty      INT          NOT NULL DEFAULT 1,
        INDEX idx_items_order_id_sku (order_id, sku)
    ) ENGINE=InnoDB;

    INSERT INTO explain_orders (status, amount) VALUES
        ('pending', 10.00), ('pending', 20.00),
        ('shipped', 30.00), ('delivered', 40.00);

    INSERT INTO explain_order_items (order_id, sku, qty) VALUES
        (1, 'A001', 1), (1, 'A002', 2),
        (2, 'B001', 1), (3, 'A001', 3);
"""

_CLEANUP_SQL = """
    DROP TABLE IF EXISTS explain_order_items;
    DROP TABLE IF EXISTS explain_orders;
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def indexed_backend(mariadb_backend_single):
    """Sync backend with test tables and indexes."""
    mariadb_backend_single.executescript(_SETUP_SQL)
    yield mariadb_backend_single
    try:
        mariadb_backend_single.executescript(_CLEANUP_SQL)
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def async_indexed_backend(async_mariadb_backend):
    """Async backend with test tables and indexes."""
    await async_mariadb_backend.executescript(_SETUP_SQL)
    yield async_mariadb_backend
    try:
        await async_mariadb_backend.executescript(_CLEANUP_SQL)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Protocol checking
# ---------------------------------------------------------------------------

class TestExplainProtocol:
    def test_sync_backend_implements_protocol(self, mariadb_backend_single):
        assert isinstance(mariadb_backend_single, SyncExplainBackendProtocol)

    @pytest.mark.asyncio
    async def test_async_backend_implements_protocol(self, async_mariadb_backend):
        assert isinstance(async_mariadb_backend, AsyncExplainBackendProtocol)


# ---------------------------------------------------------------------------
# Sync explain – basic structure
# ---------------------------------------------------------------------------

class TestSyncExplainBasic:
    def test_explain_returns_mysql_explain_result(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        assert isinstance(result, MariaDBExplainResult)

    def test_result_has_rows(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        assert len(result.rows) > 0

    def test_result_row_type(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        for row in result.rows:
            assert isinstance(row, MariaDBExplainRow)

    def test_result_has_sql(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        assert "explain_orders" in result.sql.lower()
        assert result.sql.upper().startswith("EXPLAIN")

    def test_result_has_duration(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        assert result.duration >= 0.0

    def test_result_has_raw_rows(self, indexed_backend):
        dialect = indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr)
        assert isinstance(result.raw_rows, list)
        assert len(result.raw_rows) == len(result.rows)


# ---------------------------------------------------------------------------
# Sync explain – index usage analysis
# ---------------------------------------------------------------------------

class TestSyncExplainIndexAnalysis:
    def test_full_scan_detection(self, indexed_backend):
        """SELECT * FROM table without WHERE → full scan (type='ALL')."""
        dialect = indexed_backend.dialect
        result = indexed_backend.explain(
            RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        )
        assert result.analyze_index_usage() == "full_scan"
        assert result.is_full_scan is True
        assert result.is_index_used is False
        assert result.is_covering_index is False

    def test_index_with_lookup_detection(self, indexed_backend):
        """SELECT * … WHERE indexed_col = ? → index lookup + table read."""
        dialect = indexed_backend.dialect
        result = indexed_backend.explain(
            RawSQLExpression(dialect, "SELECT * FROM explain_orders WHERE status = 'pending'")
        )
        usage = result.analyze_index_usage()
        # Could be index_with_lookup or covering_index depending on optimizer
        assert usage in ("index_with_lookup", "covering_index")
        assert result.is_index_used is True
        assert result.is_full_scan is False

    def test_covering_index_detection(self, indexed_backend):
        """SELECT indexed_col FROM table WHERE indexed_col = ? → covering index."""
        dialect = indexed_backend.dialect
        result = indexed_backend.explain(
            RawSQLExpression(
                dialect,
                "SELECT order_id, sku FROM explain_order_items WHERE order_id = 1"
            )
        )
        usage = result.analyze_index_usage()
        # Both columns are in the covering index (order_id, sku)
        assert usage == "covering_index"
        assert result.is_covering_index is True
        assert result.is_full_scan is False

    def test_row_fields_present(self, indexed_backend):
        """Verify MariaDBExplainRow has expected attribute names."""
        dialect = indexed_backend.dialect
        result = indexed_backend.explain(
            RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        )
        row = result.rows[0]
        # All expected fields must exist (may be None for some)
        assert hasattr(row, "id")
        assert hasattr(row, "select_type")
        assert hasattr(row, "table")
        assert hasattr(row, "type")
        assert hasattr(row, "key")
        assert hasattr(row, "rows")
        assert hasattr(row, "extra")


# ---------------------------------------------------------------------------
# Async explain – mirror of sync tests
# ---------------------------------------------------------------------------

class TestAsyncExplainBasic:
    @pytest.mark.asyncio
    async def test_explain_returns_mysql_explain_result(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = await async_indexed_backend.explain(expr)
        assert isinstance(result, MariaDBExplainResult)

    @pytest.mark.asyncio
    async def test_result_has_rows(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = await async_indexed_backend.explain(expr)
        assert len(result.rows) > 0

    @pytest.mark.asyncio
    async def test_result_has_sql_and_duration(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = await async_indexed_backend.explain(expr)
        assert result.sql.upper().startswith("EXPLAIN")
        assert result.duration >= 0.0

    @pytest.mark.asyncio
    async def test_full_scan_detection(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        result = await async_indexed_backend.explain(
            RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        )
        assert result.is_full_scan is True

    @pytest.mark.asyncio
    async def test_index_used_detection(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        result = await async_indexed_backend.explain(
            RawSQLExpression(dialect, "SELECT * FROM explain_orders WHERE status = 'pending'")
        )
        assert result.is_index_used is True

    @pytest.mark.asyncio
    async def test_covering_index_detection(self, async_indexed_backend):
        dialect = async_indexed_backend.dialect
        result = await async_indexed_backend.explain(
            RawSQLExpression(
                dialect,
                "SELECT order_id, sku FROM explain_order_items WHERE order_id = 1"
            )
        )
        assert result.is_covering_index is True


# ---------------------------------------------------------------------------
# FORMAT option (version-gated)
# ---------------------------------------------------------------------------

class TestExplainFormat:
    def test_format_json_when_supported(self, indexed_backend):
        """EXPLAIN FORMAT=JSON returns a result (may not be MariaDBExplainResult rows)."""
        dialect = indexed_backend.dialect
        if not dialect.supports_explain_format("JSON"):
            pytest.skip("MySQL version does not support FORMAT=JSON")
        from rhosocial.activerecord.backend.expression.statements import ExplainFormat
        opts = ExplainOptions(format=ExplainFormat.JSON)
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr, opts)
        # We get back a MariaDBExplainResult; raw_rows should be non-empty
        assert isinstance(result, MariaDBExplainResult)
        assert len(result.raw_rows) > 0

    def test_format_tree_when_supported(self, indexed_backend):
        """EXPLAIN FORMAT=TREE (MySQL 8.0.16+)."""
        dialect = indexed_backend.dialect
        if not dialect.supports_explain_format("TREE"):
            pytest.skip("MySQL version does not support FORMAT=TREE")
        from rhosocial.activerecord.backend.expression.statements import ExplainFormat
        opts = ExplainOptions(format=ExplainFormat.TREE)
        expr = RawSQLExpression(dialect, "SELECT * FROM explain_orders")
        result = indexed_backend.explain(expr, opts)
        assert isinstance(result, MariaDBExplainResult)
        assert len(result.raw_rows) > 0
