# src/rhosocial/activerecord/backend/impl/mariadb/mixins/fulltext_search.py
"""MariaDB full-text search mixin.

MariaDB full-text search features:
- FULLTEXT indexes (InnoDB 10.0+, MyISAM all versions)
- FULLTEXT parser plugins (10.0+)
- Query expansion mode
- MATCH ... AGAINST expression
"""
from typing import List, Optional, Tuple


class MariaDBFullTextSearchMixin:
    """MariaDB full-text search mixin.

    MariaDB full-text search features:
    - FULLTEXT indexes (InnoDB 10.0+, MyISAM all versions)
    - FULLTEXT parser plugins (10.0+)
    - Query expansion mode
    - MATCH ... AGAINST expression
    """

    def supports_fulltext_index(self) -> bool:
        """MariaDB 10.0+ supports FULLTEXT for InnoDB."""
        return self.version >= (10, 0, 0)

    def supports_fulltext_parser(self) -> bool:
        """MariaDB supports FULLTEXT parser plugins."""
        return self.version >= (10, 0, 0)

    def supports_fulltext_query_expansion(self) -> bool:
        """MariaDB supports QUERY EXPANSION."""
        return True

    def format_fulltext_index_options(
        self,
        index: str,
        columns: List[str],
        index_type: Optional[str] = None,
        parser_name: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format FULLTEXT index options for CREATE TABLE / ALTER TABLE.

        Args:
            index: Index name
            columns: Indexed columns
            index_type: Index type (ignored for FULLTEXT)
            parser_name: Parser name for full-text search

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        col_parts = [self.format_identifier(c) for c in columns]
        sql = f"FULLTEXT {self.format_identifier(index)} ({', '.join(col_parts)})"
        if parser_name:
            sql += f" WITH PARSER {self.format_identifier(parser_name)}"
        return sql, ()

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression."""
        cols_sql = ", ".join(self.format_identifier(c) for c in columns)

        placeholder = self.get_parameter_placeholder()
        search_sql = placeholder
        search_params = (search_string,)

        if mode:
            mode_upper = mode.upper()
            if mode_upper == "NATURAL_LANGUAGE":
                mode_str = "IN NATURAL LANGUAGE MODE"
            elif mode_upper == "BOOLEAN":
                mode_str = "IN BOOLEAN MODE"
            elif mode_upper == "QUERY_EXPANSION":
                mode_str = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
            else:
                mode_str = ""
        else:
            mode_str = "IN NATURAL LANGUAGE MODE"

        sql = f"MATCH({cols_sql}) AGAINST({search_sql} {mode_str})"
        return sql, search_params


__all__ = ['MariaDBFullTextSearchMixin']