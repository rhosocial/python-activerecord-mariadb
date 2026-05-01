# src/rhosocial/activerecord/backend/impl/mariadb/functions/fulltext.py
"""
MariaDB full-text search function factories.

Functions: match_against
"""

from typing import Union, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases
from rhosocial.activerecord.backend.expression import operators

if TYPE_CHECKING:  # pragma: no cover
    from .dialect import MariaDBDialect


def match_against(
    dialect: "MariaDBDialect",
    columns: Union[str, List[str]],
    search_string: str,
    mode: Optional[str] = None,
) -> "bases.BaseExpression":
    """Creates a MATCH ... AGAINST expression for full-text search.

    Usage rules:
    - Natural language mode (default): match_against(dialect, "content", "search term")
    - Boolean mode: match_against(dialect, "content", "+term -exclude", mode="BOOLEAN")
    - Query expansion: match_against(dialect, "content", "search term", mode="QUERY_EXPANSION")

    Args:
        dialect: The MariaDB dialect instance
        columns: Column name(s) to search
        search_string: Search string
        mode: Search mode - "NATURAL_LANGUAGE", "BOOLEAN", or "QUERY_EXPANSION"

    Returns:
        A BaseExpression instance representing MATCH ... AGAINST

    Version: All MariaDB versions (with FULLTEXT index on MyISAM, Aria, or InnoDB)
    """
    from rhosocial.activerecord.backend.expression import core

    if isinstance(columns, str):
        columns = [columns]

    col_parts = []
    for col in columns:
        if isinstance(col, bases.BaseExpression):
            col_parts.append(str(col))
        else:
            col_parts.append(dialect.format_identifier(col))

    match_args = ", ".join(col_parts)
    against_arg = f"'{search_string}'"

    if mode == "BOOLEAN":
        against_arg += " IN BOOLEAN MODE"
    elif mode == "QUERY_EXPANSION":
        against_arg += " WITH QUERY EXPANSION"

    sql = f"MATCH ({match_args}) AGAINST({against_arg})"
    return operators.RawSQLExpression(dialect, sql)


__all__ = [
    "match_against",
]