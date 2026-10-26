# src/rhosocial/activerecord/backend/impl/mariadb/cli/introspect.py
"""introspect subcommand - Database introspection.

There is no namespace flag here, and that is deliberate. MariaDB has
exactly one namespace level and calls it a *database* -- ``CREATE SCHEMA``
is a synonym for ``CREATE DATABASE`` and nothing sits inside a database
under a further name. So ``--database``, which the connection already
takes, is the whole answer: the run connects to a database and asks about
that database. An earlier version accepted ``--schema`` as well, which
named the same thing under a word MariaDB does not use; it is gone rather
than aliased.
"""

import argparse
import asyncio
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import AsyncMariaDBBackend
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError

from .connection import add_connection_args, resolve_connection_config_from_args
from .output import create_provider

OUTPUT_CHOICES = ['table', 'json', 'csv', 'tsv']

INTROSPECT_TYPES = [
    "tables", "views", "columns",
    "indexes", "foreign-keys", "triggers", "database",
    "sequences", "table-options",
]

#: Families that only some MariaDB versions can answer, mapped to the dialect
#: capability that decides it. ``sequences`` arrived in 10.3; everything else
#: in ``INTROSPECT_TYPES`` is answerable on every supported server, so a
#: family absent from this map is never refused after connecting.
_VERSION_GATED_FAMILIES = {
    "sequences": "supports_sequence_introspection",
}


