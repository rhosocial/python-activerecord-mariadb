# src/rhosocial/activerecord/backend/impl/mariadb/expression/table_options.py
"""MariaDB-specific CREATE TABLE options.

MariaDB adds table-level options that have no generic equivalent:

* ``ENGINE=<name>`` — storage engine.
* ``DEFAULT CHARSET=<name>`` — table character set.
* ``COLLATE=<name>`` — table collation.

These live on ``MariaDBCreateTableOptions`` (deriving the generic
``CreateTableOptions``) and are rendered by the MariaDB
``format_create_table_statement`` override. MariaDB implements this
independently of MySQL; the two backends never share table-option classes.
"""

from typing import Optional, TYPE_CHECKING
from enum import Enum

from rhosocial.activerecord.backend.expression.statements import CreateTableOptions

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBRowFormat",
    "MariaDBCreateTableOptions",
]


class MariaDBRowFormat(Enum):
    """MariaDB ``ROW_FORMAT`` table option values."""

    DEFAULT = "DEFAULT"
    DYNAMIC = "DYNAMIC"
    FIXED = "FIXED"
    COMPRESSED = "COMPRESSED"
    REDUNDANT = "REDUNDANT"
    COMPACT = "COMPACT"
    PAGE = "PAGE"


class MariaDBCreateTableOptions(CreateTableOptions):
    """A MariaDB CREATE TABLE options declaration extending the generic one.

    Adds the MariaDB-only ``engine`` / ``charset`` / ``collate`` /
    ``auto_increment`` / ``row_format`` / ``with_system_versioning`` options.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        or_replace: bool = False,
        comment: Optional[str] = None,
        engine: Optional[object] = None,
        charset: Optional[object] = None,
        collate: Optional[str] = None,
        auto_increment: Optional[int] = None,
        row_format: Optional[object] = None,
        with_system_versioning: bool = False,
    ):
        super().__init__(dialect, or_replace=or_replace, comment=comment)
        self.engine = (
            dialect.validate_storage_engine_name(engine) if engine is not None else None
        )
        self.charset = (
            dialect.validate_charset_name(charset) if charset is not None else None
        )
        self.collate = (
            dialect.validate_collation_by_name(collate) if collate is not None else None
        )
        if auto_increment is not None and (
            not isinstance(auto_increment, int) or auto_increment <= 0
        ):
            raise ValueError(
                f"auto_increment must be a positive int, got {auto_increment!r}"
            )
        self.auto_increment = auto_increment
        self.row_format = self._normalize_row_format(row_format)
        self.with_system_versioning = bool(with_system_versioning)

    @staticmethod
    def _normalize_row_format(value: Optional[object]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, MariaDBRowFormat):
            return value.value
        if isinstance(value, str):
            normalized = value.upper()
            if normalized in {member.value for member in MariaDBRowFormat}:
                return normalized
            raise ValueError(f"Unsupported MariaDB ROW_FORMAT: {value!r}")
        raise TypeError(
            f"row_format must be MariaDBRowFormat or str, got {type(value).__name__}"
        )
