# src/rhosocial/activerecord/backend/impl/mariadb/functions/fulltext.py
"""
MariaDB full-text search function factories.

Functions: match_against
"""

from typing import Union, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


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
        A MariaDBMatchAgainstExpression instance representing MATCH ... AGAINST

    Note:
        The search string is bound as a driver parameter by the dialect's
        ``format_match_against``, never interpolated into the SQL text. Callers
        may therefore pass user-supplied search terms directly.

    Version: All MariaDB versions (with FULLTEXT index on MyISAM, Aria, or InnoDB)
    """
    from rhosocial.activerecord.backend.impl.mariadb.expression.match_against import (
        MariaDBMatchAgainstExpression,
    )

    if isinstance(columns, str):
        columns = [columns]

    return MariaDBMatchAgainstExpression(
        dialect,
        columns=columns,
        search_string=search_string,
        mode=mode,
    )


__all__ = [
    "match_against",
]