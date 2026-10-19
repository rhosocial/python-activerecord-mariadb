# src/rhosocial/activerecord/backend/impl/mariadb/expression/match_against.py
"""
MariaDB-specific MATCH...AGAINST expression.

This module provides MariaDBMatchAgainstExpression for MariaDB's full-text search functionality.
"""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValue
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MatchAgainstMode(str, Enum):
    """Full-text search modes, as the wire word form.

    A closed set, so it takes an enum rather than string constants on a class:
    the constant-class form accepted any string at the call site, which left
    the set closed in the documentation only. The ``str`` base with ``__str__``
    pinned to ``str.__str__`` makes the member the word it carries.
    """

    #: A member *is* the word it carries (org rules §11.3).
    __str__ = str.__str__

    NATURAL_LANGUAGE = "NATURAL LANGUAGE"
    BOOLEAN = "BOOLEAN"
    NATURAL_LANGUAGE_WITH_QUERY_EXPANSION = "NATURAL LANGUAGE WITH QUERY EXPANSION"


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
        return "format_match_against"


__all__ = [
    "MariaDBMatchAgainstExpression",
    "MatchAgainstMode",
]
