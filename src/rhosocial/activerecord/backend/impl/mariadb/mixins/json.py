# src/rhosocial/activerecord/backend/impl/mariadb/mixins/json.py
"""MariaDB JSON function mixin.

MariaDB 10.2.3+ supports JSON functions, and 10.2.7+ supports
JSON arrow operators (-> and ->>).
"""
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES
from rhosocial.activerecord.backend.expression import bases

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.advanced_functions import JSONExpression


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

    def supports_json_arrow_operators(self) -> bool:
        """Whether native JSON arrow operators (-> and ->>) are usable.

        MariaDB has no native ``->`` / ``->>`` on any release this backend
        supports in a form that can be emitted unconditionally. The 13.1
        ``column -> path`` syntax additionally only applies to a real JSON
        *column*: ``CAST(x AS JSON) -> '$'`` is a syntax error even on 13.1,
        so it is not a safe default for the general expression path.

        This backend therefore renders ``->`` / ``->>`` through
        ``JSON_EXTRACT`` / ``JSON_UNQUOTE(JSON_EXTRACT(...))``, which is
        equivalent and works on every supported version. Use
        :meth:`supports_json_arrow_operators_native` to ask whether the
        13.1 native form is available for a column operand.
        """
        return False

    def supports_json_arrow_operators_native(self) -> bool:
        """Whether MariaDB 13.1's native ``->`` / ``->>`` is available.

        Only valid for a real JSON column operand, not for an arbitrary
        expression such as ``CAST(... AS JSON)``.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_ARROW_NATIVE']

    def supports_json_arrows(self) -> bool:
        """Alias for :meth:`supports_json_arrow_operators`."""
        return self.supports_json_arrow_operators()

    def get_json_access_operator(self) -> str:
        """Get JSON access operator.

        Empty because arrows are rendered as function calls; see
        :meth:`supports_json_arrow_operators`.
        """
        return ""

    def format_json_function_expression(self, expr: "JSONExpression") -> Tuple[str, tuple]:
        """Format JSON expression using function-based equivalents.

        Arrows are rendered as the equivalent function calls:
        - `->`  -> JSON_EXTRACT(column, path)
        - `->>` -> JSON_UNQUOTE(JSON_EXTRACT(column, path))
        """
        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()

        escaped_path = self._escape_sql_string(expr.path)

        if expr.operation == "->":
            sql = f"JSON_EXTRACT({col_sql}, '{escaped_path}')"
            params = col_params
        elif expr.operation == "->>":
            sql = f"JSON_UNQUOTE(JSON_EXTRACT({col_sql}, '{escaped_path}'))"
            params = col_params
        else:
            sql = f"{col_sql} {expr.operation} '{escaped_path}'"
            params = col_params

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE is supported.

        MariaDB supports ``JSON_TABLE`` from 10.6 (verified against live
        servers: the statement works unchanged on 12.2, 12.3, 13.0 and
        13.1).

        Returns:
            True if MariaDB version >= 10.6.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_TABLE']

    def format_json_table_expression(
        self, expr
    ) -> Tuple[str, tuple]:
        """Format a JSON_TABLE expression.

        Two node shapes are accepted, because both are reachable on a
        ``MariaDBDialect``:

        - :class:`MariaDBJSONTableExpression` -- carries ``json_doc`` plus
          ``FOR ORDINALITY``, ``EXISTS``, ``ON EMPTY`` / ``ON ERROR`` and
          ``NESTED PATH`` support.
        - the core :class:`JSONTableExpression` -- carries ``json_column`` and
          columns typed by a ``data_type`` expression.

        Every string that reaches the SQL goes through identifier quoting or
        single-quote escaping; column types are validated against a strict
        allow-list, because unlike a path they are not data and are never
        escaped, only accepted or rejected.

        Raises:
            UnsupportedFeatureError: If the server predates JSON_TABLE, a
                column type is not a plain SQL type, or an ``error_handling``
                mode is not recognised.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )

        if not self.supports_json_table():
            boundary = MARIADB_VERSION_BOUNDARIES['JSON_TABLE']
            required = ".".join(str(part) for part in boundary[:2])
            raise UnsupportedFeatureError(
                self.name,
                "JSON_TABLE function",
                f"JSON_TABLE requires MariaDB {required} or later.",
            )

        columns = list(getattr(expr, "columns", None) or [])
        if not self._validate_data_type_name(columns):
            raise UnsupportedFeatureError(
                self.name,
                "JSON_TABLE column type",
                "JSON_TABLE column type must be a plain SQL type name.",
            )

        # The two nodes mean different things by a plain string:
        #   MariaDB ``json_doc``  -> a JSON document literal
        #   core    ``json_column`` -> the name of a column holding one
        # An expression is used as-is in both cases.
        if hasattr(expr, "json_doc"):
            doc_sql, params = self._json_document_sql(expr.json_doc)
        else:
            doc_sql, params = self._json_column_sql(
                getattr(expr, "json_column", None)
            )
        path_sql = self._escape_sql_string(expr.path)

        column_defs = [self._format_json_table_column(col) for col in columns]
        for nested in (getattr(expr, "nested_paths", None) or []):
            nested_cols = ", ".join(
                self._format_json_table_column(col) for col in nested.columns
            )
            # MariaDB's grammar is `NESTED PATH 'p' COLUMNS (...)` with no
            # alias; verified against 12.2 / 12.3 / 13.0 / 13.1, where adding
            # one is a syntax error.
            column_defs.append(
                f"NESTED PATH '{self._escape_sql_string(nested.path)}' "
                f"COLUMNS({nested_cols})"
            )

        columns_sql = f"COLUMNS({', '.join(column_defs)})"
        sql = f"JSON_TABLE({doc_sql}, '{path_sql}' {columns_sql})"
        if expr.alias:
            sql += f" AS {self.format_identifier(expr.alias)}"
        return sql, params

    @staticmethod
    def _json_document_sql(json_doc) -> Tuple[str, tuple]:
        """Render a JSON document argument.

        A :class:`~...expression.bases.BaseExpression` is rendered as SQL; a
        plain string is a JSON document and is emitted as a quoted literal, so
        a caller cannot smuggle SQL in through it.
        """
        from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
        from rhosocial.activerecord.backend.expression import bases

        if isinstance(json_doc, bases.BaseExpression):
            return json_doc.to_sql()
        if isinstance(json_doc, str):
            return f"'{SQLDialectBase._escape_sql_string(json_doc)}'", ()
        raise TypeError(
            f"json_doc must be a str or expression, got {type(json_doc).__name__}"
        )

    def _json_column_sql(self, json_column) -> Tuple[str, tuple]:
        """Render a column reference holding the JSON document.

        A plain string names a column and is quoted as an identifier.
        """
        from rhosocial.activerecord.backend.expression import bases

        if isinstance(json_column, bases.BaseExpression):
            return json_column.to_sql()
        if isinstance(json_column, str):
            return self.format_identifier(json_column), ()
        raise TypeError(
            f"json_column must be a str or expression, got {type(json_column).__name__}"
        )

    def _format_json_table_column(self, col) -> str:
        """Render one entry of the ``COLUMNS(...)`` list.

        Handles both column shapes: the MariaDB column's ``type`` is a plain
        SQL type string, while the core column's ``data_type`` is a DataType
        expression that renders itself.
        """
        name_sql = self.format_identifier(col.name)
        if getattr(col, "ordinality", False):
            # FOR ORDINALITY takes no type and no path.
            return f"{name_sql} FOR ORDINALITY"

        type_sql = self._json_table_column_type(col)
        path = getattr(col, "path", None)
        path_sql = self._escape_sql_string(path) if path is not None else None

        if getattr(col, "exists", False) and path_sql is not None:
            # EXISTS is spelled between the type and PATH.
            head = f"{name_sql} {type_sql} EXISTS PATH '{path_sql}'"
        elif path_sql is not None:
            head = f"{name_sql} {type_sql} PATH '{path_sql}'"
        else:
            head = f"{name_sql} {type_sql}"

        handling = getattr(col, "error_handling", None)
        if handling:
            token = str(handling).strip().upper()
            if token == "DEFAULT":
                default = getattr(col, "default_value", None)
                literal = (
                    f"'{self._escape_sql_string(str(default))}'"
                    if default is not None else "NULL"
                )
                head += f" DEFAULT {literal} ON EMPTY"
                head += f" DEFAULT {literal} ON ERROR"
            elif token in ("NULL", "TRUE", "FALSE"):
                head += f" {token} ON EMPTY"
                head += f" {token} ON ERROR"
            else:
                from rhosocial.activerecord.backend.dialect.exceptions import (
                    UnsupportedFeatureError,
                )
                raise UnsupportedFeatureError(
                    self.name,
                    "JSON_TABLE error handling",
                    f"Unsupported JSON_TABLE error handling {handling!r}; "
                    "expected NULL, TRUE, FALSE or DEFAULT.",
                )
        return head

    def _json_table_column_type(self, col) -> str:
        """The rendered SQL type for one JSON_TABLE column."""
        from rhosocial.activerecord.backend.expression import bases

        declared = getattr(col, "type", None)
        if declared is not None:
            return str(declared)
        data_type = getattr(col, "data_type", None)
        if data_type is None:
            return "VARCHAR(255)"
        if isinstance(data_type, bases.BaseExpression):
            rendered, _ = data_type.to_sql()
            return rendered
        return str(data_type)

    @staticmethod
    def _validate_data_type_name(columns) -> bool:
        """Every column type must be a plain SQL type name.

        Types are interpolated into DDL, so they are validated rather than
        escaped: an allow-list of characters cannot be subverted by quoting.
        A ``data_type`` expression renders itself from a vetted DataType node
        and is exempt.
        """
        import re

        pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]*(\(\s*[0-9,\s]*\s*\))?(\s*\[\])?$")
        for col in columns or ():
            declared = getattr(col, "type", None)
            if declared is None:
                # Either a core DataType expression (self-rendering) or
                # unspecified, which defaults at format time.
                continue
            if not pattern.match(str(declared).strip()):
                return False
        return True

    def format_json_extract(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBJSONExtractExpression` node."""
        sql, params = self._format_json_extract_parts(expr.json_column, expr.path)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_extract_parts(
        self, json_doc: str, path: str, paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function."""
        all_paths = [path]
        if paths:
            all_paths.extend(paths)
        path_placeholders = ', '.join([self.p() for _ in all_paths])
        return f"JSON_EXTRACT({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function.

        Args:
            json_val: JSON value expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_UNQUOTE({json_val})", ()

    def format_json_object(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBJSONObjectExpression` node."""
        sql, params = self._format_json_object_parts(expr.pairs)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_object_parts(
        self, key_value_pairs: List[Tuple[str, Any]]
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function."""
        if not key_value_pairs:
            return "JSON_OBJECT()", ()

        parts = []
        params: List[Any] = []

        for key, value in key_value_pairs:
            parts.append(self.p())
            parts.append(self.p())
            params.append(key)
            params.append(value)

        return f"JSON_OBJECT({', '.join(parts)})", tuple(params)

    def format_json_array(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBJSONArrayExpression` node."""
        sql, params = self._format_json_array_parts(expr.values)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_array_parts(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function."""
        if not values:
            return "JSON_ARRAY()", ()
        placeholders = ', '.join([self.p() for _ in values])
        return f"JSON_ARRAY({placeholders})", tuple(values)

    def format_json_contains(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBJSONContainsExpression` node."""
        sql, params = self._format_json_contains_parts(
            expr.json_column, expr.value, expr.path
        )
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_contains_parts(
        self, target: str, candidate: str, path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function."""
        if path:
            return f"JSON_CONTAINS({target}, {self.p()}, {self.p()})", (candidate, path)
        return f"JSON_CONTAINS({target}, {self.p()})", (candidate,)

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
            parts.append(self.p())
            parts.append(self.p())
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

        path_placeholders = ', '.join([self.p() for _ in all_paths])
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
            return f"JSON_KEYS({json_doc}, {self.p()})", (path,)
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
            return f"JSON_SEARCH({json_doc}, {one_or_all}, {self.p()}, NULL, {self.p()})", (search_str, path)
        return f"JSON_SEARCH({json_doc}, {one_or_all}, {self.p()})", (search_str,)

    def format_json_arrow(
        self,
        json_doc: str,
        path: str,
        unquote: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON arrow operator (-> or ->>).

        MariaDB does NOT support arrow operators. Instead, use JSON_EXTRACT
        and JSON_UNQUOTE functions to emulate the same behavior.

        Args:
            json_doc: JSON document or column name.
            path: JSON path expression.
            unquote: If True, emulate ->> (unquoted result).

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        escaped_path = self._escape_sql_string(path)
        if unquote:
            return f"JSON_UNQUOTE(JSON_EXTRACT({json_doc}, '{escaped_path}'))", ()
        return f"JSON_EXTRACT({json_doc}, '{escaped_path}')", ()

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

    def format_json_query(
        self,
        json_doc: str,
        path: str
    ) -> Tuple[str, tuple]:
        """Format JSON_QUERY function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column.
            path: JSON path expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_QUERY({json_doc}, '{path}')", ()

    def format_json_value(
        self,
        json_doc: str,
        path: str,
        returning_type: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_VALUE function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column.
            path: JSON path expression.
            returning_type: Optional RETURNING data type.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if returning_type:
            return f"JSON_VALUE({json_doc}, '{path}' RETURNING {returning_type})", ()
        return f"JSON_VALUE({json_doc}, '{path}')", ()

    def format_json_exists(
        self,
        json_doc: str,
        path: str
    ) -> Tuple[str, tuple]:
        """Format JSON_EXISTS function call (MariaDB 10.2.3+).

        Args:
            json_doc: JSON document or column.
            path: JSON path expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"JSON_EXISTS({json_doc}, '{path}')", ()

    def supports_json_merge_patch(self) -> bool:
        """Whether JSON_MERGE_PATCH is supported.

        MariaDB 10.2.3+ supports JSON_MERGE_PATCH.

        Returns:
            True if MariaDB version supports JSON_MERGE_PATCH.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_FUNCTIONS']


__all__ = ['MariaDBJSONMixin']
