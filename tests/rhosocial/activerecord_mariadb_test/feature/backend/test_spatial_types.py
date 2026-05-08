# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_spatial_types.py
"""
MySQL spatial data type support tests.

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
        """Test POINT type support."""
        dialect_55 = MariaDBDialect(version=(5, 5, 0))
        assert not dialect_55.supports_spatial_type('POINT')

        dialect_57 = MariaDBDialect(version=(5, 7, 0))
        assert dialect_57.supports_spatial_type('POINT')

        dialect_80 = MariaDBDialect(version=(8, 0, 0))
        assert dialect_80.supports_spatial_type('POINT')

    def test_supports_spatial_type_all_types(self):
        """Test all spatial types support."""
        dialect = MariaDBDialect(version=(8, 0, 0))
        
        spatial_types = [
            'GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON',
            'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON',
            'GEOMETRYCOLLECTION'
        ]
        
        for stype in spatial_types:
            assert dialect.supports_spatial_type(stype), f"{stype} should be supported"

    def test_supports_spatial_type_invalid(self):
        """Test invalid spatial type."""
        dialect = MariaDBDialect(version=(8, 0, 0))
        assert not dialect.supports_spatial_type('INVALID_TYPE')

    def test_supports_spatial_index(self):
        """Test SPATIAL index support."""
        dialect_55 = MariaDBDialect(version=(5, 5, 0))
        assert not dialect_55.supports_spatial_index()

        dialect_57 = MariaDBDialect(version=(5, 7, 0))
        assert dialect_57.supports_spatial_index()

    def test_supports_geojson(self):
        """Test GeoJSON support."""
        dialect_570 = MariaDBDialect(version=(5, 7, 0))
        assert not dialect_570.supports_geojson()

        dialect_575 = MariaDBDialect(version=(5, 7, 5))
        assert dialect_575.supports_geojson()

    def test_format_spatial_literal_no_srid(self):
        """Test spatial literal without SRID."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_spatial_literal('POINT(1 1)')

        assert sql == 'ST_GeomFromText(%s)'
        assert params == ('POINT(1 1)',)

    def test_format_spatial_literal_with_srid(self):
        """Test spatial literal with SRID."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_spatial_literal('POINT(1 1)', 4326)

        assert sql == 'ST_GeomFromText(%s, %s)'
        assert params == ('POINT(1 1)', 4326)

    def test_format_st_geom_from_text_no_srid(self):
        """Test ST_GeomFromText without SRID."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_geom_from_text('LINESTRING(0 0, 1 1)')

        assert sql == 'ST_GeomFromText(%s)'
        assert params == ('LINESTRING(0 0, 1 1)',)

    def test_format_st_geom_from_text_with_srid(self):
        """Test ST_GeomFromText with SRID."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_geom_from_text('LINESTRING(0 0, 1 1)', 4326)

        assert sql == 'ST_GeomFromText(%s, %s)'
        assert params == ('LINESTRING(0 0, 1 1)', 4326)

    def test_format_st_geom_from_wkb_no_srid(self):
        """Test ST_GeomFromWKB without SRID."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        wkb_bytes = b'\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\xf0\x3f\x00\x00\x00\x00\x00\x00\xf0\x3f'
        sql, params = dialect.format_st_geom_from_wkb(wkb_bytes)

        assert sql == 'ST_GeomFromWKB(%s)'
        assert params == (wkb_bytes,)

    def test_format_st_as_text(self):
        """Test ST_AsText function."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_as_text('location')

        assert sql == 'ST_AsText(location)'
        assert params == ()

    def test_format_st_as_geojson_supported(self):
        """Test ST_AsGeoJSON function (MySQL 5.7.5+)."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_as_geojson('location')

        assert sql == 'ST_AsGeoJSON(location)'
        assert params == ()

    def test_format_st_as_geojson_unsupported(self):
        """Test ST_AsGeoJSON function with unsupported version."""
        dialect = MariaDBDialect(version=(5, 7, 0))

        with pytest.raises(Exception):  # UnsupportedFeatureError
            dialect.format_st_as_geojson('location')

    def test_format_st_distance(self):
        """Test ST_Distance function."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_distance('geom1', 'geom2')

        assert sql == 'ST_Distance(geom1, geom2)'
        assert params == ()

    def test_format_st_within(self):
        """Test ST_Within function."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_within('point_geom', 'polygon_geom')

        assert sql == 'ST_Within(point_geom, polygon_geom)'
        assert params == ()

    def test_format_st_contains(self):
        """Test ST_Contains function."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_contains('polygon_geom', 'point_geom')

        assert sql == 'ST_Contains(polygon_geom, point_geom)'
        assert params == ()

    def test_format_create_spatial_index_supported(self):
        """Test CREATE SPATIAL INDEX (MySQL 5.7+)."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_create_spatial_index('idx_location', 'places', 'geom')

        assert 'CREATE SPATIAL INDEX' in sql
        assert '`idx_location`' in sql
        assert '`places`' in sql
        assert '`geom`' in sql
        assert params == ()

    def test_format_create_spatial_index_unsupported(self):
        """Test CREATE SPATIAL INDEX with unsupported version."""
        dialect = MariaDBDialect(version=(5, 5, 0))

        with pytest.raises(Exception):  # UnsupportedFeatureError
            dialect.format_create_spatial_index('idx_location', 'places', 'geom')


class TestAsyncSpatialTypeProtocol:
    """Test async spatial data type protocol (same as sync, but verifies parity)."""

    @pytest.mark.asyncio
    async def test_async_supports_spatial_type(self):
        """Test async version of supports_spatial_type."""
        dialect = MariaDBDialect(version=(8, 0, 0))
        assert dialect.supports_spatial_type('POINT')

    @pytest.mark.asyncio
    async def test_async_supports_spatial_index(self):
        """Test async version of supports_spatial_index."""
        dialect = MariaDBDialect(version=(8, 0, 0))
        assert dialect.supports_spatial_index()

    @pytest.mark.asyncio
    async def test_async_format_spatial_literal(self):
        """Test async version of spatial literal formatting."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_spatial_literal('POINT(1 1)', 4326)

        assert 'ST_GeomFromText' in sql
        assert params == ('POINT(1 1)', 4326)

    @pytest.mark.asyncio
    async def test_async_format_st_distance(self):
        """Test async version of ST_Distance formatting."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_st_distance('geom1', 'geom2')

        assert 'ST_Distance' in sql
        assert params == ()

    @pytest.mark.asyncio
    async def test_async_format_create_spatial_index(self):
        """Test async version of CREATE SPATIAL INDEX formatting."""
        dialect = MariaDBDialect(version=(8, 0, 0))

        sql, params = dialect.format_create_spatial_index('idx_geom', 'table', 'col')

        assert 'CREATE SPATIAL INDEX' in sql
