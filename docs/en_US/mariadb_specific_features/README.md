<!-- docs/en_US/mariadb_specific_features/README.md -->
# MariaDB-Specific Features

This chapter is about what MariaDB does differently and how this backend spells
it. Core topics (modeling, querying, relationships, the generic expression
layer) are deliberately left to the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).

## Chapters

- [Field types](field_types.md) — MariaDB native and extended column types
- [Dialect](dialect.md) — quoting, literals and SQL spelling
- [Version gates](version_gates.md) — asking the connected server what it supports
- [Storage engines](storage_engine.md) — InnoDB and alternatives
- [Indexing](indexing.md) — index DDL and design notes
- [Introspection](introspection.md) — three layers of server answers
- [Partitioning](partition.md) — strategies, suggestions, introspection, subpartitioning
- [Datetime expressions](datetime_expressions.md) — `seconds_between` and fractional precision
- [EXPLAIN](explain.md) — plans and `ANALYZE FORMAT=JSON`

## Quick orientation

| If you need… | Start here |
|--------------|------------|
| A MariaDB column type on a model field | [Field types](field_types.md) |
| To know whether a feature works on the connected server | [Version gates](version_gates.md) |
| `ENGINE`, `CHARSET`, `AUTO_INCREMENT` in a `CREATE TABLE` | [Storage engines](storage_engine.md) |
| To add or inspect indexes | [Indexing](indexing.md) |
| To read what the server declares or has been doing | [Introspection](introspection.md) |
| To add/drop partitions over time | [Partitioning](partition.md) |
| Sub-second elapsed time in SQL | [Datetime expressions](datetime_expressions.md) |
| To read a query plan | [EXPLAIN](explain.md) |
