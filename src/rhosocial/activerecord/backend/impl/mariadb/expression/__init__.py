# src/rhosocial/activerecord/backend/impl/mariadb/expression/__init__.py
"""
MariaDB-specific expression classes.

This module provides expression classes that are specific to MariaDB, such as
LOAD DATA INFILE, JSON_TABLE, JSON functions, spatial functions, vector
functions, MATCH...AGAINST expressions, and row-level locking expressions.

Directory structure:
- load_data.py      - LOAD DATA INFILE expression
- json_table.py    - JSON_TABLE expression
- json.py           - JSON function expressions
- spatial.py         - Spatial function expressions
- match_against.py - MATCH...AGAINST expression
- locking.py        - Row-level locking expressions (FOR UPDATE, FOR SHARE)
"""

from .load_data import MariaDBLoadDataExpression, LoadDataOptions
from .json_table import MariaDBJSONTableExpression, JSONTableColumn, NestedPath
from .json import (
    MariaDBJSONExtractExpression,
    MariaDBJSONObjectExpression,
    MariaDBJSONArrayExpression,
    MariaDBJSONContainsExpression,
)
from .spatial import (
    MariaDBSTGeomFromTextExpression,
    MariaDBSTDistanceExpression,
    MariaDBSTWithinExpression,
    MariaDBSTContainsExpression,
)
from .match_against import MariaDBMatchAgainstExpression, MatchAgainstMode
from .locking import MariaDBForUpdateClause, MariaDBLockStrength

__all__ = [
    "MariaDBLoadDataExpression",
    "LoadDataOptions",
    "MariaDBJSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "MariaDBJSONExtractExpression",
    "MariaDBJSONObjectExpression",
    "MariaDBJSONArrayExpression",
    "MariaDBJSONContainsExpression",
    "MariaDBSTGeomFromTextExpression",
    "MariaDBSTDistanceExpression",
    "MariaDBSTWithinExpression",
    "MariaDBSTContainsExpression",
    "MariaDBMatchAgainstExpression",
    "MatchAgainstMode",
    "MariaDBForUpdateClause",
    "MariaDBLockStrength",
]