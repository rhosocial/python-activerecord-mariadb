# src/rhosocial/activerecord/backend/impl/mariadb/protocols.py
"""MariaDB dialect-specific protocol definitions.

This module defines protocols for features exclusive to MariaDB,
which are not part of the SQL standard and may differ from MySQL.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBSequenceSupport(Protocol):
    """MariaDB SEQUENCE protocol.

    Feature Source: MariaDB 10.3+ (not available in MySQL)

    MariaDB SEQUENCE features:
    - CREATE SEQUENCE: Create sequence object
    - NEXTVAL: Get next value
    - CURRVAL: Get current value
    - SETVAL: Set sequence value
    - RESTART: Restart sequence
    - CACHE/NOCACHE: Cache options
    - CYCLE/NOCYCLE: Cycle behavior

    Official Documentation:
    - https://mariadb.com/kb/en/sequence-storage-engine/
    - https://mariadb.com/kb/en/create-sequence/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        MariaDB 10.3+ supports SEQUENCE storage engine.
        """
        ...

    def format_create_sequence_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_drop_sequence_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_nextval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format NEXTVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_currval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format CURRVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_setval(
        self,
        sequence_name: str,
        value: int,
        is_called: bool = True
    ) -> Tuple[str, tuple]:
        """Format SETVAL expression.

        Args:
            sequence_name: Name of the sequence
            value: Value to set
            is_called: If True, next NEXTVAL returns value + increment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBReturningSupport(Protocol):
    """MariaDB RETURNING clause protocol.

    Feature Source: MariaDB 10.5+ (not available in MySQL)

    MariaDB RETURNING features:
    - RETURNING *: Return all columns
    - RETURNING col1, col2: Return specific columns
    - RETURNING expr AS alias: Return expressions with aliases

    Official Documentation:
    - https://mariadb.com/kb/en/insert-on-duplicate/

    Version Requirements:
    - MariaDB 10.5.0+
    """

    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported.

        MariaDB 10.5+ supports RETURNING for INSERT, DELETE, REPLACE.
        """
        ...

    def supports_returning_expression(self) -> bool:
        """Whether expressions are supported in RETURNING.

        MariaDB 10.5+ supports expressions and aliases in RETURNING.
        """
        ...

    def format_returning_clause(
        self,
        columns: Optional[List[str]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None,
        aliases: Optional[Dict[str, str]] = None
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause for MariaDB.

        Args:
            columns: Column names to return
            expressions: Expressions with optional aliases
            aliases: Column/expression to alias mappings

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBIntersectExceptSupport(Protocol):
    """MariaDB INTERSECT/EXCEPT protocol.

    Feature Source: MariaDB 10.3+ (MySQL 8.0.31+ also supports)

    MariaDB INTERSECT/EXCEPT features:
    - INTERSECT: Return rows in both result sets
    - INTERSECT ALL: Include duplicates
    - EXCEPT: Return rows in first but not second
    - EXCEPT ALL: Include duplicates

    Official Documentation:
    - https://mariadb.com/kb/en/intersect/
    - https://mariadb.com/kb/en/except/

    Version Requirements:
    - MariaDB 10.3+ (native support)
    """

    def supports_intersect(self) -> bool:
        """Whether INTERSECT is supported.

        MariaDB 10.3+ supports INTERSECT.
        """
        ...

    def supports_except(self) -> bool:
        """Whether EXCEPT is supported.

        MariaDB 10.3+ supports EXCEPT.
        """
        ...

    def supports_intersect_all(self) -> bool:
        """Whether INTERSECT ALL is supported.

        MariaDB 10.3+ supports INTERSECT ALL.
        """
        ...

    def supports_except_all(self) -> bool:
        """Whether EXCEPT ALL is supported.

        MariaDB 10.3+ supports EXCEPT ALL.
        """
        ...


@runtime_checkable
class MariaDBSystemVersioningSupport(Protocol):
    """MariaDB System-Versioned Tables protocol.

    Feature Source: MariaDB 10.3+ (not available in MySQL)

    MariaDB System-Versioning features:
    - FOR SYSTEM_TIME AS OF: Query historical data
    - FOR SYSTEM_TIME BETWEEN: Query data between timestamps
    - FOR SYSTEM_TIME FROM...TO: Query data in range
    - WITH SYSTEM VERSIONING: Create versioned table
    - WITHOUT SYSTEM VERSIONING: Disable versioning

    Official Documentation:
    - https://mariadb.com/kb/en/system-versioned-tables/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_system_versioning(self) -> bool:
        """Whether system-versioned tables are supported.

        MariaDB 10.3+ supports system-versioned tables.
        """
        ...

    def format_system_time_as_of(
        self,
        timestamp: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME AS OF clause.

        Args:
            timestamp: Point in time to query

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_system_time_between(
        self,
        start: Any,
        end: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME BETWEEN clause.

        Args:
            start: Start timestamp
            end: End timestamp

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBJSONFunctionSupport(Protocol):
    """MariaDB JSON function protocol.

    Feature Source: MariaDB 10.2.3+

    MariaDB JSON functions (similar to MySQL with some differences):
    - JSON_EXTRACT: Extract data from JSON documents
    - JSON_UNQUOTE: Unquote JSON value
    - JSON_OBJECT: Create JSON object
    - JSON_ARRAY: Create JSON array
    - JSON_CONTAINS: Check if JSON contains value
    - JSON_SET: Set value in JSON
    - JSON_INSERT: Insert value into JSON
    - JSON_REPLACE: Replace value in JSON
    - JSON_REMOVE: Remove data from JSON
    - JSON_TYPE: Get type of JSON value
    - JSON_VALID: Validate JSON
    - JSON_QUERY: JSON path query (MariaDB 10.2.3+)
    - JSON_VALUE: Extract scalar value (MariaDB 10.2.3+)

    MariaDB-specific JSON operators:
    - -> : Extract JSON value (MariaDB 10.2.7+)
    - ->> : Extract JSON value as text (MariaDB 10.2.7+)

    Official Documentation:
    - https://mariadb.com/kb/en/json-functions/

    Version Requirements:
    - JSON functions: MariaDB 10.2.3+
    - JSON arrow operators: MariaDB 10.2.7+
    """

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported.

        Args:
            function_name: Name of JSON function

        Returns:
            True if function is supported in current MariaDB version
        """
        ...

    def supports_json_arrows(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        MariaDB 10.2.7+ supports JSON arrow operators.
        """
        ...

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function.

        Args:
            json_doc: JSON document or column name
            path: JSON path expression
            paths: Additional paths for multiple extraction

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_arrow(
        self,
        json_doc: str,
        path: str,
        unquote: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON arrow operator (-> or ->>).

        Args:
            json_doc: JSON document or column name
            path: JSON path expression
            unquote: If True, use ->> (unquoted result)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBFullTextSearchSupport(Protocol):
    """MariaDB Full-Text Search protocol.

    Feature Source: MariaDB 10.0+ (with MyISAM/Aria/InnoDB)

    MariaDB Full-Text Search features:
    - MATCH ... AGAINST: Full-text search
    - IN NATURAL LANGUAGE MODE: Natural language search
    - IN BOOLEAN MODE: Boolean search with operators
    - WITH QUERY EXPANSION: Query expansion
    - IN BOOLEAN MODE operators: +, -, *, "", ()

    Official Documentation:
    - https://mariadb.com/kb/en/full-text-index-overview/

    Version Requirements:
    - MyISAM: All versions
    - InnoDB: MariaDB 10.0+
    - Aria: All versions
    """

    def supports_fulltext_index(self) -> bool:
        """Whether FULLTEXT indexes are supported.

        MariaDB supports FULLTEXT indexes on MyISAM, Aria, and InnoDB.
        """
        ...

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: str = 'natural_language',
        query_expansion: bool = False
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression.

        Args:
            columns: Columns to search
            search_string: Search string
            mode: Search mode ('natural_language', 'boolean')
            query_expansion: Enable query expansion

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBWindowFunctionSupport(Protocol):
    """MariaDB Window Function protocol.

    Feature Source: MariaDB 10.2+ (MySQL 8.0+)

    MariaDB Window Function features:
    - ROW_NUMBER(): Assign row numbers
    - RANK(): Rank rows with gaps
    - DENSE_RANK(): Rank rows without gaps
    - LEAD/LAG: Access other rows
    - FIRST_VALUE/LAST_VALUE: First/last values in frame
    - Aggregate functions with OVER clause

    Official Documentation:
    - https://mariadb.com/kb/en/window-functions/

    Version Requirements:
    - MariaDB 10.2+
    """

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported.

        MariaDB 10.2+ supports window functions.
        """
        ...

    def supports_named_windows(self) -> bool:
        """Whether named window definitions are supported.

        MariaDB 10.2+ supports named windows.
        """
        ...


@runtime_checkable
class MariaDBCTESupport(Protocol):
    """MariaDB Common Table Expression (CTE) protocol.

    Feature Source: MariaDB 10.2+ (MySQL 8.0+)

    MariaDB CTE features:
    - WITH clause: Define CTEs
    - Recursive CTEs: WITH RECURSIVE
    - Multiple CTEs: Comma-separated

    Official Documentation:
    - https://mariadb.com/kb/en/common-table-expressions/

    Version Requirements:
    - MariaDB 10.2+
    """

    def supports_cte(self) -> bool:
        """Whether CTEs (WITH clause) are supported.

        MariaDB 10.2+ supports CTEs.
        """
        ...

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported.

        MariaDB 10.2+ supports recursive CTEs.
        """
        ...


__all__ = [
    'MariaDBSequenceSupport',
    'MariaDBReturningSupport',
    'MariaDBIntersectExceptSupport',
    'MariaDBSystemVersioningSupport',
    'MariaDBJSONFunctionSupport',
    'MariaDBFullTextSearchSupport',
    'MariaDBWindowFunctionSupport',
    'MariaDBCTESupport',
]
