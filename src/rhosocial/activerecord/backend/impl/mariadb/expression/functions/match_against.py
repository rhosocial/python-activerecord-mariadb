# src/rhosocial/activerecord/backend/impl/mariadb/expression/functions/match_against.py
"""
MariaDB-specific MATCH...AGAINST expression.

MariaDB's MATCH...AGAINST expression node. The mode vocabulary it accepts
lives in ``..predicates.match_against``.
"""

from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases.bases import SQLValue
from rhosocial.activerecord.backend.expression.bases.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBMatchAgainstExpression(
    AliasableMixin,
    ComparisonMixin,
    SQLValue,
):
    """MariaDB MATCH...AGAINST expression.

    Generates MATCH(col1, col2, ...) AGAINST(search_string [IN mode]) syntax.
    Supported in MariaDB 5.5+ (with FULLTEXT index).

    Attributes:
        columns: Column names to search
        search_string: Search term
        mode: Search mode - NATURAL_LANGUAGE, BOOLEAN, or NATURAL_LANGUAGE_WITH_QUERY_EXPANSION

    Example:
        >>> expr = MariaDBMatchAgainstExpression(
        ...     dialect,
        ...     columns=['title', 'content'],
        ...     search_string='MariaDB',
        ...     mode='NATURAL_LANGUAGE'
        ... )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None,
        *,
        alias: Optional[str] = None,
    ):
        """Initialize MATCH...AGAINST expression.

        Args:
            dialect: SQL dialect
            columns: Column names to search
            search_string: Search term
            mode: Search mode
        """
        super().__init__(dialect)
        self.columns = columns
        self.search_string = search_string
        self.mode = mode
        self.alias = alias  # Initialize alias attribute

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_match_against_expression"


__all__ = [
    "MariaDBMatchAgainstExpression",
]
