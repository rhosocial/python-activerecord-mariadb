# src/rhosocial/activerecord/backend/impl/mariadb/protocols/spatial.py
"""MariaDB spatial data type protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable



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


    def format_st_geom_from_text_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromText function call.

        Args:
            expr: MariaDBSTGeomFromTextExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


    def render_st_as_text(self, expr: str) -> Tuple[str, tuple]:
        """Format ST_AsText function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def render_st_as_geojson(self, expr: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_distance_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format ST_Distance function call.

        Args:
            expr: MariaDBSTDistanceExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_within_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format ST_Within function call.

        Args:
            expr: MariaDBSTWithinExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_contains_expression(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format ST_Contains function call.

        Args:
            expr: MariaDBSTContainsExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...



