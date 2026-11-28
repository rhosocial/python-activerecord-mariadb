# src/rhosocial/activerecord/backend/impl/mariadb/expression/statements/alter_table_options.py
"""MariaDB ``ALTER TABLE ... <table options>`` statement.

MariaDB's ``ALTER TABLE`` grammar accepts ``table_options`` as one of its
alter specifications, so an existing table's engine, character set, collation,
row format, comment and auto-increment counter can be changed in place::

    ALTER TABLE t ENGINE=InnoDB, DEFAULT CHARSET=utf8mb4, COMMENT='orders'

The option vocabulary is the same one ``CREATE TABLE`` uses, but core models
table options only for creation (``CreateTableOptions``) and has no ALTER-time
carrier. This node is therefore owned by this backend and is never re-exported
from core.

The constructor collects parameters and validates nothing; the dialect
formatter owns the value checks (engine/charset/collation vocabularies), the
literal quoting and every refusal.
"""

from typing import Any, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect

__all__ = ["MariaDBAlterTableOptionsStatement"]


class MariaDBAlterTableOptionsStatement(BaseExpression):
    """``ALTER TABLE <table> <engine/charset/collate/row-format/comment>``.

    Args:
        dialect: The MariaDB dialect, or ``None`` for a later binding.
        table: Target table name.
        engine: Storage engine, e.g. ``"InnoDB"``.
        charset: Character set, e.g. ``"utf8mb4"``; rendered as
            ``DEFAULT CHARSET=...``.
        collate: Collation name, e.g. ``"utf8mb4_general_ci"``.
        row_format: Row format word, e.g. ``"COMPACT"``.
        comment: Table comment text; empty string removes it.
        auto_increment: Next auto-increment value.
        schema: Optional database name.

    At least one option must be supplied -- an ``ALTER TABLE`` with no alter
    specification is not a statement, and the formatter refuses it by name.
    """

    def __init__(
        self,
        dialect: Optional["MariaDBDialect"],
        table: str,
        *,
        engine: Optional[Any] = None,
        charset: Optional[Any] = None,
        collate: Optional[str] = None,
        row_format: Optional[Any] = None,
        comment: Optional[str] = None,
        auto_increment: Optional[int] = None,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.engine = engine
        self.charset = charset
        self.collate = collate
        self.row_format = row_format
        self.comment = comment
        self.auto_increment = auto_increment
        self.schema = schema

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this statement."""
        return "format_mariadb_alter_table_options_statement"
