# src/rhosocial/activerecord/backend/impl/mariadb/expression/value_types/table_options.py
"""MariaDB ``ROW_FORMAT`` table-option values.

A closed set of words, kept apart from the statement that carries them.
"""

from enum import Enum


class MariaDBRowFormat(str, Enum):
    """MariaDB ``ROW_FORMAT`` table option values.

    A closed set, so it takes an enum with a ``str`` base and ``__str__``
    pinned to ``str.__str__``: the member is the word it carries.
    """

    #: A member *is* the word it carries (org rules §11.3).
    __str__ = str.__str__

    DEFAULT = "DEFAULT"
    DYNAMIC = "DYNAMIC"
    FIXED = "FIXED"
    COMPRESSED = "COMPRESSED"
    REDUNDANT = "REDUNDANT"
    COMPACT = "COMPACT"
    PAGE = "PAGE"


__all__ = [
    "MariaDBRowFormat",
]
