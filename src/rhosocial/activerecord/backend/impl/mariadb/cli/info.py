# src/rhosocial/activerecord/backend/impl/mariadb/cli/info.py
"""info subcommand - Display MariaDB environment information.

info can optionally connect to a database for version introspection,
falling back to --version flag when no connection is available.
"""

import argparse
import json
from typing import Any, Dict, List, Tuple

from rhosocial.activerecord.backend.dialect import capabilities as _cap
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, FilterClauseSupport,
    ReturningSupport, UpsertSupport, LateralJoinSupport, JoinSupport,
    JSONSupport, ExplainSupport, GraphSupport,
    SetOperationSupport, ViewObjectSupport,
    TableObjectSupport, TruncateSupport, GeneratedColumnSupport,
    TriggerObjectSupport, RoutineObjectSupport,
    AdvancedGroupingSupport, ArraySupport, ILIKESupport,
    IndexObjectSupport, LockingSupport, MergeSupport,
    OrderedSetAggregationSupport, QualifyClauseSupport,
    NamespaceSupport, SequenceObjectSupport, TemporalTableSupport,
)
from rhosocial.activerecord.backend.impl.mariadb.protocols import (
    MariaDBSequenceSupport,
    MariaDBReturningSupport,
    MariaDBIntersectExceptSupport,
    MariaDBSystemVersioningSupport,
    MariaDBJSONFunctionSupport,
    MariaDBFullTextSearchSupport,
    MariaDBWindowFunctionSupport,
    MariaDBCTESupport,
)
from rhosocial.activerecord.logging.defaults import get_logger

from .connection import add_connection_args, add_version_arg, resolve_connection_config_from_args
from .output import INFO_OUTPUT_CHOICES, create_provider, RICH_AVAILABLE

logger = get_logger("rhosocial.activerecord.backend.mariadb.cli.info")

# Groups that are specific to MariaDB dialect
DIALECT_SPECIFIC_GROUPS = {"MariaDB-specific"}

# Protocol family groups for display
PROTOCOL_FAMILY_GROUPS: Dict[str, list] = {
    "Query Features": [
        WindowFunctionSupport, CTESupport, FilterClauseSupport,
        SetOperationSupport, AdvancedGroupingSupport,
    ],
    "JOIN Support": [JoinSupport, LateralJoinSupport],
    "Data Types": [JSONSupport, ArraySupport],
    "DML Features": [
        ReturningSupport, UpsertSupport, MergeSupport,
        OrderedSetAggregationSupport,
    ],
    "Transaction & Locking": [LockingSupport, TemporalTableSupport],
    "Query Analysis": [ExplainSupport, GraphSupport, QualifyClauseSupport],
    "DDL - Table": [TableObjectSupport, TruncateSupport, GeneratedColumnSupport],
    "DDL - View": [ViewObjectSupport],
    "DDL - Namespace & Index": [NamespaceSupport, IndexObjectSupport],
    "DDL - Sequence & Trigger": [
        SequenceObjectSupport, TriggerObjectSupport, RoutineObjectSupport,
    ],
    "String Matching": [ILIKESupport],
    "MariaDB-specific": [
        MariaDBSequenceSupport, MariaDBReturningSupport,
        MariaDBIntersectExceptSupport, MariaDBSystemVersioningSupport,
        MariaDBJSONFunctionSupport, MariaDBFullTextSearchSupport,
        MariaDBWindowFunctionSupport, MariaDBCTESupport,
    ],
}

# All possible test arguments for methods that require parameters
SUPPORT_METHOD_ALL_ARGS: Dict[str, List[str]] = {
    # ExplainSupport: all possible format types
    "supports_explain_format": ["TEXT", "JSON", "TREE", "XML", "YAML", "DOT"],
    # MariaDBJSONFunctionSupport: JSON functions with version-specific support
    "supports_json_function": [
        "JSON_EXTRACT", "JSON_ARRAY", "JSON_OBJECT", "JSON_MERGE",
        "JSON_TABLE", "JSON_VALUE", "JSON_SCHEMA_VALID", "JSON_MERGE_PATCH",
    ],
}


