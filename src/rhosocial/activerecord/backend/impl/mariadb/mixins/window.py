# src/rhosocial/activerecord/backend/impl/mariadb/mixins/window.py
"""MariaDB window function support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBWindowMixin:
    """MariaDB window function support.

    Window functions and frame clauses are supported since MariaDB 10.2.
    """

    def supports_window_functions(self) -> bool:
        """Window functions are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']

    def supports_window_frame_clause(self) -> bool:
        """Window frame clauses are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']


__all__ = ['MariaDBWindowMixin']
