# MariaDB Datetime Expressions

Core's expression layer states the temporal questions and this backend spells
them. `seconds_between` is the one that needed a MariaDB spelling of its own:
the distance between two instants, signed, and fractional where the column
keeps a fraction.

## `seconds_between`

```python
from rhosocial.activerecord.backend.expression import Column, seconds_between

elapsed = seconds_between(
    dialect,
    Column(dialect, "queued_at"),
    Column(dialect, "started_at"),
).as_("queue_seconds")
sql, params = elapsed.to_sql()
# sql: (
#   TIMESTAMPDIFF(MICROSECOND, `queued_at`, `started_at`) / 1000000
# ) AS `queue_seconds`
# params: ()
```

The node answers with `end - start`, so the direction is part of the value:

| Case | Result |
|------|--------|
| `end` later than `start` | positive |
| `end` earlier than `start` | negative |
| same instant | `0` |
| a `DATETIME(6)` fraction present | kept, subject to the scale below |

`TIMESTAMPDIFF(SECOND, start, end)` is not used: it counts whole seconds and
drops the fraction. Counting in `MICROSECOND` and dividing by `1000000`
keeps the sub-second part that a `DATETIME(6)` column stores.

The quotient is MariaDB's exact division of two integers, so its scale is the
integer's scale plus `div_precision_increment` (4 by default). That is 0.1 ms
resolution out of the box. A caller that needs the full microsecond can raise
the session's `div_precision_increment` or cast the result to a wider decimal;
a caller that wants whole seconds rounds explicitly, because the node never
does.

## Operand order and binding

The operands are rendered in the SQL's order -- `start` first, `end` second --
so the bind parameters follow the placeholders rather than the constructor's
argument order:

```python
from rhosocial.activerecord.backend.expression import Literal, seconds_between

expr = seconds_between(
    dialect,
    Literal(dialect, "2026-01-01 00:00:00"),
    Literal(dialect, "2026-01-02 00:00:00"),
)
sql, params = expr.to_sql()
# sql: "(TIMESTAMPDIFF(MICROSECOND, %s, %s) / 1000000)"
# params: ("2026-01-01 00:00:00", "2026-01-02 00:00:00")
```

The division is parenthesised, so the node composes as an operand and
`.as_("...")` applies to the whole value rather than to the second argument of
`TIMESTAMPDIFF`.

## Contract

This backend implements core's one dialect hook:

```python
def format_seconds_between_expression(self, expr) -> Tuple[str, Tuple]:
```

The signature, the sign rule and the alias behaviour are core's. What MariaDB
adds is the spelling and the `MICROSECOND` unit; the full cross-backend table
is in
[core's expression docs](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/backend/expression/functions.md#seconds_between).
