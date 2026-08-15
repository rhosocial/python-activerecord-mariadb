# src/rhosocial/activerecord/backend/impl/mariadb/protocols/json.py
"""MariaDB JSON function protocol."""

from typing import Any, List, Optional, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import JSONSupport


@runtime_checkable
class MariaDBJSONFunctionSupport(JSONSupport, Protocol):
    """MariaDB JSON function protocol.

    Feature Source: MariaDB 10.2.3+

    MariaDB JSON functions:
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
    - JSON_EXISTS: Check if JSON path exists (MariaDB 10.2.3+)
    - JSON_DEPTH: Get maximum depth (MariaDB 10.2.3+)
    - JSON_KEYS: Get keys from JSON object (MariaDB 10.2.3+)
    - JSON_LENGTH: Get length of JSON document (MariaDB 10.2.3+)
    - JSON_MERGE: Merge JSON documents (MariaDB 10.2.3+)

    MariaDB-specific JSON operators:
    - -> : Extract JSON value (MariaDB 10.2.7+)
    - ->> : Extract JSON value as text (MariaDB 10.2.7+)

    Note: MariaDB uses a LONGTEXT column with JSON validation constraint
    rather than a native JSON type. Most JSON functions are available
    but JSON_TABLE is not supported (unlike MySQL 8.0.4+).

    Official Documentation:
    - JSON Functions: https://mariadb.com/kb/en/json-functions/

    Version Requirements:
    - JSON functions: MariaDB 10.2.3+
    - JSON arrow operators: MariaDB 10.2.7+
    """

    def supports_json_type(self) -> bool:
        """Whether JSON data type is supported.

        MariaDB uses LONGTEXT with CHECK constraint for JSON validation,
        not a native JSON type. Returns True for compatibility.
        """
        ...

    def supports_json_merge_patch(self) -> bool:
        """Whether JSON_MERGE_PATCH is supported.

        MariaDB does not have JSON_MERGE_PATCH (unlike MySQL 8.0.3+).
        Use JSON_MERGE instead.
        """
        ...

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE is supported.

        MariaDB does NOT support JSON_TABLE (unlike MySQL 8.0.4+).
        Always returns False for MariaDB.
        """
        ...

    def supports_json_function(self, function_name: str) -> bool:
        """Whether a specific JSON function is supported.

        Args:
            function_name: Name of the JSON function (e.g. 'json_extract')

        Returns:
            True if the function is supported in current MariaDB version
        """
        ...

    def supports_json_arrow_operators(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        MariaDB does NOT support JSON arrow operators.
        """
        ...

    def supports_json_arrows(self) -> bool:
        """Deprecated singular alias for :meth:`supports_json_arrow_operators`.

        Kept for backwards compatibility with callers that predate the
        pluralised rename. MariaDB does NOT support JSON arrow operators.
        """
        ...

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function call.

        Args:
            json_doc: JSON document or column
            path: JSON path expression
            paths: Additional path expressions

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function call.

        Args:
            json_val: JSON value to unquote

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_object(
        self,
        key_value_pairs: List[Tuple[str, Any]]
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function call.

        Args:
            key_value_pairs: List of (key, value) tuples

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_array(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function call.

        Args:
            values: Values to include in the JSON array

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_contains(
        self,
        target: str,
        candidate: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function call.

        Args:
            target: JSON document or column to search in
            candidate: JSON value to search for
            path: Optional path within the target document

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_set(
        self,
        json_doc: str,
        path: str,
        value: Any,
        path_value_pairs: Optional[List[Tuple[str, Any]]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_SET function call.

        Args:
            json_doc: JSON document or column
            path: JSON path expression
            value: Value to set at the path
            path_value_pairs: Additional (path, value) pairs

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_remove(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_REMOVE function call.

        Args:
            json_doc: JSON document or column
            path: JSON path to remove
            paths: Additional paths to remove

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_type(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function call.

        Args:
            json_val: JSON value to type-check

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_valid(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function call.

        Args:
            json_val: Value to check for valid JSON

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_search(
        self,
        json_doc: str,
        search_str: str,
        path: Optional[str] = None,
        all: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON_SEARCH function call.

        Args:
            json_doc: JSON document or column to search in
            search_str: Search string (supports % and _ wildcards)
            path: Optional path to search within
            all: If True, return all matches; if False, return first match

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

    def format_json_query(
        self,
        json_doc: str,
        path: str
    ) -> Tuple[str, tuple]:
        """Format JSON_QUERY function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column
            path: JSON path expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_value(
        self,
        json_doc: str,
        path: str,
        returning_type: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_VALUE function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column
            path: JSON path expression
            returning_type: Optional RETURNING data type

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_exists(
        self,
        json_doc: str,
        path: str
    ) -> Tuple[str, tuple]:
        """Format JSON_EXISTS function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column
            path: JSON path expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def get_json_access_operator(self) -> str:
        """Get the JSON access operator for MariaDB.

        MariaDB uses -> and ->> operators (10.2.7+).

        Returns:
            The JSON access operator string.
        """
        ...

    def format_json_table_expression(
        self,
        expr: Any
    ) -> Tuple[str, tuple]:
        """Format JSON_TABLE expression.

        MariaDB does NOT support JSON_TABLE (unlike MySQL 8.0.4+).

        Args:
            expr: JsonTableExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_keys(
        self,
        json_doc: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_KEYS function call.

        Args:
            json_doc: JSON document or column
            path: Optional path within the document

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_merge(
        self,
        json_docs: List[str]
    ) -> Tuple[str, tuple]:
        """Format JSON_MERGE function call.

        Args:
            json_docs: List of JSON documents to merge

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_merge_patch(
        self,
        json_docs: List[str]
    ) -> Tuple[str, tuple]:
        """Format JSON_MERGE_PATCH function call.

        Args:
            json_docs: List of JSON documents to merge

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
