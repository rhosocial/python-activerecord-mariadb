# src/rhosocial/activerecord/backend/impl/mariadb/cli/named_migration.py
"""named-migration subcommand — MariaDB adapter for the shared CLI helper."""

from __future__ import annotations

from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

from .connection import create_connection_parent_parser, resolve_connection_config_from_args
from .output import create_provider


def create_parser(subparsers):
    """Create the named-migration subcommand parser.

    Provides connection and output arguments via a parent parser.
    """
    from rhosocial.activerecord.backend.migration.cli import create_named_migration_parser

    local_parent = create_connection_parent_parser()
    nm_epilog = """Examples:
  # Apply a migration
  %(prog)s myapp.migrations.v001.CreateUsersTable --host localhost --database mydb --direction up

  # Rollback
  %(prog)s myapp.migrations.v001.CreateUsersTable --host localhost --database mydb --direction down

  # Apply with record store
  %(prog)s myapp.migrations.v001.CreateUsersTable --database mydb --record-store ./migrations.json

  # Dry-run
  %(prog)s myapp.migrations.v001.CreateUsersTable --database mydb --direction up --dry-run

  # List available migrations
  %(prog)s myapp.migrations --list

  # Describe a migration
  %(prog)s myapp.migrations.v001.CreateUsersTable --describe
"""
    return create_named_migration_parser(subparsers, local_parent, epilog=nm_epilog)


def handle(args):
    """Handle the named-migration subcommand."""
    from rhosocial.activerecord.backend.migration.cli import handle_named_migration as handle_nm

    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    backend = None

    def backend_factory():
        nonlocal backend
        config = resolve_connection_config_from_args(args)
        backend = MariaDBBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        return backend

    def disconnect():
        if backend and getattr(backend, "_connection", None):
            backend.disconnect()

    handle_nm(
        args,
        provider,
        backend_factory=backend_factory,
        disconnect=disconnect,
    )