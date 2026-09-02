# src/rhosocial/activerecord/backend/impl/mariadb/mixins/spatial.py
"""MariaDB spatial data types mixin.

MariaDB supports spatial data types with the same syntax as MySQL.
Available in MyISAM, Aria, and InnoDB (MariaDB 10.0+).
"""
from typing import List, Optional, Tuple

from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBSpatialMixin:
    """MariaDB spatial data type implementation.

    MariaDB spatial types (same as MySQL):
    - GEOMETRY: Base type for all spatial values
    - POINT: A point in 2D/3D/4D space
    - LINESTRING: A sequence of points forming a line
    - POLYGON: A closed area with one or more rings
    - MULTIPOINT, MULTILINESTRING, MULTIPOLYGON: Collections
    - GEOMETRYCOLLECTION: Heterogeneous collection

    Official Documentation:
    - https://mariadb.com/kb/en/spatial-data-types/

    Version Requirements:
    - Basic spatial types: All versions (MyISAM/Aria), MariaDB 10.0+ (InnoDB)
    - SPATIAL indexes: MariaDB 10.0+ (InnoDB)
    - GeoJSON support: MariaDB 10.2.3+
    """

    def supports_spatial_type(self, type_name: str) -> bool:
        """Check if specific spatial type is supported.

        Args:
            type_name: Name of the spatial type.

        Returns:
            True if the type is valid.
        """
        valid_types = {
            'GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON',
            'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON',
            'GEOMETRYCOLLECTION'
        }
        return type_name.upper() in valid_types

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL indexes are supported.

        MariaDB 10.0+ supports SPATIAL indexes for InnoDB.

        Returns:
            True.
        """
        return True

    def supports_geojson(self) -> bool:
        """Whether GeoJSON functions are supported.

        MariaDB 10.2.3+ supports ST_AsGeoJSON.

        Returns:
            True if MariaDB version >= 10.2.3.
        """
        return self.version >= (10, 2, 3)

    def supports_geometry_type(self) -> bool:
        """Whether GEOMETRY type is supported."""
        return True

    def supports_point_type(self) -> bool:
        """Whether POINT type is supported."""
        return True

    def supports_curve_type(self) -> bool:
        """Whether curve types (LINESTRING, MULTILINESTRING) are supported."""
        return True

    def supports_surface_type(self) -> bool:
        """Whether surface types (POLYGON, MULTIPOLYGON) are supported."""
        return True

    def supports_geometry_collection_type(self) -> bool:
        """Whether GEOMETRYCOLLECTION is supported."""
        return True

    def format_spatial_literal(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format spatial literal from WKT (Well-Known Text).

        Args:
            wkt: Well-Known Text representation.
            srid: Optional Spatial Reference System Identifier.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if srid is not None:
            return "ST_GeomFromText(%s, %s)", (wkt, srid)
        return "ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_text(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromText function.

        Args:
            wkt: Well-Known Text string.
            srid: Optional SRID.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if srid is not None:
            return "ST_GeomFromText(%s, %s)", (wkt, srid)
        return "ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_wkb(
        self,
        wkb: bytes,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromWKB function.

        Args:
            wkb: Well-Known Binary data.
            srid: Optional SRID.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if srid is not None:
            return "ST_GeomFromWKB(%s, %s)", (wkb, srid)
        return "ST_GeomFromWKB(%s)", (wkb,)

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsText function.

        Args:
            geom: Geometry column or expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_AsText({geom})", ()

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function.

        MariaDB 10.2.3+ supports ST_AsGeoJSON.

        Args:
            geom: Geometry column or expression.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If GeoJSON not supported.
        """
        if not self.supports_geojson():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "GeoJSON functions",
                "GeoJSON functions require MariaDB 10.2.3 or later."
            )
        return f"ST_AsGeoJSON({geom})", ()

    def format_st_distance(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance function.

        Args:
            geom1: First geometry.
            geom2: Second geometry.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_Distance({geom1}, {geom2})", ()

    def format_st_distance_sphere(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance_Sphere function.

        MariaDB-specific: Computes distance on a sphere (Earth).

        Args:
            geom1: First geometry (point).
            geom2: Second geometry (point).

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_Distance_Sphere({geom1}, {geom2})", ()

    def format_st_within(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Within function.

        Args:
            geom1: Geometry to check.
            geom2: Geometry to check within.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_Within({geom1}, {geom2})", ()

    def format_st_contains(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Contains function.

        Args:
            geom1: Containing geometry.
            geom2: Geometry to check.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_Contains({geom1}, {geom2})", ()

    def format_st_intersects(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Intersects function.

        Args:
            geom1: First geometry.
            geom2: Second geometry.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"ST_Intersects({geom1}, {geom2})", ()

    def format_create_spatial_index(
        self,
        index: str,
        table: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE SPATIAL INDEX statement.

        Args:
            index: Name of the index.
            table: Name of the table.
            column: Geometry column name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return (
            f"CREATE SPATIAL INDEX {self.format_identifier(index)} "
            f"ON {self.format_identifier(table)} "
            f"({self.format_identifier(column)})",
            ()
        )


__all__ = ['MariaDBSpatialMixin']
