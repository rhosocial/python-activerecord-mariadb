# rhosocial-activerecord MariaDB Backend Documentation

The MariaDB backend is the MariaDB backend implementation for
[rhosocial-activerecord](https://github.com/rhosocial/python-activerecord). It uses the
`mariadb` driver and extends the MySQL backend with MariaDB-specific behaviour, including
`OR REPLACE` on `CREATE TRIGGER`, `FOLLOWS` / `PRECEDES` trigger ordering, and
`WAIT` / `NOWAIT` on `ALTER TABLE`.

## Table of Contents

- **[Schema Namespaces](mariadb_specific_features/schema_namespace.md)**: declaring
  `__schema_name__`, the fact that `schema` is another name for a database, three-part
  column references, trigger placement, and `ALTER TABLE ... WAIT`

## Key facts at a glance

| Question | Answer |
|---|---|
| What does `schema_name` mean? | A database — `CREATE SCHEMA` is a synonym for `CREATE DATABASE` |
| Qualified table renders as | `` `app`.`orders` `` |
| Column references | Three parts on unaliased ranges: `` `app`.`orders`.`id` `` |
| After an alias | `` `o`.`id` `` |
| Current schema | `SELECT DATABASE()` or `SELECT SCHEMA()` |
| `CREATE SCHEMA` / `DROP SCHEMA` | Supported |
| Triggers | `OR REPLACE`, `FOLLOWS`, `PRECEDES` |

## Related documentation

- **[Schema Namespaces (core guide)](https://github.com/rhosocial/python-activerecord/tree/docs/docs/modeling/schema_namespace.md)**:
  the dialect-independent rules that every backend shares

---

> ⚠️ **Dependency note**: this backend depends on the core library
> `rhosocial-activerecord`. Install it together with the core library rather than
> independently.