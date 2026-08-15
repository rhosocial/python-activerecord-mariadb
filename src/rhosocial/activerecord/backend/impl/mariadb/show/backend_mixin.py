# src/rhosocial/activerecord/backend/impl/mariadb/show/backend_mixin.py
"""
MariaDB backend mixins for SHOW functionality.

This module provides mixin classes that add the show() factory method
to MariaDB backends. The show() method returns a MariaDBShowFunctionality
instance that provides all MariaDB SHOW commands.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .functionality import MariaDBShowFunctionality, AsyncMariaDBShowFunctionality


class MariaDBShowMixin:
    """MariaDB backend mixin for SHOW functionality.

    Provides the show() factory method that returns a MariaDBShowFunctionality
    instance for executing MariaDB SHOW commands.
    """

    def show(self) -> "MariaDBShowFunctionality":
        """Return a MariaDBShowFunctionality instance."""
        return self._create_show_functionality()

    def _create_show_functionality(self) -> "MariaDBShowFunctionality":
        """Create MariaDB SHOW functionality instance.

        Returns:
            MariaDBShowFunctionality instance with version awareness.
        """
        from .functionality import MariaDBShowFunctionality
        # Get server version for feature adaptation
        version = getattr(self, "_version", None)
        if version is None and hasattr(self, "get_server_version"):
            try:
                version = self.get_server_version()
            except Exception:
                version = None
        return MariaDBShowFunctionality(self, version)


class AsyncMariaDBShowMixin:
    """Async MariaDB backend mixin for SHOW functionality.

    Provides the show() factory method that returns an AsyncMariaDBShowFunctionality
    instance for executing MariaDB SHOW commands asynchronously.
    """

    def show(self) -> "AsyncMariaDBShowFunctionality":
        """Return an AsyncMariaDBShowFunctionality instance."""
        return self._create_show_functionality()

    def _create_show_functionality(self) -> "AsyncMariaDBShowFunctionality":
        """Create async MariaDB SHOW functionality instance.

        Returns:
            AsyncMariaDBShowFunctionality instance with version awareness.
        """
        from .functionality import AsyncMariaDBShowFunctionality
        # Get server version for feature adaptation
        version = getattr(self, "_version", None)
        if version is None and hasattr(self, "_version"):
            version = self._version
        return AsyncMariaDBShowFunctionality(self, version)