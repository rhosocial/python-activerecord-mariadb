# src/rhosocial/activerecord/backend/impl/mariadb/protocols/__init__.py
"""MariaDB dialect-specific protocol definitions.

This module provides modular protocol classes for features specific to MariaDB,
covering both features shared with MySQL and MariaDB-exclusive features.

MariaDB version mapping (relative to MySQL):
  - MySQL 5.6+ → MariaDB 10.0+
  - MySQL 5.7+ → MariaDB 10.2+
  - MySQL 8.0+ → MariaDB 10.3+
  - MySQL 8.4+ → MariaDB 11.0+

Protocol Organization:
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

from .cte import MariaDBCTESupport
from .dml import MariaDBDMLOperationSupport
from .fulltext_search import MariaDBFullTextSearchSupport
from .json import MariaDBJSONFunctionSupport
from .locking import MariaDBLockingSupport
from .modify_column import MariaDBModifyColumnSupport
from .partition import MariaDBPartitionSupport
from .returning import MariaDBReturningSupport
from .sequence import MariaDBSequenceSupport
from .set_operation import MariaDBIntersectExceptSupport
from .set_type import MariaDBSetTypeSupport
from .spatial import MariaDBSpatialSupport
from .system_versioning import MariaDBSystemVersioningSupport
from .table import MariaDBTableSupport
from .trigger import MariaDBTriggerSupport
from .window_function import MariaDBWindowFunctionSupport
from .rename_table import MariaDBRenameTableSupport
from .alter_table import MariaDBAlterTableSupport
from .maintenance import MariaDBMaintenanceSupport
from .routine import MariaDBRoutineSupport
from .admin import MariaDBAdminSupport

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
    'MariaDBRenameTableSupport',
    'MariaDBAlterTableSupport',
    'MariaDBMaintenanceSupport',
    'MariaDBRoutineSupport',
    'MariaDBAdminSupport',
]
