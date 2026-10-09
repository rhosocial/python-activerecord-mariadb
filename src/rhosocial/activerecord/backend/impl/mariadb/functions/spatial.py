# src/rhosocial/activerecord/backend/impl/mariadb/functions/spatial.py
"""
MariaDB spatial function factories.

Functions: st_geom_from_text, st_geom_from_wkb, st_as_text, st_as_geojson,
st_distance, st_within, st_contains, st_intersects

MariaDB-specific notes:
- MariaDB 10.2+ supports OGC-compliant spatial functions with ST_ prefix
- MariaDB also supports legacy functions (GeomFromText, etc.)
- Aria and InnoDB storage engines support spatial indexes

Every geometry argument is an expression.  A geometry held as data is built by
``st_geom_from_text`` or ``st_geom_from_wkb`` below, which are the named
constructors for this module: a geometry argument used to be accepted as a
bare string, and whether that string was the name of a column or the WKT of a
value had to be guessed from its type alone.  It always guessed "column", so
``st_as_text(dialect, "POINT(1 1)")`` asked the server for a column named
``POINT(1 1)`` and got errno 1054 back.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


def st_geom_from_text(
    dialect: "MariaDBDialect",
    wkt: str,
    srid: Optional[int] = None,
) -> "core.FunctionCall":
    """Creates an ST_GeomFromText function call.

    Constructs a geometry value from a WKT (Well-Known Text) representation.
    This is the named construction for a geometry given as data: it takes the
    WKT itself, so a caller states that it has a value rather than a column.

    Args:
        dialect: The MariaDB dialect instance
        wkt: Well-Known Text string
        srid: Optional SRID (Spatial Reference System Identifier)

    Returns:
        A FunctionCall instance representing ST_GeomFromText

    Version: MariaDB 10.2+
    """
    wkt_expr = core.Literal(dialect, wkt)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr)


def st_geom_from_wkb(
    dialect: "MariaDBDialect",
    wkb: bytes,
    srid: Optional[int] = None,
) -> "core.FunctionCall":
    """Creates an ST_GeomFromWKB function call.

    Constructs a geometry value from a WKB (Well-Known Binary) representation.
    This is the named construction for a geometry given as binary data.

    Args:
        dialect: The MariaDB dialect instance
        wkb: Well-Known Binary data
        srid: Optional SRID (Spatial Reference System Identifier)

    Returns:
        A FunctionCall instance representing ST_GeomFromWKB

    Version: MariaDB 10.2+
    """
    wkb_expr = core.Literal(dialect, wkb)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr)


def st_as_text(
    dialect: "MariaDBDialect",
    geom: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_AsText function call.

    Returns the WKT (Well-Known Text) representation of a geometry.

    Args:
        dialect: The MariaDB dialect instance
        geom: Geometry expression, e.g. a ``Column`` or an ``st_geom_from_text``

    Returns:
        A FunctionCall instance representing ST_AsText

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_AsText", geom)


def st_as_geojson(
    dialect: "MariaDBDialect",
    geom: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_AsGeoJSON function call.

    Returns the GeoJSON representation of a geometry.

    Args:
        dialect: The MariaDB dialect instance
        geom: Geometry expression, e.g. a ``Column`` or an ``st_geom_from_text``

    Returns:
        A FunctionCall instance representing ST_AsGeoJSON

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_AsGeoJSON", geom)


def st_distance(
    dialect: "MariaDBDialect",
    geom1: "bases.BaseExpression",
    geom2: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_Distance function call.

    Returns the distance between two geometries.

    Args:
        dialect: The MariaDB dialect instance
        geom1: First geometry expression
        geom2: Second geometry expression

    Returns:
        A FunctionCall instance representing ST_Distance

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_Distance", geom1, geom2)


def st_within(
    dialect: "MariaDBDialect",
    geom1: "bases.BaseExpression",
    geom2: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_Within function call.

    Checks if geom1 is spatially within geom2.

    Args:
        dialect: The MariaDB dialect instance
        geom1: First geometry expression
        geom2: Second geometry expression

    Returns:
        A FunctionCall instance representing ST_Within

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_Within", geom1, geom2)


def st_contains(
    dialect: "MariaDBDialect",
    geom1: "bases.BaseExpression",
    geom2: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_Contains function call.

    Checks if geom1 spatially contains geom2.

    Args:
        dialect: The MariaDB dialect instance
        geom1: First geometry expression
        geom2: Second geometry expression

    Returns:
        A FunctionCall instance representing ST_Contains

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_Contains", geom1, geom2)


def st_intersects(
    dialect: "MariaDBDialect",
    geom1: "bases.BaseExpression",
    geom2: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates an ST_Intersects function call.

    Checks if two geometries spatially intersect.

    Args:
        dialect: The MariaDB dialect instance
        geom1: First geometry expression
        geom2: Second geometry expression

    Returns:
        A FunctionCall instance representing ST_Intersects

    Version: MariaDB 10.2+
    """
    return core.FunctionCall(dialect, "ST_Intersects", geom1, geom2)


__all__ = [
    "st_geom_from_text",
    "st_geom_from_wkb",
    "st_as_text",
    "st_as_geojson",
    "st_distance",
    "st_within",
    "st_contains",
    "st_intersects",
]
