# src/rhosocial/activerecord/backend/impl/mariadb/mixins/partition.py
"""MariaDB table partitioning mixin — delegates to MySQL-compatible implementation."""

from rhosocial.activerecord.backend.impl.mysql.mixins.partition import MySQLPartitionMixin


class MariaDBPartitionMixin(MySQLPartitionMixin):
    """MariaDB table partitioning implementation.

    MariaDB supports the same partitioning strategies as MySQL (RANGE, LIST,
    HASH, KEY, RANGE COLUMNS, LIST COLUMNS, LINEAR variants, and subpartitioning).
    This mixin inherits all implementation from MySQLPartitionMixin since
    the partitioning SQL syntax is identical.
    """