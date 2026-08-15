# src/rhosocial/activerecord/backend/impl/mariadb/schema/__init__.py
"""MariaDB schema differ."""

from .differ import MariaDBSchemaDiffer

__all__ = ["MariaDBSchemaDiffer"]