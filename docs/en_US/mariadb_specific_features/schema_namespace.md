# docs/en_US/mariadb_specific_features/schema_namespace.md

> What `schema_name` names on MariaDB, how it reaches the generated SQL, and the
> MariaDB-only options that attach to a qualified object.

Everything in the dialect-independent half — where a namespace comes from, when
it is read, and why DDL needs one of its own — is in
`docs/modeling/schema_namespace.md` in the core repository. This page covers only
what MariaDB does differently.

## 1. On MariaDB, a schema is a database

There is no schema layer. `schema` and `database` are two words for the same
thing, and MariaDB's own documentation writes the two together:

```
CREATE [OR REPLACE] {DATABASE | SCHEMA} [IF NOT EXISTS] db_name
    [create_specification] ...
```

> `CREATE SCHEMA` is a synonym for `CREATE DATABASE`.

Three consequences follow, all confirmed on a live server:

* `CREATE SCHEMA app` creates the database `app`. The MariaDB documentation has no
  `CREATE SCHEMA` page of its own; the statement is documented as `CREATE DATABASE`.
* `SHOW DATABASES` and `SHOW SCHEMAS` return the same list, and both contain a
  database created as a schema.
* A schema-qualified reference is a **cross-database** reference. `` `shop`.`orders` ``
  reads a table in the database `shop`, not in a schema of the current database.

That last point is the whole difference from PostgreSQL. In PostgreSQL a schema
is a namespace *inside* the database you are connected to: `search_path` decides
which one an unqualified name resolves to, and the database itself is fixed by the
connection. In MariaDB the connection's default database plays the role that
`search_path` plays in PostgreSQL, and naming a schema means naming a *different*
database. There is no connection setting that lists several databases and searches
them in order.

`supports_schema()` returns `True` on the MariaDB dialect, and the dialect
implements the `SchemaSupport` protocol, so a `schema_name` is accepted and
rendered rather than refused. What the value names is defined by the backend, not
by the flag.

## 2. Reading and writing through a model

Declare the namespace on the model with `__schema_name__`:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = "app"        # a database named "app"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    user_id: Optional[int] = None
```

`__table_name__` and `__schema_name__` stay separate. Folding them together
(`__table_name__ = "app.orders"`) produces one quoted identifier containing a dot,
which is not a qualified reference.

**DDL does not read `__schema_name__`.** A migration that creates the table has to
name the database itself:

```python
CreateTableExpression(
    dialect,
    TableExpression(dialect, "orders", schema_name="app"),
    columns,
).to_sql()
# CREATE TABLE `app`.`orders` (`id` INT PRIMARY KEY)
```

`schema_name` defaults to `None`, which means unqualified — the same default as
everywhere else in the expression layer.

## 3. What the SQL looks like

The MariaDB dialect does not override `format_table` or `format_column`; both are
inherited from the core expression layer. What follows is what that inheritance
produces here.

**A qualified range, and an unqualified one:**

```python
TableExpression(dialect, "orders", schema_name="app").to_sql()
# `app`.`orders`

TableExpression(dialect, "orders").to_sql()
# `orders`
```

**Columns carry three parts while the range is unaliased:**

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `app`.`orders`.`id` FROM `app`.`orders`
```

The database qualifies the column all the way through, because the range in
`FROM` names no alias. This is worth comparing with the MySQL backend, which
overrides `format_column` and emits only two parts — `table`.`column` — without
reading `schema_name` at all. MariaDB keeps the third segment:

| Backend | `Column(dialect, "id", table="orders", schema_name="app")` renders |
|---|---|
| MariaDB | `` `app`.`orders`.`id` `` |
| MySQL | `` `orders`.`id` `` |

**Once an alias is in effect the database is dropped from the column**, because
the alias already identifies the range:

```python
# FROM `app`.`orders` AS `o`
# SELECT `o`.`id`          not `app`.`orders`.`id`
```

The suppression happens when the column expression is built, not when it is
rendered. The framework enforces the same rule at join time: a join condition that
still refers to the unaliased range while the join carries an alias is rejected
with a `ValueError`.

**A join spans two databases without extra configuration**, each side qualifying
its own range:

```python
Order.query().join(
    User, on=Order.c.user_id == User.c.id
).select(Order.c.id, User.c.name).to_sql()[0]
# SELECT `app`.`orders`.`id`, `crm`.`users`.`name` FROM `app`.`orders`
#   JOIN `crm`.`users` ON `app`.`orders`.`user_id` = `crm`.`users`.`id`
```