def create_parser(subparsers):
    """Create the introspect subcommand parser."""
    parser = subparsers.add_parser(
        'introspect',
        help='Database introspection',
        epilog="""Examples:
  # List all tables in database
  %(prog)s tables --database mydb

  # List all views
  %(prog)s views --database mydb

  # Get detailed table info (columns, indexes, foreign keys)
  %(prog)s table users --database mydb

  # Get column details for a table
  %(prog)s columns users --database mydb

  # Output as JSON
  %(prog)s tables --database mydb -o json

  # List sequences, and one sequence's own limits
  %(prog)s sequences --database mydb
  %(prog)s sequences my_seq --database mydb

  # Show storage options for every table, or for one
  %(prog)s table-options --database mydb
  %(prog)s table-options users --database mydb

  # Using environment variables for connection
  export MARIADB_HOST=localhost MARIADB_DATABASE=mydb MARIADB_USER=root MARIADB_PASSWORD=secret
  %(prog)s tables
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format
    parser.add_argument(
        '-o', '--output',
        choices=OUTPUT_CHOICES,
        default='table',
        help='Output format (default: table)',
    )

    # Connection arguments
    add_connection_args(parser)

    # Rich display options
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.',
    )

    # introspect-specific arguments
    # `INTROSPECT_TYPES` is the whole candidate list: it says what MariaDB can
    # be asked about, which is a fact about the engine and not about the server
    # this run will reach. The parser is built before the run connects, so it
    # has no version to consult; a family the connected server is too old for
    # is refused by `_refuse_version_gated_family` instead of being hidden
    # here, because hiding it would also hide it from a server that has it.
    parser.add_argument(
        "type",
        choices=INTROSPECT_TYPES,
        help="Introspection type: tables, views, columns, indexes, foreign-keys, triggers, database, "
             "sequences, table-options",
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Table/view name (required for some types)",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system tables in output",
    )

    return parser


def handle(args):
    """Handle the introspect subcommand."""
    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    named_conn = getattr(args, "named_connection", None)
    if not named_conn and not args.database:
        print(
            "Error: --database is required for introspection",
            file=sys.stderr
        )
        sys.exit(1)

    config = resolve_connection_config_from_args(args)

    if args.is_async:
        backend = AsyncMariaDBBackend(connection_config=config)
        asyncio.run(
            _handle_introspect_async(args, backend, provider)
        )
    else:
        backend = MariaDBBackend(connection_config=config)
        _handle_introspect_sync(args, backend, provider)


def _refuse_version_gated_family(args, backend) -> None:
    """Refuse a family this server is too old to answer.

    The parser offers every family MariaDB has, because that is a fact about
    the engine; which of them *this* server can answer is a fact about its
    version, and only known after ``connect()`` has adapted the dialect. So
    the second reading happens here, and it asks the dialect rather than
    comparing version numbers itself: the dialect is where the release
    boundary for a family is recorded, and a copy of it in the CLI is a
    second place to keep in step.

    Only ``sequences`` is version-gated today (MariaDB 10.3+); a family with
    no entry here is answerable on every server this backend supports. The
    refusal is an ``UnsupportedFeatureError`` so it names the dialect and the
    family, which reads as "this server cannot answer that" rather than as
    argparse's "invalid choice" -- the family *is* valid here, just not on
    this server.
    """
    capability_name = _VERSION_GATED_FAMILIES.get(args.type)
    if capability_name is None:
        return
    if not getattr(backend.dialect, capability_name)():
        raise UnsupportedFeatureError(
            backend.dialect.name,
            f"{args.type} introspection",
        )


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _serialize_for_output(obj: Any) -> Any:
    """Serialize object for JSON output, handling non-serializable types."""
    if obj is None:
        return None
    if hasattr(obj, 'model_dump'):
        try:
            result = obj.model_dump(mode='json')
            return _serialize_for_output(result)
        except TypeError:
            result = obj.model_dump()
            return _serialize_for_output(result)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize_for_output(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_output(item) for item in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _handle_introspect_sync(args, backend: MariaDBBackend, provider):
    """Handle introspect subcommand synchronously."""
    try:
        backend.connect()
        _refuse_version_gated_family(args, backend)

        introspector = backend.introspector

        if args.type == "tables":
            tables = introspector.list_tables(
                schema=None,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            views = introspector.list_views(schema=None)
            data = _serialize_for_output(views)
            provider.display_results(data, title="Views")

        elif args.type == "columns":
            if not args.name:
                print(
                    "Error: Table name is required for 'columns' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            columns = introspector.list_columns(
                args.name, schema=None
            )
            data = _serialize_for_output(columns)
            provider.display_results(
                data, title=f"Columns of {args.name}"
            )

        elif args.type == "indexes":
            if not args.name:
                print(
                    "Error: Table name is required for 'indexes' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            indexes = introspector.list_indexes(
                args.name, schema=None
            )
            data = _serialize_for_output(indexes)
            provider.display_results(
                data, title=f"Indexes of {args.name}"
            )

        elif args.type == "foreign-keys":
            if not args.name:
                print(
                    "Error: Table name is required for 'foreign-keys' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            fks = introspector.list_foreign_keys(
                args.name, schema=None
            )
            data = _serialize_for_output(fks)
            provider.display_results(
                data, title=f"Foreign Keys of {args.name}"
            )

        elif args.type == "triggers":
            triggers = introspector.list_triggers(
                table_name=args.name,
                schema=None
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "sequences":
            if args.name:
                info = introspector.get_sequence_info(
                    args.name, schema=None
                )
                if info is None:
                    print(
                        f"Error: Sequence '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Sequence {args.name}"
                )
            else:
                data = _serialize_for_output(
                    introspector.list_sequences(schema=None)
                )
                provider.display_results(data, title="Sequences")

        elif args.type == "table-options":
            if args.name:
                options = introspector.get_table_options(
                    args.name, schema=None
                )
                if options is None:
                    print(
                        f"Error: Table '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(options)]
                provider.display_results(
                    data, title=f"Table Options of {args.name}"
                )
            else:
                data = _serialize_for_output(
                    introspector.list_table_options(schema=None)
                )
                provider.display_results(data, title="Table Options")

        elif args.type == "database":
            info = introspector.get_database_info()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            backend.disconnect()


async def _handle_introspect_async(args, backend: AsyncMariaDBBackend, provider):
    """Handle introspect subcommand asynchronously."""
    try:
        await backend.connect()
        _refuse_version_gated_family(args, backend)

        introspector = backend.introspector

        if args.type == "tables":
            tables = await introspector.list_tables(
                schema=None,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            views = await introspector.list_views(
                schema=None
            )
            data = _serialize_for_output(views)
            provider.display_results(data, title="Views")

        elif args.type == "columns":
            if not args.name:
                print(
                    "Error: Table name is required for 'columns' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            columns = await introspector.list_columns(
                args.name, schema=None
            )
            data = _serialize_for_output(columns)
            provider.display_results(
                data, title=f"Columns of {args.name}"
            )

        elif args.type == "indexes":
            if not args.name:
                print(
                    "Error: Table name is required for 'indexes' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            indexes = await introspector.list_indexes(
                args.name, schema=None
            )
            data = _serialize_for_output(indexes)
            provider.display_results(
                data, title=f"Indexes of {args.name}"
            )

        elif args.type == "foreign-keys":
            if not args.name:
                print(
                    "Error: Table name is required for 'foreign-keys' introspection",
                    file=sys.stderr
                )
                sys.exit(1)
            fks = await introspector.list_foreign_keys(
                args.name, schema=None
            )
            data = _serialize_for_output(fks)
            provider.display_results(
                data, title=f"Foreign Keys of {args.name}"
            )

        elif args.type == "triggers":
            triggers = await introspector.list_triggers(
                table_name=args.name,
                schema=None
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "sequences":
            if args.name:
                info = await introspector.get_sequence_info(
                    args.name, schema=None
                )
                if info is None:
                    print(
                        f"Error: Sequence '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Sequence {args.name}"
                )
            else:
                data = _serialize_for_output(
                    await introspector.list_sequences(schema=None)
                )
                provider.display_results(data, title="Sequences")

        elif args.type == "table-options":
            if args.name:
                options = await introspector.get_table_options(
                    args.name, schema=None
                )
                if options is None:
                    print(
                        f"Error: Table '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(options)]
                provider.display_results(
                    data, title=f"Table Options of {args.name}"
                )
            else:
                data = _serialize_for_output(
                    await introspector.list_table_options(schema=None)
                )
                provider.display_results(data, title="Table Options")

        elif args.type == "database":
            info = await introspector.get_database_info()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            await backend.disconnect()
