# src/rhosocial/activerecord/backend/impl/mariadb/protocols/spatial.py
"""MariaDB spatial data type protocol."""

from typing import Optional, Protocol, Tuple, runtime_checkable


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
