# docs/examples/ar-migration/01_partition_build.py
"""MariaDB AR migration example: offline dry-run of the partition BUILD suggestion.

No database and no ``ctx.apply()`` are involved.  We construct a ``MariaDBDialect``
with no connection, build a caller-owned plan (a plain dict), ask the dialect for
its build suggestion, and print the SQL rendered by each expression's ``to_sql()``.

MariaDB is one of the few backends with eight distinct ``PARTITION BY`` spellings;
this script walks all eight plus the explicit "unsupported strategy" path.  The
plan contract is intentionally small: ``keys`` is a sequence of column names,
``definitions`` is a sequence of ``MariaDBPartitionDefinition`` nodes, and
``count`` drives the HASH/KEY variants.
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

    # RANGE / RANGE COLUMNS: less_than boundaries on one (or more) keys.
    range_defs = (
        MariaDBPartitionDefinition("p0", less_than=(MariaDBPartitionValue(dialect, 10),)),
        MariaDBPartitionDefinition("p1", less_than=(MariaDBPartitionValue(dialect, 20),)),
    )
    render(
        "build / RANGE",
        dialect.suggest_partition_build("RANGE", {"keys": ["id"], "definitions": range_defs}),
    )
    render(
        "build / RANGE COLUMNS",
        dialect.suggest_partition_build(
            "RANGE COLUMNS", {"keys": ["created_at"], "definitions": range_defs}
        ),
    )

    # LIST / LIST COLUMNS: in_values boundaries instead of less_than.
    list_defs = (
        MariaDBPartitionDefinition("p_east", in_values=(MariaDBPartitionValue(dialect, "east"),)),
        MariaDBPartitionDefinition("p_west", in_values=(MariaDBPartitionValue(dialect, "west"),)),
    )
    render(
        "build / LIST",
        dialect.suggest_partition_build("LIST", {"keys": ["region"], "definitions": list_defs}),
    )
    render(
        "build / LIST COLUMNS",
        dialect.suggest_partition_build(
            "LIST COLUMNS", {"keys": ["region"], "definitions": list_defs}
        ),
    )

    # HASH / LINEAR HASH / KEY / LINEAR KEY: a key plus a partition count.
    for strategy in ("HASH", "LINEAR HASH", "KEY", "LINEAR KEY"):
        render(
            f"build / {strategy}",
            dialect.suggest_partition_build(strategy, {"keys": ["id"], "count": 4}),
        )

    # Unknown strategy: explicit unsupported tri-state, no expression and no SQL.
    render("build / unknown strategy", dialect.suggest_partition_build("NOT A STRATEGY", None))


if __name__ == "__main__":
    main()
