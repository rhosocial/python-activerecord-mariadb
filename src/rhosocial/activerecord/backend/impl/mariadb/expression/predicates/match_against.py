# src/rhosocial/activerecord/backend/impl/mariadb/expression/predicates/match_against.py
"""MariaDB MATCH...AGAINST predicate vocabulary.

The closed set of MATCH modes used by the full-text predicate. Kept apart
from the expression node so the predicate vocabulary has its own home.
"""

from enum import Enum


class MatchAgainstMode(str, Enum):
    """Full-text search modes, as the wire word form.

    A closed set, so it takes an enum rather than string constants on a class:
    the constant-class form accepted any string at the call site, which left
    the set closed in the documentation only. The ``str`` base with ``__str__``
    pinned to ``str.__str__`` makes the member the word it carries.
    """

    #: A member *is* the word it carries (org rules §11.3).
    __str__ = str.__str__

    NATURAL_LANGUAGE = "NATURAL LANGUAGE"
    BOOLEAN = "BOOLEAN"
    NATURAL_LANGUAGE_WITH_QUERY_EXPANSION = "NATURAL LANGUAGE WITH QUERY EXPANSION"


__all__ = [
    "MatchAgainstMode",
]
