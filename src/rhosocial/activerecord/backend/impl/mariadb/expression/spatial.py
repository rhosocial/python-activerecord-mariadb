# src/rhosocial/activerecord/backend/impl/mariadb/expression/spatial.py
"""
MariaDB-specific spatial expression functions.

This module provides expression classes for MariaDB spatial functions:
- MariaDBSTGeomFromTextExpression
- MariaDBSTDistanceExpression
- MariaDBSTWithinExpression
- MariaDBSTContainsExpression
"""

from typing import TYPE_CHECKING, Optional

from rhosocial.activerecord.backend.expression.bases import SQLQueryAndParams, SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBSTGeomFromTextExpression(AliasableMixin, SQLValueExpression):
    """MariaDB ST_GeomFromText expression.
    
    Creates a geometry value from WKT.
    
    Example:
        >>> expr = MariaDBSTGeomFromTextExpression(dialect, 'POINT(1 1)')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        wkt: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.wkt = wkt
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_geom_from_text(self.wkt)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBSTDistanceExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MariaDB ST_Distance expression.
    
    Returns the distance between two geometries.
    
    Example:
        >>> expr = MariaDBSTDistanceExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_distance(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBSTWithinExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MariaDB ST_Within expression.
    
    Returns whether one geometry is within another.
    
    Example:
        >>> expr = MariaDBSTWithinExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_within(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBSTContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MariaDB ST_Contains expression.
    
    Returns whether one geometry contains another.
    
    Example:
        >>> expr = MariaDBSTContainsExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_contains(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


__all__ = [
    "MariaDBSTGeomFromTextExpression",
    "MariaDBSTDistanceExpression",
    "MariaDBSTWithinExpression",
    "MariaDBSTContainsExpression",
]