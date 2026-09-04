# tests/rhosocial/activerecord_mariadb_test/feature/backend/mariadb/spatial/test_spatial_types.py
"""
MariaDB spatial data type support tests.

This module tests MariaDB-specific spatial data type functionality including:
- Type support detection
- Spatial literal formatting
- Spatial function formatting
- SPATIAL index creation
"""
import pytest
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestSpatialTypeProtocol:
    """Test spatial data type protocol implementation."""

    def test_supports_spatial_type_point(self):
        """Test POINT type support - MariaDB supports POINT in all versions."""
        dialect_102 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_102.supports_spatial_type('POINT')

        dialect_103 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_103.supports_spatial_type('POINT')

    def test_supports_spatial_type_all_types(self):
        """Test all spatial types support."""
        dialect = MariaDBDialect(version=(10, 3, 0))

        spatial_types = [
            'GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON',
            'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON',
            'GEOMETRYCOLLECTION'
        ]

        for stype in spatial_types:
            assert dialect.supports_spatial_type(stype), f"{stype} should be supported"

    def test_supports_spatial_type_invalid(self):
        """Test invalid spatial type."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        assert not dialect.supports_spatial_type('INVALID_TYPE')

    def test_supports_spatial_index(self):
        """Test SPATIAL index support - InnoDB SPATIAL index from MariaDB 10.2.2+."""
        dialect_102 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_102.supports_spatial_index()

        dialect_103 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_103.supports_spatial_index()

    def test_supports_geojson(self):
        """Test GeoJSON support - MariaDB supports ST_AsGeoJSON in all versions."""
        dialect_102 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_102.supports_geojson()

        dialect_103 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_103.supports_geojson()


class TestSpatialLiteralFormatting:
    """Test spatial literal formatting."""

    def test_format_spatial_literal(self):
        """Test spatial literal formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_spatial_literal("POINT(1 1)")
        assert "ST_GeomFromText" in sql
        assert params == ("POINT(1 1)",)

    def test_format_spatial_literal_with_srid(self):
        """Test spatial literal formatting with SRID."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_spatial_literal("POINT(1 1)", srid=4326)
        assert "ST_GeomFromText" in sql
        assert 4326 in params


class TestSpatialFunctionFormatting:
    """Test spatial function formatting."""

    def test_format_st_geom_from_text(self):
        """Test ST_GeomFromText formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_geom_from_text("POINT(1 1)")
        assert "ST_GeomFromText" in sql
        assert params == ("POINT(1 1)",)

    def test_format_st_as_text(self):
        """Test ST_AsText formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_as_text("geom_col")
        assert "ST_AsText" in sql
        assert "geom_col" in sql

    def test_format_st_as_geojson(self):
        """Test ST_AsGeoJSON formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_as_geojson("geom_col")
        assert "ST_AsGeoJSON" in sql
        assert "geom_col" in sql

    def test_format_st_distance(self):
        """Test ST_Distance formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_distance("geom1", "geom2")
        assert "ST_Distance" in sql

    def test_format_st_within(self):
        """Test ST_Within formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_within("geom1", "geom2")
        assert "ST_Within" in sql

    def test_format_st_contains(self):
        """Test ST_Contains formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_contains("geom1", "geom2")
        assert "ST_Contains" in sql

    def test_format_st_distance_sphere(self):
        """Test ST_Distance_Sphere formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_distance_sphere("geom1", "geom2")
        assert "ST_Distance_Sphere" in sql

    def test_format_st_intersects(self):
        """Test ST_Intersects formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_st_intersects("geom1", "geom2")
        assert "ST_Intersects" in sql


class TestSpatialIndexFormatting:
    """Test SPATIAL index creation formatting."""

    def test_format_create_spatial_index(self):
        """Test CREATE SPATIAL INDEX formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_create_spatial_index("idx_spatial", "test_table", "geom_col")
        assert "SPATIAL INDEX" in sql
        assert "idx_spatial" in sql
        assert "test_table" in sql
        assert "geom_col" in sql

    def test_format_create_spatial_index_unsupported(self):
        """Test CREATE SPATIAL INDEX raises error for unsupported version."""
        # MariaDB always supports spatial index, so this should not raise
        dialect = MariaDBDialect(version=(10, 3, 0))
        sql, params = dialect.format_create_spatial_index("idx_spatial", "test_table", "geom_col")
        assert "SPATIAL INDEX" in sql
