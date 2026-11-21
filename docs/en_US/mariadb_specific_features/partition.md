<!-- docs/en_US/mariadb_specific_features/partition.md -->
# MariaDB Partitioning

> 📖 Part of [MariaDB-Specific Features](README.md) · [Documentation home](../README.md)

MariaDB supports table partitioning: RANGE, RANGE COLUMNS, LIST, LIST COLUMNS,
HASH, KEY, and their LINEAR variants.

## Expression Layer

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBPartitionByRange,
    MariaDBPartitionValue,
)
from rhosocial.activerecord.backend.expression.objects import Table

expression = MariaDBPartitionByRange(
    dialect,
    [Column(dialect, "created_at")],
    partitions=[
        PartitionDefinitionExpression(
            dialect, "p2026", less_than=[MariaDBPartitionValue(dialect, "2027-01-01")]
        ),
    ],
)
```

Lifecycle expressions cover `ADD`, `DROP`, `TRUNCATE`, `REORGANIZE`,
`EXCHANGE`, `REMOVE PARTITIONING`, `COALESCE`, and the `ANALYZE` / `CHECK` /
`OPTIMIZE` / `REBUILD` / `REPAIR` maintenance spells.

## Suggestions and Introspection

MariaDB exposes its partition capability through two backend mechanisms:

1. **Backend suggestions** answer *how* each partition operation is spelled in
   MariaDB.  The dialect implements all eight core partition lifecycle
   suggestion protocols; each answer is a tuple of real expression nodes (or
   an explicit `False`/`None` tri-state when the strategy is unsupported).
2. **Introspection** answers *what* the server currently reports, via
   `information_schema.PARTITIONS` (the `MariaDBGetPartitionsExpression`
   statement and the `MariaDBPartitionInfo` records returned by the
   introspector).

```python
from rhosocial.activerecord.backend.dialect.protocols import (
    PartitionAddSuggestionSupport,
)
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import PartitionByRangeClause
from rhosocial.activerecord.backend.suggestion import PartitionSuggestionRenderer
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

dialect = MariaDBDialect()
assert isinstance(dialect, PartitionAddSuggestionSupport)
strategy = PartitionByRangeClause(dialect, [Column(dialect, "id")])

# `plan` is caller-owned and opaque: the dialect reads `table`, `definitions`,
# `keys`, `count`, `partition`, `into` and `partitions` by attribute or key.
operations = PartitionSuggestionRenderer().add(dialect, strategy, plan)  # doctest: +SKIP
```

Planning, validation and retention policy belong to the application layer.
The backend only supplies the MariaDB statement for each operation, so there
is no backend-specific plan, report, executor or maintenance type to import.

Like other DDL, partition statements are statement-level rather than
transaction-level: MariaDB commits them implicitly.

## Subpartitioning

MariaDB supports subpartitioning only with `HASH` and `KEY` (and their
`LINEAR` variants).  `SUBPARTITION BY RANGE` or `LIST` raises
`UnsupportedFeatureError` instead of being silently downgraded.

```python
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBSubpartitionClause, MariaDBSubpartitionStrategy,
)

subpartition_by = MariaDBSubpartitionClause(
    dialect,
    strategy=MariaDBSubpartitionStrategy.HASH,
    expression=Column(dialect, "tenant_id"),
    count=4,
)
```

A partition definition may carry explicit `subpartitions`
(`SubpartitionDefinitionExpression` nodes); those names override the template
for that parent partition. Storage options travel in the definition's `options`
(`PartitionOptionsExpression`) field.