All four of these forms — the qualified table, the three-part column, the aliased
column, and the cross-database join — execute against a live server without error.

**Set operations qualify each branch.** `UNION`, `INTERSECT` and `EXCEPT` combine
queries rather than naming an object, so there is nothing for the operation itself
to qualify:

```sql
SELECT `shop`.`orders`.`id` FROM `shop`.`orders`
UNION
SELECT `crm`.`users`.`id` FROM `crm`.`users`
```

**A CTE name is not in a namespace.** A CTE is named for the rest of the query,
not for the database, so its own name is never qualified — while the query inside
it keeps carrying the model's database:

```sql
WITH `recent` AS (SELECT `shop`.`orders`.`id` FROM `shop`.`orders`)
SELECT `*` FROM `recent`
```

## 4. `None`, `""` and other values

A `schema_name` must be `None` or a non-empty string. Validation is deferred to
render time, because an expression only collects its parameters while it is being
built; the statement is not known to be whole until it renders.

`None` means unqualified. An empty string is a mistake rather than a way of
spelling unqualified, and it is rejected:

```python
TableExpression(dialect, "orders", schema_name="").to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#              use None for an unqualified reference
```

Construction succeeds; the error arrives when the statement is rendered. The same
applies when the empty string reaches a model instead:

```python
class Bad(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = ""          # accepted here, rejected on the first render

Bad.schema_name()                 # ''
Bad.c.id.schema_name              # ''
Bad.c.id.to_sql()                 # ValueError
```

A non-string is rejected the same way, with a message naming the type:

```python
Column(dialect, "id", table="orders", schema_name=123).to_sql()
# ValueError: Column.schema_name must be a string or None, not int
```

The check lives in one place in the core dialect layer rather than in each
statement, so all forty-odd expressions that accept a `schema_name` reject the
same values identically.

## 5. `CREATE SCHEMA` and `DROP SCHEMA`

Both statements render, and both map onto their database equivalents:

```python
CreateSchemaExpression(dialect, "app", if_not_exists=True).to_sql()
# CREATE SCHEMA IF NOT EXISTS `app`

DropSchemaExpression(dialect, "app", if_exists=True).to_sql()
# DROP SCHEMA IF EXISTS `app`
```

Two standard clauses are not available, and each raises `UnsupportedFeatureError`
rather than being dropped from the statement:

| Option | Behaviour on MariaDB |
|---|---|
| `CREATE SCHEMA IF NOT EXISTS` | supported |
| `DROP SCHEMA IF EXISTS` | supported |
| `DROP SCHEMA CASCADE` | refused — MariaDB has no `CASCADE` on `DROP SCHEMA` |
| `CREATE SCHEMA AUTHORIZATION` | refused — MariaDB has no `AUTHORIZATION` clause |

## 6. Triggers: three MariaDB-only options

`MariaDBCreateTriggerExpression` extends the generic `CreateTriggerExpression`
with three attributes that SQL:1999 does not have:

| Attribute | Renders as | Meaning |
|---|---|---|
| `or_replace=True` | `CREATE OR REPLACE TRIGGER` | drop and redefine an existing trigger of the same name instead of failing |
| `ordering=("FOLLOWS" \| "PRECEDES", other_trigger)` | `FOLLOWS`/`PRECEDES other_trigger` | place this trigger after or before another on the same table and event |
| `body=<expression>` | the inline statement between `BEGIN` and `END` | the statement to run, rather than a call to a stored routine |

They are declared on the MariaDB expression rather than on the core one because
they belong to no other dialect. MySQL has no `OR REPLACE` on `CREATE TRIGGER`,
and Oracle spells replacement its own way; `FOLLOWS`/`PRECEDES` are MariaDB's
answer to multiple triggers per timing and event, which MariaDB gained and MySQL
did not. `body` exists because MariaDB follows MySQL in taking an inline trigger
body, whereas the generic expression models a call to a stored function. A
formatter that reached for these with `getattr(expr, name, default)` would turn
"this dialect has no such option" into "this statement silently omits what the
caller asked for", so every attribute the MariaDB formatter reads is declared on
the expression it is read from.

**`schema_name` qualifies three things at once** — the trigger name, the table it
is bound to, and the function it calls:

