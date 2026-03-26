# src/rhosocial/activerecord/backend/impl/mariadb/backend/__init__.py
"""MariaDB backend module."""

from .sync import MariaDBBackend

__all__ = ["MariaDBBackend"]
