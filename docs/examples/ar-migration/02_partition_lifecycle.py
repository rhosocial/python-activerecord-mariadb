# docs/examples/ar-migration/02_partition_lifecycle.py
"""MariaDB AR migration example: offline dry-run of the partition LIFECYCLE suggestions.

Everything here is offline: a connection-less ``MariaDBDialect`` answers the
lifecycle protocols with MariaDB-owned expression nodes, and the only SQL shown
is what ``expr.to_sql()`` renders.  No hand-built SQL text and no ``ctx.apply()``.

Covered: table_drop, table_alter, add, drop, split, merge, retention, and the
explicit unsupported (``operations is False``) paths.  MariaDB's plan is a plain
dict read by attribute/key aliases (``table``, ``definitions``, ``partition_names``,
``partition``, ``into``, ``count``); ``table_drop`` even works without a plan.
"""

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBPartitionDefinition,
    MariaDBPartitionValue,
)


def render(label, suggestion):
    """Render a suggestion's expression tuple using only expr.to_sql()."""
    print(f"\n=== {label} ===")
    operations = suggestion.operations
    if operations is False:
        print("unsupported: operations is False (no SQL rendered)")
        return
    if operations is None:
        print("nothing to do: operations is None")
        return
    for index, expr in enumerate(operations, 1):
        sql, params = expr.to_sql()
        print(f"[{index}] {type(expr).__name__}")
        print(sql)
        if params:
            print(f"    params: {params}")


def main():
    dialect = MariaDBDialect()
    defs = (
        MariaDBPartitionDefinition("p0", less_than=(MariaDBPartitionValue(dialect, 10),)),
        MariaDBPartitionDefinition("p1", less_than=(MariaDBPartitionValue(dialect, 20),)),
        MariaDBPartitionDefinition("p2", less_than=(MariaDBPartitionValue(dialect, 30),)),
    )
    plan = {"table": "events", "definitions": defs}

    # table_drop: no plan needed -> REMOVE PARTITIONING then DROP TABLE (2 ops).
    render("table_drop / no plan", dialect.suggest_partition_table_drop("RANGE", None))
    render("table_drop / with plan", dialect.suggest_partition_table_drop("RANGE", plan))

    # table_alter: HASH/KEY -> COALESCE PARTITION; RANGE/LIST -> REMOVE PARTITIONING.
    render(
        "table_alter / HASH -> COALESCE",
        dialect.suggest_partition_table_alter("HASH", {"table": "events", "count": 2}),
    )
    render("table_alter / RANGE -> REMOVE", dialect.suggest_partition_table_alter("RANGE", plan))

    # add: ALTER TABLE ... ADD PARTITION with a new definition.
    new_def = (MariaDBPartitionDefinition("p3", less_than=(MariaDBPartitionValue(dialect, 40),)),)
    render(
        "add / RANGE",
        dialect.suggest_partition_add("RANGE", {"table": "events", "definitions": new_def}),
    )

    # drop: names can be given explicitly or read back from the plan definitions.
    render(
        "drop / explicit partition_names",
        dialect.suggest_partition_drop("RANGE", {"table": "events", "partition_names": ["p0"]}),
    )
    render("drop / names from definitions", dialect.suggest_partition_drop("RANGE", plan))

    # split: ALTER TABLE ... REORGANIZE PARTITION ... INTO.
    split_into = (
        MariaDBPartitionDefinition("p1a", less_than=(MariaDBPartitionValue(dialect, 15),)),
        MariaDBPartitionDefinition("p1b", less_than=(MariaDBPartitionValue(dialect, 20),)),
    )
    render(
        "split / RANGE",
        dialect.suggest_partition_split(
            "RANGE",
            {"table": "events", "partition": "p1", "into": split_into},
        ),
    )

    # merge: MariaDB has no MERGE PARTITION DDL -> always unsupported.
    render("merge / RANGE (always False)", dialect.suggest_partition_merge("RANGE", plan))

    # retention: one DROP PARTITION per RANGE definition carrying less_than.
    render("retention / RANGE", dialect.suggest_partition_retention("RANGE", plan))
    list_plan = {
        "table": "events",
        "definitions": (
            MariaDBPartitionDefinition(
                "p_east", in_values=(MariaDBPartitionValue(dialect, "east"),)
            ),
        ),
    }
    render("retention / LIST (unsupported)", dialect.suggest_partition_retention("LIST", list_plan))

    # Unsupported strategy on the lifecycle points -> explicit False tri-state.
    for name in ("add", "drop", "split", "table_alter"):
        render(
            f"{name} / unknown strategy",
            getattr(dialect, f"suggest_partition_{name}")("WRONG", plan),
        )


if __name__ == "__main__":
    main()
