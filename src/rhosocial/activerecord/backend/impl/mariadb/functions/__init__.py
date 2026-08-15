# src/rhosocial/activerecord/backend/impl/mariadb/functions/__init__.py
"""
MariaDB-specific SQL function factories.

This module provides factory functions for creating MariaDB-specific SQL
expression objects, organized into submodules by category:

- json: JSON functions (json_extract, json_object, etc.)
- spatial: Spatial/geometric functions (st_geom_from_text, st_distance, etc.)
- fulltext: Full-text search functions (match_against)
- enum_set: SET and Enum type functions (find_in_set, elt, field)
- math_enhanced: Enhanced math functions (round, pow, sqrt, ceil, floor, etc.)

Usage:
    from rhosocial.activerecord.backend.impl.mariadb.functions import json_extract
    from rhosocial.activerecord.backend.impl.mariadb.functions import st_distance
    from rhosocial.activerecord.backend.impl.mariadb.functions import match_against
    from rhosocial.activerecord.backend.impl.mariadb.functions import round_

Or import directly from submodules:
    from rhosocial.activerecord.backend.impl.mariadb.functions.json import json_extract
    from rhosocial.activerecord.backend.impl.mariadb.functions.spatial import st_distance
    from rhosocial.activerecord.backend.impl.mariadb.functions.fulltext import match_against
    from rhosocial.activerecord.backend.impl.mariadb.functions.math_enhanced import round_

Version Requirements:
- JSON functions: MariaDB 10.2.3+
- JSON arrow operators: MariaDB 10.2.7+
- Window functions: MariaDB 10.2+
- SEQUENCE: MariaDB 10.3+
- RETURNING: MariaDB 10.5+
- Full-text search: All versions
- Spatial functions: MariaDB 10.2+
"""

from .json import (
    json_extract,
    json_unquote,
    json_object,
    json_array,
    json_contains,
    json_set,
    json_remove,
    json_type,
    json_valid,
    json_search,
)

from .math_enhanced import (
    round_,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_,
    min_,
    avg,
)

from .spatial import (
    st_geom_from_text,
    st_geom_from_wkb,
    st_as_text,
    st_as_geojson,
    st_distance,
    st_within,
    st_contains,
    st_intersects,
)

from .fulltext import (
    match_against,
)

from .enum_set import (
    find_in_set,
    elt,
    field,
)

from .bitwise import (
    bit_and,
    bit_or,
    bit_xor,
    bit_count,
    bit_get_bit,
    bit_shift_left,
    bit_shift_right,
)

__all__ = [
    # JSON functions
    "json_extract",
    "json_unquote",
    "json_object",
    "json_array",
    "json_contains",
    "json_set",
    "json_remove",
    "json_type",
    "json_valid",
    "json_search",
    # Spatial functions
    "st_geom_from_text",
    "st_geom_from_wkb",
    "st_as_text",
    "st_as_geojson",
    "st_distance",
    "st_within",
    "st_contains",
    "st_intersects",
    # Full-text search
    "match_against",
    # SET type functions
    "find_in_set",
    # Enum type functions
    "elt",
    "field",
    # Math enhanced functions
    "round_",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_",
    "min_",
    "avg",
    # Bitwise functions
    "bit_and",
    "bit_or",
    "bit_xor",
    "bit_count",
    "bit_get_bit",
    "bit_shift_left",
    "bit_shift_right",
]