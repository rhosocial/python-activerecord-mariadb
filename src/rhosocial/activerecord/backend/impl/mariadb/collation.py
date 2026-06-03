# src/rhosocial/activerecord/backend/impl/mariadb/collation.py
"""
MariaDB collation names supported by the dialect whitelist.
"""

from enum import Enum
from typing import Optional, Tuple


class MariaDBCollation(Enum):
    """Common MariaDB collations for expression-level COLLATE."""

    BINARY = "binary"
    LATIN1_SWEDISH_CI = "latin1_swedish_ci"
    UTF8_GENERAL_CI = "utf8_general_ci"
    UTF8_UNICODE_CI = "utf8_unicode_ci"
    UTF8MB4_BIN = "utf8mb4_bin"
    UTF8MB4_GENERAL_CI = "utf8mb4_general_ci"
    UTF8MB4_UNICODE_CI = "utf8mb4_unicode_ci"


_MARIADB_COLLATIONS = {collation.value for collation in MariaDBCollation}


def validate_mariadb_collation_name(
    name: str,
    version: Optional[Tuple[int, int, int]] = None,
) -> str:
    normalized = name.lower()
    if normalized not in _MARIADB_COLLATIONS:
        raise ValueError(f"Unsupported MariaDB collation: {name!r}")
    return normalized