```python
MariaDBCreateTriggerExpression(
    dialect, "audit_ins", "orders", TriggerTiming.BEFORE, [TriggerEvent.INSERT],
    function_name="log_order", or_replace=True,
    ordering=("FOLLOWS", "other_trg"), schema_name="app",
).to_sql()[0]
# CREATE OR REPLACE TRIGGER `app`.`audit_ins` BEFORE INSERT ON `app`.`orders`
#   FOR EACH ROW FOLLOWS `other_trg` BEGIN CALL `app`.`log_order`(); END
```

An inline body renders in the same position:

```python
MariaDBCreateTriggerExpression(
    dialect, "audit_ins", "orders", TriggerTiming.BEFORE, [TriggerEvent.INSERT],
    body=RawSQLExpression(dialect, "SET NEW.n = NEW.n + 1"),
    or_replace=True, schema_name="app",
).to_sql()[0]
# CREATE OR REPLACE TRIGGER `app`.`audit_ins` BEFORE INSERT ON `app`.`orders`
#   FOR EACH ROW BEGIN SET NEW.n = NEW.n + 1 END
```

Qualifying all three is not decoration. A MariaDB trigger must live in the same
database as its table, and the server enforces it:

```
CREATE TRIGGER `t` BEFORE INSERT ON `other_db`.`t1` FOR EACH ROW ...
ERROR 1435 (HY000): Trigger in wrong schema
```

Qualifying only the table, or only the trigger name, produces that error.

The `FOLLOWS` / `PRECEDES` reference is the one name the renderer leaves bare,
because MariaDB resolves it in the trigger's own database. A bare `FOLLOWS`
reference placed next to a trigger of the same name in the connection's default
database still ordered after the one in the trigger's database.

**Version requirements.** The official `CREATE TRIGGER` syntax places
`{ FOLLOWS | PRECEDES } other_trigger_name` after `FOR EACH ROW` and before the
body, which is where the formatter puts it. The current reference page states no
version for `OR REPLACE` or for `FOLLOWS`/`PRECEDES`; the MariaDB release notes
place `OR REPLACE` on `CREATE TRIGGER` in 10.1 (MDEV-7286, the batch that added
consistent `IF EXISTS` / `IF NOT EXISTS` / `OR REPLACE` support) and
`FOLLOWS`/`PRECEDES` together with multiple triggers per event in 10.2 (MDEV-6112).
The dialect gates `supports_trigger_order()` at 10.2.3 and reports
`supports_or_replace_trigger()` unconditionally. All three options were executed
against MariaDB 13.1.1; treat the exact minimum version as governed by the
official documentation rather than by this page.

The capability probes that are `False` on MariaDB, each raising
`UnsupportedFeatureError` when the corresponding argument is supplied:

| Probe | Why |
|---|---|
| `supports_trigger_if_not_exists()` | the dialect points callers at `or_replace` instead |
| `supports_trigger_when()` | no `WHEN` condition on a MariaDB trigger |
| `supports_trigger_referencing()` | no `REFERENCING` clause; use `OLD` and `NEW` directly |
| `supports_statement_trigger()` | `FOR EACH ROW` only |

`FOR EACH ROW` is emitted unconditionally, and `supports_instead_of_trigger()`
reports `True` from 10.4 onward.

## 7. `ALTER TABLE ... WAIT n` / `NOWAIT`

`MariaDBAlterTableExpression` adds two statement-level qualifiers that the
generic `ALTER TABLE` expression does not have, and both are placed after the
qualified table name and before the alter specifications:

```python
MariaDBAlterTableExpression(
    dialect, "orders", [RenameObject(dialect, "old_c", "new_c")],
    schema_name="app", wait=5,
).to_sql()[0]
# ALTER TABLE `app`.`orders` WAIT 5  RENAME COLUMN `old_c` TO `new_c`

MariaDBAlterTableExpression(
    dialect, "orders", [RenameObject(dialect, "old_c", "new_c")],
    schema_name="app", nowait=True,
).to_sql()[0]
# ALTER TABLE `app`.`orders` NOWAIT  RENAME COLUMN `old_c` TO `new_c`
```

(The renderer currently emits a second space between the qualifier and the first
alter specification; the two spaces above are what it produces.)

`if_exists=True` composes with both, giving
``ALTER TABLE IF EXISTS `app`.`orders` WAIT 3  RENAME COLUMN ...``.

