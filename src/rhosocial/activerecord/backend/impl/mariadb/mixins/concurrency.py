# src/rhosocial/activerecord/backend/impl/mariadb/mixins/concurrency.py
"""MariaDB concurrency hint mixins.

Fetches max_connections from MariaDB server during connect and caches the value.
Returns min(max_connections, pool_size) as the concurrency limit.
"""
import logging
from typing import Optional

from rhosocial.activerecord.backend.protocols import ConcurrencyHint

from ..expression.show import ShowVariablesExpression


class MariaDBConcurrencyMixin:
    """Mixin providing MariaDB-specific concurrency hint.

    Fetches max_connections from MariaDB server during connect and caches the value.
    Returns min(max_connections, pool_size) as the concurrency limit.
    """

    _concurrency_hint: Optional[ConcurrencyHint] = None

    def connect(self):
        """Establish connection to MariaDB and fetch concurrency hint."""
        super().connect()

        self._fetch_concurrency_hint()

    def _fetch_concurrency_hint(self) -> None:
        """Fetch max_connections from MariaDB server and compute concurrency hint."""
        try:
            cursor = self._connection.cursor(dictionary=True)
            sql, params = ShowVariablesExpression(
                self.dialect, like_pattern="max_connections"
            ).to_sql()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            cursor.close()

            if row:
                max_connections = int(row["Value"])
                pool_size = getattr(self.config, "pool_size", 5) or 5
                limit = min(max_connections, pool_size)
                self._concurrency_hint = ConcurrencyHint(
                    max_concurrency=limit,
                    reason=f"min(max_connections={max_connections}, pool_size={pool_size})",
                )
                self.log(
                    logging.DEBUG,
                    f"Concurrency hint: max_concurrency={limit}, max_connections={max_connections}, pool_size={pool_size}",
                )
        except Exception as e:
            self.log(logging.WARNING, f"Failed to fetch concurrency hint: {e}")
            self._concurrency_hint = None

    def get_concurrency_hint(self) -> Optional[ConcurrencyHint]:
        """Get cached concurrency hint."""
        return self._concurrency_hint


class AsyncMariaDBConcurrencyMixin:
    """Async mixin providing MariaDB-specific concurrency hint.

    Fetches max_connections from MariaDB server during connect and caches the value.
    Returns min(max_connections, pool_size) as the concurrency limit.
    """

    _concurrency_hint: Optional[ConcurrencyHint] = None

    async def connect(self):
        """Establish connection to MariaDB and fetch concurrency hint."""
        await super().connect()

        await self._fetch_concurrency_hint()

    async def _fetch_concurrency_hint(self) -> None:
        """Fetch max_connections from MariaDB server and compute concurrency hint."""
        try:
            cursor = self._connection.cursor(dictionary=True)
            sql, params = ShowVariablesExpression(
                self.dialect, like_pattern="max_connections"
            ).to_sql()
            await cursor.execute(sql, params)
            row = await cursor.fetchone()
            await cursor.close()

            if row:
                max_connections = int(row["Value"])
                pool_size = getattr(self.config, "pool_size", 5) or 5
                limit = min(max_connections, pool_size)
                self._concurrency_hint = ConcurrencyHint(
                    max_concurrency=limit,
                    reason=f"min(max_connections={max_connections}, pool_size={pool_size})",
                )
                self.log(
                    logging.DEBUG,
                    f"Concurrency hint: max_concurrency={limit}, max_connections={max_connections}, pool_size={pool_size}",
                )
        except Exception as e:
            self.log(logging.WARNING, f"Failed to fetch concurrency hint: {e}")
            self._concurrency_hint = None

    def get_concurrency_hint(self) -> Optional[ConcurrencyHint]:
        """Get cached concurrency hint."""
        return self._concurrency_hint


__all__ = ['MariaDBConcurrencyMixin', 'AsyncMariaDBConcurrencyMixin']