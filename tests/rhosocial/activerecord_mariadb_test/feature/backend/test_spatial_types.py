# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_spatial_types.py
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
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    types as maria_types,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.spatial import (
    MariaDBSTGeomFromTextExpression,
    MariaDBSTDistanceExpression,
    MariaDBSTWithinExpression,
    MariaDBSTContainsExpression,
)


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


class TestSpatialSRIDColumnAttribute:
    """The spatial ``srid`` is rendered and read with MariaDB's spelling.

    MariaDB's column attribute is ``REF_SYSTEM_ID=<n>``; ``SRID <n>`` is
    MySQL's spelling of the same idea and is rejected with errno 1064 by every
    MariaDB server measured (live on 10.2.44 and 13.1.1 for this change;
    10.6.28, 11.4.13, 11.8.9, 12.1.2 and 12.3.3 in the typed-columns
    investigation), so the rendered DDL no server accepted until it was
    corrected.
    """

    #: ``(word, class name)`` for the eight spatial classes that carry ``srid``.
    SPATIAL = (
        ("GEOMETRY", "MariaDBGeometryType"),
        ("POINT", "MariaDBPointType"),
        ("LINESTRING", "MariaDBLineStringType"),
        ("POLYGON", "MariaDBPolygonType"),
        ("MULTIPOINT", "MariaDBMultiPointType"),
        ("MULTILINESTRING", "MariaDBMultiLineStringType"),
        ("MULTIPOLYGON", "MariaDBMultiPolygonType"),
        ("GEOMETRYCOLLECTION", "MariaDBGeometryCollectionType"),
    )

    @pytest.fixture
    def dialect(self):
        return MariaDBDialect(version=(10, 6, 0))

    @pytest.mark.parametrize("word,cls_name", SPATIAL)
    def test_formatter_renders_ref_system_id(self, dialect, word, cls_name):
        cls = getattr(maria_types, cls_name)
        rendered, params = dialect.format_data_type(cls(dialect, 4326))
        assert rendered == f"{word} REF_SYSTEM_ID=4326"
        assert params == ()

    @pytest.mark.parametrize("word,cls_name", SPATIAL)
    def test_parse_reads_ref_system_id(self, dialect, word, cls_name):
        # The spaces around '=' are tolerated by the server and by the reader.
        parsed = dialect.parse_type(f"{word.lower()} ref_system_id = 4326")
        assert type(parsed).__name__ == cls_name
        assert parsed.srid == 4326

    @pytest.mark.parametrize("word,cls_name", SPATIAL)
    def test_the_rendered_attribute_round_trips(self, dialect, word, cls_name):
        cls = getattr(maria_types, cls_name)
        declared = cls(dialect, 4326)
        rendered, _ = dialect.format_data_type(declared)
        assert dialect.parse_type(rendered) == declared

    def test_no_srid_renders_the_bare_word(self, dialect):
        for word, cls_name in self.SPATIAL:
            cls = getattr(maria_types, cls_name)
            assert dialect.format_data_type(cls(dialect))[0] == word

    def test_the_mysql_srid_spelling_is_not_read(self, dialect):
        """``SRID <n>`` arrives from nowhere MariaDB writes.

        Every measured server rejects it (errno 1064), so it cannot come out of
        a MariaDB catalog, and it is deliberately not one of the spellings
        ``parse_type`` reads: the type parses as the bare spatial word with no
        declared reference system rather than acquiring one from invalid DDL.
        """
        assert dialect.parse_type("point srid 4326").srid is None


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
        expr = MariaDBSTGeomFromTextExpression(dialect, "POINT(1 1)")
        sql, params = expr.to_sql()
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
        expr = MariaDBSTDistanceExpression(dialect, "geom1", "geom2")
        sql, params = expr.to_sql()
        assert "ST_Distance" in sql

    def test_format_st_within(self):
        """Test ST_Within formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        expr = MariaDBSTWithinExpression(dialect, "geom1", "geom2")
        sql, params = expr.to_sql()
        assert "ST_Within" in sql

    def test_format_st_contains(self):
        """Test ST_Contains formatting."""
        dialect = MariaDBDialect(version=(10, 3, 0))
        expr = MariaDBSTContainsExpression(dialect, "geom1", "geom2")
        sql, params = expr.to_sql()
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
