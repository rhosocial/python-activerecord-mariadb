# src/rhosocial/activerecord/backend/impl/mariadb/mixins/typed_value.py
"""MariaDB's spellings for the value types whose literal form is its own.

MariaDB agrees with the base on NULL, booleans, numbers, strings and
date/time values -- measured, not assumed: on 13.1.1 (192.168.1.3:15694) a
``CREATE TABLE`` carrying ``DEFAULT TRUE`` / ``DEFAULT FALSE`` / ``DEFAULT 42``
/ ``DEFAULT 1.5`` / ``DEFAULT 1.25`` / ``DEFAULT 'x''y'`` / ``DEFAULT
'2026-10-17'`` / ``DEFAULT '10:30:00'`` / ``DEFAULT '2026-10-17 10:00:00'``
is accepted, and the defaults read back as the same values -- so no tier-1
method is overridden here.

Two value types differ, and both differ because MariaDB's grammar says so:

* **binary** -- ``X'0102FF'``, the ``x''``-quoted hex form. Measured on
  13.1.1: ``SELECT X'0102FF'`` returns ``b'\\x01\\x02\\xff'`` and a
  ``VARBINARY(16) DEFAULT X'0102FF'`` (likewise ``TINYBLOB``) fills the
  column with those bytes on insert. Lower-case hex is accepted too;
  the upper-case spelling is what this dialect renders. Quoting the bytes
  as text would produce a string that reads back as text -- the wrong
  value in a binary column and the wrong length besides.
* **UUID** -- the bare quoted canonical text. MariaDB has no literal
  form other than the text (the ``0x``-prefixed hex form is a *binary*
  literal, measured to come back as bytes, not as a UUID). Measured on
  13.1.1: ``CHAR(36) DEFAULT '550e8400-...-446655440000'`` and the native
  ``UUID`` column type (MariaDB 10.7+) with the same default each read
  the hyphenated text back verbatim, so one spelling serves both column
  homes and no ``::uuid``-style suffix exists to add.

**INTERVAL stays unimplemented on purpose.** Measured on 13.1.1:
``SELECT INTERVAL 1 DAY`` is a syntax error (errno 1064) and a column
``iv INTERVAL DEFAULT INTERVAL 1 DAY`` is refused as ``Unknown data
type: 'INTERVAL'`` (errno 4161) -- ``INTERVAL`` exists only as the
keyword-parameter of date arithmetic (``DATE_ADD('2026-10-17', INTERVAL 1
DAY)`` is accepted), never as a value with a literal form of its own. A
DDL position that needs one cannot be written for this engine, so this
mixin defines no ``format_interval_value`` -- leaving the method absent
is what makes the base's explicit failure the answer here.
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.values import TypedValue


class MariaDBTypedValueMixin:
    """MariaDB's tier-2 value literals.

    Stands alone rather than inheriting :class:`TypedValueMixin`, like every
    other MariaDB mixin: the dialect composes the specific mixin ahead of the
    generic one, and these methods win by that position. Inheriting would put
    the base ahead of the other generic mixins and make the ordering the
    dialect has to reason about depend on this class instead.
    """

    def format_binary_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A binary literal: ``X'0102FF'``, upper-case hex.

        Rendered from the bytes the node holds, because this conversion has
        to happen somewhere and the dialect is the only layer that knows
        which form its engine accepts.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return f"X'{bytes(expr.value).hex().upper()}'", ()

    def format_uuid_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A UUID as the bare quoted canonical text.

        MariaDB accepts the hyphenated form in ``CHAR(36)`` and in its
        native ``UUID`` column type alike, and offers no other literal
        spelling (the ``0x`` form is a binary literal).
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return self.format_literal(str(expr.value)), ()
