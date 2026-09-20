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

from rhosocial.activerecord.backend.expression.statements import CreateTableOptions

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBCreateTableOptions",
]


class MariaDBCreateTableOptions(CreateTableOptions):
    """A MariaDB CREATE TABLE options declaration extending the generic one.

    Adds the MariaDB-only ``engine`` / ``charset`` / ``collate`` table options.
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
