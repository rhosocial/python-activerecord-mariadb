# src/rhosocial/activerecord/backend/impl/mariadb/mixins/literal.py
"""MariaDB's tier-2 value literals.

``SQLDialectBase.format_literal`` is the single entry point for writing a
value as SQL text, and it resolves in three tiers: the portable scalars it
knows, the types a backend spells for themselves, and the
literal-construction protocol. This module is MariaDB's second tier, and it
carries the two spellings measured on the live server (13.1.1,
192.168.1.3:15694):

* ``bytes`` becomes ``X'0102FF'``, the x-quoted upper-case hex form.
  ``SELECT X'0102FF'`` returns those bytes and a ``VARBINARY(16)`` /
  ``TINYBLOB DEFAULT X'0102FF'`` fills the column with them on insert;
  lower-case hex is accepted too, and upper-case is what this dialect
  renders. Quoting the bytes as text would read back as text -- the wrong
  value in a binary column and the wrong length besides.
* ``UUID`` becomes the bare quoted canonical text. ``CHAR(36) DEFAULT
  '...'`` and the native ``UUID`` column type (MariaDB 10.7+) accept it
  identically, and the ``0x``-prefixed form is a *binary* literal
  (measured to come back as bytes), so it is not an alternative here.

**INTERVAL stays unimplemented on purpose.** ``timedelta`` has no branch
here, so the base's explicit refusal is the answer: measured on 13.1.1,
``SELECT INTERVAL 1 DAY`` is a syntax error (errno 1064) and a column
``iv INTERVAL DEFAULT INTERVAL 1 DAY`` is refused as ``Unknown data type:
'INTERVAL'`` (errno 4161). ``INTERVAL`` exists only as the keyword
parameter of date arithmetic (``DATE_ADD('2026-10-17', INTERVAL 1 DAY)``
is accepted), never as a value with a literal form of its own, and this
module adds no spelling rather than inventing one.

The tier-1 forms (NULL / booleans / numbers / strings / dates / times /
datetimes) are the base's: measured on 13.1.1 as ``DEFAULT`` values
accepted by ``CREATE TABLE`` (``TRUE`` / ``FALSE`` / ``42`` / ``1.5`` /
``1.25`` / ``'x''y'`` / ``'2026-10-17'`` / ``'10:30:00'`` /
``'2026-10-17 10:00:00'``) and read back unchanged, so none of them is
overridden.
"""

import uuid
from typing import Any


class MariaDBLiteralValueMixin:
    """MariaDB's tier-2 branches of :meth:`format_literal`.

    Stands alone rather than inheriting the base, and the dialect composes
    it ahead of :class:`SQLDialectBase` -- the one base that defines
    ``format_literal`` -- because a mixin placed after the class it
    overrides never wins.
    """

    def format_literal(self, value: Any) -> str:
        """Render *value* as inline SQL text, MariaDB's spelling where it has one.

        Args:
            value: The host value to write into the statement.

        Returns:
            The escaped literal text, without a bind parameter.

        Raises:
            TypeError: The base implementation refuses a type MariaDB has
                no literal form for -- ``timedelta`` among them, which is
                the measured answer rather than a gap.
        """
        if isinstance(value, (bytes, bytearray)):
            return f"X'{bytes(value).hex().upper()}'"
        if isinstance(value, uuid.UUID):
            return self.format_literal(str(value))
        return super().format_literal(value)