These qualifiers control the **metadata lock** wait, not the namespace. They are
orthogonal to `schema_name`: `schema_name` says which database the table is in,
`WAIT n` / `NOWAIT` says how long to wait for a lock on it. `WAIT 0` is equivalent
to `NOWAIT`. The official syntax is
`ALTER [ONLINE] [IGNORE] TABLE [IF EXISTS] tbl_name [WAIT n | NOWAIT] alter_specification ...`.

`WAIT n` / `NOWAIT` arrived in MariaDB 10.3 as "DDL Fast Fail" (MDEV-11379,
MDEV-11388), and the dialect gates `supports_alter_table_wait()` at 10.3.0. On an
older dialect the qualifiers are refused:

```python
MariaDBAlterTableExpression(dialect_10_2, "orders", [action], nowait=True).to_sql()
# UnsupportedFeatureError: 'MariaDB' dialect does not support ALTER TABLE
# WAIT/NOWAIT. Suggestion: WAIT/NOWAIT lock wait timeout requires MariaDB 10.3
# or later.
```

The same two options exist on `RENAME TABLE` and `TRUNCATE TABLE` in this
backend. All three forms were executed against MariaDB 13.1.1.

## 8. Reading the current database

`rhosocial.activerecord.backend.impl.mariadb.functions.schema.current_schema`
returns the namespace an unqualified reference resolves against:

```python
current_schema(dialect).to_sql()
# DATABASE()
```

`SELECT DATABASE()` and `SELECT SCHEMA()` both return the current database on
MariaDB — verified on a session connected to `test_db`, where each returned
`test_db`. `DATABASE()` returns `NULL` when no database has been selected, which
is why the function carries a note about the no-database-selected case rather
than assuming a value.

## 9. Common mistakes

**Treating a schema as a namespace inside the current database.** `__schema_name__ = "app"`
on a connection to `test_db` does not look for a schema `app` inside `test_db`. It
addresses the database `app`, and the statement fails if that database does not
exist or the account has no privilege on it.

**Expecting `search_path`-style resolution.** MariaDB has no ordered list of
databases to search. An unqualified name resolves against the connection's
default database and nothing else.

**Qualifying a database that does not exist yet.** Nothing validates the value
against the server. `schema_name` must be `None` or a non-empty string and the
dialect must be able to express a namespace; whether the database is present is
decided by the server, when the statement runs.

**Leaving the trigger name or table unqualified while qualifying the other.**
MariaDB requires a trigger and its table to share a database, and answers a
mismatched pair with error 1435.

**Using `""` to mean "no database".** It renders an error rather than an
unqualified reference. Use `None`, or leave the attribute unset.

**Reading a `DROP SCHEMA ... CASCADE` as "drop the database and its contents".**
The clause is refused. `DROP DATABASE` on MariaDB removes the database and
everything in it; there is nothing to cascade.

**Assuming the connection carries TLS by default on every server.** This backend
requests TLS unless `ssl_disabled=True`, which is what a server with
`require_secure_transport=ON` needs. Connecting without it fails at handshake:

```
Connections using insecure transport are prohibited while
--require_secure_transport=ON. (errno: 3159, sqlstate: 08004)
```

Pass `tls_version` alongside `ssl` to pin the protocol version.

## Cross-reference

`docs/modeling/schema_namespace.md` in the core repository covers the parts that
do not vary by backend: declaring `__schema_name__`, when the qualifier is read,
why DDL takes a `schema_name` of its own, and the backend support matrix.

## How these statements were checked

Rendering claims come from `MariaDBDialect(version=(13, 1, 1))` with
`PYTHONPATH=src .venv3.14-ubuntu26.04/bin/python`. Server behaviour —
`SELECT DATABASE()`, `SELECT SCHEMA()`, `CREATE SCHEMA` appearing in both
`SHOW DATABASES` and `SHOW SCHEMAS`, the four query shapes in §3, `CREATE OR
REPLACE TRIGGER`, `FOLLOWS` and `PRECEDES` with their effect on
`INFORMATION_SCHEMA.TRIGGERS.ACTION_ORDER`, the error-1435 rejection, and the
three `ALTER TABLE` forms in §7 — was executed against MariaDB 13.1.1 over TLS.
Syntax and version attributions for `CREATE TRIGGER`, `CREATE DATABASE`,
`ALTER TABLE` and `WAIT`/`NOWAIT` were checked against the MariaDB documentation
and the 10.1, 10.2 and 10.3 release notes.
