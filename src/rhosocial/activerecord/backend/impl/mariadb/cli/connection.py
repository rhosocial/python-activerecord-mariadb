# src/rhosocial/activerecord/backend/impl/mariadb/cli/connection.py
"""Connection argument parsing and backend creation for MariaDB CLI."""

import os

from .output import RICH_AVAILABLE


def add_connection_args(parser):
    """Add MariaDB connection arguments to a subcommand parser.

    Each subcommand that needs a database connection calls this.
    """
    parser.add_argument(
        "--host",
        default=os.getenv("MARIADB_HOST", "localhost"),
        help="Database host (env: MARIADB_HOST, default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MARIADB_PORT", "3306")),
        help="Database port (env: MARIADB_PORT, default: 3306)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MARIADB_DATABASE"),
        help="Database name (env: MARIADB_DATABASE, optional for some operations)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("MARIADB_USER", "root"),
        help="Database user (env: MARIADB_USER, default: root)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MARIADB_PASSWORD", ""),
        help="Database password (env: MARIADB_PASSWORD)",
    )
    parser.add_argument(
        "--charset",
        default=os.getenv("MARIADB_CHARSET", "utf8mb4"),
        help="Connection charset (env: MARIADB_CHARSET, default: utf8mb4)",
    )
    parser.add_argument(
        "--async",
        action="store_true",
        dest="is_async",
        help="Use asynchronous backend",
    )
    parser.add_argument(
        "--named-connection",
        dest="named_connection",
        metavar="QUALIFIED_NAME",
        help="Named connection from Python module (e.g., myapp.connections.prod_db).",
    )
    parser.add_argument(
        "--conn-param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="connection_params",
        help="Connection parameter override for named connection. Can be specified multiple times.",
    )


def add_version_arg(parser):
    """Add --version argument (used only by info subcommand)."""
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help='MariaDB version to simulate (e.g., "10.11.0", "10.5.0"). Default: 10.11.0.',
    )


def create_connection_parent_parser():
    """Create a parent parser with connection and output arguments.

    Used by shared CLI helpers (named-query, named-procedure) that
    require a parent_parser containing connection parameters.
    """
    import argparse
    parent = argparse.ArgumentParser(add_help=False)
    add_connection_args(parent)
    # Output parameters
    parent.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "tsv"],
        default="table",
        help='Output format. Defaults to "table" if rich is installed.',
    )
    parent.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII characters for rich table borders.",
    )
    return parent


def resolve_connection_config_from_args(args):
    """Resolve MariaDB connection config from parsed args.

    Priority order:
    1. --named-connection + --conn-param
    2. Explicit connection parameters (--host, --port, etc.)
    3. Default values
    """
    from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
    from rhosocial.activerecord.backend.named_connection.cli import parse_params
    from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver

    named_conn = getattr(args, "named_connection", None)
    conn_params = getattr(args, "connection_params", [])

    if conn_params:
        conn_params = parse_params(conn_params)
    else:
        conn_params = {}

    if named_conn:
        resolver = NamedConnectionResolver(named_conn).load()
        if conn_params:
            return resolver.resolve(conn_params)
        return resolver.resolve({})

    # Fallback to explicit connection parameters
    return MariaDBConnectionConfig(
        host=args.host or "localhost",
        port=args.port or 3306,
        database=args.database,
        username=args.user,
        password=args.password,
        charset=args.charset,
    )


def create_backend(args):
    """Create, connect, and introspect a MariaDB backend from parsed args."""
    from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
    config = resolve_connection_config_from_args(args)
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    return backend
