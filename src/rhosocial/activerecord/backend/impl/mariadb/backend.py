# src/rhosocial/activerecord/backend/impl/mariadb/backend.py
"""Legacy backend module - use backend.sync instead."""

from .backend.sync import MariaDBBackend

__all__ = ["MariaDBBackend"]
