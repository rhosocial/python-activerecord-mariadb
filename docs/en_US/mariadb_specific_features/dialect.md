<!-- docs/en_US/mariadb_specific_features/dialect.md -->
# MariaDB dialect

The dialect binds core expression objects to MariaDB SQL. It is the single
place where rendering decisions — quoting, literal formatting, clause order and
version-sensitive spelling — are made.

## Identifiers and quoting

MariaDB identifiers are quoted with backticks. Reserved words are escaped
against a version-aware list maintained in the backend (`reserved_words.py`),
so a column named `order` or `status` is rendered safely:

```sql
SELECT `users`.`name` FROM `users` WHERE `users`.`status` = %s
```

Placeholders are the `mariadb` connector's `%s` form; values travel as a
separate parameter tuple, never interpolated into the SQL text.

## AUTO_INCREMENT and RETURNING

`AUTO_INCREMENT` is rendered on integer primary-key columns. To retrieve a
database-generated key:

- use the backend's `RETURNING` support (MariaDB 10.5+) where applicable, or
- read `QueryResult.last_insert_id`, which is backed by `LAST_INSERT_ID()`.

`RETURNING` for `UPDATE` is a later addition (13.0) and is gated separately from
INSERT/DELETE/REPLACE.

## DDL spelling

The backend owns the MariaDB side of DDL: `ENGINE`, `CHARSET`, `COLLATE`,
`AUTO_INCREMENT`, `WITH SYSTEM VERSIONING`, index definitions and table
options. A column that says `NOT NULL` in the portable declaration stays
`NOT NULL`; optional columns remain nullable. See
[DDL Operations](../ddl/README.md).

## MariaDB-only expressions

Everything beyond portable SQL lives under
`rhosocial.activerecord.backend.impl.mariadb.expression`:

- `partition` — partition and subpartition DDL
- `json`, `json_table` — JSON path access and JSON_TABLE
- `spatial`, `match_against`, `set_type` — spatial predicates, full-text and SET operations
- `routine`, `admin`, `maintenance`, `show`, `status` — MariaDB administrative and introspection statements
- `table_options`, `alter_table`, `column` — engine/charset and column attributes

No hand-written SQL string is needed to use these; construct the expression and
call `.to_sql()` to preview it.

## Preview before executing

```python
sql, params = User.query().where(User.c.age >= 18).to_sql()
print(sql, params)
```

Only an explicit execution step sends the statement to the server, so every
piece of generated SQL can be inspected first.

## Version awareness

The dialect asks the connected server for its version and resolves feature gates
before emitting newer syntax. See [Version gates](version_gates.md) and
[Supported versions](../introduction/supported_versions.md).
