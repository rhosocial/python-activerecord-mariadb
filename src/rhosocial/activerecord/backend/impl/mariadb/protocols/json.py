# src/rhosocial/activerecord/backend/impl/mariadb/protocols/json.py
"""MariaDB JSON function protocol."""

from typing import Any, List, Protocol, Tuple, runtime_checkable

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

    def supports_json_type_validation(self) -> bool:
        """Whether a ``JSON`` column refuses a document that is not valid JSON.

        ``JSON`` is the ``LONGTEXT`` alias; the server adds an automatic
        ``CHECK (json_valid(...))`` to the column from MariaDB 10.4.3 onward,
        so older servers store whatever text is written.
        """
        ...

    def supports_json_path(self) -> bool:
        """Whether a JSON path can be read on this server (MariaDB 10.2.3+).

        Declared apart from supports_json_type because they are separate
        questions: the functions and the column type arrived together in
        10.2.3, but only one of them has to be true for a path to render.
        """
        ...

    def supports_json_merge_patch(self) -> bool:
        """Whether JSON_MERGE_PATCH is supported.

        MariaDB does not have JSON_MERGE_PATCH (unlike MySQL 8.0.3+).
        Use JSON_MERGE instead.
        """
        ...

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE is supported (MariaDB 10.6+)."""
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
        """Whether arrows are emitted natively as ``->`` / ``->>``.

        False for MariaDB on every version: arrows are rendered as the
        equivalent ``JSON_EXTRACT`` calls, which behave identically
        everywhere. See :meth:`supports_json_arrow_operators_native` for the
        13.1 column-only form.
        """
        ...

    def supports_json_arrow_operators_native(self) -> bool:
        """Whether MariaDB 13.1's native ``->`` / ``->>`` is available.

        Only valid for a real JSON column operand, not for an arbitrary
        expression such as ``CAST(x AS JSON)``.
        """
        ...

    def supports_json_arrows(self) -> bool:
        """Alias for :meth:`supports_json_arrow_operators`."""
        ...

    def format_json_extract_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function call.

        Args:
            expr: MariaDBJSONExtractExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_unquote(self, expr: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function call.

        Args:
            json_val: JSON value to unquote

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_object_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function call.

        Args:
            expr: MariaDBJSONObjectExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_array_expression(self, expr: Any) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function call.

        Args:
            expr: MariaDBJSONArrayExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_contains_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function call.

        Args:
            expr: MariaDBJSONContainsExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...



    def format_json_type(self, expr: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function call.

        Args:
            json_val: JSON value to type-check

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_valid(self, expr: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function call.

        Args:
            json_val: Value to check for valid JSON

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
        """Format core's portable ``JSON_TABLE`` expression.

        MariaDB supports JSON_TABLE from 10.6; below that floor the formatter
        refuses the request rather than emitting SQL the server rejects.

        Args:
            expr: core ``JSONTableExpression`` instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_mariadb_json_table_expression(
        self,
        expr: Any
    ) -> Tuple[str, tuple]:
        """Format this backend's own ``JSON_TABLE`` expression.

        The MariaDB node carries ``json_doc`` and ``NESTED PATH`` support,
        which core's portable node does not; each node kind names its own
        formatter.

        Args:
            expr: ``MariaDBJSONTableExpression`` instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_mariadb_json_table_column(
        self, expr: Any
    ) -> Tuple[str, tuple]:
        """Render one entry of a MariaDB ``JSON_TABLE`` column list.

        MariaDB's column carries ``FOR ORDINALITY``, ``EXISTS`` and the error
        handling, none of which the core column has, so the two shapes render
        through separate paths rather than one branching on the instance.

        Args:
            column: MariaDBJSONTableColumn instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


    def format_json_merge(
        self,
        expr: List[str]
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
        expr: List[str]
    ) -> Tuple[str, tuple]:
        """Format JSON_MERGE_PATCH function call.

        Args:
            json_docs: List of JSON documents to merge

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
