# src/rhosocial/activerecord/backend/impl/mariadb/expression/column.py
"""MariaDB-specific column definition expressions.

MariaDB extends the standard column definition with per-column attributes that
have no generic equivalent:

* ``CHARACTER SET <name>`` — column character set.
* ``COLLATE <name>`` — column collation.
* ``COLUMN_FORMAT {FIXED|DYNAMIC|DEFAULT}`` — column format.
* ``STORAGE {DISK|MEMORY|DEFAULT}`` — storage type.
* ``INVISIBLE`` — column hidden from ``SELECT *``.

These live on ``MariaDBColumnDefinition`` (deriving the generic
``ColumnDefinition``) and are rendered by the MariaDB
``format_column_definition`` override. They are declared through
``MariaDBColumnOptions`` (deriving the generic ``ColumnOptions``).

MariaDB implements this independently of MySQL: the two backends never share
column classes, even where their syntax coincides.
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.base.ddl.options import ColumnOptions

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBColumnFormat",
    "MariaDBColumnStorage",
    "MariaDBColumnDefinition",
    "MariaDBColumnOptions",
]


class MariaDBColumnFormat(Enum):
    """MariaDB ``COLUMN_FORMAT`` values."""

    FIXED = "FIXED"
    DYNAMIC = "DYNAMIC"
    DEFAULT = "DEFAULT"


class MariaDBColumnStorage(Enum):
    """MariaDB ``STORAGE`` values."""

    DISK = "DISK"
    MEMORY = "MEMORY"
    DEFAULT = "DEFAULT"


class MariaDBColumnDefinition(ColumnDefinition):
    """A MariaDB column definition extending the generic one.

    Adds MariaDB-only typed attributes: ``character_set``, ``column_format``,
    ``storage`` and ``invisible``.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        data_type,
        constraints=None,
        comment: Optional[str] = None,
        generated_expression=None,
        attributes=None,
        *,
        character_set: Optional[str] = None,
        column_format: Optional[MariaDBColumnFormat] = None,
        storage: Optional[MariaDBColumnStorage] = None,
        invisible: Optional[bool] = None,
    ):
        super().__init__(
            dialect,
            name,
            data_type,
            constraints=constraints,
            comment=comment,
            generated_expression=generated_expression,
            attributes=attributes,
        )
        if column_format is not None and not isinstance(column_format, MariaDBColumnFormat):
            raise TypeError(
                "column_format must be a MariaDBColumnFormat value, "
                f"got {type(column_format).__name__}"
            )
        if storage is not None and not isinstance(storage, MariaDBColumnStorage):
            raise TypeError(
                "storage must be a MariaDBColumnStorage value, "
                f"got {type(storage).__name__}"
            )
        self.character_set = character_set
        self.column_format = column_format
        self.storage = storage
        self.invisible = invisible


class MariaDBColumnOptions(ColumnOptions):
    """MariaDB per-column options declaration."""

    def __init__(
        self,
        *,
        character_set: Optional[str] = None,
        column_format: Optional[MariaDBColumnFormat] = None,
        storage: Optional[MariaDBColumnStorage] = None,
        invisible: Optional[bool] = None,
    ):
        super().__init__()
        if column_format is not None and not isinstance(column_format, MariaDBColumnFormat):
            raise TypeError(
                "column_format must be a MariaDBColumnFormat value, "
                f"got {type(column_format).__name__}"
            )
        if storage is not None and not isinstance(storage, MariaDBColumnStorage):
            raise TypeError(
                "storage must be a MariaDBColumnStorage value, "
                f"got {type(storage).__name__}"
            )
        self.character_set = character_set
        self.column_format = column_format
        self.storage = storage
        self.invisible = invisible

    def column_definition_class(self):
        """Build a ``MariaDBColumnDefinition`` for these options."""
        return MariaDBColumnDefinition

    def apply_to(self, column) -> None:
        """Transfer the MariaDB-only fields onto the column definition."""
        if not isinstance(column, MariaDBColumnDefinition):
            raise TypeError(
                "MariaDBColumnOptions.apply_to requires a MariaDBColumnDefinition, "
                f"got {type(column).__name__}"
            )
        column.character_set = self.character_set
        column.column_format = self.column_format
        column.storage = self.storage
        column.invisible = self.invisible
