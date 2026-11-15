# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_geometry.py
"""``GEOMETRY`` family: native literals, ``ST_AsText`` decoding, SRID semantics.

Two facts shape this module:

* a ``GEOMETRY`` column handed back by the connector is the server's internal
  binary form, not WKT, so every read goes through ``ST_AsText(...)``;
* a plain WKT *parameter* is rejected by the server (errno 1416), so writes go
  through ``ST_GeomFromText(...)``; the adapter's plain-text binding is pinned
  as an ``xfail`` that names the exact server error.

``REF_SYSTEM_ID`` is metadata only: it neither coerces a stored geometry's SRID
nor rejects a geometry carrying a different one. That is asserted explicitly
rather than left implied.
"""

import pytest

from rhosocial.activerecord.backend.adapters import (
    Geometry,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBGeometryAdapter

from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.helpers import (
    DML,
    read_raw,
)

adapter = MariaDBGeometryAdapter()

SHAPE_CASES = (
    ("POINT(1 2)", Point(1, 2)),
    ("LINESTRING(0 0, 1 1, 2 0)", LineString([(0, 0), (1, 1), (2, 0)])),
    ("POLYGON((0 0, 4 0, 4 4, 0 4, 0 0))", Polygon([[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]])),
    # MariaDB 11.8 accepts only the non-parenthesised MultiPoint WKT: the
    # standard's ``MULTIPOINT((0 0),(1 1))`` parses into an invalid geometry,
    # so ``ST_AsText`` answers NULL for it (measured on 11.8.9).
    ("MULTIPOINT(0 0, 1 1)", MultiPoint([(0, 0), (1, 1)])),
    (
        "MULTILINESTRING((0 0, 1 1), (2 0, 3 1))",
        MultiLineString([[(0, 0), (1, 1)], [(2, 0), (3, 1)]]),
    ),
    ("MULTIPOLYGON(((0 0, 4 0, 4 4, 0 4, 0 0)))", MultiPolygon([[[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]]])),
    ("GEOMETRYCOLLECTION(POINT(1 2), LINESTRING(0 0, 1 1))", GeometryCollection([Point(1, 2), LineString([(0, 0), (1, 1)])])),
)


def _insert_geom(model, pk: int, column: str, wkt: str, srid=None) -> None:
    srid_sql = "" if srid is None else f", {int(srid)}"
    model.backend().execute(
        f"INSERT INTO native_geometry (id, {column}) "
        f"VALUES ({int(pk)}, ST_GeomFromText('{wkt}'{srid_sql}))",
        (),
        options=DML,
    )


def test_wkt_literals_decode_through_st_astext(native_geometry):
    for offset, (wkt, expected) in enumerate(SHAPE_CASES, start=1):
        _insert_geom(native_geometry, 100 + offset, "geom", wkt)

        text = read_raw(native_geometry, "ST_AsText(geom)", 100 + offset)
        decoded = adapter.from_database(text, Geometry)
        assert decoded == expected, f"{type(expected).__name__} must survive ST_AsText"
        assert adapter.to_database(decoded, str) == expected.to_wkt(), (
            "decoding foreign WKT then re-encoding must produce the canonical WKT"
        )


def test_type_specific_columns_keep_their_shape(native_geometry):
    _insert_geom(native_geometry, 201, "pt", "POINT(3 4)")
    assert read_raw(native_geometry, "ST_AsText(pt)", 201) == "POINT(3 4)"
    assert adapter.from_database(read_raw(native_geometry, "ST_AsText(pt)", 201), Point) == Point(3, 4)

    row = native_geometry.backend().fetch_all(
        "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'native_geometry' "
        "AND COLUMN_NAME IN ('geom','pt','srid_geom')",
        (),
    )
    assert {r["COLUMN_NAME"]: r["DATA_TYPE"] for r in row} == {
        "geom": "geometry",
        "pt": "point",
        "srid_geom": "geometry",
    }


def test_wkt_parameter_binding_inside_st_geomfromtext(native_geometry):
    placeholder = native_geometry.backend().dialect.get_parameter_placeholder()
    native_geometry.backend().execute(
        f"INSERT INTO native_geometry (id, geom) "
        f"VALUES ({placeholder}, ST_GeomFromText({placeholder}, {placeholder}))",
        (301, "POINT(9 9)", 4326),
        options=DML,
    )
    assert read_raw(native_geometry, "ST_AsText(geom)", 301) == "POINT(9 9)"
    assert read_raw(native_geometry, "ST_SRID(geom)", 301) == 4326


def test_ref_system_id_is_metadata_not_a_constraint(native_geometry):
    _insert_geom(native_geometry, 401, "srid_geom", "POINT(1 2)")
    _insert_geom(native_geometry, 402, "srid_geom", "POINT(5 6)", srid=3857)

    assert read_raw(native_geometry, "ST_SRID(srid_geom)", 401) == 0, (
        "REF_SYSTEM_ID does not coerce a geometry inserted without an SRID"
    )
    assert read_raw(native_geometry, "ST_SRID(srid_geom)", 402) == 3857, (
        "REF_SYSTEM_ID does not reject a geometry carrying another SRID"
    )

    row = native_geometry.backend().fetch_one(
        "SELECT SRID FROM information_schema.GEOMETRY_COLUMNS "
        "WHERE F_TABLE_SCHEMA = DATABASE() AND F_TABLE_NAME = 'native_geometry' "
        "AND G_GEOMETRY_COLUMN = 'srid_geom'",
        (),
    )
    assert row["SRID"] == 4326, "the declared column SRID remains 4326"


@pytest.mark.xfail(
    reason=(
        "MariaDB rejects a plain WKT parameter bound to GEOMETRY: errno 1416 "
        "'Cannot get geometry object from data you send to the GEOMETRY field'; "
        "requires execution-layer bind_expression (testing-plan §4.4 / §7.4)"
    ),
    raises=DatabaseError,
    strict=True,
)
def test_model_write_plain_wkt_is_rejected(native_geometry):
    """Plain WKT parameter binding fails; the server names the reason.

    Registered as an xfail, not a skip: the adapter exists but the
    execution layer cannot wrap the bound text in ``ST_GeomFromText``.
    """
    native_geometry(geom=Point(1, 2)).save()


def test_plain_wkt_binding_error_is_the_expected_one(native_geometry):
    """The rejection is the server's geometry check, not a decoding failure."""
    with pytest.raises(DatabaseError) as info:
        native_geometry(geom=Point(1, 2)).save()
    assert "1416" in str(info.value)
    assert "Cannot get geometry object" in str(info.value)
