# src/rhosocial/activerecord/backend/impl/mariadb/introspection/types.py
"""Typed results for MariaDB's own introspection families.

The families here are MariaDB vocabulary rather than part of the
cross-backend introspection model: sequences and table options (from
``information_schema.TABLES``), partitions (from ``PARTITIONS``), stored
routines (from ``ROUTINES``/``PARAMETERS``) and CHECK constraints (from
``TABLE_CONSTRAINTS``/``CHECK_CONSTRAINTS``). Each is typed in this backend
and returned by its introspectors alone.

Every dataclass is frozen: an introspection result reports what the server
held when it was read, and a caller mutating it would make the cache lie.
Fields are optional when the server did not report a value; ``None`` always
means "not reported", never an invented default.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

__all__ = [
    "SequenceInfo",
    "TableOptionsInfo",
    "MariaDBPartitionInfo",
    "MariaDBRoutineInfo",
    "MariaDBRoutineParameterInfo",
    "MariaDBConstraintInfo",
]


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

    def to_core(self):
        """Project this sequence onto core's common minimum.

        Four backends grew four sequence classes, so core now carries the
        smallest shape every engine with sequences can answer
        (:class:`rhosocial.activerecord.backend.introspection.SequenceInfo`)
        as the cross-dialect entry point. This class stays the complete
        MariaDB semantics; the projection joins the two by mapping, not by
        inheritance, so a field core has no meaning for is ``None`` rather
        than a guess (``.claude/rules/introspection.md`` §5).

        ``last_value`` is the one core slot MariaDB has no view to read a
        sequence's current value from, so it is reported as not exposed
        rather than filled from a different kind of source.
        """
        from rhosocial.activerecord.backend.introspection import SequenceInfo as CoreSequenceInfo

        return CoreSequenceInfo(
            name=self.name,
            schema=self.schema,
            data_type=self.data_type,
            start_value=self.start_value,
            minimum_value=self.minimum_value,
            maximum_value=self.maximum_value,
            increment=self.increment,
            cycle=self.cycle,
            cache_size=self.cache_size,
            last_value=None,
        )


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


@dataclass(frozen=True)
class MariaDBPartitionInfo:
    """One row of ``information_schema.PARTITIONS`` for a table.

    A sequence is a table on MariaDB; a partition is a *row* of that table's
    physical layout. The view reports one row per partition, and one row per
    (partition, subpartition) pair when the table is subpartitioned. The
    subpartition identity is therefore carried alongside the partition one:
    without it two rows of the same partition would look identical.

    ``partition_method`` is the server's own spelling -- ``RANGE``, ``RANGE
    COLUMNS``, ``LIST``, ``LIST COLUMNS``, ``HASH``, ``LINEAR HASH``, ``KEY``
    or ``LINEAR KEY`` -- rather than a normalised enum, because MariaDB keeps
    the exact grammar token the DDL used and a caller re-deriving DDL needs it.
    ``partition_expression`` is the expression the method applied to
    (``YEAR(created_at)``, a column list, or an empty string for ``KEY``).
    ``partition_description`` is the RANGE/LIST boundary text as the server
    writes it; it is deliberately not parsed into values here, because the
    parsing rules depend on the partition method and on the column's type.

    ``None`` means the server did not report the slot. A non-partitioned
    table is not represented at all: the ``PARTITION_NAME IS NULL`` row the
    view returns for it is excluded by the statement, so an empty list means
    exactly "this table is not partitioned".

    Fields:
        schema: The database the table lives in.
        table_name: The partitioned table's name.
        partition_name: The partition's name.
        subpartition_name: The subpartition's name when subpartitioned.
        partition_method: The server's partition method token.
        subpartition_method: The server's subpartition method token.
        partition_expression: The top-level partitioning expression.
        subpartition_expression: The subpartitioning expression.
        partition_description: The RANGE/LIST boundary text.
        subpartition_description: The subpartition boundary text, when the
            server publishes it. MariaDB's ``information_schema.PARTITIONS``
            has no such column (it publishes the subpartition name, method,
            expression and ordinal, but not the boundary text), so this field
            stays ``None`` there; the only source would be the de-parsed
            ``SHOW CREATE TABLE`` text, which this backend does not read.
        partition_ordinal_position: 1-based partition position.
        subpartition_ordinal_position: 1-based position within the partition.
        table_rows: Rows the server estimates this partition holds.
        data_length: Bytes the server accounts to this partition's rows.
        index_length: Bytes the server accounts to this partition's indexes.
        partition_comment: The partition's ``COMMENT``, when declared.
    """

    schema: str
    table_name: str
    partition_name: Optional[str] = None
    subpartition_name: Optional[str] = None
    partition_method: Optional[str] = None
    subpartition_method: Optional[str] = None
    partition_expression: Optional[str] = None
    subpartition_expression: Optional[str] = None
    partition_description: Optional[str] = None
    subpartition_description: Optional[str] = None
    partition_ordinal_position: Optional[int] = None
    subpartition_ordinal_position: Optional[int] = None
    table_rows: Optional[int] = None
    data_length: Optional[int] = None
    index_length: Optional[int] = None
    partition_comment: Optional[str] = None

    @property
    def is_subpartition(self) -> bool:
        """Whether this row describes a subpartition rather than a partition."""
        return self.subpartition_name is not None

    @property
    def total_length(self) -> Optional[int]:
        """Data plus index bytes, or ``None`` when neither was reported."""
        if self.data_length is None and self.index_length is None:
            return None
        return (self.data_length or 0) + (self.index_length or 0)


@dataclass(frozen=True)
class MariaDBRoutineParameterInfo:
    """One parameter of a stored procedure or function.

    ``information_schema.PARAMETERS`` reports a function's return value as
    a synthetic row at ``ORDINAL_POSITION = 0``; that row is not a parameter
    and is filtered out before parsing, so ordinal positions here start at
    one. ``mode`` is ``IN``, ``OUT``, ``INOUT`` or ``None`` for a parameter
    whose direction the server did not report.

    ``data_type`` is the base type word (``INT``, ``VARCHAR``, ...) and
    ``data_type_full`` is ``DTD_IDENTIFIER`` -- the declared type with its
    length, precision or enum/set labels. Keeping both means a caller can
    branch on the family without losing the declaration.
    """

    ordinal_position: int
    mode: Optional[str] = None
    name: Optional[str] = None
    data_type: Optional[str] = None
    data_type_full: Optional[str] = None


@dataclass(frozen=True)
class MariaDBRoutineInfo:
    """One stored procedure or function, from ``information_schema.ROUTINES``.

    ``kind`` is the server's ``ROUTINE_TYPE`` -- ``PROCEDURE`` or
    ``FUNCTION``. The two share ``ROUTINES`` and can, on MariaDB, share a
    name, which is why the kind is part of the identity and why
    ``get_routine_info`` accepts it to disambiguate.

    ``return_type`` is populated for a function only. A procedure has no
    return type, so the field stays ``None`` rather than repeating ``DATA_TYPE``
    (which the server fills with an empty value for procedures).

    ``language`` is ``EXTERNAL_LANGUAGE`` when the routine is external, and
    ``ROUTINE_BODY`` (``SQL``) otherwise. ``deterministic`` is the server's
    ``IS_DETERMINISTIC``; ``None`` means it was not reported. The routine
    body text is not part of this type: it lives in ``ROUTINE_DEFINITION`` and
    can be very large, so it is deliberately left to ``SHOW CREATE`` rather
    than duplicated in every listing.

    Fields:
        schema: The database the routine lives in.
        name: The routine name.
        kind: ``PROCEDURE`` or ``FUNCTION``.
        return_type: The declared return type, for functions only.
        parameters: The routine's parameters, ordered by position.
        language: The routine language, when reported.
        deterministic: Whether the routine is declared deterministic.
        sql_data_access: ``CONTAINS SQL``, ``NO SQL``, ``READS SQL DATA`` or
            ``MODIFIES SQL DATA``.
        security_type: ``DEFINER`` or ``INVOKER``.
        comment: The routine's ``COMMENT``.
        definer: The definer as ``user@host``.
        created: Creation timestamp, as the server rendered it.
        last_altered: Last-alteration timestamp, as the server rendered it.
    """

    schema: str
    name: str
    kind: str
    return_type: Optional[str] = None
    parameters: Tuple[MariaDBRoutineParameterInfo, ...] = ()
    language: Optional[str] = None
    deterministic: Optional[bool] = None
    sql_data_access: Optional[str] = None
    security_type: Optional[str] = None
    comment: Optional[str] = None
    definer: Optional[str] = None
    created: Optional[str] = None
    last_altered: Optional[str] = None

    @property
    def is_function(self) -> bool:
        """Whether this routine is a function (and therefore has a return type)."""
        return self.kind.upper() == "FUNCTION"


@dataclass(frozen=True)
class MariaDBConstraintInfo:
    """One CHECK constraint on a table.

    This family answers CHECK constraints only. PRIMARY KEY and UNIQUE live
    in ``information_schema.STATISTICS`` and are reported by ``list_indexes``;
    FOREIGN KEY has its own family and its referenced table, which a CHECK
    row could not carry without inventing columns. So ``constraint_type`` is
    kept -- always ``CHECK`` today -- so the shape can grow if a later family
    adds kinds, without a caller having to change its field access.

    MariaDB's catalog has no ``ENFORCED`` column (the constraint is enforced
    from the release that started recording CHECK rows at all), so ``enforced``
    stays ``None``: "not reported", not "disabled". ``check_clause`` is the
    engine's own expression text, which is the only reliable source for
    re-creating the constraint.
    """

    schema: str
    table_name: str
    name: str
    constraint_type: str = "CHECK"
    check_clause: Optional[str] = None
    enforced: Optional[bool] = None
