# src/rhosocial/activerecord/backend/impl/mariadb/protocols/fulltext_search.py
"""MariaDB full-text search protocol."""

from typing import List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBFullTextSearchSupport(Protocol):
    """MariaDB full-text search protocol.

    Note: Most interfaces are defined in generic IndexSupport protocol.
    This protocol only defines MariaDB-specific interfaces.

    Feature Source: MariaDB 10.0+ (with MyISAM/Aria/InnoDB)

    MariaDB full-text features:
    - FULLTEXT index on CHAR, VARCHAR, TEXT columns
    - FULLTEXT index on multiple columns
    - Natural language, Boolean, Query expansion modes
    - IN NATURAL LANGUAGE MODE, IN BOOLEAN MODE, WITH QUERY EXPANSION
    - Stopwords, minimum word length

    Official Documentation:
    - Full-Text Search: https://mariadb.com/kb/en/full-text-index-overview/

    Version Requirements:
    - FULLTEXT index: MariaDB 10.0+ (InnoDB), all versions (MyISAM/Aria)
    - FULLTEXT parser: MariaDB 5.x+
    - IN BOOLEAN MODE: MariaDB 5.x+
    - WITH QUERY EXPANSION: MariaDB 5.x+
    """

    def supports_fulltext_index(self) -> bool:
        """Whether FULLTEXT index is supported (MariaDB 10.0+ InnoDB)."""
        ...

    def supports_fulltext_parser(self) -> bool:
        """Whether custom full-text parser plugins are supported (MariaDB 5.x+)."""
        ...

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether query expansion mode is supported (MariaDB 5.x+)."""
        ...

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression.

        Args:
            columns: Column names to search
            search_string: Search string
            mode: Search mode (None, 'NATURAL_LANGUAGE', 'BOOLEAN', 'QUERY_EXPANSION')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fulltext_index_options(
        self,
        index: str,
        columns: List[str],
        index_type: Optional[str] = None,
        parser_name: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format FULLTEXT index options.

        Args:
            index: Index name (usually 'FULLTEXT')
            columns: Indexed columns
            index_type: Index type (BTREE, HASH - ignored for FULLTEXT)
            parser_name: Parser name for full-text search

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
