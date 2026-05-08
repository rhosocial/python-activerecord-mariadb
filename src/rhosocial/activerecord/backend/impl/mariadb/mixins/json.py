# src/rhosocial/activerecord/backend/impl/mariadb/mixins/json.py
"""MariaDB JSON function mixin.

MariaDB 10.2.3+ supports JSON functions, and 10.2.7+ supports
JSON arrow operators (-> and ->>).
"""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.query_sources import JSONTableExpression


class MariaDBJSONMixin:
    """MariaDB JSON function support mixin.

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
    - JSON_KEYS: Get keys from JSON object
    - JSON_LENGTH: Get length of JSON document
    - JSON_DEPTH: Get depth of JSON document
    - JSON_MERGE: Merge JSON documents
    - JSON_MERGE_PATCH: Merge JSON documents (RFC 7396)
    - JSON_SEARCH: Search in JSON
    - JSON_ARRAY_APPEND: Append to JSON array
    - JSON_QUOTE: Quote JSON value
    - JSON_QUERY: Query JSON path (MariaDB-specific)
    - JSON_VALUE: Extract scalar value (MariaDB-specific)

    MariaDB-specific JSON operators:
    - -> : Extract JSON value (MariaDB 10.2.7+)
    - ->> : Extract JSON value as text (MariaDB 10.2.7+)

    Official Documentation:
    - https://mariadb.com/kb/en/json-functions/

    Version Requirements:
    - JSON functions: MariaDB 10.2.3+
    - JSON arrow operators: MariaDB 10.2.7+
    """

    def supports_json_type(self) -> bool:
        """Whether JSON data type is supported.

        MariaDB 10.2.3+ supports JSON type and functions.

        Returns:
            True if MariaDB version >= 10.2.3.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_FUNCTIONS']

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported.

        Args:
            function_name: Name of JSON function.

        Returns:
            True if function is supported in current MariaDB version.
        """
        if self.version < MARIADB_VERSION_BOUNDARIES['JSON_FUNCTIONS']:
            return False

        json_functions = {
            'json_extract', 'json_unquote', 'json_object', 'json_array',
            'json_contains', 'json_set', 'json_insert', 'json_replace',
            'json_remove', 'json_type', 'json_valid', 'json_keys',
            'json_length', 'json_depth', 'json_merge', 'json_merge_patch',
            'json_search', 'json_array_append', 'json_quote',
            'json_query', 'json_value',
        }
        return function_name.lower() in json_functions

    def supports_json_arrows(self) -> bool:
        """Whether JSON arrow operators are supported.

        MariaDB 10.2.7+ supports JSON arrow operators (-> and ->>).

        Returns:
            True if MariaDB version >= 10.2.7.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_ARROWS']

    def get_json_access_operator(self) -> str:
        """Get JSON access operator.

        MariaDB 10.2.7+ uses -> for JSON access.

        Returns:
            '->' if supported, empty string otherwise.
        """
        if self.version >= MARIADB_VERSION_BOUNDARIES['JSON_ARROWS']:
            return "->"
        return ""

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE function is supported.

        MariaDB does NOT support JSON_TABLE function.
        Use json_table() stored procedure or other alternatives.

        Returns:
            False.
        """
        return False

    def format_json_table_expression(
        self, expr: "JSONTableExpression"
    ) -> Tuple[str, Tuple]:
        path = expr.path.replace("'", "''")
        parts = ["JSON_TABLE(", expr.json_doc, ",", f"'{path}'", " COLUMNS ("]
        col_parts_list = []
        for col in expr.columns:
            col_parts = []
            if col.ordinality:
                col_parts.append(f"{col.name} FOR ORDINALITY")
            elif col.exists:
                col_path = col.path.replace("'", "''") if col.path else ""
                col_parts.append(f"{col.name} INT EXISTS (PATH '{col_path}')")
            else:
                col_parts.append(f"{col.name} {col.type}")
                if col.path:
                    col_path = col.path.replace("'", "''")
                    col_parts.append(f"PATH '{col_path}'")
            col_parts_list.append(' '.join(col_parts))
        parts.append(', '.join(col_parts_list))
        parts.append("))")
        result = ''.join(parts)
        if expr.alias:
            result += f" AS {self.format_identifier(expr.alias)}"
        return result, ()

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function.

        Args:
            json_doc: JSON document or column name.
            path: JSON path expression.
            paths: Additional paths for multiple extraction.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        all_paths = [path]
        if paths:
            all_paths.extend(paths)

        path_placeholders = ', '.join(['%s' for _ in all_paths])
        return f"JSON_EXTRACT({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function.

        Args:
            json_val: JSON value expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_UNQUOTE({json_val})", ()

    def format_json_object(
        self,
        key_value_pairs: List[Tuple[str, Any]]
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function.

        Args:
            key_value_pairs: List of (key, value) tuples.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not key_value_pairs:
            return "JSON_OBJECT()", ()

        parts = []
        params: List[Any] = []

        for key, value in key_value_pairs:
            parts.append('%s')
            parts.append('%s')
            params.append(key)
            params.append(value)

        return f"JSON_OBJECT({', '.join(parts)})", tuple(params)

    def format_json_array(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function.

        Args:
            values: List of values for the array.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not values:
            return "JSON_ARRAY()", ()

        placeholders = ', '.join(['%s' for _ in values])
        return f"JSON_ARRAY({placeholders})", tuple(values)

    def format_json_contains(
        self,
        target: str,
        candidate: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function.

        Args:
            target: Target JSON document.
            candidate: Candidate value to search for.
            path: Optional JSON path.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if path:
            return f"JSON_CONTAINS({target}, %s, %s)", (candidate, path)
        return f"JSON_CONTAINS({target}, %s)", (candidate,)

    def format_json_set(
        self,
        json_doc: str,
        path: str,
        value: Any,
        path_value_pairs: Optional[List[Tuple[str, Any]]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_SET function.

        Args:
            json_doc: JSON document.
            path: JSON path.
            value: Value to set.
            path_value_pairs: Additional (path, value) pairs.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        all_pairs = [(path, value)]
        if path_value_pairs:
            all_pairs.extend(path_value_pairs)

        parts = []
        params: List[Any] = []

        for p, v in all_pairs:
            parts.append('%s')
            parts.append('%s')
            params.append(p)
            params.append(v)

        return f"JSON_SET({json_doc}, {', '.join(parts)})", tuple(params)

    def format_json_remove(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_REMOVE function.

        Args:
            json_doc: JSON document.
            path: JSON path to remove.
            paths: Additional paths to remove.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        all_paths = [path]
        if paths:
            all_paths.extend(paths)

        path_placeholders = ', '.join(['%s' for _ in all_paths])
        return f"JSON_REMOVE({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_type(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function.

        Args:
            json_val: JSON value expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_TYPE({json_val})", ()

    def format_json_valid(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function.

        Args:
            json_val: JSON value expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_VALID({json_val})", ()

    def format_json_keys(
        self,
        json_doc: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_KEYS function.

        Args:
            json_doc: JSON document.
            path: Optional JSON path.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if path:
            return f"JSON_KEYS({json_doc}, %s)", (path,)
        return f"JSON_KEYS({json_doc})", ()

    def format_json_search(
        self,
        json_doc: str,
        search_str: str,
        path: Optional[str] = None,
        all_: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON_SEARCH function.

        Args:
            json_doc: JSON document.
            search_str: String to search for.
            path: Optional JSON path.
            all_: If True, return all matches; otherwise, return first.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        one_or_all = "'all'" if all_ else "'one'"
        if path:
            return f"JSON_SEARCH({json_doc}, {one_or_all}, %s, NULL, %s)", (search_str, path)
        return f"JSON_SEARCH({json_doc}, {one_or_all}, %s)", (search_str,)

    def format_json_arrow(
        self,
        json_doc: str,
        path: str,
        unquote: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON arrow operator (-> or ->>).

        MariaDB 10.2.7+ supports this syntax.

        Args:
            json_doc: JSON document or column name.
            path: JSON path expression.
            unquote: If True, use ->> (unquoted result).

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If arrow operators not supported.
        """
        if not self.supports_json_arrows():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "JSON arrow operators",
                "JSON arrow operators (-> and ->>) require MariaDB 10.2.7 or later."
            )

        op = "->>" if unquote else "->"
        return f"{json_doc}{op}'{path}'", ()

    def format_json_merge(
        self,
        json_docs: List[str]
    ) -> Tuple[str, tuple]:
        """Format JSON_MERGE function.

        Args:
            json_docs: List of JSON documents to merge.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if len(json_docs) < 2:
            raise ValueError("JSON_MERGE requires at least 2 JSON documents")
        return f"JSON_MERGE({', '.join(json_docs)})", ()

    def format_json_merge_patch(
        self,
        json_docs: List[str]
    ) -> Tuple[str, tuple]:
        """Format JSON_MERGE_PATCH function.

        Args:
            json_docs: List of JSON documents to merge.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if len(json_docs) < 2:
            raise ValueError("JSON_MERGE_PATCH requires at least 2 JSON documents")
        return f"JSON_MERGE_PATCH({', '.join(json_docs)})", ()


__all__ = ['MariaDBJSONMixin']
