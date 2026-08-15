# src/rhosocial/activerecord/backend/impl/mariadb/protocols.py
"""MariaDB dialect-specific protocol definitions.

This module is a backward-compatibility shim that re-exports all protocols
from the modular protocols/ subdirectory.

For new code, import directly from the protocols subdirectory:
    from rhosocial.activerecord.backend.impl.mariadb.protocols import (
        MariaDBPartitionSupport,
        MariaDBJSONFunctionSupport,
        ...
    )

The protocols are organized as follows:
- dml.py: DML operations (INSERT IGNORE, REPLACE, LOAD DATA)
- trigger.py: Trigger DDL protocol
- table.py: Table DDL protocol
- set_type.py: SET type support
- json.py: JSON function support
- spatial.py: Spatial data types and functions
- fulltext_search.py: Full-text search support
- locking.py: Row-level locking (FOR UPDATE, FOR SHARE, SKIP LOCKED)
- modify_column.py: MODIFY/CHANGE COLUMN support
- sequence.py: SEQUENCE storage engine support (MariaDB 10.3+)
- returning.py: RETURNING clause support (MariaDB 10.5+)
- set_operation.py: INTERSECT/EXCEPT set operations
- system_versioning.py: System-versioned tables (MariaDB 10.3+)
- window_function.py: Window functions support
- cte.py: Common Table Expressions support
- partition.py: Table partitioning support
"""

# Import from modular protocols subdirectory
from .protocols import (
    MariaDBCTESupport,
    MariaDBDMLOperationSupport,
    MariaDBFullTextSearchSupport,
    MariaDBIntersectExceptSupport,
    MariaDBJSONFunctionSupport,
    MariaDBLockingSupport,
    MariaDBModifyColumnSupport,
    MariaDBPartitionSupport,
    MariaDBReturningSupport,
    MariaDBSequenceSupport,
    MariaDBSetTypeSupport,
    MariaDBSpatialSupport,
    MariaDBSystemVersioningSupport,
    MariaDBTableSupport,
    MariaDBTriggerSupport,
    MariaDBWindowFunctionSupport,
)

__all__ = [
    'MariaDBDMLOperationSupport',
    'MariaDBTriggerSupport',
    'MariaDBTableSupport',
    'MariaDBSetTypeSupport',
    'MariaDBJSONFunctionSupport',
    'MariaDBSpatialSupport',
    'MariaDBFullTextSearchSupport',
    'MariaDBLockingSupport',
    'MariaDBModifyColumnSupport',
    'MariaDBSequenceSupport',
    'MariaDBReturningSupport',
    'MariaDBIntersectExceptSupport',
    'MariaDBSystemVersioningSupport',
    'MariaDBWindowFunctionSupport',
    'MariaDBCTESupport',
    'MariaDBPartitionSupport',
]
