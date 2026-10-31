# src/rhosocial/activerecord/backend/impl/mariadb/introspection/types.py
"""Typed results for MariaDB's own introspection families.

Two families live here that the cross-backend introspection model does not
have: sequences and table options. Both are read from ``information_schema``
and both are MariaDB vocabulary, so they are typed in this backend and
returned by its introspectors alone.

Both dataclasses are frozen: an introspection result reports what the server
held when it was read, and a caller mutating it would make the cache lie.
"""

from dataclasses import dataclass
from typing import Optional

__all__ = ["SequenceInfo", "TableOptionsInfo"]


@dataclass(frozen=True)
class SequenceInfo:
    """One MariaDB sequence.

    A sequence *is* a table: MariaDB 10.3 added ``CREATE SEQUENCE``, and the
    sequence appears in ``information_schema.TABLES`` with
    ``TABLE_TYPE='SEQUENCE'``. That table row is the definition of the list
    this type belongs to, and it is the only source available on every server
    that has sequences at all.

    The numeric facts -- start, bounds, increment and cycle -- are not columns
    of ``TABLES``. They live in ``information_schema.SEQUENCES``, which MariaDB
    only added in 11.7 (measured: absent through 11.4, present from 11.7). On
    10.3 through 11.4 the sequence is still listed and these fields are
    ``None``: the server keeps the values, but exposes no view to read them
    from. ``None`` therefore means "not reported by this server", not
    "unset" -- the defaults a sequence gets when a clause is omitted are the
    server's, and this backend does not invent them.

    ``cache_size`` is ``None`` on every server. No ``information_schema`` view
    carries a sequence's cache size; it survives only in the text of
    ``SHOW CREATE SEQUENCE``. Reading it would mean parsing a DDL string, so
    the field is reported as not exposed rather than filled from a different
    kind of source.

    Fields:
        name: The sequence name (``SEQUENCE_NAME`` / ``TABLE_NAME``).
        schema: The schema the sequence lives in.
        start_value: The declared ``START WITH`` value, when reported.
        minimum_value: The declared or default ``MINVALUE``, when reported.
        maximum_value: The declared or default ``MAXVALUE``, when reported.
        increment: The declared ``INCREMENT BY``, when reported.
        cycle: Whether the sequence wraps around, when reported.
        cache_size: Always ``None``; see above.
        data_type: The sequence's numeric type (``bigint``), when reported.
    """

    name: str
    schema: str
    start_value: Optional[int] = None
    minimum_value: Optional[int] = None
    maximum_value: Optional[int] = None
    increment: Optional[int] = None
    cycle: Optional[bool] = None
    cache_size: Optional[int] = None
    data_type: Optional[str] = None


@dataclass(frozen=True)
class TableOptionsInfo:
    """The storage options of one relation, as ``information_schema.TABLES``
    reports them.

    ``table_type`` is carried because ``TABLES`` holds base tables, views and
    sequences in one list, and ``ENGINE``/``ROW_FORMAT``/``AUTO_INCREMENT``
    mean different things (or nothing) for each. A view reports ``engine`` as
    ``None``; that is the server's answer, not a missing field.

    ``create_options`` is the server's own text of the options that have no
    column of their own (``row_format=DYNAMIC``, ``partitioned``, and so on),
    kept verbatim rather than parsed: the set of options MariaDB can write
    there grows with the server, and a parser here would silently drop what it
    does not know.
    """

    name: str
    schema: str
    table_type: Optional[str] = None
    engine: Optional[str] = None
    row_format: Optional[str] = None
    collation: Optional[str] = None
    auto_increment: Optional[int] = None
    comment: Optional[str] = None
    create_options: Optional[str] = None
