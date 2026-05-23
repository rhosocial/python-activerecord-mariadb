# src/rhosocial/activerecord/backend/impl/mariadb/protocols.py
"""MariaDB dialect-specific protocol definitions.

This module defines protocols for features specific to MariaDB,
covering both features shared with MySQL and MariaDB-exclusive features.

MariaDB version mapping (relative to MySQL):
  - MySQL 5.6+ → MariaDB 10.0+
  - MySQL 5.7+ → MariaDB 10.2+
  - MySQL 8.0+ → MariaDB 10.3+
  - MySQL 8.4+ → MariaDB 11.0+
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import (
    JSONSupport,
    LockingSupport,
    TableSupport,
)


@runtime_checkable
class MariaDBDMLOperationSupport(Protocol):
    """MariaDB-specific DML operations protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB DML features beyond SQL standard:
    - INSERT IGNORE: Silently ignore rows that would cause duplicate key errors
    - REPLACE INTO: Delete and re-insert on duplicate key (changes AUTO_INCREMENT)
    - LOAD DATA INFILE: High-performance bulk data import
    - INSERT ... RETURNING: Insert and return values (MariaDB 10.5+)

    Official Documentation:
    - INSERT: https://mariadb.com/kb/en/insert/
    - REPLACE: https://mariadb.com/kb/en/replace/
    - LOAD DATA: https://mariadb.com/kb/en/load-data-infile/

    Version Requirements:
    - INSERT IGNORE: All MariaDB versions
    - REPLACE INTO: All MariaDB versions
    - LOAD DATA INFILE: All MariaDB versions
    """

    def supports_insert_ignore(self) -> bool:
        """Whether INSERT IGNORE is supported.

        MariaDB supports INSERT IGNORE to silently ignore rows that would
        cause duplicate key errors instead of raising an error.
        """
        ...

    def supports_replace_into(self) -> bool:
        """Whether REPLACE INTO is supported.

        MariaDB supports REPLACE INTO which deletes and re-inserts on
        duplicate key. Note: AUTO_INCREMENT value changes on replacement.
        """
        ...

    def supports_load_data(self) -> bool:
        """Whether LOAD DATA INFILE is supported.

        MariaDB supports LOAD DATA INFILE for high-performance bulk data
        import from files. LOCAL variant reads files from the client.
        """
        ...

    def format_load_data_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Args:
            expr: MariaDBLoadDataExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_on_conflict_clause(self, expr: Any) -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE clause (MariaDB upsert).

        MariaDB uses ON DUPLICATE KEY UPDATE (same as MySQL) instead of
        the SQL-standard ON CONFLICT clause for upsert operations.

        Args:
            expr: OnConflictExpression or equivalent instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def supports_returning_for_insert(self) -> bool:
        """Whether RETURNING is supported for INSERT (MariaDB 10.5+)."""
        ...

    def supports_returning_for_delete(self) -> bool:
        """Whether RETURNING is supported for DELETE (MariaDB 10.5+)."""
        ...

    def supports_returning_for_replace(self) -> bool:
        """Whether RETURNING is supported for REPLACE (MariaDB 10.5+)."""
        ...

    def supports_returning_for_update(self) -> bool:
        """Whether RETURNING is supported for UPDATE.

        MariaDB does NOT support RETURNING for UPDATE.
        """
        ...

    def format_insert_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format INSERT statement with MariaDB-specific options.

        Supports INSERT IGNORE, REPLACE INTO, and RETURNING clause.

        Args:
            expr: InsertExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_delete_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format DELETE statement with MariaDB-specific options.

        Supports RETURNING clause.

        Args:
            expr: DeleteExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_replace_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format REPLACE INTO statement.

        Args:
            expr: ReplaceExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBTriggerSupport(Protocol):
    """MariaDB trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MariaDB triggers:
    - BEFORE/AFTER: Timing
    - INSERT/UPDATE/DELETE: Event
    - FOR EACH ROW: Level (only row-level triggers supported)
    - NEW/OLD: Row references

    MariaDB-specific trigger enhancements:
    - Trigger IF NOT EXISTS: CREATE OR REPLACE TRIGGER (MariaDB 10.1.4+)
    - Trigger order: FOLLOWS/PRECEDES (MariaDB 10.2.3+)
    - Trigger on all tables: MariaDB 10.3+

    Official Documentation:
    - CREATE TRIGGER: https://mariadb.com/kb/en/create-trigger/

    Version Requirements:
    - Triggers: MariaDB 5.x+
    - Trigger IF NOT EXISTS: MariaDB 10.1.4+
    - Trigger FOLLOWS/PRECEDES: MariaDB 10.2.3+
    """

    def supports_trigger(self) -> bool:
        """Whether triggers are supported."""
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported (MariaDB 10.1.4+)."""
        ...

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MariaDB does NOT support INSTEAD OF triggers (only BEFORE/AFTER).
        This method always returns False for MariaDB.
        """
        ...

    def supports_statement_trigger(self) -> bool:
        """Whether statement-level triggers are supported.

        MariaDB only supports row-level triggers (FOR EACH ROW).
        This method always returns False for MariaDB.
        """
        ...

    def supports_trigger_referencing(self) -> bool:
        """Whether trigger referencing (NEW/OLD) is supported.

        MariaDB supports NEW and OLD row references in triggers.
        """
        ...

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition on triggers is supported.

        MariaDB does NOT support WHEN condition on triggers.
        This method always returns False for MariaDB.
        """
        ...

    def supports_trigger_order(self) -> bool:
        """Whether trigger ordering (FOLLOWS/PRECEDES) is supported (MariaDB 10.2.3+)."""
        ...

    def supports_create_trigger(self) -> bool:
        """Whether CREATE TRIGGER is supported."""
        ...

    def supports_drop_trigger(self) -> bool:
        """Whether DROP TRIGGER is supported."""
        ...

    def supports_or_replace_trigger(self) -> bool:
        """Whether CREATE OR REPLACE TRIGGER is supported (MariaDB 10.1.4+)."""
        ...

    def supports_multiple_triggers_per_timing(self) -> bool:
        """Whether multiple triggers per timing/event are supported (MariaDB 10.2.3+)."""
        ...

    def format_create_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement.

        Args:
            expr: CreateTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement.

        Args:
            expr: DropTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBTableSupport(Protocol):
    """MariaDB table DDL protocol.

    Feature Source: Native support (no extension required)

    MariaDB table features beyond SQL standard:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    - Row format options
    - CREATE OR REPLACE TABLE (MariaDB 10.1+)
    - WITH SYSTEM VERSIONING (MariaDB 10.3+)

    Official Documentation:
    - CREATE TABLE: https://mariadb.com/kb/en/create-table/
    - CREATE TABLE ... LIKE: https://mariadb.com/kb/en/create-table-like/

    Version Requirements:
    - Basic features: All versions
    - Various storage engines: All versions
    - CREATE OR REPLACE TABLE: MariaDB 10.1+
    - System-versioned tables: MariaDB 10.3+
    """

    def supports_table_like_syntax(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported.

        MariaDB supports copying table structure with LIKE syntax.
        """
        ...

    def supports_inline_index(self) -> bool:
        """Whether inline index definitions are supported.

        MariaDB allows INDEX/KEY definitions within CREATE TABLE.
        """
        ...

    def supports_storage_engine_option(self) -> bool:
        """Whether ENGINE option is supported.

        MariaDB supports multiple storage engines (InnoDB, MyISAM, Aria, etc.).
        """
        ...

    def supports_charset_option(self) -> bool:
        """Whether CHARSET/COLLATE options are supported.

        MariaDB supports character set and collation at table level.
        """
        ...

    def supports_create_or_replace_table(self) -> bool:
        """Whether CREATE OR REPLACE TABLE is supported (MariaDB 10.1+)."""
        ...

    def format_create_table_statement(
        self,
        expr,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement.

        Note: Generic TableSupport protocol defines this interface.
        This MariaDB-specific version documents available options.

        Args:
            expr: CreateTableExpression instance
            dialect_options: MariaDB-specific options:
                - 'engine': Storage engine (InnoDB, MyISAM, Aria, etc.)
                - 'charset': Character set
                - 'collate': Collation
                - 'auto_increment': Initial AUTO_INCREMENT value
                - 'row_format': Row format (DYNAMIC, COMPACT, etc.)
                - 'with_system_versioning': Enable system-versioned tables (MariaDB 10.3+)
                Example: dialect_options={'engine': 'InnoDB', 'charset': 'utf8mb4'}
        """
        ...


@runtime_checkable
class MariaDBSetTypeSupport(Protocol):
    """MariaDB SET type protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB SET features:
    - String object with zero or more values from predefined list
    - Stored as integer (bit flags) internally
    - Maximum 64 members
    - Supports FIND_IN_SET, LIKE operations
    - Automatically sorted on storage

    Official Documentation:
    - SET Type: https://mariadb.com/kb/en/set-data-type/

    Version Requirements:
    - All MariaDB versions
    """

    def supports_set_type(self) -> bool:
        """Whether SET type is supported."""
        ...

    def format_set_literal(
        self,
        values: List[str],
        column_values: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format SET type literal.

        Args:
            values: Allowed values for the SET type
            column_values: Values being inserted/compared

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_find_in_set(
        self,
        value: str,
        set_column: str
    ) -> Tuple[str, tuple]:
        """Format FIND_IN_SET function call.

        Args:
            value: Value to search for
            set_column: SET column or expression to search in

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_set_contains(
        self,
        column: str,
        values: List[str]
    ) -> Tuple[str, tuple]:
        """Format SET contains check expression.

        Args:
            column: SET column name
            values: Values to check for containment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBJSONFunctionSupport(Protocol):
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


@runtime_checkable
class MariaDBSpatialSupport(Protocol):
    """MariaDB spatial data type protocol.

    Feature Source: MariaDB 5.x+ with MyISAM/Aria/InnoDB

    MariaDB spatial features:
    - SPATIAL data types: GEOMETRY, POINT, LINESTRING, POLYGON, etc.
    - Spatial indexes (InnoDB supports SPATIAL index from MariaDB 10.2.2+)
    - CRS (Coordinate Reference System) support (MariaDB 10.2+)

    Official Documentation:
    - Spatial Data Types: https://mariadb.com/kb/en/spatial-data-types/

    Version Requirements:
    - Basic spatial types: All MariaDB versions
    - InnoDB spatial index: MariaDB 10.2.2+
    - CRS support improvements: MariaDB 10.2+
    """

    def supports_spatial_type(self, type_name: str) -> bool:
        """Whether a specific spatial data type is supported.

        Args:
            type_name: Spatial type name (e.g. 'POINT', 'LINESTRING')

        Returns:
            True if the spatial type is supported
        """
        ...

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL index is supported."""
        ...

    def supports_geojson(self) -> bool:
        """Whether GeoJSON functions (ST_AsGeoJSON) are supported (MariaDB 5.x+)."""
        ...

    def supports_geometry_type(self) -> bool:
        """Whether GEOMETRY type is supported."""
        ...

    def supports_point_type(self) -> bool:
        """Whether POINT type is supported."""
        ...

    def supports_curve_type(self) -> bool:
        """Whether curve types (LINESTRING, MULTILINESTRING) are supported."""
        ...

    def supports_surface_type(self) -> bool:
        """Whether surface types (POLYGON, MULTIPOLYGON) are supported."""
        ...

    def supports_geometry_collection_type(self) -> bool:
        """Whether GEOMETRYCOLLECTION is supported."""
        ...

    def format_spatial_literal(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format spatial literal from WKT.

        Args:
            wkt: Well-Known Text representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_geom_from_text(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromText function call.

        Args:
            wkt: Well-Known Text representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_geom_from_wkb(
        self,
        wkb: bytes,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromWKB function call.

        Args:
            wkb: Well-Known Binary representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsText function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_distance(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance function call.

        Args:
            geom1: First geometry
            geom2: Second geometry

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_within(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Within function call.

        Args:
            geom1: Geometry to test
            geom2: Geometry to test against

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_contains(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Contains function call.

        Args:
            geom1: Geometry to test
            geom2: Geometry to test against

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_create_spatial_index(
        self,
        index_name: str,
        table_name: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE SPATIAL INDEX statement.

        Args:
            index_name: Index name
            table_name: Table name
            column: Column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_distance_sphere(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance_Sphere function call.

        Args:
            geom1: First geometry (point)
            geom2: Second geometry (point)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_intersects(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Intersects function call.

        Args:
            geom1: First geometry
            geom2: Second geometry

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


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
        index_name: str,
        columns: List[str],
        index_type: Optional[str] = None,
        parser_name: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format FULLTEXT index options.

        Args:
            index_name: Index name (usually 'FULLTEXT')
            columns: Indexed columns
            index_type: Index type (BTREE, HASH - ignored for FULLTEXT)
            parser_name: Parser name for full-text search

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBLockingSupport(Protocol):
    """MariaDB row-level locking protocol.

    Feature Source: MariaDB native (FOR UPDATE all versions, FOR SHARE MariaDB 10.2+)

    MariaDB locking features beyond SQL standard:
    - FOR SHARE: Shared lock (MariaDB 10.2+, replaces LOCK IN SHARE MODE)
    - NOWAIT: Fail immediately if rows are locked (MariaDB 10.3+)
    - SKIP LOCKED: Skip locked rows (MariaDB 10.3+)

    Note: MariaDB does NOT support PostgreSQL's FOR NO KEY UPDATE or
    FOR KEY SHARE lock strengths.

    Official Documentation:
    - Locking Reads: https://mariadb.com/kb/en/locking-reads/

    Version Requirements:
    - FOR UPDATE: All MariaDB versions
    - FOR SHARE (replacing LOCK IN SHARE MODE): MariaDB 10.2+
    - NOWAIT: MariaDB 10.3+
    - SKIP LOCKED: MariaDB 10.3+
    """

    def supports_for_share(self) -> bool:
        """Whether FOR SHARE clause is supported (MariaDB 10.2+)."""
        ...

    def supports_for_update_nowait(self) -> bool:
        """Whether FOR UPDATE NOWAIT is supported (MariaDB 10.3+)."""
        ...

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported (MariaDB 10.3+)."""
        ...

    def format_for_update_clause(self, clause: Any) -> Tuple[str, tuple]:
        """Format MariaDB-specific FOR UPDATE clause.

        Args:
            clause: MariaDBForUpdateClause instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported.

        MariaDB supports FOR UPDATE in all versions.
        """
        ...

    def supports_lock_strength(self) -> bool:
        """Whether different lock strengths (FOR NO KEY UPDATE, FOR KEY SHARE) are supported.

        MariaDB does NOT support different lock strengths (PostgreSQL feature).
        """
        ...

    def format_lock_in_share_mode(self, clause: Any) -> Tuple[str, tuple]:
        """Format LOCK IN SHARE MODE clause (legacy MariaDB syntax).

        Args:
            clause: LockInShareModeClause instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MariaDBModifyColumnSupport(Protocol):
    """MariaDB MODIFY COLUMN and CHANGE COLUMN protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB ALTER TABLE features beyond SQL standard:
    - MODIFY COLUMN: Redefine a column with new specification (name unchanged)
    - CHANGE COLUMN: Rename and redefine a column in one operation
    - FIRST/AFTER: Column positioning within the table

    Official Documentation:
    - ALTER TABLE: https://mariadb.com/kb/en/alter-table/

    Version Requirements:
    - MODIFY COLUMN: All MariaDB versions
    - CHANGE COLUMN: All MariaDB versions
    """

    def supports_modify_column(self) -> bool:
        """Whether MODIFY COLUMN is supported."""
        ...

    def supports_change_column(self) -> bool:
        """Whether CHANGE COLUMN is supported."""
        ...

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        """Format MODIFY COLUMN action for ALTER TABLE.

        Args:
            action: ModifyColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_change_column_action(self, action) -> Tuple[str, tuple]:
        """Format CHANGE COLUMN action for ALTER TABLE.

        Args:
            action: ChangeColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


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
    'MariaDBDMLOperationSupport',
    'MariaDBTriggerSupport',
    'MariaDBTableSupport',
    'MariaDBSetTypeSupport',
    'MariaDBJSONFunctionSupport',
    'MariaDBSpatialSupport',
    'MariaDBFullTextSearchSupport',
    'MariaDBLockingSupport',
    'MariaDBModifyColumnSupport',
    'MariaDBSequenceSupport',
    'MariaDBReturningSupport',
    'MariaDBIntersectExceptSupport',
    'MariaDBSystemVersioningSupport',
    'MariaDBWindowFunctionSupport',
    'MariaDBCTESupport',
]