def create_parser(subparsers):
    """Create the info subcommand parser."""
    parser = subparsers.add_parser(
        'info',
        help='Display MariaDB environment information',
        epilog="""Examples:
  # Show info using default version (10.11.0)
  %(prog)s

  # Show info for a specific version
  %(prog)s --version 10.5.0

  # Show info from actual database connection
  %(prog)s --host localhost --database mydb --user root --password secret

  # Output as JSON
  %(prog)s -o json

  # Detailed protocol support
  %(prog)s -vv
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format (only table and json; info has nested output)
    parser.add_argument(
        '-o', '--output',
        choices=INFO_OUTPUT_CHOICES,
        default='table',
        help='Output format (default: table)',
    )

    # Connection arguments (optional; info can work without a database)
    add_connection_args(parser)

    # Version override
    add_version_arg(parser)

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity. -v for families, -vv for details.',
    )

    # Rich display options
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.',
    )

    return parser


def handle(args):
    """Handle the info subcommand."""
    create_provider(args.output, ascii_borders=args.rich_ascii)

    # Track whether we're using an actual database or defaults
    is_connected = False
    dialect = None
    version_display = None
    variables: Dict[str, Any] = {}
    variables_source = "no live connection; server variables were not queried"

    named_conn = getattr(args, "named_connection", None)
    if named_conn or args.database:
        try:
            from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
            config = resolve_connection_config_from_args(args)
            backend = MariaDBBackend(connection_config=config)
            backend.connect()
            backend.introspect_and_adapt()

            # Use the adapted dialect from backend
            dialect = backend.dialect
            version_tuple = backend.get_server_version()
            if version_tuple:
                version_display = (
                    f"{version_tuple[0]}.{version_tuple[1]}"
                    f".{version_tuple[2]}"
                )
            is_connected = True

            # Read server variables through the existing SHOW VARIABLES status
            # introspector. No new database queries are introduced here; if the
            # introspector cannot answer, the dialect information still stands.
            try:
                config_items = backend.introspector.status.list_configuration()
                variables = {item.name: item.value for item in config_items}
                variables_source = "SHOW VARIABLES via the status introspector (live connection)"
            except Exception as e:
                logger.warning("Could not read server variables: %s", e)
                variables_source = "SHOW VARIABLES via the status introspector unavailable"

            backend.disconnect()
        except Exception as e:
            logger.warning(
                "Could not connect to database for introspection: %s", e
            )
            logger.warning(
                "Using default values for dialect information."
            )

    # Create default dialect if not connected
    if dialect is None:
        # Parse version from command line or use default
        actual_version = args.version
        if actual_version:
            version = parse_version(actual_version)
        else:
            version = (10, 11, 0)  # Default version
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        dialect = MariaDBDialect(version=version)
        version_display = f"{version[0]}.{version[1]}.{version[2]}"

    # Capability and suggestion reports are computed from the (possibly offline)
    # dialect through the shared core helper.
    capabilities = _cap.build_capability_report(
        dialect,
        family_groups=PROTOCOL_FAMILY_GROUPS,
        dialect_specific_groups=DIALECT_SPECIFIC_GROUPS,
        all_args=SUPPORT_METHOD_ALL_ARGS,
        verbose=args.verbose,
    )
    suggestions = _cap.build_suggestion_report(dialect, args.verbose)

    # Unified structure for JSON output
    info = {
        "database": {
            "type": "mariadb",
            "version": version_display,
            "version_tuple": list(dialect.version),
            "connected": is_connected,
        },
        "server": {
            "version": version_display,
            "variables": variables,
            "source": variables_source,
            "connected": is_connected,
        },
        "features": {},
        "capabilities": capabilities,
        "suggestions": suggestions,
        # compatibility alias for one release cycle
        "protocols": capabilities,
    }

    if args.output == "json" or not RICH_AVAILABLE:
        print(json.dumps(info, indent=2))
    else:
        # Use legacy structure for rich display
        info_legacy = {
            "mariadb": info["database"],
            "protocols": capabilities,
            "suggestions": suggestions,
        }
        _display_info_rich(
            info_legacy, args.verbose, version_display, is_connected
        )

    return info


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string like '10.11.0' to tuple."""
    parts = version_str.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


def _get_status_style(pct: float) -> Tuple[str, str]:
    """Get color and symbol based on percentage."""
    if pct == 100:
        return "green", "[OK]"
    elif pct >= 50:
        return "yellow", "[~]"
    elif pct > 0:
        return "red", "[~]"
    else:
        return "red", "[X]"


def _format_method_display(method: str) -> str:
    """Format method name for display."""
    return (
        method.replace("supports_", "")
        .replace("_", " ")
        .replace("is_", "")
        .replace("_available", "")
    )


def _display_method_details(console: Any, method: str, value: Any) -> None:
    """Display detailed method support information."""
    method_display = _format_method_display(method)

    if isinstance(value, dict):
        console.print(f" [dim]{method_display}:[/dim]")
        for arg, supported in value.get("args", {}).items():
            m_status = (
                "[green][OK][/green]" if supported
                else "[red][X][/red]"
            )
            console.print(f" {m_status} {arg}")
    else:
        m_status = (
            "[green][OK][/green]" if value
            else "[red][X][/red]"
        )
        console.print(f" {m_status} {method_display}")


def _display_protocol_item(
    console: Any,
    protocol_name: str,
    stats: Dict[str, Any],
    verbose: int
) -> None:
    """Display a single protocol's support information."""
    pct = stats["percentage"]
    color, symbol = _get_status_style(pct)

    bar_len = 20
    filled = int(pct / 100 * bar_len)
    progress_bar = "#" * filled + "-" * (bar_len - filled)

    sup = stats["supported"]
    tot = stats["total"]
    origin = stats.get("origin", "")
    origin_tag = f" [dim][{origin}][/dim]" if origin else ""
    console.print(
        f" [{color}]{symbol}[/{color}] {protocol_name}{origin_tag}: "
        f"[{color}]{progress_bar}[/{color}] "
        f"{pct:.0f}% ({sup}/{tot})"
    )

    if verbose >= 2 and "methods" in stats:
        for method, value in stats["methods"].items():
            _display_method_details(console, method, value)


def _display_protocol_group(
    console: Any,
    group_name: str,
    protocols: Dict[str, Any],
    verbose: int
) -> None:
    """Display a protocol group's support information."""
    if group_name in DIALECT_SPECIFIC_GROUPS:
        console.print(
            f"\n [bold underline]{group_name}:[/bold underline] "
            f"[dim](dialect-specific)[/dim]"
        )
    else:
        console.print(
            f"\n [bold underline]{group_name}:[/bold underline]"
        )

    for protocol_name, stats in protocols.items():
        _display_protocol_item(console, protocol_name, stats, verbose)


def _display_info_rich(
    info: Dict, verbose: int, version_display: str,
    is_connected: bool = True
):
    """Display info using rich console."""
    from rich.console import Console

    console = Console(force_terminal=True)

    console.print(
        "\n[bold cyan]MariaDB Environment Information[/bold cyan]\n"
    )

    if is_connected:
        console.print(
            f"[bold]MariaDB Version:[/bold] {version_display} "
            f"[dim](from actual connection)[/dim]\n"
        )
    else:
        console.print(
            f"[bold]MariaDB Version:[/bold] {version_display} "
            f"[yellow](default value - no database connection)[/yellow]\n"
        )

    label = "Detailed" if verbose >= 2 else "Family Overview"
    console.print(
        f"[bold green]Protocol Support ({label}):[/bold green]"
    )

    for group_name, protocols in info["protocols"].items():
        _display_protocol_group(console, group_name, protocols, verbose)

    # Suggestion support (independent of capability support)
    suggestions = info.get("suggestions", {})
    if suggestions:
        console.print("\n[bold green]Suggestion Support:[/bold green]")
        for proto_name, entry in suggestions.items():
            supported = entry.get("supported", False)
            symbol = "[OK]" if supported else "[X]"
            color = "green" if supported else "red"
            console.print(f" [{color}]{symbol}[/{color}] {proto_name}")

    console.print()
