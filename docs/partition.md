# MariaDB Partitioning

MariaDB supports the same table-partitioning strategies as MySQL: RANGE,
RANGE COLUMNS, LIST, LIST COLUMNS, HASH, KEY, and their LINEAR variants.

## Expression Layer

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBPartitionByRange,
    MariaDBPartitionDefinition,
    MariaDBPartitionValue,
)
from rhosocial.activerecord.backend.expression.objects import Table

expression = MariaDBPartitionByRange(
    dialect,
    [Column(dialect, "created_at")],
    partitions=[
        MariaDBPartitionDefinition("p2026", less_than=[MariaDBPartitionValue(dialect, "2027-01-01")]),
    ],
)
```

Lifecycle expressions cover `ADD`, `DROP`, `TRUNCATE`, `REORGANIZE`,
`EXCHANGE`, `REMOVE PARTITIONING`, `COALESCE`, and the `ANALYZE` / `CHECK` /
`OPTIMIZE` / `REBUILD` / `REPAIR` maintenance spells.

## Backend-Level Maintenance

`MariaDBPartitionMaintenance` turns a caller-owned plan into the three
operations an application needs: add missing partitions, report the partition
tree, and drop partitions older than a cutoff.  It carries no table names,
calendar vocabulary, or retention defaults.

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBPartitionDefinition, MariaDBPartitionValue,
)
from rhosocial.activerecord.backend.impl.mariadb.partition_maintenance import (
    MariaDBPartitionMaintenance, MariaDBPartitionPlan,
)

plan = MariaDBPartitionPlan(
    "orders",
    (
        MariaDBPartitionDefinition("p2026_01", less_than=[MariaDBPartitionValue(dialect, "2026-02-01")]),
        MariaDBPartitionDefinition("p2026_02", less_than=[MariaDBPartitionValue(dialect, "2026-03-01")]),
    ),
)
maintenance = MariaDBPartitionMaintenance(backend)

report = maintenance.ensure(plan)                 # add what is missing
report = maintenance.list("orders", plan=plan)    # tree + missing + orphans
report = maintenance.validate(plan)               # method/boundary findings
report = maintenance.drop_before(plan, cutoff, dry_run=True)
```

Planning rules are reported rather than hidden:

- a definition above the current RANGE maximum is appended with
  `ADD PARTITION`;
- a definition in a gap below the maximum reorganises the following partition
  with `REORGANIZE PARTITION ... INTO (missing definitions, that partition)`;
- a definition that must land before an existing `MAXVALUE` partition
  reorganises that `MAXVALUE` partition the same way;
- an existing partition the plan does not name, boundary or method drift, and
  a subpartitioned reorganisation target are reported in `skipped` with the
  reason the DDL is unsafe;
- `validate` compares `PARTITION_NAME`, `PARTITION_METHOD` and
  `PARTITION_DESCRIPTION`, filling `missing`, `orphans` and `issues`;
- `drop_before` treats a partition whose upper bound equals the cutoff as
  expired (`<=`) and never drops the last partition of a table;
- `drop_before` is a dry run unless `dry_run=False` is passed.

`ensure`, `validate` and `drop_before` are statement-level, not
transaction-level: MariaDB partition DDL implicitly commits.  A report
describes what one statement did.  `AsyncMariaDBPartitionMaintenance` offers
the same methods with `await`.

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

A partition definition may carry explicit `subpartition_definitions`; those
names override the template for that parent partition.
